//! DynamoDB Streams management for Dyscount

use crate::models::*;
use chrono::{DateTime, Utc};
use rusqlite::{params, Connection};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use thiserror::Error;
use uuid::Uuid;

/// Stream manager error types
#[derive(Error, Debug)]
pub enum StreamError {
    #[error("Stream not found: {0}")]
    StreamNotFound(String),
    #[error("Stream already exists: {0}")]
    StreamAlreadyExists(String),
    #[error("Table not found: {0}")]
    TableNotFound(String),
    #[error("Shard not found: {0}")]
    ShardNotFound(String),
    #[error("Invalid iterator: {0}")]
    InvalidIterator(String),
    #[error("Database error: {0}")]
    DatabaseError(#[from] rusqlite::Error),
    #[error("JSON error: {0}")]
    JsonError(#[from] serde_json::Error),
    #[error("Storage error: {0}")]
    StorageError(#[from] crate::storage::StorageError),
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Manages DynamoDB Streams
pub struct StreamManager {
    data_directory: std::path::PathBuf,
    namespace: String,
    iterators: Arc<Mutex<HashMap<String, ShardIteratorInfo>>>,
}

/// Information stored about a shard iterator
#[derive(Debug, Clone)]
struct ShardIteratorInfo {
    stream_arn: String,
    shard_id: String,
    iterator_type: ShardIteratorType,
    sequence_number: Option<String>,
    timestamp: Option<DateTime<Utc>>,
    created_at: DateTime<Utc>,
}

impl StreamManager {
    /// Create a new StreamManager
    pub fn new(data_directory: impl Into<std::path::PathBuf>, namespace: impl Into<String>) -> Self {
        Self {
            data_directory: data_directory.into(),
            namespace: namespace.into(),
            iterators: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Get the database path for streams storage
    fn get_streams_db_path(&self) -> std::path::PathBuf {
        self.data_directory
            .join(&self.namespace)
            .join("__streams.db")
    }

    /// Initialize the streams database
    fn init_streams_db(&self) -> Result<Connection, StreamError> {
        let db_path = self.get_streams_db_path();
        
        // Create parent directory if it doesn't exist
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let conn = Connection::open(&db_path)?;

        // Create stream_records table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS stream_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_arn TEXT NOT NULL,
                sequence_number TEXT NOT NULL UNIQUE,
                event_id TEXT NOT NULL,
                event_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                keys BLOB NOT NULL,
                new_image BLOB,
                old_image BLOB,
                stream_view_type TEXT NOT NULL,
                creation_time TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0
            )",
            [],
        )?;

        // Create index on stream_arn and sequence_number for efficient querying
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_stream_records_arn ON stream_records(stream_arn)",
            [],
        )?;

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_stream_records_seq ON stream_records(sequence_number)",
            [],
        )?;

        Ok(conn)
    }

    /// Get a connection to the streams database
    fn get_connection(&self) -> Result<Connection, StreamError> {
        self.init_streams_db()
    }

    /// Generate a stream ARN for a table
    pub fn generate_stream_arn(&self, table_name: &str, stream_label: &str) -> String {
        format!(
            "arn:aws:dynamodb:local:{}:table/{}/stream/{}",
            self.namespace, table_name, stream_label
        )
    }

    /// Generate a sequence number for a stream record
    fn generate_sequence_number(&self, timestamp: DateTime<Utc>, counter: u64) -> String {
        // Format: <timestamp_millis>.<counter>
        format!("{}.{:010}", timestamp.timestamp_millis(), counter)
    }

    /// Create a stream for a table (called when table is created with StreamSpecification)
    pub fn create_stream(
        &self,
        table_name: &str,
        stream_view_type: StreamViewType,
    ) -> Result<StreamMetadata, StreamError> {
        let now = Utc::now();
        let stream_label = format!("{}", now.timestamp());
        let stream_arn = self.generate_stream_arn(table_name, &stream_label);

        let metadata = StreamMetadata {
            stream_arn: stream_arn.clone(),
            stream_label: stream_label.clone(),
            table_name: table_name.to_string(),
            stream_status: "ENABLED".to_string(),
            stream_view_type,
            creation_date_time: now,
        };

        Ok(metadata)
    }

    /// Write a stream record for an item operation
    pub fn write_stream_record(
        &self,
        stream_arn: &str,
        table_name: &str,
        event_name: &str, // INSERT, MODIFY, REMOVE
        stream_view_type: &StreamViewType,
        keys: &Item,
        new_image: Option<&Item>,
        old_image: Option<&Item>,
    ) -> Result<String, StreamError> {
        let conn = self.get_connection()?;
        let now = Utc::now();

        // Generate a unique event ID
        let event_id = Uuid::new_v4().to_string();

        // Get current count for sequence number generation
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM stream_records WHERE stream_arn = ?",
            [stream_arn],
            |row| row.get(0),
        ).unwrap_or(0);

        let sequence_number = self.generate_sequence_number(now, (count + 1) as u64);

        // Calculate size in bytes (approximate)
        let keys_json = serde_json::to_vec(keys)?;
        let new_image_json = new_image.map(|i| serde_json::to_vec(i)).transpose()?.unwrap_or_default();
        let old_image_json = old_image.map(|i| serde_json::to_vec(i)).transpose()?.unwrap_or_default();
        let size_bytes = (keys_json.len() + new_image_json.len() + old_image_json.len()) as i64;

        // Serialize for storage
        let keys_blob = keys_json;
        let new_image_blob = if new_image.is_some() { Some(new_image_json) } else { None };
        let old_image_blob = if old_image.is_some() { Some(old_image_json) } else { None };

        conn.execute(
            "INSERT INTO stream_records (
                stream_arn, sequence_number, event_id, event_name, table_name,
                keys, new_image, old_image, stream_view_type, creation_time, size_bytes
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                stream_arn,
                &sequence_number,
                &event_id,
                event_name,
                table_name,
                keys_blob,
                new_image_blob.as_ref().map(|v| v.as_slice()),
                old_image_blob.as_ref().map(|v| v.as_slice()),
                stream_view_type.to_string(),
                now.to_rfc3339(),
                size_bytes
            ],
        )?;

        Ok(sequence_number)
    }

