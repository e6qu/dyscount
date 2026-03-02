"""Unit tests for condition parser and evaluator."""

import pytest
from dyscount_core.expressions.condition_parser import (
    ConditionExpressionParser,
    Condition,
    ConditionType,
)
from dyscount_core.expressions.condition_evaluator import ConditionEvaluator


class TestConditionParser:
    """Test the condition expression parser."""
    
    @pytest.fixture
    def parser(self):
        return ConditionExpressionParser()
    
    def test_parse_simple_comparison(self, parser):
        """Test parsing a simple comparison."""
        condition = parser.parse("#n = :val")
        assert condition.condition_type == ConditionType.COMPARISON
        assert condition.operator == "="
        assert condition.operands == ["#n", ":val"]
    
    def test_parse_comparison_ne(self, parser):
        """Test parsing not-equal comparison."""
        condition = parser.parse("#n <> :val")
        assert condition.condition_type == ConditionType.COMPARISON
        assert condition.operator == "<>"
    
    def test_parse_comparison_lt(self, parser):
        """Test parsing less-than comparison."""
        condition = parser.parse("#n < :val")
        assert condition.condition_type == ConditionType.COMPARISON
        assert condition.operator == "<"
    
    def test_parse_comparison_le(self, parser):
        """Test parsing less-than-or-equal comparison."""
        condition = parser.parse("#n <= :val")
        assert condition.condition_type == ConditionType.COMPARISON
        assert condition.operator == "<="
    
    def test_parse_comparison_gt(self, parser):
        """Test parsing greater-than comparison."""
        condition = parser.parse("#n > :val")
        assert condition.condition_type == ConditionType.COMPARISON
        assert condition.operator == ">"
    
    def test_parse_comparison_ge(self, parser):
        """Test parsing greater-than-or-equal comparison."""
        condition = parser.parse("#n >= :val")
        assert condition.condition_type == ConditionType.COMPARISON
        assert condition.operator == ">="
    
    def test_parse_and_operator(self, parser):
        """Test parsing AND operator."""
        condition = parser.parse("#a = :val1 AND #b = :val2")
        assert condition.condition_type == ConditionType.LOGICAL
        assert condition.operator == "AND"
        assert len(condition.operands) == 2
    
    def test_parse_or_operator(self, parser):
        """Test parsing OR operator."""
        condition = parser.parse("#a = :val1 OR #b = :val2")
        assert condition.condition_type == ConditionType.LOGICAL
        assert condition.operator == "OR"
        assert len(condition.operands) == 2
    
    def test_parse_not_operator(self, parser):
        """Test parsing NOT operator."""
        condition = parser.parse("NOT #a = :val")
        assert condition.condition_type == ConditionType.LOGICAL
        assert condition.operator == "NOT"
        assert len(condition.operands) == 1
    
    def test_parse_and_or_precedence(self, parser):
        """Test that AND has higher precedence than OR."""
        condition = parser.parse("#a = :v1 OR #b = :v2 AND #c = :v3")
        assert condition.condition_type == ConditionType.LOGICAL
        assert condition.operator == "OR"
        # Should be: (#a = :v1) OR ((#b = :v2) AND (#c = :v3))
        assert len(condition.operands) == 2
    
    def test_parse_function_attribute_exists(self, parser):
        """Test parsing attribute_exists function."""
        condition = parser.parse("attribute_exists(#n)")
        assert condition.condition_type == ConditionType.FUNCTION
        assert condition.operator == "attribute_exists"
        assert condition.operands == ["#n"]
    
    def test_parse_function_attribute_not_exists(self, parser):
        """Test parsing attribute_not_exists function."""
        condition = parser.parse("attribute_not_exists(#n)")
        assert condition.condition_type == ConditionType.FUNCTION
        assert condition.operator == "attribute_not_exists"
    
    def test_parse_function_begins_with(self, parser):
        """Test parsing begins_with function."""
        condition = parser.parse("begins_with(#n, :prefix)")
        assert condition.condition_type == ConditionType.FUNCTION
        assert condition.operator == "begins_with"
        assert len(condition.operands) == 2
    
    def test_parse_function_contains(self, parser):
        """Test parsing contains function."""
        condition = parser.parse("contains(#n, :val)")
        assert condition.condition_type == ConditionType.FUNCTION
        assert condition.operator == "contains"
        assert len(condition.operands) == 2
    
    def test_parse_between(self, parser):
        """Test parsing BETWEEN operator."""
        condition = parser.parse("#n BETWEEN :low AND :high")
        assert condition.condition_type == ConditionType.BETWEEN
        assert condition.operator == "BETWEEN"
        assert len(condition.operands) == 3
    
    def test_parse_in(self, parser):
        """Test parsing IN operator."""
        condition = parser.parse("#n IN (:v1, :v2, :v3)")
        assert condition.condition_type == ConditionType.IN
        assert condition.operator == "IN"
        assert len(condition.operands) == 4  # attr + 3 values
    
    def test_parse_parentheses(self, parser):
        """Test parsing parenthesized expressions."""
        condition = parser.parse("(#a = :v1 AND #b = :v2) OR #c = :v3")
        assert condition.condition_type == ConditionType.LOGICAL
        assert condition.operator == "OR"
    
    def test_parse_empty_expression_raises(self, parser):
        """Test that empty expression raises error."""
        with pytest.raises(ValueError):
            parser.parse("")
        
        with pytest.raises(ValueError):
            parser.parse("   ")


