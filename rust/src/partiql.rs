//! PartiQL parser and executor for DynamoDB-compatible SQL queries
//!
//! PartiQL is a SQL-compatible query language for DynamoDB.
//! This implementation supports basic SELECT, INSERT, UPDATE, and DELETE statements.

use crate::items::{ItemError, ItemManager};
use crate::models::*;
use crate::storage::StorageError;
use std::collections::HashMap;
use tracing::{debug, error};

/// Error types for PartiQL operations
#[derive(Debug, thiserror::Error)]
pub enum PartiQLError {
    #[error("Parse error: {0}")]
    ParseError(String),
    #[error("Execution error: {0}")]
    ExecutionError(String),
    #[error("Invalid statement: {0}")]
    InvalidStatement(String),
    #[error("Item error: {0}")]
    ItemError(#[from] ItemError),
    #[error("Storage error: {0}")]
    Storage(#[from] StorageError),
}

/// Parsed PartiQL statement types
#[derive(Debug, Clone)]
pub enum ParsedStatement {
    /// SELECT statement
    Select {
        /// Columns to select (empty means SELECT *)
        columns: Vec<String>,
        /// Table name
        table: String,
        /// WHERE clause conditions (column name, operator, parameter index)
        conditions: Vec<WhereCondition>,
    },
    /// INSERT statement
    Insert {
        /// Table name
        table: String,
        /// Item attributes in order (attribute name, value or placeholder index)
        /// If value is None, it means use the parameter at the given index
        attributes: Vec<(String, Option<AttributeValue>, Option<usize>)>,
    },
    /// UPDATE statement
    Update {
        /// Table name
        table: String,
        /// SET clauses (attribute name, parameter index)
        sets: Vec<(String, usize)>,
        /// WHERE clause conditions
        conditions: Vec<WhereCondition>,
    },
    /// DELETE statement
    Delete {
        /// Table name
        table: String,
        /// WHERE clause conditions
        conditions: Vec<WhereCondition>,
    },
}

/// WHERE clause condition
#[derive(Debug, Clone)]
pub struct WhereCondition {
    /// Column name
    pub column: String,
    /// Operator (=, <, >, <=, >=)
    pub operator: String,
    /// Parameter index (0-based) for value lookup
    pub param_index: usize,
}

/// PartiQL execution result
#[derive(Debug, Clone)]
pub enum ExecutionResult {
    /// Items returned from SELECT
    Items(Vec<Item>),
    /// Single item (from INSERT/UPDATE with return values)
    Item(Option<Item>),
    /// Empty result (DELETE, INSERT without return)
    Empty,
}

/// PartiQL parser and executor
pub struct PartiQLEngine;

impl PartiQLEngine {
    /// Create a new PartiQL engine
    pub fn new() -> Self {
        Self
    }

    /// Parse a PartiQL statement
    pub fn parse(statement: &str) -> Result<ParsedStatement, PartiQLError> {
        let trimmed = statement.trim();
        let upper = trimmed.to_uppercase();

        if upper.starts_with("SELECT ") {
            Self::parse_select(trimmed)
        } else if upper.starts_with("INSERT INTO ") {
            Self::parse_insert(trimmed)
        } else if upper.starts_with("UPDATE ") {
            Self::parse_update(trimmed)
        } else if upper.starts_with("DELETE FROM ") {
            Self::parse_delete(trimmed)
        } else {
            Err(PartiQLError::InvalidStatement(
                "Unsupported statement type".to_string(),
            ))
        }
    }

    /// Parse a SELECT statement
    /// Format: SELECT * FROM table [WHERE pk = ? [AND sk = ?]]
    fn parse_select(statement: &str) -> Result<ParsedStatement, PartiQLError> {
        // Remove trailing semicolon if present
        let stmt = statement.trim_end_matches(';');

        // Parse columns between SELECT and FROM
        let from_idx = stmt.to_uppercase().find(" FROM ").ok_or_else(|| {
            PartiQLError::ParseError("Expected FROM clause".to_string())
        })?;

        let columns_part = &stmt[7..from_idx]; // Skip "SELECT "
        let columns: Vec<String> = if columns_part.trim() == "*" {
            vec![] // Empty means SELECT *
        } else {
            columns_part
                .split(',')
                .map(|s| s.trim().to_string())
                .collect()
        };

        // Parse table name and WHERE clause
        let rest = &stmt[from_idx + 6..]; // Skip " FROM "
        let (table, where_clause) = Self::parse_table_and_where(rest)?;

        Ok(ParsedStatement::Select {
            columns,
            table,
            conditions: where_clause,
        })
    }

    /// Parse an INSERT statement
    /// Format: INSERT INTO table VALUE {'pk': ?, 'sk': ?, ...}
    fn parse_insert(statement: &str) -> Result<ParsedStatement, PartiQLError> {
        // Remove trailing semicolon if present
        let stmt = statement.trim_end_matches(';');

        // Extract table name (after "INSERT INTO " and before " VALUE")
        let value_idx = stmt.to_uppercase().find(" VALUE").ok_or_else(|| {
            PartiQLError::ParseError("Expected VALUE clause".to_string())
        })?;

        let table = stmt[12..value_idx].trim().to_string();

        // Parse the JSON-like item structure
        let value_part = &stmt[value_idx + 6..].trim(); // Skip " VALUE"
        let attributes = Self::parse_item_attributes(value_part)?;

        Ok(ParsedStatement::Insert { table, attributes })
    }

    /// Parse an UPDATE statement
    /// Format: UPDATE table SET col = ? [WHERE pk = ?]
    fn parse_update(statement: &str) -> Result<ParsedStatement, PartiQLError> {
        // Remove trailing semicolon if present
        let stmt = statement.trim_end_matches(';');

        // Get table name (after "UPDATE " and before " SET")
        let set_idx = stmt.to_uppercase().find(" SET ").ok_or_else(|| {
            PartiQLError::ParseError("Expected SET clause".to_string())
        })?;

        let table = stmt[7..set_idx].trim().to_string();

        // Parse SET clauses and WHERE clause
        let rest = &stmt[set_idx + 5..]; // Skip " SET "

        // Split into SET part and WHERE part
        let (set_part, where_part) = if let Some(where_idx) = rest.to_uppercase().find(" WHERE ") {
            (&rest[..where_idx], Some(&rest[where_idx + 7..]))
        } else {
            (rest, None)
        };

        // Parse SET assignments
        let mut sets = Vec::new();
        for assignment in set_part.split(',') {
            let parts: Vec<&str> = assignment.splitn(2, '=').collect();
            if parts.len() != 2 {
                return Err(PartiQLError::ParseError(format!(
                    "Invalid SET assignment: {}",
                    assignment
                )));
            }

            let col = parts[0].trim().to_string();
            let val_str = parts[1].trim();

            // Check if it's a parameter placeholder
            if val_str == "?" {
                sets.push((col, sets.len()));
            } else {
                return Err(PartiQLError::ParseError(
                    "Only ? placeholders supported in SET".to_string(),
                ));
            }
        }

        // Parse WHERE conditions
        let conditions = where_part
            .map(Self::parse_where_clause)
            .transpose()?
            .unwrap_or_default();

        Ok(ParsedStatement::Update {
            table,
            sets,
            conditions,
        })
    }

    /// Parse a DELETE statement
    /// Format: DELETE FROM table [WHERE pk = ?]
    fn parse_delete(statement: &str) -> Result<ParsedStatement, PartiQLError> {
        // Remove trailing semicolon if present
        let stmt = statement.trim_end_matches(';');

        // Parse table name and WHERE clause
        let rest = &stmt[12..]; // Skip "DELETE FROM "
        let (table, conditions) = Self::parse_table_and_where(rest)?;

        Ok(ParsedStatement::Delete { table, conditions })
    }

    /// Parse table name and optional WHERE clause
    fn parse_table_and_where(rest: &str) -> Result<(String, Vec<WhereCondition>), PartiQLError> {
        let upper = rest.to_uppercase();

        let (table, where_clause) = if let Some(where_idx) = upper.find(" WHERE ") {
            let table = rest[..where_idx].trim().to_string();
            let where_str = &rest[where_idx + 7..];
            let conditions = Self::parse_where_clause(where_str)?;
            (table, conditions)
        } else {
            (rest.trim().to_string(), vec![])
        };

        Ok((table, where_clause))
    }

    /// Parse WHERE clause conditions
    fn parse_where_clause(where_str: &str) -> Result<Vec<WhereCondition>, PartiQLError> {
        let mut conditions = Vec::new();

        // Split by AND (case insensitive)
        let and_parts: Vec<&str> = where_str.splitn(2, " AND ").collect();
        let pk_condition = and_parts[0].trim();

        // Parse pk condition
        conditions.push(Self::parse_condition(pk_condition, 0)?);

        // Parse sk condition if present
        if and_parts.len() > 1 {
            let sk_condition = and_parts[1].trim();
            conditions.push(Self::parse_condition(sk_condition, 1)?);
        }

        Ok(conditions)
    }

    /// Parse a single condition (column = ?)
    fn parse_condition(cond_str: &str, param_index: usize) -> Result<WhereCondition, PartiQLError> {
        // Support operators: =, <, >, <=, >=
        let operators = ["=", "<=", ">=", "<", ">"];

        for op in &operators {
            if let Some(op_idx) = cond_str.find(op) {
                let column = cond_str[..op_idx].trim().to_string();
                let value_part = cond_str[op_idx + op.len()..].trim();

                if value_part != "?" {
                    return Err(PartiQLError::ParseError(
                        "Only ? placeholders supported in WHERE".to_string(),
                    ));
                }

                return Ok(WhereCondition {
                    column,
                    operator: op.to_string(),
                    param_index,
                });
            }
        }

        Err(PartiQLError::ParseError(format!(
            "Invalid condition: {}",
            cond_str
        )))
    }

    /// Parse item attributes from PartiQL syntax
    /// Format: {'pk': ?, 'sk': ?, 'data': ?}
    /// Returns a vector of (key, value, param_index) tuples in order
    fn parse_item_attributes(value_str: &str) -> Result<Vec<(String, Option<AttributeValue>, Option<usize>)>, PartiQLError> {
        let mut attributes = Vec::new();
        let trimmed = value_str.trim();

        // Check for braces
        if !trimmed.starts_with('{') || !trimmed.ends_with('}') {
            return Err(PartiQLError::ParseError(
                "Item value must be enclosed in {}".to_string(),
            ));
        }

        // Remove braces and parse key-value pairs
        let inner = &trimmed[1..trimmed.len() - 1];

        if inner.trim().is_empty() {
            return Ok(attributes);
        }

        // Split by commas (not inside quotes)
        let pairs = Self::split_pairs(inner);
        let mut param_idx = 0;

        for pair in pairs.iter() {
            let kv: Vec<&str> = pair.splitn(2, ':').collect();
            if kv.len() != 2 {
                return Err(PartiQLError::ParseError(format!(
                    "Invalid key-value pair: {}",
                    pair
                )));
            }

            let key = kv[0].trim().trim_matches('\'').trim_matches('"').to_string();
            let value_str = kv[1].trim();

            // For now, only support ? placeholders
            if value_str == "?" {
                // Store a placeholder with parameter index
                attributes.push((key, None, Some(param_idx)));
                param_idx += 1;
            } else if value_str.starts_with('\'') || value_str.starts_with('"') {
                // Literal string value
                let value = value_str
                    .trim_matches('\'')
                    .trim_matches('"')
                    .to_string();
                attributes.push((key, Some(AttributeValue::s(value)), None));
            } else if value_str.parse::<f64>().is_ok() {
                // Numeric literal
                attributes.push((key, Some(AttributeValue::n(value_str.to_string())), None));
            } else {
                return Err(PartiQLError::ParseError(format!(
                    "Unsupported value: {}",
                    value_str
                )));
            }
        }

        Ok(attributes)
    }

    /// Split comma-separated pairs respecting quotes
    fn split_pairs(s: &str) -> Vec<String> {
        let mut result = Vec::new();
        let mut current = String::new();
        let mut in_quotes = false;
        let mut quote_char = '\0';

        for c in s.chars() {
            match c {
                '\'' | '"' if !in_quotes => {
                    in_quotes = true;
                    quote_char = c;
                    current.push(c);
                }
                c if in_quotes && c == quote_char => {
                    in_quotes = false;
                    current.push(c);
                }
                ',' if !in_quotes => {
                    result.push(current.trim().to_string());
                    current.clear();
                }
                _ => current.push(c),
            }
        }

        if !current.is_empty() {
            result.push(current.trim().to_string());
        }

        result
    }

    /// Execute a parsed PartiQL statement
    pub fn execute(
        &self,
        statement: &ParsedStatement,
        parameters: Option<&Vec<AttributeValue>>,
        item_manager: &ItemManager,
        _consistent_read: bool,
    ) -> Result<ExecutionResult, PartiQLError> {
        let empty_params: Vec<AttributeValue> = vec![];
        let params = parameters.unwrap_or(&empty_params);

        match statement {
            ParsedStatement::Select {
                columns,
                table,
                conditions,
            } => {
                self.execute_select(table, columns, conditions, params, item_manager)
            }
            ParsedStatement::Insert { table, attributes } => {
                self.execute_insert(table, attributes, params, item_manager)
            }
            ParsedStatement::Update {
                table,
                sets,
                conditions,
            } => {
                self.execute_update(table, sets, conditions, params, item_manager)
            }
            ParsedStatement::Delete { table, conditions } => {
                self.execute_delete(table, conditions, params, item_manager)
            }
        }
    }

    /// Execute a SELECT statement
    fn execute_select(
        &self,
        table: &str,
        columns: &[String],
        conditions: &[WhereCondition],
        params: &[AttributeValue],
        item_manager: &ItemManager,
    ) -> Result<ExecutionResult, PartiQLError> {
        debug!("Executing SELECT from table: {}", table);

        // Build key for GetItem from conditions
        let key = self.build_key_from_conditions(conditions, params)?;

        // If we have both pk and sk, use GetItem
        // Otherwise, we would need to use Query (for just pk) or Scan (no conditions)
        // For simplicity, we'll use GetItem when possible, otherwise fallback to scan
        let items = if key.len() >= 1 {
            // Try to get specific item(s)
            match item_manager.get_item(table, &key, false) {
                Ok(Some(item)) => vec![item],
                Ok(None) => vec![],
                Err(e) => return Err(PartiQLError::ItemError(e)),
            }
        } else {
            // Scan all items (simplified - in production would use Query)
            match item_manager.scan(table, None, None, None, None, None, None) {
                Ok((items, _, _, _)) => items,
                Err(e) => return Err(PartiQLError::ItemError(e)),
            }
        };

        // Apply column projection if specified
        let projected_items = if columns.is_empty() {
            items
        } else {
            items
                .into_iter()
                .map(|item| {
                    let mut projected = Item::new();
                    for col in columns {
                        if let Some(val) = item.get(col) {
                            projected.insert(col.clone(), val.clone());
                        }
                    }
                    projected
                })
                .collect()
        };

        Ok(ExecutionResult::Items(projected_items))
    }

    /// Execute an INSERT statement
    fn execute_insert(
        &self,
        table: &str,
        attributes: &[(String, Option<AttributeValue>, Option<usize>)],
        params: &[AttributeValue],
        item_manager: &ItemManager,
    ) -> Result<ExecutionResult, PartiQLError> {
        debug!("Executing INSERT into table: {}", table);

        // Build the item by substituting parameters
        let mut item = Item::new();

        for (key, literal_value, param_idx) in attributes {
            if let Some(idx) = param_idx {
                // This is a placeholder, substitute with the corresponding parameter
                if *idx < params.len() {
                    item.insert(key.clone(), params[*idx].clone());
                } else {
                    return Err(PartiQLError::ExecutionError(format!(
                        "Missing parameter at index {}",
                        idx
                    )));
                }
            } else if let Some(val) = literal_value {
                // Literal value, use as is
                item.insert(key.clone(), val.clone());
            }
        }

        // Execute put_item
        match item_manager.put_item(table, &item, false, None, None, None) {
            Ok(_) => Ok(ExecutionResult::Empty),
            Err(e) => Err(PartiQLError::ItemError(e)),
        }
    }

    /// Execute an UPDATE statement
    fn execute_update(
        &self,
        table: &str,
        sets: &[(String, usize)],
        conditions: &[WhereCondition],
        params: &[AttributeValue],
        item_manager: &ItemManager,
    ) -> Result<ExecutionResult, PartiQLError> {
        debug!("Executing UPDATE on table: {}", table);

        // Build key from conditions
        let key = self.build_key_from_conditions(conditions, params)?;

        // Build update expression
        let mut update_parts = Vec::new();
        let mut expression_values = HashMap::new();

        for (i, (col, param_idx)) in sets.iter().enumerate() {
            let val_key = format!("val{}", i);
            update_parts.push(format!("SET {} = :{}", col, val_key));

            // Get value from parameters (offset by condition parameters)
            let offset_param_idx = conditions.len() + *param_idx;
            if offset_param_idx < params.len() {
                expression_values.insert(val_key, params[offset_param_idx].clone());
            }
        }

        let update_expression = update_parts.join(", ");

        // Execute update_item
        match item_manager.update_item(
            table,
            &key,
            Some(&update_expression),
            Some(&expression_values),
            "NONE",
            None,
            None,
        ) {
            Ok((new_item, _)) => Ok(ExecutionResult::Item(new_item)),
            Err(e) => Err(PartiQLError::ItemError(e)),
        }
    }

    /// Execute a DELETE statement
    fn execute_delete(
        &self,
        table: &str,
        conditions: &[WhereCondition],
        params: &[AttributeValue],
        item_manager: &ItemManager,
    ) -> Result<ExecutionResult, PartiQLError> {
        debug!("Executing DELETE from table: {}", table);

        // Build key from conditions
        let key = self.build_key_from_conditions(conditions, params)?;

        // Execute delete_item
        match item_manager.delete_item(table, &key, false, None, None, None) {
            Ok(_) => Ok(ExecutionResult::Empty),
            Err(e) => Err(PartiQLError::ItemError(e)),
        }
    }

    /// Build a key Item from WHERE conditions and parameters
    fn build_key_from_conditions(
        &self,
        conditions: &[WhereCondition],
        params: &[AttributeValue],
    ) -> Result<Item, PartiQLError> {
        let mut key = Item::new();

        for cond in conditions {
            if cond.param_index < params.len() {
                key.insert(cond.column.clone(), params[cond.param_index].clone());
            } else {
                return Err(PartiQLError::ExecutionError(format!(
                    "Missing parameter at index {}",
                    cond.param_index
                )));
            }
        }

        Ok(key)
    }
}

impl Default for PartiQLEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::items::ItemManager;
    use crate::models::{AttributeDefinition, DynamoDBRequest, KeySchemaElement};
    use crate::storage::TableManager;
    use std::sync::Arc;
    use tempfile::TempDir;

    fn setup_test() -> (PartiQLEngine, Arc<ItemManager>, Arc<TableManager>, TempDir) {
        let temp_dir = TempDir::new().unwrap();
        let table_manager = Arc::new(
            TableManager::new(temp_dir.path(), "test").unwrap()
        );
        let item_manager = Arc::new(ItemManager::new(table_manager.clone()));
        let engine = PartiQLEngine::new();
        (engine, item_manager, table_manager, temp_dir)
    }

    fn create_test_table(tm: &TableManager, name: &str) {
        let req = DynamoDBRequest {
            table_name: Some(name.to_string()),
            key_schema: Some(vec![
                KeySchemaElement::hash("pk"),
            ]),
            attribute_definitions: Some(vec![
                AttributeDefinition::s("pk"),
            ]),
            billing_mode: Some("PAY_PER_REQUEST".to_string()),
            ..Default::default()
        };
        tm.create_table(&req).unwrap();
    }

    #[test]
    fn test_parse_select_star() {
        let stmt = "SELECT * FROM users WHERE pk = ?";
        let parsed = PartiQLEngine::parse(stmt).unwrap();

        match parsed {
            ParsedStatement::Select { columns, table, conditions } => {
                assert!(columns.is_empty());
                assert_eq!(table, "users");
                assert_eq!(conditions.len(), 1);
                assert_eq!(conditions[0].column, "pk");
                assert_eq!(conditions[0].operator, "=");
            }
            _ => panic!("Expected Select statement"),
        }
    }

    #[test]
    fn test_parse_select_columns() {
        let stmt = "SELECT name, email FROM users WHERE pk = ?";
        let parsed = PartiQLEngine::parse(stmt).unwrap();

        match parsed {
            ParsedStatement::Select { columns, table, .. } => {
                assert_eq!(columns, vec!["name", "email"]);
                assert_eq!(table, "users");
            }
            _ => panic!("Expected Select statement"),
        }
    }

    #[test]
    fn test_parse_insert() {
        let stmt = "INSERT INTO users VALUE {'pk': ?, 'name': ?}";
        let parsed = PartiQLEngine::parse(stmt).unwrap();

        match parsed {
            ParsedStatement::Insert { table, attributes } => {
                assert_eq!(table, "users");
                assert_eq!(attributes.len(), 2);
                assert_eq!(attributes[0].0, "pk");
                assert_eq!(attributes[0].2, Some(0)); // First placeholder
                assert_eq!(attributes[1].0, "name");
                assert_eq!(attributes[1].2, Some(1)); // Second placeholder
            }
            _ => panic!("Expected Insert statement"),
        }
    }

    #[test]
    fn test_parse_update() {
        let stmt = "UPDATE users SET name = ? WHERE pk = ?";
        let parsed = PartiQLEngine::parse(stmt).unwrap();

        match parsed {
            ParsedStatement::Update { table, sets, conditions } => {
                assert_eq!(table, "users");
                assert_eq!(sets.len(), 1);
                assert_eq!(sets[0].0, "name");
                assert_eq!(conditions.len(), 1);
                assert_eq!(conditions[0].column, "pk");
            }
            _ => panic!("Expected Update statement"),
        }
    }

    #[test]
    fn test_parse_delete() {
        let stmt = "DELETE FROM users WHERE pk = ?";
        let parsed = PartiQLEngine::parse(stmt).unwrap();

        match parsed {
            ParsedStatement::Delete { table, conditions } => {
                assert_eq!(table, "users");
                assert_eq!(conditions.len(), 1);
                assert_eq!(conditions[0].column, "pk");
            }
            _ => panic!("Expected Delete statement"),
        }
    }

    #[test]
    fn test_parse_select_with_pk_and_sk() {
        let stmt = "SELECT * FROM users WHERE pk = ? AND sk = ?";
        let parsed = PartiQLEngine::parse(stmt).unwrap();

        match parsed {
            ParsedStatement::Select { conditions, .. } => {
                assert_eq!(conditions.len(), 2);
                assert_eq!(conditions[0].column, "pk");
                assert_eq!(conditions[1].column, "sk");
            }
            _ => panic!("Expected Select statement"),
        }
    }

    #[test]
    fn test_execute_insert_and_select() {
        let (engine, item_manager, table_manager, _temp) = setup_test();
        create_test_table(&table_manager, "TestTable");

        // Insert an item
        let insert_stmt = "INSERT INTO TestTable VALUE {'pk': ?, 'name': ?}";
        let parsed = PartiQLEngine::parse(insert_stmt).unwrap();
        let params = vec![
            AttributeValue::s("user1"),
            AttributeValue::s("John"),
        ];

        let result = engine.execute(&parsed, Some(&params), &item_manager, false);
        assert!(result.is_ok());

        // Select the item
        let select_stmt = "SELECT * FROM TestTable WHERE pk = ?";
        let parsed = PartiQLEngine::parse(select_stmt).unwrap();
        let params = vec![AttributeValue::s("user1")];

        let result = engine.execute(&parsed, Some(&params), &item_manager, false).unwrap();
        match result {
            ExecutionResult::Items(items) => {
                assert_eq!(items.len(), 1);
                assert_eq!(items[0].get("pk").unwrap().as_s(), Some("user1"));
                assert_eq!(items[0].get("name").unwrap().as_s(), Some("John"));
            }
            _ => panic!("Expected Items result"),
        }
    }

    #[test]
    fn test_execute_delete() {
        let (engine, item_manager, table_manager, _temp) = setup_test();
        create_test_table(&table_manager, "TestTable");

        // Insert an item
        let insert_stmt = "INSERT INTO TestTable VALUE {'pk': ?, 'name': ?}";
        let parsed = PartiQLEngine::parse(insert_stmt).unwrap();
        let params = vec![
            AttributeValue::s("user1"),
            AttributeValue::s("John"),
        ];
        engine.execute(&parsed, Some(&params), &item_manager, false).unwrap();

        // Delete the item
        let delete_stmt = "DELETE FROM TestTable WHERE pk = ?";
        let parsed = PartiQLEngine::parse(delete_stmt).unwrap();
        let params = vec![AttributeValue::s("user1")];
        engine.execute(&parsed, Some(&params), &item_manager, false).unwrap();

        // Verify item is deleted
        let select_stmt = "SELECT * FROM TestTable WHERE pk = ?";
        let parsed = PartiQLEngine::parse(select_stmt).unwrap();
        let params = vec![AttributeValue::s("user1")];

        let result = engine.execute(&parsed, Some(&params), &item_manager, false).unwrap();
        match result {
            ExecutionResult::Items(items) => {
                assert!(items.is_empty());
            }
            _ => panic!("Expected Items result"),
        }
    }

    #[test]
    fn test_execute_select_with_projection() {
        let (engine, item_manager, table_manager, _temp) = setup_test();
        create_test_table(&table_manager, "TestTable");

        // Insert an item
        let insert_stmt = "INSERT INTO TestTable VALUE {'pk': ?, 'name': ?, 'email': ?}";
        let parsed = PartiQLEngine::parse(insert_stmt).unwrap();
        let params = vec![
            AttributeValue::s("user1"),
            AttributeValue::s("John"),
            AttributeValue::s("john@example.com"),
        ];
        engine.execute(&parsed, Some(&params), &item_manager, false).unwrap();

        // Select with column projection
        let select_stmt = "SELECT pk, name FROM TestTable WHERE pk = ?";
        let parsed = PartiQLEngine::parse(select_stmt).unwrap();
        let params = vec![AttributeValue::s("user1")];

        let result = engine.execute(&parsed, Some(&params), &item_manager, false).unwrap();
        match result {
            ExecutionResult::Items(items) => {
                assert_eq!(items.len(), 1);
                assert!(items[0].contains_key("pk"));
                assert!(items[0].contains_key("name"));
                // email should not be in the result due to projection
            }
            _ => panic!("Expected Items result"),
        }
    }
}
