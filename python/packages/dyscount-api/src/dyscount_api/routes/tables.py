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
    elif operation == "DescribeEndpoints":
        return await handle_describe_endpoints(body, config)
    elif operation == "GetItem":
        return await handle_get_item(body, config)
    elif operation == "PutItem":
        return await handle_put_item(body, config)
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
