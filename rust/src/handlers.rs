//! HTTP handlers for DynamoDB API operations

use crate::items::{ItemError, ItemManager};
use crate::models::*;
use crate::storage::{StorageError, TableManager};
use axum::{
    body::Bytes,
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
    body: Bytes,
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

    // Parse body based on operation type
    match operation {
        // PITR operations
        "UpdateContinuousBackups" => {
            let request: UpdateContinuousBackupsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_update_continuous_backups(state, request).await
        }
        "DescribeContinuousBackups" => {
            let request: DescribeContinuousBackupsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_continuous_backups(state, request).await
        }
        "RestoreTableToPointInTime" => {
            let request: RestoreTableToPointInTimeRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_restore_table_to_point_in_time(state, request).await
        }
        // Backup/Restore operations
        "CreateBackup" => {
            let request: CreateBackupRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_create_backup(state, request).await
        }
        "DescribeBackup" => {
            let request: DescribeBackupRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_backup(state, request).await
        }
        "ListBackups" => {
            let request: ListBackupsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_list_backups(state, request).await
        }
        "DeleteBackup" => {
            let request: DeleteBackupRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_delete_backup(state, request).await
        }
        "RestoreTableFromBackup" => {
            let request: RestoreTableFromBackupRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_restore_table_from_backup(state, request).await
        }
        // TTL operations
        "UpdateTimeToLive" => {
            let request: UpdateTimeToLiveRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_update_time_to_live(state, request).await
        }
        "DescribeTimeToLive" => {
            let request: DescribeTimeToLiveRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_time_to_live(state, request).await
        }
        // Batch operations need special parsing
        "BatchGetItem" => {
            let request: BatchGetItemRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_batch_get_item(state, request).await
        }
        "BatchWriteItem" => {
            let request: BatchWriteItemRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_batch_write_item(state, request).await
        }
        // Transaction operations
        "TransactGetItems" => {
            let request: TransactGetItemsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_transact_get_items(state, request).await
        }
        "TransactWriteItems" => {
            let request: TransactWriteItemsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_transact_write_items(state, request).await
        }
        // All other operations use DynamoDBRequest
        _ => {
            let request: DynamoDBRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            
            // Route to appropriate handler
            match operation {
                // Control plane operations
                "CreateTable" => handle_create_table(state, request).await,
                "DeleteTable" => handle_delete_table(state, request).await,
                "ListTables" => handle_list_tables(state).await,
                "DescribeTable" => handle_describe_table(state, request).await,
                "UpdateTable" => handle_update_table(state, request).await,
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

/// Handle UpdateTable operation
async fn handle_update_table(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Table name is required")),
        )
    })?;

    let update_request = UpdateTableRequest {
        table_name,
        attribute_definitions: request.attribute_definitions,
        billing_mode: request.billing_mode,
        global_secondary_index_updates: None, // Will be parsed from raw request in full implementation
        provisioned_throughput: request.provisioned_throughput,
    };

    match state.table_manager.update_table(&update_request) {
        Ok(metadata) => {
            info!("Updated table: {}", metadata.table_name);
            Ok(Json(DynamoDBResponse {
                table_description: Some(metadata),
                ..Default::default()
            }))
        }
        Err(StorageError::TableNotFound(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    update_request.table_name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to update table: {}", e);
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(e.to_string())),
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

/// Handle UpdateTimeToLive operation
async fn handle_update_time_to_live(
    state: AppState,
    request: UpdateTimeToLiveRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name;

    match state
        .table_manager
        .update_time_to_live(&table_name, &request.time_to_live_specification)
    {
        Ok(description) => {
            info!(
                "Updated TTL for table {}: enabled={}, attribute={}",
                table_name,
                request.time_to_live_specification.enabled,
                request.time_to_live_specification.attribute_name
            );
            Ok(Json(DynamoDBResponse {
                time_to_live_description: Some(description),
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
            error!("Failed to update TTL for table {}: {}", table_name, e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeTimeToLive operation
async fn handle_describe_time_to_live(
    state: AppState,
    request: DescribeTimeToLiveRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name;

    match state.table_manager.describe_time_to_live(&table_name) {
        Ok(description) => {
            info!("Described TTL for table {}: status={}", table_name, description.time_to_live_status);
            Ok(Json(DynamoDBResponse {
                time_to_live_description: Some(description),
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
            error!("Failed to describe TTL for table {}: {}", table_name, e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
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
    let condition_expression = request.condition_expression.as_deref();
    let expression_names = request.expression_attribute_names.as_ref();
    let expression_values = request.expression_attribute_values.as_ref();

    match state.item_manager.put_item(
        &table_name,
        &item,
        return_old,
        condition_expression,
        expression_names,
        expression_values,
    ) {
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
        Err(ItemError::ConditionCheckFailed(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::conditional_check_failed(
                    "The conditional request failed",
                )),
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
    let condition_expression = request.condition_expression.as_deref();
    let expression_names = request.expression_attribute_names.as_ref();

    match state.item_manager.update_item(
        &table_name,
        &key,
        update_expression,
        expression_values,
        return_values,
        condition_expression,
        expression_names,
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
        Err(ItemError::ConditionCheckFailed(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::conditional_check_failed(
                    "The conditional request failed",
                )),
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
    let condition_expression = request.condition_expression.as_deref();
    let expression_names = request.expression_attribute_names.as_ref();
    let expression_values = request.expression_attribute_values.as_ref();

    match state.item_manager.delete_item(
        &table_name,
        &key,
        return_old,
        condition_expression,
        expression_names,
        expression_values,
    ) {
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
        Err(ItemError::ConditionCheckFailed(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::conditional_check_failed(
                    "The conditional request failed",
                )),
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

// ==================== Batch Operation Handlers ====================

/// Handle BatchGetItem operation
async fn handle_batch_get_item(
    state: AppState,
    request: BatchGetItemRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let request_items = request.request_items;

    // Validate that at least one table is specified
    if request_items.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "At least one table must be specified in RequestItems",
            )),
        ));
    }

    // Validate the 100 item limit
    let total_keys: usize = request_items.values().map(|k| k.keys.len()).sum();
    if total_keys > 100 {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "BatchGetItem can retrieve up to 100 items per operation",
            )),
        ));
    }

    match state.item_manager.batch_get_item(&request_items) {
        Ok((responses, unprocessed)) => {
            Ok(Json(DynamoDBResponse {
                batch_responses: Some(responses),
                unprocessed_keys: if unprocessed.is_empty() {
                    None
                } else {
                    Some(unprocessed)
                },
                ..Default::default()
            }))
        }
        Err(ItemError::InvalidKey(msg)) => Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(msg)),
        )),
        Err(e) => {
            error!("Failed to batch get items: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle BatchWriteItem operation
async fn handle_batch_write_item(
    state: AppState,
    request: BatchWriteItemRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let request_items = request.request_items;

    // Validate that at least one table is specified
    if request_items.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "At least one table must be specified in RequestItems",
            )),
        ));
    }

    // Validate the 25 item limit
    let total_items: usize = request_items.values().map(|v| v.len()).sum();
    if total_items > 25 {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "BatchWriteItem can write up to 25 items per operation",
            )),
        ));
    }

    match state.item_manager.batch_write_item(&request_items) {
        Ok(unprocessed) => {
            Ok(Json(DynamoDBResponse {
                unprocessed_items: if unprocessed.is_empty() {
                    None
                } else {
                    Some(unprocessed)
                },
                ..Default::default()
            }))
        }
        Err(ItemError::InvalidKey(msg)) => Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(msg)),
        )),
        Err(e) => {
            error!("Failed to batch write items: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

// ==================== Transaction Handlers ====================

/// Handle TransactGetItems operation
async fn handle_transact_get_items(
    state: AppState,
    request: TransactGetItemsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let transact_items = request.transact_items;

    // Validate that at least one item is specified
    if transact_items.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "TransactItems must contain at least one item",
            )),
        ));
    }

    // Validate the 100 item limit
    if transact_items.len() > 100 {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "TransactGetItems can retrieve up to 100 items per operation",
            )),
        ));
    }

    match state.item_manager.transact_get_items(&transact_items) {
        Ok(responses) => {
            Ok(Json(DynamoDBResponse {
                item_responses: Some(responses),
                ..Default::default()
            }))
        }
        Err(ItemError::InvalidKey(msg)) => Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(msg)),
        )),
        Err(ItemError::Storage(StorageError::TableNotFound(table))) => Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::resource_not_found(format!(
                "Table not found: {}",
                table
            ))),
        )),
        Err(e) => {
            error!("Failed to transact get items: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle TransactWriteItems operation
async fn handle_transact_write_items(
    state: AppState,
    request: TransactWriteItemsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let transact_items = request.transact_items;

    // Validate that at least one item is specified
    if transact_items.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "TransactItems must contain at least one item",
            )),
        ));
    }

    // Validate the 25 item limit
    if transact_items.len() > 25 {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "TransactWriteItems can write up to 25 items per operation",
            )),
        ));
    }

    match state.item_manager.transact_write_items(&transact_items) {
        Ok(()) => {
            // TransactWriteItems returns empty response on success
            Ok(Json(DynamoDBResponse::default()))
        }
        Err(ItemError::InvalidKey(msg)) => Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(msg)),
        )),
        Err(ItemError::ConditionCheckFailed(msg)) => Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::conditional_check_failed(msg)),
        )),
        Err(ItemError::Storage(StorageError::TableNotFound(table))) => Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::resource_not_found(format!(
                "Table not found: {}",
                table
            ))),
        )),
        Err(e) => {
            error!("Failed to transact write items: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

// ==================== Backup/Restore Handlers ====================

/// Handle CreateBackup operation
async fn handle_create_backup(
    state: AppState,
    request: CreateBackupRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.create_backup(&request.table_name, request.backup_name) {
        Ok(backup_description) => {
            info!(
                "Created backup {} for table {}",
                backup_description.backup_name, backup_description.table_name
            );
            Ok(Json(DynamoDBResponse {
                backup_description: Some(backup_description),
                ..Default::default()
            }))
        }
        Err(StorageError::TableNotFound(table)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to create backup: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeBackup operation
async fn handle_describe_backup(
    state: AppState,
    request: DescribeBackupRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.describe_backup(&request.backup_arn) {
        Ok(backup_description) => {
            info!("Described backup: {}", backup_description.backup_arn);
            Ok(Json(DynamoDBResponse {
                backup_description: Some(backup_description),
                ..Default::default()
            }))
        }
        Err(StorageError::TableNotFound(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Backup not found: {}",
                    request.backup_arn
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to describe backup: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle ListBackups operation
async fn handle_list_backups(
    state: AppState,
    request: ListBackupsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state
        .table_manager
        .list_backups(request.table_name.as_deref(), request.limit)
    {
        Ok(backup_summaries) => {
            info!("Listed {} backups", backup_summaries.len());
            Ok(Json(DynamoDBResponse {
                backup_summaries: Some(backup_summaries),
                ..Default::default()
            }))
        }
        Err(e) => {
            error!("Failed to list backups: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DeleteBackup operation
async fn handle_delete_backup(
    state: AppState,
    request: DeleteBackupRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.delete_backup(&request.backup_arn) {
        Ok(backup_description) => {
            info!("Deleted backup: {}", backup_description.backup_arn);
            Ok(Json(DynamoDBResponse {
                backup_description: Some(backup_description),
                ..Default::default()
            }))
        }
        Err(StorageError::TableNotFound(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Backup not found: {}",
                    request.backup_arn
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to delete backup: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle RestoreTableFromBackup operation
async fn handle_restore_table_from_backup(
    state: AppState,
    request: RestoreTableFromBackupRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state
        .table_manager
        .restore_table_from_backup(&request.target_table_name, &request.backup_arn)
    {
        Ok(table_metadata) => {
            info!(
                "Restored table {} from backup {}",
                request.target_table_name, request.backup_arn
            );
            Ok(Json(DynamoDBResponse {
                table_description: Some(table_metadata),
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
        Err(StorageError::TableNotFound(msg)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(msg)),
            ))
        }
        Err(e) => {
            error!("Failed to restore table from backup: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

// ==================== PITR Handlers ====================

/// Handle UpdateContinuousBackups operation
async fn handle_update_continuous_backups(
    state: AppState,
    request: UpdateContinuousBackupsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name;
    let enabled = request.point_in_time_recovery_specification.point_in_time_recovery_enabled;

    match state.table_manager.update_continuous_backups(&table_name, enabled) {
        Ok(description) => {
            info!(
                "Updated continuous backups for table {}: PITR enabled={}",
                table_name, enabled
            );
            Ok(Json(DynamoDBResponse {
                continuous_backups_description: Some(description),
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
            error!("Failed to update continuous backups for table {}: {}", table_name, e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeContinuousBackups operation
async fn handle_describe_continuous_backups(
    state: AppState,
    request: DescribeContinuousBackupsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let table_name = request.table_name;

    match state.table_manager.describe_continuous_backups(&table_name) {
        Ok(description) => {
            info!("Described continuous backups for table {}", table_name);
            Ok(Json(DynamoDBResponse {
                continuous_backups_description: Some(description),
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
            error!("Failed to describe continuous backups for table {}: {}", table_name, e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle RestoreTableToPointInTime operation
async fn handle_restore_table_to_point_in_time(
    state: AppState,
    request: RestoreTableToPointInTimeRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.restore_table_to_point_in_time(&request) {
        Ok(table_metadata) => {
            info!(
                "Restored table {} to point in time from source table {}",
                request.target_table_name, request.source_table_name
            );
            Ok(Json(DynamoDBResponse {
                table_description: Some(table_metadata),
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
        Err(StorageError::TableNotFound(msg)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(msg)),
            ))
        }
        Err(StorageError::InvalidKey(msg)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(msg)),
            ))
        }
        Err(e) => {
            error!("Failed to restore table to point in time: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
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
