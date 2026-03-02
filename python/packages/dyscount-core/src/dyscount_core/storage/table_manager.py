"""Table management for DynamoDB-compatible storage."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import aiosqlite

from ..models.table import (
    AttributeDefinition,
    BillingMode,
    GlobalSecondaryIndex,
    KeySchemaElement,
    LocalSecondaryIndex,
    ProvisionedThroughput,
    TableMetadata,
    TableStatus,
)
from .sqlite_backend import SQLiteConnectionManager


class TableManager:
    """Manages DynamoDB table lifecycle in SQLite.
    
    Each DynamoDB table is stored as a separate SQLite database file.
    Table metadata is stored in a special `__table_metadata` table.
    
    Storage structure:
        {data_directory}/{namespace}/{table_name}.db
    """

    def __init__(
        self,
        data_directory: Path,
        namespace: str = "default",
        connection_manager: Optional[SQLiteConnectionManager] = None,
    ):
        """Initialize the table manager.
        
        Args:
            data_directory: Root directory for SQLite database files
            namespace: Logical namespace for table isolation
            connection_manager: Optional connection manager to use
        """
        self.data_directory = Path(data_directory)
        self.namespace = namespace
        self._own_connection_manager = connection_manager is None
        self.connection_manager = connection_manager or SQLiteConnectionManager()
        
        # Ensure data directory exists
        self._namespace_path.mkdir(parents=True, exist_ok=True)
    
    async def close(self) -> None:
        """Close all connections and cleanup resources."""
        if self._own_connection_manager:
            await self.connection_manager.close_all()

    @property
    def _namespace_path(self) -> Path:
        """Get the namespace directory path."""
        return self.data_directory / self.namespace

    def _get_db_path(self, table_name: str) -> Path:
        """Get the SQLite database file path for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Path to the SQLite database file
        """
        return self._namespace_path / f"{table_name}.db"

    async def create_table(
        self,
        table_name: str,
        key_schema: List[KeySchemaElement],
        attribute_definitions: List[AttributeDefinition],
        billing_mode: BillingMode = BillingMode.PROVISIONED,
        provisioned_throughput: Optional[ProvisionedThroughput] = None,
        global_secondary_indexes: Optional[List[GlobalSecondaryIndex]] = None,
        local_secondary_indexes: Optional[List[LocalSecondaryIndex]] = None,
    ) -> TableMetadata:
        """Create a new table.
        
        Args:
            table_name: Name of the table to create
            key_schema: Primary key structure
            attribute_definitions: Attribute definitions
            billing_mode: Billing mode (PROVISIONED or PAY_PER_REQUEST)
            provisioned_throughput: Provisioned throughput settings
            global_secondary_indexes: Optional list of global secondary indexes
            local_secondary_indexes: Optional list of local secondary indexes
            
        Returns:
            TableMetadata for the created table
        """
        db_path = self._get_db_path(table_name)
        
        # Check if table already exists
        if db_path.exists():
            raise ValueError(f"Table already exists: {table_name}")
        
        # Create connection (this also creates the file)
        conn = await self.connection_manager.get_connection(db_path)
        
        # Create the items table
        await self._create_items_table(conn)
        
        # Create metadata table and store table info
        await self._create_metadata_table(conn)
        
        # Generate table metadata
        now = datetime.now(timezone.utc)
        table_id = str(uuid.uuid4())
        
        metadata = TableMetadata(
            TableName=table_name,
            TableArn=f"arn:aws:dynamodb:local:{self.namespace}:table/{table_name}",
            TableId=table_id,
            TableStatus=TableStatus.ACTIVE,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            CreationDateTime=now,
            BillingModeSummary={
                "BillingMode": billing_mode.value,
            } if billing_mode else None,
            provisioned_throughput=provisioned_throughput or ProvisionedThroughput(
                ReadCapacityUnits=5, WriteCapacityUnits=5
            ),
            GlobalSecondaryIndexes=global_secondary_indexes,
            LocalSecondaryIndexes=local_secondary_indexes,
        )
        
        # Store metadata
        await self._store_metadata(conn, table_name, metadata)
        
        # Store index metadata if provided
        if global_secondary_indexes:
            await self._store_index_metadata(conn, global_secondary_indexes, "GSI")
        
        if local_secondary_indexes:
            await self._store_index_metadata(conn, local_secondary_indexes, "LSI")
        
        return metadata

    async def delete_table(self, table_name: str) -> Optional[TableMetadata]:
        """Delete a table.
        
        Args:
            table_name: Name of the table to delete
            
        Returns:
            TableMetadata of the deleted table, or None if not found
        """
        db_path = self._get_db_path(table_name)
        
        if not db_path.exists():
            return None
        
        # Get metadata before deletion
        try:
            metadata = await self.describe_table(table_name)
        except ValueError:
            metadata = None
        
        # Close connection if open
        await self.connection_manager.close_connection(db_path)
        
        # Delete the database file
        db_path.unlink()
        
        return metadata

    async def list_tables(self, limit: Optional[int] = None) -> List[str]:
        """List all table names.
        
        Args:
            limit: Maximum number of tables to return
            
        Returns:
            List of table names
        """
        tables = []
        
        if self._namespace_path.exists():
            for item in self._namespace_path.iterdir():
                if item.is_file() and item.suffix == ".db":
                    tables.append(item.stem)
        
        tables.sort()
        
        if limit:
            tables = tables[:limit]
        
        return tables

    async def describe_table(self, table_name: str) -> TableMetadata:
        """Get table metadata.
        
        Args:
            table_name: Name of the table
            
        Returns:
            TableMetadata for the table
            
        Raises:
            ValueError: If the table does not exist
        """
        db_path = self._get_db_path(table_name)
        
        if not db_path.exists():
            raise ValueError(f"Table not found: {table_name}")
        
        conn = await self.connection_manager.get_connection(db_path)
        metadata = await self._load_metadata(conn, table_name)
        
        if metadata is None:
            raise ValueError(f"Table metadata not found: {table_name}")
        
        return metadata

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if the table exists, False otherwise
        """
        db_path = self._get_db_path(table_name)
        return db_path.exists()

    async def _create_items_table(self, conn: aiosqlite.Connection) -> None:
        """Create the items table for storing DynamoDB items.
        
        Args:
            conn: SQLite connection
        """
        # Main items table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                pk BLOB NOT NULL,
                sk BLOB,
                version INTEGER DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                item_data BLOB NOT NULL,
                pk_type TEXT NOT NULL CHECK(pk_type IN ('S', 'N', 'B')),
                sk_type TEXT CHECK(sk_type IN ('S', 'N', 'B', NULL)),
                PRIMARY KEY (pk, sk)
            )
        """)
        
        # Indexes for efficient queries
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_sk ON items(sk)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_updated ON items(updated_at)
        """)
        
        await conn.commit()

    async def _create_metadata_table(self, conn: aiosqlite.Connection) -> None:
        """Create the metadata table for storing table information.
        
        Args:
            conn: SQLite connection
        """
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS __table_metadata (
                key TEXT PRIMARY KEY,
                value BLOB
            )
        """)
        
        # Index metadata table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS __index_metadata (
                index_name TEXT PRIMARY KEY,
                index_type TEXT NOT NULL CHECK(index_type IN ('GSI', 'LSI')),
                key_schema BLOB NOT NULL,
                projection_type TEXT NOT NULL,
                projected_attributes BLOB,
                index_status TEXT,
                backfilling INTEGER,
                provisioned_throughput BLOB
            )
        """)
        
        # Statistics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS __table_stats (
                stat_name TEXT PRIMARY KEY,
                stat_value INTEGER,
                last_updated INTEGER
            )
        """)
        
        await conn.commit()

    async def _store_metadata(
        self,
        conn: aiosqlite.Connection,
        table_name: str,
        metadata: TableMetadata,
    ) -> None:
        """Store table metadata in the database.
        
        Args:
            conn: SQLite connection
            table_name: Name of the table
            metadata: Table metadata to store
        """
        # Convert metadata to serializable format
        metadata_dict = metadata.model_dump(mode="json")
        
        # Store key pieces of metadata
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("table_name", table_name.encode())
        )
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("table_id", metadata.TableId.encode())
        )
        # table_status is already a string when use_enum_values=True
        table_status_value = metadata.table_status
        if hasattr(table_status_value, 'value'):
            table_status_value = table_status_value.value
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("table_status", str(table_status_value).encode())
        )
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("key_schema", json.dumps(metadata_dict.get("KeySchema", [])).encode())
        )
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("attribute_definitions", json.dumps(metadata_dict.get("AttributeDefinitions", [])).encode())
        )
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("creation_time", str(metadata.CreationDateTime.timestamp() * 1000).encode())
        )
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("billing_mode", json.dumps(metadata_dict.get("BillingModeSummary", {})).encode())
        )
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("provisioned_throughput", json.dumps(metadata_dict.get("ProvisionedThroughput", {})).encode())
        )
        
        # Store full metadata as JSON
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("full_metadata", json.dumps(metadata_dict).encode())
        )
        
        # Store GSI/LSI info in metadata
        if metadata.GlobalSecondaryIndexes:
            await conn.execute(
                "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
                ("global_secondary_indexes", json.dumps(metadata_dict.get("GlobalSecondaryIndexes", [])).encode())
            )
        
        if metadata.LocalSecondaryIndexes:
            await conn.execute(
                "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
                ("local_secondary_indexes", json.dumps(metadata_dict.get("LocalSecondaryIndexes", [])).encode())
            )
        
        await conn.commit()

    async def _store_index_metadata(
        self,
        conn: aiosqlite.Connection,
        indexes: List[GlobalSecondaryIndex] | List[LocalSecondaryIndex],
        index_type: str,
    ) -> None:
        """Store index metadata in the database.
        
        Args:
            conn: SQLite connection
            indexes: List of indexes to store
            index_type: Type of index ('GSI' or 'LSI')
        """
        for index in indexes:
            # Serialize key schema
            key_schema_json = json.dumps([ks.model_dump(mode="json") for ks in index.KeySchema])
            
            # Extract projection info
            projection = index.Projection
            projection_type = projection.get("ProjectionType", "ALL")
            projected_attrs = projection.get("NonKeyAttributes", [])
            
            # Serialize provisioned throughput for GSI
            provisioned_throughput_json = None
            if hasattr(index, 'ProvisionedThroughput') and index.ProvisionedThroughput:
                provisioned_throughput_json = json.dumps(index.ProvisionedThroughput.model_dump(mode="json"))
            
            await conn.execute(
                """
                INSERT INTO __index_metadata (
                    index_name, index_type, key_schema, projection_type, 
                    projected_attributes, index_status, backfilling, provisioned_throughput
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    index.IndexName,
                    index_type,
                    key_schema_json.encode(),
                    projection_type,
                    json.dumps(projected_attrs).encode() if projected_attrs else None,
                    "ACTIVE",
                    0,  # backfilling = false
                    provisioned_throughput_json.encode() if provisioned_throughput_json else None,
                )
            )
        
        await conn.commit()

    async def _load_metadata(
        self,
        conn: aiosqlite.Connection,
        table_name: str,
    ) -> Optional[TableMetadata]:
        """Load table metadata from the database.
        
        Args:
            conn: SQLite connection
            table_name: Name of the table
            
        Returns:
            TableMetadata if found, None otherwise
        """
        cursor = await conn.execute(
            "SELECT value FROM __table_metadata WHERE key = ?",
            ("full_metadata",)
        )
        row = await cursor.fetchone()
        
        if row is None:
            return None
        
        metadata_dict = json.loads(row[0].decode())
        return TableMetadata.model_validate(metadata_dict)

    async def _update_metadata(
        self,
        table_name: str,
        metadata: TableMetadata,
    ) -> None:
        """Update table metadata in the database.
        
        Args:
            table_name: Name of the table
            metadata: Updated table metadata
        """
        db_path = self._get_db_path(table_name)
        conn = await self.connection_manager.get_connection(db_path)
        
        # Convert metadata to serializable format
        metadata_dict = metadata.model_dump(mode="json")
        
        # Update full metadata
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("full_metadata", json.dumps(metadata_dict).encode())
        )
        
        # Update individual fields
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("billing_mode", json.dumps(metadata_dict.get("BillingModeSummary", {})).encode())
        )
        await conn.execute(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
            ("provisioned_throughput", json.dumps(metadata_dict.get("ProvisionedThroughput", {})).encode())
        )
        
        # Update GSI info
        if metadata.GlobalSecondaryIndexes:
            await conn.execute(
                "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
                ("global_secondary_indexes", json.dumps(metadata_dict.get("GlobalSecondaryIndexes", [])).encode())
            )
        
        await conn.commit()

    async def _add_gsi(
        self,
        table_name: str,
        gsi: GlobalSecondaryIndex,
    ) -> None:
        """Add a global secondary index to the table.
        
        Args:
            table_name: Name of the table
            gsi: Global secondary index to add
        """
        db_path = self._get_db_path(table_name)
        conn = await self.connection_manager.get_connection(db_path)
        
        # Serialize key schema
        key_schema_json = json.dumps([ks.model_dump(mode="json") for ks in gsi.KeySchema])
        
        # Extract projection info
        projection = gsi.Projection
        projection_type = projection.get("ProjectionType", "ALL")
        projected_attrs = projection.get("NonKeyAttributes", [])
        
        # Serialize provisioned throughput
        provisioned_throughput_json = None
        if gsi.ProvisionedThroughput:
            # Handle both dict and model instances
            if isinstance(gsi.ProvisionedThroughput, dict):
                provisioned_throughput_json = json.dumps(gsi.ProvisionedThroughput)
            else:
                provisioned_throughput_json = json.dumps(gsi.ProvisionedThroughput.model_dump(mode="json"))
        
        await conn.execute(
            """
            INSERT INTO __index_metadata (
                index_name, index_type, key_schema, projection_type, 
                projected_attributes, index_status, backfilling, provisioned_throughput
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                gsi.IndexName,
                "GSI",
                key_schema_json.encode(),
                projection_type,
                json.dumps(projected_attrs).encode() if projected_attrs else None,
                "ACTIVE",
                0,  # backfilling = false
                provisioned_throughput_json.encode() if provisioned_throughput_json else None,
            )
        )
        
        await conn.commit()

    async def _remove_gsi(
        self,
        table_name: str,
        index_name: str,
    ) -> None:
        """Remove a global secondary index from the table.
        
        Args:
            table_name: Name of the table
            index_name: Name of the index to remove
        """
        db_path = self._get_db_path(table_name)
        conn = await self.connection_manager.get_connection(db_path)
        
        await conn.execute(
            "DELETE FROM __index_metadata WHERE index_name = ? AND index_type = ?",
            (index_name, "GSI")
        )
        
        await conn.commit()

    # =========================================================================
    # Item Operations (Data Plane)
    # =========================================================================

    async def get_item(
        self,
        table_name: str,
        key: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get a single item by its primary key.
        
        Args:
            table_name: Name of the table
            key: Primary key as a dict of attribute name to AttributeValue dict
                e.g., {"pk": {"S": "user#123"}, "sk": {"S": "profile"}}
        
        Returns:
            The item as a dict of attribute name to AttributeValue dict, or None if not found
            e.g., {"pk": {"S": "user#123"}, "name": {"S": "John"}}
        
        Raises:
            ValueError: If table does not exist
        """
        db_path = self._get_db_path(table_name)
        
        if not db_path.exists():
            raise ValueError(f"Table does not exist: {table_name}")
        
        # Get table metadata to understand key schema
        conn = await self.connection_manager.get_connection(db_path)
        metadata = await self._load_metadata(conn, table_name)
        
        if metadata is None:
            raise ValueError(f"Table metadata not found: {table_name}")
        
        # Extract partition key and sort key from the key dict
        key_schema = metadata.KeySchema
        partition_key_name = key_schema[0].AttributeName
        partition_key_value = key.get(partition_key_name)
        
        if partition_key_value is None:
            raise ValueError(f"Missing partition key attribute: {partition_key_name}")
        
        # Serialize partition key
        pk_bytes = self._serialize_key_value(partition_key_value)
        pk_type = self._get_key_type(partition_key_value)
        
        # Handle sort key if present
        sk_bytes = None
        sk_type = None
        if len(key_schema) > 1:
            sort_key_name = key_schema[1].AttributeName
            sort_key_value = key.get(sort_key_name)
            
            if sort_key_value is None:
                raise ValueError(f"Missing sort key attribute: {sort_key_name}")
            
            sk_bytes = self._serialize_key_value(sort_key_value)
            sk_type = self._get_key_type(sort_key_value)
        
        # Use empty blob for NULL sk lookup
        if sk_bytes is None:
            sk_bytes = b''
        
        # Query the database
        cursor = await conn.execute(
            "SELECT item_data FROM items WHERE pk = ? AND sk = ?",
            (pk_bytes, sk_bytes)
        )
        
        row = await cursor.fetchone()
        
        if row is None:
            return None
        
        # Deserialize item data
        import msgpack
        item_data = msgpack.unpackb(row[0], raw=False)
        
        return item_data

    def _serialize_key_value(self, key_value: Any) -> bytes:
        """Serialize a key AttributeValue to bytes for storage.
        
        Args:
            key_value: AttributeValue dict, e.g., {"S": "user#123"}
        
        Returns:
            Serialized bytes
        """
        import msgpack
        
        # Handle DynamoDB JSON format
        if isinstance(key_value, dict):
            return msgpack.packb(key_value, use_bin_type=True)
        
        # If it's already a simple value, wrap it
        return msgpack.packb(key_value, use_bin_type=True)

    def _get_key_type(self, key_value: Any) -> str:
        """Extract the DynamoDB type from a key AttributeValue.
        
        Args:
            key_value: AttributeValue dict, e.g., {"S": "user#123"}
        
        Returns:
            Type string: 'S', 'N', or 'B'
        """
        if isinstance(key_value, dict):
            # DynamoDB JSON format
            if "S" in key_value:
                return "S"
            elif "N" in key_value:
                return "N"
            elif "B" in key_value:
                return "B"
        
        raise ValueError(f"Invalid key value format: {key_value}")

    async def put_item(
        self,
        table_name: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Put an item into a table.
        
        Creates a new item or replaces an existing item.
        
        Args:
            table_name: Name of the table
            item: Item data as dict of attribute name to AttributeValue
            condition_expression: Optional condition expression to evaluate
            expression_attribute_names: Optional name placeholders
            expression_attribute_values: Optional value placeholders
        
        Returns:
            Previous item data if item existed, None otherwise
        
        Raises:
            ValueError: If table does not exist or condition is not met
        """
        import msgpack
        
        db_path = self._get_db_path(table_name)
        
        if not db_path.exists():
            raise ValueError(f"Table does not exist: {table_name}")
        
        # Get table metadata to understand key schema
        conn = await self.connection_manager.get_connection(db_path)
        metadata = await self._load_metadata(conn, table_name)
        
        if metadata is None:
            raise ValueError(f"Table metadata not found: {table_name}")
        
        # Extract partition key and sort key from item
        key_schema = metadata.KeySchema
        partition_key_name = key_schema[0].AttributeName
        partition_key_value = item.get(partition_key_name)
        
        if partition_key_value is None:
            raise ValueError(f"Missing partition key attribute: {partition_key_name}")
        
        # Serialize partition key
        pk_bytes = self._serialize_key_value(partition_key_value)
        pk_type = self._get_key_type(partition_key_value)
        
        # Handle sort key if present
        sk_bytes = None
        sk_type = None
        if len(key_schema) > 1:
            sort_key_name = key_schema[1].AttributeName
            sort_key_value = item.get(sort_key_name)
            
            if sort_key_value is None:
                raise ValueError(f"Missing sort key attribute: {sort_key_name}")
            
            sk_bytes = self._serialize_key_value(sort_key_value)
            sk_type = self._get_key_type(sort_key_value)
        
        # Use empty blob for NULL sk lookup
        lookup_sk = sk_bytes if sk_bytes is not None else b''
        
        # Check if item already exists (for returning old values)
        cursor = await conn.execute(
            "SELECT item_data FROM items WHERE pk = ? AND sk = ?",
            (pk_bytes, lookup_sk)
        )
        
        row = await cursor.fetchone()
        old_item = None
        if row is not None:
            old_item = msgpack.unpackb(row[0], raw=False)
        
        # Evaluate condition expression if provided
        if condition_expression:
            from dyscount_core.expressions import ConditionEvaluator
            evaluator = ConditionEvaluator()
            
            # Use existing item for condition evaluation, or empty dict if new item
            # Condition is evaluated against the current state of the item in the database
            condition_item = old_item if old_item is not None else {}
            
            condition_met = evaluator.evaluate(
                condition_item,
                condition_expression,
                expression_attribute_names or {},
                expression_attribute_values or {},
            )
            
            if not condition_met:
                raise ValueError("ConditionalCheckFailedException: Condition expression is not met")
        
        # Serialize item data
        item_data = msgpack.packb(item, use_bin_type=True)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        # Use empty blob for NULL sk to make UPSERT work correctly
        if sk_bytes is None:
            sk_bytes = b''
            sk_type = ''
        
        # Insert or replace item
        await conn.execute(
            """
            INSERT INTO items (pk, sk, pk_type, sk_type, item_data, created_at, updated_at, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(pk, sk) DO UPDATE SET
                item_data = excluded.item_data,
                updated_at = excluded.updated_at,
                version = items.version + 1
            """,
            (pk_bytes, sk_bytes, pk_type, sk_type, item_data, now_ms, now_ms)
        )
        
        await conn.commit()
        
        return old_item

    async def delete_item(
        self,
        table_name: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Delete an item from a table.
        
        Args:
            table_name: Name of the table
            key: Primary key as a dict of attribute name to AttributeValue dict
            condition_expression: Optional condition expression to evaluate
            expression_attribute_names: Optional name placeholders
            expression_attribute_values: Optional value placeholders
        
        Returns:
            The deleted item data if item existed, None otherwise
        
        Raises:
            ValueError: If table does not exist or condition is not met
        """
        import msgpack
        
        db_path = self._get_db_path(table_name)
        
        if not db_path.exists():
            raise ValueError(f"Table does not exist: {table_name}")
        
        # Get table metadata to understand key schema
        conn = await self.connection_manager.get_connection(db_path)
        metadata = await self._load_metadata(conn, table_name)
        
        if metadata is None:
            raise ValueError(f"Table metadata not found: {table_name}")
        
        # Extract partition key and sort key from the key dict
        key_schema = metadata.KeySchema
        partition_key_name = key_schema[0].AttributeName
        partition_key_value = key.get(partition_key_name)
        
        if partition_key_value is None:
            raise ValueError(f"Missing partition key attribute: {partition_key_name}")
        
        # Serialize partition key
        pk_bytes = self._serialize_key_value(partition_key_value)
        
        # Handle sort key if present
        sk_bytes = None
        if len(key_schema) > 1:
            sort_key_name = key_schema[1].AttributeName
            sort_key_value = key.get(sort_key_name)
            
            if sort_key_value is None:
                raise ValueError(f"Missing sort key attribute: {sort_key_name}")
            
            sk_bytes = self._serialize_key_value(sort_key_value)
        
        # Use empty blob for NULL sk
        lookup_sk = sk_bytes if sk_bytes is not None else b''
        
        # Get the item before deleting (for ReturnValues)
        cursor = await conn.execute(
            "SELECT item_data FROM items WHERE pk = ? AND sk = ?",
            (pk_bytes, lookup_sk)
        )
        row = await cursor.fetchone()
        
        deleted_item = None
        if row is not None:
            deleted_item = msgpack.unpackb(row[0], raw=False)
            
            # Evaluate condition expression if provided
            if condition_expression:
                from dyscount_core.expressions import ConditionEvaluator
                evaluator = ConditionEvaluator()
                
                condition_met = evaluator.evaluate(
                    deleted_item,
                    condition_expression,
                    expression_attribute_names or {},
                    expression_attribute_values or {},
                )
                
                if not condition_met:
                    raise ValueError("ConditionalCheckFailedException: Condition expression is not met")
            
            # Delete the item
            await conn.execute(
                "DELETE FROM items WHERE pk = ? AND sk = ?",
                (pk_bytes, lookup_sk)
            )
            await conn.commit()
        
        return deleted_item

    async def update_item(
        self,
        table_name: str,
        key: dict[str, Any],
        update_expression: str,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        condition_expression: str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Update an item in a table.
        
        Args:
            table_name: Name of the table
            key: Primary key as a dict of attribute name to AttributeValue dict
            update_expression: The UpdateExpression to apply
            expression_attribute_names: Optional name placeholders
            expression_attribute_values: Optional value placeholders
            condition_expression: Optional condition expression to evaluate
        
        Returns:
            Tuple of (old_item, new_item)
        
        Raises:
            ValueError: If table does not exist or expression is invalid
        """
        from dyscount_core.expressions import ExpressionEvaluator
        
        import msgpack
        
        db_path = self._get_db_path(table_name)
        
        if not db_path.exists():
            raise ValueError(f"Table does not exist: {table_name}")
        
        # Get table metadata to understand key schema
        conn = await self.connection_manager.get_connection(db_path)
        metadata = await self._load_metadata(conn, table_name)
        
        if metadata is None:
            raise ValueError(f"Table metadata not found: {table_name}")
        
        # Extract partition key and sort key from the key dict
        key_schema = metadata.KeySchema
        partition_key_name = key_schema[0].AttributeName
        partition_key_value = key.get(partition_key_name)
        
        if partition_key_value is None:
            raise ValueError(f"Missing partition key attribute: {partition_key_name}")
        
        # Serialize partition key
        pk_bytes = self._serialize_key_value(partition_key_value)
        
        # Handle sort key if present
        sk_bytes = None
        if len(key_schema) > 1:
            sort_key_name = key_schema[1].AttributeName
            sort_key_value = key.get(sort_key_name)
            
            if sort_key_value is None:
                raise ValueError(f"Missing sort key attribute: {sort_key_name}")
            
            sk_bytes = self._serialize_key_value(sort_key_value)
        
        # Use empty blob for NULL sk
        lookup_sk = sk_bytes if sk_bytes is not None else b''
        
        # Get the existing item
        cursor = await conn.execute(
            "SELECT item_data FROM items WHERE pk = ? AND sk = ?",
            (pk_bytes, lookup_sk)
        )
        row = await cursor.fetchone()
        
        old_item = None
        if row is not None:
            old_item = msgpack.unpackb(row[0], raw=False)
            new_item = dict(old_item)  # Copy for modification
        else:
            # Item doesn't exist - create new with just the key
            new_item = {partition_key_name: partition_key_value}
            if len(key_schema) > 1:
                new_item[key_schema[1].AttributeName] = key[key_schema[1].AttributeName]
        
        # Evaluate condition expression if provided
        if condition_expression:
            from dyscount_core.expressions import ConditionEvaluator
            condition_evaluator = ConditionEvaluator()
            
            # Use old_item for condition evaluation (existing item or None)
            condition_item = old_item if old_item is not None else {}
            
            condition_met = condition_evaluator.evaluate(
                condition_item,
                condition_expression,
                expression_attribute_names or {},
                expression_attribute_values or {},
            )
            
            if not condition_met:
                raise ValueError("ConditionalCheckFailedException: Condition expression is not met")
        
        # Apply the update expression
        evaluator = ExpressionEvaluator()
        try:
            new_item = evaluator.evaluate(
                new_item,
                update_expression,
                expression_attribute_names or {},
                expression_attribute_values or {},
            )
        except ValueError as e:
            raise ValueError(f"Invalid UpdateExpression: {e}") from e
        
        # Serialize and store the updated item
        item_data = msgpack.packb(new_item, use_bin_type=True)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        # Get pk_type from the serialized key
        pk_type = self._get_key_type(partition_key_value)
        sk_type = self._get_key_type(key[key_schema[1].AttributeName]) if len(key_schema) > 1 else ""
        
        await conn.execute(
            """
            INSERT INTO items (pk, sk, pk_type, sk_type, item_data, created_at, updated_at, version)
            VALUES (?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM items WHERE pk = ? AND sk = ?), ?), ?, 
                    COALESCE((SELECT version FROM items WHERE pk = ? AND sk = ?), 0) + 1)
            ON CONFLICT(pk, sk) DO UPDATE SET
                item_data = excluded.item_data,
                updated_at = excluded.updated_at,
                version = excluded.version
            """,
            (pk_bytes, lookup_sk, pk_type, sk_type, item_data, pk_bytes, lookup_sk, now_ms, now_ms, pk_bytes, lookup_sk)
        )
        await conn.commit()
        
        return old_item, new_item


    # =========================================================================
    # Query & Scan Operations (Data Plane)
    # =========================================================================

    async def query(
        self,
        table_name: str,
        key_condition_expression: str,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        scan_index_forward: bool = True,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Query items in a table using key conditions.
        
        Args:
            table_name: Name of the table
            key_condition_expression: Key condition expression
            expression_attribute_names: Optional name placeholders
            expression_attribute_values: Optional value placeholders
            filter_expression: Optional filter expression for post-filtering
            projection_expression: Optional projection for attribute selection
            scan_index_forward: If True, ascending order; if False, descending
            limit: Maximum number of items to evaluate
            exclusive_start_key: Primary key to start from (for pagination)
            
        Returns:
            Tuple of (items, last_evaluated_key)
            items: List of matching items
            last_evaluated_key: Key for next page, or None if no more items
            
        Raises:
            ValueError: If table does not exist or expression is invalid
        """
        from dyscount_core.expressions import ConditionEvaluator
        from dyscount_core.expressions.key_condition_parser import KeyConditionExpressionParser
        
        import msgpack
        
        db_path = self._get_db_path(table_name)
        
        if not db_path.exists():
            raise ValueError(f"Table does not exist: {table_name}")
        
        conn = await self.connection_manager.get_connection(db_path)
        metadata = await self._load_metadata(conn, table_name)
        
        if metadata is None:
            raise ValueError(f"Table metadata not found: {table_name}")
        
        # Parse key condition expression
        parser = KeyConditionExpressionParser()
        try:
            pk_condition, sk_condition = parser.parse(
                key_condition_expression,
                expression_attribute_names or {},
            )
        except ValueError as e:
            raise ValueError(f"Invalid KeyConditionExpression: {e}") from e
        
        # Build SQL query
        # Get partition key value
        pk_value = self._get_key_value_from_condition(
            pk_condition,
            expression_attribute_values or {},
        )
        pk_bytes = self._serialize_key_value(pk_value)
        
        # Build WHERE clause
        where_conditions = ["pk = ?"]
        params = [pk_bytes]
        
        # Handle sort key condition
        if sk_condition:
            sk_clause, sk_params = self._build_sort_key_condition(
                sk_condition,
                metadata,
                expression_attribute_values or {},
            )
            where_conditions.append(sk_clause)
            params.extend(sk_params)
        
        where_clause = " AND ".join(where_conditions)
        
        # Handle pagination (exclusive_start_key)
        if exclusive_start_key:
            # We need to filter in Python for complex pagination
            # For now, we'll fetch and filter
            pass
        
        # Build ORDER BY
        order_by = "ASC" if scan_index_forward else "DESC"
        
        # Build limit
        limit_clause = ""
        if limit:
            limit_clause = f" LIMIT {limit + 1}"  # +1 to check for more items
        
        # Execute query
        sql = f"""
            SELECT item_data FROM items
            WHERE {where_clause}
            ORDER BY sk {order_by}
            {limit_clause}
        """
        
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        
        # Deserialize items
        items = []
        for row in rows:
            item = msgpack.unpackb(row[0], raw=False)
            items.append(item)
        
        # Handle limit and pagination
        last_evaluated_key = None
        if limit and len(items) > limit:
            items = items[:limit]
            # Return last item's key as last_evaluated_key
            last_item = items[-1]
            last_evaluated_key = self._extract_key(last_item, metadata)
        
        # Apply filter expression if provided
        if filter_expression:
            evaluator = ConditionEvaluator()
            filtered_items = []
            for item in items:
                try:
                    if evaluator.evaluate(
                        item,
                        filter_expression,
                        expression_attribute_names or {},
                        expression_attribute_values or {},
                    ):
                        filtered_items.append(item)
                except ValueError:
                    # Item doesn't have attributes for filter, skip
                    pass
            items = filtered_items
        
        # Apply projection if provided
        if projection_expression:
            items = self._apply_projection(items, projection_expression, expression_attribute_names or {})
        
        return items, last_evaluated_key
    
    def _get_key_value_from_condition(
        self,
        condition,
        expression_attribute_values: dict[str, Any],
    ) -> Any:
        """Extract key value from condition and expression values."""
        if not condition.values:
            raise ValueError("Condition has no values")
        
        value_ref = condition.values[0]
        
        if value_ref.startswith(":"):
            if value_ref not in expression_attribute_values:
                raise ValueError(f"Undefined value placeholder: {value_ref}")
            return expression_attribute_values[value_ref]
        
        return value_ref
    
    def _build_sort_key_condition(
        self,
        sk_condition,
        metadata,
        expression_attribute_values: dict[str, Any],
    ) -> tuple[str, list]:
        """Build SQL WHERE clause for sort key condition."""
        from dyscount_core.expressions.key_condition_parser import KeyConditionType
        
        # Serialize sort key value
        sk_value = self._get_key_value_from_condition(sk_condition, expression_attribute_values)
        sk_bytes = self._serialize_key_value(sk_value)
        
        if sk_condition.condition_type == KeyConditionType.EQ:
            return "sk = ?", [sk_bytes]
        elif sk_condition.condition_type == KeyConditionType.LT:
            return "sk < ?", [sk_bytes]
        elif sk_condition.condition_type == KeyConditionType.LE:
            return "sk <= ?", [sk_bytes]
        elif sk_condition.condition_type == KeyConditionType.GT:
            return "sk > ?", [sk_bytes]
        elif sk_condition.condition_type == KeyConditionType.GE:
            return "sk >= ?", [sk_bytes]
        elif sk_condition.condition_type == KeyConditionType.BETWEEN:
            lower = expression_attribute_values.get(sk_condition.values[0], sk_condition.values[0])
            upper = expression_attribute_values.get(sk_condition.values[1], sk_condition.values[1])
            lower_bytes = self._serialize_key_value(lower)
            upper_bytes = self._serialize_key_value(upper)
            return "sk >= ? AND sk <= ?", [lower_bytes, upper_bytes]
        elif sk_condition.condition_type == KeyConditionType.BEGINS_WITH:
            # For begins_with, we need to handle it differently
            # We'll need to filter in Python or use LIKE
            prefix = sk_condition.values[0]
            if prefix.startswith(":"):
                prefix_value = expression_attribute_values.get(prefix, prefix)
                prefix_bytes = self._serialize_key_value(prefix_value)
                # Use hex comparison for prefix matching (approximate)
                # This is a simplification - proper implementation would need more work
                return "sk >= ?", [prefix_bytes]
        
        raise ValueError(f"Unsupported sort key condition: {sk_condition.condition_type}")
    
    def _extract_key(self, item: dict, metadata) -> dict:
        """Extract primary key from item."""
        key_schema = metadata.KeySchema
        key = {}
        for key_element in key_schema:
            attr_name = key_element.AttributeName
            if attr_name in item:
                key[attr_name] = item[attr_name]
        return key
    
    def _apply_projection(
        self,
        items: list[dict],
        projection_expression: str,
        expression_attribute_names: dict[str, str],
    ) -> list[dict]:
        """Apply projection expression to items."""
        # Parse projection expression (comma-separated attribute names)
        # Handle #name placeholders
        projected_items = []
        
        for item in items:
            projected_item = {}
            # Always include primary key attributes
            # (This is simplified - would need proper key extraction)
            
            # Parse projection attributes
            for attr_ref in projection_expression.split(","):
                attr_ref = attr_ref.strip()
                attr_name = expression_attribute_names.get(attr_ref, attr_ref)
                if attr_name in item:
                    projected_item[attr_name] = item[attr_name]
            
            projected_items.append(projected_item)
        
        return projected_items

    async def scan(
        self,
        table_name: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any] | None]:
        """Scan items in a table.
        
        Args:
            table_name: Name of the table
            filter_expression: Optional filter expression
            projection_expression: Optional projection for attribute selection
            expression_attribute_names: Optional name placeholders
            expression_attribute_values: Optional value placeholders
            limit: Maximum number of items to evaluate
            exclusive_start_key: Primary key to start from (for pagination)
            segment: For parallel scan, the segment to scan
            total_segments: For parallel scan, the total number of segments
            
        Returns:
            Tuple of (items, scanned_count, last_evaluated_key)
            items: List of matching items (after filter)
            scanned_count: Number of items scanned (before filter)
            last_evaluated_key: Key for next page, or None if no more items
            
        Raises:
            ValueError: If table does not exist
        """
        from dyscount_core.expressions import ConditionEvaluator
        
        import msgpack
        
        db_path = self._get_db_path(table_name)
        
        if not db_path.exists():
            raise ValueError(f"Table does not exist: {table_name}")
        
        conn = await self.connection_manager.get_connection(db_path)
        metadata = await self._load_metadata(conn, table_name)
        
        if metadata is None:
            raise ValueError(f"Table metadata not found: {table_name}")
        
        # Build query
        # For parallel scan, we'd use modulo on pk hash
        # For now, we scan all items
        
        limit_clause = ""
        if limit:
            # +1 to check if there are more items
            limit_clause = f" LIMIT {limit + 1}"
        
        # Build OFFSET for pagination using exclusive_start_key
        offset_clause = ""
        offset_params = []
        if exclusive_start_key:
            # We'd need to find the position of this key
            # For simplicity, we'll fetch all and slice
            pass
        
        sql = f"""
            SELECT item_data FROM items
            ORDER BY pk, sk
            {limit_clause}
        """
        
        cursor = await conn.execute(sql, offset_params)
        rows = await cursor.fetchall()
        
        # Deserialize items
        all_items = []
        for row in rows:
            item = msgpack.unpackb(row[0], raw=False)
            all_items.append(item)
        
        scanned_count = len(all_items)
        
        # Handle pagination
        last_evaluated_key = None
        if limit and len(all_items) > limit:
            all_items = all_items[:limit]
            last_item = all_items[-1]
            last_evaluated_key = self._extract_key(last_item, metadata)
        
        # Apply filter expression if provided
        items = all_items
        if filter_expression:
            evaluator = ConditionEvaluator()
            filtered_items = []
            for item in all_items:
                try:
                    if evaluator.evaluate(
                        item,
                        filter_expression,
                        expression_attribute_names or {},
                        expression_attribute_values or {},
                    ):
                        filtered_items.append(item)
                except ValueError:
                    pass
            items = filtered_items
        
        # Apply projection if provided
        if projection_expression:
            items = self._apply_projection(items, projection_expression, expression_attribute_names or {})
        
        return items, scanned_count, last_evaluated_key