    /// List all streams, optionally filtered by table
    pub fn list_streams(
        &self,
        table_name: Option<&str>,
        _exclusive_start_stream_arn: Option<&str>,
        limit: Option<i32>,
    ) -> Result<(Vec<Stream>, Option<String>), StreamError> {
        let conn = self.get_connection()?;

        // Build query based on filter
        let sql = if table_name.is_some() {
            "SELECT DISTINCT stream_arn, table_name FROM stream_records WHERE table_name = ?1 ORDER BY stream_arn"
        } else {
            "SELECT DISTINCT stream_arn, table_name FROM stream_records ORDER BY stream_arn"
        };

        let mut stmt = conn.prepare(sql)?;

        // Execute query
        let rows: Vec<_> = if let Some(table) = table_name {
            let row_iter = stmt.query_map([table], |row| {
                let stream_arn: String = row.get(0)?;
                let table_name: String = row.get(1)?;
                
                // Extract stream label from ARN
                let stream_label = stream_arn.split('/').last().unwrap_or("").to_string();
                
                Ok((stream_arn, stream_label, table_name))
            })?;
            row_iter.collect::<Result<Vec<_>, _>>()?
        } else {
            let row_iter = stmt.query_map([], |row| {
                let stream_arn: String = row.get(0)?;
                let table_name: String = row.get(1)?;
                
                let stream_label = stream_arn.split('/').last().unwrap_or("").to_string();
                
                Ok((stream_arn, stream_label, table_name))
            })?;
            row_iter.collect::<Result<Vec<_>, _>>()?
        };

        // Convert to Stream objects
        let mut streams: Vec<Stream> = rows.into_iter()
            .map(|(stream_arn, stream_label, table_name)| Stream {
                stream_arn,
                stream_label,
                table_name,
                stream_status: "ENABLED".to_string(),
            })
            .collect();

        // Apply limit
        let limit = limit.unwrap_or(100) as usize;
        let last_evaluated = if streams.len() > limit {
            let last = streams[limit - 1].stream_arn.clone();
            streams.truncate(limit);
            Some(last)
        } else {
            None
        };

        Ok((streams, last_evaluated))
    }

