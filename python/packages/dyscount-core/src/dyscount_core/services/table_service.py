"""Table service layer"""

import re
from datetime import datetime

from dyscount_core.config import Config
from dyscount_core.models.table import TableMetadata, TableStatus
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
from dyscount_core.storage.table_manager import TableManager
from dyscount_core.models.errors import (
    ResourceNotFoundException,
    TableAlreadyExistsException,
    ValidationException,
)


class TableService:
    """Service layer for table operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.table_manager = TableManager(config.storage.data_directory)
    
    def _validate_table_name(self, table_name: str) -> None:
        """Validate table name according to DynamoDB rules"""
        if not table_name:
            raise ValidationException("Table name cannot be empty")
        if len(table_name) < 3 or len(table_name) > 255:
            raise ValidationException("Table name must be between 3 and 255 characters")
        if not re.match(r'^[a-zA-Z0-9_.-]+$', table_name):
            raise ValidationException(
                "Table name can only contain alphanumeric characters, underscore, hyphen, and period"
            )
    
    def _validate_key_schema(self, key_schema: list) -> None:
        """Validate key schema"""
        if not key_schema or len(key_schema) == 0:
            raise ValidationException("KeySchema cannot be empty")
        if len(key_schema) > 2:
            raise ValidationException("KeySchema can have at most 2 elements")
        
        # First element must be HASH key
        if key_schema[0].KeyType != "HASH":
            raise ValidationException("First element of KeySchema must be a HASH key")
        
        # If second element exists, it must be RANGE key
        if len(key_schema) == 2 and key_schema[1].KeyType != "RANGE":
            raise ValidationException("Second element of KeySchema must be a RANGE key")
    
    def _validate_attribute_definitions(self, attr_defs: list, key_schema: list) -> None:
        """Validate attribute definitions match key schema"""
        key_attrs = {ks.AttributeName for ks in key_schema}
        defined_attrs = {ad.AttributeName for ad in attr_defs}
        
        missing = key_attrs - defined_attrs
        if missing:
            raise ValidationException(
                f"AttributeDefinitions must include all key attributes: {missing}"
            )
    
    async def create_table(self, request: CreateTableRequest) -> CreateTableResponse:
        """Create a new table"""
        # Validate table name
        self._validate_table_name(request.table_name)
        
        # Validate key schema
        self._validate_key_schema(request.key_schema)
        
        # Validate attribute definitions
        self._validate_attribute_definitions(
            request.attribute_definitions, 
            request.key_schema
        )
        
        # Check if table already exists
        if await self.table_manager.table_exists(request.table_name):
            raise TableAlreadyExistsException(
                f"Table already exists: {request.table_name}"
            )
        
        # Create the table
        await self.table_manager.create_table(
            table_name=request.table_name,
            key_schema=request.key_schema,
            attribute_definitions=request.attribute_definitions,
        )
        
        # Get the created table metadata
        metadata = await self.table_manager.describe_table(request.table_name)
        
        return CreateTableResponse(TableDescription=metadata)
    
    async def delete_table(self, request: DeleteTableRequest) -> DeleteTableResponse:
        """Delete a table"""
        # Validate table name
        self._validate_table_name(request.TableName)
        
        # Check table exists
        if not await self.table_manager.table_exists(request.TableName):
            raise ResourceNotFoundException(
                f"Table not found: {request.TableName}"
            )
        
        # Get metadata before deletion
        metadata = await self.table_manager.describe_table(request.TableName)
        
        # Set status to DELETING
        from dyscount_core.models.table import TableStatus
        metadata.table_status = TableStatus.DELETING
        
        # Delete the table
        await self.table_manager.delete_table(request.TableName)
        
        return DeleteTableResponse(TableDescription=metadata)
    
    async def list_tables(self, request: ListTablesRequest) -> ListTablesResponse:
        """List all tables with pagination"""
        # Validate ExclusiveStartTableName if provided
        if request.ExclusiveStartTableName:
            self._validate_table_name(request.ExclusiveStartTableName)
        
        # Get all tables from manager
        all_tables = await self.table_manager.list_tables()
        
        # Sort alphabetically
        all_tables.sort()
        
        # Handle pagination
        start_index = 0
        if request.ExclusiveStartTableName:
            try:
                start_index = all_tables.index(request.ExclusiveStartTableName) + 1
            except ValueError:
                # Table not found, start from beginning
                start_index = 0
        
        # Apply limit
        limit = request.Limit or 100
        end_index = start_index + limit
        
        # Get the page of tables
        table_names = all_tables[start_index:end_index]
        
        # Determine if there are more tables
        last_evaluated = None
        if end_index < len(all_tables):
            last_evaluated = all_tables[end_index - 1]
        
        return ListTablesResponse(
            TableNames=table_names,
            LastEvaluatedTableName=last_evaluated
        )
    
    async def describe_table(self, request: DescribeTableRequest) -> DescribeTableResponse:
        """Describe a table"""
        # Validate table name
        self._validate_table_name(request.TableName)
        
        # Check table exists
        if not await self.table_manager.table_exists(request.TableName):
            raise ResourceNotFoundException(
                f"Table not found: {request.TableName}"
            )
        
        # Get table metadata
        metadata = await self.table_manager.describe_table(request.TableName)
        
        return DescribeTableResponse(Table=metadata)
    
    async def describe_endpoints(self, request: DescribeEndpointsRequest) -> DescribeEndpointsResponse:
        """Describe service endpoints"""
        from dyscount_core.models.operations import Endpoint
        
        return DescribeEndpointsResponse(
            Endpoints=[
                Endpoint(
                    Address=f"{self.config.server.host}:{self.config.server.port}",
                    CachePeriodInMinutes=1440  # 24 hours
                )
            ]
        )
    
    async def close(self):
        """Close any open resources"""
        await self.table_manager.close()