class TestConditionEvaluator:
    """Test the condition evaluator."""
    
    @pytest.fixture
    def evaluator(self):
        return ConditionEvaluator()
    
    def test_evaluate_eq_true(self, evaluator):
        """Test equality comparison when true."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(item, "#n = :val", {"#n": "name"}, {":val": {"S": "John"}})
        assert result is True
    
    def test_evaluate_eq_false(self, evaluator):
        """Test equality comparison when false."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(item, "#n = :val", {"#n": "name"}, {":val": {"S": "Jane"}})
        assert result is False
    
    def test_evaluate_ne_true(self, evaluator):
        """Test not-equal comparison when true."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(item, "#n <> :val", {"#n": "name"}, {":val": {"S": "Jane"}})
        assert result is True
    
    def test_evaluate_number_comparison(self, evaluator):
        """Test numeric comparison."""
        item = {"age": {"N": "30"}}
        result = evaluator.evaluate(item, "#a < :val", {"#a": "age"}, {":val": {"N": "40"}})
        assert result is True
    
    def test_evaluate_and_true(self, evaluator):
        """Test AND when both conditions true."""
        item = {"name": {"S": "John"}, "age": {"N": "30"}}
        result = evaluator.evaluate(
            item, 
            "#n = :name AND #a = :age",
            {"#n": "name", "#a": "age"},
            {":name": {"S": "John"}, ":age": {"N": "30"}}
        )
        assert result is True
    
    def test_evaluate_and_false(self, evaluator):
        """Test AND when one condition false."""
        item = {"name": {"S": "John"}, "age": {"N": "30"}}
        result = evaluator.evaluate(
            item,
            "#n = :name AND #a = :age",
            {"#n": "name", "#a": "age"},
            {":name": {"S": "John"}, ":age": {"N": "99"}}
        )
        assert result is False
    
    def test_evaluate_or_true(self, evaluator):
        """Test OR when one condition true."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(
            item,
            "#n = :name OR #n = :other",
            {"#n": "name"},
            {":name": {"S": "John"}, ":other": {"S": "Jane"}}
        )
        assert result is True
    
    def test_evaluate_or_false(self, evaluator):
        """Test OR when both conditions false."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(
            item,
            "#n = :v1 OR #n = :v2",
            {"#n": "name"},
            {":v1": {"S": "Jane"}, ":v2": {"S": "Bob"}}
        )
        assert result is False
    
    def test_evaluate_not(self, evaluator):
        """Test NOT operator."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(
            item,
            "NOT #n = :val",
            {"#n": "name"},
            {":val": {"S": "Jane"}}
        )
        assert result is True
    
    def test_evaluate_attribute_exists_true(self, evaluator):
        """Test attribute_exists when attribute exists."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(item, "attribute_exists(#n)", {"#n": "name"}, {})
        assert result is True
    
    def test_evaluate_attribute_exists_false(self, evaluator):
        """Test attribute_exists when attribute doesn't exist."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(item, "attribute_exists(#n)", {"#n": "age"}, {})
        assert result is False
    
    def test_evaluate_attribute_not_exists_true(self, evaluator):
        """Test attribute_not_exists when attribute doesn't exist."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(item, "attribute_not_exists(#n)", {"#n": "age"}, {})
        assert result is True
    
    def test_evaluate_begins_with_true(self, evaluator):
        """Test begins_with when true."""
        item = {"name": {"S": "John Doe"}}
        result = evaluator.evaluate(
            item,
            "begins_with(#n, :prefix)",
            {"#n": "name"},
            {":prefix": {"S": "John"}}
        )
        assert result is True
    
    def test_evaluate_begins_with_false(self, evaluator):
        """Test begins_with when false."""
        item = {"name": {"S": "John Doe"}}
        result = evaluator.evaluate(
            item,
            "begins_with(#n, :prefix)",
            {"#n": "name"},
            {":prefix": {"S": "Jane"}}
        )
        assert result is False
    
    def test_evaluate_contains_string(self, evaluator):
        """Test contains with string."""
        item = {"name": {"S": "John Doe"}}
        result = evaluator.evaluate(
            item,
            "contains(#n, :sub)",
            {"#n": "name"},
            {":sub": {"S": "Doe"}}
        )
        assert result is True
    
    def test_evaluate_contains_list(self, evaluator):
        """Test contains with list."""
        item = {"tags": {"L": [{"S": "tag1"}, {"S": "tag2"}]}}
        result = evaluator.evaluate(
            item,
            "contains(#t, :val)",
            {"#t": "tags"},
            {":val": {"S": "tag1"}}
        )
        assert result is True
    
    def test_evaluate_between_true(self, evaluator):
        """Test BETWEEN when value is in range."""
        item = {"age": {"N": "30"}}
        result = evaluator.evaluate(
            item,
            "#a BETWEEN :low AND :high",
            {"#a": "age"},
            {":low": {"N": "20"}, ":high": {"N": "40"}}
        )
        assert result is True
    
    def test_evaluate_between_false(self, evaluator):
        """Test BETWEEN when value is out of range."""
        item = {"age": {"N": "50"}}
        result = evaluator.evaluate(
            item,
            "#a BETWEEN :low AND :high",
            {"#a": "age"},
            {":low": {"N": "20"}, ":high": {"N": "40"}}
        )
        assert result is False
    
    def test_evaluate_in_true(self, evaluator):
        """Test IN when value is in list."""
        item = {"name": {"S": "John"}}
        result = evaluator.evaluate(
            item,
            "#n IN (:v1, :v2)",
            {"#n": "name"},
            {":v1": {"S": "Jane"}, ":v2": {"S": "John"}}
        )
        assert result is True
    
    def test_evaluate_in_false(self, evaluator):
        """Test IN when value is not in list."""
        item = {"name": {"S": "Bob"}}
        result = evaluator.evaluate(
            item,
            "#n IN (:v1, :v2)",
            {"#n": "name"},
            {":v1": {"S": "Jane"}, ":v2": {"S": "John"}}
        )
        assert result is False
    
    def test_evaluate_empty_item(self, evaluator):
        """Test evaluation with empty item."""
        result = evaluator.evaluate({}, "attribute_not_exists(#n)", {"#n": "name"}, {})
        assert result is True
    
    def test_evaluate_undefined_name_placeholder(self, evaluator):
        """Test error on undefined name placeholder."""
        item = {"name": {"S": "John"}}
        with pytest.raises(ValueError):
            evaluator.evaluate(item, "#n = :val", {}, {":val": {"S": "John"}})
    
    def test_evaluate_undefined_value_placeholder(self, evaluator):
        """Test error on undefined value placeholder."""
        item = {"name": {"S": "John"}}
        with pytest.raises(ValueError):
            evaluator.evaluate(item, "#n = :val", {"#n": "name"}, {})