    /// Describe a stream
    pub fn describe_stream(
        &self,
        stream_arn: &str,
        _exclusive_start_shard_id: Option<&str>,
        limit: Option<i32>,
    ) -> Result<StreamDescription, StreamError> {
        let conn = self.get_connection()?;

        // Get stream info from the most recent record
        let mut stmt = conn.prepare(
            "SELECT DISTINCT table_name, stream_view_type, MIN(creation_time) 
             FROM stream_records WHERE stream_arn = ? GROUP BY table_name, stream_view_type"
        )?;

        let result: Result<(String, String, String), rusqlite::Error> = stmt.query_row(
            [stream_arn],
            |row| {
                Ok((
                    row.get(0)?,
                    row.get(1)?,
                    row.get(2)?,
                ))
            },
        );

        let (table_name, view_type_str, creation_time_str) = match result {
            Ok(data) => data,
            Err(rusqlite::Error::QueryReturnedNoRows) => {
                // Stream not found in records - try to extract info from ARN
                let parts: Vec<&str> = stream_arn.split('/').collect();
                if parts.len() < 2 {
                    return Err(StreamError::StreamNotFound(stream_arn.to_string()));
                }
                let table_name = parts[parts.len() - 2].to_string();
                let stream_label = parts.last().unwrap_or(&"").to_string();
                let now = Utc::now();
                
                return Ok(StreamDescription {
                    stream_arn: stream_arn.to_string(),
                    stream_label,
                    table_name,
                    stream_status: "ENABLED".to_string(),
                    stream_view_type: StreamViewType::NewAndOldImages,
                    creation_date_time: now,
                    shards: Some(vec![]),
                });
            }
            Err(e) => return Err(e.into()),
        };

        let stream_label = stream_arn.split('/').last().unwrap_or("").to_string();
        let creation_date_time = DateTime::parse_from_rfc3339(&creation_time_str)
            .map_err(|_| StreamError::StorageError(
                crate::storage::StorageError::InvalidKey("Invalid creation time".to_string())
            ))?
            .with_timezone(&Utc);

        let stream_view_type = match view_type_str.as_str() {
            "NEW_IMAGE" => StreamViewType::NewImage,
            "OLD_IMAGE" => StreamViewType::OldImage,
            "NEW_AND_OLD_IMAGES" => StreamViewType::NewAndOldImages,
            "KEYS_ONLY" => StreamViewType::KeysOnly,
            _ => StreamViewType::NewAndOldImages,
        };

        // Get sequence number range
        let seq_range = self.get_sequence_number_range(stream_arn)?;

        // Create single shard (simplified implementation)
        let shard = Shard {
            shard_id: "shardId-00000000000000000000-00000000".to_string(),
            parent_shard_id: None,
            sequence_number_range: seq_range,
        };

        let shards = if limit.map(|l| l > 0).unwrap_or(true) {
            Some(vec![shard])
        } else {
            Some(vec![])
        };

        Ok(StreamDescription {
            stream_arn: stream_arn.to_string(),
            stream_label,
            table_name,
            stream_status: "ENABLED".to_string(),
            stream_view_type,
            creation_date_time,
            shards,
        })
    }

    /// Get sequence number range for a stream
    fn get_sequence_number_range(&self, stream_arn: &str) -> Result<SequenceNumberRange, StreamError> {
        let conn = self.get_connection()?;

        let min_seq: Option<String> = conn.query_row(
            "SELECT MIN(sequence_number) FROM stream_records WHERE stream_arn = ?",
            [stream_arn],
            |row| row.get(0),
        ).ok();

        let max_seq: Option<String> = conn.query_row(
            "SELECT MAX(sequence_number) FROM stream_records WHERE stream_arn = ?",
            [stream_arn],
            |row| row.get(0),
        ).ok();

        Ok(SequenceNumberRange {
            starting_sequence_number: min_seq.unwrap_or_else(|| "0".to_string()),
            ending_sequence_number: max_seq,
        })
    }

