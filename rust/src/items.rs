//! Item storage and operations for DynamoDB items

use crate::expression::{parse_condition_expression, ExpressionEvaluator};
use crate::models::*;
use crate::storage::{StorageError, TableManager};
use crate::stream_manager::{StreamError, StreamManager};
use rusqlite::{params, Connection};
use serde_json;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tracing::{debug, error};

/// Error types for item operations
#[derive(Debug, thiserror::Error)]
pub enum ItemError {
    #[error("Item not found")]
    NotFound,
    #[error("Invalid key: {0}")]
    InvalidKey(String),
    #[error("Invalid update expression: {0}")]
    InvalidUpdateExpression(String),
    #[error("Condition check failed: {0}")]
    ConditionCheckFailed(String),
    #[error("Storage error: {0}")]
    Storage(#[from] StorageError),
    #[error("Database error: {0}")]
    Database(#[from] rusqlite::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("Expression error: {0}")]
    Expression(String),
}

/// Manages DynamoDB items in SQLite
pub struct ItemManager {
    table_manager: Arc<TableManager>,
    stream_manager: Arc<StreamManager>,
    connections: Mutex<HashMap<String, Connection>>,
}

impl ItemManager {
    /// Create a new ItemManager
    pub fn new(table_manager: Arc<TableManager>, stream_manager: Arc<StreamManager>) -> Self {
        Self {
            table_manager,
            stream_manager,
            connections: Mutex::new(HashMap::new()),
        }
    }

    /// Extract key attributes from an item based on key schema
    fn extract_key_attributes(
        &self,
        item: &Item,
        key_schema: &[KeySchemaElement],
    ) -> Item {
        let mut key = Item::new();
        for ks in key_schema {
            if let Some(attr) = item.get(&ks.attribute_name) {
                key.insert(ks.attribute_name.clone(), attr.clone());
            }
        }
        key
    }

    /// Write a stream record for an item operation
    fn write_stream_record(
        &self,
        table_name: &str,
        event_name: &str,
        keys: &Item,
        new_image: Option<&Item>,
        old_image: Option<&Item>,
    ) -> Result<(), StreamError> {
        // Check if stream is enabled for this table
        let stream_spec = self.table_manager.get_stream_specification(table_name)?;
        
        if let Some(spec) = stream_spec {
            if !spec.stream_enabled {
                return Ok(());
            }

            let view_type = spec.stream_view_type.unwrap_or(StreamViewType::NewAndOldImages);
            
            // Generate stream ARN
            let stream_arn = self.stream_manager.generate_stream_arn(
                table_name,
                &format!("{}", chrono::Utc::now().timestamp())
            );

            // Filter images based on view type
            let (new_img, old_img) = match view_type {
                StreamViewType::KeysOnly => (None, None),
                StreamViewType::NewImage => (new_image, None),
                StreamViewType::OldImage => (None, old_image),
                StreamViewType::NewAndOldImages => (new_image, old_image),
            };

            self.stream_manager.write_stream_record(
                &stream_arn,
                table_name,
                event_name,
                &view_type,
                keys,
                new_img,
                old_img,
            )?;
        }

        Ok(())
    }

    /// Get or create a connection for a table
    fn get_connection(&self, table_name: &str) -> Result<Connection, ItemError> {
        // For simplicity, open a new connection each time
        // In production, you'd want connection pooling
        self.table_manager.get_connection(table_name).map_err(|e| e.into())
    }

    /// Extract primary key values from an item
    fn extract_key(
        &self,
        item: &Item,
        key_schema: &[KeySchemaElement],
        attr_defs: &[AttributeDefinition],
    ) -> Result<(String, Option<String>), ItemError> {
        let mut pk_name = None;
        let mut pk_type = None;
        let mut sk_name = None;
        let mut sk_type = None;

        // Find key attributes from schema
        for ks in key_schema {
            if ks.key_type == "HASH" {
                pk_name = Some(ks.attribute_name.clone());
                // Find type from attribute definitions
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

        let pk_name = pk_name.ok_or_else(|| ItemError::InvalidKey("No HASH key in schema".to_string()))?;
        let pk_type = pk_type.ok_or_else(|| ItemError::InvalidKey(format!("No type found for partition key {}", pk_name)))?;

        // Extract partition key value
        let pk_attr = item.get(&pk_name)
            .ok_or_else(|| ItemError::InvalidKey(format!("Missing partition key attribute: {}", pk_name)))?;
        let pk_value = self.attr_to_string(pk_attr, &pk_type)?;

        // Extract sort key value if present
        let sk_value = if let (Some(sk_name), Some(sk_type)) = (sk_name, sk_type) {
            let sk_attr = item.get(&sk_name)
                .ok_or_else(|| ItemError::InvalidKey(format!("Missing sort key attribute: {}", sk_name)))?;
            Some(self.attr_to_string(sk_attr, &sk_type)?)
        } else {
            None
        };

        Ok((pk_value, sk_value))
    }

    /// Convert attribute value to string for storage
    fn attr_to_string(&self, attr: &AttributeValue, attr_type: &str) -> Result<String, ItemError> {
        match attr_type {
            "S" => attr.as_s()
                .map(|s| s.to_string())
                .ok_or_else(|| ItemError::InvalidKey("Expected string attribute".to_string())),
            "N" => attr.as_n()
                .map(|n| n.to_string())
                .ok_or_else(|| ItemError::InvalidKey("Expected number attribute".to_string())),
            "B" => {
                // For binary, we store the base64 string
                match attr {
                    AttributeValue::B { b } => Ok(b.clone()),
                    _ => Err(ItemError::InvalidKey("Expected binary attribute".to_string())),
                }
            }
            _ => Err(ItemError::InvalidKey(format!("Unsupported key type: {}", attr_type))),
        }
    }

    /// Get an item by its primary key
    pub fn get_item(
        &self,
        table_name: &str,
        key: &Item,
        _consistent_read: bool,
    ) -> Result<Option<Item>, ItemError> {
        let conn = self.get_connection(table_name)?;

        // Get table metadata
        let metadata = self.table_manager.describe_table(table_name)?;

        // Extract key values
        let (pk, sk) = self.extract_key(key, &metadata.key_schema, &metadata.attribute_definitions)?;

        debug!("Getting item: pk={}, sk={:?}", pk, sk);

        // Query the database
        let data: Option<Vec<u8>> = if let Some(sk_val) = sk {
            conn.query_row(
                "SELECT data FROM items WHERE pk = ? AND sk = ?",
                params![pk, sk_val],
                |row| row.get(0),
            ).ok()
        } else {
            conn.query_row(
                "SELECT data FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')",
                params![pk],
                |row| row.get(0),
            ).ok()
        };

        match data {
            Some(bytes) => {
                let item: Item = serde_json::from_slice(&bytes)?;
                Ok(Some(item))
            }
            None => Ok(None),
        }
    }

    /// Put an item (insert or replace)
    pub fn put_item(
        &self,
        table_name: &str,
        item: &Item,
        return_old: bool,
        condition_expression: Option<&str>,
        expression_names: Option<&HashMap<String, String>>,
        expression_values: Option<&HashMap<String, AttributeValue>>,
    ) -> Result<Option<Item>, ItemError> {
        let conn = self.get_connection(table_name)?;

        // Get table metadata
        let metadata = self.table_manager.describe_table(table_name)?;

        // Extract key values from the item itself
        let (pk, sk) = self.extract_key(item, &metadata.key_schema, &metadata.attribute_definitions)?;

        debug!("Putting item: pk={}, sk={:?}", pk, sk);

        // Get existing item for condition check and return_old
        let key = self.build_key_item(&metadata.key_schema, &pk, sk.as_deref())?;
        let existing_item = self.get_item(table_name, &key, true)?;

        // Evaluate condition expression if provided
        if let Some(cond_expr) = condition_expression {
            let empty_names = HashMap::new();
            let empty_values = HashMap::new();
            let names = expression_names.unwrap_or(&empty_names);
            let values = expression_values.unwrap_or(&empty_values);

            let evaluator = ExpressionEvaluator::new(names, values);
            let condition = parse_condition_expression(cond_expr)
                .map_err(|e| ItemError::Expression(e.to_string()))?;

            // For conditional puts, evaluate against existing item (or empty if new)
            let empty_item = Item::new();
            let item_to_check = existing_item.as_ref().unwrap_or(&empty_item);
            let result = evaluator
                .evaluate_condition(&condition, item_to_check)
                .map_err(|e| ItemError::Expression(e.to_string()))?;

            if !result {
                return Err(ItemError::ConditionCheckFailed(
                    "The conditional request failed".to_string(),
                ));
            }
        }

        // Serialize the item
        let data = serde_json::to_vec(item)?;
        let now = chrono::Utc::now().timestamp();

        // Insert or replace
        conn.execute(
            "INSERT INTO items (pk, sk, data, created_at, updated_at) 
             VALUES (?1, ?2, ?3, ?4, ?5)
             ON CONFLICT(pk, sk) DO UPDATE SET
             data = excluded.data, updated_at = excluded.updated_at",
            params![pk, sk, data, now, now],
        )?;

        // Write stream record
        let keys = self.extract_key_attributes(item, &metadata.key_schema);
        let event_name = if existing_item.is_some() { "MODIFY" } else { "INSERT" };
        if let Err(e) = self.write_stream_record(
            table_name,
            event_name,
            &keys,
            Some(item),
            existing_item.as_ref(),
        ) {
            error!("Failed to write stream record: {}", e);
        }

        Ok(if return_old { existing_item } else { None })
    }

    /// Delete an item by its primary key
    pub fn delete_item(
        &self,
        table_name: &str,
        key: &Item,
        return_old: bool,
        condition_expression: Option<&str>,
        expression_names: Option<&HashMap<String, String>>,
        expression_values: Option<&HashMap<String, AttributeValue>>,
    ) -> Result<Option<Item>, ItemError> {
        let conn = self.get_connection(table_name)?;

        // Get table metadata
        let metadata = self.table_manager.describe_table(table_name)?;

        // Extract key values
        let (pk, sk) = self.extract_key(key, &metadata.key_schema, &metadata.attribute_definitions)?;

        debug!("Deleting item: pk={}, sk={:?}", pk, sk);

        // Get existing item for condition check
        let existing_item = self.get_item(table_name, key, true)?;

        // Evaluate condition expression if provided
        if let Some(cond_expr) = condition_expression {
            let empty_names = HashMap::new();
            let empty_values = HashMap::new();
            let names = expression_names.unwrap_or(&empty_names);
            let values = expression_values.unwrap_or(&empty_values);

            let evaluator = ExpressionEvaluator::new(names, values);
            let condition = parse_condition_expression(cond_expr)
                .map_err(|e| ItemError::Expression(e.to_string()))?;

            // For conditional deletes, evaluate against existing item (or fail if not exists)
            let item_to_check = match &existing_item {
                Some(item) => item,
                None => {
                    return Err(ItemError::ConditionCheckFailed(
                        "The conditional request failed".to_string(),
                    ));
                }
            };

            let result = evaluator
                .evaluate_condition(&condition, item_to_check)
                .map_err(|e| ItemError::Expression(e.to_string()))?;

            if !result {
                return Err(ItemError::ConditionCheckFailed(
                    "The conditional request failed".to_string(),
                ));
            }
        }

        // Delete the item
        if let Some(sk_val) = sk {
            conn.execute(
                "DELETE FROM items WHERE pk = ? AND sk = ?",
                params![pk, sk_val],
            )?;
        } else {
            conn.execute(
                "DELETE FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')",
                params![pk],
            )?;
        }

        // Write stream record
        let keys = self.extract_key_attributes(key, &metadata.key_schema);
        if let Err(e) = self.write_stream_record(
            table_name,
            "REMOVE",
            &keys,
            None,
            existing_item.as_ref(),
        ) {
            error!("Failed to write stream record: {}", e);
        }

        Ok(if return_old { existing_item } else { None })
    }

    /// Update an item using update expressions
    pub fn update_item(
        &self,
        table_name: &str,
        key: &Item,
        update_expression: Option<&str>,
        expression_values: Option<&HashMap<String, AttributeValue>>,
        return_values: &str,
        condition_expression: Option<&str>,
        expression_names: Option<&HashMap<String, String>>,
    ) -> Result<(Option<Item>, Option<Item>), ItemError> {
        let conn = self.get_connection(table_name)?;

        // Get table metadata
        let metadata = self.table_manager.describe_table(table_name)?;

        // Extract key values
        let (pk, sk) = self.extract_key(key, &metadata.key_schema, &metadata.attribute_definitions)?;

        debug!("Updating item: pk={}, sk={:?}", pk, sk);

        // Get current item or create new one
        let mut current_item = match self.get_item(table_name, key, true)? {
            Some(item) => item,
            None => {
                // Create new item with key attributes
                let mut new_item = Item::new();
                for ks in &metadata.key_schema {
                    if let Some(attr) = key.get(&ks.attribute_name) {
                        new_item.insert(ks.attribute_name.clone(), attr.clone());
                    }
                }
                new_item
            }
        };

        // Evaluate condition expression if provided
        if let Some(cond_expr) = condition_expression {
            let empty_names = HashMap::new();
            let empty_values = HashMap::new();
            let names = expression_names.unwrap_or(&empty_names);
            let values = expression_values.unwrap_or(&empty_values);

            let evaluator = ExpressionEvaluator::new(names, values);
            let condition = parse_condition_expression(cond_expr)
                .map_err(|e| ItemError::Expression(e.to_string()))?;

            // Evaluate against current item
            let result = evaluator
                .evaluate_condition(&condition, &current_item)
                .map_err(|e| ItemError::Expression(e.to_string()))?;

            if !result {
                return Err(ItemError::ConditionCheckFailed(
                    "The conditional request failed".to_string(),
                ));
            }
        }

        // Store old item for return
        let old_item = if return_values == "ALL_OLD" {
            Some(current_item.clone())
        } else {
            None
        };

        // Apply update expression
        if let Some(expr) = update_expression {
            self.apply_update_expression(&mut current_item, expr, expression_values)?;
        }

        // Serialize and store
        let data = serde_json::to_vec(&current_item)?;
        let now = chrono::Utc::now().timestamp();

        conn.execute(
            "INSERT INTO items (pk, sk, data, created_at, updated_at) 
             VALUES (?1, ?2, ?3, ?4, ?5)
             ON CONFLICT(pk, sk) DO UPDATE SET
             data = excluded.data, updated_at = excluded.updated_at",
            params![pk, sk.as_deref(), data, now, now],
        )?;

        // Write stream record
        let keys = self.extract_key_attributes(key, &metadata.key_schema);
        let event_name = if old_item.is_some() { "MODIFY" } else { "INSERT" };
        if let Err(e) = self.write_stream_record(
            table_name,
            event_name,
            &keys,
            Some(&current_item),
            old_item.as_ref(),
        ) {
            error!("Failed to write stream record: {}", e);
        }

        let new_item = if return_values == "ALL_NEW" {
            Some(current_item)
        } else {
            None
        };

        Ok((new_item, old_item))
    }

    /// Apply a simple SET update expression
    fn apply_update_expression(
        &self,
        item: &mut Item,
        expression: &str,
        expression_values: Option<&HashMap<String, AttributeValue>>,
    ) -> Result<(), ItemError> {
        // Simple parser for SET expressions
        // Format: SET attr1 = :val1, attr2 = :val2, ...
        let expr = expression.trim();
        
        if !expr.to_uppercase().starts_with("SET ") {
            return Err(ItemError::InvalidUpdateExpression(
                "Only SET expressions are supported".to_string()
            ));
        }

        let assignments = &expr[4..]; // Remove "SET " prefix
        
        // Split by commas (but not within parentheses)
        for assignment in self.split_assignments(assignments) {
            let assignment = assignment.trim();
            let parts: Vec<&str> = assignment.splitn(2, '=').collect();
            
            if parts.len() != 2 {
                return Err(ItemError::InvalidUpdateExpression(
                    format!("Invalid assignment: {}", assignment)
                ));
            }

            let attr_name = parts[0].trim().trim_start_matches('#');
            let value_ref = parts[1].trim();

            // Look up value in expression values
            if let Some(values) = expression_values {
                if value_ref.starts_with(':') {
                    let value_key = &value_ref[1..];
                    if let Some(value) = values.get(value_key) {
                        item.insert(attr_name.to_string(), value.clone());
                    }
                }
            }
        }

        Ok(())
    }

    /// Split assignments handling nested parentheses
    fn split_assignments(&self, expr: &str) -> Vec<String> {
        let mut result = Vec::new();
        let mut current = String::new();
        let mut depth = 0;

        for c in expr.chars() {
            match c {
                '(' => {
                    depth += 1;
                    current.push(c);
                }
                ')' => {
                    depth -= 1;
                    current.push(c);
                }
                ',' if depth == 0 => {
                    if !current.is_empty() {
                        result.push(current.trim().to_string());
                        current.clear();
                    }
                }
                _ => current.push(c),
            }
        }

        if !current.is_empty() {
            result.push(current.trim().to_string());
        }

        result
    }

    /// Query items by partition key with optional filter expression
    pub fn query(
        &self,
        table_name: &str,
        index_name: Option<&str>,
        partition_key_value: &str,
        _key_conditions: Option<&HashMap<String, crate::models::Condition>>,
        scan_index_forward: bool,
        limit: Option<i32>,
        filter_expression: Option<&str>,
        expression_names: Option<&HashMap<String, String>>,
        expression_values: Option<&HashMap<String, AttributeValue>>,
    ) -> Result<(Vec<Item>, Option<Item>, i32, i32), ItemError> {
        let conn = self.get_connection(table_name)?;

        // Get table metadata
        let metadata = self.table_manager.describe_table(table_name)?;

        // Use GSI schema if index_name is provided
        let key_schema = if let Some(idx_name) = index_name {
            metadata.global_secondary_indexes
                .as_ref()
                .and_then(|gsis| gsis.iter().find(|g| g.index_name == idx_name))
                .map(|gsi| gsi.key_schema.clone())
                .ok_or_else(|| ItemError::InvalidKey(format!("Index not found: {}", idx_name)))?
        } else {
            metadata.key_schema.clone()
        };

        debug!("Querying items: pk={}, forward={}, limit={:?}", 
               partition_key_value, scan_index_forward, limit);

        // Get all items for the partition key
        let mut stmt = conn.prepare("SELECT data FROM items WHERE pk = ?")?;
        let rows = stmt.query_map(params![partition_key_value], |row| {
            let data: Vec<u8> = row.get(0)?;
            Ok(data)
        })?;

        let mut items: Vec<Item> = Vec::new();
        for row in rows {
            let data = row?;
            if let Ok(item) = serde_json::from_slice::<Item>(&data) {
                items.push(item);
            }
        }

        // Sort items by sort key if present
        if key_schema.len() > 1 {
            let sk_name = &key_schema[1].attribute_name;
            items.sort_by(|a, b| {
                let a_val = a.get(sk_name).and_then(|v| v.as_s()).unwrap_or("");
                let b_val = b.get(sk_name).and_then(|v| v.as_s()).unwrap_or("");
                if scan_index_forward {
                    a_val.cmp(b_val)
                } else {
                    b_val.cmp(a_val)
                }
            });
        }

        // Track scanned count before filtering
        let scanned_count = items.len() as i32;

        // Apply filter expression if provided
        let filtered_items = if let Some(filter_expr) = filter_expression {
            self.apply_filter_expression(items, filter_expr, expression_names, expression_values)?
        } else {
            items
        };

        // Apply limit after filtering
        let (final_items, last_evaluated_key) = if let Some(limit_val) = limit {
            let limit = limit_val as usize;
            if filtered_items.len() > limit {
                let last_item = &filtered_items[limit - 1];
                let last_key = self.extract_key_from_item(last_item, &key_schema)?;
                let mut truncated = filtered_items;
                truncated.truncate(limit);
                (truncated, Some(last_key))
            } else {
                (filtered_items, None)
            }
        } else {
            (filtered_items, None)
        };

        let count = final_items.len() as i32;

        Ok((final_items, last_evaluated_key, count, scanned_count))
    }

    /// Apply filter expression to a list of items
    fn apply_filter_expression(
        &self,
        items: Vec<Item>,
        filter_expression: &str,
        expression_names: Option<&HashMap<String, String>>,
        expression_values: Option<&HashMap<String, AttributeValue>>,
    ) -> Result<Vec<Item>, ItemError> {
        let empty_names = HashMap::new();
        let empty_values = HashMap::new();
        let names = expression_names.unwrap_or(&empty_names);
        let values = expression_values.unwrap_or(&empty_values);

        let evaluator = ExpressionEvaluator::new(names, values);
        let condition = parse_condition_expression(filter_expression)
            .map_err(|e| ItemError::Expression(e.to_string()))?;

        let mut filtered = Vec::new();
        for item in items {
            match evaluator.evaluate_condition(&condition, &item) {
                Ok(true) => filtered.push(item),
                Ok(false) => (), // Item filtered out
                Err(e) => return Err(ItemError::Expression(e.to_string())),
            }
        }

        Ok(filtered)
    }

    /// Scan all items in a table with optional filter expression
    pub fn scan(
        &self,
        table_name: &str,
        _index_name: Option<&str>,
        limit: Option<i32>,
        _exclusive_start_key: Option<&Item>,
        filter_expression: Option<&str>,
        expression_names: Option<&HashMap<String, String>>,
        expression_values: Option<&HashMap<String, AttributeValue>>,
    ) -> Result<(Vec<Item>, Option<Item>, i32, i32), ItemError> {
        let conn = self.get_connection(table_name)?;

        // Get table metadata
        let metadata = self.table_manager.describe_table(table_name)?;

        debug!("Scanning items: limit={:?}", limit);

        // Get all items
        let mut stmt = conn.prepare("SELECT data FROM items")?;
        let rows = stmt.query_map([], |row| {
            let data: Vec<u8> = row.get(0)?;
            Ok(data)
        })?;

        let mut items: Vec<Item> = Vec::new();
        for row in rows {
            let data = row?;
            if let Ok(item) = serde_json::from_slice::<Item>(&data) {
                items.push(item);
            }
        }

        // Track scanned count before filtering
        let scanned_count = items.len() as i32;

        // Apply filter expression if provided
        let filtered_items = if let Some(filter_expr) = filter_expression {
            self.apply_filter_expression(items, filter_expr, expression_names, expression_values)?
        } else {
            items
        };

        // Apply limit after filtering
        let (final_items, last_evaluated_key) = if let Some(limit_val) = limit {
            let limit = limit_val as usize;
            if filtered_items.len() > limit {
                let last_item = &filtered_items[limit - 1];
                let last_key = self.extract_key_from_item(last_item, &metadata.key_schema)?;
                let mut truncated = filtered_items;
                truncated.truncate(limit);
                (truncated, Some(last_key))
            } else {
                (filtered_items, None)
            }
        } else {
            (filtered_items, None)
        };

        let count = final_items.len() as i32;

        Ok((final_items, last_evaluated_key, count, scanned_count))
    }

    /// Build a key item from pk/sk values
    fn build_key_item(
        &self,
        key_schema: &[KeySchemaElement],
        pk: &str,
        sk: Option<&str>,
    ) -> Result<Item, ItemError> {
        let mut item = Item::new();

        // Add partition key
        if let Some(ks) = key_schema.first() {
            item.insert(ks.attribute_name.clone(), AttributeValue::s(pk));
        }

        // Add sort key if present
        if let Some(sk_val) = sk {
            if let Some(ks) = key_schema.get(1) {
                item.insert(ks.attribute_name.clone(), AttributeValue::s(sk_val));
            }
        }

        Ok(item)
    }

    /// Extract key attributes from an item
    fn extract_key_from_item(
        &self,
        item: &Item,
        key_schema: &[KeySchemaElement],
    ) -> Result<Item, ItemError> {
        let mut key = Item::new();

        for ks in key_schema {
            if let Some(attr) = item.get(&ks.attribute_name) {
                key.insert(ks.attribute_name.clone(), attr.clone());
            }
        }

        Ok(key)
    }

    // ============== Batch Operations ==============

    /// Batch get items from multiple tables
    pub fn batch_get_item(
        &self,
        requests: &HashMap<String, KeysAndAttributes>,
    ) -> Result<(HashMap<String, Vec<Item>>, HashMap<String, KeysAndAttributes>), ItemError> {
        let mut responses: HashMap<String, Vec<Item>> = HashMap::new();
        let mut unprocessed: HashMap<String, KeysAndAttributes> = HashMap::new();

        // Check total key count (max 100)
        let total_keys: usize = requests.values().map(|k| k.keys.len()).sum();
        if total_keys > 100 {
            return Err(ItemError::InvalidKey(
                "BatchGetItem can retrieve up to 100 items".to_string(),
            ));
        }

        for (table_name, keys_and_attrs) in requests {
            match self.batch_get_from_table(table_name, keys_and_attrs) {
                Ok(items) => {
                    responses.insert(table_name.clone(), items);
                }
                Err(_) => {
                    unprocessed.insert(table_name.clone(), keys_and_attrs.clone());
                }
            }
        }

        Ok((responses, unprocessed))
    }

    /// Get items from a single table for batch get
    fn batch_get_from_table(
        &self,
        table_name: &str,
        keys_and_attrs: &KeysAndAttributes,
    ) -> Result<Vec<Item>, ItemError> {
        let conn = self.get_connection(table_name)?;
        
        // Get table metadata
        let metadata = self
            .table_manager
            .describe_table(table_name)
            .map_err(|_| ItemError::InvalidKey(format!("Table not found: {}", table_name)))?;

        let key_schema = &metadata.key_schema;
        let attr_defs = &metadata.attribute_definitions;

        let mut items = Vec::new();

        for key in &keys_and_attrs.keys {
            let (pk, sk) = self.extract_key(key, key_schema, attr_defs)?;

            let mut stmt = if let Some(ref sk_val) = sk {
                conn.prepare("SELECT data FROM items WHERE pk = ? AND sk = ?")?
            } else {
                conn.prepare("SELECT data FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')")?
            };

            let data: Result<String, _> = if let Some(ref sk_val) = sk {
                stmt.query_row(params![pk, sk_val], |row| row.get(0))
            } else {
                stmt.query_row(params![pk], |row| row.get(0))
            };

            if let Ok(data) = data {
                let item: Item = serde_json::from_str(&data)?;
                items.push(item);
            }
        }

        Ok(items)
    }

    /// Batch write items to multiple tables
    pub fn batch_write_item(
        &self,
        requests: &HashMap<String, Vec<WriteRequest>>,
    ) -> Result<HashMap<String, Vec<WriteRequest>>, ItemError> {
        let mut unprocessed: HashMap<String, Vec<WriteRequest>> = HashMap::new();

        // Check total item count (max 25)
        let total_items: usize = requests.values().map(|v| v.len()).sum();
        if total_items > 25 {
            return Err(ItemError::InvalidKey(
                "BatchWriteItem can write up to 25 items".to_string(),
            ));
        }

        for (table_name, write_requests) in requests {
            let unproc = self.batch_write_to_table(table_name, write_requests)?;
            if !unproc.is_empty() {
                unprocessed.insert(table_name.clone(), unproc);
            }
        }

        Ok(unprocessed)
    }

    /// Write items to a single table for batch write
    fn batch_write_to_table(
        &self,
        table_name: &str,
        write_requests: &[WriteRequest],
    ) -> Result<Vec<WriteRequest>, ItemError> {
        let mut unprocessed = Vec::new();

        for write_req in write_requests {
            let success = if let Some(ref put) = write_req.put_request {
                self.put_item(table_name, &put.item, false, None, None, None).is_ok()
            } else if let Some(ref del) = write_req.delete_request {
                self.delete_item(table_name, &del.key, false, None, None, None).is_ok()
            } else {
                false
            };

            if !success {
                unprocessed.push(write_req.clone());
            }
        }

        Ok(unprocessed)
    }

    // ============== Transaction Operations ==============

    /// ConditionCheck - verify item conditions without modifying
    pub fn condition_check(
        &self,
        table_name: &str,
        key: &Item,
        condition_expression: &str,
        expression_names: Option<&HashMap<String, String>>,
        expression_values: Option<&HashMap<String, AttributeValue>>,
    ) -> Result<(), ItemError> {
        // Get existing item
        let existing_item = self.get_item(table_name, key, true)?;

        // If item doesn't exist, condition check fails
        let item_to_check = match existing_item {
            Some(item) => item,
            None => {
                return Err(ItemError::ConditionCheckFailed(
                    "The conditional request failed".to_string(),
                ));
            }
        };

        // Evaluate condition expression
        let empty_names: HashMap<String, String> = HashMap::new();
        let empty_values: HashMap<String, AttributeValue> = HashMap::new();
        let names = expression_names.unwrap_or(&empty_names);
        let values = expression_values.unwrap_or(&empty_values);

        let evaluator = ExpressionEvaluator::new(names, values);
        let condition = parse_condition_expression(condition_expression)
            .map_err(|e| ItemError::Expression(e.to_string()))?;

        let result = evaluator
            .evaluate_condition(&condition, &item_to_check)
            .map_err(|e| ItemError::Expression(e.to_string()))?;

        if !result {
            return Err(ItemError::ConditionCheckFailed(
                "The conditional request failed".to_string(),
            ));
        }

        Ok(())
    }

    /// Transact get items atomically
    pub fn transact_get_items(
        &self,
        items: &[TransactGetItem],
    ) -> Result<Vec<ItemResponse>, ItemError> {
        // DynamoDB limit: up to 100 items for TransactGetItems
        if items.len() > 100 {
            return Err(ItemError::InvalidKey(
                "TransactGetItems can retrieve up to 100 items".to_string(),
            ));
        }

        // Check for duplicates
        let mut key_set = std::collections::HashSet::new();
        for item in items {
            let key = format!("{}:{:?}", item.get.table_name, item.get.key);
            if !key_set.insert(key) {
                return Err(ItemError::InvalidKey(
                    "Duplicate key in transaction".to_string(),
                ));
            }
        }

        let mut responses = Vec::new();

        for item in items {
            let table_name = &item.get.table_name;
            let key = &item.get.key;

            match self.get_item(table_name, key, true) {
                Ok(item_opt) => {
                    responses.push(ItemResponse { item: item_opt });
                }
                Err(_) => {
                    responses.push(ItemResponse { item: None });
                }
            }
        }

        Ok(responses)
    }

    /// Transact write items atomically
    pub fn transact_write_items(&self, items: &[TransactWriteItem]) -> Result<(), ItemError> {
        // DynamoDB limit: up to 25 items
        if items.len() > 25 {
            return Err(ItemError::InvalidKey(
                "TransactWriteItems can write up to 25 items".to_string(),
            ));
        }

        // Check for duplicates
        let mut key_set = std::collections::HashSet::new();
        for item in items {
            let (table_name, key) = self.extract_transact_key(item);
            let key_str = format!("{}:{:?}", table_name, key);
            if !key_set.insert(key_str) {
                return Err(ItemError::InvalidKey(
                    "Duplicate key in transaction".to_string(),
                ));
            }
        }

        // Validate all items first
        for item in items {
            self.validate_transact_item(item)?;
        }

        // Execute all operations
        for item in items {
            self.execute_transact_write(item)?;
        }

        Ok(())
    }

    /// Extract table name and key from transact write item
    fn extract_transact_key(&self, item: &TransactWriteItem) -> (String, Item) {
        if let Some(ref put) = item.put {
            (put.table_name.clone(), put.item.clone())
        } else if let Some(ref update) = item.update {
            (update.table_name.clone(), update.key.clone())
        } else if let Some(ref delete) = item.delete {
            (delete.table_name.clone(), delete.key.clone())
        } else if let Some(ref check) = item.condition_check {
            (check.table_name.clone(), check.key.clone())
        } else {
            (String::new(), Item::new())
        }
    }

    /// Validate a transact write item
    fn validate_transact_item(&self, item: &TransactWriteItem) -> Result<(), ItemError> {
        let table_name = if let Some(ref put) = item.put {
            &put.table_name
        } else if let Some(ref update) = item.update {
            &update.table_name
        } else if let Some(ref delete) = item.delete {
            &delete.table_name
        } else if let Some(ref check) = item.condition_check {
            &check.table_name
        } else {
            return Err(ItemError::InvalidKey(
                "Invalid transaction item".to_string(),
            ));
        };

        // Check table exists
        let _ = self
            .table_manager
            .describe_table(table_name)
            .map_err(|_| ItemError::InvalidKey(format!("Table not found: {}", table_name)))?;

        Ok(())
    }

    /// Execute a transact write operation
    fn execute_transact_write(&self, item: &TransactWriteItem) -> Result<(), ItemError> {
        if let Some(ref put) = item.put {
            // Handle conditional put
            let condition_expression = put.condition_expression.as_deref();
            self.put_item(
                &put.table_name,
                &put.item,
                false,
                condition_expression,
                None,
                None,
            )?;
        } else if let Some(ref update) = item.update {
            // Execute update with optional update expression
            let update_expression = update.update_expression.as_deref();
            self.update_item(
                &update.table_name,
                &update.key,
                update_expression,
                None,
                "NONE",
                None,
                None,
            )?;
        } else if let Some(ref delete) = item.delete {
            // Handle conditional delete
            let condition_expression = delete.condition_expression.as_deref();
            self.delete_item(
                &delete.table_name,
                &delete.key,
                false,
                condition_expression,
                None,
                None,
            )?;
        } else if let Some(ref condition_check) = item.condition_check {
            // ConditionCheck - verify the condition without modifying
            let existing_item = self.get_item(
                &condition_check.table_name,
                &condition_check.key,
                true,
            )?;

            // If item doesn't exist, condition check fails
            let item_to_check = match existing_item {
                Some(item) => item,
                None => {
                    return Err(ItemError::ConditionCheckFailed(
                        "The conditional request failed".to_string(),
                    ));
                }
            };

            // Evaluate condition expression
            let empty_names: HashMap<String, String> = HashMap::new();
            let empty_values: HashMap<String, AttributeValue> = HashMap::new();
            let evaluator = ExpressionEvaluator::new(&empty_names, &empty_values);
            let condition = parse_condition_expression(&condition_check.condition_expression)
                .map_err(|e| ItemError::Expression(e.to_string()))?;

            let result = evaluator
                .evaluate_condition(&condition, &item_to_check)
                .map_err(|e| ItemError::Expression(e.to_string()))?;

            if !result {
                return Err(ItemError::ConditionCheckFailed(
                    "The conditional request failed".to_string(),
                ));
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::expression::{parse_condition_expression, ExpressionEvaluator};
    use crate::stream_manager::StreamManager;
    use std::collections::HashMap;
    use tempfile::TempDir;

    fn setup_test_manager() -> (ItemManager, Arc<TableManager>, Arc<StreamManager>, TempDir) {
        let temp_dir = TempDir::new().unwrap();
        let table_manager = Arc::new(
            TableManager::new(temp_dir.path(), "test").unwrap()
        );
        let stream_manager = Arc::new(StreamManager::new(temp_dir.path(), "test"));
        let item_manager = ItemManager::new(table_manager.clone(), stream_manager.clone());
        (item_manager, table_manager, stream_manager, temp_dir)
    }

    fn create_test_table(tm: &TableManager, name: &str) {
        let req = DynamoDBRequest {
            table_name: Some(name.to_string()),
            key_schema: Some(vec![
                KeySchemaElement::hash("pk"),
                KeySchemaElement::range("sk"),
            ]),
            attribute_definitions: Some(vec![
                AttributeDefinition::s("pk"),
                AttributeDefinition::s("sk"),
            ]),
            billing_mode: Some("PAY_PER_REQUEST".to_string()),
            ..Default::default()
        };
        tm.create_table(&req).unwrap();
    }

    #[test]
    fn test_put_and_get_item() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("name".to_string(), AttributeValue::s("John Doe"));
            i.insert("age".to_string(), AttributeValue::n("30"));
            i
        };

        // Put item
        let old = im.put_item("TestTable", &item, false, None, None, None).unwrap();
        assert!(old.is_none());

        // Get item
        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        let retrieved = im.get_item("TestTable", &key, true).unwrap();
        assert!(retrieved.is_some());
        
        let retrieved = retrieved.unwrap();
        assert_eq!(retrieved.get("name").unwrap().as_s(), Some("John Doe"));
    }

    #[test]
    fn test_update_item() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("name".to_string(), AttributeValue::s("John"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        // Update item
        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        let expr_values = {
            let mut m = HashMap::new();
            m.insert("newName".to_string(), AttributeValue::s("Jane"));
            m
        };

        let (new_item, old_item) = im.update_item(
            "TestTable",
            &key,
            Some("SET name = :newName"),
            Some(&expr_values),
            "ALL_NEW",
            None,
            None,
        ).unwrap();

        assert!(new_item.is_some());
        assert_eq!(new_item.unwrap().get("name").unwrap().as_s(), Some("Jane"));
    }

    #[test]
    fn test_delete_item() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("data".to_string(), AttributeValue::s("value"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        // Delete item
        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        let old = im.delete_item("TestTable", &key, true, None, None, None).unwrap();
        assert!(old.is_some());

        // Verify deletion
        let retrieved = im.get_item("TestTable", &key, true).unwrap();
        assert!(retrieved.is_none());
    }

    #[test]
    fn test_query() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put multiple items
        for i in 0..5 {
            let item = {
                let mut item = Item::new();
                item.insert("pk".to_string(), AttributeValue::s("user1"));
                item.insert("sk".to_string(), AttributeValue::s(&format!("item{}", i)));
                item.insert("data".to_string(), AttributeValue::s(&format!("data{}", i)));
                item
            };
            im.put_item("TestTable", &item, false, None, None, None).unwrap();
        }

        // Query items
        let (items, last_key, count, scanned_count) = im.query(
            "TestTable",
            None,
            "user1",
            None,
            true,
            Some(3),
            None,
            None,
            None,
        ).unwrap();

        assert_eq!(items.len(), 3);
        assert_eq!(count, 3);
        assert_eq!(scanned_count, 5);
        assert!(last_key.is_some()); // Pagination key present
    }

    #[test]
    fn test_query_with_filter_expression() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put multiple items with different statuses
        for i in 0..5 {
            let item = {
                let mut item = Item::new();
                item.insert("pk".to_string(), AttributeValue::s("user1"));
                item.insert("sk".to_string(), AttributeValue::s(&format!("item{}", i)));
                item.insert("status".to_string(), AttributeValue::s(if i % 2 == 0 { "active" } else { "inactive" }));
                item.insert("age".to_string(), AttributeValue::n(&format!("{}", 20 + i)));
                item
            };
            im.put_item("TestTable", &item, false, None, None, None).unwrap();
        }

        // Query with filter expression for active status
        let expr_values: HashMap<String, AttributeValue> = [
            ("statusVal".to_string(), AttributeValue::s("active".to_string())),
        ].into_iter().collect();

        let (items, last_key, count, scanned_count) = im.query(
            "TestTable",
            None,
            "user1",
            None,
            true,
            None,
            Some("status = :statusVal"),
            None,
            Some(&expr_values),
        ).unwrap();

        // Should return only 3 items (item0, item2, item4 have status=active)
        assert_eq!(items.len(), 3);
        assert_eq!(count, 3);
        assert_eq!(scanned_count, 5); // All 5 items were scanned
        assert!(last_key.is_none());

        // Query with filter expression for age > 22
        let expr_values: HashMap<String, AttributeValue> = [
            ("ageVal".to_string(), AttributeValue::n("22".to_string())),
        ].into_iter().collect();

        let (items, _, count, scanned_count) = im.query(
            "TestTable",
            None,
            "user1",
            None,
            true,
            None,
            Some("age > :ageVal"),
            None,
            Some(&expr_values),
        ).unwrap();

        // Should return 2 items (item3=23, item4=24 have age > 22)
        assert_eq!(items.len(), 2);
        assert_eq!(count, 2);
        assert_eq!(scanned_count, 5);
    }

    #[test]
    fn test_scan() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put multiple items
        for i in 0..5 {
            let item = {
                let mut item = Item::new();
                item.insert("pk".to_string(), AttributeValue::s(&format!("user{}", i)));
                item.insert("sk".to_string(), AttributeValue::s("profile"));
                item.insert("data".to_string(), AttributeValue::s(&format!("data{}", i)));
                item
            };
            im.put_item("TestTable", &item, false, None, None, None).unwrap();
        }

        // Scan items
        let (items, last_key, count, scanned_count) = im.scan("TestTable", None, Some(3), None, None, None, None).unwrap();

        assert_eq!(items.len(), 3);
        assert_eq!(count, 3);
        assert_eq!(scanned_count, 5);
        assert!(last_key.is_some());
    }

    #[test]
    fn test_scan_with_filter_expression() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put multiple items with different categories
        for i in 0..5 {
            let item = {
                let mut item = Item::new();
                item.insert("pk".to_string(), AttributeValue::s(&format!("user{}", i)));
                item.insert("sk".to_string(), AttributeValue::s("profile"));
                item.insert("category".to_string(), AttributeValue::s(if i < 3 { "A" } else { "B" }));
                item.insert("score".to_string(), AttributeValue::n(&format!("{}", i * 10)));
                item
            };
            im.put_item("TestTable", &item, false, None, None, None).unwrap();
        }

        // Scan with filter expression for category = A
        let expr_values: HashMap<String, AttributeValue> = [
            ("catVal".to_string(), AttributeValue::s("A".to_string())),
        ].into_iter().collect();

        let (items, _, count, scanned_count) = im.scan(
            "TestTable",
            None,
            None,
            None,
            Some("category = :catVal"),
            None,
            Some(&expr_values),
        ).unwrap();

        // Should return 3 items (user0, user1, user2 have category=A)
        assert_eq!(items.len(), 3);
        assert_eq!(count, 3);
        assert_eq!(scanned_count, 5); // All 5 items were scanned

        // Scan with filter expression for score >= 20
        let expr_values: HashMap<String, AttributeValue> = [
            ("scoreVal".to_string(), AttributeValue::n("20".to_string())),
        ].into_iter().collect();

        let (items, _, count, scanned_count) = im.scan(
            "TestTable",
            None,
            None,
            None,
            Some("score >= :scoreVal"),
            None,
            Some(&expr_values),
        ).unwrap();

        // Should return 3 items (user2=20, user3=30, user4=40 have score >= 20)
        assert_eq!(items.len(), 3);
        assert_eq!(count, 3);
        assert_eq!(scanned_count, 5);
    }

    #[test]
    fn test_filter_expression_with_functions() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put items with different attributes
        let item1 = {
            let mut item = Item::new();
            item.insert("pk".to_string(), AttributeValue::s("user1"));
            item.insert("sk".to_string(), AttributeValue::s("profile"));
            item.insert("name".to_string(), AttributeValue::s("John Doe"));
            item.insert("email".to_string(), AttributeValue::s("john@example.com"));
            item
        };
        im.put_item("TestTable", &item1, false, None, None, None).unwrap();

        let item2 = {
            let mut item = Item::new();
            item.insert("pk".to_string(), AttributeValue::s("user2"));
            item.insert("sk".to_string(), AttributeValue::s("profile"));
            item.insert("name".to_string(), AttributeValue::s("Jane Smith"));
            // No email attribute
            item
        };
        im.put_item("TestTable", &item2, false, None, None, None).unwrap();

        let item3 = {
            let mut item = Item::new();
            item.insert("pk".to_string(), AttributeValue::s("user3"));
            item.insert("sk".to_string(), AttributeValue::s("profile"));
            item.insert("name".to_string(), AttributeValue::s("Bob Johnson"));
            item.insert("email".to_string(), AttributeValue::s("bob@test.org"));
            item
        };
        im.put_item("TestTable", &item3, false, None, None, None).unwrap();

        // Scan with attribute_exists filter
        let (items, _, count, scanned_count) = im.scan(
            "TestTable",
            None,
            None,
            None,
            Some("attribute_exists(email)"),
            None,
            None,
        ).unwrap();

        // Should return 2 items (user1 and user3 have email)
        assert_eq!(items.len(), 2);
        assert_eq!(count, 2);
        assert_eq!(scanned_count, 3);

        // Scan with begins_with filter
        let expr_values: HashMap<String, AttributeValue> = [
            ("prefix".to_string(), AttributeValue::s("John".to_string())),
        ].into_iter().collect();

        let (items, _, count, _) = im.scan(
            "TestTable",
            None,
            None,
            None,
            Some("begins_with(name, :prefix)"),
            None,
            Some(&expr_values),
        ).unwrap();

        // Should return 1 item (only John Doe begins with "John")
        assert_eq!(items.len(), 1);
        assert_eq!(count, 1);
        assert_eq!(items[0].get("pk").unwrap().as_s(), Some("user1"));

        // Scan with contains filter
        let expr_values: HashMap<String, AttributeValue> = [
            ("domain".to_string(), AttributeValue::s("example.com".to_string())),
        ].into_iter().collect();

        let (items, _, count, _) = im.scan(
            "TestTable",
            None,
            None,
            None,
            Some("contains(email, :domain)"),
            None,
            Some(&expr_values),
        ).unwrap();

        // Should return 1 item (john@example.com)
        assert_eq!(items.len(), 1);
        assert_eq!(count, 1);
        assert_eq!(items[0].get("pk").unwrap().as_s(), Some("user1"));
    }

    #[test]
    fn test_put_item_with_condition_success() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("active"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        // Conditional put with condition that should pass
        let new_item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("updated"));
            i
        };

        let expr_values = {
            let mut m = HashMap::new();
            m.insert("val".to_string(), AttributeValue::s("active"));
            m
        };

        let result = im.put_item(
            "TestTable",
            &new_item,
            true,
            Some("status = :val"),
            None,
            Some(&expr_values),
        );
        assert!(result.is_ok());
        // Should return old item
        assert_eq!(result.unwrap().unwrap().get("status").unwrap().as_s(), Some("active"));
    }

