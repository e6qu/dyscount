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
    KeySchemaElement,
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
    ) -> TableMetadata:
        """Create a new table.
        
        Args:
            table_name: Name of the table to create
            key_schema: Primary key structure
            attribute_definitions: Attribute definitions
            billing_mode: Billing mode (PROVISIONED or PAY_PER_REQUEST)
            provisioned_throughput: Provisioned throughput settings
            
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
        )
        
        # Store metadata
        await self._store_metadata(conn, table_name, metadata)
        
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