    /// Get a shard iterator
    pub fn get_shard_iterator(
        &self,
        stream_arn: &str,
        shard_id: &str,
        shard_iterator_type: ShardIteratorType,
        sequence_number: Option<&str>,
        timestamp: Option<DateTime<Utc>>,
    ) -> Result<String, StreamError> {
        // Generate iterator token
        let iterator_id = Uuid::new_v4().to_string();
        
        // Store iterator info
        let iterator_info = ShardIteratorInfo {
            stream_arn: stream_arn.to_string(),
            shard_id: shard_id.to_string(),
            iterator_type: shard_iterator_type.clone(),
            sequence_number: sequence_number.map(|s| s.to_string()),
            timestamp,
            created_at: Utc::now(),
        };

        self.iterators.lock().unwrap().insert(iterator_id.clone(), iterator_info);

        // Format iterator as base64-like string (just UUID for now)
        Ok(format!("iterator-{}", iterator_id))
    }

    /// Get records from a shard iterator
    pub fn get_records(
        &self,
        shard_iterator: &str,
        limit: Option<i32>,
    ) -> Result<(Vec<Record>, Option<String>), StreamError> {
        // Parse iterator
        let iterator_id = shard_iterator.trim_start_matches("iterator-");
        
        let iterators = self.iterators.lock().unwrap();
        let iterator_info = iterators
            .get(iterator_id)
            .cloned()
            .ok_or_else(|| StreamError::InvalidIterator(shard_iterator.to_string()))?;
        
        drop(iterators);

        let conn = self.get_connection()?;
        let limit = limit.unwrap_or(1000);

        // Collect records based on iterator type
        let rows: Vec<(Record, String)> = match iterator_info.iterator_type {
            ShardIteratorType::TrimHorizon => {
                let mut stmt = conn.prepare(
                    "SELECT sequence_number, event_id, event_name, table_name, keys, 
                            new_image, old_image, stream_view_type, creation_time, size_bytes
                     FROM stream_records 
                     WHERE stream_arn = ?
                     ORDER BY sequence_number
                     LIMIT ?"
                )?;
                let row_iter = stmt.query_map(params![iterator_info.stream_arn, limit], |row| {
                    self.row_to_stream_record(row)
                })?;
                row_iter.collect::<Result<Vec<_>, _>>()?
            }
            ShardIteratorType::Latest => {
                let mut stmt = conn.prepare(
                    "SELECT sequence_number, event_id, event_name, table_name, keys, 
                            new_image, old_image, stream_view_type, creation_time, size_bytes
                     FROM stream_records 
                     WHERE stream_arn = ? AND creation_time > ?
                     ORDER BY sequence_number
                     LIMIT ?"
                )?;
                let row_iter = stmt.query_map(
                    params![iterator_info.stream_arn, iterator_info.created_at.to_rfc3339(), limit],
                    |row| self.row_to_stream_record(row)
                )?;
                row_iter.collect::<Result<Vec<_>, _>>()?
            }
            ShardIteratorType::AtSequenceNumber => {
                let seq = iterator_info.sequence_number.as_deref().unwrap_or("0");
                let mut stmt = conn.prepare(
                    "SELECT sequence_number, event_id, event_name, table_name, keys, 
                            new_image, old_image, stream_view_type, creation_time, size_bytes
                     FROM stream_records 
                     WHERE stream_arn = ? AND sequence_number >= ?
                     ORDER BY sequence_number
                     LIMIT ?"
                )?;
                let row_iter = stmt.query_map(params![iterator_info.stream_arn, seq, limit], |row| {
                    self.row_to_stream_record(row)
                })?;
                row_iter.collect::<Result<Vec<_>, _>>()?
            }
            ShardIteratorType::AfterSequenceNumber => {
                let seq = iterator_info.sequence_number.as_deref().unwrap_or("0");
                let mut stmt = conn.prepare(
                    "SELECT sequence_number, event_id, event_name, table_name, keys, 
                            new_image, old_image, stream_view_type, creation_time, size_bytes
                     FROM stream_records 
                     WHERE stream_arn = ? AND sequence_number > ?
                     ORDER BY sequence_number
                     LIMIT ?"
                )?;
                let row_iter = stmt.query_map(params![iterator_info.stream_arn, seq, limit], |row| {
                    self.row_to_stream_record(row)
                })?;
                row_iter.collect::<Result<Vec<_>, _>>()?
            }
            ShardIteratorType::AtTimestamp => {
                let ts = iterator_info.timestamp.unwrap_or_else(|| Utc::now());
                let mut stmt = conn.prepare(
                    "SELECT sequence_number, event_id, event_name, table_name, keys, 
                            new_image, old_image, stream_view_type, creation_time, size_bytes
                     FROM stream_records 
                     WHERE stream_arn = ? AND creation_time >= ?
                     ORDER BY sequence_number
                     LIMIT ?"
                )?;
                let row_iter = stmt.query_map(params![iterator_info.stream_arn, ts.to_rfc3339(), limit], |row| {
                    self.row_to_stream_record(row)
                })?;
                row_iter.collect::<Result<Vec<_>, _>>()?
            }
        };

        // Extract records and track last sequence number
        let mut records = Vec::new();
        let mut last_sequence_number: Option<String> = None;

        for (record, seq_num) in rows {
            last_sequence_number = Some(seq_num);
            records.push(record);
        }

        // Generate next iterator
        let next_iterator = if records.len() >= limit as usize {
            // More records available - create new iterator after last record
            let next_seq = last_sequence_number.map(|s| format!("after-{}", s));
            let new_iterator_id = Uuid::new_v4().to_string();
            
            let new_iterator_info = ShardIteratorInfo {
                stream_arn: iterator_info.stream_arn.clone(),
                shard_id: iterator_info.shard_id.clone(),
                iterator_type: ShardIteratorType::AfterSequenceNumber,
                sequence_number: next_seq.map(|s| s.trim_start_matches("after-").to_string()),
                timestamp: None,
                created_at: Utc::now(),
            };

            self.iterators.lock().unwrap().insert(new_iterator_id.clone(), new_iterator_info);
            Some(format!("iterator-{}", new_iterator_id))
        } else {
            // No more records - return empty iterator (or could return None)
            Some(shard_iterator.to_string())
        };

        Ok((records, next_iterator))
    }

