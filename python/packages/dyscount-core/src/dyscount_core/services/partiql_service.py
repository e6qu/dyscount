"""PartiQL service for executing SQL-compatible queries."""

from typing import Any, Dict, List, Optional

from dyscount_core.config import Config
from dyscount_core.models.operations import (
    ExecuteStatementRequest,
    ExecuteStatementResponse,
    BatchExecuteStatementRequest,
    BatchExecuteStatementResponse,
    BatchStatementRequest,
    BatchStatementResponse,
    PutItemRequest,
    UpdateItemRequest,
    DeleteItemRequest,
)
from dyscount_core.models.errors import ResourceNotFoundException, ValidationException
from dyscount_core.partiql import parse_partiql, PartiQLOperation
from dyscount_core.storage.table_manager import TableManager
from dyscount_core.services.item_service import ItemService


class PartiQLService:
    """Service for executing PartiQL statements.
    
    PartiQL is a SQL-compatible query language for DynamoDB.
    This service parses PartiQL statements and executes them using
    the existing DynamoDB operations.
    """
    
    def __init__(self, config: Config):
        """Initialize the PartiQL service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.table_manager = TableManager(config.storage.data_directory)
        self.item_service = ItemService(config)
    
    async def execute_statement(
        self,
        request: ExecuteStatementRequest,
    ) -> ExecuteStatementResponse:
        """Execute a single PartiQL statement.
        
        Args:
            request: ExecuteStatementRequest with the PartiQL statement
            
        Returns:
            ExecuteStatementResponse with results
            
        Raises:
            ValidationException: If the statement is invalid
            ResourceNotFoundException: If the table doesn't exist
        """
        # Parse the PartiQL statement
        parse_result = parse_partiql(
            request.statement,
            request.parameters,
        )
        
        if parse_result.operation == PartiQLOperation.UNKNOWN:
            raise ValidationException(f"Unsupported or invalid PartiQL statement: {request.statement}")
        
        # Check if table exists
        if not await self.table_manager.table_exists(parse_result.table_name):
            raise ResourceNotFoundException(f"Table not found: {parse_result.table_name}")
        
        # Execute based on operation type
        if parse_result.operation == PartiQLOperation.SELECT:
            return await self._execute_select(parse_result, request)
        elif parse_result.operation == PartiQLOperation.INSERT:
            return await self._execute_insert(parse_result, request)
        elif parse_result.operation == PartiQLOperation.UPDATE:
            return await self._execute_update(parse_result, request)
        elif parse_result.operation == PartiQLOperation.DELETE:
            return await self._execute_delete(parse_result, request)
        else:
            raise ValidationException(f"Unsupported operation: {parse_result.operation}")
    
    async def _execute_select(
        self,
        parse_result: Any,
        request: ExecuteStatementRequest,
    ) -> ExecuteStatementResponse:
        """Execute a SELECT statement.
        
        Args:
            parse_result: Parsed PartiQL result
            request: Original request
            
        Returns:
            ExecuteStatementResponse with items
        """
        from dyscount_core.models.operations import ScanRequest
        
        # Build scan request
        scan_request = ScanRequest(
            table_name=parse_result.table_name,
            limit=parse_result.limit or request.limit,
            consistent_read=request.consistent_read,
        )
        
        # Execute scan
        scan_response = await self.item_service.scan(scan_request)
        
        # Convert items to response format
        items = []
        for item in scan_response.items or []:
            items.append(item)
        
        return ExecuteStatementResponse(
            items=items,
            last_evaluated_key=scan_response.last_evaluated_key,
        )
    
    async def _execute_insert(
        self,
        parse_result: Any,
        request: ExecuteStatementRequest,
    ) -> ExecuteStatementResponse:
        """Execute an INSERT statement.
        
        Args:
            parse_result: Parsed PartiQL result
            request: Original request
            
        Returns:
            ExecuteStatementResponse
        """
        if not parse_result.values:
            raise ValidationException("INSERT statement must have values")
        
        item = parse_result.values[0]
        
        # Convert Python values to DynamoDB format
        dynamo_item = self._convert_to_dynamo_format(item)
        
        # Build put item request
        put_request = PutItemRequest(
            TableName=parse_result.table_name,
            Item=dynamo_item,
        )
        
        # Execute put
        await self.item_service.put_item(put_request)
        
        return ExecuteStatementResponse()
    
    async def _execute_update(
        self,
        parse_result: Any,
        request: ExecuteStatementRequest,
    ) -> ExecuteStatementResponse:
        """Execute an UPDATE statement.
        
        Args:
            parse_result: Parsed PartiQL result
            request: Original request
            
        Returns:
            ExecuteStatementResponse
        """
        if not parse_result.where_conditions:
            raise ValidationException("UPDATE statement must have a WHERE clause")
        
        if not parse_result.set_clause:
            raise ValidationException("UPDATE statement must have a SET clause")
        
        # Get table metadata to find key attributes
        table_metadata = await self.table_manager.describe_table(parse_result.table_name)
        key_schema = table_metadata.KeySchema
        
        # Build key from WHERE conditions
        key = {}
        for col, op, value in parse_result.where_conditions:
            # Check if this is a key attribute
            for key_element in key_schema:
                if key_element.AttributeName == col:
                    key[col] = self._convert_single_value_to_dynamo(value)
                    break
        
        if not key:
            raise ValidationException("WHERE clause must specify the primary key")
        
        # Build update expression
        update_expression = "SET "
        expression_values = {}
        
        for i, (col, value) in enumerate(parse_result.set_clause.items()):
            if i > 0:
                update_expression += ", "
            update_expression += f"#{col} = :val{i}"
            expression_values[f":val{i}"] = self._convert_single_value_to_dynamo(value)
        
        # Build update item request
        update_request = UpdateItemRequest(
            TableName=parse_result.table_name,
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames={f"#{col}": col for col in parse_result.set_clause.keys()},
        )
        
        # Execute update
        await self.item_service.update_item(update_request)
        
        return ExecuteStatementResponse()
    
    async def _execute_delete(
        self,
        parse_result: Any,
        request: ExecuteStatementRequest,
    ) -> ExecuteStatementResponse:
        """Execute a DELETE statement.
        
        Args:
            parse_result: Parsed PartiQL result
            request: Original request
            
        Returns:
            ExecuteStatementResponse
        """
        if not parse_result.where_conditions:
            raise ValidationException("DELETE statement must have a WHERE clause")
        
        # Get table metadata to find key attributes
        table_metadata = await self.table_manager.describe_table(parse_result.table_name)
        key_schema = table_metadata.KeySchema
        
        # Build key from WHERE conditions
        key = {}
        for col, op, value in parse_result.where_conditions:
            # Check if this is a key attribute
            for key_element in key_schema:
                if key_element.AttributeName == col:
                    key[col] = self._convert_single_value_to_dynamo(value)
                    break
        
        if not key:
            raise ValidationException("WHERE clause must specify the primary key")
        
        # Build delete item request
        delete_request = DeleteItemRequest(
            TableName=parse_result.table_name,
            Key=key,
        )
        
        # Execute delete
        await self.item_service.delete_item(delete_request)
        
        return ExecuteStatementResponse()
    
    async def batch_execute_statement(
        self,
        request: BatchExecuteStatementRequest,
    ) -> BatchExecuteStatementResponse:
        """Execute multiple PartiQL statements in a batch.
        
        Args:
            request: BatchExecuteStatementRequest with list of statements
            
        Returns:
            BatchExecuteStatementResponse with results for each statement
        """
        responses = []
        
        for statement_request in request.statements:
            try:
                # Convert BatchStatementRequest to ExecuteStatementRequest
                execute_request = ExecuteStatementRequest(
                    Statement=statement_request.statement,
                    Parameters=statement_request.parameters,
                    ConsistentRead=statement_request.consistent_read,
                )
                
                # Execute the statement
                result = await self.execute_statement(execute_request)
                
                # Build response
                response = BatchStatementResponse(
                    item=result.items[0] if result.items else None,
                )
                responses.append(response)
                
            except Exception as e:
                # Add error response
                response = BatchStatementResponse(
                    error={
                        "Code": "ValidationException",
                        "Message": str(e),
                    },
                )
                responses.append(response)
        
        return BatchExecuteStatementResponse(
            responses=responses,
        )
    
    def _convert_to_dynamo_format(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python dict to DynamoDB format.
        
        Args:
            item: Python dict with values
            
        Returns:
            DynamoDB formatted dict
        """
        result = {}
        for key, value in item.items():
            result[key] = self._convert_single_value_to_dynamo(value)
        return result
    
    def _convert_single_value_to_dynamo(self, value: Any) -> Dict[str, Any]:
        """Convert a single Python value to DynamoDB format.
        
        Args:
            value: Python value
            
        Returns:
            DynamoDB formatted value
        """
        if value is None:
            return {"NULL": True}
        elif isinstance(value, bool):
            return {"BOOL": value}
        elif isinstance(value, int) or isinstance(value, float):
            return {"N": str(value)}
        elif isinstance(value, str):
            return {"S": value}
        elif isinstance(value, list):
            return {"L": [self._convert_single_value_to_dynamo(v) for v in value]}
        elif isinstance(value, dict):
            return {"M": {k: self._convert_single_value_to_dynamo(v) for k, v in value.items()}}
        else:
            return {"S": str(value)}
    
    async def close(self):
        """Close any open resources."""
        await self.table_manager.close()
        await self.item_service.close()
