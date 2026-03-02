"""Evaluator for DynamoDB UpdateExpression actions."""

from typing import Any

from .parser import ActionType, UpdateAction, UpdateExpressionParser


class ExpressionEvaluator:
    """Evaluates UpdateExpression actions against items.
    
    Supports:
    - SET actions with arithmetic and functions
    - REMOVE actions
    - ADD actions for numbers and sets
    - DELETE actions for sets
    """
    
    def __init__(self) -> None:
        """Initialize the evaluator."""
        self.parser = UpdateExpressionParser()
    
    def evaluate(
        self,
        item: dict[str, Any],
        expression: str,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate an UpdateExpression against an item.
        
        Args:
            item: The item to update
            expression: The UpdateExpression string
            expression_attribute_names: Optional name placeholders (#name -> actual_name)
            expression_attribute_values: Optional value placeholders (:val -> value)
        
        Returns:
            The updated item
        
        Raises:
            ValueError: If the expression is invalid
        """
        # Parse the expression
        actions = self.parser.parse(expression)
        
        # Apply each action
        for action in actions:
            item = self._apply_action(
                item,
                action,
                expression_attribute_names or {},
                expression_attribute_values or {},
            )
        
        return item
    
    def _apply_action(
        self,
        item: dict[str, Any],
        action: UpdateAction,
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply a single update action.
        
        Args:
            item: The item to update
            action: The update action
            attr_names: Name placeholders
            attr_values: Value placeholders
        
        Returns:
            The updated item
        """
        if action.action_type == ActionType.SET:
            return self._apply_set(item, action, attr_names, attr_values)
        elif action.action_type == ActionType.REMOVE:
            return self._apply_remove(item, action, attr_names)
        elif action.action_type == ActionType.ADD:
            return self._apply_add(item, action, attr_names, attr_values)
        elif action.action_type == ActionType.DELETE:
            return self._apply_delete(item, action, attr_names, attr_values)
        
        return item
    
    def _apply_set(
        self,
        item: dict[str, Any],
        action: UpdateAction,
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply a SET action."""
        # Resolve target attribute name
        target = self._resolve_name(action.target, attr_names)
        
        if action.value is None:
            raise ValueError(f"SET action missing value for target: {target}")
        
        # Check if value is a function call
        if self.parser.is_function_call(action.value):
            value = self._evaluate_function(action.value, item, attr_names, attr_values)
        elif action.operator == "+":
            # Arithmetic: #n + :val or #n + #m
            value = self._evaluate_arithmetic(action.value, item, attr_names, attr_values, "+")
        elif action.operator == "-":
            value = self._evaluate_arithmetic(action.value, item, attr_names, attr_values, "-")
        else:
            # Simple value substitution
            value = self._resolve_value(action.value, attr_values)
        
        item[target] = value
        return item
    
    def _apply_remove(
        self,
        item: dict[str, Any],
        action: UpdateAction,
        attr_names: dict[str, str],
    ) -> dict[str, Any]:
        """Apply a REMOVE action."""
        target = self._resolve_name(action.target, attr_names)
        
        if target in item:
            del item[target]
        
        return item
    
    def _apply_add(
        self,
        item: dict[str, Any],
        action: UpdateAction,
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply an ADD action."""
        target = self._resolve_name(action.target, attr_names)
        value = self._resolve_value(action.value, attr_values)
        
        if target not in item:
            # If attribute doesn't exist, set it to the value
            item[target] = value
            return item
        
        current = item[target]
        
        # Check if it's a number addition
        if "N" in current and "N" in value:
            # Number addition
            current_num = float(current["N"])
            add_num = float(value["N"])
            item[target] = {"N": str(current_num + add_num)}
        elif "SS" in current and "SS" in value:
            # String set union
            current_set = set(current["SS"])
            add_set = set(value["SS"])
            item[target] = {"SS": list(current_set | add_set)}
        elif "NS" in current and "NS" in value:
            # Number set union
            current_set = set(current["NS"])
            add_set = set(value["NS"])
            item[target] = {"NS": list(current_set | add_set)}
        elif "BS" in current and "BS" in value:
            # Binary set union
            current_set = set(current["BS"])
            add_set = set(value["BS"])
            item[target] = {"BS": list(current_set | add_set)}
        else:
            raise ValueError(f"Cannot ADD incompatible types: {current} and {value}")
        
        return item
    
    def _apply_delete(
        self,
        item: dict[str, Any],
        action: UpdateAction,
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply a DELETE action (for sets only)."""
        target = self._resolve_name(action.target, attr_names)
        value = self._resolve_value(action.value, attr_values)
        
        if target not in item:
            return item
        
        current = item[target]
        
        # DELETE only works on sets
        if "SS" in current and "SS" in value:
            current_set = set(current["SS"])
            del_set = set(value["SS"])
            item[target] = {"SS": list(current_set - del_set)}
        elif "NS" in current and "NS" in value:
            current_set = set(current["NS"])
            del_set = set(value["NS"])
            item[target] = {"NS": list(current_set - del_set)}
        elif "BS" in current and "BS" in value:
            current_set = set(current["BS"])
            del_set = set(value["BS"])
            item[target] = {"BS": list(current_set - del_set)}
        else:
            raise ValueError(f"DELETE can only be used on sets: {current}")
        
        return item
    
    def _resolve_name(self, name: str, attr_names: dict[str, str]) -> str:
        """Resolve a name placeholder to actual name."""
        if name.startswith("#"):
            if name not in attr_names:
                raise ValueError(f"Undefined name placeholder: {name}")
            return attr_names[name]
        return name
    
    def _resolve_value(self, value: str | None, attr_values: dict[str, Any]) -> Any:
        """Resolve a value placeholder to actual value."""
        if value is None:
            return None
        
        if value.startswith(":"):
            if value not in attr_values:
                raise ValueError(f"Undefined value placeholder: {value}")
            return attr_values[value]
        
        # Might be a literal or path reference
        return value
    
    def _evaluate_function(
        self,
        func_call: str,
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> Any:
        """Evaluate a function call."""
        func_name, args = self.parser.parse_function(func_call)
        
        if func_name == "list_append":
            return self._func_list_append(args, item, attr_names, attr_values)
        elif func_name == "if_not_exists":
            return self._func_if_not_exists(args, item, attr_names, attr_values)
        else:
            raise ValueError(f"Unknown function: {func_name}")
    
    def _func_list_append(
        self,
        args: list[str],
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> Any:
        """Evaluate list_append function."""
        if len(args) != 2:
            raise ValueError(f"list_append requires 2 arguments, got {len(args)}")
        
        # First arg is the list attribute
        list_attr = self._resolve_name(args[0], attr_names)
        
        # Get current list or empty
        if list_attr in item:
            current = item[list_attr]
            if "L" not in current:
                raise ValueError(f"list_append can only be used on lists: {current}")
            result = list(current["L"])  # Copy
        else:
            result = []
        
        # Second arg is the list to append
        append_val = self._resolve_value(args[1], attr_values)
        
        if isinstance(append_val, str):
            # Might be an attribute reference
            append_attr = self._resolve_name(append_val, attr_names)
            if append_attr in item:
                append_list = item[append_attr]
                if "L" not in append_list:
                    raise ValueError(f"list_append can only append lists: {append_list}")
                result.extend(append_list["L"])
            else:
                # Try as value placeholder
                append_val = self._resolve_value(args[1], attr_values)
                if "L" in append_val:
                    result.extend(append_val["L"])
                else:
                    result.append(append_val)
        elif isinstance(append_val, dict) and "L" in append_val:
            result.extend(append_val["L"])
        else:
            result.append(append_val)
        
        return {"L": result}
    
    def _func_if_not_exists(
        self,
        args: list[str],
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
    ) -> Any:
        """Evaluate if_not_exists function."""
        if len(args) != 2:
            raise ValueError(f"if_not_exists requires 2 arguments, got {len(args)}")
        
        # First arg is the attribute to check
        attr = self._resolve_name(args[0], attr_names)
        
        # If attribute exists, return its value
        if attr in item:
            return item[attr]
        
        # Otherwise, return the default value
        default_val = self._resolve_value(args[1], attr_values)
        
        if isinstance(default_val, str):
            default_val = self._resolve_name(default_val, attr_names)
            if default_val in item:
                return item[default_val]
        
        return default_val
    
    def _evaluate_arithmetic(
        self,
        expression: str,
        item: dict[str, Any],
        attr_names: dict[str, str],
        attr_values: dict[str, Any],
        operator: str,
    ) -> Any:
        """Evaluate an arithmetic expression."""
        # Split by operator
        parts = expression.split(operator)
        if len(parts) != 2:
            raise ValueError(f"Invalid arithmetic expression: {expression}")
        
        left = parts[0].strip()
        right = parts[1].strip()
        
        # Resolve left operand (should be an attribute)
        left_attr = self._resolve_name(left, attr_names)
        if left_attr not in item:
            raise ValueError(f"Attribute not found for arithmetic: {left_attr}")
        
        left_val = item[left_attr]
        if "N" not in left_val:
            raise ValueError(f"Arithmetic requires numeric attribute: {left_val}")
        
        left_num = float(left_val["N"])
        
        # Resolve right operand (can be attribute or value)
        if right.startswith("#"):
            right_attr = self._resolve_name(right, attr_names)
            if right_attr not in item:
                raise ValueError(f"Attribute not found for arithmetic: {right_attr}")
            right_val = item[right_attr]
            if "N" not in right_val:
                raise ValueError(f"Arithmetic requires numeric attribute: {right_val}")
            right_num = float(right_val["N"])
        else:
            right_val = self._resolve_value(right, attr_values)
            if isinstance(right_val, dict) and "N" in right_val:
                right_num = float(right_val["N"])
            else:
                raise ValueError(f"Arithmetic requires numeric value: {right_val}")
        
        # Perform calculation
        if operator == "+":
            result = left_num + right_num
        else:
            result = left_num - right_num
        
        # Return as DynamoDB number format
        return {"N": str(int(result) if result == int(result) else result)}
