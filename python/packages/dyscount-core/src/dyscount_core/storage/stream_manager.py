"""DynamoDB Streams management for change data capture."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from .sqlite_backend import SQLiteConnectionManager


class StreamViewType(str, Enum):
    """Stream view type determines what data is captured."""
    KEYS_ONLY = "KEYS_ONLY"
    NEW_IMAGE = "NEW_IMAGE"
    OLD_IMAGE = "OLD_IMAGE"
    NEW_AND_OLD_IMAGES = "NEW_AND_OLD_IMAGES"


class StreamStatus(str, Enum):
    """Stream status."""
    ENABLING = "ENABLING"
    ENABLED = "ENABLED"
    DISABLING = "DISABLING"
    DISABLED = "DISABLED"


class EventName(str, Enum):
    """Stream event names."""
    INSERT = "INSERT"
    MODIFY = "MODIFY"
    REMOVE = "REMOVE"


@dataclass
class StreamRecord:
    """A single stream record."""
    event_id: str
    event_name: EventName
    event_version: str
    event_source: str
    aws_region: str
    approximate_creation_date_time: int
    keys: dict[str, Any]
    old_image: Optional[dict[str, Any]]
    new_image: Optional[dict[str, Any]]
    sequence_number: str
    size_bytes: int
    stream_view_type: StreamViewType


@dataclass
class StreamMetadata:
    """Stream metadata."""
    stream_arn: str
    stream_label: str
    stream_status: StreamStatus
    stream_view_type: StreamViewType
    creation_date_time: int
    table_name: str


class StreamManager:
    """Manages DynamoDB Streams for change data capture.
    
    Each table with streams enabled gets a separate stream log stored in
    the table's SQLite database.
    """

    def __init__(
        self,
        data_directory: Path,
        namespace: str = "default",
        connection_manager: Optional[SQLiteConnectionManager] = None,
    ):
        """Initialize the stream manager.
        
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
        """Get the SQLite database file path for a table."""
        return self._namespace_path / f"{table_name}.db"

    async def _get_connection(self, table_name: str) -> aiosqlite.Connection:
        """Get a database connection for a table."""
        db_path = self._get_db_path(table_name)
        return await self.connection_manager.get_connection(db_path)

    async def _ensure_stream_tables(self, table_name: str) -> None:
        """Ensure stream tables exist in the database."""
        conn = await self._get_connection(table_name)
        
        # Stream metadata table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS __stream_metadata (
                stream_arn TEXT PRIMARY KEY,
                stream_label TEXT NOT NULL,
                stream_status TEXT NOT NULL,
                stream_view_type TEXT NOT NULL,
                creation_date_time INTEGER NOT NULL,
                table_name TEXT NOT NULL
            )
        """)
        
        # Stream records table (WAL-like log)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS __stream_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_arn TEXT NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                event_name TEXT NOT NULL,
                event_version TEXT NOT NULL DEFAULT '1.1',
                event_source TEXT NOT NULL DEFAULT 'aws:dynamodb',
                aws_region TEXT NOT NULL DEFAULT 'local',
                approximate_creation_date_time INTEGER NOT NULL,
                keys_json TEXT NOT NULL,
                old_image_json TEXT,
                new_image_json TEXT,
                sequence_number TEXT NOT NULL UNIQUE,
                size_bytes INTEGER NOT NULL,
                stream_view_type TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stream_records_arn 
            ON __stream_records(stream_arn)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stream_records_sequence 
            ON __stream_records(sequence_number)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stream_records_expires 
            ON __stream_records(expires_at)
        """)
        
        await conn.commit()

    def _generate_stream_arn(self, table_name: str) -> str:
        """Generate a stream ARN for a table."""
        stream_uuid = uuid.uuid4()
        return f"arn:aws:dynamodb:local:000000000000:table/{table_name}/stream/{stream_uuid}"

    def _generate_sequence_number(self) -> str:
        """Generate a unique sequence number."""
        # Use timestamp + counter format like DynamoDB
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp() * 1000)  # milliseconds
        return f"{timestamp}{uuid.uuid4().hex[:8]}"

    async def enable_stream(
        self,
        table_name: str,
        stream_view_type: StreamViewType,
    ) -> StreamMetadata:
        """Enable streams on a table.
        
        Args:
            table_name: Name of the table
            stream_view_type: Type of data to capture
            
        Returns:
            StreamMetadata for the enabled stream
        """
        await self._ensure_stream_tables(table_name)
        
        conn = await self._get_connection(table_name)
        
        # Check if stream already exists
        async with conn.execute(
            "SELECT stream_arn FROM __stream_metadata WHERE table_name = ?",
            (table_name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                # Update existing stream
                stream_arn = row[0]
                await conn.execute(
                    """UPDATE __stream_metadata 
                       SET stream_status = ?, stream_view_type = ?
                       WHERE stream_arn = ?""",
                    (StreamStatus.ENABLED.value, stream_view_type.value, stream_arn)
                )
            else:
                # Create new stream
                stream_arn = self._generate_stream_arn(table_name)
                stream_label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                creation_time = int(datetime.now(timezone.utc).timestamp())
                
                await conn.execute(
                    """INSERT INTO __stream_metadata 
                       (stream_arn, stream_label, stream_status, stream_view_type, 
                        creation_date_time, table_name)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (stream_arn, stream_label, StreamStatus.ENABLED.value,
                     stream_view_type.value, creation_time, table_name)
                )
        
        await conn.commit()
        
        return await self.describe_stream(table_name)

    async def disable_stream(self, table_name: str) -> None:
        """Disable streams on a table.
        
        Args:
            table_name: Name of the table
        """
        conn = await self._get_connection(table_name)
        
        await conn.execute(
            """UPDATE __stream_metadata 
               SET stream_status = ?
               WHERE table_name = ?""",
            (StreamStatus.DISABLED.value, table_name)
        )
        
        await conn.commit()

    async def describe_stream(self, table_name: str) -> Optional[StreamMetadata]:
        """Get stream metadata for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            StreamMetadata if stream exists, None otherwise
        """
        db_path = self._get_db_path(table_name)
        if not db_path.exists():
            return None
        
        try:
            conn = await self._get_connection(table_name)
        except Exception:
            return None
        
        # Check if stream metadata table exists
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='__stream_metadata'"
        ) as cursor:
            if not await cursor.fetchone():
                return None
        
        async with conn.execute(
            """SELECT stream_arn, stream_label, stream_status, stream_view_type,
                      creation_date_time
               FROM __stream_metadata WHERE table_name = ?""",
            (table_name,)
        ) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            return StreamMetadata(
                stream_arn=row[0],
                stream_label=row[1],
                stream_status=StreamStatus(row[2]),
                stream_view_type=StreamViewType(row[3]),
                creation_date_time=row[4],
                table_name=table_name,
            )

    async def write_stream_record(
        self,
        table_name: str,
        event_name: EventName,
        keys: dict[str, Any],
        old_image: Optional[dict[str, Any]] = None,
        new_image: Optional[dict[str, Any]] = None,
    ) -> None:
        """Write a change record to the stream.
        
        Args:
            table_name: Name of the table
            event_name: Type of event (INSERT, MODIFY, REMOVE)
            keys: Primary key of the item
            old_image: Item before modification (if applicable)
            new_image: Item after modification (if applicable)
        """
        # Get stream metadata
        stream_meta = await self.describe_stream(table_name)
        if not stream_meta or stream_meta.stream_status != StreamStatus.ENABLED:
            return
        
        # Filter images based on stream view type
        old_to_store = None
        new_to_store = None
        
        if stream_meta.stream_view_type == StreamViewType.KEYS_ONLY:
            old_to_store = None
            new_to_store = None
        elif stream_meta.stream_view_type == StreamViewType.NEW_IMAGE:
            old_to_store = None
            new_to_store = new_image
        elif stream_meta.stream_view_type == StreamViewType.OLD_IMAGE:
            old_to_store = old_image
            new_to_store = None
        elif stream_meta.stream_view_type == StreamViewType.NEW_AND_OLD_IMAGES:
            old_to_store = old_image
            new_to_store = new_image
        
        # Calculate size
        size_bytes = len(json.dumps(keys))
        if old_to_store:
            size_bytes += len(json.dumps(old_to_store))
        if new_to_store:
            size_bytes += len(json.dumps(new_to_store))
        
        # Generate identifiers
        event_id = str(uuid.uuid4())
        sequence_number = self._generate_sequence_number()
        creation_time = int(datetime.now(timezone.utc).timestamp())
        expires_at = creation_time + (24 * 60 * 60)  # 24 hours TTL
        
        conn = await self._get_connection(table_name)
        
        await conn.execute(
            """INSERT INTO __stream_records
               (stream_arn, event_id, event_name, approximate_creation_date_time,
                keys_json, old_image_json, new_image_json, sequence_number,
                size_bytes, stream_view_type, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                stream_meta.stream_arn,
                event_id,
                event_name.value,
                creation_time,
                json.dumps(keys),
                json.dumps(old_to_store) if old_to_store else None,
                json.dumps(new_to_store) if new_to_store else None,
                sequence_number,
                size_bytes,
                stream_meta.stream_view_type.value,
                expires_at,
            )
        )
        
        await conn.commit()

    async def get_records(
        self,
        table_name: str,
        shard_iterator: str,
        limit: int = 100,
    ) -> tuple[list[StreamRecord], Optional[str]]:
        """Get records from a stream.
        
        Args:
            table_name: Name of the table
            shard_iterator: Sequence number to start from
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (records, next_shard_iterator)
        """
        conn = await self._get_connection(table_name)
        
        # Get records after the sequence number
        async with conn.execute(
            """SELECT event_id, event_name, event_version, event_source, aws_region,
                      approximate_creation_date_time, keys_json, old_image_json,
                      new_image_json, sequence_number, size_bytes, stream_view_type
               FROM __stream_records
               WHERE sequence_number > ?
               ORDER BY sequence_number
               LIMIT ?""",
            (shard_iterator, limit + 1)
        ) as cursor:
            rows = await cursor.fetchall()
        
        records = []
        next_iterator = None
        
        for i, row in enumerate(rows[:limit]):
            record = StreamRecord(
                event_id=row[0],
                event_name=EventName(row[1]),
                event_version=row[2],
                event_source=row[3],
                aws_region=row[4],
                approximate_creation_date_time=row[5],
                keys=json.loads(row[6]),
                old_image=json.loads(row[7]) if row[7] else None,
                new_image=json.loads(row[8]) if row[8] else None,
                sequence_number=row[9],
                size_bytes=row[10],
                stream_view_type=StreamViewType(row[11]),
            )
            records.append(record)
        
        # If there are more records, return next iterator
        if len(rows) > limit:
            next_iterator = rows[limit - 1][9]  # sequence_number of last record
        
        return records, next_iterator

    async def cleanup_expired_records(self, table_name: str) -> int:
        """Clean up expired stream records (older than 24 hours).
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of records deleted
        """
        conn = await self._get_connection(table_name)
        now = int(datetime.now(timezone.utc).timestamp())
        
        async with conn.execute(
            "DELETE FROM __stream_records WHERE expires_at < ?",
            (now,)
        ) as cursor:
            deleted = cursor.rowcount
        
        await conn.commit()
        return deleted