    /// Convert a database row to a Record
    fn row_to_stream_record(
        &self,
        row: &rusqlite::Row,
    ) -> Result<(Record, String), rusqlite::Error> {
        let sequence_number: String = row.get(0)?;
        let event_id: String = row.get(1)?;
        let event_name: String = row.get(2)?;
        let table_name: String = row.get(3)?;
        let keys_blob: Vec<u8> = row.get(4)?;
        let new_image_blob: Option<Vec<u8>> = row.get(5)?;
        let old_image_blob: Option<Vec<u8>> = row.get(6)?;
        let stream_view_type_str: String = row.get(7)?;
        let creation_time_str: String = row.get(8)?;
        let size_bytes: i64 = row.get(9)?;

        let keys: Item = serde_json::from_slice(&keys_blob).map_err(|e| {
            rusqlite::Error::FromSqlConversionFailure(
                4,
                rusqlite::types::Type::Blob,
                Box::new(e),
            )
        })?;

        let new_image = new_image_blob
            .filter(|b| !b.is_empty())
            .map(|b| serde_json::from_slice(&b))
            .transpose()
            .map_err(|e| {
                rusqlite::Error::FromSqlConversionFailure(
                    5,
                    rusqlite::types::Type::Blob,
                    Box::new(e),
                )
            })?;

        let old_image = old_image_blob
            .filter(|b| !b.is_empty())
            .map(|b| serde_json::from_slice(&b))
            .transpose()
            .map_err(|e| {
                rusqlite::Error::FromSqlConversionFailure(
                    6,
                    rusqlite::types::Type::Blob,
                    Box::new(e),
                )
            })?;

        let stream_view_type = match stream_view_type_str.as_str() {
            "NEW_IMAGE" => StreamViewType::NewImage,
            "OLD_IMAGE" => StreamViewType::OldImage,
            "NEW_AND_OLD_IMAGES" => StreamViewType::NewAndOldImages,
            "KEYS_ONLY" => StreamViewType::KeysOnly,
            _ => StreamViewType::NewAndOldImages,
        };

        let creation_time = DateTime::parse_from_rfc3339(&creation_time_str)
            .map_err(|_| rusqlite::Error::InvalidQuery)?
            .with_timezone(&Utc);

        let stream_record = StreamRecord {
            approximate_creation_date_time: creation_time,
            keys,
            new_image,
            old_image,
            sequence_number: sequence_number.clone(),
            size_bytes,
            stream_view_type,
        };

        let record = Record {
            event_id,
            event_name,
            event_version: "1.1".to_string(),
            aws_region: "local".to_string(),
            dynamodb: stream_record,
            event_source: "aws:dynamodb".to_string(),
        };

        Ok((record, sequence_number))
    }

