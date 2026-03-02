"""Evaluator for DynamoDB ConditionExpression."""

from typing import Any

from .condition_parser import Condition, ConditionExpressionParser, ConditionType


class ConditionEvaluator:
    """Evaluates ConditionExpression against items.
    
    Supports all DynamoDB condition operators and functions.
    """
    
    def __init__(self) -> None:
        """Initialize the evaluator."""
        self.parser = ConditionExpressionParser()
    
    def evaluate(
        self,
        item: dict[str, Any],
        expression: str,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> bool:
        """Evaluate a ConditionExpression against an item.
        
        Args:
            item: The item to evaluate against
            expression: The ConditionExpression string
            expression_attribute_names: Optional name placeholders
            expression_attribute_values: Optional value placeholders
        
        Returns:
            True if condition is satisfied, False otherwise
        
        Raises:
            ValueError: If the expression is invalid
        """
        # Parse the expression
        condition = self.parser.parse(expression)
        
        # Evaluate
        return self._evaluate_condition(
            condition,
            item,
            expression_attribute_names or {},
            expression_attribute_values or {},
        )
    
    def _evaluate_condition(
        self,
        condition: Condition,
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate a condition node."""
        if condition.condition_type == ConditionType.COMPARISON:
            return self._evaluate_comparison(condition, item, attr_names, attr_values)
        elif condition.condition_type == ConditionType.FUNCTION:
            return self._evaluate_function(condition, item, attr_names, attr_values)
        elif condition.condition_type == ConditionType.LOGICAL:
            return self._evaluate_logical(condition, item, attr_names, attr_values)
        elif condition.condition_type == ConditionType.BETWEEN:
            return self._evaluate_between(condition, item, attr_names, attr_values)
        elif condition.condition_type == ConditionType.IN:
            return self._evaluate_in(condition, item, attr_names, attr_values)
        
        raise ValueError(f"Unknown condition type: {condition.condition_type}")
    
    def _resolve_name(self, name: str, attr_names: dict[str, str]) -> str:
        """Resolve a name placeholder to actual name."""
        if name.startswith("#"):
            if name not in attr_names:
                raise ValueError(f"Undefined name placeholder: {name}")
            return attr_names[name]
        return name
    
    def _resolve_value(self, value: str, attr_values: dict[str, Any]) -> Any:
        """Resolve a value placeholder to actual value."""
        if value.startswith(":"):
            if value not in attr_values:
                raise ValueError(f"Undefined value placeholder: {value}")
            return attr_values[value]
        
        # Handle quoted strings
        if (value.startswith("'") and value.endswith("'")) or \
           (value.startswith('"') and value.endswith('"')):
            return {"S": value[1:-1]}
        
        # Return as-is for attribute references
        return value
    
    def _get_attribute_value(
        self,
        attr_ref: str,
        item: dict[str, Any],
        attr_names: dict[str, str],
    ) -> Any | None:
        """Get an attribute value from the item."""
        attr_name = self._resolve_name(attr_ref, attr_names)
        return item.get(attr_name)
    
    def _compare_values(self, left: Any, right: Any, op: str) -> bool:
        """Compare two DynamoDB values."""
        # Extract actual values from DynamoDB format
        left_val = self._extract_value(left)
        right_val = self._extract_value(right)
        
        if left_val is None or right_val is None:
            # Handle NULL comparisons
            if op == "=":
                return left_val is None and right_val is None
            elif op == "<>":
                return not (left_val is None and right_val is None)
            return False
        
        # Type coercion for numbers
        if isinstance(left_val, str) and isinstance(right_val, str):
            # Try numeric comparison
            try:
                left_num = float(left_val)
                right_num = float(right_val)
                if op == "=":
                    return left_num == right_num
                elif op == "<>":
                    return left_num != right_num
                elif op == "<":
                    return left_num < right_num
                elif op == "<=":
                    return left_num <= right_num
                elif op == ">":
                    return left_num > right_num
                elif op == ">=":
                    return left_num >= right_num
            except ValueError:
                # String comparison
                pass
        
        # Default comparison
        if op == "=":
            return left_val == right_val
        elif op == "<>":
            return left_val != right_val
        elif op == "<":
            return left_val < right_val
        elif op == "<=":
            return left_val <= right_val
        elif op == ">":
            return left_val > right_val
        elif op == ">=":
            return left_val >= right_val
        
        raise ValueError(f"Unknown comparison operator: {op}")
    
    def _extract_value(self, value: Any) -> Any:
        """Extract the actual value from DynamoDB AttributeValue format."""
        if not isinstance(value, dict):
            return value
        
        if "S" in value:
            return value["S"]
        if "N" in value:
            return value["N"]
        if "B" in value:
            return value["B"]
        if "BOOL" in value:
            return value["BOOL"]
        if "NULL" in value:
            return None
        if "L" in value:
            return value["L"]
        if "M" in value:
            return value["M"]
        if "SS" in value:
            return set(value["SS"])
        if "NS" in value:
            return set(value["NS"])
        if "BS" in value:
            return set(value["BS"])
        
        return value
    
    def _evaluate_comparison(
        self,
        condition: Condition,
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate a comparison condition."""
        left_ref = condition.operands[0]
        right_ref = condition.operands[1]
        op = condition.operator
        
        # Get left value from item
        left_value = self._get_attribute_value(left_ref, item, attr_names)
        
        # Get right value from values
        right_value = self._resolve_value(right_ref, attr_values)
        
        return self._compare_values(left_value, right_value, op)
    
    def _evaluate_function(
        self,
        condition: Condition,
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate a function condition."""
        func_name = condition.operator.lower()
        args = condition.operands
        
        if func_name == "attribute_exists":
            return self._func_attribute_exists(args, item, attr_names)
        elif func_name == "attribute_not_exists":
            return self._func_attribute_not_exists(args, item, attr_names)
        elif func_name == "attribute_type":
            return self._func_attribute_type(args, item, attr_names, attr_values)
        elif func_name == "begins_with":
            return self._func_begins_with(args, item, attr_names, attr_values)
        elif func_name == "contains":
            return self._func_contains(args, item, attr_names, attr_values)
        elif func_name == "size":
            raise ValueError("size() must be used in a comparison expression")
        else:
            raise ValueError(f"Unknown function: {func_name}")
    
    def _func_attribute_exists(
        self,
        args: list[str],
        item: dict[str, Any],
        attr_names: dict[str, str],
    ) -> bool:
        """Evaluate attribute_exists function."""
        if len(args) != 1:
            raise ValueError(f"attribute_exists requires 1 argument, got {len(args)}")
        
        attr_name = self._resolve_name(args[0], attr_names)
        return attr_name in item
    
    def _func_attribute_not_exists(
        self,
        args: list[str],
        item: dict[str, Any],
        attr_names: dict[str, str],
    ) -> bool:
        """Evaluate attribute_not_exists function."""
        if len(args) != 1:
            raise ValueError(f"attribute_not_exists requires 1 argument, got {len(args)}")
        
        attr_name = self._resolve_name(args[0], attr_names)
        return attr_name not in item
    
    def _func_attribute_type(
        self,
        args: list[str],
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate attribute_type function."""
        if len(args) != 2:
            raise ValueError(f"attribute_type requires 2 arguments, got {len(args)}")
        
        attr_name = self._resolve_name(args[0], attr_names)
        expected_type = self._resolve_value(args[1], attr_values)
        
        if attr_name not in item:
            return False
        
        value = item[attr_name]
        if not isinstance(value, dict):
            return False
        
        # Get actual type
        actual_type = list(value.keys())[0] if value else None
        
        if isinstance(expected_type, dict) and "S" in expected_type:
            expected_type = expected_type["S"]
        
        return actual_type == expected_type
    
    def _func_begins_with(
        self,
        args: list[str],
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate begins_with function."""
        if len(args) != 2:
            raise ValueError(f"begins_with requires 2 arguments, got {len(args)}")
        
        attr_name = self._resolve_name(args[0], attr_names)
        prefix = self._resolve_value(args[1], attr_values)
        
        if attr_name not in item:
            return False
        
        value = item[attr_name]
        if "S" not in value:
            return False
        
        if isinstance(prefix, dict) and "S" in prefix:
            prefix = prefix["S"]
        
        return value["S"].startswith(prefix)
    
    def _func_contains(
        self,
        args: list[str],
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate contains function."""
        if len(args) != 2:
            raise ValueError(f"contains requires 2 arguments, got {len(args)}")
        
        attr_name = self._resolve_name(args[0], attr_names)
        search_value = self._resolve_value(args[1], attr_values)
        
        if attr_name not in item:
            return False
        
        value = item[attr_name]
        
        # String contains
        if "S" in value:
            if isinstance(search_value, dict) and "S" in search_value:
                search_value = search_value["S"]
            return search_value in value["S"]
        
        # Set contains
        if "SS" in value:
            if isinstance(search_value, dict) and "S" in search_value:
                search_value = search_value["S"]
            return search_value in value["SS"]
        
        # List contains
        if "L" in value:
            return search_value in value["L"]
        
        return False
    
    def _evaluate_logical(
        self,
        condition: Condition,
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate a logical condition."""
        op = condition.operator.upper()
        operands = condition.operands
        
        if op == "AND":
            return (
                self._evaluate_condition(operands[0], item, attr_names, attr_values) and
                self._evaluate_condition(operands[1], item, attr_names, attr_values)
            )
        elif op == "OR":
            return (
                self._evaluate_condition(operands[0], item, attr_names, attr_values) or
                self._evaluate_condition(operands[1], item, attr_names, attr_values)
            )
        elif op == "NOT":
            return not self._evaluate_condition(operands[0], item, attr_names, attr_values)
        
        raise ValueError(f"Unknown logical operator: {op}")
    
    def _evaluate_between(
        self,
        condition: Condition,
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate a BETWEEN condition."""
        attr_ref = condition.operands[0]
        lower_ref = condition.operands[1]
        upper_ref = condition.operands[2]
        
        # Get attribute value
        attr_value = self._get_attribute_value(attr_ref, item, attr_names)
        
        # Get bounds
        lower_value = self._resolve_value(lower_ref, attr_values)
        upper_value = self._resolve_value(upper_ref, attr_values)
        
        # Compare: lower <= attr <= upper
        return (
            self._compare_values(lower_value, attr_value, "<=") and
            self._compare_values(attr_value, upper_value, "<=")
        )
    
    def _evaluate_in(
        self,
        condition: Condition,
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> bool:
        """Evaluate an IN condition."""
        attr_ref = condition.operands[0]
        value_refs = condition.operands[1:]
        
        # Get attribute value
        attr_value = self._get_attribute_value(attr_ref, item, attr_names)
        
        # Check if value is in the list
        for value_ref in value_refs:
            value = self._resolve_value(value_ref, attr_values)
            if self._compare_values(attr_value, value, "="):
                return True
        
        return False
    
    def evaluate_size_comparison(
        self,
        item: dict[str, Any],
        expression: str,
        attr_names: dict[str, str] | None = None,
        attr_values: dict[str, str] | None = None,
    ) -> bool:
        """Evaluate an expression containing size() comparison.
        
        This is a helper for size() which must be used in comparisons.
        """
        # Simple parsing for size() comparisons
        import re
        
        pattern = r"size\s*\(\s*(#?\w+)\s*\)\s*(=|<>|<|<=|>|>=)\s*(:\w+|\d+)"
        match = re.match(pattern, expression.strip(), re.IGNORECASE)
        
        if not match:
            raise ValueError(f"Invalid size() expression: {expression}")
        
        attr_ref = match.group(1)
        op = match.group(2)
        size_ref = match.group(3)
        
        # Get attribute and calculate size
        attr_name = self._resolve_name(attr_ref, attr_names or {})
        
        if attr_name not in item:
            return False
        
        value = item[attr_name]
        actual_size = self._calculate_size(value)
        
        # Get expected size
        if size_ref.startswith(":"):
            expected_size_val = self._resolve_value(size_ref, attr_values or {})
            if isinstance(expected_size_val, dict) and "N" in expected_size_val:
                expected_size = int(expected_size_val["N"])
            else:
                expected_size = int(expected_size_val)
        else:
            expected_size = int(size_ref)
        
        # Compare
        if op == "=":
            return actual_size == expected_size
        elif op == "<>":
            return actual_size != expected_size
        elif op == "<":
            return actual_size < expected_size
        elif op == "<=":
            return actual_size <= expected_size
        elif op == ">":
            return actual_size > expected_size
        elif op == ">=":
            return actual_size >= expected_size
        
        return False
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate the size of a DynamoDB value."""
        if not isinstance(value, dict):
            return 0
        
        if "S" in value:
            return len(value["S"])
        if "B" in value:
            return len(value["B"])
        if "L" in value:
            return len(value["L"])
        if "M" in value:
            return len(value["M"])
        if "SS" in value:
            return len(value["SS"])
        if "NS" in value:
            return len(value["NS"])
        if "BS" in value:
            return len(value["BS"])
        
        return 0
