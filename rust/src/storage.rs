//! SQLite-backed storage for DynamoDB tables

use crate::models::*;
use chrono::Utc;
use rusqlite::{params, Connection, Result as SqliteResult};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use thiserror::Error;
use uuid::Uuid;

/// Storage error types
#[derive(Error, Debug)]
pub enum StorageError {
    #[error("Table already exists: {0}")]
    TableAlreadyExists(String),
    #[error("Table not found: {0}")]
    TableNotFound(String),
    #[error("Database error: {0}")]
    DatabaseError(#[from] rusqlite::Error),
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    JsonError(#[from] serde_json::Error),
    #[error("Invalid key: {0}")]
    InvalidKey(String),
}

/// Manages DynamoDB tables in SQLite
pub struct TableManager {
    data_directory: PathBuf,
    namespace: String,
    connections: Arc<Mutex<HashMap<String, Connection>>>,
}

impl TableManager {
    /// Create a new TableManager
    pub fn new(data_directory: impl Into<PathBuf>, namespace: impl Into<String>) -> Result<Self, StorageError> {
        let data_directory = data_directory.into();
        let namespace = namespace.into();
        
        // Ensure namespace directory exists
        let ns_path = data_directory.join(&namespace);
        fs::create_dir_all(&ns_path)?;

        Ok(Self {
            data_directory,
            namespace,
            connections: Arc::new(Mutex::new(HashMap::new())),
        })
    }

    /// Get the database file path for a table
    fn get_db_path(&self, table_name: &str) -> PathBuf {
        self.data_directory
            .join(&self.namespace)
            .join(format!("{}.db", table_name))
    }

    /// Create a new table
    pub fn create_table(&self, req: &DynamoDBRequest) -> Result<TableMetadata, StorageError> {
        let table_name = req
            .table_name
            .as_ref()
            .ok_or_else(|| StorageError::InvalidKey("Table name is required".to_string()))?;

        let db_path = self.get_db_path(table_name);

        // Check if table already exists
        if db_path.exists() {
            return Err(StorageError::TableAlreadyExists(table_name.clone()));
        }

        // Create database
        let conn = Connection::open(&db_path)?;

        // Create items table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS items (
                pk TEXT NOT NULL,
                sk TEXT,
                data BLOB NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (pk, sk)
            )",
            [],
        )?;

        // Create metadata table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS __table_metadata (
                key TEXT PRIMARY KEY,
                value BLOB
            )",
            [],
        )?;

        // Create index metadata table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS __index_metadata (
                index_name TEXT PRIMARY KEY,
                index_type TEXT NOT NULL,
                key_schema BLOB NOT NULL,
                projection_type TEXT NOT NULL,
                projected_attributes BLOB,
                index_status TEXT,
                backfilling INTEGER,
                provisioned_throughput BLOB
            )",
            [],
        )?;

        // Generate table metadata
        let now = Utc::now();
        let table_id = Uuid::new_v4().to_string();

        let billing_mode = req.billing_mode.as_deref().unwrap_or("PROVISIONED");
        let provisioned_throughput = if billing_mode == "PROVISIONED" {
            Some(req.provisioned_throughput.clone().unwrap_or_default())
        } else {
            None
        };

        let metadata = TableMetadata {
            table_name: table_name.clone(),
            table_arn: Some(format!(
                "arn:aws:dynamodb:local:{}:table/{}",
                self.namespace, table_name
            )),
            table_id: Some(table_id),
            table_status: "ACTIVE".to_string(),
            key_schema: req.key_schema.clone().unwrap_or_default(),
            attribute_definitions: req.attribute_definitions.clone().unwrap_or_default(),
            item_count: 0,
            table_size_bytes: 0,
            creation_date_time: now,
            billing_mode_summary: Some(BillingModeSummary {
                billing_mode: billing_mode.to_string(),
                last_update_to_pay_per_request_date_time: None,
            }),
            provisioned_throughput,
            global_secondary_indexes: req.global_secondary_indexes.clone(),
            local_secondary_indexes: req.local_secondary_indexes.clone(),
            tags: req.tags.clone(),
        };

        // Store metadata
        self.store_metadata(&conn, &metadata)?;

        // Store GSI metadata
        if let Some(gsis) = &metadata.global_secondary_indexes {
            for gsi in gsis {
                self.store_index_metadata(&conn, gsi, "GSI")?;
            }
        }

        // Store LSI metadata
        if let Some(lsis) = &metadata.local_secondary_indexes {
            for lsi in lsis {
                self.store_index_metadata(&conn, lsi, "LSI")?;
            }
        }

        // Store connection for reuse
        self.connections
            .lock()
            .unwrap()
            .insert(table_name.clone(), conn);

        Ok(metadata)
    }

    /// Delete a table
    pub fn delete_table(&self, table_name: &str) -> Result<Option<TableMetadata>, StorageError> {
        let db_path = self.get_db_path(table_name);

        if !db_path.exists() {
            return Ok(None);
        }

        // Get metadata before deletion
        let metadata = self.describe_table(table_name).ok();

        // Remove from connections
        self.connections.lock().unwrap().remove(table_name);

        // Delete database file
        fs::remove_file(&db_path)?;

        Ok(metadata)
    }

    /// List all tables
    pub fn list_tables(&self) -> Result<Vec<String>, StorageError> {
        let ns_path = self.data_directory.join(&self.namespace);
        
        if !ns_path.exists() {
            return Ok(Vec::new());
        }

        let mut tables = Vec::new();
        for entry in fs::read_dir(&ns_path)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_file() {
                if let Some(ext) = path.extension() {
                    if ext == "db" {
                        if let Some(stem) = path.file_stem() {
                            tables.push(stem.to_string_lossy().to_string());
                        }
                    }
                }
            }
        }

        tables.sort();
        Ok(tables)
    }

    /// Describe a table
    pub fn describe_table(&self, table_name: &str) -> Result<TableMetadata, StorageError> {
        let db_path = self.get_db_path(table_name);

        if !db_path.exists() {
            return Err(StorageError::TableNotFound(table_name.to_string()));
        }

        // Check if we have a cached connection
        let mut connections = self.connections.lock().unwrap();
        
        if !connections.contains_key(table_name) {
            let conn = Connection::open(&db_path)?;
            connections.insert(table_name.to_string(), conn);
        }

        let conn = connections.get(table_name).unwrap();
        self.load_metadata(conn, table_name)
    }

    /// Store table metadata
    fn store_metadata(&self, conn: &Connection, metadata: &TableMetadata) -> SqliteResult<()> {
        let metadata_json = serde_json::to_vec(metadata).map_err(|e| {
            rusqlite::Error::ToSqlConversionFailure(Box::new(e))
        })?;

        conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?1, ?2)",
            params!["full_metadata", metadata_json],
        )?;

        Ok(())
    }

    /// Load table metadata
    fn load_metadata(&self, conn: &Connection, table_name: &str) -> Result<TableMetadata, StorageError> {
        let mut stmt = conn.prepare(
            "SELECT value FROM __table_metadata WHERE key = ?"
        )?;

        let metadata_json: Vec<u8> = stmt.query_row(
            ["full_metadata"],
            |row| row.get(0),
        ).map_err(|_| StorageError::TableNotFound(table_name.to_string()))?;

        let metadata: TableMetadata = serde_json::from_slice(&metadata_json)?;
        Ok(metadata)
    }

    /// Store index metadata
    fn store_index_metadata<T: serde::Serialize>(
        &self,
        conn: &Connection,
        index: &T,
        index_type: &str,
    ) -> SqliteResult<()> {
        // Extract fields using serialization
        let index_json = serde_json::to_value(index).map_err(|e| {
            rusqlite::Error::ToSqlConversionFailure(Box::new(e))
        })?;

        let index_name = index_json["index_name"].as_str().unwrap_or("");
        let key_schema = index_json["key_schema"].to_string();
        let projection = &index_json["projection"];
        let projection_type = projection["projection_type"].as_str().unwrap_or("ALL");
        let non_key_attrs = projection["non_key_attributes"].as_array().map(|a| {
            serde_json::to_string(a).unwrap_or_default()
        });

        conn.execute(
            "INSERT INTO __index_metadata (
                index_name, index_type, key_schema, projection_type,
                projected_attributes, index_status, backfilling
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                index_name,
                index_type,
                key_schema,
                projection_type,
                non_key_attrs,
                "ACTIVE",
                0
            ],
        )?;

        Ok(())
    }

    /// Get connection for a table
    pub fn get_connection(&self, table_name: &str) -> Result<Connection, StorageError> {
        let db_path = self.get_db_path(table_name);
        
        if !db_path.exists() {
            return Err(StorageError::TableNotFound(table_name.to_string()));
        }

        Ok(Connection::open(&db_path)?)
    }

    /// Update a table
    pub fn update_table(&self, req: &UpdateTableRequest) -> Result<TableMetadata, StorageError> {
        let table_name = &req.table_name;
        let db_path = self.get_db_path(table_name);

        if !db_path.exists() {
            return Err(StorageError::TableNotFound(table_name.clone()));
        }

        // Get existing connection or create new one
        let mut connections = self.connections.lock().unwrap();
        
        if !connections.contains_key(table_name) {
            let conn = Connection::open(&db_path)?;
            connections.insert(table_name.to_string(), conn);
        }

        let conn = connections.get(table_name).unwrap();
        let mut metadata = self.load_metadata(conn, table_name)?;

        // Check table status - only allow updates on ACTIVE tables
        if metadata.table_status != "ACTIVE" {
            return Err(StorageError::InvalidKey(format!(
                "Table {} is not in ACTIVE state",
                table_name
            )));
        }

        // Update provisioned throughput
        if let Some(throughput) = &req.provisioned_throughput {
            metadata.provisioned_throughput = Some(throughput.clone());
        }

        // Update billing mode
        if let Some(billing_mode) = &req.billing_mode {
            let now = Utc::now();
            metadata.billing_mode_summary = Some(BillingModeSummary {
                billing_mode: billing_mode.clone(),
                last_update_to_pay_per_request_date_time: if billing_mode == "PAY_PER_REQUEST" {
                    Some(now)
                } else {
                    None
                },
            });

            // Clear provisioned throughput if switching to PAY_PER_REQUEST
            if billing_mode == "PAY_PER_REQUEST" {
                metadata.provisioned_throughput = None;
            }
        }

        // Update global secondary indexes
        if let Some(gsi_updates) = &req.global_secondary_index_updates {
            let mut gsis = metadata.global_secondary_indexes.unwrap_or_default();

            for update in gsi_updates {
                // Handle Create
                if let Some(create) = &update.create {
                    // Check for duplicate index name
                    if gsis.iter().any(|g| g.index_name == create.index_name) {
                        return Err(StorageError::InvalidKey(format!(
                            "Global secondary index {} already exists",
                            create.index_name
                        )));
                    }

                    let new_gsi = GlobalSecondaryIndex {
                        index_name: create.index_name.clone(),
                        key_schema: create.key_schema.clone(),
                        projection: create.projection.clone(),
                        provisioned_throughput: create.provisioned_throughput.clone(),
                    };
                    gsis.push(new_gsi);
                }

                // Handle Update (throughput changes)
                if let Some(update_gsi) = &update.update {
                    if let Some(gsi) = gsis.iter_mut().find(|g| g.index_name == update_gsi.index_name) {
                        if let Some(throughput) = &update_gsi.provisioned_throughput {
                            gsi.provisioned_throughput = Some(throughput.clone());
                        }
                    } else {
                        return Err(StorageError::InvalidKey(format!(
                            "Global secondary index {} not found",
                            update_gsi.index_name
                        )));
                    }
                }

                // Handle Delete
                if let Some(delete) = &update.delete {
                    let original_len = gsis.len();
                    gsis.retain(|g| g.index_name != delete.index_name);
                    if gsis.len() == original_len {
                        return Err(StorageError::InvalidKey(format!(
                            "Global secondary index {} not found",
                            delete.index_name
                        )));
                    }
                }
            }

            metadata.global_secondary_indexes = if gsis.is_empty() { None } else { Some(gsis) };
        }

        // Update attribute definitions if provided
        if let Some(attr_defs) = &req.attribute_definitions {
            metadata.attribute_definitions = attr_defs.clone();
        }

        // Store updated metadata
        self.store_metadata(conn, &metadata)?;

        // Release connection lock before returning
        drop(connections);

        Ok(metadata)
    }

    /// Update time to live settings for a table
    pub fn update_time_to_live(
        &self,
        table_name: &str,
        ttl_spec: &TimeToLiveSpecification,
    ) -> Result<TimeToLiveDescription, StorageError> {
        let db_path = self.get_db_path(table_name);

        if !db_path.exists() {
            return Err(StorageError::TableNotFound(table_name.to_string()));
        }

        // Get existing connection or create new one
        let mut connections = self.connections.lock().unwrap();

        if !connections.contains_key(table_name) {
            let conn = Connection::open(&db_path)?;
            connections.insert(table_name.to_string(), conn);
        }

        let conn = connections.get(table_name).unwrap();

        // Store TTL configuration in metadata table
        let ttl_config_json = serde_json::to_vec(ttl_spec).map_err(|e| {
            rusqlite::Error::ToSqlConversionFailure(Box::new(e))
        })?;

        conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?1, ?2)",
            params!["ttl_config", ttl_config_json],
        )?;

        // Build and return the description
        let status = if ttl_spec.enabled {
            "ENABLED".to_string()
        } else {
            "DISABLED".to_string()
        };

        let description = TimeToLiveDescription {
            time_to_live_status: status,
            attribute_name: Some(ttl_spec.attribute_name.clone()),
        };

        drop(connections);

        Ok(description)
    }

    /// Get time to live settings for a table
    pub fn describe_time_to_live(
        &self,
        table_name: &str,
    ) -> Result<TimeToLiveDescription, StorageError> {
        let db_path = self.get_db_path(table_name);

        if !db_path.exists() {
            return Err(StorageError::TableNotFound(table_name.to_string()));
        }

        // Get existing connection or create new one
        let mut connections = self.connections.lock().unwrap();

        if !connections.contains_key(table_name) {
            let conn = Connection::open(&db_path)?;
            connections.insert(table_name.to_string(), conn);
        }

        let conn = connections.get(table_name).unwrap();

        // Load TTL configuration from metadata table
        let ttl_config: Option<Vec<u8>> = conn
            .query_row(
                "SELECT value FROM __table_metadata WHERE key = ?",
                ["ttl_config"],
                |row| row.get(0),
            )
            .ok();

        let description = if let Some(config_json) = ttl_config {
            let spec: TimeToLiveSpecification = serde_json::from_slice(&config_json)?;
            let status = if spec.enabled {
                "ENABLED".to_string()
            } else {
                "DISABLED".to_string()
            };
            TimeToLiveDescription {
                time_to_live_status: status,
                attribute_name: Some(spec.attribute_name),
            }
        } else {
            // No TTL configuration found - return DISABLED status
            TimeToLiveDescription {
                time_to_live_status: "DISABLED".to_string(),
                attribute_name: None,
            }
        };

        drop(connections);

        Ok(description)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn setup_test_manager() -> (TableManager, TempDir) {
        let temp_dir = TempDir::new().unwrap();
        let manager = TableManager::new(temp_dir.path(), "test").unwrap();
        (manager, temp_dir)
    }

    fn create_test_request(table_name: &str) -> DynamoDBRequest {
        DynamoDBRequest {
            table_name: Some(table_name.to_string()),
            key_schema: Some(vec![
                KeySchemaElement::hash("pk"),
            ]),
            attribute_definitions: Some(vec![
                AttributeDefinition::s("pk"),
            ]),
            billing_mode: Some("PAY_PER_REQUEST".to_string()),
            ..Default::default()
        }
    }

    #[test]
    fn test_create_table() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");

        let metadata = manager.create_table(&req).unwrap();
        
        assert_eq!(metadata.table_name, "TestTable");
        assert_eq!(metadata.table_status, "ACTIVE");
        assert_eq!(metadata.key_schema.len(), 1);
    }

    #[test]
    fn test_create_duplicate_table() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");

        manager.create_table(&req).unwrap();
        
        let result = manager.create_table(&req);
        assert!(matches!(result, Err(StorageError::TableAlreadyExists(_))));
    }

    #[test]
    fn test_list_tables() {
        let (manager, _temp) = setup_test_manager();
        
        let req1 = create_test_request("Table1");
        let req2 = create_test_request("Table2");
        
        manager.create_table(&req1).unwrap();
        manager.create_table(&req2).unwrap();
        
        let tables = manager.list_tables().unwrap();
        assert_eq!(tables.len(), 2);
        assert!(tables.contains(&"Table1".to_string()));
        assert!(tables.contains(&"Table2".to_string()));
    }

    #[test]
    fn test_describe_table() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        let metadata = manager.describe_table("TestTable").unwrap();
        assert_eq!(metadata.table_name, "TestTable");
    }

    #[test]
    fn test_describe_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let result = manager.describe_table("NonExistent");
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_delete_table() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        let metadata = manager.delete_table("TestTable").unwrap();
        assert!(metadata.is_some());
        
        let tables = manager.list_tables().unwrap();
        assert!(tables.is_empty());
    }

    #[test]
    fn test_delete_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let metadata = manager.delete_table("NonExistent").unwrap();
        assert!(metadata.is_none());
    }

    #[test]
    fn test_create_table_with_gsi() {
        let (manager, _temp) = setup_test_manager();
        
        let req = DynamoDBRequest {
            table_name: Some("TestTable".to_string()),
            key_schema: Some(vec![
                KeySchemaElement::hash("pk"),
                KeySchemaElement::range("sk"),
            ]),
            attribute_definitions: Some(vec![
                AttributeDefinition::s("pk"),
                AttributeDefinition::s("sk"),
                AttributeDefinition::s("gsi_pk"),
            ]),
            global_secondary_indexes: Some(vec![
                GlobalSecondaryIndex {
                    index_name: "GSI1".to_string(),
                    key_schema: vec![
                        KeySchemaElement::hash("gsi_pk"),
                    ],
                    projection: Projection {
                        projection_type: "ALL".to_string(),
                        non_key_attributes: None,
                    },
                    provisioned_throughput: None,
                },
            ]),
            ..Default::default()
        };
        
        let metadata = manager.create_table(&req).unwrap();
        assert_eq!(metadata.global_secondary_indexes.as_ref().unwrap().len(), 1);
    }

    #[test]
    fn test_update_table_throughput() {
        let (manager, _temp) = setup_test_manager();
        
        // Create table with initial throughput
        let create_req = DynamoDBRequest {
            table_name: Some("TestTable".to_string()),
            key_schema: Some(vec![
                KeySchemaElement::hash("pk"),
            ]),
            attribute_definitions: Some(vec![
                AttributeDefinition::s("pk"),
            ]),
            billing_mode: Some("PROVISIONED".to_string()),
            provisioned_throughput: Some(ProvisionedThroughput {
                read_capacity_units: 5,
                write_capacity_units: 5,
            }),
            ..Default::default()
        };
        manager.create_table(&create_req).unwrap();

        // Update throughput
        let update_req = UpdateTableRequest {
            table_name: "TestTable".to_string(),
            attribute_definitions: None,
            billing_mode: None,
            global_secondary_index_updates: None,
            provisioned_throughput: Some(ProvisionedThroughput {
                read_capacity_units: 10,
                write_capacity_units: 10,
            }),
        };

        let metadata = manager.update_table(&update_req).unwrap();
        assert_eq!(metadata.provisioned_throughput.as_ref().unwrap().read_capacity_units, 10);
        assert_eq!(metadata.provisioned_throughput.as_ref().unwrap().write_capacity_units, 10);
    }

    #[test]
    fn test_update_table_billing_mode() {
        let (manager, _temp) = setup_test_manager();
        
        // Create table with PROVISIONED billing
        let create_req = DynamoDBRequest {
            table_name: Some("TestTable".to_string()),
            key_schema: Some(vec![
                KeySchemaElement::hash("pk"),
            ]),
            attribute_definitions: Some(vec![
                AttributeDefinition::s("pk"),
            ]),
            billing_mode: Some("PROVISIONED".to_string()),
            provisioned_throughput: Some(ProvisionedThroughput {
                read_capacity_units: 5,
                write_capacity_units: 5,
            }),
            ..Default::default()
        };
        manager.create_table(&create_req).unwrap();

        // Switch to PAY_PER_REQUEST
        let update_req = UpdateTableRequest {
            table_name: "TestTable".to_string(),
            attribute_definitions: None,
            billing_mode: Some("PAY_PER_REQUEST".to_string()),
            global_secondary_index_updates: None,
            provisioned_throughput: None,
        };

        let metadata = manager.update_table(&update_req).unwrap();
        assert_eq!(metadata.billing_mode_summary.as_ref().unwrap().billing_mode, "PAY_PER_REQUEST");
        assert!(metadata.provisioned_throughput.is_none());
    }

    #[test]
    fn test_update_table_gsi_operations() {
        let (manager, _temp) = setup_test_manager();
        
        // Create table with one GSI
        let create_req = DynamoDBRequest {
            table_name: Some("TestTable".to_string()),
            key_schema: Some(vec![
                KeySchemaElement::hash("pk"),
            ]),
            attribute_definitions: Some(vec![
                AttributeDefinition::s("pk"),
                AttributeDefinition::s("gsi1_pk"),
            ]),
            global_secondary_indexes: Some(vec![
                GlobalSecondaryIndex {
                    index_name: "GSI1".to_string(),
                    key_schema: vec![
                        KeySchemaElement::hash("gsi1_pk"),
                    ],
                    projection: Projection {
                        projection_type: "ALL".to_string(),
                        non_key_attributes: None,
                    },
                    provisioned_throughput: Some(ProvisionedThroughput {
                        read_capacity_units: 5,
                        write_capacity_units: 5,
                    }),
                },
            ]),
            ..Default::default()
        };
        manager.create_table(&create_req).unwrap();

        // Test adding a new GSI
        let update_req = UpdateTableRequest {
            table_name: "TestTable".to_string(),
            attribute_definitions: None,
            billing_mode: None,
            global_secondary_index_updates: Some(vec![
                GlobalSecondaryIndexUpdate {
                    create: Some(CreateGlobalSecondaryIndexAction {
                        index_name: "GSI2".to_string(),
                        key_schema: vec![
                            KeySchemaElement::hash("pk"),
                        ],
                        projection: Projection {
                            projection_type: "KEYS_ONLY".to_string(),
                            non_key_attributes: None,
                        },
                        provisioned_throughput: Some(ProvisionedThroughput {
                            read_capacity_units: 3,
                            write_capacity_units: 3,
                        }),
                    }),
                    update: None,
                    delete: None,
                },
            ]),
            provisioned_throughput: None,
        };

        let metadata = manager.update_table(&update_req).unwrap();
        let gsis = metadata.global_secondary_indexes.unwrap();
        assert_eq!(gsis.len(), 2);
        assert!(gsis.iter().any(|g| g.index_name == "GSI2"));

        // Test updating GSI throughput
        let update_throughput_req = UpdateTableRequest {
            table_name: "TestTable".to_string(),
            attribute_definitions: None,
            billing_mode: None,
            global_secondary_index_updates: Some(vec![
                GlobalSecondaryIndexUpdate {
                    create: None,
                    update: Some(UpdateGlobalSecondaryIndexAction {
                        index_name: "GSI1".to_string(),
                        provisioned_throughput: Some(ProvisionedThroughput {
                            read_capacity_units: 10,
                            write_capacity_units: 10,
                        }),
                    }),
                    delete: None,
                },
            ]),
            provisioned_throughput: None,
        };

        let metadata = manager.update_table(&update_throughput_req).unwrap();
        let gsis = metadata.global_secondary_indexes.unwrap();
        let gsi1 = gsis.iter().find(|g| g.index_name == "GSI1").unwrap();
        assert_eq!(gsi1.provisioned_throughput.as_ref().unwrap().read_capacity_units, 10);

        // Test deleting a GSI
        let delete_gsi_req = UpdateTableRequest {
            table_name: "TestTable".to_string(),
            attribute_definitions: None,
            billing_mode: None,
            global_secondary_index_updates: Some(vec![
                GlobalSecondaryIndexUpdate {
                    create: None,
                    update: None,
                    delete: Some(DeleteGlobalSecondaryIndexAction {
                        index_name: "GSI2".to_string(),
                    }),
                },
            ]),
            provisioned_throughput: None,
        };

        let metadata = manager.update_table(&delete_gsi_req).unwrap();
        let gsis = metadata.global_secondary_indexes.unwrap();
        assert_eq!(gsis.len(), 1);
        assert!(!gsis.iter().any(|g| g.index_name == "GSI2"));
    }

    #[test]
    fn test_update_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let update_req = UpdateTableRequest {
            table_name: "NonExistent".to_string(),
            attribute_definitions: None,
            billing_mode: None,
            global_secondary_index_updates: None,
            provisioned_throughput: Some(ProvisionedThroughput {
                read_capacity_units: 10,
                write_capacity_units: 10,
            }),
        };

        let result = manager.update_table(&update_req);
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_update_time_to_live() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Enable TTL
        let ttl_spec = TimeToLiveSpecification {
            enabled: true,
            attribute_name: "expires_at".to_string(),
        };
        
        let description = manager.update_time_to_live("TestTable", &ttl_spec).unwrap();
        assert_eq!(description.time_to_live_status, "ENABLED");
        assert_eq!(description.attribute_name, Some("expires_at".to_string()));
        
        // Disable TTL
        let ttl_spec_disabled = TimeToLiveSpecification {
            enabled: false,
            attribute_name: "expires_at".to_string(),
        };
        
        let description = manager.update_time_to_live("TestTable", &ttl_spec_disabled).unwrap();
        assert_eq!(description.time_to_live_status, "DISABLED");
        assert_eq!(description.attribute_name, Some("expires_at".to_string()));
    }

    #[test]
    fn test_describe_time_to_live() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Before setting TTL - should return DISABLED
        let description = manager.describe_time_to_live("TestTable").unwrap();
        assert_eq!(description.time_to_live_status, "DISABLED");
        assert_eq!(description.attribute_name, None);
        
        // Enable TTL
        let ttl_spec = TimeToLiveSpecification {
            enabled: true,
            attribute_name: "ttl".to_string(),
        };
        manager.update_time_to_live("TestTable", &ttl_spec).unwrap();
        
        // After enabling TTL
        let description = manager.describe_time_to_live("TestTable").unwrap();
        assert_eq!(description.time_to_live_status, "ENABLED");
        assert_eq!(description.attribute_name, Some("ttl".to_string()));
    }

    #[test]
    fn test_update_time_to_live_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let ttl_spec = TimeToLiveSpecification {
            enabled: true,
            attribute_name: "ttl".to_string(),
        };
        
        let result = manager.update_time_to_live("NonExistent", &ttl_spec);
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_describe_time_to_live_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let result = manager.describe_time_to_live("NonExistent");
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }
}

// Implement Default for DynamoDBRequest for testing
impl Default for DynamoDBRequest {
    fn default() -> Self {
        Self {
            table_name: None,
            key_schema: None,
            attribute_definitions: None,
            billing_mode: None,
            global_secondary_indexes: None,
            local_secondary_indexes: None,
            provisioned_throughput: None,
            tags: None,
            resource_arn: None,
            tag_keys: None,
            key: None,
            item: None,
            index_name: None,
            consistent_read: None,
            exclusive_start_key: None,
            expression_attribute_names: None,
            expression_attribute_values: None,
            filter_expression: None,
            key_condition_expression: None,
            limit: None,
            projection_expression: None,
            return_consumed_capacity: None,
            return_values: None,
            scan_index_forward: None,
            select: None,
            update_expression: None,
            condition_expression: None,
        }
    }
}