    /// Get stream metadata for a table (if stream is enabled)
    pub fn get_table_stream_metadata(
        &self,
        table_name: &str,
    ) -> Result<Option<StreamMetadata>, StreamError> {
        let conn = self.get_connection()?;

        let result: Result<(String, String, String, String), rusqlite::Error> = conn.query_row(
            "SELECT DISTINCT stream_arn, stream_view_type, MIN(creation_time) 
             FROM stream_records WHERE table_name = ? GROUP BY stream_arn, stream_view_type LIMIT 1",
            [table_name],
            |row| {
                Ok((
                    row.get(0)?,
                    row.get(1)?,
                    row.get(2)?,
                    row.get(3)?,
                ))
            },
        );

        match result {
            Ok((stream_arn, view_type_str, _min_time, creation_time_str)) => {
                let stream_label = stream_arn.split('/').last().unwrap_or("").to_string();
                let stream_view_type = match view_type_str.as_str() {
                    "NEW_IMAGE" => StreamViewType::NewImage,
                    "OLD_IMAGE" => StreamViewType::OldImage,
                    "NEW_AND_OLD_IMAGES" => StreamViewType::NewAndOldImages,
                    "KEYS_ONLY" => StreamViewType::KeysOnly,
                    _ => StreamViewType::NewAndOldImages,
                };

                let creation_date_time = DateTime::parse_from_rfc3339(&creation_time_str)
                    .map_err(|_| StreamError::StorageError(
                        crate::storage::StorageError::InvalidKey("Invalid creation time".to_string())
                    ))?
                    .with_timezone(&Utc);

                Ok(Some(StreamMetadata {
                    stream_arn,
                    stream_label,
                    table_name: table_name.to_string(),
                    stream_status: "ENABLED".to_string(),
                    stream_view_type,
                    creation_date_time,
                }))
            }
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn setup_test_manager() -> (StreamManager, TempDir) {
        let temp_dir = TempDir::new().unwrap();
        let manager = StreamManager::new(temp_dir.path(), "test");
        (manager, temp_dir)
    }

    #[test]
    fn test_generate_stream_arn() {
        let (manager, _temp) = setup_test_manager();
        let arn = manager.generate_stream_arn("TestTable", "1234567890");
        assert!(arn.contains("TestTable"));
        assert!(arn.contains("1234567890"));
    }

    #[test]
    fn test_create_stream() {
        let (manager, _temp) = setup_test_manager();
        let metadata = manager.create_stream("TestTable", StreamViewType::NewAndOldImages).unwrap();
        
        assert_eq!(metadata.table_name, "TestTable");
        assert_eq!(metadata.stream_status, "ENABLED");
        assert!(metadata.stream_arn.contains("TestTable"));
    }

    #[test]
    fn test_write_and_get_records() {
        let (manager, _temp) = setup_test_manager();
        
        // Create stream metadata
        let metadata = manager.create_stream("TestTable", StreamViewType::NewAndOldImages).unwrap();
        
        // Write a record
        let mut keys = Item::new();
        keys.insert("pk".to_string(), AttributeValue::s("test-key"));
        
        let mut new_image = Item::new();
        new_image.insert("pk".to_string(), AttributeValue::s("test-key"));
        new_image.insert("name".to_string(), AttributeValue::s("Test Name"));
        
        let seq_num = manager.write_stream_record(
            &metadata.stream_arn,
            "TestTable",
            "INSERT",
            &StreamViewType::NewAndOldImages,
            &keys,
            Some(&new_image),
            None,
        ).unwrap();
        
        assert!(!seq_num.is_empty());
        
        // Get shard iterator
        let iterator = manager.get_shard_iterator(
            &metadata.stream_arn,
            "shardId-00000000000000000000-00000000",
            ShardIteratorType::TrimHorizon,
            None,
            None,
        ).unwrap();
        
        assert!(iterator.starts_with("iterator-"));
        
        // Get records
        let (records, next_iterator) = manager.get_records(&iterator, Some(10)).unwrap();
        
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].event_name, "INSERT");
        assert_eq!(records[0].dynamodb.sequence_number, seq_num);
        assert!(next_iterator.is_some());
    }
}
