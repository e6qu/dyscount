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
