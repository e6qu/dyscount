"""SQLite connection management with pooling."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Dict, Optional

import aiosqlite


class SQLiteConnectionManager:
    """Manages SQLite connections with connection pooling.
    
    This class provides:
    - Async context manager for connections
    - Connection pooling (one connection per database file)
    - Proper cleanup of connections
    
    Example:
        manager = SQLiteConnectionManager()
        
        # Direct connection usage
        conn = await manager.get_connection("/path/to/db.sqlite")
        await conn.execute("CREATE TABLE ...")
        await manager.close_connection("/path/to/db.sqlite")
        
        # Context manager usage
        async with manager.connection("/path/to/db.sqlite") as conn:
            await conn.execute("CREATE TABLE ...")
        
        # Cleanup all connections
        await manager.close_all()
    """

    def __init__(self, busy_timeout_ms: int = 5000):
        """Initialize the connection manager.
        
        Args:
            busy_timeout_ms: SQLite busy timeout in milliseconds
        """
        self._connections: Dict[str, aiosqlite.Connection] = {}
        self._busy_timeout_ms = busy_timeout_ms
        self._lock = asyncio.Lock()

    async def get_connection(
        self, 
        db_path: str | Path,
        *,
        isolation_level: Optional[str] = None,
    ) -> aiosqlite.Connection:
        """Get or create a connection to the specified database.
        
        Args:
            db_path: Path to the SQLite database file
            isolation_level: Transaction isolation level (None for autocommit)
            
        Returns:
            An aiosqlite connection object
        """
        db_path_str = str(db_path)
        
        async with self._lock:
            if db_path_str not in self._connections:
                # Create parent directory if it doesn't exist
                path = Path(db_path_str)
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Create new connection
                conn = await aiosqlite.connect(
                    db_path_str,
                    isolation_level=isolation_level,
                )
                
                # Configure connection
                await conn.execute(f"PRAGMA busy_timeout = {self._busy_timeout_ms}")
                await conn.execute("PRAGMA foreign_keys = ON")
                
                self._connections[db_path_str] = conn
            
            return self._connections[db_path_str]

    async def close_connection(self, db_path: str | Path) -> None:
        """Close a specific connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        db_path_str = str(db_path)
        
        async with self._lock:
            if db_path_str in self._connections:
                conn = self._connections.pop(db_path_str)
                await conn.close()

    async def close_all(self) -> None:
        """Close all managed connections."""
        async with self._lock:
            for conn in self._connections.values():
                await conn.close()
            self._connections.clear()

    @asynccontextmanager
    async def connection(
        self,
        db_path: str | Path,
        *,
        isolation_level: Optional[str] = None,
    ) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Async context manager for database connections.
        
        This context manager yields a connection and optionally closes it
        after use (controlled by the close parameter).
        
        Args:
            db_path: Path to the SQLite database file
            isolation_level: Transaction isolation level
            
        Yields:
            An aiosqlite connection object
            
        Example:
            async with manager.connection("/path/to/db.sqlite") as conn:
                cursor = await conn.execute("SELECT * FROM table")
                rows = await cursor.fetchall()
        """
        conn = await self.get_connection(db_path, isolation_level=isolation_level)
        try:
            yield conn
        finally:
            # We don't close here, connections are pooled
            pass

    @asynccontextmanager
    async def transaction(
        self,
        db_path: str | Path,
    ) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Async context manager for database transactions.
        
        Automatically commits on successful exit or rolls back on exception.
        
        Args:
            db_path: Path to the SQLite database file
            
        Yields:
            An aiosqlite connection object within a transaction
            
        Example:
            async with manager.transaction("/path/to/db.sqlite") as conn:
                await conn.execute("INSERT INTO table VALUES (?)", (value,))
                # Automatically commits here
        """
        conn = await self.get_connection(db_path, isolation_level=None)
        await conn.execute("BEGIN")
        try:
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    def is_connected(self, db_path: str | Path) -> bool:
        """Check if a connection exists for the given database path.
        
        Args:
            db_path: Path to the SQLite database file
            
        Returns:
            True if a connection exists, False otherwise
        """
        return str(db_path) in self._connections

    async def execute_pragma(
        self,
        db_path: str | Path,
        pragma: str,
        value: Optional[Any] = None,
    ) -> Any:
        """Execute a PRAGMA statement.
        
        Args:
            db_path: Path to the SQLite database file
            pragma: PRAGMA name
            value: Optional value to set
            
        Returns:
            PRAGMA query result
        """
        conn = await self.get_connection(db_path)
        if value is not None:
            cursor = await conn.execute(f"PRAGMA {pragma} = {value}")
        else:
            cursor = await conn.execute(f"PRAGMA {pragma}")
        return await cursor.fetchone()


# Global connection manager instance
_default_manager: Optional[SQLiteConnectionManager] = None


def get_default_manager() -> SQLiteConnectionManager:
    """Get the default global connection manager.
    
    Returns:
        The default SQLiteConnectionManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = SQLiteConnectionManager()
    return _default_manager


def set_default_manager(manager: SQLiteConnectionManager) -> None:
    """Set the default global connection manager.
    
    Args:
        manager: The SQLiteConnectionManager instance to use as default
    """
    global _default_manager
    _default_manager = manager
