"""Time-to-Live (TTL) background cleanup process.

This module provides a background task that periodically scans tables
and deletes expired items based on their TTL attributes.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .storage.table_manager import TableManager


logger = logging.getLogger(__name__)


class TTLCleanupTask:
    """Background task for cleaning up expired TTL items.
    
    This task runs periodically and scans all tables with TTL enabled,
    deleting items that have expired (where the TTL timestamp is in the past).
    
    Attributes:
        data_directory: Root directory for SQLite database files
        namespace: Logical namespace for table isolation
        check_interval: Seconds between cleanup runs (default: 300 = 5 minutes)
        batch_size: Maximum items to delete per table per run (default: 100)
        running: Whether the cleanup task is currently running
    """
    
    def __init__(
        self,
        data_directory: Path,
        namespace: str = "default",
        check_interval: int = 300,
        batch_size: int = 100,
    ):
        """Initialize the TTL cleanup task.
        
        Args:
            data_directory: Root directory for SQLite database files
            namespace: Logical namespace for table isolation
            check_interval: Seconds between cleanup runs
            batch_size: Maximum items to delete per table per run
        """
        self.data_directory = Path(data_directory)
        self.namespace = namespace
        self.check_interval = check_interval
        self.batch_size = batch_size
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the background cleanup task."""
        if self.running:
            logger.warning("TTL cleanup task is already running")
            return
        
        self.running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"Started TTL cleanup task (interval={self.check_interval}s, "
            f"batch_size={self.batch_size})"
        )
    
    async def stop(self) -> None:
        """Stop the background cleanup task."""
        if not self.running:
            return
        
        self.running = False
        self._stop_event.set()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped TTL cleanup task")
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup loop that runs periodically."""
        while self.running:
            try:
                await self._run_cleanup()
            except Exception as e:
                logger.error(f"Error during TTL cleanup: {e}", exc_info=True)
            
            # Wait for the next interval or until stopped
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.check_interval,
                )
            except asyncio.TimeoutError:
                # Normal timeout, continue to next iteration
                pass
    
    async def _run_cleanup(self) -> None:
        """Run a single cleanup pass on all tables."""
        # Create table manager
        table_manager = TableManager(self.data_directory, self.namespace)
        
        try:
            # List all tables
            tables = await table_manager.list_tables()
            
            if not tables:
                return
            
            logger.debug(f"Running TTL cleanup on {len(tables)} tables")
            
            current_time = int(datetime.utcnow().timestamp())
            total_deleted = 0
            
            for table_name in tables:
                try:
                    deleted = await self._cleanup_table(
                        table_manager,
                        table_name,
                        current_time,
                    )
                    total_deleted += deleted
                except Exception as e:
                    logger.error(
                        f"Error cleaning up table {table_name}: {e}",
                        exc_info=True,
                    )
            
            if total_deleted > 0:
                logger.info(f"TTL cleanup complete: deleted {total_deleted} expired items")
        
        finally:
            await table_manager.close()
    
    async def _cleanup_table(
        self,
        table_manager: TableManager,
        table_name: str,
        current_time: int,
    ) -> int:
        """Clean up expired items in a single table.
        
        Args:
            table_manager: TableManager instance
            table_name: Name of the table to clean up
            current_time: Current Unix timestamp
            
        Returns:
            Number of items deleted
        """
        # Get TTL configuration
        ttl_config = await table_manager.describe_time_to_live(table_name)
        
        # Skip if TTL is not enabled
        if ttl_config.get("TimeToLiveStatus") != "ENABLED":
            return 0
        
        ttl_attribute = ttl_config.get("AttributeName")
        if not ttl_attribute:
            return 0
        
        # Get expired items
        expired_items = await table_manager.get_expired_items(
            table_name,
            ttl_attribute,
            current_time,
            limit=self.batch_size,
        )
        
        if not expired_items:
            return 0
        
        # Delete expired items
        deleted_count = await table_manager.delete_expired_items(
            table_name,
            expired_items,
        )
        
        logger.debug(
            f"Deleted {deleted_count} expired items from table {table_name}"
        )
        
        return deleted_count
    
    async def run_once(self) -> int:
        """Run cleanup once (for manual triggering).
        
        Returns:
            Total number of items deleted
        """
        table_manager = TableManager(self.data_directory, self.namespace)
        total_deleted = 0
        
        try:
            tables = await table_manager.list_tables()
            current_time = int(datetime.utcnow().timestamp())
            
            for table_name in tables:
                deleted = await self._cleanup_table(
                    table_manager,
                    table_name,
                    current_time,
                )
                total_deleted += deleted
        
        finally:
            await table_manager.close()
        
        return total_deleted
