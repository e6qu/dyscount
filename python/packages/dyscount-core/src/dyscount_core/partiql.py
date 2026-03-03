"""PartiQL parser and executor for DynamoDB-compatible queries.

PartiQL is a SQL-compatible query language for DynamoDB that supports:
- SELECT with WHERE, ORDER BY, LIMIT
- INSERT INTO with VALUES
- UPDATE SET with WHERE
- DELETE FROM with WHERE
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum, auto


class PartiQLOperation(Enum):
    """Types of PartiQL operations."""
    SELECT = auto()
    INSERT = auto()
    UPDATE = auto()
    DELETE = auto()
    UNKNOWN = auto()


@dataclass
class PartiQLParseResult:
    """Result of parsing a PartiQL statement."""
    operation: PartiQLOperation
    table_name: str
    columns: Optional[List[str]] = None
    values: Optional[List[Dict[str, Any]]] = None
    set_clause: Optional[Dict[str, Any]] = None
    where_conditions: Optional[List[Tuple[str, str, Any]]] = None
    limit: Optional[int] = None
    parameters: Optional[List[Any]] = None


class PartiQLParser:
    """Parser for PartiQL statements.
    
    This is a simplified parser that handles basic PartiQL syntax.
    It converts PartiQL statements into structured data that can be
    mapped to DynamoDB operations.
    """
    
    def __init__(self):
        """Initialize the PartiQL parser."""
        pass
    
    def parse(self, statement: str, parameters: Optional[List[Any]] = None) -> PartiQLParseResult:
        """Parse a PartiQL statement.
        
        Args:
            statement: The PartiQL statement to parse
            parameters: Optional parameters for the statement
            
        Returns:
            PartiQLParseResult containing the parsed operation details
        """
        statement = statement.strip()
        upper_statement = statement.upper()
        
        # Determine operation type
        if upper_statement.startswith("SELECT"):
            return self._parse_select(statement, parameters)
        elif upper_statement.startswith("INSERT"):
            return self._parse_insert(statement, parameters)
        elif upper_statement.startswith("UPDATE"):
            return self._parse_update(statement, parameters)
        elif upper_statement.startswith("DELETE"):
            return self._parse_delete(statement, parameters)
        else:
            return PartiQLParseResult(
                operation=PartiQLOperation.UNKNOWN,
                table_name="",
            )
    
    def _parse_select(
        self,
        statement: str,
        parameters: Optional[List[Any]] = None,
    ) -> PartiQLParseResult:
        """Parse a SELECT statement.
        
        Supports: SELECT * FROM table [WHERE condition] [LIMIT n]
        
        Args:
            statement: The SELECT statement
            parameters: Optional parameters
            
        Returns:
            PartiQLParseResult for SELECT
        """
        # Extract table name
        from_match = re.search(r'FROM\s+(\w+)', statement, re.IGNORECASE)
        table_name = from_match.group(1) if from_match else ""
        
        # Extract columns
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', statement, re.IGNORECASE)
        columns_str = select_match.group(1).strip() if select_match else "*"
        columns = [c.strip() for c in columns_str.split(",")] if columns_str != "*" else None
        
        # Extract WHERE conditions
        where_conditions = self._parse_where(statement, parameters)
        
        # Extract LIMIT
        limit = self._parse_limit(statement)
        
        return PartiQLParseResult(
            operation=PartiQLOperation.SELECT,
            table_name=table_name,
            columns=columns,
            where_conditions=where_conditions,
            limit=limit,
            parameters=parameters,
        )
    
    def _parse_insert(
        self,
        statement: str,
        parameters: Optional[List[Any]] = None,
    ) -> PartiQLParseResult:
        """Parse an INSERT statement.
        
        Supports: INSERT INTO table VALUE { ... }
                  INSERT INTO table (col1, col2) VALUES (val1, val2)
        
        Args:
            statement: The INSERT statement
            parameters: Optional parameters
            
        Returns:
            PartiQLParseResult for INSERT
        """
        # Extract table name
        into_match = re.search(r'INSERT\s+INTO\s+(\w+)', statement, re.IGNORECASE)
        table_name = into_match.group(1) if into_match else ""
        
        # Check for VALUE syntax: INSERT INTO table VALUE { ... }
        value_match = re.search(r'VALUE\s*\{([^}]*)\}', statement, re.IGNORECASE)
        if value_match:
            item_str = "{" + value_match.group(1) + "}"
            item = self._parse_json_item(item_str, parameters)
            return PartiQLParseResult(
                operation=PartiQLOperation.INSERT,
                table_name=table_name,
                values=[item],
                parameters=parameters,
            )
        
        # Check for VALUES syntax: INSERT INTO table (col1, col2) VALUES (val1, val2)
        columns_match = re.search(r'\(([^)]+)\)\s+VALUES\s*\(([^)]+)\)', statement, re.IGNORECASE)
        if columns_match:
            columns = [c.strip() for c in columns_match.group(1).split(",")]
            values_str = columns_match.group(2)
            values = self._parse_values(values_str, parameters)
            
            # Create item dict
            item = {}
            for i, col in enumerate(columns):
                if i < len(values):
                    item[col] = values[i]
            
            return PartiQLParseResult(
                operation=PartiQLOperation.INSERT,
                table_name=table_name,
                columns=columns,
                values=[item],
                parameters=parameters,
            )
        
        return PartiQLParseResult(
            operation=PartiQLOperation.INSERT,
            table_name=table_name,
            parameters=parameters,
        )
    
    def _parse_update(
        self,
        statement: str,
        parameters: Optional[List[Any]] = None,
    ) -> PartiQLParseResult:
        """Parse an UPDATE statement.
        
        Supports: UPDATE table SET col1 = val1, col2 = val2 [WHERE condition]
        
        Args:
            statement: The UPDATE statement
            parameters: Optional parameters
            
        Returns:
            PartiQLParseResult for UPDATE
        """
        # Extract table name
        update_match = re.search(r'UPDATE\s+(\w+)', statement, re.IGNORECASE)
        table_name = update_match.group(1) if update_match else ""
        
        # Extract SET clause
        set_match = re.search(r'SET\s+(.*?)(?:\s+WHERE\s+|$)', statement, re.IGNORECASE)
        set_clause = {}
        if set_match:
            set_str = set_match.group(1)
            set_clause = self._parse_set_clause(set_str, parameters)
        
        # Extract WHERE conditions
        where_conditions = self._parse_where(statement, parameters)
        
        return PartiQLParseResult(
            operation=PartiQLOperation.UPDATE,
            table_name=table_name,
            set_clause=set_clause,
            where_conditions=where_conditions,
            parameters=parameters,
        )
    
    def _parse_delete(
        self,
        statement: str,
        parameters: Optional[List[Any]] = None,
    ) -> PartiQLParseResult:
        """Parse a DELETE statement.
        
        Supports: DELETE FROM table [WHERE condition]
        
        Args:
            statement: The DELETE statement
            parameters: Optional parameters
            
        Returns:
            PartiQLParseResult for DELETE
        """
        # Extract table name
        from_match = re.search(r'DELETE\s+FROM\s+(\w+)', statement, re.IGNORECASE)
        table_name = from_match.group(1) if from_match else ""
        
        # Extract WHERE conditions
        where_conditions = self._parse_where(statement, parameters)
        
        return PartiQLParseResult(
            operation=PartiQLOperation.DELETE,
            table_name=table_name,
            where_conditions=where_conditions,
            parameters=parameters,
        )
    
    def _parse_where(
        self,
        statement: str,
        parameters: Optional[List[Any]] = None,
    ) -> List[Tuple[str, str, Any]]:
        """Parse WHERE clause conditions.
        
        Args:
            statement: The SQL statement
            parameters: Optional parameters for ? placeholders
            
        Returns:
            List of (column, operator, value) tuples
        """
        conditions = []
        
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+LIMIT\s+|$)', statement, re.IGNORECASE)
        if not where_match:
            return conditions
        
        where_str = where_match.group(1)
        
        # Simple condition parser - handles: col = value, col > value, etc.
        # Split by AND
        condition_parts = re.split(r'\s+AND\s+', where_str, flags=re.IGNORECASE)
        
        param_index = 0
        for part in condition_parts:
            part = part.strip()
            # Match: column operator value
            match = re.match(r'(\w+)\s*(=|!=|<>|>|<|>=|<=)\s*(.+)', part)
            if match:
                col = match.group(1)
                op = match.group(2)
                val_str = match.group(3).strip()
                
                # Handle placeholders
                if val_str == '?' and parameters and param_index < len(parameters):
                    value = parameters[param_index]
                    param_index += 1
                else:
                    # Try to parse as literal
                    value = self._parse_value(val_str)
                
                conditions.append((col, op, value))
        
        return conditions
    
    def _parse_limit(self, statement: str) -> Optional[int]:
        """Parse LIMIT clause.
        
        Args:
            statement: The SQL statement
            
        Returns:
            Limit value or None
        """
        limit_match = re.search(r'LIMIT\s+(\d+)', statement, re.IGNORECASE)
        if limit_match:
            return int(limit_match.group(1))
        return None
    
    def _parse_set_clause(
        self,
        set_str: str,
        parameters: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Parse SET clause for UPDATE.
        
        Args:
            set_str: The SET clause string
            parameters: Optional parameters
            
        Returns:
            Dict of column -> value
        """
        result = {}
        param_index = 0
        
        # Split by comma, but handle nested structures
        assignments = self._split_assignments(set_str)
        
        for assignment in assignments:
            match = re.match(r'(\w+)\s*=\s*(.+)', assignment.strip())
            if match:
                col = match.group(1)
                val_str = match.group(2).strip()
                
                # Handle placeholders
                if val_str == '?' and parameters and param_index < len(parameters):
                    value = parameters[param_index]
                    param_index += 1
                else:
                    value = self._parse_value(val_str)
                
                result[col] = value
        
        return result
    
    def _split_assignments(self, set_str: str) -> List[str]:
        """Split SET clause into individual assignments.
        
        Handles commas inside nested structures.
        
        Args:
            set_str: The SET clause string
            
        Returns:
            List of assignment strings
        """
        assignments = []
        current = ""
        depth = 0
        
        for char in set_str:
            if char in '({[':
                depth += 1
            elif char in ')}]':
                depth -= 1
            elif char == ',' and depth == 0:
                assignments.append(current)
                current = ""
                continue
            current += char
        
        if current.strip():
            assignments.append(current)
        
        return assignments
    
    def _parse_values(
        self,
        values_str: str,
        parameters: Optional[List[Any]] = None,
    ) -> List[Any]:
        """Parse VALUES clause values.
        
        Args:
            values_str: The VALUES string
            parameters: Optional parameters
            
        Returns:
            List of values
        """
        values = []
        param_index = 0
        
        # Split by comma
        parts = self._split_by_comma(values_str)
        
        for part in parts:
            part = part.strip()
            if part == '?' and parameters and param_index < len(parameters):
                values.append(parameters[param_index])
                param_index += 1
            else:
                values.append(self._parse_value(part))
        
        return values
    
    def _split_by_comma(self, s: str) -> List[str]:
        """Split string by comma, respecting nested structures.
        
        Args:
            s: String to split
            
        Returns:
            List of parts
        """
        parts = []
        current = ""
        depth = 0
        
        for char in s:
            if char in '({[':
                depth += 1
            elif char in ')}]':
                depth -= 1
            elif char == ',' and depth == 0:
                parts.append(current)
                current = ""
                continue
            current += char
        
        if current.strip():
            parts.append(current)
        
        return parts
    
    def _parse_value(self, val_str: str) -> Any:
        """Parse a value string into a Python value.
        
        Args:
            val_str: The value string
            
        Returns:
            Parsed value
        """
        val_str = val_str.strip()
        
        # String literal
        if (val_str.startswith("'") and val_str.endswith("'")) or \
           (val_str.startswith('"') and val_str.endswith('"')):
            return val_str[1:-1]
        
        # Number
        try:
            if '.' in val_str:
                return float(val_str)
            return int(val_str)
        except ValueError:
            pass
        
        # Boolean
        if val_str.upper() == 'TRUE':
            return True
        if val_str.upper() == 'FALSE':
            return False
        
        # NULL
        if val_str.upper() == 'NULL':
            return None
        
        # Return as-is
        return val_str
    
    def _parse_json_item(
        self,
        item_str: str,
        parameters: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Parse a JSON-style item string.
        
        Simple parser for { 'key': 'value', ... } syntax.
        
        Args:
            item_str: The JSON item string
            parameters: Optional parameters for ? placeholders
            
        Returns:
            Parsed item dict
        """
        result = {}
        param_index = 0
        
        # Remove outer braces
        item_str = item_str.strip()
        if item_str.startswith('{'):
            item_str = item_str[1:]
        if item_str.endswith('}'):
            item_str = item_str[:-1]
        
        # Split by comma at top level
        pairs = self._split_by_comma(item_str)
        
        for pair in pairs:
            match = re.match(r"['\"](\w+)['\"]\s*:\s*(.+)", pair.strip())
            if match:
                key = match.group(1)
                val_str = match.group(2).strip()
                
                # Handle placeholders
                if val_str == '?' and parameters and param_index < len(parameters):
                    value = parameters[param_index]
                    param_index += 1
                else:
                    value = self._parse_value(val_str)
                
                result[key] = value
        
        return result


def parse_partiql(statement: str, parameters: Optional[List[Any]] = None) -> PartiQLParseResult:
    """Parse a PartiQL statement.
    
    Convenience function that creates a parser and parses the statement.
    
    Args:
        statement: The PartiQL statement to parse
        parameters: Optional parameters for the statement
        
    Returns:
        PartiQLParseResult containing the parsed operation details
    """
    parser = PartiQLParser()
    return parser.parse(statement, parameters)
