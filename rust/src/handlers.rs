//! HTTP handlers for DynamoDB API operations

use crate::global_tables::{GlobalTableError, GlobalTableManager};
use crate::items::{ItemError, ItemManager};
use crate::models::*;
use crate::partiql::{ExecutionResult, PartiQLEngine, PartiQLError};
use crate::storage::{StorageError, TableManager};
use crate::stream_manager::{StreamError, StreamManager};
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
    pub stream_manager: Arc<StreamManager>,
    pub global_table_manager: Arc<GlobalTableManager>,
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
        // PartiQL operations
        "ExecuteStatement" => {
            let request: ExecuteStatementRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_execute_statement(state, request).await
        }
        "BatchExecuteStatement" => {
            let request: BatchExecuteStatementRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_batch_execute_statement(state, request).await
        }
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
        // Import/Export operations
        "ExportTableToPointInTime" => {
            let request: ExportTableToPointInTimeRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_export_table_to_point_in_time(state, request).await
        }
        "DescribeExport" => {
            let request: DescribeExportRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_export(state, request).await
        }
        "ListExports" => {
            let request: ListExportsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_list_exports(state, request).await
        }
        "ImportTable" => {
            let request: ImportTableRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_import_table(state, request).await
        }
        "DescribeImport" => {
            let request: DescribeImportRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_import(state, request).await
        }
        "ListImports" => {
            let request: ListImportsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_list_imports(state, request).await
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
        // Global Tables operations
        "CreateGlobalTable" => {
            let request: CreateGlobalTableRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_create_global_table(state, request).await
        }
        "UpdateGlobalTable" => {
            let request: UpdateGlobalTableRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_update_global_table(state, request).await
        }
        "DescribeGlobalTable" => {
            let request: DescribeGlobalTableRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_global_table(state, request).await
        }
        "ListGlobalTables" => {
            let request: ListGlobalTablesRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_list_global_tables(state, request).await
        }
        "DeleteGlobalTable" => {
            let request: DeleteGlobalTableRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_delete_global_table(state, request).await
        }
        "UpdateGlobalTableSettings" => {
            let request: UpdateGlobalTableSettingsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_update_global_table_settings(state, request).await
        }
        "DescribeGlobalTableSettings" => {
            let request: DescribeGlobalTableSettingsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_global_table_settings(state, request).await
        }
        "UpdateReplication" => {
            let request: UpdateReplicationRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_update_replication(state, request).await
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
        // Streams operations
        "ListStreams" => {
            let request: ListStreamsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_list_streams(state, request).await
        }
        "DescribeStream" => {
            let request: DescribeStreamRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_stream(state, request).await
        }
        "GetShardIterator" => {
            let request: GetShardIteratorRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_get_shard_iterator(state, request).await
        }
        "GetRecords" => {
            let request: GetRecordsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_get_records(state, request).await
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
        "ConditionCheck" => {
            let request: ConditionCheckRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_condition_check(state, request).await
        }
        "DescribeLimits" => {
            let _request: DescribeLimitsRequest = serde_json::from_slice(&body).map_err(|e| {
                (
                    StatusCode::BAD_REQUEST,
                    Json(ErrorResponse::validation_exception(format!(
                        "Invalid request body: {}",
                        e
                    ))),
                )
            })?;
            handle_describe_limits().await
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
                "DescribeLimits" => handle_describe_limits().await,
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
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let resource_arn = request.resource_arn.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Resource ARN is required")),
        )
    })?;

    let table_name = extract_table_name_from_arn(&resource_arn).ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Invalid resource ARN")),
        )
    })?;

    let tags = request.tags.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Tags are required")),
        )
    })?;

    match state.table_manager.tag_resource(&table_name, tags) {
        Ok(()) => {
            info!("Tagged table: {}", table_name);
            Ok(Json(DynamoDBResponse::default()))
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
            error!("Failed to tag table {}: {}", table_name, e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle UntagResource operation
async fn handle_untag_resource(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let resource_arn = request.resource_arn.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Resource ARN is required")),
        )
    })?;

    let table_name = extract_table_name_from_arn(&resource_arn).ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Invalid resource ARN")),
        )
    })?;

    let tag_keys = request.tag_keys.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("TagKeys are required")),
        )
    })?;

    match state.table_manager.untag_resource(&table_name, tag_keys) {
        Ok(()) => {
            info!("Untagged table: {}", table_name);
            Ok(Json(DynamoDBResponse::default()))
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
            error!("Failed to untag table {}: {}", table_name, e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle ListTagsOfResource operation
async fn handle_list_tags_of_resource(
    state: AppState,
    request: DynamoDBRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let resource_arn = request.resource_arn.ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Resource ARN is required")),
        )
    })?;

    let table_name = extract_table_name_from_arn(&resource_arn).ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception("Invalid resource ARN")),
        )
    })?;

    match state.table_manager.list_tags_of_resource(&table_name) {
        Ok(tags) => {
            info!("Listed tags for table {}: {} tags found", table_name, tags.len());
            Ok(Json(DynamoDBResponse {
                tags: Some(tags),
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
            error!("Failed to list tags for table {}: {}", table_name, e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
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
    let filter_expression = request.filter_expression.as_deref();
    let expression_names = request.expression_attribute_names.as_ref();
    let expression_values = request.expression_attribute_values.as_ref();

    match state.item_manager.query(
        &table_name,
        index_name,
        &partition_key_value,
        None, // key_conditions - simplified
        scan_index_forward,
        limit,
        filter_expression,
        expression_names,
        expression_values,
    ) {
        Ok((items, last_key, count, scanned_count)) => {
            Ok(Json(DynamoDBResponse {
                items: Some(items),
                count: Some(count),
                scanned_count: Some(scanned_count),
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
        Err(ItemError::Expression(msg)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Invalid filter expression: {}",
                    msg
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
    let filter_expression = request.filter_expression.as_deref();
    let expression_names = request.expression_attribute_names.as_ref();
    let expression_values = request.expression_attribute_values.as_ref();

    match state.item_manager.scan(&table_name, index_name, limit, exclusive_start_key, filter_expression, expression_names, expression_values) {
        Ok((items, last_key, count, scanned_count)) => {
            Ok(Json(DynamoDBResponse {
                items: Some(items),
                count: Some(count),
                scanned_count: Some(scanned_count),
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
        Err(ItemError::Expression(msg)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Invalid filter expression: {}",
                    msg
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

// ==================== PartiQL Handlers ====================

/// Handle ExecuteStatement operation
async fn handle_execute_statement(
    state: AppState,
    request: ExecuteStatementRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    // Parse the PartiQL statement
    let parsed = match PartiQLEngine::parse(&request.statement) {
        Ok(stmt) => stmt,
        Err(e) => {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Invalid PartiQL statement: {}",
                    e
                ))),
            ));
        }
    };

    // Execute the statement
    let engine = PartiQLEngine::new();
    let consistent_read = request.consistent_read.unwrap_or(false);

    match engine.execute(
        &parsed,
        request.parameters.as_ref(),
        &state.item_manager,
        consistent_read,
    ) {
        Ok(result) => {
            let response = match result {
                ExecutionResult::Items(items) => ExecuteStatementResponse {
                    items: Some(items),
                    ..Default::default()
                },
                ExecutionResult::Item(item) => ExecuteStatementResponse {
                    item,
                    ..Default::default()
                },
                ExecutionResult::Empty => ExecuteStatementResponse::default(),
            };

            // Convert to DynamoDBResponse
            Ok(Json(DynamoDBResponse {
                items: response.items,
                item: response.item,
                ..Default::default()
            }))
        }
        Err(PartiQLError::ItemError(ItemError::Storage(StorageError::TableNotFound(table)))) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    table
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to execute PartiQL statement: {}", e);
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Execution error: {}",
                    e
                ))),
            ))
        }
    }
}

/// Handle BatchExecuteStatement operation
async fn handle_batch_execute_statement(
    state: AppState,
    request: BatchExecuteStatementRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    // DynamoDB limit: up to 25 statements per batch
    if request.statements.len() > 25 {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse::validation_exception(
                "BatchExecuteStatement can execute up to 25 statements per operation",
            )),
        ));
    }

    let engine = PartiQLEngine::new();
    let mut responses = Vec::new();

    for statement in &request.statements {
        // Parse the statement
        let parsed = match PartiQLEngine::parse(&statement.statement) {
            Ok(stmt) => stmt,
            Err(e) => {
                responses.push(PartiQLResponse {
                    error: Some(crate::models::PartiQLError {
                        code: "ValidationException".to_string(),
                        message: format!("Invalid PartiQL statement: {}", e),
                    }),
                    ..Default::default()
                });
                continue;
            }
        };

        // Execute the statement
        let consistent_read = statement.consistent_read.unwrap_or(false);

        let result = engine.execute(
            &parsed,
            statement.parameters.as_ref(),
            &state.item_manager,
            consistent_read,
        );

        match result {
            Ok(ExecutionResult::Items(items)) => {
                responses.push(PartiQLResponse {
                    items: Some(items),
                    ..Default::default()
                });
            }
            Ok(ExecutionResult::Item(item)) => {
                responses.push(PartiQLResponse {
                    item,
                    ..Default::default()
                });
            }
            Ok(ExecutionResult::Empty) => {
                responses.push(PartiQLResponse::default());
            }
            Err(PartiQLError::ItemError(ItemError::Storage(StorageError::TableNotFound(table)))) => {
                responses.push(PartiQLResponse {
                    error: Some(crate::models::PartiQLError {
                        code: "ResourceNotFoundException".to_string(),
                        message: format!("Table not found: {}", table),
                    }),
                    ..Default::default()
                });
            }
            Err(e) => {
                responses.push(PartiQLResponse {
                    error: Some(crate::models::PartiQLError {
                        code: "ExecutionException".to_string(),
                        message: format!("Execution error: {}", e),
                    }),
                    ..Default::default()
                });
            }
        }
    }

    // Convert to DynamoDBResponse (wrap in a wrapper that includes the responses)
    Ok(Json(DynamoDBResponse {
        item_responses: Some(
            responses
                .into_iter()
                .map(|r| ItemResponse { item: r.item })
                .collect(),
        ),
        ..Default::default()
    }))
}


// ==================== Import/Export Handlers ====================

/// Handle ExportTableToPointInTime operation
async fn handle_export_table_to_point_in_time(
    state: AppState,
    request: ExportTableToPointInTimeRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.export_table_to_point_in_time(
        &request.table_arn,
        &request.s3_bucket,
        request.s3_prefix,
        request.export_format,
    ) {
        Ok(export_description) => {
            info!(
                "Exported table {} to bucket {}",
                export_description.table_arn.as_ref().unwrap_or(&"unknown".to_string()),
                export_description.s3_bucket
            );
            Ok(Json(DynamoDBResponse {
                export_description: Some(export_description),
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
            error!("Failed to export table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeExport operation
async fn handle_describe_export(
    state: AppState,
    request: DescribeExportRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.describe_export(&request.export_arn) {
        Ok(export_description) => {
            info!("Described export: {}", export_description.export_arn);
            Ok(Json(DynamoDBResponse {
                export_description: Some(export_description),
                ..Default::default()
            }))
        }
        Err(StorageError::TableNotFound(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Export not found: {}",
                    request.export_arn
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to describe export: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle ListExports operation
async fn handle_list_exports(
    state: AppState,
    request: ListExportsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.list_exports(request.table_arn.as_deref()) {
        Ok(export_summaries) => {
            info!("Listed {} exports", export_summaries.len());
            Ok(Json(DynamoDBResponse {
                export_summaries: Some(export_summaries),
                ..Default::default()
            }))
        }
        Err(e) => {
            error!("Failed to list exports: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle ImportTable operation
async fn handle_import_table(
    state: AppState,
    request: ImportTableRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.import_table(
        &request.table_name,
        &request.s3_bucket_source,
        request.input_format,
        request.key_schema,
        request.attribute_definitions,
    ) {
        Ok(import_description) => {
            info!(
                "Imported table {} from bucket {}",
                request.table_name,
                request.s3_bucket_source.s3_bucket
            );
            Ok(Json(DynamoDBResponse {
                import_description: Some(import_description),
                ..Default::default()
            }))
        }
        Err(StorageError::TableNotFound(msg)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(msg)),
            ))
        }
        Err(e) => {
            error!("Failed to import table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeImport operation
async fn handle_describe_import(
    state: AppState,
    request: DescribeImportRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.describe_import(&request.import_arn) {
        Ok(import_description) => {
            info!("Described import: {}", import_description.import_arn);
            Ok(Json(DynamoDBResponse {
                import_description: Some(import_description),
                ..Default::default()
            }))
        }
        Err(StorageError::TableNotFound(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Import not found: {}",
                    request.import_arn
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to describe import: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle ListImports operation
async fn handle_list_imports(
    state: AppState,
    request: ListImportsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.table_manager.list_imports(request.table_arn.as_deref()) {
        Ok(import_summaries) => {
            info!("Listed {} imports", import_summaries.len());
            Ok(Json(DynamoDBResponse {
                import_summaries: Some(import_summaries),
                ..Default::default()
            }))
        }
        Err(e) => {
            error!("Failed to list imports: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

// ==================== Streams Handlers ====================

/// Handle ListStreams operation
async fn handle_list_streams(
    state: AppState,
    request: ListStreamsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.stream_manager.list_streams(
        request.table_name.as_deref(),
        request.exclusive_start_stream_arn.as_deref(),
        request.limit,
    ) {
        Ok((streams, last_evaluated)) => {
            info!("Listed {} streams", streams.len());
            Ok(Json(DynamoDBResponse {
                streams: Some(streams),
                last_evaluated_key: last_evaluated.map(|arn| {
                    let mut key = Item::new();
                    key.insert("LastEvaluatedStreamArn".to_string(), AttributeValue::s(arn));
                    key
                }),
                ..Default::default()
            }))
        }
        Err(e) => {
            error!("Failed to list streams: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeStream operation
async fn handle_describe_stream(
    state: AppState,
    request: DescribeStreamRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.stream_manager.describe_stream(
        &request.stream_arn,
        request.exclusive_start_shard_id.as_deref(),
        request.limit,
    ) {
        Ok(stream_description) => {
            info!("Described stream: {}", stream_description.stream_arn);
            Ok(Json(DynamoDBResponse {
                stream_description: Some(stream_description),
                ..Default::default()
            }))
        }
        Err(StreamError::StreamNotFound(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Stream not found: {}",
                    request.stream_arn
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to describe stream: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle GetShardIterator operation
async fn handle_get_shard_iterator(
    state: AppState,
    request: GetShardIteratorRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.stream_manager.get_shard_iterator(
        &request.stream_arn,
        &request.shard_id,
        request.shard_iterator_type.clone(),
        request.sequence_number.as_deref(),
        request.timestamp,
    ) {
        Ok(shard_iterator) => {
            info!("Created shard iterator for stream: {}", request.stream_arn);
            Ok(Json(DynamoDBResponse {
                shard_iterator: Some(shard_iterator),
                ..Default::default()
            }))
        }
        Err(StreamError::StreamNotFound(_)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Stream not found: {}",
                    request.stream_arn
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to get shard iterator: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle GetRecords operation
async fn handle_get_records(
    state: AppState,
    request: GetRecordsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.stream_manager.get_records(
        &request.shard_iterator,
        request.limit,
    ) {
        Ok((records, next_shard_iterator)) => {
            info!("Retrieved {} records from stream", records.len());
            Ok(Json(DynamoDBResponse {
                records: Some(records),
                shard_iterator: next_shard_iterator,
                ..Default::default()
            }))
        }
        Err(StreamError::InvalidIterator(msg)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Invalid shard iterator: {}",
                    msg
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to get records: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

// ==================== Global Tables Handlers ====================

/// Handle CreateGlobalTable operation
async fn handle_create_global_table(
    state: AppState,
    request: CreateGlobalTableRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.global_table_manager.create_global_table(&request) {
        Ok(global_table_description) => {
            info!(
                "Created global table: {} with {} replicas",
                global_table_description.global_table_name,
                global_table_description.replication_group.len()
            );
            Ok(Json(DynamoDBResponse {
                global_table_description: Some(global_table_description),
                ..Default::default()
            }))
        }
        Err(GlobalTableError::GlobalTableAlreadyExists(name)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_in_use(format!(
                    "Global table already exists: {}",
                    name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to create global table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle UpdateGlobalTable operation
async fn handle_update_global_table(
    state: AppState,
    request: UpdateGlobalTableRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.global_table_manager.update_global_table(&request) {
        Ok(global_table_description) => {
            info!(
                "Updated global table: {}",
                global_table_description.global_table_name
            );
            Ok(Json(DynamoDBResponse {
                global_table_description: Some(global_table_description),
                ..Default::default()
            }))
        }
        Err(GlobalTableError::GlobalTableNotFound(name)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Global table not found: {}",
                    name
                ))),
            ))
        }
        Err(GlobalTableError::ReplicaAlreadyExists(region)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Replica already exists in region: {}",
                    region
                ))),
            ))
        }
        Err(GlobalTableError::ReplicaNotFound(region)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Replica not found in region: {}",
                    region
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to update global table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeGlobalTable operation
async fn handle_describe_global_table(
    state: AppState,
    request: DescribeGlobalTableRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.global_table_manager.describe_global_table(&request.global_table_name) {
        Ok(global_table_description) => {
            info!(
                "Described global table: {}",
                global_table_description.global_table_name
            );
            Ok(Json(DynamoDBResponse {
                global_table_description: Some(global_table_description),
                ..Default::default()
            }))
        }
        Err(GlobalTableError::GlobalTableNotFound(name)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Global table not found: {}",
                    name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to describe global table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle ListGlobalTables operation
async fn handle_list_global_tables(
    state: AppState,
    request: ListGlobalTablesRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.global_table_manager.list_global_tables(
        request.exclusive_start_global_table_name.as_deref(),
        request.limit,
    ) {
        Ok((global_tables, last_evaluated)) => {
            info!("Listed {} global tables", global_tables.len());
            Ok(Json(DynamoDBResponse {
                global_tables: Some(global_tables),
                last_evaluated_global_table_name: last_evaluated,
                ..Default::default()
            }))
        }
        Err(e) => {
            error!("Failed to list global tables: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DeleteGlobalTable operation
async fn handle_delete_global_table(
    state: AppState,
    request: DeleteGlobalTableRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.global_table_manager.delete_global_table(&request.global_table_name) {
        Ok(global_table_description) => {
            info!(
                "Deleted global table: {}",
                global_table_description.global_table_name
            );
            Ok(Json(DynamoDBResponse {
                global_table_description: Some(global_table_description),
                ..Default::default()
            }))
        }
        Err(GlobalTableError::GlobalTableNotFound(name)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Global table not found: {}",
                    name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to delete global table: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle UpdateGlobalTableSettings operation
async fn handle_update_global_table_settings(
    state: AppState,
    request: UpdateGlobalTableSettingsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.global_table_manager.update_global_table_settings(&request) {
        Ok(global_table_description) => {
            info!(
                "Updated global table settings: {}",
                global_table_description.global_table_name
            );
            Ok(Json(DynamoDBResponse {
                global_table_description: Some(global_table_description),
                ..Default::default()
            }))
        }
        Err(GlobalTableError::GlobalTableNotFound(name)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Global table not found: {}",
                    name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to update global table settings: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeGlobalTableSettings operation
async fn handle_describe_global_table_settings(
    state: AppState,
    request: DescribeGlobalTableSettingsRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.global_table_manager.describe_global_table_settings(&request.global_table_name) {
        Ok((global_table_name, replica_settings)) => {
            info!(
                "Described global table settings: {} with {} replicas",
                global_table_name,
                replica_settings.len()
            );
            Ok(Json(DynamoDBResponse {
                table_description: Some(TableMetadata {
                    table_name: global_table_name.clone(),
                    table_arn: None,
                    table_id: None,
                    table_status: "ACTIVE".to_string(),
                    key_schema: vec![],
                    attribute_definitions: vec![],
                    item_count: 0,
                    table_size_bytes: 0,
                    creation_date_time: chrono::Utc::now(),
                    billing_mode_summary: None,
                    provisioned_throughput: None,
                    global_secondary_indexes: None,
                    local_secondary_indexes: None,
                    tags: None,
                }),
                replica_settings: Some(replica_settings),
                ..Default::default()
            }))
        }
        Err(GlobalTableError::GlobalTableNotFound(name)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Global table not found: {}",
                    name
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to describe global table settings: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle UpdateReplication operation
async fn handle_update_replication(
    state: AppState,
    request: UpdateReplicationRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    match state.global_table_manager.update_replication(&request) {
        Ok(global_table_description) => {
            info!(
                "Updated replication for global table: {}",
                global_table_description.global_table_name
            );
            Ok(Json(DynamoDBResponse {
                global_table_description: Some(global_table_description),
                ..Default::default()
            }))
        }
        Err(GlobalTableError::GlobalTableNotFound(name)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Global table not found: {}",
                    name
                ))),
            ))
        }
        Err(GlobalTableError::ReplicaAlreadyExists(region)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Replica already exists in region: {}",
                    region
                ))),
            ))
        }
        Err(GlobalTableError::ReplicaNotFound(region)) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::validation_exception(format!(
                    "Replica not found in region: {}",
                    region
                ))),
            ))
        }
        Err(e) => {
            error!("Failed to update replication: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle ConditionCheck operation
async fn handle_condition_check(
    state: AppState,
    request: ConditionCheckRequest,
) -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    let condition_expression = request.condition_expression;
    let expression_names = request.expression_attribute_names.as_ref();
    let expression_values = request.expression_attribute_values.as_ref();

    match state.item_manager.condition_check(
        &request.table_name,
        &request.key,
        &condition_expression,
        expression_names,
        expression_values,
    ) {
        Ok(()) => {
            // ConditionCheck returns empty response on success
            Ok(Json(DynamoDBResponse::default()))
        }
        Err(ItemError::Storage(StorageError::TableNotFound(_))) => {
            Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse::resource_not_found(format!(
                    "Table not found: {}",
                    request.table_name
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
            error!("Failed to condition check: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse::internal_server_error(e.to_string())),
            ))
        }
    }
}

/// Handle DescribeLimits operation
async fn handle_describe_limits() -> Result<Json<DynamoDBResponse>, (StatusCode, Json<ErrorResponse>)> {
    // Return default limits for local implementation
    // These are the maximum allowed values for DynamoDB Local
    Ok(Json(DynamoDBResponse {
        account_max_read_capacity_units: Some(100000),
        account_max_write_capacity_units: Some(100000),
        table_max_read_capacity_units: Some(100000),
        table_max_write_capacity_units: Some(100000),
        ..Default::default()
    }))
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
