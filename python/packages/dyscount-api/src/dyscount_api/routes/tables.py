"""DynamoDB table management routes."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from dyscount_core.config import Config
from dyscount_core.models.errors import DynamoDBException, ValidationException
from dyscount_core.models.errors import ResourceNotFoundException
from dyscount_core.models.errors import ResourceNotFoundException
from dyscount_core.models.operations import (
    CreateTableRequest,
    CreateTableResponse,
    DeleteTableRequest,
    DeleteTableResponse,
    DescribeEndpointsRequest,
    DescribeEndpointsResponse,
    DescribeTableRequest,
    DescribeTableResponse,
    ListTablesRequest,
    ListTablesResponse,
)
from dyscount_core.services.table_service import TableService

from ..dependencies import get_config


class DynamoDBJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles DynamoDB-specific types like datetime."""
    def default(self, obj):
        if isinstance(obj, datetime):
            # DynamoDB uses Unix timestamp in milliseconds
            return int(obj.timestamp())
        return super().default(obj)

router = APIRouter()


@router.post("/")
async def dynamodb_endpoint(
    request: Request,
    config: Config = Depends(get_config),
) -> JSONResponse:
    """Main DynamoDB endpoint. Routes based on X-Amz-Target header.
    
    Args:
        request: The incoming HTTP request containing the operation.
        config: Application configuration via dependency injection.
        
    Returns:
        JSONResponse with the operation result or error.
    """
    amz_target = request.headers.get("X-Amz-Target", "")
    body = await request.json()
    
    # Route based on X-Amz-Target
    # Format: DynamoDB_20120810.OperationName
    if "." in amz_target:
        operation = amz_target.split(".")[-1]
    else:
        operation = amz_target
    
    if operation == "CreateTable":
        return await handle_create_table(body, config)
    elif operation == "DeleteTable":
        return await handle_delete_table(body, config)
    elif operation == "ListTables":
        return await handle_list_tables(body, config)
    elif operation == "DescribeTable":
        return await handle_describe_table(body, config)
    elif operation == "UpdateTable":
        return await handle_update_table(body, config)
    elif operation == "DescribeEndpoints":
        return await handle_describe_endpoints(body, config)
    elif operation == "GetItem":
        return await handle_get_item(body, config)
    elif operation == "PutItem":
        return await handle_put_item(body, config)
    elif operation == "DeleteItem":
        return await handle_delete_item(body, config)
    elif operation == "UpdateItem":
        return await handle_update_item(body, config)
    elif operation == "Query":
        return await handle_query(body, config)
    elif operation == "Scan":
        return await handle_scan(body, config)
    elif operation == "BatchGetItem":
        return await handle_batch_get_item(body, config)
    elif operation == "BatchWriteItem":
        return await handle_batch_write_item(body, config)
    elif operation == "TransactGetItems":
        return await handle_transact_get_items(body, config)
    elif operation == "TransactWriteItems":
        return await handle_transact_write_items(body, config)
    elif operation == "TagResource":
        return await handle_tag_resource(body, config)
    elif operation == "UntagResource":
        return await handle_untag_resource(body, config)
    elif operation == "ListTagsOfResource":
        return await handle_list_tags_of_resource(body, config)
    elif operation == "UpdateTimeToLive":
        return await handle_update_time_to_live(body, config)
    elif operation == "DescribeTimeToLive":
        return await handle_describe_time_to_live(body, config)
    elif operation == "CreateBackup":
        return await handle_create_backup(body, config)
    elif operation == "RestoreTableFromBackup":
        return await handle_restore_table_from_backup(body, config)
    elif operation == "ListBackups":
        return await handle_list_backups(body, config)
    elif operation == "DeleteBackup":
        return await handle_delete_backup(body, config)
    elif operation == "ExecuteStatement":
        return await handle_execute_statement(body, config)
    elif operation == "BatchExecuteStatement":
        return await handle_batch_execute_statement(body, config)
    elif operation == "ExportTableToPointInTime":
        return await handle_export_table_to_point_in_time(body, config)
    elif operation == "DescribeExport":
        return await handle_describe_export(body, config)
    elif operation == "ListExports":
        return await handle_list_exports(body, config)
    elif operation == "ImportTable":
        return await handle_import_table(body, config)
    elif operation == "DescribeImport":
        return await handle_describe_import(body, config)
    elif operation == "ListImports":
        return await handle_list_imports(body, config)
    elif operation == "DescribeStream":
        return await handle_describe_stream(body, config)
    elif operation == "GetRecords":
        return await handle_get_records(body, config)
    elif operation == "GetShardIterator":
        return await handle_get_shard_iterator(body, config)
    elif operation == "ListStreams":
        return await handle_list_streams(body, config)
    else:
        return JSONResponse(
            status_code=400,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#ValidationException",
                "message": f"Unknown operation: {operation}"
            }
        )


