//! HTTP handlers for DynamoDB API operations

use crate::items::{ItemError, ItemManager};
use crate::models::*;
use crate::storage::{StorageError, TableManager};
use axum::{
    extract::State,
    http::{HeaderMap, StatusCode},
    response::Json,
};
use std::sync::Arc;
use tracing::{error, info, warn};

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub table_manager: Arc<TableManager>,
    pub item_manager: Arc<ItemManager>,
}

/// Main DynamoDB API handler
pub async fn dynamodb_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(request): Json<DynamoDBRequest>,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    // Get X-Amz-Target header
    let amz_target = headers
        .get("x-amz-target")
        .and_then(|v| v.to_str().ok())
        .ok_or_else(|| {
            (
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(
                    "Missing X-Amz-Target header",
                )),
            )
        })?;

    // Extract operation name
    let operation = amz_target
        .split('.')
        .last()
        .unwrap_or(amz_target);

    info!("Processing operation: {}", operation);

    // Route to appropriate handler
    match operation {
        // Control plane operations
        "CreateTable" => handle_create_table(state, request).await,
        "DeleteTable" => handle_delete_table(state, request).await,
        "ListTables" => handle_list_tables(state).await,
        "DescribeTable" => handle_describe_table(state, request).await,
        "TagResource" => handle_tag_resource(state, request).await,
        "UntagResource" => handle_untag_resource(state, request).await,
        "ListTagsOfResource" => handle_list_tags_of_resource(state, request).await,
        "DescribeEndpoints" => handle_describe_endpoints().await,
        // Data plane operations
        "GetItem" => handle_get_item(state, request).await,
        "PutItem" => handle_put_item(state, request).await,
        "UpdateItem" => handle_update_item(state, request).await,
        "DeleteItem" => handle_delete_item(state, request).await,
        "Query" => handle_query(state, request).await,
        "Scan" => handle_scan(state, request).await,
        _ => {
            warn!("Unknown operation: {}", operation);
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Unknown operation: {}",
                    operation
                ))),
            ))
        }
    }
}

/// Health check handler
pub async fn health_check() -> &'static str {
    "healthy"
}

// ==================== Control Plane Handlers ====================

/// Handle CreateTable operation
async fn handle_create_table(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    if request.table_name.is_none() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        ));
    }

    if request.key_schema.is_none() || request.key_schema.as_ref().unwrap().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("KeySchema is required")),
        ));
    }

    match state.table_manager.create_table(&request) {
        Ok(metadata) => {
            info!("Created table: {}", metadata.table_name);
            Ok(Json(DynamoDBResponse {
                table_description: Some(metadata),
                ..Default::default()
            }))
        }
        Err(StorageError::TableAlreadyExists(name)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_in_use(format!(
                    "Table already exists: {}",
                    name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to create table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DeleteTable operation
async fn handle_delete_table(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    match state.table_manager.delete_table(&table_name) {
        Ok(Some(metadata)) => {
            info!("Deleted table: {}", table_name);
            Ok(Json(DynamoDBResponse {
                table_description: Some(metadata),
                ..Default::default()
            }))
        }
        Ok(None) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to delete table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle ListTables operation
async fn handle_list_tables(
    state: AppState,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.list_tables() {
        Ok(tables) => {
            info!("Listed {} tables", tables.len());
            Ok(Json(DynamoDBResponse {
                table_names: Some(tables),
                ..Default::default()
            }))
        }
        Err(e) => {
            error!("Failed to list tables: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeTable operation
async fn handle_describe_table(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    match state.table_manager.describe_table(&table_name) {
        Ok(metadata) => {
            Ok(Json(DynamoDBResponse {
                table: Some(metadata),
                ..Default::default()
            }))
        }
        Err(StorageError::TableNotFound(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to describe table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle TagResource operation
async fn handle_tag_resource(
    _state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let resource_arn = request.resource_arn.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Resource ARN is required")),
        )
    })?;

    let _table_name = extract_table_name_from_arn(&resource_arn).ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Invalid resource ARN")),
        )
    })?;

    info!("TagResource not yet implemented");
    Ok(Json(DynamoDBResponse::default()))
}

/// Handle UntagResource operation
async fn handle_untag_resource(
    _state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let resource_arn = request.resource_arn.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Resource ARN is required")),
        )
    })?;

    let _table_name = extract_table_name_from_arn(&resource_arn).ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Invalid resource ARN")),
        )
    })?;

    info!("UntagResource not yet implemented");
    Ok(Json(DynamoDBResponse::default()))
}

/// Handle ListTagsOfResource operation
async fn handle_list_tags_of_resource(
    _state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let resource_arn = request.resource_arn.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Resource ARN is required")),
        )
    })?;

    let _table_name = extract_table_name_from_arn(&resource_arn).ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Invalid resource ARN")),
        )
    })?;

    info!("ListTagsOfResource not yet implemented");
    Ok(Json(DynamoDBResponse {
        tags: Some(Vec::new()),
        ..Default::default()
    }))
}

/// Handle DescribeEndpoints operation
async fn handle_describe_endpoints() -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    Ok(Json(DynamoDBResponse {
        endpoints: Some(vec![
            Endpoint {
                address: "localhost:8000".to_string(),
                cache_period_in_minutes: 1440,
            },
        ]),
        ..Default::default()
    }))
}

