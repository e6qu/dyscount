//! SQLite-backed storage for DynamoDB tables

use crate::models::*;
use chrono::{DateTime, Utc};
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

        // Create tags table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS __tags (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at INTEGER NOT NULL
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

        // Store stream specification if provided
        if let Some(stream_spec) = &req.stream_specification {
            self.store_stream_specification(&conn, stream_spec)?;
        }

        // Store connection for reuse
        self.connections
            .lock()
            .unwrap()
            .insert(table_name.clone(), conn);

        Ok(metadata)
    }

    /// Store stream specification in table metadata
    fn store_stream_specification(
        &self,
        conn: &Connection,
        stream_spec: &StreamSpecification,
    ) -> SqliteResult<()> {
        let spec_json = serde_json::to_vec(stream_spec).map_err(|e| {
            rusqlite::Error::ToSqlConversionFailure(Box::new(e))
        })?;

        conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?1, ?2)",
            params!["stream_specification", spec_json],
        )?;

        Ok(())
    }

    /// Get stream specification for a table
    pub fn get_stream_specification(
        &self,
        table_name: &str,
    ) -> Result<Option<StreamSpecification>, StorageError> {
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

        // Load stream specification from metadata table
        let spec_json: Option<Vec<u8>> = conn
            .query_row(
                "SELECT value FROM __table_metadata WHERE key = ?",
                ["stream_specification"],
                |row| row.get(0),
            )
            .ok();

        let spec = if let Some(json) = spec_json {
            Some(serde_json::from_slice(&json)?)
        } else {
            None
        };

        drop(connections);

        Ok(spec)
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

    /// Get the path for backup storage directory
    fn get_backups_dir(&self) -> PathBuf {
        self.data_directory.join(&self.namespace).join("__backups")
    }

    /// Get the path for a specific backup database
    fn get_backup_db_path(&self, backup_id: &str) -> PathBuf {
        self.get_backups_dir().join(format!("{}.db", backup_id))
    }

    /// Initialize the backup storage
    fn init_backup_storage(&self) -> Result<Connection, StorageError> {
        let backups_dir = self.get_backups_dir();
        fs::create_dir_all(&backups_dir)?;

        let metadata_db_path = backups_dir.join("metadata.db");
        let conn = Connection::open(&metadata_db_path)?;

        // Create backup metadata table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS backups (
                backup_id TEXT PRIMARY KEY,
                backup_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                table_arn TEXT,
                backup_status TEXT NOT NULL,
                backup_size_bytes INTEGER NOT NULL DEFAULT 0,
                backup_creation_date_time TEXT NOT NULL,
                source_table_metadata BLOB
            )",
            [],
        )?;

        Ok(conn)
    }

    /// Create a backup of a table
    pub fn create_backup(
        &self,
        table_name: &str,
        backup_name: Option<String>,
    ) -> Result<BackupDescription, StorageError> {
        // Check if table exists
        let table_metadata = self.describe_table(table_name)?;

        // Initialize backup storage
        let conn = self.init_backup_storage()?;

        // Generate backup ID and name
        let backup_id = Uuid::new_v4().to_string();
        let backup_name = backup_name.unwrap_or_else(|| {
            format!("{}-backup-{}", table_name, chrono::Local::now().format("%Y%m%d-%H%M%S"))
        });

        let now = Utc::now();
        let backup_arn = format!(
            "arn:aws:dynamodb:local:{}:table/{}/backup/{}:{}",
            self.namespace, table_name, self.namespace, backup_id
        );

        // Serialize source table metadata
        let source_metadata_json = serde_json::to_vec(&table_metadata)?;

        // Insert backup metadata
        conn.execute(
            "INSERT INTO backups (
                backup_id, backup_name, table_name, table_arn, 
                backup_status, backup_size_bytes, backup_creation_date_time, source_table_metadata
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                backup_id,
                backup_name,
                table_name,
                table_metadata.table_arn,
                "AVAILABLE",
                table_metadata.table_size_bytes,
                now.to_rfc3339(),
                source_metadata_json
            ],
        )?;

        // Copy table data to backup database
        let source_db_path = self.get_db_path(table_name);
        let backup_db_path = self.get_backup_db_path(&backup_id);

        // Use SQLite backup API to copy the entire database
        let source_conn = Connection::open(&source_db_path)?;
        let mut backup_conn = Connection::open(&backup_db_path)?;

        let backup = rusqlite::backup::Backup::new(&source_conn, &mut backup_conn)?;
        backup.run_to_completion(5, std::time::Duration::from_millis(250), None)?;

        Ok(BackupDescription {
            backup_arn,
            backup_name,
            table_name: table_name.to_string(),
            table_arn: table_metadata.table_arn,
            backup_status: "AVAILABLE".to_string(),
            backup_size_bytes: table_metadata.table_size_bytes,
            backup_creation_date_time: now,
            backup_expiry_date_time: None,
        })
    }

    /// Describe a backup by ARN
    pub fn describe_backup(&self, backup_arn: &str) -> Result<BackupDescription, StorageError> {
        // Extract backup ID from ARN
        let backup_id = self.extract_backup_id_from_arn(backup_arn)
            .ok_or_else(|| StorageError::InvalidKey("Invalid backup ARN".to_string()))?;

        // Initialize backup storage
        let conn = self.init_backup_storage()?;

        // Query backup metadata
        let mut stmt = conn.prepare(
            "SELECT backup_name, table_name, table_arn, backup_status, 
                    backup_size_bytes, backup_creation_date_time
             FROM backups WHERE backup_id = ?"
        )?;

        let result: Result<BackupDescription, rusqlite::Error> = stmt.query_row(
            [&backup_id],
            |row| {
                let creation_time_str: String = row.get(5)?;
                let creation_time = DateTime::parse_from_rfc3339(&creation_time_str)
                    .map_err(|_| rusqlite::Error::InvalidQuery)?
                    .with_timezone(&Utc);

                Ok(BackupDescription {
                    backup_arn: backup_arn.to_string(),
                    backup_name: row.get(0)?,
                    table_name: row.get(1)?,
                    table_arn: row.get(2)?,
                    backup_status: row.get(3)?,
                    backup_size_bytes: row.get(4)?,
                    backup_creation_date_time: creation_time,
                    backup_expiry_date_time: None,
                })
            },
        );

        match result {
            Ok(desc) => Ok(desc),
            Err(rusqlite::Error::QueryReturnedNoRows) => {
                Err(StorageError::TableNotFound(format!("Backup not found: {}", backup_arn)))
            }
            Err(e) => Err(e.into()),
        }
    }

    /// List all backups
    pub fn list_backups(
        &self,
        table_name: Option<&str>,
        _limit: Option<i32>,
    ) -> Result<Vec<BackupSummary>, StorageError> {
        let conn = self.init_backup_storage()?;

        let mut summaries = Vec::new();

        if let Some(table) = table_name {
            let mut stmt = conn.prepare(
                "SELECT backup_id, backup_name, table_name, backup_status, 
                        backup_creation_date_time, backup_size_bytes
                 FROM backups WHERE table_name = ? AND backup_status != 'DELETED'
                 ORDER BY backup_creation_date_time DESC"
            )?;

            let rows = stmt.query_map([table], |row| {
                let creation_time_str: String = row.get(4)?;
                let creation_time = DateTime::parse_from_rfc3339(&creation_time_str)
                    .map_err(|_| rusqlite::Error::InvalidQuery)?
                    .with_timezone(&Utc);

                let backup_id: String = row.get(0)?;
                let table_name: String = row.get(2)?;
                let backup_arn = format!(
                    "arn:aws:dynamodb:local:{}:table/{}/backup/{}:{}",
                    self.namespace, table_name, self.namespace, backup_id
                );

                Ok(BackupSummary {
                    backup_arn,
                    backup_name: row.get(1)?,
                    table_name,
                    backup_status: row.get(3)?,
                    backup_creation_date_time: creation_time,
                    backup_size_bytes: Some(row.get(5)?),
                })
            })?;

            for row in rows {
                summaries.push(row?);
            }
        } else {
            let mut stmt = conn.prepare(
                "SELECT backup_id, backup_name, table_name, backup_status, 
                        backup_creation_date_time, backup_size_bytes
                 FROM backups WHERE backup_status != 'DELETED'
                 ORDER BY backup_creation_date_time DESC"
            )?;

            let rows = stmt.query_map([], |row| {
                let creation_time_str: String = row.get(4)?;
                let creation_time = DateTime::parse_from_rfc3339(&creation_time_str)
                    .map_err(|_| rusqlite::Error::InvalidQuery)?
                    .with_timezone(&Utc);

                let backup_id: String = row.get(0)?;
                let table_name: String = row.get(2)?;
                let backup_arn = format!(
                    "arn:aws:dynamodb:local:{}:table/{}/backup/{}:{}",
                    self.namespace, table_name, self.namespace, backup_id
                );

                Ok(BackupSummary {
                    backup_arn,
                    backup_name: row.get(1)?,
                    table_name,
                    backup_status: row.get(3)?,
                    backup_creation_date_time: creation_time,
                    backup_size_bytes: Some(row.get(5)?),
                })
            })?;

            for row in rows {
                summaries.push(row?);
            }
        }

        Ok(summaries)
    }

    /// Delete a backup
    pub fn delete_backup(&self, backup_arn: &str) -> Result<BackupDescription, StorageError> {
        // Extract backup ID from ARN
        let backup_id = self.extract_backup_id_from_arn(backup_arn)
            .ok_or_else(|| StorageError::InvalidKey("Invalid backup ARN".to_string()))?;

        let conn = self.init_backup_storage()?;

        // Get backup info before deleting
        let description = self.describe_backup(backup_arn)?;

        // Update status to DELETED
        conn.execute(
            "UPDATE backups SET backup_status = 'DELETED' WHERE backup_id = ?",
            [&backup_id],
        )?;

        // Delete backup database file
        let backup_db_path = self.get_backup_db_path(&backup_id);
        if backup_db_path.exists() {
            fs::remove_file(&backup_db_path)?;
        }

        Ok(description)
    }

    /// Restore a table from a backup
    pub fn restore_table_from_backup(
        &self,
        target_table_name: &str,
        backup_arn: &str,
    ) -> Result<TableMetadata, StorageError> {
        // Check if target table already exists
        let target_db_path = self.get_db_path(target_table_name);
        if target_db_path.exists() {
            return Err(StorageError::TableAlreadyExists(target_table_name.to_string()));
        }

        // Extract backup ID from ARN
        let backup_id = self.extract_backup_id_from_arn(backup_arn)
            .ok_or_else(|| StorageError::InvalidKey("Invalid backup ARN".to_string()))?;

        // Get source backup metadata
        let conn = self.init_backup_storage()?;

        let source_metadata_json: Option<Vec<u8>> = conn.query_row(
            "SELECT source_table_metadata FROM backups WHERE backup_id = ? AND backup_status != 'DELETED'",
            [&backup_id],
            |row| row.get(0),
        ).ok();

        let source_metadata: Option<TableMetadata> = match source_metadata_json {
            Some(json) => serde_json::from_slice(&json).ok(),
            None => None,
        };

        // Check backup database exists
        let backup_db_path = self.get_backup_db_path(&backup_id);
        if !backup_db_path.exists() {
            return Err(StorageError::TableNotFound(format!("Backup not found: {}", backup_arn)));
        }

        // Copy backup database to new table location
        let target_dir = self.data_directory.join(&self.namespace);
        fs::create_dir_all(&target_dir)?;

        fs::copy(&backup_db_path, &target_db_path)?;

        // Update the metadata in the restored table
        let now = Utc::now();
        let table_id = Uuid::new_v4().to_string();
        let table_arn = format!("arn:aws:dynamodb:local:{}:table/{}", self.namespace, target_table_name);

        let new_metadata = TableMetadata {
            table_name: target_table_name.to_string(),
            table_arn: Some(table_arn),
            table_id: Some(table_id),
            table_status: "ACTIVE".to_string(),
            key_schema: source_metadata.as_ref().map(|m| m.key_schema.clone()).unwrap_or_default(),
            attribute_definitions: source_metadata.as_ref().map(|m| m.attribute_definitions.clone()).unwrap_or_default(),
            item_count: source_metadata.as_ref().map(|m| m.item_count).unwrap_or(0),
            table_size_bytes: source_metadata.as_ref().map(|m| m.table_size_bytes).unwrap_or(0),
            creation_date_time: now,
            billing_mode_summary: source_metadata.as_ref().and_then(|m| m.billing_mode_summary.clone()),
            provisioned_throughput: source_metadata.as_ref().and_then(|m| m.provisioned_throughput.clone()),
            global_secondary_indexes: source_metadata.as_ref().and_then(|m| m.global_secondary_indexes.clone()),
            local_secondary_indexes: source_metadata.as_ref().and_then(|m| m.local_secondary_indexes.clone()),
            tags: source_metadata.as_ref().and_then(|m| m.tags.clone()),
        };

        // Update metadata in the restored database
        let target_conn = Connection::open(&target_db_path)?;
        self.store_metadata(&target_conn, &new_metadata)?;

        // Add connection to cache
        self.connections.lock().unwrap().insert(target_table_name.to_string(), target_conn);

        Ok(new_metadata)
    }

    /// Extract backup ID from ARN
    fn extract_backup_id_from_arn(&self, arn: &str) -> Option<String> {
        // ARN format: arn:aws:dynamodb:local:{namespace}:table/{table_name}/backup/{namespace}:{backup_id}
        arn.split(':').last().map(|s| s.to_string())
    }

    // ============== Point-in-Time Recovery (PITR) Operations ==============

    /// Update continuous backups (enable/disable PITR)
    pub fn update_continuous_backups(
        &self,
        table_name: &str,
        enabled: bool,
    ) -> Result<ContinuousBackupsDescription, StorageError> {
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

        // Store PITR configuration in metadata table
        let pitr_config = PitrConfiguration {
            enabled,
            enabled_at: if enabled { Some(Utc::now()) } else { None },
        };

        let config_json = serde_json::to_vec(&pitr_config).map_err(|e| {
            rusqlite::Error::ToSqlConversionFailure(Box::new(e))
        })?;

        conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?1, ?2)",
            params!["pitr_config", config_json],
        )?;

        // Build response
        let pitr_description = if enabled {
            let now = Utc::now();
            Some(PointInTimeRecoveryDescription {
                point_in_time_recovery_status: PointInTimeRecoveryStatus::Enabled,
                earliest_restorable_date_time: Some(now),
                latest_restorable_date_time: Some(now),
            })
        } else {
            Some(PointInTimeRecoveryDescription {
                point_in_time_recovery_status: PointInTimeRecoveryStatus::Disabled,
                earliest_restorable_date_time: None,
                latest_restorable_date_time: None,
            })
        };

        let description = ContinuousBackupsDescription {
            continuous_backups_status: ContinuousBackupsStatus::Enabled,
            point_in_time_recovery_description: pitr_description,
        };

        drop(connections);

        Ok(description)
    }

    /// Describe continuous backups (get PITR status)
    pub fn describe_continuous_backups(
        &self,
        table_name: &str,
    ) -> Result<ContinuousBackupsDescription, StorageError> {
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

        // Load PITR configuration from metadata table
        let pitr_config: Option<Vec<u8>> = conn
            .query_row(
                "SELECT value FROM __table_metadata WHERE key = ?",
                ["pitr_config"],
                |row| row.get(0),
            )
            .ok();

        let pitr_description = if let Some(config_json) = pitr_config {
            let config: PitrConfiguration = serde_json::from_slice(&config_json)?;
            if config.enabled {
                let now = Utc::now();
                Some(PointInTimeRecoveryDescription {
                    point_in_time_recovery_status: PointInTimeRecoveryStatus::Enabled,
                    earliest_restorable_date_time: config.enabled_at,
                    latest_restorable_date_time: Some(now),
                })
            } else {
                Some(PointInTimeRecoveryDescription {
                    point_in_time_recovery_status: PointInTimeRecoveryStatus::Disabled,
                    earliest_restorable_date_time: None,
                    latest_restorable_date_time: None,
                })
            }
        } else {
            // No PITR configuration found - return disabled status
            Some(PointInTimeRecoveryDescription {
                point_in_time_recovery_status: PointInTimeRecoveryStatus::Disabled,
                earliest_restorable_date_time: None,
                latest_restorable_date_time: None,
            })
        };

        let description = ContinuousBackupsDescription {
            continuous_backups_status: ContinuousBackupsStatus::Enabled,
            point_in_time_recovery_description: pitr_description,
        };

        drop(connections);

        Ok(description)
    }

    /// Restore a table to a specific point in time
    pub fn restore_table_to_point_in_time(
        &self,
        req: &RestoreTableToPointInTimeRequest,
    ) -> Result<TableMetadata, StorageError> {
        let source_table_name = &req.source_table_name;
        let target_table_name = &req.target_table_name;

        // Check if source table exists
        let source_db_path = self.get_db_path(source_table_name);
        if !source_db_path.exists() {
            return Err(StorageError::TableNotFound(format!(
                "Source table not found: {}",
                source_table_name
            )));
        }

        // Check if target table already exists
        let target_db_path = self.get_db_path(target_table_name);
        if target_db_path.exists() {
            return Err(StorageError::TableAlreadyExists(target_table_name.clone()));
        }

        // Get source table metadata
        let source_metadata = self.describe_table(source_table_name)?;

        // Check if PITR is enabled on source table
        let pitr_config = self.describe_continuous_backups(source_table_name)?;
        let pitr_enabled = pitr_config
            .point_in_time_recovery_description
            .map(|d| d.point_in_time_recovery_status == PointInTimeRecoveryStatus::Enabled)
            .unwrap_or(false);

        if !pitr_enabled {
            return Err(StorageError::InvalidKey(format!(
                "Point in time recovery is not enabled for table: {}",
                source_table_name
            )));
        }

        // Copy source database to target location (simplified PITR implementation)
        let target_dir = self.data_directory.join(&self.namespace);
        fs::create_dir_all(&target_dir)?;
        fs::copy(&source_db_path, &target_db_path)?;

        // Create new metadata for restored table
        let now = Utc::now();
        let table_id = Uuid::new_v4().to_string();
        let table_arn = format!(
            "arn:aws:dynamodb:local:{}:table/{}",
            self.namespace, target_table_name
        );

        let new_metadata = TableMetadata {
            table_name: target_table_name.clone(),
            table_arn: Some(table_arn),
            table_id: Some(table_id),
            table_status: "ACTIVE".to_string(),
            key_schema: source_metadata.key_schema.clone(),
            attribute_definitions: source_metadata.attribute_definitions.clone(),
            item_count: source_metadata.item_count,
            table_size_bytes: source_metadata.table_size_bytes,
            creation_date_time: now,
            billing_mode_summary: source_metadata.billing_mode_summary.clone(),
            provisioned_throughput: source_metadata.provisioned_throughput.clone(),
            global_secondary_indexes: source_metadata.global_secondary_indexes.clone(),
            local_secondary_indexes: source_metadata.local_secondary_indexes.clone(),
            tags: source_metadata.tags.clone(),
        };

        // Update metadata in the restored database
        let target_conn = Connection::open(&target_db_path)?;
        self.store_metadata(&target_conn, &new_metadata)?;

        // Clear PITR config from restored table (it needs to be explicitly enabled)
        let pitr_config = PitrConfiguration {
            enabled: false,
            enabled_at: None,
        };
        let config_json = serde_json::to_vec(&pitr_config).map_err(|e| {
            rusqlite::Error::ToSqlConversionFailure(Box::new(e))
        })?;
        target_conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?1, ?2)",
            params!["pitr_config", config_json],
        )?;

        // Add connection to cache
        self.connections
            .lock()
            .unwrap()
            .insert(target_table_name.clone(), target_conn);

        Ok(new_metadata)
    }

    // ============== Import/Export Operations ==============

    /// Get the path for import/export storage directory
    fn get_import_export_dir(&self) -> PathBuf {
        self.data_directory.join(&self.namespace).join("__import_export")
    }

    /// Initialize the import/export metadata storage
    fn init_import_export_storage(&self) -> Result<Connection, StorageError> {
        let import_export_dir = self.get_import_export_dir();
        fs::create_dir_all(&import_export_dir)?;

        let metadata_db_path = import_export_dir.join("metadata.db");
        let conn = Connection::open(&metadata_db_path)?;

        // Create export metadata table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS exports (
                export_id TEXT PRIMARY KEY,
                export_arn TEXT NOT NULL UNIQUE,
                export_status TEXT NOT NULL,
                table_arn TEXT,
                table_name TEXT NOT NULL,
                s3_bucket TEXT NOT NULL,
                s3_prefix TEXT,
                export_format TEXT NOT NULL,
                item_count INTEGER NOT NULL DEFAULT 0,
                start_time TEXT NOT NULL,
                end_time TEXT,
                failure_code TEXT,
                failure_message TEXT
            )",
            [],
        )?;

        // Create import metadata table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS imports (
                import_id TEXT PRIMARY KEY,
                import_arn TEXT NOT NULL UNIQUE,
                import_status TEXT NOT NULL,
                table_arn TEXT,
                table_name TEXT NOT NULL,
                s3_bucket TEXT NOT NULL,
                s3_key_prefix TEXT,
                input_format TEXT NOT NULL,
                processed_item_count INTEGER NOT NULL DEFAULT 0,
                imported_item_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                start_time TEXT NOT NULL,
                end_time TEXT,
                failure_code TEXT,
                failure_message TEXT
            )",
            [],
        )?;

        Ok(conn)
    }

    /// Export table to point in time
    pub fn export_table_to_point_in_time(
        &self,
        table_arn: &str,
        s3_bucket: &str,
        s3_prefix: Option<String>,
        export_format: Option<String>,
    ) -> Result<ExportDescription, StorageError> {
        let table_name = self.extract_table_name_from_arn(table_arn)
            .ok_or_else(|| StorageError::InvalidKey("Invalid table ARN".to_string()))?;

        let table_metadata = self.describe_table(&table_name)?;
        let conn = self.init_import_export_storage()?;

        let export_id = Uuid::new_v4().to_string();
        let export_arn = format!(
            "arn:aws:dynamodb:local:{}:table/{}/export/{}:{}",
            self.namespace, table_name, self.namespace, export_id
        );

        let export_format = export_format.unwrap_or_else(|| "DYNAMODB_JSON".to_string());
        let s3_prefix = s3_prefix.or_else(|| Some(format!("exports/{}/", s3_bucket)));
        let now = Utc::now();

        // Use s3_bucket as directory name for easier import lookup
        let export_dir = self.get_import_export_dir()
            .join("exports")
            .join(s3_bucket);
        fs::create_dir_all(&export_dir)?;

        let item_count = self.export_table_items(&table_name, &export_dir, &export_format)?;

        conn.execute(
            "INSERT INTO exports (
                export_id, export_arn, export_status, table_arn, table_name,
                s3_bucket, s3_prefix, export_format, item_count, start_time, end_time
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                export_id, &export_arn, "COMPLETED", table_metadata.table_arn, &table_name,
                s3_bucket, &s3_prefix, &export_format, item_count,
                now.to_rfc3339(), now.to_rfc3339()
            ],
        )?;

        Ok(ExportDescription {
            export_arn,
            export_status: "COMPLETED".to_string(),
            table_arn: table_metadata.table_arn,
            s3_bucket: s3_bucket.to_string(),
            s3_prefix,
            export_format,
            item_count: Some(item_count),
            export_time: Some(now),
            start_time: Some(now),
            end_time: Some(now),
            failure_code: None,
            failure_message: None,
        })
    }

    /// Export table items to files
    fn export_table_items(
        &self,
        table_name: &str,
        export_dir: &PathBuf,
        _export_format: &str,
    ) -> Result<i64, StorageError> {
        let conn = self.get_connection(table_name)?;
        let mut stmt = conn.prepare("SELECT data FROM items")?;
        
        let mut item_count: i64 = 0;
        let mut rows = stmt.query([])?;

        while let Some(row) = rows.next()? {
            let data: Vec<u8> = row.get(0)?;
            let item: Item = serde_json::from_slice(&data)?;
            
            let filename = format!("item_{}.json", item_count);
            let file_path = export_dir.join(&filename);
            let file = std::fs::File::create(&file_path)?;
            serde_json::to_writer(file, &item)?;
            
            item_count += 1;
        }

        let metadata_path = export_dir.join("export_metadata.json");
        let metadata = serde_json::json!({
            "table_name": table_name,
            "item_count": item_count,
            "export_time": Utc::now().to_rfc3339(),
            "format": "DYNAMODB_JSON"
        });
        let file = std::fs::File::create(&metadata_path)?;
        serde_json::to_writer(file, &metadata)?;

        Ok(item_count)
    }

    /// Describe an export by ARN
    pub fn describe_export(&self, export_arn: &str) -> Result<ExportDescription, StorageError> {
        let export_id = self.extract_export_id_from_arn(export_arn)
            .ok_or_else(|| StorageError::InvalidKey("Invalid export ARN".to_string()))?;

        let conn = self.init_import_export_storage()?;

        let mut stmt = conn.prepare(
            "SELECT export_status, table_arn, s3_bucket, s3_prefix, export_format,
                    item_count, start_time, end_time, failure_code, failure_message
             FROM exports WHERE export_id = ?"
        )?;

        let result: Result<ExportDescription, rusqlite::Error> = stmt.query_row(
            [&export_id],
            |row| {
                let start_time_str: String = row.get(6)?;
                let end_time_str: Option<String> = row.get(7)?;

                Ok(ExportDescription {
                    export_arn: export_arn.to_string(),
                    export_status: row.get(0)?,
                    table_arn: row.get(1)?,
                    s3_bucket: row.get(2)?,
                    s3_prefix: row.get(3)?,
                    export_format: row.get(4)?,
                    item_count: row.get(5)?,
                    export_time: DateTime::parse_from_rfc3339(&start_time_str).ok().map(|d| d.with_timezone(&Utc)),
                    start_time: DateTime::parse_from_rfc3339(&start_time_str).ok().map(|d| d.with_timezone(&Utc)),
                    end_time: end_time_str.and_then(|s| DateTime::parse_from_rfc3339(&s).ok()).map(|d| d.with_timezone(&Utc)),
                    failure_code: row.get(8)?,
                    failure_message: row.get(9)?,
                })
            },
        );

        match result {
            Ok(desc) => Ok(desc),
            Err(rusqlite::Error::QueryReturnedNoRows) => {
                Err(StorageError::TableNotFound(format!("Export not found: {}", export_arn)))
            }
            Err(e) => Err(e.into()),
        }
    }

    /// List all exports
    pub fn list_exports(&self, table_arn: Option<&str>) -> Result<Vec<ExportSummary>, StorageError> {
        let conn = self.init_import_export_storage()?;
        let mut summaries = Vec::new();

        if let Some(table_arn) = table_arn {
            let mut stmt = conn.prepare(
                "SELECT export_arn, export_status, table_arn FROM exports WHERE table_arn = ? ORDER BY start_time DESC"
            )?;

            let rows = stmt.query_map([table_arn], |row| {
                Ok(ExportSummary {
                    export_arn: row.get(0)?,
                    export_status: row.get(1)?,
                    table_arn: row.get(2)?,
                })
            })?;

            for row in rows {
                summaries.push(row?);
            }
        } else {
            let mut stmt = conn.prepare(
                "SELECT export_arn, export_status, table_arn FROM exports ORDER BY start_time DESC"
            )?;

            let rows = stmt.query_map([], |row| {
                Ok(ExportSummary {
                    export_arn: row.get(0)?,
                    export_status: row.get(1)?,
                    table_arn: row.get(2)?,
                })
            })?;

            for row in rows {
                summaries.push(row?);
            }
        }

        Ok(summaries)
    }

    /// Import table from export files
    pub fn import_table(
        &self,
        table_name: &str,
        s3_bucket_source: &S3BucketSource,
        input_format: Option<String>,
        key_schema: Option<Vec<KeySchemaElement>>,
        attribute_definitions: Option<Vec<AttributeDefinition>>,
    ) -> Result<ImportDescription, StorageError> {
        let target_db_path = self.get_db_path(table_name);
        let table_exists = target_db_path.exists();
        let conn = self.init_import_export_storage()?;

        let import_id = Uuid::new_v4().to_string();
        let import_arn = format!(
            "arn:aws:dynamodb:local:{}:import/{}:{}",
            self.namespace, self.namespace, import_id
        );

        let input_format = input_format.unwrap_or_else(|| "DYNAMODB_JSON".to_string());
        let now = Utc::now();

        let export_dir = self.get_import_export_dir()
            .join("exports")
            .join(&s3_bucket_source.s3_bucket);

        if !export_dir.exists() {
            conn.execute(
                "INSERT INTO imports (import_id, import_arn, import_status, table_arn, table_name,
                    s3_bucket, s3_key_prefix, input_format, processed_item_count, imported_item_count,
                    error_count, start_time, end_time, failure_code, failure_message)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)",
                params![
                    import_id, &import_arn, "FAILED", None::<String>, table_name,
                    &s3_bucket_source.s3_bucket, s3_bucket_source.s3_key_prefix.as_ref(),
                    &input_format, 0, 0, 1, now.to_rfc3339(), now.to_rfc3339(),
                    "ExportNotFound", "Source export not found"
                ],
            )?;
            return Err(StorageError::TableNotFound(format!("Source export not found: {}", s3_bucket_source.s3_bucket)));
        }

        if !table_exists {
            let key_schema = key_schema.unwrap_or_else(|| vec![KeySchemaElement::hash("pk")]);
            let attribute_definitions = attribute_definitions.unwrap_or_else(|| vec![AttributeDefinition::s("pk")]);

            let create_req = DynamoDBRequest {
                table_name: Some(table_name.to_string()),
                key_schema: Some(key_schema),
                attribute_definitions: Some(attribute_definitions),
                billing_mode: Some("PAY_PER_REQUEST".to_string()),
                ..Default::default()
            };
            self.create_table(&create_req)?;
        }

        let (processed_count, imported_count, error_count) = 
            self.import_items_from_files(table_name, &export_dir, &input_format)?;

        let table_arn = format!("arn:aws:dynamodb:local:{}:table/{}", self.namespace, table_name);

        conn.execute(
            "INSERT INTO imports (import_id, import_arn, import_status, table_arn, table_name,
                s3_bucket, s3_key_prefix, input_format, processed_item_count, imported_item_count,
                error_count, start_time, end_time)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
            params![
                import_id, &import_arn, "COMPLETED", &table_arn, table_name,
                &s3_bucket_source.s3_bucket, s3_bucket_source.s3_key_prefix.as_ref(),
                &input_format, processed_count, imported_count, error_count,
                now.to_rfc3339(), Utc::now().to_rfc3339()
            ],
        )?;

        Ok(ImportDescription {
            import_arn,
            import_status: "COMPLETED".to_string(),
            table_arn: Some(table_arn),
            s3_bucket_source: s3_bucket_source.clone(),
            input_format,
            processed_item_count: Some(processed_count),
            imported_item_count: Some(imported_count),
            error_count: Some(error_count),
            start_time: Some(now),
            end_time: Some(Utc::now()),
            failure_code: None,
            failure_message: None,
        })
    }

    /// Import items from export files
    fn import_items_from_files(
        &self,
        table_name: &str,
        export_dir: &PathBuf,
        _input_format: &str,
    ) -> Result<(i64, i64, i64), StorageError> {
        let mut processed_count: i64 = 0;
        let mut imported_count: i64 = 0;
        let mut error_count: i64 = 0;

        for entry in fs::read_dir(export_dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.is_file() && path.extension() == Some(std::ffi::OsStr::new("json")) {
                let filename = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                if filename == "export_metadata.json" {
                    continue;
                }

                processed_count += 1;
                let content = fs::read_to_string(&path)?;
                match serde_json::from_str::<Item>(&content) {
                    Ok(item) => {
                        if self.insert_imported_item(table_name, &item).is_ok() {
                            imported_count += 1;
                        } else {
                            error_count += 1;
                        }
                    }
                    Err(_) => error_count += 1,
                }
            }
        }

        Ok((processed_count, imported_count, error_count))
    }

    /// Insert an imported item into a table
    fn insert_imported_item(&self, table_name: &str, item: &Item) -> Result<(), StorageError> {
        let metadata = self.describe_table(table_name)?;
        let (pk, sk) = self.extract_keys_from_item(item, &metadata.key_schema, &metadata.attribute_definitions)?;

        let conn = self.get_connection(table_name)?;
        let now = Utc::now().timestamp();
        let data = serde_json::to_vec(item)?;

        conn.execute(
            "INSERT OR REPLACE INTO items (pk, sk, data, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![pk, sk, data, now, now],
        )?;

        Ok(())
    }

    /// Extract keys from an item based on key schema
    fn extract_keys_from_item(
        &self,
        item: &Item,
        key_schema: &[KeySchemaElement],
        attr_defs: &[AttributeDefinition],
    ) -> Result<(String, Option<String>), StorageError> {
        let mut pk_name = None;
        let mut pk_type = None;
        let mut sk_name = None;
        let mut sk_type = None;

        for ks in key_schema {
            if ks.key_type == "HASH" {
                pk_name = Some(ks.attribute_name.clone());
                for ad in attr_defs {
                    if ad.attribute_name == ks.attribute_name {
                        pk_type = Some(ad.attribute_type.clone());
                        break;
                    }
                }
            } else if ks.key_type == "RANGE" {
                sk_name = Some(ks.attribute_name.clone());
                for ad in attr_defs {
                    if ad.attribute_name == ks.attribute_name {
                        sk_type = Some(ad.attribute_type.clone());
                        break;
                    }
                }
            }
        }

        let pk_name = pk_name.ok_or_else(|| StorageError::InvalidKey("No HASH key in schema".to_string()))?;
        let pk_type = pk_type.ok_or_else(|| StorageError::InvalidKey(format!("No type for partition key {}", pk_name)))?;

        let pk_attr = item.get(&pk_name)
            .ok_or_else(|| StorageError::InvalidKey(format!("Missing partition key: {}", pk_name)))?;
        let pk_value = self.attr_value_to_string(pk_attr, &pk_type)?;

        let sk_value = if let (Some(sk_name), Some(sk_type)) = (sk_name, sk_type) {
            let sk_attr = item.get(&sk_name)
                .ok_or_else(|| StorageError::InvalidKey(format!("Missing sort key: {}", sk_name)))?;
            Some(self.attr_value_to_string(sk_attr, &sk_type)?)
        } else {
            None
        };

        Ok((pk_value, sk_value))
    }

    /// Convert attribute value to string
    fn attr_value_to_string(&self, attr: &AttributeValue, attr_type: &str) -> Result<String, StorageError> {
        match (attr, attr_type) {
            (AttributeValue::S { s }, "S") => Ok(s.clone()),
            (AttributeValue::N { n }, "N") => Ok(n.clone()),
            (AttributeValue::B { b }, "B") => Ok(b.clone()),
            _ => Err(StorageError::InvalidKey(format!("Attribute {:?} doesn't match type {}", attr, attr_type))),
        }
    }

    /// Describe an import by ARN
    pub fn describe_import(&self, import_arn: &str) -> Result<ImportDescription, StorageError> {
        let import_id = self.extract_import_id_from_arn(import_arn)
            .ok_or_else(|| StorageError::InvalidKey("Invalid import ARN".to_string()))?;

        let conn = self.init_import_export_storage()?;

        let mut stmt = conn.prepare(
            "SELECT import_status, table_arn, table_name, s3_bucket, s3_key_prefix, input_format,
                    processed_item_count, imported_item_count, error_count, start_time, end_time,
                    failure_code, failure_message FROM imports WHERE import_id = ?"
        )?;

        let result: Result<ImportDescription, rusqlite::Error> = stmt.query_row(
            [&import_id],
            |row| {
                let start_time_str: String = row.get(9)?;
                let end_time_str: Option<String> = row.get(10)?;

                Ok(ImportDescription {
                    import_arn: import_arn.to_string(),
                    import_status: row.get(0)?,
                    table_arn: row.get(1)?,
                    s3_bucket_source: S3BucketSource {
                        s3_bucket: row.get(3)?,
                        s3_key_prefix: row.get(4)?,
                    },
                    input_format: row.get(5)?,
                    processed_item_count: row.get(6)?,
                    imported_item_count: row.get(7)?,
                    error_count: row.get(8)?,
                    start_time: DateTime::parse_from_rfc3339(&start_time_str).ok().map(|d| d.with_timezone(&Utc)),
                    end_time: end_time_str.and_then(|s| DateTime::parse_from_rfc3339(&s).ok()).map(|d| d.with_timezone(&Utc)),
                    failure_code: row.get(11)?,
                    failure_message: row.get(12)?,
                })
            },
        );

        match result {
            Ok(desc) => Ok(desc),
            Err(rusqlite::Error::QueryReturnedNoRows) => {
                Err(StorageError::TableNotFound(format!("Import not found: {}", import_arn)))
            }
            Err(e) => Err(e.into()),
        }
    }

    /// List all imports
    pub fn list_imports(&self, table_arn: Option<&str>) -> Result<Vec<ImportSummary>, StorageError> {
        let conn = self.init_import_export_storage()?;
        let mut summaries = Vec::new();

        if let Some(table_arn) = table_arn {
            let mut stmt = conn.prepare(
                "SELECT import_arn, import_status, table_arn FROM imports WHERE table_arn = ? ORDER BY start_time DESC"
            )?;

            let rows = stmt.query_map([table_arn], |row| {
                Ok(ImportSummary {
                    import_arn: row.get(0)?,
                    import_status: row.get(1)?,
                    table_arn: row.get(2)?,
                })
            })?;

            for row in rows {
                summaries.push(row?);
            }
        } else {
            let mut stmt = conn.prepare(
                "SELECT import_arn, import_status, table_arn FROM imports ORDER BY start_time DESC"
            )?;

            let rows = stmt.query_map([], |row| {
                Ok(ImportSummary {
                    import_arn: row.get(0)?,
                    import_status: row.get(1)?,
                    table_arn: row.get(2)?,
                })
            })?;

            for row in rows {
                summaries.push(row?);
            }
        }

        Ok(summaries)
    }

    fn extract_export_id_from_arn(&self, arn: &str) -> Option<String> {
        arn.split(':').last().map(|s| s.to_string())
    }

    fn extract_import_id_from_arn(&self, arn: &str) -> Option<String> {
        arn.split(':').last().map(|s| s.to_string())
    }

    fn extract_table_name_from_arn(&self, arn: &str) -> Option<String> {
        arn.split('/').last().map(|s| s.to_string())
    }

    // ============== Tagging Operations ==============

    /// Add tags to a table
    pub fn tag_resource(&self, table_name: &str, tags: Vec<Tag>) -> Result<(), StorageError> {
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

        // Insert or replace tags
        for tag in tags {
            let now = Utc::now().timestamp();
            conn.execute(
                "INSERT OR REPLACE INTO __tags (key, value, created_at) VALUES (?1, ?2, ?3)",
                params![tag.key, tag.value, now],
            )?;
        }

        drop(connections);

        Ok(())
    }

    /// Remove tags from a table
    pub fn untag_resource(&self, table_name: &str, tag_keys: Vec<String>) -> Result<(), StorageError> {
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

        // Delete tags
        for key in tag_keys {
            conn.execute(
                "DELETE FROM __tags WHERE key = ?1",
                params![key],
            )?;
        }

        drop(connections);

        Ok(())
    }

    /// List all tags on a table
    pub fn list_tags_of_resource(&self, table_name: &str) -> Result<Vec<Tag>, StorageError> {
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

        // Query all tags - collect into a Vec first to release the borrow on conn
        let mut stmt = conn.prepare("SELECT key, value FROM __tags")?;

        let tags_result: Result<Vec<(String, String)>, rusqlite::Error> = stmt
            .query_map([], |row| {
                Ok((row.get(0)?, row.get(1)?))
            })?
            .collect();

        // Explicitly drop statement before dropping connections
        drop(stmt);

        let tags: Vec<Tag> = tags_result?
            .into_iter()
            .map(|(key, value)| Tag { key, value })
            .collect();

        drop(connections);

        Ok(tags)
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

    #[test]
    fn test_create_backup() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        let backup = manager.create_backup("TestTable", Some("MyBackup".to_string())).unwrap();
        
        assert_eq!(backup.table_name, "TestTable");
        assert_eq!(backup.backup_name, "MyBackup");
        assert_eq!(backup.backup_status, "AVAILABLE");
        assert!(backup.backup_arn.contains("backup"));
    }

    #[test]
    fn test_create_backup_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let result = manager.create_backup("NonExistent", Some("MyBackup".to_string()));
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_describe_backup() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        let backup = manager.create_backup("TestTable", Some("MyBackup".to_string())).unwrap();
        
        let described = manager.describe_backup(&backup.backup_arn).unwrap();
        
        assert_eq!(described.backup_name, backup.backup_name);
        assert_eq!(described.table_name, backup.table_name);
        assert_eq!(described.backup_status, "AVAILABLE");
    }

    #[test]
    fn test_describe_backup_not_found() {
        let (manager, _temp) = setup_test_manager();
        
        let result = manager.describe_backup("arn:aws:dynamodb:local:default:table/Test/backup/default:nonexistent");
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_list_backups() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        manager.create_backup("TestTable", Some("Backup1".to_string())).unwrap();
        manager.create_backup("TestTable", Some("Backup2".to_string())).unwrap();
        
        let backups = manager.list_backups(None, None).unwrap();
        
        assert_eq!(backups.len(), 2);
    }

    #[test]
    fn test_list_backups_filtered_by_table() {
        let (manager, _temp) = setup_test_manager();
        
        let req1 = create_test_request("Table1");
        let req2 = create_test_request("Table2");
        
        manager.create_table(&req1).unwrap();
        manager.create_table(&req2).unwrap();
        
        manager.create_backup("Table1", Some("Backup1".to_string())).unwrap();
        manager.create_backup("Table2", Some("Backup2".to_string())).unwrap();
        
        let backups = manager.list_backups(Some("Table1"), None).unwrap();
        
        assert_eq!(backups.len(), 1);
        assert_eq!(backups[0].table_name, "Table1");
    }

    #[test]
    fn test_delete_backup() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        let backup = manager.create_backup("TestTable", Some("MyBackup".to_string())).unwrap();
        
        let deleted = manager.delete_backup(&backup.backup_arn).unwrap();
        
        assert_eq!(deleted.backup_arn, backup.backup_arn);
        
        // Backup should no longer be in list
        let backups = manager.list_backups(None, None).unwrap();
        assert!(backups.is_empty());
    }

    #[test]
    fn test_restore_table_from_backup() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("SourceTable");
        
        manager.create_table(&req).unwrap();
        let backup = manager.create_backup("SourceTable", Some("MyBackup".to_string())).unwrap();
        
        let restored = manager.restore_table_from_backup("RestoredTable", &backup.backup_arn).unwrap();
        
        assert_eq!(restored.table_name, "RestoredTable");
        assert_eq!(restored.table_status, "ACTIVE");
        
        // Verify the restored table is listed
        let tables = manager.list_tables().unwrap();
        assert!(tables.contains(&"RestoredTable".to_string()));
    }

    #[test]
    fn test_restore_table_already_exists() {
        let (manager, _temp) = setup_test_manager();
        let req1 = create_test_request("SourceTable");
        let req2 = create_test_request("ExistingTable");
        
        manager.create_table(&req1).unwrap();
        manager.create_table(&req2).unwrap();
        
        let backup = manager.create_backup("SourceTable", Some("MyBackup".to_string())).unwrap();
        
        let result = manager.restore_table_from_backup("ExistingTable", &backup.backup_arn);
        assert!(matches!(result, Err(StorageError::TableAlreadyExists(_))));
    }

    // ============== PITR Tests ==============

    #[test]
    fn test_update_continuous_backups_enable_pitr() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Enable PITR
        let description = manager.update_continuous_backups("TestTable", true).unwrap();
        
        assert_eq!(description.continuous_backups_status.to_string(), "ENABLED");
        let pitr = description.point_in_time_recovery_description.unwrap();
        assert_eq!(pitr.point_in_time_recovery_status.to_string(), "ENABLED");
        assert!(pitr.earliest_restorable_date_time.is_some());
        assert!(pitr.latest_restorable_date_time.is_some());
    }

    #[test]
    fn test_update_continuous_backups_disable_pitr() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // First enable PITR
        manager.update_continuous_backups("TestTable", true).unwrap();
        
        // Then disable it
        let description = manager.update_continuous_backups("TestTable", false).unwrap();
        
        assert_eq!(description.continuous_backups_status.to_string(), "ENABLED");
        let pitr = description.point_in_time_recovery_description.unwrap();
        assert_eq!(pitr.point_in_time_recovery_status.to_string(), "DISABLED");
        assert!(pitr.earliest_restorable_date_time.is_none());
        assert!(pitr.latest_restorable_date_time.is_none());
    }

    #[test]
    fn test_describe_continuous_backups_default_disabled() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Before enabling PITR - should return DISABLED
        let description = manager.describe_continuous_backups("TestTable").unwrap();
        
        assert_eq!(description.continuous_backups_status.to_string(), "ENABLED");
        let pitr = description.point_in_time_recovery_description.unwrap();
        assert_eq!(pitr.point_in_time_recovery_status.to_string(), "DISABLED");
    }

    #[test]
    fn test_describe_continuous_backups_enabled() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Enable PITR
        manager.update_continuous_backups("TestTable", true).unwrap();
        
        // Describe should show enabled
        let description = manager.describe_continuous_backups("TestTable").unwrap();
        
        assert_eq!(description.continuous_backups_status.to_string(), "ENABLED");
        let pitr = description.point_in_time_recovery_description.unwrap();
        assert_eq!(pitr.point_in_time_recovery_status.to_string(), "ENABLED");
    }

    #[test]
    fn test_update_continuous_backups_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let result = manager.update_continuous_backups("NonExistent", true);
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_describe_continuous_backups_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let result = manager.describe_continuous_backups("NonExistent");
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_restore_table_to_point_in_time() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("SourceTable");
        
        manager.create_table(&req).unwrap();
        
        // Enable PITR on source table
        manager.update_continuous_backups("SourceTable", true).unwrap();
        
        // Restore to point in time
        let restore_req = RestoreTableToPointInTimeRequest {
            source_table_name: "SourceTable".to_string(),
            target_table_name: "RestoredTable".to_string(),
            use_latest_restorable_time: Some(true),
            restore_date_time: None,
        };
        
        let restored = manager.restore_table_to_point_in_time(&restore_req).unwrap();
        
        assert_eq!(restored.table_name, "RestoredTable");
        assert_eq!(restored.table_status, "ACTIVE");
        
        // Verify the restored table is listed
        let tables = manager.list_tables().unwrap();
        assert!(tables.contains(&"RestoredTable".to_string()));
    }

    #[test]
    fn test_restore_table_to_point_in_time_source_not_found() {
        let (manager, _temp) = setup_test_manager();
        
        let restore_req = RestoreTableToPointInTimeRequest {
            source_table_name: "NonExistent".to_string(),
            target_table_name: "RestoredTable".to_string(),
            use_latest_restorable_time: Some(true),
            restore_date_time: None,
        };
        
        let result = manager.restore_table_to_point_in_time(&restore_req);
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_restore_table_to_point_in_time_target_exists() {
        let (manager, _temp) = setup_test_manager();
        let req1 = create_test_request("SourceTable");
        let req2 = create_test_request("ExistingTable");
        
        manager.create_table(&req1).unwrap();
        manager.create_table(&req2).unwrap();
        
        // Enable PITR on source table
        manager.update_continuous_backups("SourceTable", true).unwrap();
        
        let restore_req = RestoreTableToPointInTimeRequest {
            source_table_name: "SourceTable".to_string(),
            target_table_name: "ExistingTable".to_string(),
            use_latest_restorable_time: Some(true),
            restore_date_time: None,
        };
        
        let result = manager.restore_table_to_point_in_time(&restore_req);
        assert!(matches!(result, Err(StorageError::TableAlreadyExists(_))));
    }

    #[test]
    fn test_restore_table_to_point_in_time_pitr_not_enabled() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("SourceTable");
        
        manager.create_table(&req).unwrap();
        
        // Don't enable PITR - try to restore directly
        let restore_req = RestoreTableToPointInTimeRequest {
            source_table_name: "SourceTable".to_string(),
            target_table_name: "RestoredTable".to_string(),
            use_latest_restorable_time: Some(true),
            restore_date_time: None,
        };
        
        let result = manager.restore_table_to_point_in_time(&restore_req);
        assert!(matches!(result, Err(StorageError::InvalidKey(_))));
    }

    // ============== Import/Export Tests ==============

    #[test]
    fn test_export_table_to_point_in_time() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        let export = manager.export_table_to_point_in_time(
            "arn:aws:dynamodb:local:default:table/TestTable",
            "test-bucket",
            Some("test-prefix/".to_string()),
            Some("DYNAMODB_JSON".to_string()),
        ).unwrap();
        
        assert_eq!(export.export_status, "COMPLETED");
        assert_eq!(export.s3_bucket, "test-bucket");
        assert_eq!(export.export_format, "DYNAMODB_JSON");
        assert!(export.export_arn.contains("export"));
    }

    #[test]
    fn test_describe_export() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        let export = manager.export_table_to_point_in_time(
            "arn:aws:dynamodb:local:default:table/TestTable",
            "test-bucket",
            None,
            None,
        ).unwrap();
        
        let described = manager.describe_export(&export.export_arn).unwrap();
        assert_eq!(described.export_arn, export.export_arn);
        assert_eq!(described.export_status, "COMPLETED");
    }

    #[test]
    fn test_list_exports() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        manager.export_table_to_point_in_time(
            "arn:aws:dynamodb:local:default:table/TestTable",
            "test-bucket",
            None,
            None,
        ).unwrap();
        
        let exports = manager.list_exports(None).unwrap();
        assert_eq!(exports.len(), 1);
    }

    #[test]
    fn test_import_table() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("SourceTable");
        
        // Create source table and export it first
        manager.create_table(&req).unwrap();
        
        let export = manager.export_table_to_point_in_time(
            "arn:aws:dynamodb:local:default:table/SourceTable",
            "test-bucket",
            None,
            None,
        ).unwrap();
        
        // Now import to a new table
        let import = manager.import_table(
            "ImportedTable",
            &S3BucketSource {
                s3_bucket: export.s3_bucket.clone(),
                s3_key_prefix: export.s3_prefix.clone(),
            },
            Some("DYNAMODB_JSON".to_string()),
            None,
            None,
        ).unwrap();
        
        assert_eq!(import.import_status, "COMPLETED");
        assert_eq!(import.table_arn, Some("arn:aws:dynamodb:local:test:table/ImportedTable".to_string()));
        
        // Verify the imported table exists
        let tables = manager.list_tables().unwrap();
        assert!(tables.contains(&"ImportedTable".to_string()));
    }

    #[test]
    fn test_describe_import() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("SourceTable");
        
        manager.create_table(&req).unwrap();
        
        let export = manager.export_table_to_point_in_time(
            "arn:aws:dynamodb:local:default:table/SourceTable",
            "test-bucket",
            None,
            None,
        ).unwrap();
        
        let import = manager.import_table(
            "ImportedTable",
            &S3BucketSource {
                s3_bucket: export.s3_bucket,
                s3_key_prefix: export.s3_prefix,
            },
            Some("DYNAMODB_JSON".to_string()),
            None,
            None,
        ).unwrap();
        
        let described = manager.describe_import(&import.import_arn).unwrap();
        assert_eq!(described.import_arn, import.import_arn);
        assert_eq!(described.import_status, "COMPLETED");
    }

    #[test]
    fn test_list_imports() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("SourceTable");
        
        manager.create_table(&req).unwrap();
        
        let export = manager.export_table_to_point_in_time(
            "arn:aws:dynamodb:local:default:table/SourceTable",
            "test-bucket",
            None,
            None,
        ).unwrap();
        
        manager.import_table(
            "ImportedTable",
            &S3BucketSource {
                s3_bucket: export.s3_bucket,
                s3_key_prefix: export.s3_prefix,
            },
            Some("DYNAMODB_JSON".to_string()),
            None,
            None,
        ).unwrap();
        
        let imports = manager.list_imports(None).unwrap();
        assert_eq!(imports.len(), 1);
    }

    // ============== Tagging Tests ==============

    #[test]
    fn test_tag_resource() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Add tags
        let tags = vec![
            Tag { key: "Environment".to_string(), value: "Test".to_string() },
            Tag { key: "Owner".to_string(), value: "Team".to_string() },
        ];
        
        manager.tag_resource("TestTable", tags).unwrap();
        
        // List tags to verify
        let tags = manager.list_tags_of_resource("TestTable").unwrap();
        assert_eq!(tags.len(), 2);
        assert!(tags.iter().any(|t| t.key == "Environment" && t.value == "Test"));
        assert!(tags.iter().any(|t| t.key == "Owner" && t.value == "Team"));
    }

    #[test]
    fn test_tag_resource_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let tags = vec![
            Tag { key: "Environment".to_string(), value: "Test".to_string() },
        ];
        
        let result = manager.tag_resource("NonExistent", tags);
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_untag_resource() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Add tags
        let tags = vec![
            Tag { key: "Environment".to_string(), value: "Test".to_string() },
            Tag { key: "Owner".to_string(), value: "Team".to_string() },
        ];
        manager.tag_resource("TestTable", tags).unwrap();
        
        // Remove one tag
        manager.untag_resource("TestTable", vec!["Environment".to_string()]).unwrap();
        
        // List tags to verify
        let tags = manager.list_tags_of_resource("TestTable").unwrap();
        assert_eq!(tags.len(), 1);
        assert_eq!(tags[0].key, "Owner");
        assert_eq!(tags[0].value, "Team");
    }

    #[test]
    fn test_untag_resource_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let result = manager.untag_resource("NonExistent", vec!["Environment".to_string()]);
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_list_tags_of_resource_empty() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // List tags on table with no tags
        let tags = manager.list_tags_of_resource("TestTable").unwrap();
        assert!(tags.is_empty());
    }

    #[test]
    fn test_list_tags_of_resource_nonexistent_table() {
        let (manager, _temp) = setup_test_manager();
        
        let result = manager.list_tags_of_resource("NonExistent");
        assert!(matches!(result, Err(StorageError::TableNotFound(_))));
    }

    #[test]
    fn test_update_existing_tag() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Add initial tag
        let tags = vec![
            Tag { key: "Environment".to_string(), value: "Test".to_string() },
        ];
        manager.tag_resource("TestTable", tags).unwrap();
        
        // Update tag with new value
        let new_tags = vec![
            Tag { key: "Environment".to_string(), value: "Production".to_string() },
        ];
        manager.tag_resource("TestTable", new_tags).unwrap();
        
        // List tags to verify
        let tags = manager.list_tags_of_resource("TestTable").unwrap();
        assert_eq!(tags.len(), 1);
        assert_eq!(tags[0].key, "Environment");
        assert_eq!(tags[0].value, "Production");
    }

    #[test]
    fn test_untag_nonexistent_tag() {
        let (manager, _temp) = setup_test_manager();
        let req = create_test_request("TestTable");
        
        manager.create_table(&req).unwrap();
        
        // Add a tag
        let tags = vec![
            Tag { key: "Environment".to_string(), value: "Test".to_string() },
        ];
        manager.tag_resource("TestTable", tags).unwrap();
        
        // Try to remove a non-existent tag (should not fail)
        manager.untag_resource("TestTable", vec!["NonExistent".to_string()]).unwrap();
        
        // Verify original tag still exists
        let tags = manager.list_tags_of_resource("TestTable").unwrap();
        assert_eq!(tags.len(), 1);
        assert_eq!(tags[0].key, "Environment");
    }
}


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
            stream_specification: None,
        }
    }
}
