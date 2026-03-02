"""Item service layer for data plane operations."""

from typing import Any

from dyscount_core.config import Config
from dyscount_core.models.errors import (
    ResourceNotFoundException,
    ValidationException,
    ConditionalCheckFailedException,
)
from dyscount_core.models.operations import (
    UpdateItemRequest,
    UpdateItemResponse,
    DeleteItemRequest,
    DeleteItemResponse,
    PutItemRequest,
    PutItemResponse,
    ConsumedCapacity,
    GetItemRequest,
    GetItemResponse,
)
from dyscount_core.storage.table_manager import TableManager
from dyscount_core.expressions import ConditionEvaluator


class ItemService:
    """Service layer for item operations (Data Plane)."""

    def __init__(self, config: Config):
        self.config = config
        self.table_manager = TableManager(config.storage.data_directory)

    def _validate_table_name(self, table_name: str) -> None:
        """Validate table name according to DynamoDB rules."""
        if not table_name:
            raise ValidationException("Table name cannot be empty")
        if len(table_name) < 3 or len(table_name) > 255:
            raise ValidationException("Table name must be between 3 and 255 characters")
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', table_name):
            raise ValidationException(
                "Table name can only contain alphanumeric characters, underscore, hyphen,"
            )

    def _validate_key(self, key: dict[str, Any], table_name: str) -> None:
        """Validate the primary key format.
        
        Args:
            key: The key dict with AttributeValue format
            table_name: Name of the table (for error messages)
        """
        if not key:
            raise ValidationException("Key cannot be empty")

        if not isinstance(key, dict):
            raise ValidationException("Key must be a map")

        # Each value should be an AttributeValue (dict with single type key)
        for attr_name, attr_value in key.items():
            if not isinstance(attr_value, dict):
                raise ValidationException(
                    f"Key attribute '{attr_name}' must be an AttributeValue map"
                )

            # Check that exactly one type is specified
            valid_types = {'S', 'N', 'B', 'BOOL', 'NULL', 'M', 'L', 'SS', 'NS', 'BS'}
            type_keys = [k for k in attr_value.keys() if k in valid_types]

            if len(type_keys) != 1:
                raise ValidationException(
                    f"Key attribute '{attr_name}' must have exactly one type descriptor, "
                    f"got: {type_keys}"
                )

    def _calculate_consumed_capacity(
        self,
        table_name: str,
        capacity_units: float = 0.5,  # Eventually consistent read
    ) -> ConsumedCapacity:
        """Calculate consumed capacity for an operation.
        
        Args:
            table_name: Name of the table
            capacity_units: Number of capacity units consumed
        
        Returns:
            ConsumedCapacity object
        """
        return ConsumedCapacity(
            TableName=table_name,
            CapacityUnits=capacity_units,
            ReadCapacityUnits=capacity_units,
        )

    async def get_item(self, request: GetItemRequest) -> GetItemResponse:
        """Get a single item by its primary key.
        
        Args:
            request: GetItemRequest with table name and key
        
        Returns:
            GetItemResponse with item data (if found)
        
        Raises:
            ResourceNotFoundException: If table does not exist
            ValidationException: If request is invalid
        """
        # Validate table name
        self._validate_table_name(request.table_name)

        # Validate key
        self._validate_key(request.key, request.table_name)

        # Check table exists
        if not await self.table_manager.table_exists(request.table_name):
            raise ResourceNotFoundException(
                f"Table not found: {request.table_name}"
            )

        # Get the item
        try:
            item = await self.table_manager.get_item(
                table_name=request.table_name,
                key=request.key,
            )
        except ValueError as e:
            # Re-raise as validation exception if it's a key format issue
            if "key" in str(e).lower():
                raise ValidationException(str(e))
            raise

        # Calculate consumed capacity
        # Eventually consistent read = 0.5 RCU, strongly consistent = 1 RCU
        capacity_units = 1.0 if request.consistent_read else 0.5
        consumed_capacity = self._calculate_consumed_capacity(
            request.table_name,
            capacity_units,
        )

        # Build response
        response = GetItemResponse(
            Item=item,  # Will be None if item not found (which is valid)
            ConsumedCapacity=consumed_capacity,
        )

        return response

    async def close(self):
        """Close any open resources."""
        await self.table_manager.close()

    def _validate_item(self, item: dict[str, Any], table_name: str) -> None:
        """Validate the item format.
        
        Args:
            item: The item dict with AttributeValue format
            table_name: Name of the table (for error messages)
        """
        if not item:
            raise ValidationException("Item cannot be empty")
        
        if not isinstance(item, dict):
            raise ValidationException("Item must be a map")
        
        # Each value should be an AttributeValue (dict with single type key)
        for attr_name, attr_value in item.items():
            if not isinstance(attr_value, dict):
                raise ValidationException(
                    f"Item attribute '{attr_name}' must be an AttributeValue map"
                )
            
            # Check that exactly one type is specified
            valid_types = {'S', 'N', 'B', 'BOOL', 'NULL', 'M', 'L', 'SS', 'NS', 'BS'}
            type_keys = [k for k in attr_value if k in valid_types]
            
            if len(type_keys) != 1:
                raise ValidationException(
                    f"Item attribute '{attr_name}' must have exactly one type descriptor, "
                    f"got: {type_keys}"
                )
    
    async def put_item(self, request: PutItemRequest) -> PutItemResponse:
        """Put an item into a table.
        
        Args:
            request: PutItemRequest with table name and item
        
        Returns:
            PutItemResponse with old attributes if ReturnValues=ALL_OLD
        
        Raises:
            ResourceNotFoundException: If table does not exist
            ValidationException: If request is invalid
        """
        from dyscount_core.models.operations import PutItemResponse
        
        # Validate table name
        self._validate_table_name(request.table_name)
        
        # Validate item
        self._validate_item(request.item, request.table_name)
        
        # Check table exists
        if not await self.table_manager.table_exists(request.table_name):
            raise ResourceNotFoundException(
                f"Table not found: {request.table_name}"
            )
        
        # Put the item
        try:
            old_item = await self.table_manager.put_item(
                table_name=request.table_name,
                item=request.item,
                condition_expression=request.condition_expression,
                expression_attribute_names=request.expression_attribute_names,
                expression_attribute_values=request.expression_attribute_values,
            )
        except ValueError as e:
            if "key" in str(e).lower():
                raise ValidationException(str(e)) from None
            if "ConditionalCheckFailedException" in str(e):
                raise ConditionalCheckFailedException(str(e).replace("ConditionalCheckFailedException: ", "")) from None
            raise
        
        # Calculate consumed capacity
        # Write operation = 1 WCU
        consumed_capacity = self._calculate_consumed_capacity(
            request.table_name,
            capacity_units=1.0,
        )
        consumed_capacity.write_capacity_units = 1.0
        
        # Build response
        response = PutItemResponse(
            consumed_capacity=consumed_capacity,
        )
        
        # Handle ReturnValues
        if request.return_values == "ALL_OLD" and old_item is not None:
            response.attributes = old_item
        
        return response

    async def delete_item(self, request: DeleteItemRequest) -> DeleteItemResponse:
        """Delete an item from a table.
        
        Args:
            request: DeleteItemRequest with table name and key
        
        Returns:
            DeleteItemResponse with old attributes if ReturnValues=ALL_OLD
        
        Raises:
            ResourceNotFoundException: If table does not exist
            ValidationException: If request is invalid
        """
        from dyscount_core.models.operations import DeleteItemResponse
        
        # Validate table name
        self._validate_table_name(request.table_name)
        
        # Validate key
        self._validate_key(request.key, request.table_name)
        
        # Check table exists
        if not await self.table_manager.table_exists(request.table_name):
            raise ResourceNotFoundException(
                f"Table not found: {request.table_name}"
            )
        
        # Delete the item
        try:
            deleted_item = await self.table_manager.delete_item(
                table_name=request.table_name,
                key=request.key,
                condition_expression=request.condition_expression,
                expression_attribute_names=request.expression_attribute_names,
                expression_attribute_values=request.expression_attribute_values,
            )
        except ValueError as e:
            if "key" in str(e).lower():
                raise ValidationException(str(e)) from None
            if "ConditionalCheckFailedException" in str(e):
                raise ConditionalCheckFailedException(str(e).replace("ConditionalCheckFailedException: ", "")) from None
            raise
        
        # Calculate consumed capacity
        # Write operation = 1 WCU
        consumed_capacity = self._calculate_consumed_capacity(
            request.table_name,
            capacity_units=1.0,
        )
        consumed_capacity.write_capacity_units = 1.0
        
        # Build response
        response = DeleteItemResponse(
            consumed_capacity=consumed_capacity,
        )
        
        # Handle ReturnValues
        if request.return_values == "ALL_OLD" and deleted_item is not None:
            response.attributes = deleted_item
        
        return response

    async def update_item(self, request: UpdateItemRequest) -> UpdateItemResponse:
        """Update an item in a table.
        
        Args:
            request: UpdateItemRequest with table name, key, and update expression
        
        Returns:
            UpdateItemResponse with old/new attributes based on ReturnValues
        
        Raises:
            ResourceNotFoundException: If table does not exist
            ValidationException: If request is invalid
        """
        from dyscount_core.models.operations import UpdateItemResponse
        
        # Validate table name
        self._validate_table_name(request.table_name)
        
        # Validate key
        self._validate_key(request.key, request.table_name)
        
        # Check table exists
        if not await self.table_manager.table_exists(request.table_name):
            raise ResourceNotFoundException(
                f"Table not found: {request.table_name}"
            )
        
        # Update the item
        try:
            old_item, new_item = await self.table_manager.update_item(
                table_name=request.table_name,
                key=request.key,
                update_expression=request.update_expression,
                expression_attribute_names=request.expression_attribute_names,
                expression_attribute_values=request.expression_attribute_values,
                condition_expression=request.condition_expression,
            )
        except ValueError as e:
            if "ConditionalCheckFailedException" in str(e):
                raise ConditionalCheckFailedException(str(e).replace("ConditionalCheckFailedException: ", "")) from None
            if "key" in str(e).lower() or "UpdateExpression" in str(e):
                raise ValidationException(str(e)) from None
            raise
        
        # Calculate consumed capacity
        # Write operation = 1 WCU
        consumed_capacity = self._calculate_consumed_capacity(
            request.table_name,
            capacity_units=1.0,
        )
        consumed_capacity.write_capacity_units = 1.0
        
        # Build response
        response = UpdateItemResponse(
            consumed_capacity=consumed_capacity,
        )
        
        # Handle ReturnValues
        return_values = request.return_values or "NONE"
        
        if return_values == "ALL_OLD" and old_item is not None:
            response.attributes = old_item
        elif return_values == "ALL_NEW":
            response.attributes = new_item
        elif return_values == "UPDATED_OLD" and old_item is not None:
            # Return only attributes that were updated
            updated_attrs = {}
            for key in new_item:
                if key in old_item:
                    updated_attrs[key] = old_item[key]
            if updated_attrs:
                response.attributes = updated_attrs
        elif return_values == "UPDATED_NEW":
            # Return only attributes that were updated
            updated_attrs = {}
            for key in new_item:
                if old_item is None or key not in old_item or old_item.get(key) != new_item.get(key):
                    updated_attrs[key] = new_item[key]
            if updated_attrs:
                response.attributes = updated_attrs
        
        return response


    async def query(self, request) -> "QueryResponse":
        """Query items in a table.
        
        Args:
            request: QueryRequest with table name and key conditions
            
        Returns:
            QueryResponse with matching items
        """
        from dyscount_core.models.operations import QueryResponse
        
        # Validate table name
        self._validate_table_name(request.table_name)
        
        # Check table exists
        if not await self.table_manager.table_exists(request.table_name):
            raise ResourceNotFoundException(
                f"Table not found: {request.table_name}"
            )
        
        # Execute query
        try:
            items, last_evaluated_key = await self.table_manager.query(
                table_name=request.table_name,
                key_condition_expression=request.key_condition_expression,
                expression_attribute_names=request.expression_attribute_names,
                expression_attribute_values=request.expression_attribute_values,
                filter_expression=request.filter_expression,
                projection_expression=request.projection_expression,
                scan_index_forward=request.scan_index_forward,
                limit=request.limit,
                exclusive_start_key=request.exclusive_start_key,
            )
        except ValueError as e:
            if "expression" in str(e).lower():
                raise ValidationException(str(e)) from None
            raise
        
        # Calculate consumed capacity
        # Query: 1 RCU per 4KB read
        consumed_capacity = self._calculate_consumed_capacity(
            request.table_name,
            capacity_units=float(len(items)) * 0.5,
        )
        consumed_capacity.read_capacity_units = float(len(items)) * 0.5
        
        # Build response
        response = QueryResponse(
            Items=items,
            Count=len(items),
            ScannedCount=len(items),
            LastEvaluatedKey=last_evaluated_key,
            ConsumedCapacity=consumed_capacity,
        )
        
        return response

    async def scan(self, request) -> "ScanResponse":
        """Scan items in a table.
        
        Args:
            request: ScanRequest with table name and optional filters
            
        Returns:
            ScanResponse with matching items
        """
        from dyscount_core.models.operations import ScanResponse
        
        # Validate table name
        self._validate_table_name(request.table_name)
        
        # Check table exists
        if not await self.table_manager.table_exists(request.table_name):
            raise ResourceNotFoundException(
                f"Table not found: {request.table_name}"
            )
        
        # Execute scan
        try:
            items, scanned_count, last_evaluated_key = await self.table_manager.scan(
                table_name=request.table_name,
                filter_expression=request.filter_expression,
                projection_expression=request.projection_expression,
                expression_attribute_names=request.expression_attribute_names,
                expression_attribute_values=request.expression_attribute_values,
                limit=request.limit,
                exclusive_start_key=request.exclusive_start_key,
                segment=request.segment,
                total_segments=request.total_segments,
            )
        except ValueError as e:
            if "expression" in str(e).lower():
                raise ValidationException(str(e)) from None
            raise
        
        # Calculate consumed capacity
        # Scan: 1 RCU per 4KB read
        consumed_capacity = self._calculate_consumed_capacity(
            request.table_name,
            capacity_units=float(scanned_count) * 0.5,
        )
        consumed_capacity.read_capacity_units = float(scanned_count) * 0.5
        
        # Build response
        response = ScanResponse(
            Items=items,
            Count=len(items),
            ScannedCount=scanned_count,
            LastEvaluatedKey=last_evaluated_key,
            ConsumedCapacity=consumed_capacity,
        )
        
        return response


    async def batch_get_item(self, request) -> "BatchGetItemResponse":
        """Get multiple items from one or more tables.
        
        Args:
            request: BatchGetItemRequest with table names and keys
            
        Returns:
            BatchGetItemResponse with retrieved items
        """
        from dyscount_core.models.operations import BatchGetItemResponse, BatchGetItemTableRequest
        from dyscount_core.models.operations import GetItemRequest
        
        # Validate and process each table
        responses: dict[str, list[dict]] = {}
        unprocessed_keys: dict[str, BatchGetItemTableRequest] = {}
        consumed_capacities: list = []
        
        # DynamoDB limit: 100 items per batch get
        MAX_ITEMS = 100
        total_items = sum(len(table_req.keys) for table_req in request.request_items.values())
        
        if total_items > MAX_ITEMS:
            # Mark excess items as unprocessed
            remaining_capacity = MAX_ITEMS
            for table_name, table_req in request.request_items.items():
                if remaining_capacity <= 0:
                    # All remaining items are unprocessed
                    unprocessed_keys[table_name] = table_req
                    continue
                
                if len(table_req.keys) <= remaining_capacity:
                    # All keys fit
                    remaining_capacity -= len(table_req.keys)
                else:
                    # Split keys
                    processed_keys = table_req.keys[:remaining_capacity]
                    unprocessed_keys_list = table_req.keys[remaining_capacity:]
                    table_req.keys = processed_keys
                    unprocessed_keys[table_name] = BatchGetItemTableRequest(
                        Keys=unprocessed_keys_list,
                        ProjectionExpression=table_req.projection_expression,
                        ExpressionAttributeNames=table_req.expression_attribute_names,
                        ConsistentRead=table_req.consistent_read,
                    )
                    remaining_capacity = 0
        
        # Process each table
        for table_name, table_req in request.request_items.items():
            if table_name in unprocessed_keys and not table_req.keys:
                continue  # All keys were unprocessed
            
            # Validate table name
            self._validate_table_name(table_name)
            
            # Check table exists
            if not await self.table_manager.table_exists(table_name):
                raise ResourceNotFoundException(f"Table not found: {table_name}")
            
            # Get each item
            table_items = []
            for key in table_req.keys:
                get_request = GetItemRequest(
                    TableName=table_name,
                    Key=key,
                    ProjectionExpression=table_req.projection_expression,
                    ExpressionAttributeNames=table_req.expression_attribute_names,
                    ConsistentRead=table_req.consistent_read,
                )
                
                try:
                    item = await self.table_manager.get_item(table_name, key)
                    if item is not None:
                        table_items.append(item)
                except ValueError:
                    # Item not found, skip
                    pass
            
            responses[table_name] = table_items
            
            # Calculate consumed capacity (0.5 RCU per item)
            consumed_capacity = self._calculate_consumed_capacity(
                table_name,
                capacity_units=len(table_req.keys) * 0.5,
            )
            consumed_capacity.read_capacity_units = len(table_req.keys) * 0.5
            consumed_capacities.append(consumed_capacity)
        
        # Build response
        response = BatchGetItemResponse(
            Responses=responses,
            UnprocessedKeys=unprocessed_keys if unprocessed_keys else None,
            ConsumedCapacity=consumed_capacities if request.return_consumed_capacity else None,
        )
        
        return response

    async def batch_write_item(self, request) -> "BatchWriteItemResponse":
        """Put or delete multiple items in one or more tables.
        
        Args:
            request: BatchWriteItemRequest with table names and write requests
            
        Returns:
            BatchWriteItemResponse with unprocessed items
        """
        from dyscount_core.models.operations import BatchWriteItemResponse, PutItemRequest, DeleteItemRequest
        from dyscount_core.models.operations import BatchWriteItemTableRequest
        
        # DynamoDB limit: 25 items per batch write
        MAX_ITEMS = 25
        total_items = sum(len(write_requests) for write_requests in request.request_items.values())
        
        unprocessed_items: dict[str, list[BatchWriteItemTableRequest]] = {}
        consumed_capacities: list = []
        
        if total_items > MAX_ITEMS:
            # Mark excess items as unprocessed
            remaining_capacity = MAX_ITEMS
            for table_name, write_requests in request.request_items.items():
                if remaining_capacity <= 0:
                    # All remaining items are unprocessed
                    unprocessed_items[table_name] = write_requests
                    continue
                
                if len(write_requests) <= remaining_capacity:
                    # All items fit
                    remaining_capacity -= len(write_requests)
                else:
                    # Split items
                    processed = write_requests[:remaining_capacity]
                    unprocessed = write_requests[remaining_capacity:]
                    request.request_items[table_name] = processed
                    unprocessed_items[table_name] = unprocessed
                    remaining_capacity = 0
        
        # Process each table
        for table_name, write_requests in request.request_items.items():
            if table_name in unprocessed_items and not write_requests:
                continue  # All items were unprocessed
            
            # Validate table name
            self._validate_table_name(table_name)
            
            # Check table exists
            if not await self.table_manager.table_exists(table_name):
                raise ResourceNotFoundException(f"Table not found: {table_name}")
            
            # Process each write request
            for write_req in write_requests:
                try:
                    if write_req.put_request is not None:
                        # Put item
                        put_request = PutItemRequest(
                            TableName=table_name,
                            Item=write_req.put_request.item,
                        )
                        await self.table_manager.put_item(
                            table_name=put_request.table_name,
                            item=put_request.item,
                        )
                    elif write_req.delete_request is not None:
                        # Delete item
                        delete_request = DeleteItemRequest(
                            TableName=table_name,
                            Key=write_req.delete_request.key,
                        )
                        await self.table_manager.delete_item(
                            table_name=delete_request.table_name,
                            key=delete_request.key,
                        )
                except ValueError as e:
                    # Add to unprocessed
                    if table_name not in unprocessed_items:
                        unprocessed_items[table_name] = []
                    unprocessed_items[table_name].append(write_req)
            
            # Calculate consumed capacity (1 WCU per item)
            consumed_capacity = self._calculate_consumed_capacity(
                table_name,
                capacity_units=len(write_requests) * 1.0,
            )
            consumed_capacity.write_capacity_units = len(write_requests) * 1.0
            consumed_capacities.append(consumed_capacity)
        
        # Build response
        response = BatchWriteItemResponse(
            UnprocessedItems=unprocessed_items if unprocessed_items else None,
            ConsumedCapacity=consumed_capacities if request.return_consumed_capacity else None,
        )
        
        return response
