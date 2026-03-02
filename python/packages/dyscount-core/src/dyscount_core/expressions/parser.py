"""Parser for DynamoDB UpdateExpression."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionType(Enum):
    """Types of update actions."""
    SET = "SET"
    REMOVE = "REMOVE"
    ADD = "ADD"
    DELETE = "DELETE"


@dataclass
class UpdateAction:
    """Represents a single update action.
    
    Attributes:
        action_type: The type of action (SET, REMOVE, ADD, DELETE)
        target: The attribute path being modified
        value: The value expression (for SET/ADD/DELETE)
        operator: Optional operator (+, -) for arithmetic
    """
    action_type: ActionType
    target: str
    value: str | None = None
    operator: str | None = None


class UpdateExpressionParser:
    """Parser for DynamoDB UpdateExpression strings.
    
    Supports:
    - SET actions: SET #n = :val, #n = #n + :inc, #n = list_append(#n, :list)
    - REMOVE actions: REMOVE #n, #n2
    - ADD actions: ADD #n :num, #s :set_val
    - DELETE actions: DELETE #s :set_val
    """
    
    def __init__(self) -> None:
        """Initialize the parser."""
        self._action_pattern = re.compile(
            r"(SET|REMOVE|ADD|DELETE)\s+(.+?)(?=(?:SET|REMOVE|ADD|DELETE)\s|$)",
            re.IGNORECASE | re.DOTALL,
        )
        
        # Pattern for SET action: #name = expression
        self._set_pattern = re.compile(
            r"(#\w+|\w+)\s*=\s*(.+?)(?:,\s*(?=#\w+|\w+)\s*=|$)",
            re.DOTALL,
        )
        
        # Pattern for function calls: list_append(#n, :val), if_not_exists(#n, :val)
        self._function_pattern = re.compile(
            r"(\w+)\s*\(\s*([^)]+)\s*\)",
        )
    
    def parse(self, expression: str) -> list[UpdateAction]:
        """Parse an UpdateExpression string.
        
        Args:
            expression: The UpdateExpression to parse
        
        Returns:
            List of UpdateAction objects
        
        Raises:
            ValueError: If the expression is invalid
        """
        if not expression:
            raise ValueError("UpdateExpression cannot be empty")
        
        actions = []
        
        # Find all action clauses (SET, REMOVE, ADD, DELETE)
        matches = list(self._action_pattern.finditer(expression))
        
        if not matches:
            # Try simpler parsing if regex doesn't match
            return self._parse_simple(expression)
        
        for match in matches:
            action_type_str = match.group(1).upper()
            action_content = match.group(2).strip()
            
            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                raise ValueError(f"Invalid action type: {action_type_str}")
            
            # Parse actions based on type
            if action_type == ActionType.SET:
                actions.extend(self._parse_set_actions(action_content))
            elif action_type == ActionType.REMOVE:
                actions.extend(self._parse_remove_actions(action_content))
            elif action_type == ActionType.ADD:
                actions.extend(self._parse_add_actions(action_content))
            elif action_type == ActionType.DELETE:
                actions.extend(self._parse_delete_actions(action_content))
        
        if not actions:
            raise ValueError(f"No valid actions found in expression: {expression}")
        
        return actions
    
    def _parse_simple(self, expression: str) -> list[UpdateAction]:
        """Simple parsing fallback for basic expressions."""
        expression = expression.strip()
        actions = []
        
        # Check for SET
        if expression.upper().startswith("SET "):
            content = expression[4:].strip()
            actions.extend(self._parse_set_actions(content))
        
        return actions
    
    def _parse_set_actions(self, content: str) -> list[UpdateAction]:
        """Parse SET action content."""
        actions = []
        
        # Split by comma, but be careful with nested parentheses
        parts = self._split_by_comma(content)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check for = operator
            if "=" not in part:
                raise ValueError(f"Invalid SET action (missing =): {part}")
            
            target, value = part.split("=", 1)
            target = target.strip()
            value = value.strip()
            
            # Check for arithmetic operators in value
            operator = None
            if " + " in value and not value.startswith("list_append"):
                # Check if it's an arithmetic expression like #n + :val
                operator = "+"
            elif " - " in value and not value.startswith("list_append"):
                operator = "-"
            
            actions.append(UpdateAction(
                action_type=ActionType.SET,
                target=target,
                value=value,
                operator=operator,
            ))
        
        return actions
    
    def _parse_remove_actions(self, content: str) -> list[UpdateAction]:
        """Parse REMOVE action content."""
        actions = []
        
        parts = self._split_by_comma(content)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            actions.append(UpdateAction(
                action_type=ActionType.REMOVE,
                target=part,
            ))
        
        return actions
    
    def _parse_add_actions(self, content: str) -> list[UpdateAction]:
        """Parse ADD action content."""
        actions = []
        
        parts = self._split_by_comma(content)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # ADD format: #name :value
            tokens = part.split()
            if len(tokens) != 2:
                raise ValueError(f"Invalid ADD action (expected '#name :value'): {part}")
            
            actions.append(UpdateAction(
                action_type=ActionType.ADD,
                target=tokens[0],
                value=tokens[1],
            ))
        
        return actions
    
    def _parse_delete_actions(self, content: str) -> list[UpdateAction]:
        """Parse DELETE action content."""
        actions = []
        
        parts = self._split_by_comma(content)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # DELETE format: #name :value
            tokens = part.split()
            if len(tokens) != 2:
                raise ValueError(f"Invalid DELETE action (expected '#name :value'): {part}")
            
            actions.append(UpdateAction(
                action_type=ActionType.DELETE,
                target=tokens[0],
                value=tokens[1],
            ))
        
        return actions
    
    def _split_by_comma(self, content: str) -> list[str]:
        """Split content by comma, respecting parentheses."""
        parts = []
        current = []
        depth = 0
        
        for char in content:
            if char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(char)
        
        if current:
            parts.append("".join(current))
        
        return parts
    
    def is_function_call(self, value: str) -> bool:
        """Check if value is a function call.
        
        Args:
            value: The value expression
        
        Returns:
            True if value is a function call
        """
        return bool(self._function_pattern.match(value.strip()))
    
    def parse_function(self, value: str) -> tuple[str, list[str]]:
        """Parse a function call.
        
        Args:
            value: The function call expression
        
        Returns:
            Tuple of (function_name, args)
        """
        match = self._function_pattern.match(value.strip())
        if not match:
            raise ValueError(f"Invalid function call: {value}")
        
        func_name = match.group(1)
        args_str = match.group(2)
        
        # Split args by comma
        args = [arg.strip() for arg in self._split_by_comma(args_str)]
        
        return func_name, args
