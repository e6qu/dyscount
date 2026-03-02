"""Item service layer for data plane operations."""

from typing import Any

from dyscount_core.config import Config
from dyscount_core.models.errors import (
    ResourceNotFoundException,
    ValidationException,
)
from dyscount_core.models.operations import (
    ConsumedCapacity,
    GetItemRequest,
    GetItemResponse,
)
from dyscount_core.storage.table_manager import TableManager


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
