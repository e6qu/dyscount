"""Parser for DynamoDB ConditionExpression."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class ConditionType(Enum):
    """Types of condition expressions."""
    COMPARISON = auto()
    FUNCTION = auto()
    LOGICAL = auto()
    BETWEEN = auto()
    IN = auto()


class ComparisonOp(Enum):
    """Comparison operators."""
    EQ = "="
    NE = "<>"
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="


class LogicalOp(Enum):
    """Logical operators."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


@dataclass
class Condition:
    """Represents a condition expression node.
    
    Attributes:
        condition_type: The type of condition
        operator: The operator (comparison, logical, or function name)
        operands: List of operands (can be nested Conditions or values)
    """
    condition_type: ConditionType
    operator: str
    operands: list[Any]


class ConditionExpressionParser:
    """Parser for DynamoDB ConditionExpression strings.
    
    Supports:
    - Comparison operators: =, <>, <, <=, >, >=
    - Logical operators: AND, OR, NOT
    - BETWEEN operator
    - IN operator
    - Functions: attribute_exists, attribute_not_exists, begins_with, contains, size
    """
    
    # Comparison operators (order matters - check multi-char first)
    COMPARISON_OPS = ["<>", "<=", ">=", "=", "<", ">"]
    
    # Logical operators
    LOGICAL_OPS = ["AND", "OR", "NOT"]
    
    # Functions
    FUNCTIONS = [
        "attribute_exists",
        "attribute_not_exists",
        "attribute_type",
        "begins_with",
        "contains",
        "size",
    ]
    
    def __init__(self) -> None:
        """Initialize the parser."""
        self._function_pattern = re.compile(r"(\w+)\s*\(\s*([^)]+)\s*\)")
        self._token_pattern = re.compile(
            r"(\w+|<>|<=|>=|=|<|>|\(|\)|,|:\w+|#\w+|'[^']*'|\"[^\"]*\"|\S)"
        )
    
    def parse(self, expression: str) -> Condition:
        """Parse a ConditionExpression string.
        
        Args:
            expression: The ConditionExpression to parse
        
        Returns:
            Condition AST root node
        
        Raises:
            ValueError: If the expression is invalid
        """
        if not expression or not expression.strip():
            raise ValueError("ConditionExpression cannot be empty")
        
        # Tokenize
        tokens = self._tokenize(expression)
        
        # Parse and build AST
        pos = [0]  # Use list for mutable reference
        result = self._parse_expression(tokens, pos)
        
        if pos[0] < len(tokens):
            raise ValueError(f"Unexpected token: {tokens[pos[0]]}")
        
        return result
    
    def _tokenize(self, expression: str) -> list[str]:
        """Tokenize the expression string."""
        # Handle multi-character operators and special tokens
        tokens = []
        i = 0
        while i < len(expression):
            # Skip whitespace
            if expression[i].isspace():
                i += 1
                continue
            
            # Check for multi-char operators first
            if i + 1 < len(expression):
                two_char = expression[i:i+2]
                if two_char in ["<>", "<=", ">="]:
                    tokens.append(two_char)
                    i += 2
                    continue
            
            # Check for single-char operators
            char = expression[i]
            if char in "=<>(),":
                tokens.append(char)
                i += 1
                continue
            
            # Check for quoted strings
            if char in "'\"":
                end = expression.find(char, i + 1)
                if end == -1:
                    raise ValueError(f"Unterminated string: {expression[i:]}")
                tokens.append(expression[i:end+1])
                i = end + 1
                continue
            
            # Check for identifiers and placeholders
            if char.isalpha() or char == "#" or char == ":":
                j = i + 1
                while j < len(expression) and (expression[j].isalnum() or expression[j] == "_"):
                    j += 1
                tokens.append(expression[i:j])
                i = j
                continue
            
            # Unknown character
            raise ValueError(f"Invalid character in expression: {char}")
        
        return tokens
    
    def _parse_expression(self, tokens: list[str], pos: list[int]) -> Condition:
        """Parse an expression (handles OR)."""
        left = self._parse_and_expression(tokens, pos)
        
        while pos[0] < len(tokens) and tokens[pos[0]].upper() == "OR":
            pos[0] += 1  # Skip OR
            right = self._parse_and_expression(tokens, pos)
            left = Condition(
                condition_type=ConditionType.LOGICAL,
                operator="OR",
                operands=[left, right],
            )
        
        return left
    
    def _parse_and_expression(self, tokens: list[str], pos: list[int]) -> Condition:
        """Parse an AND expression."""
        left = self._parse_not_expression(tokens, pos)
        
        while pos[0] < len(tokens) and tokens[pos[0]].upper() == "AND":
            pos[0] += 1  # Skip AND
            right = self._parse_not_expression(tokens, pos)
            left = Condition(
                condition_type=ConditionType.LOGICAL,
                operator="AND",
                operands=[left, right],
            )
        
        return left
    
    def _parse_not_expression(self, tokens: list[str], pos: list[int]) -> Condition:
        """Parse a NOT expression."""
        if pos[0] < len(tokens) and tokens[pos[0]].upper() == "NOT":
            pos[0] += 1  # Skip NOT
            operand = self._parse_not_expression(tokens, pos)
            return Condition(
                condition_type=ConditionType.LOGICAL,
                operator="NOT",
                operands=[operand],
            )
        
        return self._parse_primary(tokens, pos)
    
    def _parse_primary(self, tokens: list[str], pos: list[int]) -> Condition:
        """Parse a primary expression (comparison, function, or parenthesized)."""
        if pos[0] >= len(tokens):
            raise ValueError("Unexpected end of expression")
        
        token = tokens[pos[0]]
        
        # Parenthesized expression
        if token == "(":
            pos[0] += 1
            result = self._parse_expression(tokens, pos)
            if pos[0] >= len(tokens) or tokens[pos[0]] != ")":
                raise ValueError("Missing closing parenthesis")
            pos[0] += 1
            return result
        
        # Function call
        if token.lower() in [f.lower() for f in self.FUNCTIONS]:
            return self._parse_function(tokens, pos)
        
        # BETWEEN expression
        if pos[0] + 1 < len(tokens) and tokens[pos[0] + 1].upper() == "BETWEEN":
            return self._parse_between(tokens, pos)
        
        # IN expression
        if pos[0] + 1 < len(tokens) and tokens[pos[0] + 1].upper() == "IN":
            return self._parse_in(tokens, pos)
        
        # Comparison expression
        return self._parse_comparison(tokens, pos)
    
    def _parse_function(self, tokens: list[str], pos: list[int]) -> Condition:
        """Parse a function call."""
        func_name = tokens[pos[0]]
        pos[0] += 1
        
        if pos[0] >= len(tokens) or tokens[pos[0]] != "(":
            raise ValueError(f"Expected '(' after function name: {func_name}")
        pos[0] += 1
        
        # Parse arguments
        args = []
        while pos[0] < len(tokens) and tokens[pos[0]] != ")":
            args.append(tokens[pos[0]])
            pos[0] += 1
            
            if pos[0] < len(tokens) and tokens[pos[0]] == ",":
                pos[0] += 1
        
        if pos[0] >= len(tokens) or tokens[pos[0]] != ")":
            raise ValueError(f"Missing closing parenthesis for function: {func_name}")
        pos[0] += 1
        
        return Condition(
            condition_type=ConditionType.FUNCTION,
            operator=func_name,
            operands=args,
        )
    
    def _parse_between(self, tokens: list[str], pos: list[int]) -> Condition:
        """Parse a BETWEEN expression."""
        attr = tokens[pos[0]]
        pos[0] += 1  # Skip attribute
        
        if tokens[pos[0]].upper() != "BETWEEN":
            raise ValueError("Expected BETWEEN")
        pos[0] += 1  # Skip BETWEEN
        
        lower = tokens[pos[0]]
        pos[0] += 1
        
        if tokens[pos[0]].upper() != "AND":
            raise ValueError("Expected AND in BETWEEN expression")
        pos[0] += 1  # Skip AND
        
        upper = tokens[pos[0]]
        pos[0] += 1
        
        return Condition(
            condition_type=ConditionType.BETWEEN,
            operator="BETWEEN",
            operands=[attr, lower, upper],
        )
    
    def _parse_in(self, tokens: list[str], pos: list[int]) -> Condition:
        """Parse an IN expression."""
        attr = tokens[pos[0]]
        pos[0] += 1  # Skip attribute
        
        if tokens[pos[0]].upper() != "IN":
            raise ValueError("Expected IN")
        pos[0] += 1  # Skip IN
        
        if pos[0] >= len(tokens) or tokens[pos[0]] != "(":
            raise ValueError("Expected '(' after IN")
        pos[0] += 1  # Skip (
        
        # Parse values
        values = []
        while pos[0] < len(tokens) and tokens[pos[0]] != ")":
            values.append(tokens[pos[0]])
            pos[0] += 1
            
            if pos[0] < len(tokens) and tokens[pos[0]] == ",":
                pos[0] += 1
        
        if pos[0] >= len(tokens) or tokens[pos[0]] != ")":
            raise ValueError("Missing closing parenthesis for IN expression")
        pos[0] += 1  # Skip )
        
        return Condition(
            condition_type=ConditionType.IN,
            operator="IN",
            operands=[attr] + values,
        )
    
    def _parse_comparison(self, tokens: list[str], pos: list[int]) -> Condition:
        """Parse a comparison expression."""
        left = tokens[pos[0]]
        pos[0] += 1
        
        if pos[0] >= len(tokens):
            raise ValueError(f"Expected operator after: {left}")
        
        op = tokens[pos[0]]
        if op not in self.COMPARISON_OPS:
            raise ValueError(f"Unknown operator: {op}")
        pos[0] += 1
        
        if pos[0] >= len(tokens):
            raise ValueError(f"Expected value after operator: {op}")
        
        right = tokens[pos[0]]
        pos[0] += 1
        
        return Condition(
            condition_type=ConditionType.COMPARISON,
            operator=op,
            operands=[left, right],
        )
