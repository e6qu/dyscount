"""Parser for DynamoDB KeyConditionExpression.

KeyConditionExpression is used in Query operations to specify the key conditions.
It supports:
- Partition key equality: pk = :value
- Sort key comparisons: sk = :val, sk < :val, sk <= :val, sk > :val, sk >= :val
- Sort key BETWEEN: sk BETWEEN :low AND :high
- Sort key begins_with: begins_with(sk, :prefix)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class KeyConditionType(Enum):
    """Types of key condition expressions."""
    EQ = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    BETWEEN = auto()
    BEGINS_WITH = auto()


@dataclass
class KeyCondition:
    """Represents a key condition.
    
    Attributes:
        key_name: The name of the key attribute
        condition_type: The type of condition
        values: List of values for the condition
    """
    key_name: str
    condition_type: KeyConditionType
    values: list[Any]


class KeyConditionExpressionParser:
    """Parser for DynamoDB KeyConditionExpression.
    
    Supports:
    - Partition key equality: pk = :value
    - Sort key comparisons: sk = :val, sk < :val, sk <= :val, sk > :val, sk >= :val
    - Sort key BETWEEN: sk BETWEEN :low AND :high
    - Sort key begins_with: begins_with(sk, :prefix)
    """
    
    def parse(
        self,
        expression: str,
        expression_attribute_names: dict[str, str] | None = None,
    ) -> tuple[KeyCondition, KeyCondition | None]:
        """Parse a KeyConditionExpression.
        
        Args:
            expression: The KeyConditionExpression string
            expression_attribute_names: Optional name placeholders
            
        Returns:
            Tuple of (partition_key_condition, sort_key_condition_or_none)
            
        Raises:
            ValueError: If the expression is invalid
        """
        if not expression or not expression.strip():
            raise ValueError("KeyConditionExpression cannot be empty")
        
        expr = expression.strip()
        attr_names = expression_attribute_names or {}
        
        # Parse AND-separated conditions
        if " AND " in expr.upper():
            parts = self._split_by_and(expr)
            if len(parts) != 2:
                raise ValueError("KeyConditionExpression can have at most two conditions")
            
            cond1 = self._parse_single_condition(parts[0], attr_names)
            cond2 = self._parse_single_condition(parts[1], attr_names)
            
            return cond1, cond2
        else:
            # Single condition (partition key only)
            cond = self._parse_single_condition(expr, attr_names)
            return cond, None
    
    def _split_by_and(self, expr: str) -> list[str]:
        """Split expression by AND, respecting case."""
        # Find AND in a case-insensitive way but preserve original case in parts
        # Be careful not to split on AND that's inside BETWEEN...AND
        import re
        
        # First, temporarily replace BETWEEN...AND patterns
        # to protect them from splitting
        between_pattern = r'BETWEEN\s+\S+\s+AND\s+\S+'
        matches = list(re.finditer(between_pattern, expr, re.IGNORECASE))
        
        if not matches:
            # No BETWEEN, safe to split on AND
            parts = re.split(r'\s+AND\s+', expr, flags=re.IGNORECASE)
            return [p.strip() for p in parts if p.strip()]
        
        # Replace BETWEEN...AND with placeholders
        placeholders = {}
        modified_expr = expr
        for i, match in enumerate(matches):
            placeholder = f"__BETWEEN{i}__"
            placeholders[placeholder] = match.group(0)
            modified_expr = modified_expr.replace(match.group(0), placeholder, 1)
        
        # Now split on AND
        parts = re.split(r'\s+AND\s+', modified_expr, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]
        
        # Restore BETWEEN...AND patterns
        result = []
        for part in parts:
            for placeholder, original in placeholders.items():
                part = part.replace(placeholder, original)
            result.append(part)
        
        return result
    
    def _parse_single_condition(
        self,
        expr: str,
        attr_names: dict[str, str],
    ) -> KeyCondition:
        """Parse a single key condition."""
        expr = expr.strip()
        
        # Check for begins_with
        if expr.lower().startswith("begins_with("):
            return self._parse_begins_with(expr, attr_names)
        
        # Check for BETWEEN
        if " BETWEEN " in expr.upper():
            return self._parse_between(expr, attr_names)
        
        # Parse comparison operators
        return self._parse_comparison(expr, attr_names)
    
    def _parse_begins_with(
        self,
        expr: str,
        attr_names: dict[str, str],
    ) -> KeyCondition:
        """Parse begins_with condition."""
        # Format: begins_with(#name, :value) or begins_with(name, :value)
        if not expr.endswith(")"):
            raise ValueError(f"Invalid begins_with syntax: {expr}")
        
        inner = expr[12:-1]  # Remove "begins_with(" and ")"
        parts = [p.strip() for p in inner.split(",")]
        
        if len(parts) != 2:
            raise ValueError(f"begins_with requires 2 arguments: {expr}")
        
        key_name = self._resolve_name(parts[0], attr_names)
        value_ref = parts[1].strip()
        
        return KeyCondition(
            key_name=key_name,
            condition_type=KeyConditionType.BEGINS_WITH,
            values=[value_ref],
        )
    
    def _parse_between(
        self,
        expr: str,
        attr_names: dict[str, str],
    ) -> KeyCondition:
        """Parse BETWEEN condition."""
        # Format: #name BETWEEN :low AND :high
        import re
        match = re.match(
            r'(.+?)\s+BETWEEN\s+(.+?)\s+AND\s+(.+)',
            expr,
            re.IGNORECASE
        )
        
        if not match:
            raise ValueError(f"Invalid BETWEEN syntax: {expr}")
        
        key_name = self._resolve_name(match.group(1).strip(), attr_names)
        lower = match.group(2).strip()
        upper = match.group(3).strip()
        
        return KeyCondition(
            key_name=key_name,
            condition_type=KeyConditionType.BETWEEN,
            values=[lower, upper],
        )
    
    def _parse_comparison(
        self,
        expr: str,
        attr_names: dict[str, str],
    ) -> KeyCondition:
        """Parse comparison condition (=, <, <=, >, >=)."""
        # Multi-char operators first
        operators = [
            ("<=", KeyConditionType.LE),
            (">=", KeyConditionType.GE),
            ("=", KeyConditionType.EQ),
            ("<", KeyConditionType.LT),
            (">", KeyConditionType.GT),
        ]
        
        for op_str, op_type in operators:
            if op_str in expr:
                parts = expr.split(op_str, 1)
                if len(parts) == 2:
                    key_name = self._resolve_name(parts[0].strip(), attr_names)
                    value = parts[1].strip()
                    return KeyCondition(
                        key_name=key_name,
                        condition_type=op_type,
                        values=[value],
                    )
        
        raise ValueError(f"Invalid key condition: {expr}")
    
    def _resolve_name(self, name: str, attr_names: dict[str, str]) -> str:
        """Resolve a name placeholder to actual name."""
        if name.startswith("#"):
            if name not in attr_names:
                raise ValueError(f"Undefined name placeholder: {name}")
            return attr_names[name]
        return name
