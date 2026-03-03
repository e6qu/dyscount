"""Item service layer for data plane operations."""

from typing import Any, Optional

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
from dyscount_core.storage.stream_manager import StreamManager, EventName
from dyscount_core.expressions import ConditionEvaluator


class ItemService:
    """Service layer for item operations (Data Plane)."""

    def __init__(self, config: Config):
        self.config = config
        self.table_manager = TableManager(config.storage.data_directory)
        self.stream_manager = StreamManager(config.storage.data_directory)

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
        await self.stream_manager.close()

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
        
        # Validate item size (400KB limit per DynamoDB)
        item_size = self._calculate_item_size(item)
        max_size = self.config.limits.max_item_size  # 409600 bytes = 400KB
        if item_size > max_size:
            raise ValidationException(
                f"Item size has exceeded the maximum allowed size ("
                f"{item_size} bytes > {max_size} bytes)"
            )
    
    def _calculate_item_size(self, item: dict[str, Any]) -> int:
        """Calculate the size of an item in bytes."""
        import json
        try:
            json_str = json.dumps(item, ensure_ascii=False)
            return len(json_str.encode('utf-8'))
        except (TypeError, ValueError):
            return self._estimate_item_size(item)
    
    def _estimate_item_size(self, item: dict[str, Any]) -> int:
        """Estimate item size by traversing the structure."""
        total = 0
        for attr_name, attr_value in item.items():
            total += len(attr_name.encode('utf-8'))
            total += self._estimate_attribute_value_size(attr_value)
        return total
    
    def _estimate_attribute_value_size(self, attr_value: dict[str, Any]) -> int:
        """Estimate the size of a single AttributeValue."""
        import json
        if not isinstance(attr_value, dict):
            return len(str(attr_value).encode('utf-8'))
        for type_key, value in attr_value.items():
            if type_key == 'S':
                return len(value.encode('utf-8')) if value else 0
            elif type_key == 'N':
                return len(str(value).encode('utf-8'))
            elif type_key == 'B':
                return len(str(value).encode('utf-8'))
            elif type_key == 'BOOL':
                return 1
            elif type_key == 'NULL':
                return 1
            elif type_key == 'M':
                return self._estimate_item_size(value) if value else 0
            elif type_key == 'L':
                total = 0
                if value:
                    for item in value:
                        total += self._estimate_attribute_value_size(item)
                return total
            elif type_key in ('SS', 'NS', 'BS'):
                total = 0
                if value:
                    for item in value:
                        total += len(str(item).encode('utf-8'))
                return total
        return len(json.dumps(attr_value).encode('utf-8'))
    
    def _extract_keys(self, table_name: str, item: dict[str, Any]) -> dict[str, Any]:
        """Extract primary key attributes from an item.
        
        Args:
            table_name: Name of the table
            item: The item containing key attributes
            
        Returns:
            Dict with only the key attributes
        """
        # Get key schema from table metadata
        # For now, we extract based on common patterns
        keys = {}
        for key in ['pk', 'sk', 'PK', 'SK']:
            if key in item:
                keys[key] = item[key]
        # Also check for standard DynamoDB key names
        if 'id' in item:
            keys['id'] = item['id']
        return keys

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
        
        # Write to stream
        keys = self._extract_keys(request.table_name, request.item)
        event_name = EventName.MODIFY if old_item else EventName.INSERT
        await self.stream_manager.write_stream_record(
            table_name=request.table_name,
            event_name=event_name,
            keys=keys,
            old_image=old_item,
            new_image=request.item,
        )
        
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
        
        # Write to stream if item was actually deleted
        if deleted_item:
            await self.stream_manager.write_stream_record(
                table_name=request.table_name,
                event_name=EventName.REMOVE,
                keys=request.key,
                old_image=deleted_item,
                new_image=None,
            )
        
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
        
        # Write to stream
        if new_item:
            event_name = EventName.MODIFY if old_item else EventName.INSERT
            await self.stream_manager.write_stream_record(
                table_name=request.table_name,
                event_name=event_name,
                keys=request.key,
                old_image=old_item,
                new_image=new_item,
            )
        
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


    async def transact_get_items(self, request) -> "TransactGetItemsResponse":
        """Get multiple items from one or more tables in an atomic transaction.
        
        Args:
            request: TransactGetItemsRequest with list of Get operations
            
        Returns:
            TransactGetItemsResponse with retrieved items
        """
        from dyscount_core.models.operations import TransactGetItemsResponse
        
        # Validate not empty
        if not request.transact_items:
            raise ValidationException("TransactItems cannot be empty")
        
        # Validate limit (max 100 items)
        MAX_ITEMS = 100
        if len(request.transact_items) > MAX_ITEMS:
            raise ValidationException(f"TransactItems can contain at most {MAX_ITEMS} items")
        
        # Validate all table names and check existence first
        for item in request.transact_items:
            self._validate_table_name(item.get.table_name)
            if not await self.table_manager.table_exists(item.get.table_name):
                raise ResourceNotFoundException(f"Table not found: {item.get.table_name}")
        
        # Get all items
        responses = []
        consumed_capacities = []
        total_consumed_units = 0
        
        for item in request.transact_items:
            try:
                result = await self.table_manager.get_item(
                    table_name=item.get.table_name,
                    key=item.get.key,
                )
                
                # Apply projection if specified
                if result is not None and item.get.projection_expression:
                    projected = self.table_manager._apply_projection(
                        [result],
                        item.get.projection_expression,
                        item.get.expression_attribute_names or {},
                    )
                    result = projected[0] if projected else {}
                
                responses.append(result if result is not None else {})
                
                # Track consumed capacity (0.5 RCU per item)
                total_consumed_units += 0.5
            except ValueError:
                # Item not found, return empty dict
                responses.append({})
        
        # Calculate consumed capacity
        # Group by table for ConsumedCapacity list
        table_counts = {}
        for item in request.transact_items:
            table_name = item.get.table_name
            table_counts[table_name] = table_counts.get(table_name, 0) + 0.5
        
        for table_name, units in table_counts.items():
            consumed_capacity = self._calculate_consumed_capacity(
                table_name,
                capacity_units=units,
            )
            consumed_capacity.read_capacity_units = units
            consumed_capacities.append(consumed_capacity)
        
        return TransactGetItemsResponse(
            Responses=responses,
            ConsumedCapacity=consumed_capacities if request.return_consumed_capacity else None,
        )

    async def transact_write_items(self, request) -> "TransactWriteItemsResponse":
        """Perform multiple write operations in an atomic transaction.
        
        All operations succeed or all fail (atomic).
        
        Args:
            request: TransactWriteItemsRequest with list of write operations
            
        Returns:
            TransactWriteItemsResponse with consumed capacity
            
        Raises:
            TransactionCanceledException: If any condition check fails
            ValidationException: If request is invalid
        """
        from dyscount_core.models.operations import TransactWriteItemsResponse
        from dyscount_core.models.errors import ConditionalCheckFailedException
        
        # Validate not empty
        if not request.transact_items:
            raise ValidationException("TransactItems cannot be empty")
        
        # Validate limit (max 100 items)
        MAX_ITEMS = 100
        if len(request.transact_items) > MAX_ITEMS:
            raise ValidationException(f"TransactItems can contain at most {MAX_ITEMS} items")
        
        # Validate all table names and check existence first
        for item in request.transact_items:
            table_name = self._get_table_name_from_transact_item(item)
            if table_name:
                self._validate_table_name(table_name)
                if not await self.table_manager.table_exists(table_name):
                    raise ResourceNotFoundException(f"Table not found: {table_name}")
        
        # Pre-validate all operations before executing
        # This ensures we fail fast if any operation is invalid
        for item in request.transact_items:
            self._validate_transact_write_item(item)
        
        # Execute all operations atomically
        # In a real implementation, this would use SQLite transactions
        # For now, we execute sequentially but validate all conditions first
        
        try:
            # First pass: Validate all condition checks
            for item in request.transact_items:
                await self._validate_transact_condition(item)
            
            # Second pass: Execute all operations
            for item in request.transact_items:
                await self._execute_transact_write_item(item)
        except ConditionalCheckFailedException as e:
            # Transaction failed - all operations should be rolled back
            # In a real implementation with SQLite transactions, this would be automatic
            raise ConditionalCheckFailedException(f"Transaction cancelled: {e.message}")
        
        # Calculate consumed capacity (1 WCU per write)
        table_counts = {}
        for item in request.transact_items:
            table_name = self._get_table_name_from_transact_item(item)
            if table_name:
                table_counts[table_name] = table_counts.get(table_name, 0) + 1
        
        consumed_capacities = []
        for table_name, count in table_counts.items():
            consumed_capacity = self._calculate_consumed_capacity(
                table_name,
                capacity_units=float(count),
            )
            consumed_capacity.write_capacity_units = float(count)
            consumed_capacities.append(consumed_capacity)
        
        return TransactWriteItemsResponse(
            ConsumedCapacity=consumed_capacities if request.return_consumed_capacity else None,
        )
    
    def _get_table_name_from_transact_item(self, item) -> str | None:
        """Extract table name from a TransactWriteItem."""
        if item.condition_check:
            return item.condition_check.table_name
        elif item.put:
            return item.put.table_name
        elif item.delete:
            return item.delete.table_name
        elif item.update:
            return item.update.table_name
        return None
    
    def _validate_transact_write_item(self, item) -> None:
        """Validate a single transaction write item."""
        # Check exactly one operation is specified
        ops = [item.condition_check, item.put, item.delete, item.update]
        op_count = sum(1 for op in ops if op is not None)
        
        if op_count == 0:
            raise ValidationException("TransactWriteItem must specify exactly one operation")
        if op_count > 1:
            raise ValidationException("TransactWriteItem can only specify one operation")
    
    async def _validate_transact_condition(self, item) -> None:
        """Validate condition for a transaction item."""
        from dyscount_core.expressions import ConditionEvaluator
        from dyscount_core.models.errors import ConditionalCheckFailedException
        
        condition_expression = None
        expression_attribute_names = None
        expression_attribute_values = None
        table_name = None
        key = None
        
        if item.condition_check:
            condition_expression = item.condition_check.condition_expression
            expression_attribute_names = item.condition_check.expression_attribute_names
            expression_attribute_values = item.condition_check.expression_attribute_values
            table_name = item.condition_check.table_name
            key = item.condition_check.key
        elif item.put and item.put.condition_expression:
            condition_expression = item.put.condition_expression
            expression_attribute_names = item.put.expression_attribute_names
            expression_attribute_values = item.put.expression_attribute_values
            table_name = item.put.table_name
            key = item.put.item.get("pk")  # Extract key from item
        elif item.delete and item.delete.condition_expression:
            condition_expression = item.delete.condition_expression
            expression_attribute_names = item.delete.expression_attribute_names
            expression_attribute_values = item.delete.expression_attribute_values
            table_name = item.delete.table_name
            key = item.delete.key
        elif item.update and item.update.condition_expression:
            condition_expression = item.update.condition_expression
            expression_attribute_names = item.update.expression_attribute_names
            expression_attribute_values = item.update.expression_attribute_values
            table_name = item.update.table_name
            key = item.update.key
        
        if condition_expression:
            # Get current item for condition evaluation
            current_item = await self.table_manager.get_item(table_name, key) or {}
            
            evaluator = ConditionEvaluator()
            condition_met = evaluator.evaluate(
                current_item,
                condition_expression,
                expression_attribute_names or {},
                expression_attribute_values or {},
            )
            
            if not condition_met:
                raise ConditionalCheckFailedException("Condition check failed")
    
    async def _execute_transact_write_item(self, item) -> None:
        """Execute a single transaction write item."""
        from dyscount_core.models.operations import PutItemRequest, DeleteItemRequest, UpdateItemRequest
        
        if item.condition_check:
            # Condition check only - already validated in _validate_transact_condition
            pass
        elif item.put:
            put_request = PutItemRequest(
                TableName=item.put.table_name,
                Item=item.put.item,
            )
            await self.table_manager.put_item(
                table_name=put_request.table_name,
                item=put_request.item,
            )
        elif item.delete:
            delete_request = DeleteItemRequest(
                TableName=item.delete.table_name,
                Key=item.delete.key,
            )
            await self.table_manager.delete_item(
                table_name=delete_request.table_name,
                key=delete_request.key,
            )
        elif item.update:
            update_request = UpdateItemRequest(
                TableName=item.update.table_name,
                Key=item.update.key,
                UpdateExpression=item.update.update_expression,
                ExpressionAttributeNames=item.update.expression_attribute_names,
                ExpressionAttributeValues=item.update.expression_attribute_values,
            )
            await self.table_manager.update_item(
                table_name=update_request.table_name,
                key=update_request.key,
                update_expression=update_request.update_expression,
                expression_attribute_names=update_request.expression_attribute_names,
                expression_attribute_values=update_request.expression_attribute_values,
            )