async def handle_create_table(body: dict, config: Config) -> JSONResponse:
    """Handle CreateTable operation"""
    service = None
    try:
        # Parse request
        request = CreateTableRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.create_table(request)
        
        # Serialize response with custom encoder for datetime
        content = json.loads(json.dumps(response.model_dump(by_alias=True, exclude_none=True), cls=DynamoDBJSONEncoder))
        
        # Return success
        return JSONResponse(
            status_code=200,
            content=content
        )
        
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={
                "__type": e.error_type,
                "message": e.message
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_delete_table(body: dict, config: Config) -> JSONResponse:
    """Handle DeleteTable operation"""
    service = None
    try:
        # Parse request
        request = DeleteTableRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.delete_table(request)
        
        # Serialize response with custom encoder for datetime
        content = json.loads(json.dumps(response.model_dump(by_alias=True, exclude_none=True), cls=DynamoDBJSONEncoder))
        
        # Return success
        return JSONResponse(
            status_code=200,
            content=content
        )
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={
                "__type": e.error_type,
                "message": e.message
            }
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={
                "__type": e.error_type,
                "message": e.message
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_list_tables(body: dict, config: Config) -> JSONResponse:
    """Handle ListTables operation"""
    service = None
    try:
        # Parse request
        request = ListTablesRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.list_tables(request)
        
        # Serialize response
        content = json.loads(json.dumps(response.model_dump(by_alias=True, exclude_none=True), cls=DynamoDBJSONEncoder))
        
        # Return success
        return JSONResponse(
            status_code=200,
            content=content
        )
        
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={
                "__type": e.error_type,
                "message": e.message
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_describe_table(body: dict, config: Config) -> JSONResponse:
    """Handle DescribeTable operation"""
    service = None
    try:
        # Parse request
        request = DescribeTableRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.describe_table(request)
        
        # Serialize response with custom encoder for datetime
        content = json.loads(json.dumps(response.model_dump(by_alias=True, exclude_none=True), cls=DynamoDBJSONEncoder))
        
        # Return success
        return JSONResponse(
            status_code=200,
            content=content
        )
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={
                "__type": e.error_type,
                "message": e.message
            }
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={
                "__type": e.error_type,
                "message": e.message
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_describe_endpoints(body: dict, config: Config) -> JSONResponse:
    """Handle DescribeEndpoints operation"""
    service = None
    try:
        # Parse request (empty body is allowed)
        request = DescribeEndpointsRequest.model_validate(body if body else {})
        
        # Create service and execute
        service = TableService(config)
        response = await service.describe_endpoints(request)
        
        # Serialize response
        content = json.loads(json.dumps(response.model_dump(by_alias=True, exclude_none=True), cls=DynamoDBJSONEncoder))
        
        # Return success
        return JSONResponse(
            status_code=200,
            content=content
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# GetItem (Data Plane)
# =============================================================================

from dyscount_core.models.operations import GetItemRequest, GetItemResponse
from dyscount_core.services.item_service import ItemService


async def handle_get_item(body: dict, config: Config) -> JSONResponse:
    """Handle GetItem operation."""
    service = None
    try:
        # Parse request
        request = GetItemRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.get_item(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# PutItem (Data Plane)
# =============================================================================

from dyscount_core.models.operations import PutItemRequest, PutItemResponse


async def handle_put_item(body: dict, config: Config) -> JSONResponse:
    """Handle PutItem operation."""
    service = None
    try:
        # Parse request
        request = PutItemRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.put_item(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# DeleteItem (Data Plane)
# =============================================================================

from dyscount_core.models.operations import DeleteItemRequest, DeleteItemResponse


async def handle_delete_item(body: dict, config: Config) -> JSONResponse:
    """Handle DeleteItem operation."""
    service = None
    try:
        # Parse request
        request = DeleteItemRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.delete_item(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# UpdateItem (Data Plane)
# =============================================================================

from dyscount_core.models.operations import UpdateItemRequest, UpdateItemResponse


async def handle_update_item(body: dict, config: Config) -> JSONResponse:
    """Handle UpdateItem operation."""
    service = None
    try:
        # Parse request
        request = UpdateItemRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.update_item(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()



# =============================================================================
# Query (Data Plane)
# =============================================================================

from dyscount_core.models.operations import QueryRequest, QueryResponse


async def handle_query(body: dict, config: Config) -> JSONResponse:
    """Handle Query operation."""
    service = None
    try:
        # Parse request
        request = QueryRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.query(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# Scan (Data Plane)
# =============================================================================

from dyscount_core.models.operations import ScanRequest, ScanResponse


async def handle_scan(body: dict, config: Config) -> JSONResponse:
    """Handle Scan operation."""
    service = None
    try:
        # Parse request
        request = ScanRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.scan(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()



# =============================================================================
# BatchGetItem (Data Plane)
# =============================================================================

from dyscount_core.models.operations import BatchGetItemRequest, BatchGetItemResponse


async def handle_batch_get_item(body: dict, config: Config) -> JSONResponse:
    """Handle BatchGetItem operation."""
    service = None
    try:
        # Parse request
        request = BatchGetItemRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.batch_get_item(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# BatchWriteItem (Data Plane)
# =============================================================================

from dyscount_core.models.operations import BatchWriteItemRequest, BatchWriteItemResponse


async def handle_batch_write_item(body: dict, config: Config) -> JSONResponse:
    """Handle BatchWriteItem operation."""
    service = None
    try:
        # Parse request
        request = BatchWriteItemRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.batch_write_item(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()



# =============================================================================
# TransactGetItems (Data Plane)
# =============================================================================

from dyscount_core.models.operations import TransactGetItemsRequest, TransactGetItemsResponse


async def handle_transact_get_items(body: dict, config: Config) -> JSONResponse:
    """Handle TransactGetItems operation (atomic multi-item read)."""
    service = None
    try:
        # Parse request
        request = TransactGetItemsRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.transact_get_items(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# TransactWriteItems (Data Plane)
# =============================================================================

from dyscount_core.models.operations import TransactWriteItemsRequest, TransactWriteItemsResponse


async def handle_transact_write_items(body: dict, config: Config) -> JSONResponse:
    """Handle TransactWriteItems operation (atomic multi-item write)."""
    service = None
    try:
        # Parse request
        request = TransactWriteItemsRequest.model_validate(body)
        
        # Create service and execute
        service = ItemService(config)
        response = await service.transact_write_items(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()



# =============================================================================
# UpdateTable (Control Plane)
# =============================================================================

from dyscount_core.models.operations import UpdateTableRequest, UpdateTableResponse


async def handle_update_table(body: dict, config: Config) -> JSONResponse:
    """Handle UpdateTable operation."""
    service = None
    try:
        # Parse request
        request = UpdateTableRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.update_table(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()



# =============================================================================
# Tagging Operations
# =============================================================================

from dyscount_core.models.operations import (
    TagResourceRequest,
    TagResourceResponse,
    UntagResourceRequest,
    UntagResourceResponse,
    ListTagsOfResourceRequest,
    ListTagsOfResourceResponse,
)


async def handle_tag_resource(body: dict, config: Config) -> JSONResponse:
    """Handle TagResource operation."""
    service = None
    try:
        # Parse request
        request = TagResourceRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.tag_resource(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_untag_resource(body: dict, config: Config) -> JSONResponse:
    """Handle UntagResource operation."""
    service = None
    try:
        # Parse request
        request = UntagResourceRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.untag_resource(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_list_tags_of_resource(body: dict, config: Config) -> JSONResponse:
    """Handle ListTagsOfResource operation."""
    service = None
    try:
        # Parse request
        request = ListTagsOfResourceRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.list_tags_of_resource(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()



async def handle_update_time_to_live(body: dict, config: Config) -> JSONResponse:
    """Handle UpdateTimeToLive operation"""
    service = None
    try:
        from dyscount_core.models.operations import (
            UpdateTimeToLiveRequest,
            UpdateTimeToLiveResponse,
        )
        
        # Parse request
        request = UpdateTimeToLiveRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.update_time_to_live(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_describe_time_to_live(body: dict, config: Config) -> JSONResponse:
    """Handle DescribeTimeToLive operation"""
    service = None
    try:
        from dyscount_core.models.operations import (
            DescribeTimeToLiveRequest,
            DescribeTimeToLiveResponse,
        )
        
        # Parse request
        request = DescribeTimeToLiveRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.describe_time_to_live(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# Backup Operations (M2 Phase 2)
# =============================================================================

async def handle_create_backup(body: dict, config: Config) -> JSONResponse:
    """Handle CreateBackup operation"""
    service = None
    try:
        from dyscount_core.models.operations import (
            CreateBackupRequest,
            CreateBackupResponse,
        )
        
        # Parse request
        request = CreateBackupRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.create_backup(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_restore_table_from_backup(body: dict, config: Config) -> JSONResponse:
    """Handle RestoreTableFromBackup operation"""
    service = None
    try:
        from dyscount_core.models.operations import (
            RestoreTableFromBackupRequest,
            RestoreTableFromBackupResponse,
        )
        
        # Parse request
        request = RestoreTableFromBackupRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.restore_table_from_backup(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except TableAlreadyExistsException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_list_backups(body: dict, config: Config) -> JSONResponse:
    """Handle ListBackups operation"""
    service = None
    try:
        from dyscount_core.models.operations import (
            ListBackupsRequest,
            ListBackupsResponse,
        )
        
        # Parse request
        request = ListBackupsRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.list_backups(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_delete_backup(body: dict, config: Config) -> JSONResponse:
    """Handle DeleteBackup operation"""
    service = None
    try:
        from dyscount_core.models.operations import (
            DeleteBackupRequest,
            DeleteBackupResponse,
        )
        
        # Parse request
        request = DeleteBackupRequest.model_validate(body)
        
        # Create service and execute
        service = TableService(config)
        response = await service.delete_backup(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# PartiQL Operations (M2 Phase 4)
# =============================================================================

async def handle_execute_statement(body: dict, config: Config) -> JSONResponse:
    """Handle ExecuteStatement operation"""
    service = None
    try:
        from dyscount_core.models.operations import (
            ExecuteStatementRequest,
            ExecuteStatementResponse,
        )
        from dyscount_core.services.partiql_service import PartiQLService
        
        # Parse request
        request = ExecuteStatementRequest.model_validate(body)
        
        # Create service and execute
        service = PartiQLService(config)
        response = await service.execute_statement(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


async def handle_batch_execute_statement(body: dict, config: Config) -> JSONResponse:
    """Handle BatchExecuteStatement operation"""
    service = None
    try:
        from dyscount_core.models.operations import (
            BatchExecuteStatementRequest,
            BatchExecuteStatementResponse,
        )
        from dyscount_core.services.partiql_service import PartiQLService
        
        # Parse request
        request = BatchExecuteStatementRequest.model_validate(body)
        
        # Create service and execute
        service = PartiQLService(config)
        response = await service.batch_execute_statement(request)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if service:
            await service.close()


# =============================================================================
# Import/Export Operations (M4 Phase 1)
# =============================================================================

async def handle_export_table_to_point_in_time(body: dict, config: Config) -> JSONResponse:
    """Handle ExportTableToPointInTime operation"""
    from dyscount_core.services.import_export_service import ImportExportService
    from dyscount_core.services.table_service import TableService
    from dyscount_core.services.item_service import ItemService
    from dyscount_core.models.operations import (
        ExportTableToPointInTimeRequest,
        ExportTableToPointInTimeResponse,
    )
    
    export_service = None
    table_service = None
    item_service = None
    
    try:
        # Parse request
        request = ExportTableToPointInTimeRequest.model_validate(body)
        
        # Create services
        export_service = ImportExportService(
            data_directory=config.storage.data_directory,
            namespace=config.storage.default_namespace,
        )
        table_service = TableService(config)
        item_service = ItemService(config)
        
        # Execute export
        response = await export_service.export_table_to_point_in_time(
            request=request,
            table_manager=table_service.table_manager,
            item_service=item_service,
        )
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if table_service:
            await table_service.close()
        if item_service:
            await item_service.close()


async def handle_describe_export(body: dict, config: Config) -> JSONResponse:
    """Handle DescribeExport operation"""
    from dyscount_core.services.import_export_service import ImportExportService
    from dyscount_core.models.operations import (
        DescribeExportRequest,
        DescribeExportResponse,
    )
    
    export_service = None
    
    try:
        # Parse request
        request = DescribeExportRequest.model_validate(body)
        
        # Create service
        export_service = ImportExportService(
            data_directory=config.storage.data_directory,
            namespace=config.storage.default_namespace,
        )
        
        # Execute describe
        response = await export_service.describe_export(request.export_arn)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )


async def handle_list_exports(body: dict, config: Config) -> JSONResponse:
    """Handle ListExports operation"""
    from dyscount_core.services.import_export_service import ImportExportService
    from dyscount_core.models.operations import (
        ListExportsRequest,
        ListExportsResponse,
    )
    
    export_service = None
    
    try:
        # Parse request
        request = ListExportsRequest.model_validate(body)
        
        # Create service
        export_service = ImportExportService(
            data_directory=config.storage.data_directory,
            namespace=config.storage.default_namespace,
        )
        
        # Execute list
        response = await export_service.list_exports(
            table_arn=request.table_arn,
            max_results=request.max_results,
            next_token=request.next_token,
        )
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )


async def handle_import_table(body: dict, config: Config) -> JSONResponse:
    """Handle ImportTable operation"""
    from dyscount_core.services.import_export_service import ImportExportService
    from dyscount_core.services.table_service import TableService
    from dyscount_core.services.item_service import ItemService
    from dyscount_core.models.operations import (
        ImportTableRequest,
        ImportTableResponse,
    )
    
    import_service = None
    table_service = None
    item_service = None
    
    try:
        # Parse request
        request = ImportTableRequest.model_validate(body)
        
        # Create services
        import_service = ImportExportService(
            data_directory=config.storage.data_directory,
            namespace=config.storage.default_namespace,
        )
        table_service = TableService(config)
        item_service = ItemService(config)
        
        # Execute import
        response = await import_service.import_table(
            request=request,
            table_manager=table_service.table_manager,
            item_service=item_service,
        )
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ValidationException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if table_service:
            await table_service.close()
        if item_service:
            await item_service.close()


async def handle_describe_import(body: dict, config: Config) -> JSONResponse:
    """Handle DescribeImport operation"""
    from dyscount_core.services.import_export_service import ImportExportService
    from dyscount_core.models.operations import (
        DescribeImportRequest,
        DescribeImportResponse,
    )
    
    import_service = None
    
    try:
        # Parse request
        request = DescribeImportRequest.model_validate(body)
        
        # Create service
        import_service = ImportExportService(
            data_directory=config.storage.data_directory,
            namespace=config.storage.default_namespace,
        )
        
        # Execute describe
        response = await import_service.describe_import(request.import_arn)
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except ResourceNotFoundException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )


async def handle_list_imports(body: dict, config: Config) -> JSONResponse:
    """Handle ListImports operation"""
    from dyscount_core.services.import_export_service import ImportExportService
    from dyscount_core.models.operations import (
        ListImportsRequest,
        ListImportsResponse,
    )
    
    import_service = None
    
    try:
        # Parse request
        request = ListImportsRequest.model_validate(body)
        
        # Create service
        import_service = ImportExportService(
            data_directory=config.storage.data_directory,
            namespace=config.storage.default_namespace,
        )
        
        # Execute list
        response = await import_service.list_imports(
            table_arn=request.table_arn,
            page_size=request.page_size,
            next_token=request.next_token,
        )
        
        # Serialize response
        content = json.loads(
            json.dumps(
                response.model_dump(by_alias=True, exclude_none=True),
                cls=DynamoDBJSONEncoder
            )
        )
        
        # Return success
        return JSONResponse(status_code=200, content=content)
        
    except DynamoDBException as e:
        return JSONResponse(
            status_code=400,
            content={"__type": e.error_type, "message": e.message}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )



# =============================================================================
# Stream Operations (DynamoDB Streams)
# =============================================================================

from dyscount_core.storage.stream_manager import StreamManager, StreamViewType


async def handle_describe_stream(body: dict, config: Config) -> JSONResponse:
    """Handle DescribeStream operation."""
    stream_manager = None
    try:
        # Parse request
        table_name = body.get("TableName")
        if not table_name:
            # Try to extract from stream ARN
            stream_arn = body.get("StreamArn", "")
            if stream_arn:
                # Parse ARN format: arn:aws:dynamodb:region:account:table/table-name/stream/...
                parts = stream_arn.split("/")
                if len(parts) >= 2:
                    table_name = parts[1]
        
        if not table_name:
            return JSONResponse(
                status_code=400,
                content={
                    "__type": "com.amazonaws.dynamodb.v20120810#ValidationException",
                    "message": "TableName or StreamArn is required"
                }
            )
        
        # Create stream manager
        stream_manager = StreamManager(config.storage.data_directory)
        
        # Get stream metadata
        stream_meta = await stream_manager.describe_stream(table_name)
        
        if not stream_meta:
            return JSONResponse(
                status_code=400,
                content={
                    "__type": "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
                    "message": f"Stream not found for table: {table_name}"
                }
            )
        
        # Build response
        response = {
            "StreamDescription": {
                "StreamArn": stream_meta.stream_arn,
                "StreamLabel": stream_meta.stream_label,
                "StreamStatus": stream_meta.stream_status.value,
                "StreamViewType": stream_meta.stream_view_type.value,
                "CreationDateTime": stream_meta.creation_date_time,
                "TableName": stream_meta.table_name,
                "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
                "Shards": [
                    {
                        "ShardId": "shardId-000000000000",
                        "SequenceNumberRange": {
                            "StartingSequenceNumber": "0"
                        }
                    }
                ]
            }
        }
        
        return JSONResponse(status_code=200, content=response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if stream_manager:
            await stream_manager.close()


async def handle_get_records(body: dict, config: Config) -> JSONResponse:
    """Handle GetRecords operation."""
    stream_manager = None
    try:
        # Parse request
        shard_iterator = body.get("ShardIterator", "0")
        limit = body.get("Limit", 100)
        
        # Extract table name from shard iterator
        # Format: table_name:sequence_number
        if ":" in shard_iterator:
            parts = shard_iterator.split(":", 1)
            table_name = parts[0]
            sequence_number = parts[1] if len(parts) > 1 else "0"
        else:
            table_name = shard_iterator
            sequence_number = "0"
        
        # Create stream manager
        stream_manager = StreamManager(config.storage.data_directory)
        
        # Get records
        records, next_iterator = await stream_manager.get_records(
            table_name=table_name,
            shard_iterator=sequence_number,
            limit=limit,
        )
        
        # Build response
        response_records = []
        for record in records:
            response_record = {
                "eventID": record.event_id,
                "eventName": record.event_name.value,
                "eventVersion": record.event_version,
                "eventSource": record.event_source,
                "awsRegion": record.aws_region,
                "dynamodb": {
                    "ApproximateCreationDateTime": record.approximate_creation_date_time,
                    "Keys": record.keys,
                    "SequenceNumber": record.sequence_number,
                    "SizeBytes": record.size_bytes,
                    "StreamViewType": record.stream_view_type.value,
                }
            }
            
            if record.old_image:
                response_record["dynamodb"]["OldImage"] = record.old_image
            if record.new_image:
                response_record["dynamodb"]["NewImage"] = record.new_image
            
            response_records.append(response_record)
        
        response = {
            "Records": response_records,
        }
        
        if next_iterator:
            response["NextShardIterator"] = f"{table_name}:{next_iterator}"
        
        return JSONResponse(status_code=200, content=response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if stream_manager:
            await stream_manager.close()


async def handle_get_shard_iterator(body: dict, config: Config) -> JSONResponse:
    """Handle GetShardIterator operation."""
    stream_manager = None
    try:
        # Parse request
        stream_arn = body.get("StreamArn", "")
        shard_id = body.get("ShardId", "")
        iterator_type = body.get("ShardIteratorType", "TRIM_HORIZON")
        sequence_number = body.get("SequenceNumber", "0")
        
        # Extract table name from stream ARN
        table_name = None
        if stream_arn:
            parts = stream_arn.split("/")
            if len(parts) >= 2:
                table_name = parts[1]
        
        if not table_name:
            return JSONResponse(
                status_code=400,
                content={
                    "__type": "com.amazonaws.dynamodb.v20120810#ValidationException",
                    "message": "StreamArn is required"
                }
            )
        
        # Create stream manager
        stream_manager = StreamManager(config.storage.data_directory)
        
        # Get stream metadata to verify it exists
        stream_meta = await stream_manager.describe_stream(table_name)
        if not stream_meta:
            return JSONResponse(
                status_code=400,
                content={
                    "__type": "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
                    "message": f"Stream not found: {stream_arn}"
                }
            )
        
        # Build shard iterator based on type
        if iterator_type == "LATEST":
            # Get the latest sequence number
            conn = await stream_manager._get_connection(table_name)
            async with conn.execute(
                "SELECT MAX(sequence_number) FROM __stream_records WHERE stream_arn = ?",
                (stream_meta.stream_arn,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    sequence_number = row[0]
                else:
                    sequence_number = "0"
        elif iterator_type == "TRIM_HORIZON":
            sequence_number = "0"
        elif iterator_type == "AT_SEQUENCE_NUMBER" or iterator_type == "AFTER_SEQUENCE_NUMBER":
            # Use the provided sequence number
            pass
        
        shard_iterator = f"{table_name}:{sequence_number}"
        
        response = {
            "ShardIterator": shard_iterator
        }
        
        return JSONResponse(status_code=200, content=response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if stream_manager:
            await stream_manager.close()


async def handle_list_streams(body: dict, config: Config) -> JSONResponse:
    """Handle ListStreams operation."""
    stream_manager = None
    try:
        # Parse request
        table_name = body.get("TableName")
        limit = body.get("Limit", 100)
        
        # Create stream manager
        stream_manager = StreamManager(config.storage.data_directory)
        
        # List all tables
        from dyscount_core.storage.table_manager import TableManager
        table_manager = TableManager(config.storage.data_directory)
        tables = await table_manager.list_tables()
        
        streams = []
        for t in tables:
            # Skip if filtering by table name
            if table_name and t != table_name:
                continue
            
            # Check if stream is enabled
            stream_meta = await stream_manager.describe_stream(t)
            if stream_meta and stream_meta.stream_status.value == "ENABLED":
                streams.append(stream_meta.stream_arn)
                
                if len(streams) >= limit:
                    break
        
        response = {
            "Streams": [{"StreamArn": arn} for arn in streams]
        }
        
        return JSONResponse(status_code=200, content=response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
                "message": str(e)
            }
        )
    finally:
        if stream_manager:
            await stream_manager.close()
