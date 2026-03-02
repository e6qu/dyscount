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
    UpdateTableRequest,
    UpdateTableResponse,
    TagResourceRequest,
    TagResourceResponse,
    UntagResourceRequest,
    UntagResourceResponse,
    ListTagsOfResourceRequest,
    ListTagsOfResourceResponse,
    UpdateTimeToLiveRequest,
    UpdateTimeToLiveResponse,
    DescribeTimeToLiveRequest,
    DescribeTimeToLiveResponse,
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
    
    def _validate_gsi_key_schema(
        self, 
        gsi_list: list, 
        attr_defs: list,
        table_key_schema: list
    ) -> None:
        """Validate GSI key schemas and attribute definitions.
        
        Args:
            gsi_list: List of GlobalSecondaryIndex definitions
            attr_defs: Table attribute definitions
            table_key_schema: Table's primary key schema
        """
        if not gsi_list:
            return
        
        # DynamoDB limit: 20 GSIs per table
        if len(gsi_list) > 20:
            raise ValidationException("Cannot create more than 20 global secondary indexes")
        
        defined_attrs = {ad.AttributeName: ad.AttributeType for ad in attr_defs}
        table_hash_key = table_key_schema[0].AttributeName
        
        for gsi in gsi_list:
            # Validate GSI has a name
            if not gsi.IndexName:
                raise ValidationException("GlobalSecondaryIndex must have an IndexName")
            
            # Validate GSI key schema
            if not gsi.KeySchema or len(gsi.KeySchema) == 0:
                raise ValidationException(f"KeySchema cannot be empty for index {gsi.IndexName}")
            if len(gsi.KeySchema) > 2:
                raise ValidationException(f"KeySchema can have at most 2 elements for index {gsi.IndexName}")
            
            # First element must be HASH key
            if gsi.KeySchema[0].KeyType != "HASH":
                raise ValidationException(f"First element of KeySchema must be a HASH key for index {gsi.IndexName}")
            
            # If second element exists, it must be RANGE key
            if len(gsi.KeySchema) == 2 and gsi.KeySchema[1].KeyType != "RANGE":
                raise ValidationException(f"Second element of KeySchema must be a RANGE key for index {gsi.IndexName}")
            
            # Validate GSI key attributes are defined
            for ks in gsi.KeySchema:
                if ks.AttributeName not in defined_attrs:
                    raise ValidationException(
                        f"AttributeDefinitions must include all key attributes for index {gsi.IndexName}: {ks.AttributeName}"
                    )
            
            # GSI hash key must be different from table hash key (DynamoDB requirement)
            gsi_hash_key = gsi.KeySchema[0].AttributeName
            if gsi_hash_key == table_hash_key and len(gsi.KeySchema) == 1:
                # This is allowed if GSI has a range key different from table's
                pass  # Actually, DynamoDB allows this - the GSI just won't be very useful
    
    def _validate_lsi_key_schema(
        self, 
        lsi_list: list, 
        attr_defs: list,
        table_key_schema: list
    ) -> None:
        """Validate LSI key schemas and attribute definitions.
        
        Args:
            lsi_list: List of LocalSecondaryIndex definitions
            attr_defs: Table attribute definitions
            table_key_schema: Table's primary key schema
        """
        if not lsi_list:
            return
        
        # DynamoDB limit: 5 LSIs per table
        if len(lsi_list) > 5:
            raise ValidationException("Cannot create more than 5 local secondary indexes")
        
        # LSI requires a table with a composite key (HASH + RANGE)
        if len(table_key_schema) < 2:
            raise ValidationException(
                "LocalSecondaryIndexes can only be created on tables with a composite primary key (HASH + RANGE)"
            )
        
        defined_attrs = {ad.AttributeName: ad.AttributeType for ad in attr_defs}
        table_hash_key = table_key_schema[0].AttributeName
        
        for lsi in lsi_list:
            # Validate LSI has a name
            if not lsi.IndexName:
                raise ValidationException("LocalSecondaryIndex must have an IndexName")
            
            # Validate LSI key schema
            if not lsi.KeySchema or len(lsi.KeySchema) == 0:
                raise ValidationException(f"KeySchema cannot be empty for index {lsi.IndexName}")
            if len(lsi.KeySchema) > 2:
                raise ValidationException(f"KeySchema can have at most 2 elements for index {lsi.IndexName}")
            
            # First element must be HASH key (same as table's hash key)
            if lsi.KeySchema[0].KeyType != "HASH":
                raise ValidationException(f"First element of KeySchema must be a HASH key for index {lsi.IndexName}")
            
            # LSI hash key must match table hash key
            if lsi.KeySchema[0].AttributeName != table_hash_key:
                raise ValidationException(
                    f"LocalSecondaryIndex hash key must match table hash key for index {lsi.IndexName}"
                )
            
            # If second element exists, it must be RANGE key
            if len(lsi.KeySchema) == 2 and lsi.KeySchema[1].KeyType != "RANGE":
                raise ValidationException(f"Second element of KeySchema must be a RANGE key for index {lsi.IndexName}")
            
            # Validate LSI key attributes are defined
            for ks in lsi.KeySchema:
                if ks.AttributeName not in defined_attrs:
                    raise ValidationException(
                        f"AttributeDefinitions must include all key attributes for index {lsi.IndexName}: {ks.AttributeName}"
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
        
        # Validate GSI if provided
        if request.global_secondary_indexes:
            self._validate_gsi_key_schema(
                request.global_secondary_indexes,
                request.attribute_definitions,
                request.key_schema
            )
        
        # Validate LSI if provided
        if request.local_secondary_indexes:
            self._validate_lsi_key_schema(
                request.local_secondary_indexes,
                request.attribute_definitions,
                request.key_schema
            )
        
        # Create the table
        await self.table_manager.create_table(
            table_name=request.table_name,
            key_schema=request.key_schema,
            attribute_definitions=request.attribute_definitions,
            global_secondary_indexes=request.global_secondary_indexes,
            local_secondary_indexes=request.local_secondary_indexes,
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
    
    async def update_table(self, request: UpdateTableRequest) -> UpdateTableResponse:
        """Update a table's settings and indexes.
        
        Supports:
        - Updating provisioned throughput
        - Updating billing mode
        - Creating global secondary indexes
        - Deleting global secondary indexes
        """
        # Validate table name
        self._validate_table_name(request.TableName)
        
        # Check table exists
        if not await self.table_manager.table_exists(request.TableName):
            raise ResourceNotFoundException(
                f"Table not found: {request.TableName}"
            )
        
        # Get current table metadata
        metadata = await self.table_manager.describe_table(request.TableName)
        
        # Validate and process attribute definitions if provided
        if request.AttributeDefinitions:
            self._validate_attribute_definitions(
                request.AttributeDefinitions,
                metadata.KeySchema
            )
            # Merge new attribute definitions with existing
            existing_attrs = {ad.AttributeName: ad for ad in metadata.AttributeDefinitions}
            new_attrs = {ad.AttributeName: ad for ad in request.AttributeDefinitions}
            existing_attrs.update(new_attrs)
            metadata.AttributeDefinitions = list(existing_attrs.values())
        
        # Process GSI updates
        if request.GlobalSecondaryIndexUpdates:
            await self._process_gsi_updates(
                request.TableName,
                request.GlobalSecondaryIndexUpdates,
                metadata
            )
        
        # Update billing mode if provided
        if request.BillingMode:
            billing_mode_value = request.BillingMode
            if hasattr(billing_mode_value, 'value'):
                billing_mode_value = billing_mode_value.value
            metadata.billing_mode_summary = {"BillingMode": billing_mode_value}
        
        # Update provisioned throughput if provided
        if request.ProvisionedThroughput:
            metadata.provisioned_throughput = request.ProvisionedThroughput
        
        # Update deletion protection if provided
        if request.DeletionProtectionEnabled is not None:
            metadata.DeletionProtectionEnabled = request.DeletionProtectionEnabled
        
        # Store updated metadata
        await self.table_manager._update_metadata(request.TableName, metadata)
        
        return UpdateTableResponse(TableDescription=metadata)
    
    async def _process_gsi_updates(
        self,
        table_name: str,
        gsi_updates: list,
        metadata: TableMetadata
    ) -> None:
        """Process global secondary index updates.
        
        Args:
            table_name: Name of the table
            gsi_updates: List of GSI update operations
            metadata: Current table metadata (will be modified)
        """
        from dyscount_core.models.table import GlobalSecondaryIndex
        
        # Get existing GSIs
        existing_gsis = {gsi.IndexName: gsi for gsi in (metadata.GlobalSecondaryIndexes or [])}
        
        for update in gsi_updates:
            # Check for Create operation
            if "Create" in update:
                create_info = update["Create"]
                index_name = create_info["IndexName"]
                
                # Check if index already exists
                if index_name in existing_gsis:
                    raise ValidationException(
                        f"GlobalSecondaryIndex already exists: {index_name}"
                    )
                
                # Check total GSI limit (max 20)
                if len(existing_gsis) >= 20:
                    raise ValidationException(
                        "Cannot create more than 20 global secondary indexes"
                    )
                
                # Create new GSI
                new_gsi = GlobalSecondaryIndex(
                    IndexName=index_name,
                    KeySchema=create_info["KeySchema"],
                    Projection=create_info.get("Projection", {"ProjectionType": "ALL"}),
                    ProvisionedThroughput=create_info.get("ProvisionedThroughput"),
                )
                
                # Validate the new GSI
                self._validate_gsi_key_schema(
                    [new_gsi],
                    metadata.AttributeDefinitions,
                    metadata.KeySchema
                )
                
                # Add to metadata (status CREATING initially)
                # In real DynamoDB, this would be CREAING while backfilling
                # For simplicity, we set it to ACTIVE
                existing_gsis[index_name] = new_gsi
                
                # Store the index in the database
                await self.table_manager._add_gsi(table_name, new_gsi)
            
            # Check for Delete operation
            elif "Delete" in update:
                delete_info = update["Delete"]
                index_name = delete_info["IndexName"]
                
                # Check if index exists
                if index_name not in existing_gsis:
                    raise ResourceNotFoundException(
                        f"GlobalSecondaryIndex not found: {index_name}"
                    )
                
                # Remove from metadata
                del existing_gsis[index_name]
                
                # Remove from database
                await self.table_manager._remove_gsi(table_name, index_name)
            
            # Check for Update operation (provisioned throughput only)
            elif "Update" in update:
                update_info = update["Update"]
                index_name = update_info["IndexName"]
                
                # Check if index exists
                if index_name not in existing_gsis:
                    raise ResourceNotFoundException(
                        f"GlobalSecondaryIndex not found: {index_name}"
                    )
                
                # Update provisioned throughput
                gsi = existing_gsis[index_name]
                if "ProvisionedThroughput" in update_info:
                    gsi.ProvisionedThroughput = update_info["ProvisionedThroughput"]
        
        # Update metadata with modified GSIs
        metadata.GlobalSecondaryIndexes = list(existing_gsis.values())
    
    async def close(self):
        """Close any open resources"""
        await self.table_manager.close()


    # =====================================================================
    # Tagging Operations
    # =====================================================================
    
    async def tag_resource(self, request: TagResourceRequest) -> TagResourceResponse:
        """Add tags to a table resource.
        
        Args:
            request: TagResourceRequest with resource ARN and tags
            
        Returns:
            TagResourceResponse (empty on success)
        """
        # Extract table name from ARN
        # ARN format: arn:aws:dynamodb:<region>:<account>:table/<table_name>
        table_name = self._extract_table_name_from_arn(request.resource_arn)
        
        # Validate table name
        self._validate_table_name(table_name)
        
        # Check table exists
        if not await self.table_manager.table_exists(table_name):
            raise ResourceNotFoundException(
                f"Table not found: {table_name}"
            )
        
        # Store tags
        await self.table_manager._store_tags(table_name, request.tags)
        
        return TagResourceResponse()
    
    async def untag_resource(self, request: UntagResourceRequest) -> UntagResourceResponse:
        """Remove tags from a table resource.
        
        Args:
            request: UntagResourceRequest with resource ARN and tag keys
            
        Returns:
            UntagResourceResponse (empty on success)
        """
        # Extract table name from ARN
        table_name = self._extract_table_name_from_arn(request.resource_arn)
        
        # Validate table name
        self._validate_table_name(table_name)
        
        # Check table exists
        if not await self.table_manager.table_exists(table_name):
            raise ResourceNotFoundException(
                f"Table not found: {table_name}"
            )
        
        # Remove tags
        await self.table_manager._remove_tags(table_name, request.tag_keys)
        
        return UntagResourceResponse()
    
    async def list_tags_of_resource(self, request: ListTagsOfResourceRequest) -> ListTagsOfResourceResponse:
        """List tags on a table resource.
        
        Args:
            request: ListTagsOfResourceRequest with resource ARN
            
        Returns:
            ListTagsOfResourceResponse with list of tags
        """
        # Extract table name from ARN
        table_name = self._extract_table_name_from_arn(request.resource_arn)
        
        # Validate table name
        self._validate_table_name(table_name)
        
        # Check table exists
        if not await self.table_manager.table_exists(table_name):
            raise ResourceNotFoundException(
                f"Table not found: {table_name}"
            )
        
        # Get tags
        tags = await self.table_manager._get_tags(table_name)
        
        return ListTagsOfResourceResponse(Tags=tags)
    
    def _extract_table_name_from_arn(self, arn: str) -> str:
        """Extract table name from resource ARN.
        
        Args:
            arn: Resource ARN (arn:aws:dynamodb:<region>:<account>:table/<table_name>)
            
        Returns:
            Table name
            
        Raises:
            ValidationException: If ARN format is invalid
        """
        # Handle both formats:
        # arn:aws:dynamodb:<region>:<account>:table/<table_name>
        # arn:aws:dynamodb:local:<namespace>:table/<table_name>
        
        if not arn.startswith("arn:aws:dynamodb:"):
            raise ValidationException(f"Invalid resource ARN: {arn}")
        
        # Split by '/' and get the last part (table name)
        parts = arn.split("/")
        if len(parts) < 2:
            raise ValidationException(f"Invalid resource ARN format: {arn}")
        
        table_name = parts[-1]
        if not table_name:
            raise ValidationException(f"Invalid resource ARN: no table name found")
        
        return table_name

    # ==========================================================================
    # Time-to-Live (TTL) Operations
    # ==========================================================================

    async def update_time_to_live(
        self,
        request: UpdateTimeToLiveRequest,
    ) -> UpdateTimeToLiveResponse:
        """Enable or disable TTL on a table.
        
        Args:
            request: UpdateTimeToLiveRequest with table name and TTL spec
            
        Returns:
            UpdateTimeToLiveResponse with updated TTL specification
            
        Raises:
            ResourceNotFoundException: If table doesn't exist
            ValidationException: If TTL attribute is invalid
        """
        table_name = request.table_name
        
        # Validate table exists
        if not await self.table_manager.table_exists(table_name):
            raise ResourceNotFoundException(
                f"Table not found: {table_name}"
            )
        
        # Validate TTL attribute name
        ttl_spec = request.time_to_live_specification
        ttl_attribute = ttl_spec.attribute_name
        
        if not ttl_attribute:
            raise ValidationException("TTL attribute name cannot be empty")
        
        # Update TTL configuration
        result = await self.table_manager.update_time_to_live(
            table_name,
            ttl_attribute,
            ttl_spec.enabled,
        )
        
        return UpdateTimeToLiveResponse(
            time_to_live_specification=ttl_spec,
        )

    async def describe_time_to_live(
        self,
        request: DescribeTimeToLiveRequest,
    ) -> DescribeTimeToLiveResponse:
        """Describe TTL configuration for a table.
        
        Args:
            request: DescribeTimeToLiveRequest with table name
            
        Returns:
            DescribeTimeToLiveResponse with TTL description
            
        Raises:
            ResourceNotFoundException: If table doesn't exist
        """
        table_name = request.table_name
        
        # Validate table exists
        if not await self.table_manager.table_exists(table_name):
            raise ResourceNotFoundException(
                f"Table not found: {table_name}"
            )
        
        # Get TTL configuration
        ttl_desc = await self.table_manager.describe_time_to_live(table_name)
        
        from dyscount_core.models.operations import TimeToLiveDescription
        
        return DescribeTimeToLiveResponse(
            time_to_live_description=TimeToLiveDescription(
                attribute_name=ttl_desc.get("AttributeName"),
                time_to_live_status=ttl_desc.get("TimeToLiveStatus", "DISABLED"),
            ),
        )
    
    async def close(self):
        """Close any open resources"""
        await self.table_manager.close()
