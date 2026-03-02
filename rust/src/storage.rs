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