// ==================== Data Plane Handlers ====================

/// Handle GetItem operation
async fn handle_get_item(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    let key = request.key.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Key is required")),
        )
    })?;

    let consistent_read = request.consistent_read.unwrap_or(false);

    match state.item_manager.get_item(&table_name, &key, consistent_read) {
        Ok(item) => {
            Ok(Json(DynamoDBResponse {
                item,
                ..Default::default()
            }))
        }
        Err(ItemError::Storage(StorageError::TableNotFound(_))) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to get item: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle PutItem operation
async fn handle_put_item(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    let item = request.item.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Item is required")),
        )
    })?;

    let return_values = request.return_values.as_deref().unwrap_or("NONE");
    let return_old = return_values == "ALL_OLD";

    match state.item_manager.put_item(&table_name, &item, return_old) {
        Ok(old_item) => {
            let response = if return_values == "ALL_OLD" {
                DynamoDBResponse {
                    attributes: old_item,
                    ..Default::default()
                }
            } else {
                DynamoDBResponse::default()
            };
            Ok(Json(response))
        }
        Err(ItemError::Storage(StorageError::TableNotFound(_))) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to put item: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle UpdateItem operation
async fn handle_update_item(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    let key = request.key.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Key is required")),
        )
    })?;

    let return_values = request.return_values.as_deref().unwrap_or("NONE");
    let update_expression = request.update_expression.as_deref();
    let expression_values = request.expression_attribute_values.as_ref();

    match state.item_manager.update_item(
        &table_name,
        &key,
        update_expression,
        expression_values,
        return_values,
    ) {
        Ok((new_item, old_item)) => {
            let response = match return_values {
                "ALL_NEW" => DynamoDBResponse {
                    attributes: new_item,
                    ..Default::default()
                },
                "ALL_OLD" => DynamoDBResponse {
                    attributes: old_item,
                    ..Default::default()
                },
                _ => DynamoDBResponse::default(),
            };
            Ok(Json(response))
        }
        Err(ItemError::Storage(StorageError::TableNotFound(_))) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to update item: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DeleteItem operation
async fn handle_delete_item(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    let key = request.key.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Key is required")),
        )
    })?;

    let return_values = request.return_values.as_deref().unwrap_or("NONE");
    let return_old = return_values == "ALL_OLD";

    match state.item_manager.delete_item(&table_name, &key, return_old) {
        Ok(old_item) => {
            let response = if return_values == "ALL_OLD" {
                DynamoDBResponse {
                    attributes: old_item,
                    ..Default::default()
                }
            } else {
                DynamoDBResponse::default()
            };
            Ok(Json(response))
        }
        Err(ItemError::Storage(StorageError::TableNotFound(_))) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to delete item: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle Query operation
async fn handle_query(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    // Extract partition key value from key condition expression
    // This is a simplified implementation
    let partition_key_value = request
        .expression_attribute_values
        .as_ref()
        .and_then(|vals| vals.get(":pk"))
        .and_then(|attr| attr.as_s())
        .map(|s| s.to_string())
        .or_else(|| {
            // Try to extract from key condition expression
            request.key_condition_expression.as_ref().and_then(|expr| {
                // Simple extraction - look for = :value pattern
                expr.split("=").nth(1).map(|s| s.trim().trim_start_matches(':').to_string())
            })
        })
        .ok_or_else(|| {
            (
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception("Partition key condition is required")),
            )
        })?;

    let index_name = request.index_name.as_deref();
    let scan_index_forward = request.scan_index_forward.unwrap_or(true);
    let limit = request.limit;

    match state.item_manager.query(
        &table_name,
        index_name,
        &partition_key_value,
        None, // key_conditions - simplified
        scan_index_forward,
        limit,
    ) {
        Ok((items, last_key)) => {
            Ok(Json(DynamoDBResponse {
                items: Some(items),
                count: Some(request.limit.unwrap_or(0)),
                scanned_count: Some(request.limit.unwrap_or(0)),
                last_evaluated_key: last_key,
                ..Default::default()
            }))
        }
        Err(ItemError::Storage(StorageError::TableNotFound(_))) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to query items: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle Scan operation
async fn handle_scan(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    let index_name = request.index_name.as_deref();
    let limit = request.limit;
    let exclusive_start_key = request.exclusive_start_key.as_ref();

    match state.item_manager.scan(&table_name, index_name, limit, exclusive_start_key) {
        Ok((items, last_key)) => {
            let count = items.len() as i32;
            Ok(Json(DynamoDBResponse {
                items: Some(items),
                count: Some(count),
                scanned_count: Some(count),
                last_evaluated_key: last_key,
                ..Default::default()
            }))
        }
        Err(ItemError::Storage(StorageError::TableNotFound(_))) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to scan items: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Extract table name from ARN
fn extract_table_name_from_arn(arn: &str) -> Option<String> {
    if !arn.starts_with("arn:aws:dynamodb:") {
        return None;
    }

    arn.split('/').last().map(|s| s.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_table_name_from_arn() {
        let arn = "arn:aws:dynamodb:local:000000000000:table/TestTable";
        assert_eq!(
            extract_table_name_from_arn(arn),
            Some("TestTable".to_string())
        );

        assert_eq!(extract_table_name_from_arn("invalid"), None);
    }
}