    #[test]
    fn test_put_item_with_condition_failure() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("active"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        // Conditional put with condition that should fail
        let new_item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("updated"));
            i
        };

        let expr_values = {
            let mut m = HashMap::new();
            m.insert("val".to_string(), AttributeValue::s("inactive"));
            m
        };

        let result = im.put_item(
            "TestTable",
            &new_item,
            false,
            Some("status = :val"),
            None,
            Some(&expr_values),
        );
        assert!(result.is_err());
        match result.unwrap_err() {
            ItemError::ConditionCheckFailed(_) => {}
            _ => panic!("Expected ConditionCheckFailed error"),
        }
    }

    #[test]
    fn test_update_item_with_condition_success() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("active"));
            i.insert("count".to_string(), AttributeValue::n("5"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        let expr_values = {
            let mut m = HashMap::new();
            m.insert("newStatus".to_string(), AttributeValue::s("updated"));
            m.insert("val".to_string(), AttributeValue::n("3"));
            m
        };

        // Update with condition that count > 3
        let result = im.update_item(
            "TestTable",
            &key,
            Some("SET status = :newStatus"),
            Some(&expr_values),
            "ALL_NEW",
            Some("count > :val"),
            None,
        );
        assert!(result.is_ok());
        let (new_item, _) = result.unwrap();
        assert_eq!(new_item.unwrap().get("status").unwrap().as_s(), Some("updated"));
    }

    #[test]
    fn test_update_item_with_condition_failure() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("count".to_string(), AttributeValue::n("5"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        let expr_values = {
            let mut m = HashMap::new();
            m.insert("newStatus".to_string(), AttributeValue::s("updated"));
            m.insert("val".to_string(), AttributeValue::n("10"));
            m
        };

        // Update with condition that count > 10 (should fail)
        let result = im.update_item(
            "TestTable",
            &key,
            Some("SET status = :newStatus"),
            Some(&expr_values),
            "NONE",
            Some("count > :val"),
            None,
        );
        assert!(result.is_err());
        match result.unwrap_err() {
            ItemError::ConditionCheckFailed(_) => {}
            _ => panic!("Expected ConditionCheckFailed error"),
        }
    }

    #[test]
    fn test_delete_item_with_condition_success() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("deleted"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        let expr_values = {
            let mut m = HashMap::new();
            m.insert("val".to_string(), AttributeValue::s("deleted"));
            m
        };

        // Delete with condition that status = "deleted"
        let result = im.delete_item(
            "TestTable",
            &key,
            false,
            Some("status = :val"),
            None,
            Some(&expr_values),
        );
        assert!(result.is_ok());

        // Verify deletion
        let retrieved = im.get_item("TestTable", &key, true).unwrap();
        assert!(retrieved.is_none());
    }

    #[test]
    fn test_delete_item_with_condition_failure() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("active"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        let expr_values = {
            let mut m = HashMap::new();
            m.insert("val".to_string(), AttributeValue::s("deleted"));
            m
        };

        // Delete with condition that status = "deleted" (should fail)
        let result = im.delete_item(
            "TestTable",
            &key,
            false,
            Some("status = :val"),
            None,
            Some(&expr_values),
        );
        assert!(result.is_err());
        match result.unwrap_err() {
            ItemError::ConditionCheckFailed(_) => {}
            _ => panic!("Expected ConditionCheckFailed error"),
        }

        // Verify item still exists
        let retrieved = im.get_item("TestTable", &key, true).unwrap();
        assert!(retrieved.is_some());
    }

    #[test]
    fn test_attribute_exists_condition() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item with 'name' attribute
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("name".to_string(), AttributeValue::s("John"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        // Update with condition attribute_exists(name) - should succeed
        let result = im.update_item(
            "TestTable",
            &key,
            Some("SET age = :age"),
            Some(&[("age".to_string(), AttributeValue::n("25"))].into_iter().collect()),
            "NONE",
            Some("attribute_exists(name)"),
            None,
        );
        assert!(result.is_ok());

        // Update with condition attribute_exists(nonexistent) - should fail
        let result = im.update_item(
            "TestTable",
            &key,
            Some("SET age = :age"),
            Some(&[("age".to_string(), AttributeValue::n("30"))].into_iter().collect()),
            "NONE",
            Some("attribute_exists(nonexistent)"),
            None,
        );
        assert!(result.is_err());
        match result.unwrap_err() {
            ItemError::ConditionCheckFailed(_) => {}
            _ => panic!("Expected ConditionCheckFailed error"),
        }
    }

    #[test]
    fn test_attribute_not_exists_condition() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item without 'nickname' attribute
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("name".to_string(), AttributeValue::s("John"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        // Conditional put with attribute_not_exists(nickname) - should succeed
        let new_item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("name".to_string(), AttributeValue::s("Jane"));
            i
        };

        let result = im.put_item(
            "TestTable",
            &new_item,
            false,
            Some("attribute_not_exists(nickname)"),
            None,
            None,
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_condition_check_success() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("active"));
            i.insert("version".to_string(), AttributeValue::n("1"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        // ConditionCheck with matching condition - should succeed
        let expr_values = {
            let mut m = HashMap::new();
            m.insert("statusVal".to_string(), AttributeValue::s("active"));
            m
        };

        let result = im.condition_check(
            "TestTable",
            &key,
            "status = :statusVal",
            None,
            Some(&expr_values),
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_condition_check_failure() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("active"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        // ConditionCheck with non-matching condition - should fail
        let expr_values = {
            let mut m = HashMap::new();
            m.insert("statusVal".to_string(), AttributeValue::s("inactive"));
            m
        };

        let result = im.condition_check(
            "TestTable",
            &key,
            "status = :statusVal",
            None,
            Some(&expr_values),
        );
        assert!(result.is_err());
        match result.unwrap_err() {
            ItemError::ConditionCheckFailed(_) => {}
            _ => panic!("Expected ConditionCheckFailed error"),
        }
    }

    #[test]
    fn test_condition_check_item_not_found() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Key for non-existent item
        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("nonexistent"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        // ConditionCheck on non-existent item - should fail
        let result = im.condition_check(
            "TestTable",
            &key,
            "attribute_exists(pk)",
            None,
            None,
        );
        assert!(result.is_err());
        match result.unwrap_err() {
            ItemError::ConditionCheckFailed(_) => {}
            _ => panic!("Expected ConditionCheckFailed error for non-existent item"),
        }
    }

    #[test]
    fn test_condition_check_does_not_modify_item() {
        let (im, tm, _stream_manager, _temp) = setup_test_manager();
        create_test_table(&tm, "TestTable");

        // Put initial item
        let item = {
            let mut i = Item::new();
            i.insert("pk".to_string(), AttributeValue::s("user1"));
            i.insert("sk".to_string(), AttributeValue::s("profile"));
            i.insert("status".to_string(), AttributeValue::s("active"));
            i.insert("counter".to_string(), AttributeValue::n("5"));
            i
        };
        im.put_item("TestTable", &item, false, None, None, None).unwrap();

        let key = {
            let mut k = Item::new();
            k.insert("pk".to_string(), AttributeValue::s("user1"));
            k.insert("sk".to_string(), AttributeValue::s("profile"));
            k
        };

        // ConditionCheck - should not modify the item
        let expr_values = {
            let mut m = HashMap::new();
            m.insert("statusVal".to_string(), AttributeValue::s("active"));
            m
        };

        im.condition_check(
            "TestTable",
            &key,
            "status = :statusVal",
            None,
            Some(&expr_values),
        ).unwrap();

        // Verify item is unchanged
        let retrieved = im.get_item("TestTable", &key, true).unwrap();
        assert!(retrieved.is_some());
        let retrieved = retrieved.unwrap();
        assert_eq!(retrieved.get("status").unwrap().as_s(), Some("active"));
        assert_eq!(retrieved.get("counter").unwrap().as_n(), Some("5"));
    }
}

