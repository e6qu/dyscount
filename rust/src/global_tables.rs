//! Global Tables management for DynamoDB-compatible API
//!
//! This module provides a simplified local implementation of DynamoDB Global Tables.
//! In real DynamoDB, Global Tables replicate across AWS regions. Here, we simulate
//! the API but store everything locally.

use crate::models::*;
use crate::storage::{StorageError, TableManager};
use chrono::{DateTime, Utc};
use rusqlite::{params, Connection};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use thiserror::Error;
use uuid::Uuid;

/// Global tables error types
#[derive(Error, Debug)]
pub enum GlobalTableError {
    #[error("Global table already exists: {0}")]
    GlobalTableAlreadyExists(String),
    #[error("Global table not found: {0}")]
    GlobalTableNotFound(String),
    #[error("Table not found: {0}")]
    TableNotFound(String),
    #[error("Replica already exists in region: {0}")]
    ReplicaAlreadyExists(String),
    #[error("Replica not found in region: {0}")]
    ReplicaNotFound(String),
    #[error("Database error: {0}")]
    DatabaseError(#[from] rusqlite::Error),
    #[error("JSON error: {0}")]
    JsonError(#[from] serde_json::Error),
    #[error("Storage error: {0}")]
    StorageError(#[from] StorageError),
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Invalid key: {0}")]
    InvalidKey(String),
}

/// Manages Global Tables in SQLite
pub struct GlobalTableManager {
    data_directory: PathBuf,
    namespace: String,
    table_manager: Arc<TableManager>,
    connections: Arc<Mutex<HashMap<String, Connection>>>,
}

impl GlobalTableManager {
    /// Create a new GlobalTableManager
    pub fn new(
        data_directory: impl Into<PathBuf>,
        namespace: impl Into<String>,
        table_manager: Arc<TableManager>,
    ) -> Result<Self, GlobalTableError> {
        let data_directory = data_directory.into();
        let namespace = namespace.into();

        // Ensure namespace directory exists
        let ns_path = data_directory.join(&namespace);
        fs::create_dir_all(&ns_path)?;

        let manager = Self {
            data_directory,
            namespace,
            table_manager,
            connections: Arc::new(Mutex::new(HashMap::new())),
        };

        // Initialize metadata storage
        manager.init_global_tables_storage()?;

        Ok(manager)
    }

    /// Get the global tables metadata database path
    fn get_metadata_db_path(&self) -> PathBuf {
        self.data_directory
            .join(&self.namespace)
            .join("__global_tables")
            .join("metadata.db")
    }

    /// Initialize the global tables storage
    fn init_global_tables_storage(&self) -> Result<Connection, GlobalTableError> {
        let metadata_db_path = self.get_metadata_db_path();
        
        // Ensure directory exists
        if let Some(parent) = metadata_db_path.parent() {
            fs::create_dir_all(parent)?;
        }

        let conn = Connection::open(&metadata_db_path)?;

        // Create global tables metadata table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS global_tables (
                global_table_id TEXT PRIMARY KEY,
                global_table_name TEXT NOT NULL UNIQUE,
                global_table_arn TEXT NOT NULL,
                global_table_status TEXT NOT NULL,
                creation_date_time TEXT NOT NULL,
                underlying_table_name TEXT NOT NULL
            )",
            [],
        )?;

        // Create replicas table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS replicas (
                replica_id TEXT PRIMARY KEY,
                global_table_id TEXT NOT NULL,
                region_name TEXT NOT NULL,
                replica_status TEXT NOT NULL,
                kms_master_key_id TEXT,
                FOREIGN KEY (global_table_id) REFERENCES global_tables(global_table_id)
            )",
            [],
        )?;

