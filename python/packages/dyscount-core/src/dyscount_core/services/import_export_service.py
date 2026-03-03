"""Import/Export service for DynamoDB operations."""

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from dyscount_core.models.operations import (
    ExportDescription,
    ExportFormat,
    ExportStatus,
    ExportTableToPointInTimeRequest,
    ExportTableToPointInTimeResponse,
    DescribeExportResponse,
    ListExportsResponse,
    ExportSummary,
    ImportTableDescription,
    ImportStatus,
    ImportTableRequest,
    ImportTableResponse,
    DescribeImportResponse,
    ListImportsResponse,
    ImportSummary,
    S3BucketSource,
    InputFormat,
)
from dyscount_core.models.errors import ResourceNotFoundException, ValidationException
from dyscount_core.storage.table_manager import TableManager
from dyscount_core.services.item_service import ItemService


class ImportExportService:
    """Service for handling DynamoDB Import/Export operations.
    
    Uses local filesystem as S3-compatible storage.
    Export/Import tasks run asynchronously in the background.
    """
    
    def __init__(self, data_directory: str, namespace: str = "default"):
        """Initialize the import/export service.
        
        Args:
            data_directory: Base directory for data storage
            namespace: Namespace for organizing exports/imports
        """
        self.data_directory = Path(data_directory)
        self.namespace = namespace
        self.exports_dir = self.data_directory / "exports"
        self.imports_dir = self.data_directory / "imports"
        
        # Ensure directories exist
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.imports_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory task storage (in production, this would be persistent)
        self._exports: Dict[str, ExportDescription] = {}
        self._imports: Dict[str, ImportTableDescription] = {}
        
        # Track background tasks
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    def _generate_export_arn(self, export_id: str) -> str:
        """Generate an export ARN."""
        return f"arn:aws:dynamodb:{self.namespace}:export/{export_id}"
    
    def _generate_import_arn(self, import_id: str) -> str:
        """Generate an import ARN."""
        return f"arn:aws:dynamodb:{self.namespace}:import/{import_id}"
    
    def _extract_table_name_from_arn(self, table_arn: str) -> str:
        """Extract table name from ARN."""
        # Handle both simple names and full ARNs
        if "/" in table_arn:
            return table_arn.split("/")[-1]
        return table_arn
    
    async def export_table_to_point_in_time(
        self,
        request: ExportTableToPointInTimeRequest,
        table_manager: TableManager,
        item_service: ItemService,
    ) -> ExportTableToPointInTimeResponse:
        """Start an export task for a table.
        
        Args:
            request: Export request parameters
            table_manager: Table manager for accessing table metadata
            item_service: Item service for reading table data
            
        Returns:
            ExportTableToPointInTimeResponse with export description
            
        Raises:
            ResourceNotFoundException: If table doesn't exist
            ValidationException: If parameters are invalid
        """
        # Extract table name from ARN
        table_name = self._extract_table_name_from_arn(request.table_arn)
        
        # Verify table exists
        try:
            table_metadata = await table_manager.describe_table(table_name)
        except Exception as e:
            raise ResourceNotFoundException(f"Table not found: {table_name}") from e
        
        # Generate unique export ID
        export_id = str(uuid.uuid4())
        export_arn = self._generate_export_arn(export_id)
        
        # Create export directory
        export_dir = self.exports_dir / export_id
        export_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = int(time.time())
        
        # Create export description
        export_desc = ExportDescription(
            export_arn=export_arn,
            export_status=ExportStatus.IN_PROGRESS,
            export_type=request.export_type,
            export_format=request.export_format,
            table_arn=request.table_arn,
            table_id=table_metadata.table_id if hasattr(table_metadata, 'table_id') else None,
            s3_bucket=request.s3_bucket,
            s3_prefix=request.s3_prefix or export_id,
            s3_bucket_owner=request.s3_bucket_owner,
            s3_sse_algorithm=request.s3_sse_algorithm,
            s3_sse_kms_key_id=request.s3_sse_kms_key_id,
            export_time=request.export_time or start_time,
            start_time=start_time,
        )
        
        # Store export
        self._exports[export_arn] = export_desc
        
        # Start background export task
        task = asyncio.create_task(
            self._perform_export(
                export_id=export_id,
                export_arn=export_arn,
                table_name=table_name,
                export_dir=export_dir,
                item_service=item_service,
            )
        )
        self._running_tasks[export_arn] = task
        
        return ExportTableToPointInTimeResponse(export_description=export_desc)
    
    async def _perform_export(
        self,
        export_id: str,
        export_arn: str,
        table_name: str,
        export_dir: Path,
        item_service: ItemService,
    ) -> None:
        """Perform the actual export operation in the background.
        
        Args:
            export_id: Unique export ID
            export_arn: Export ARN
            table_name: Name of the table to export
            export_dir: Directory for export files
            item_service: Item service for reading data
        """
        try:
            # Scan all items from the table
            items: List[Dict[str, Any]] = []
            
            try:
                # Use Scan to get all items
                from dyscount_core.models.operations import ScanRequest
                scan_request = ScanRequest(table_name=table_name)
                scan_response = await item_service.scan(scan_request)
                items = scan_response.items
                
                # Handle pagination
                while scan_response.last_evaluated_key:
                    scan_request.exclusive_start_key = scan_response.last_evaluated_key
                    scan_response = await item_service.scan(scan_request)
                    items.extend(scan_response.items)
                    
            except Exception as e:
                # Update export status to failed
                export_desc = self._exports.get(export_arn)
                if export_desc:
                    export_desc.export_status = ExportStatus.FAILED
                    export_desc.end_time = int(time.time())
                    export_desc.failure_code = "ExportError"
                    export_desc.failure_message = str(e)
                return
            
            # Write data.json
            data_file = export_dir / "data.json"
            export_data = {
                "Items": items,
                "ExportMetadata": {
                    "ExportArn": export_arn,
                    "TableName": table_name,
                    "ExportTime": int(time.time()),
                    "ItemCount": len(items),
                    "Format": "DYNAMODB_JSON"
                }
            }
            
            with open(data_file, "w") as f:
                json.dump(export_data, f, indent=2)
            
            # Write manifest.json
            manifest_file = export_dir / "manifest.json"
            manifest = {
                "ExportArn": export_arn,
                "ExportStatus": "COMPLETED",
                "ItemCount": len(items),
                "DataFile": "data.json",
                "Format": "DYNAMODB_JSON"
            }
            
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Update export status
            export_desc = self._exports.get(export_arn)
            if export_desc:
                export_desc.export_status = ExportStatus.COMPLETED
                export_desc.end_time = int(time.time())
                export_desc.item_count = len(items)
                export_desc.processed_size_bytes = os.path.getsize(data_file)
                export_desc.billed_size_bytes = export_desc.processed_size_bytes
                export_desc.export_manifest = str(manifest_file.relative_to(self.data_directory))
                
        except Exception as e:
            # Update export status to failed
            export_desc = self._exports.get(export_arn)
            if export_desc:
                export_desc.export_status = ExportStatus.FAILED
                export_desc.end_time = int(time.time())
                export_desc.failure_code = "ExportError"
                export_desc.failure_message = str(e)
        finally:
            # Remove from running tasks
            self._running_tasks.pop(export_arn, None)
    
    async def describe_export(self, export_arn: str) -> DescribeExportResponse:
        """Describe an export task.
        
        Args:
            export_arn: ARN of the export to describe
            
        Returns:
            DescribeExportResponse with export description
            
        Raises:
            ResourceNotFoundException: If export doesn't exist
        """
        export_desc = self._exports.get(export_arn)
        if not export_desc:
            raise ResourceNotFoundException(f"Export not found: {export_arn}")
        
        return DescribeExportResponse(export_description=export_desc)
    
    async def list_exports(
        self,
        table_arn: Optional[str] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> ListExportsResponse:
        """List export tasks.
        
        Args:
            table_arn: Filter by table ARN
            max_results: Maximum number of results
            next_token: Pagination token
            
        Returns:
            ListExportsResponse with list of export summaries
        """
        # Filter exports
        filtered_exports = list(self._exports.values())
        
        if table_arn:
            filtered_exports = [
                e for e in filtered_exports if e.table_arn == table_arn
            ]
        
        # Sort by start time (newest first)
        filtered_exports.sort(key=lambda e: e.start_time, reverse=True)
        
        # Handle pagination
        start_idx = 0
        if next_token:
            try:
                start_idx = int(next_token)
            except ValueError:
                pass
        
        end_idx = len(filtered_exports)
        if max_results:
            end_idx = min(start_idx + max_results, len(filtered_exports))
        
        paginated_exports = filtered_exports[start_idx:end_idx]
        
        # Create summaries
        summaries = [
            ExportSummary(
                export_arn=e.export_arn,
                export_status=e.export_status,
                export_type=e.export_type,
            )
            for e in paginated_exports
        ]
        
        # Determine next token
        new_next_token = None
        if max_results and end_idx < len(filtered_exports):
            new_next_token = str(end_idx)
        
        return ListExportsResponse(
            export_summaries=summaries,
            next_token=new_next_token,
        )
    
    async def import_table(
        self,
        request: ImportTableRequest,
        table_manager: TableManager,
        item_service: ItemService,
    ) -> ImportTableResponse:
        """Start an import task to create a table from S3 data.
        
        Args:
            request: Import request parameters
            table_manager: Table manager for creating the table
            item_service: Item service for writing data
            
        Returns:
            ImportTableResponse with import description
            
        Raises:
            ValidationException: If parameters are invalid
        """
        # Validate input format
        if request.input_format != InputFormat.DYNAMODB_JSON:
            raise ValidationException(
                f"Input format {request.input_format} not yet supported. Use DYNAMODB_JSON."
            )
        
        # Generate unique import ID
        import_id = str(uuid.uuid4())
        import_arn = self._generate_import_arn(import_id)
        
        # Get table creation parameters
        table_params = request.table_creation_parameters
        
        # Create import directory
        import_dir = self.imports_dir / import_id
        import_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = int(time.time())
        
        # Create import description
        import_desc = ImportTableDescription(
            import_arn=import_arn,
            import_status=ImportStatus.IN_PROGRESS,
            table_name=table_params.table_name,
            s3_bucket_source=request.s3_bucket_source,
            input_format=request.input_format,
            input_compression_type=request.input_compression_type,
            start_time=start_time,
        )
        
        # Store import
        self._imports[import_arn] = import_desc
        
        # Start background import task
        task = asyncio.create_task(
            self._perform_import(
                import_id=import_id,
                import_arn=import_arn,
                table_params=table_params,
                s3_source=request.s3_bucket_source,
                import_dir=import_dir,
                table_manager=table_manager,
                item_service=item_service,
            )
        )
        self._running_tasks[import_arn] = task
        
        return ImportTableResponse(import_table_description=import_desc)
    
    async def _perform_import(
        self,
        import_id: str,
        import_arn: str,
        table_params: Any,
        s3_source: S3BucketSource,
        import_dir: Path,
        table_manager: TableManager,
        item_service: ItemService,
    ) -> None:
        """Perform the actual import operation in the background.
        
        Args:
            import_id: Unique import ID
            import_arn: Import ARN
            table_params: Table creation parameters
            s3_source: S3 source information
            import_dir: Directory for import files
            table_manager: Table manager for creating table
            item_service: Item service for writing data
        """
        try:
            # Resolve S3 source path (local filesystem)
            # In real implementation, this would be an S3 bucket
            # For local dev, we map S3 bucket to local path
            # Exports are stored in {data_directory}/exports/{export_id}/
            source_path = self.exports_dir
            if s3_source.s3_key_prefix:
                source_path = source_path / s3_source.s3_key_prefix
            elif s3_source.s3_bucket:
                # Try to find by bucket name as export_id
                source_path = self.exports_dir / s3_source.s3_bucket
            
            # Look for data.json
            data_file = source_path / "data.json"
            if not data_file.exists():
                # Try manifest.json to find data file
                manifest_file = source_path / "manifest.json"
                if manifest_file.exists():
                    with open(manifest_file, "r") as f:
                        manifest = json.load(f)
                    data_file_name = manifest.get("DataFile", "data.json")
                    data_file = source_path / data_file_name
                else:
                    raise FileNotFoundError(f"No data file found at {source_path}")
            
            # Load data
            with open(data_file, "r") as f:
                export_data = json.load(f)
            
            items = export_data.get("Items", [])
            
            # Create the table first
            from dyscount_core.models.operations import (
                CreateTableRequest,
                ProvisionedThroughput,
            )
            
            create_request = CreateTableRequest(
                TableName=table_params.table_name,
                AttributeDefinitions=table_params.attribute_definitions,
                KeySchema=table_params.key_schema,
                BillingMode=table_params.billing_mode,
                ProvisionedThroughput=table_params.provisioned_throughput or ProvisionedThroughput(
                    ReadCapacityUnits=5, WriteCapacityUnits=5
                ),
                GlobalSecondaryIndexes=table_params.global_secondary_indexes,
            )
            
            try:
                await table_manager.create_table(
                    table_name=table_params.table_name,
                    key_schema=table_params.key_schema,
                    attribute_definitions=table_params.attribute_definitions,
                    billing_mode=table_params.billing_mode,
                    provisioned_throughput=table_params.provisioned_throughput,
                    global_secondary_indexes=table_params.global_secondary_indexes,
                )
            except Exception as e:
                if "already exists" not in str(e).lower():
                    raise
            
            # Import items
            imported_count = 0
            error_count = 0
            
            for item in items:
                try:
                    from dyscount_core.models.operations import PutItemRequest
                    put_request = PutItemRequest(
                        table_name=table_params.table_name,
                        item=item,
                    )
                    await item_service.put_item(put_request)
                    imported_count += 1
                except Exception:
                    error_count += 1
            
            # Write manifest
            manifest_file = import_dir / "manifest.json"
            manifest = {
                "ImportArn": import_arn,
                "ImportStatus": "COMPLETED",
                "TableName": table_params.table_name,
                "ImportedItemCount": imported_count,
                "ErrorCount": error_count,
            }
            
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Get table info
            table_info = await table_manager.describe_table(table_params.table_name)
            
            # Update import status
            import_desc = self._imports.get(import_arn)
            if import_desc:
                import_desc.import_status = ImportStatus.COMPLETED
                import_desc.end_time = int(time.time())
                import_desc.table_arn = table_info.table_arn if hasattr(table_info, 'table_arn') else None
                import_desc.table_id = table_info.table_id if hasattr(table_info, 'table_id') else None
                import_desc.imported_item_count = imported_count
                import_desc.processed_item_count = imported_count + error_count
                import_desc.error_count = error_count
                import_desc.processed_size_bytes = os.path.getsize(data_file)
                
        except Exception as e:
            # Update import status to failed
            import_desc = self._imports.get(import_arn)
            if import_desc:
                import_desc.import_status = ImportStatus.FAILED
                import_desc.end_time = int(time.time())
                import_desc.failure_code = "ImportError"
                import_desc.failure_message = str(e)
        finally:
            # Remove from running tasks
            self._running_tasks.pop(import_arn, None)
    
    async def describe_import(self, import_arn: str) -> DescribeImportResponse:
        """Describe an import task.
        
        Args:
            import_arn: ARN of the import to describe
            
        Returns:
            DescribeImportResponse with import description
            
        Raises:
            ResourceNotFoundException: If import doesn't exist
        """
        import_desc = self._imports.get(import_arn)
        if not import_desc:
            raise ResourceNotFoundException(f"Import not found: {import_arn}")
        
        return DescribeImportResponse(import_table_description=import_desc)
    
    async def list_imports(
        self,
        table_arn: Optional[str] = None,
        page_size: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> ListImportsResponse:
        """List import tasks.
        
        Args:
            table_arn: Filter by table ARN
            page_size: Number of results per page
            next_token: Pagination token
            
        Returns:
            ListImportsResponse with list of import summaries
        """
        # Filter imports
        filtered_imports = list(self._imports.values())
        
        if table_arn:
            filtered_imports = [
                i for i in filtered_imports if i.table_arn == table_arn
            ]
        
        # Sort by start time (newest first)
        filtered_imports.sort(key=lambda i: i.start_time, reverse=True)
        
        # Handle pagination
        start_idx = 0
        if next_token:
            try:
                start_idx = int(next_token)
            except ValueError:
                pass
        
        end_idx = len(filtered_imports)
        if page_size:
            end_idx = min(start_idx + page_size, len(filtered_imports))
        
        paginated_imports = filtered_imports[start_idx:end_idx]
        
        # Create summaries
        summaries = [
            ImportSummary(
                import_arn=i.import_arn,
                import_status=i.import_status,
                table_arn=i.table_arn,
                s3_bucket_source=i.s3_bucket_source,
            )
            for i in paginated_imports
        ]
        
        # Determine next token
        new_next_token = None
        if page_size and end_idx < len(filtered_imports):
            new_next_token = str(end_idx)
        
        return ListImportsResponse(
            import_summary_list=summaries,
            next_token=new_next_token,
        )