        // Create index on global_table_name for faster lookups
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_global_table_name ON global_tables(global_table_name)",
            [],
        )?;

        Ok(conn)
    }

    /// Get connection to global tables metadata database
    fn get_metadata_connection(&self) -> Result<Connection, GlobalTableError> {
        let db_path = self.get_metadata_db_path();
        Ok(Connection::open(&db_path)?)
    }

    /// Create a new global table
    pub fn create_global_table(
        &self,
        req: &CreateGlobalTableRequest,
    ) -> Result<GlobalTableDescription, GlobalTableError> {
        let conn = self.get_metadata_connection()?;

        // Check if global table already exists
        let existing: Option<String> = conn
            .query_row(
                "SELECT global_table_id FROM global_tables WHERE global_table_name = ?",
                [&req.global_table_name],
                |row| row.get(0),
            )
            .ok();

        if existing.is_some() {
            return Err(GlobalTableError::GlobalTableAlreadyExists(
                req.global_table_name.clone(),
            ));
        }

        // Generate global table metadata
        let global_table_id = Uuid::new_v4().to_string();
        let now = Utc::now();
        let global_table_arn = format!(
            "arn:aws:dynamodb::{}:global-table/{}",
            self.namespace, req.global_table_name
        );

        // Create underlying table if it doesn't exist
        let underlying_table_name = format!("__gt_{}", req.global_table_name);
        
        // Check if underlying table exists by trying to describe it
        let table_exists = match self.table_manager.describe_table(&underlying_table_name) {
            Ok(_) => true,
            Err(_) => false,
        };

        if !table_exists {
            // Create underlying table with default schema
            let create_req = DynamoDBRequest {
                table_name: Some(underlying_table_name.clone()),
                key_schema: Some(vec![KeySchemaElement::hash("pk")]),
                attribute_definitions: Some(vec![AttributeDefinition::s("pk")]),
                billing_mode: Some("PAY_PER_REQUEST".to_string()),
                ..Default::default()
            };
            self.table_manager.create_table(&create_req)?;
        }

        // Insert global table metadata
        conn.execute(
            "INSERT INTO global_tables (
                global_table_id, global_table_name, global_table_arn,
                global_table_status, creation_date_time, underlying_table_name
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                global_table_id,
                req.global_table_name,
                global_table_arn,
                "ACTIVE",
                now.to_rfc3339(),
                underlying_table_name
            ],
        )?;

        // Insert replicas
        let mut replicas = Vec::new();
        for replica in &req.replication_group {
            let replica_id = Uuid::new_v4().to_string();
            conn.execute(
                "INSERT INTO replicas (
                    replica_id, global_table_id, region_name, replica_status
                ) VALUES (?1, ?2, ?3, ?4)",
                params![
                    replica_id,
                    global_table_id,
                    replica.region_name,
                    "ACTIVE"
                ],
            )?;

            replicas.push(ReplicaDescription {
                region_name: replica.region_name.clone(),
                replica_status: "ACTIVE".to_string(),
                kms_master_key_id: None,
            });
        }

        Ok(GlobalTableDescription {
            global_table_name: req.global_table_name.clone(),
            global_table_status: "ACTIVE".to_string(),
            global_table_arn: Some(global_table_arn),
            creation_date_time: now,
            replication_group: replicas,
        })
    }

    /// Update a global table (add/remove replicas)
    pub fn update_global_table(
        &self,
        req: &UpdateGlobalTableRequest,
    ) -> Result<GlobalTableDescription, GlobalTableError> {
        let conn = self.get_metadata_connection()?;

        // Get global table metadata
        let (global_table_id, global_table_arn, creation_date_time, _): (
            String,
            String,
            String,
            String,
        ) = conn
            .query_row(
                "SELECT global_table_id, global_table_arn, creation_date_time, underlying_table_name 
                 FROM global_tables WHERE global_table_name = ?",
                [&req.global_table_name],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                    ))
                },
            )
            .map_err(|_| {
                GlobalTableError::GlobalTableNotFound(req.global_table_name.clone())
            })?;

        // Process replica updates
        for update in &req.replica_updates {
            // Handle Create
            if let Some(create) = &update.create {
                // Check if replica already exists
                let existing: Option<String> = conn
                    .query_row(
                        "SELECT replica_id FROM replicas WHERE global_table_id = ? AND region_name = ?",
                        params![&global_table_id, &create.region_name],
                        |row| row.get(0),
                    )
                    .ok();

                if existing.is_some() {
                    return Err(GlobalTableError::ReplicaAlreadyExists(
                        create.region_name.clone(),
                    ));
                }

                let replica_id = Uuid::new_v4().to_string();
                conn.execute(
                    "INSERT INTO replicas (replica_id, global_table_id, region_name, replica_status)
                     VALUES (?1, ?2, ?3, ?4)",
                    params![replica_id, global_table_id, create.region_name, "ACTIVE"],
                )?;
            }

            // Handle Delete
            if let Some(delete) = &update.delete {
                let result = conn.execute(
                    "DELETE FROM replicas WHERE global_table_id = ? AND region_name = ?",
                    params![&global_table_id, &delete.region_name],
                )?;

                if result == 0 {
                    return Err(GlobalTableError::ReplicaNotFound(delete.region_name.clone()));
                }
            }
        }

        // Get updated replicas
        let replicas = self.get_replicas(&conn, &global_table_id)?;

        Ok(GlobalTableDescription {
            global_table_name: req.global_table_name.clone(),
            global_table_status: "ACTIVE".to_string(),
            global_table_arn: Some(global_table_arn),
            creation_date_time: DateTime::parse_from_rfc3339(&creation_date_time)
                .map_err(|_| GlobalTableError::InvalidKey("Invalid date format".to_string()))?
                .with_timezone(&Utc),
            replication_group: replicas,
        })
    }

    /// Describe a global table
    pub fn describe_global_table(
        &self,
        global_table_name: &str,
    ) -> Result<GlobalTableDescription, GlobalTableError> {
        let conn = self.get_metadata_connection()?;

        // Get global table metadata
        let (global_table_id, global_table_arn, creation_date_time, _): (
            String,
            String,
            String,
            String,
        ) = conn
            .query_row(
                "SELECT global_table_id, global_table_arn, creation_date_time, underlying_table_name 
                 FROM global_tables WHERE global_table_name = ?",
                [global_table_name],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                    ))
                },
            )
            .map_err(|_| GlobalTableError::GlobalTableNotFound(global_table_name.to_string()))?;

        // Get replicas
        let replicas = self.get_replicas(&conn, &global_table_id)?;

        Ok(GlobalTableDescription {
            global_table_name: global_table_name.to_string(),
            global_table_status: "ACTIVE".to_string(),
            global_table_arn: Some(global_table_arn),
            creation_date_time: DateTime::parse_from_rfc3339(&creation_date_time)
                .map_err(|_| GlobalTableError::InvalidKey("Invalid date format".to_string()))?
                .with_timezone(&Utc),
            replication_group: replicas,
        })
    }

    /// List all global tables
    pub fn list_global_tables(
        &self,
        exclusive_start: Option<&str>,
        limit: Option<i32>,
    ) -> Result<(Vec<GlobalTableSummary>, Option<String>), GlobalTableError> {
        let conn = self.get_metadata_connection()?;

        let limit = limit.unwrap_or(100).max(1).min(100) as usize;

        let mut global_tables = Vec::new();
        let mut last_name = None;

        // Build query based on exclusive_start
        let _query = if let Some(_start) = exclusive_start {
            "SELECT global_table_id, global_table_name 
             FROM global_tables 
             WHERE global_table_name > ?
             ORDER BY global_table_name 
             LIMIT ?"
        } else {
            "SELECT global_table_id, global_table_name 
             FROM global_tables 
             ORDER BY global_table_name 
             LIMIT ?"
        };

        let mut global_table_entries: Vec<(String, String)> = Vec::new();

        if let Some(start) = exclusive_start {
            let mut stmt = conn.prepare(
                "SELECT global_table_id, global_table_name 
                 FROM global_tables 
                 WHERE global_table_name > ?
                 ORDER BY global_table_name 
                 LIMIT ?"
            )?;

            let rows = stmt.query_map(params![start, limit + 1], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;

            for row in rows {
                global_table_entries.push(row?);
            }
        } else {
            let mut stmt = conn.prepare(
                "SELECT global_table_id, global_table_name 
                 FROM global_tables 
                 ORDER BY global_table_name 
                 LIMIT ?"
            )?;

            let rows = stmt.query_map([limit + 1], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;

            for row in rows {
                global_table_entries.push(row?);
            }
        };

        for (i, (global_table_id, global_table_name)) in global_table_entries.into_iter().enumerate() {

            if i >= limit {
                // This is the extra item - use it as the last_evaluated marker
                last_name = Some(global_table_name);
                break;
            }

            // Get replicas for this table
            let replicas = self.get_global_table_replicas(&conn, &global_table_id)?;

            global_tables.push(GlobalTableSummary {
                global_table_name,
                replication_group: replicas,
            });
        }

        Ok((global_tables, last_name))
    }

    /// Delete a global table
    pub fn delete_global_table(
        &self,
        global_table_name: &str,
    ) -> Result<GlobalTableDescription, GlobalTableError> {
        let conn = self.get_metadata_connection()?;

        // Get global table metadata before deletion
        let (global_table_id, global_table_arn, creation_date_time, _underlying_table_name): (
            String,
            String,
            String,
            String,
        ) = conn
            .query_row(
                "SELECT global_table_id, global_table_arn, creation_date_time, underlying_table_name 
                 FROM global_tables WHERE global_table_name = ?",
                [global_table_name],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                    ))
                },
            )
            .map_err(|_| GlobalTableError::GlobalTableNotFound(global_table_name.to_string()))?;

        // Get replicas before deletion
        let replicas = self.get_replicas(&conn, &global_table_id)?;

        // Delete replicas first (foreign key constraint)
        conn.execute(
            "DELETE FROM replicas WHERE global_table_id = ?",
            [&global_table_id],
        )?;

        // Delete global table
        conn.execute(
            "DELETE FROM global_tables WHERE global_table_id = ?",
            [&global_table_id],
        )?;

        // Optionally delete underlying table (keep data for safety)
        // Uncomment the following lines if you want to delete the underlying table too:
        // let _ = self.table_manager.delete_table(&underlying_table_name);

        Ok(GlobalTableDescription {
            global_table_name: global_table_name.to_string(),
            global_table_status: "DELETING".to_string(),
            global_table_arn: Some(global_table_arn),
            creation_date_time: DateTime::parse_from_rfc3339(&creation_date_time)
                .map_err(|_| GlobalTableError::InvalidKey("Invalid date format".to_string()))?
                .with_timezone(&Utc),
            replication_group: replicas,
        })
    }

    /// Update global table settings (billing mode, capacity)
    pub fn update_global_table_settings(
        &self,
        req: &UpdateGlobalTableSettingsRequest,
    ) -> Result<GlobalTableDescription, GlobalTableError> {
        // For this simplified implementation, we just return the current description
        // In a full implementation, this would update the billing mode and capacity settings
        self.describe_global_table(&req.global_table_name)
    }

    /// Helper: Get replica descriptions for a global table
    fn get_replicas(
        &self,
        conn: &Connection,
        global_table_id: &str,
    ) -> Result<Vec<ReplicaDescription>, GlobalTableError> {
        let mut stmt = conn.prepare(
            "SELECT region_name, replica_status, kms_master_key_id 
             FROM replicas WHERE global_table_id = ?"
        )?;

        let rows = stmt.query_map([global_table_id], |row| {
            Ok(ReplicaDescription {
                region_name: row.get(0)?,
                replica_status: row.get(1)?,
                kms_master_key_id: row.get(2)?,
            })
        })?;

        let mut replicas = Vec::new();
        for row in rows {
            replicas.push(row?);
        }

        Ok(replicas)
    }

    /// Helper: Get replica definitions (simplified) for a global table
    fn get_global_table_replicas(
        &self,
        conn: &Connection,
        global_table_id: &str,
    ) -> Result<Vec<Replica>, GlobalTableError> {
        let mut stmt = conn.prepare(
            "SELECT region_name FROM replicas WHERE global_table_id = ?"
        )?;

        let rows = stmt.query_map([global_table_id], |row| {
            Ok(Replica {
                region_name: row.get(0)?,
            })
        })?;

        let mut replicas = Vec::new();
        for row in rows {
            replicas.push(row?);
        }

        Ok(replicas)
    }

    /// Get the underlying table name for a global table
    pub fn get_underlying_table_name(
        &self,
        global_table_name: &str,
    ) -> Result<String, GlobalTableError> {
        let conn = self.get_metadata_connection()?;

        let underlying_name: String = conn
            .query_row(
                "SELECT underlying_table_name FROM global_tables WHERE global_table_name = ?",
                [global_table_name],
                |row| row.get(0),
            )
            .map_err(|_| GlobalTableError::GlobalTableNotFound(global_table_name.to_string()))?;

        Ok(underlying_name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn setup_test_manager() -> (GlobalTableManager, TempDir) {
        let temp_dir = TempDir::new().unwrap();
        let table_manager = TableManager::new(temp_dir.path(), "test").unwrap();
        let manager = GlobalTableManager::new(
            temp_dir.path(),
            "test",
            Arc::new(table_manager),
        )
        .unwrap();
        (manager, temp_dir)
    }

    #[test]
    fn test_create_global_table() {
        let (manager, _temp) = setup_test_manager();

        let req = CreateGlobalTableRequest {
            global_table_name: "TestGlobalTable".to_string(),
            replication_group: vec![
                Replica {
                    region_name: "us-east-1".to_string(),
                },
                Replica {
                    region_name: "us-west-2".to_string(),
                },
            ],
        };

        let desc = manager.create_global_table(&req).unwrap();

        assert_eq!(desc.global_table_name, "TestGlobalTable");
        assert_eq!(desc.global_table_status, "ACTIVE");
        assert_eq!(desc.replication_group.len(), 2);
    }

    #[test]
    fn test_create_duplicate_global_table() {
        let (manager, _temp) = setup_test_manager();

        let req = CreateGlobalTableRequest {
            global_table_name: "TestGlobalTable".to_string(),
            replication_group: vec![Replica {
                region_name: "us-east-1".to_string(),
            }],
        };

        manager.create_global_table(&req).unwrap();

        let result = manager.create_global_table(&req);
        assert!(matches!(
            result,
            Err(GlobalTableError::GlobalTableAlreadyExists(_))
        ));
    }

    #[test]
    fn test_describe_global_table() {
        let (manager, _temp) = setup_test_manager();

        let req = CreateGlobalTableRequest {
            global_table_name: "TestGlobalTable".to_string(),
            replication_group: vec![Replica {
                region_name: "us-east-1".to_string(),
            }],
        };

        manager.create_global_table(&req).unwrap();

        let desc = manager.describe_global_table("TestGlobalTable").unwrap();
        assert_eq!(desc.global_table_name, "TestGlobalTable");
        assert_eq!(desc.replication_group.len(), 1);
    }

    #[test]
    fn test_describe_nonexistent_global_table() {
        let (manager, _temp) = setup_test_manager();

        let result = manager.describe_global_table("NonExistent");
        assert!(matches!(
            result,
            Err(GlobalTableError::GlobalTableNotFound(_))
        ));
    }

    #[test]
    fn test_list_global_tables() {
        let (manager, _temp) = setup_test_manager();

        // Create two global tables
        let req1 = CreateGlobalTableRequest {
            global_table_name: "Table1".to_string(),
            replication_group: vec![Replica {
                region_name: "us-east-1".to_string(),
            }],
        };
        let req2 = CreateGlobalTableRequest {
            global_table_name: "Table2".to_string(),
            replication_group: vec![Replica {
                region_name: "us-west-2".to_string(),
            }],
        };

        manager.create_global_table(&req1).unwrap();
        manager.create_global_table(&req2).unwrap();

        let (tables, _) = manager.list_global_tables(None, None).unwrap();
        assert_eq!(tables.len(), 2);
    }

    #[test]
    fn test_update_global_table_add_replica() {
        let (manager, _temp) = setup_test_manager();

        // Create global table with one replica
        let create_req = CreateGlobalTableRequest {
            global_table_name: "TestGlobalTable".to_string(),
            replication_group: vec![Replica {
                region_name: "us-east-1".to_string(),
            }],
        };
        manager.create_global_table(&create_req).unwrap();

        // Add another replica
        let update_req = UpdateGlobalTableRequest {
            global_table_name: "TestGlobalTable".to_string(),
            replica_updates: vec![ReplicaUpdate {
                create: Some(CreateReplicaAction {
                    region_name: "eu-west-1".to_string(),
                }),
                delete: None,
            }],
        };

        let desc = manager.update_global_table(&update_req).unwrap();
        assert_eq!(desc.replication_group.len(), 2);
    }

    #[test]
    fn test_update_global_table_remove_replica() {
        let (manager, _temp) = setup_test_manager();

        // Create global table with two replicas
        let create_req = CreateGlobalTableRequest {
            global_table_name: "TestGlobalTable".to_string(),
            replication_group: vec![
                Replica {
                    region_name: "us-east-1".to_string(),
                },
                Replica {
                    region_name: "us-west-2".to_string(),
                },
            ],
        };
        manager.create_global_table(&create_req).unwrap();

        // Remove one replica
        let update_req = UpdateGlobalTableRequest {
            global_table_name: "TestGlobalTable".to_string(),
            replica_updates: vec![ReplicaUpdate {
                create: None,
                delete: Some(DeleteReplicaAction {
                    region_name: "us-west-2".to_string(),
                }),
            }],
        };

        let desc = manager.update_global_table(&update_req).unwrap();
        assert_eq!(desc.replication_group.len(), 1);
        assert_eq!(desc.replication_group[0].region_name, "us-east-1");
    }

    #[test]
    fn test_delete_global_table() {
        let (manager, _temp) = setup_test_manager();

        let req = CreateGlobalTableRequest {
            global_table_name: "TestGlobalTable".to_string(),
            replication_group: vec![Replica {
                region_name: "us-east-1".to_string(),
            }],
        };

        manager.create_global_table(&req).unwrap();

        let desc = manager.delete_global_table("TestGlobalTable").unwrap();
        assert_eq!(desc.global_table_name, "TestGlobalTable");
        assert_eq!(desc.global_table_status, "DELETING");

        // Verify it's deleted
        let result = manager.describe_global_table("TestGlobalTable");
        assert!(matches!(
            result,
            Err(GlobalTableError::GlobalTableNotFound(_))
        ));
    }
}
