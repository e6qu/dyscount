// Package expression provides DynamoDB expression parsing and evaluation.
package expression

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/e6qu/dyscount/internal/models"
)

// Evaluator evaluates condition and filter expressions against items.
type Evaluator struct {
	expressionAttributeNames  map[string]string
	expressionAttributeValues map[string]models.AttributeValue
}

// NewEvaluator creates a new expression evaluator.
func NewEvaluator(names map[string]string, values map[string]models.AttributeValue) *Evaluator {
	return &Evaluator{
		expressionAttributeNames:  names,
		expressionAttributeValues: values,
	}
}

// EvaluateCondition evaluates a condition expression against an item.
func (e *Evaluator) EvaluateCondition(item models.Item, conditionExpr string) (bool, error) {
	if conditionExpr == "" {
		return true, nil
	}

	// Simple condition parser - handles basic comparisons
	condition, err := e.parseCondition(conditionExpr)
	if err != nil {
		return false, err
	}

	return e.evaluateCondition(item, condition)
}

// parseCondition parses a simple condition expression.
func (e *Evaluator) parseCondition(expr string) (*Condition, error) {
	expr = strings.TrimSpace(expr)
	upperExpr := strings.ToUpper(expr)

	// Handle attribute_exists function
	if strings.HasPrefix(upperExpr, "ATTRIBUTE_EXISTS(") {
		path := e.extractFunctionArg(expr, "attribute_exists")
		path = e.resolveAttributeName(path)
		exists := true
		return &Condition{Exists: &exists, Path: path}, nil
	}

	// Handle attribute_not_exists function
	if strings.HasPrefix(upperExpr, "ATTRIBUTE_NOT_EXISTS(") {
		path := e.extractFunctionArg(expr, "attribute_not_exists")
		path = e.resolveAttributeName(path)
		exists := false
		return &Condition{Exists: &exists, Path: path}, nil
	}

	// Handle BETWEEN operator
	if strings.Contains(upperExpr, " BETWEEN ") {
		return e.parseBetween(expr)
	}

	// Handle IN operator
	if strings.Contains(upperExpr, " IN ") {
		return e.parseIn(expr)
	}

	// Handle comparison operators
	return e.parseComparison(expr)
}

// extractFunctionArg extracts the argument from a function call.
func (e *Evaluator) extractFunctionArg(expr, funcName string) string {
	prefix := funcName + "("
	suffix := ")"
	
	start := strings.Index(strings.ToLower(expr), strings.ToLower(prefix))
	if start == -1 {
		return ""
	}
	
	start += len(prefix)
	end := strings.LastIndex(expr, suffix)
	if end == -1 || end <= start {
		return ""
	}
	
	return strings.TrimSpace(expr[start:end])
}

// parseBetween parses a BETWEEN condition.
func (e *Evaluator) parseBetween(expr string) (*Condition, error) {
	upperExpr := strings.ToUpper(expr)
	betweenIdx := strings.Index(upperExpr, " BETWEEN ")
	andIdx := strings.Index(upperExpr[betweenIdx+9:], " AND ")
	
	if betweenIdx == -1 || andIdx == -1 {
		return nil, fmt.Errorf("invalid BETWEEN expression: %s", expr)
	}

	path := strings.TrimSpace(expr[:betweenIdx])
	path = e.resolveAttributeName(path)

	lowerBound := strings.TrimSpace(expr[betweenIdx+9 : betweenIdx+9+andIdx])
	upperBound := strings.TrimSpace(expr[betweenIdx+9+andIdx+5:])

	lowerVal, err := e.resolveValue(lowerBound)
	if err != nil {
		return nil, err
	}

	upperVal, err := e.resolveValue(upperBound)
	if err != nil {
		return nil, err
	}

	return &Condition{
		Operator: "BETWEEN",
		Path:     path,
		Values:   []models.AttributeValue{lowerVal, upperVal},
	}, nil
}

// parseIn parses an IN condition.
func (e *Evaluator) parseIn(expr string) (*Condition, error) {
	upperExpr := strings.ToUpper(expr)
	inIdx := strings.Index(upperExpr, " IN ")
	
	if inIdx == -1 {
		return nil, fmt.Errorf("invalid IN expression: %s", expr)
	}

	path := strings.TrimSpace(expr[:inIdx])
	path = e.resolveAttributeName(path)

	// Extract values list
	valuesStart := strings.Index(expr[inIdx+4:], "(")
	valuesEnd := strings.LastIndex(expr, ")")
	
	if valuesStart == -1 || valuesEnd == -1 || valuesEnd <= valuesStart+inIdx+4 {
		return nil, fmt.Errorf("invalid IN expression: %s", expr)
	}

	valuesStr := expr[inIdx+4+valuesStart+1 : valuesEnd]
	values := e.splitValues(valuesStr)

	var resolvedValues []models.AttributeValue
	for _, v := range values {
		val, err := e.resolveValue(strings.TrimSpace(v))
		if err != nil {
			return nil, err
		}
		resolvedValues = append(resolvedValues, val)
	}

	return &Condition{
		Operator: "IN",
		Path:     path,
		Values:   resolvedValues,
	}, nil
}

// parseComparison parses a simple comparison condition.
func (e *Evaluator) parseComparison(expr string) (*Condition, error) {
	// Try different operators (order matters - check longer ones first)
	operators := []struct {
		op   string
		type_ string
	}{
		{"<>", "NE"},
		{"<=", "LE"},
		{">=", "GE"},
		{"=", "EQ"},
		{"<", "LT"},
		{">", "GT"},
	}

	for _, op := range operators {
		if idx := strings.Index(expr, op.op); idx != -1 {
			path := strings.TrimSpace(expr[:idx])
			path = e.resolveAttributeName(path)

			valueStr := strings.TrimSpace(expr[idx+len(op.op):])
			value, err := e.resolveValue(valueStr)
			if err != nil {
				return nil, err
			}

			return &Condition{
				Operator: op.type_,
				Path:     path,
				Value:    value,
			}, nil
		}
	}

	return nil, fmt.Errorf("unsupported condition expression: %s", expr)
}

// resolveAttributeName resolves expression attribute names.
func (e *Evaluator) resolveAttributeName(name string) string {
	if strings.HasPrefix(name, "#") {
		if resolved, ok := e.expressionAttributeNames[name]; ok {
			return resolved
		}
	}
	return name
}

// resolveValue resolves expression attribute values.
func (e *Evaluator) resolveValue(valueStr string) (models.AttributeValue, error) {
	if strings.HasPrefix(valueStr, ":") {
		if val, ok := e.expressionAttributeValues[valueStr]; ok {
			return val, nil
		}
		return nil, fmt.Errorf("undefined value: %s", valueStr)
	}

	// Try to parse as literal
	return e.parseLiteral(valueStr)
}

// parseLiteral parses a literal value.
func (e *Evaluator) parseLiteral(s string) (models.AttributeValue, error) {
	s = strings.TrimSpace(s)

	// String literal
	if strings.HasPrefix(s, "'") && strings.HasSuffix(s, "'") {
		return models.NewStringAttribute(s[1 : len(s)-1]), nil
	}
	if strings.HasPrefix(s, "\"") && strings.HasSuffix(s, "\"") {
		return models.NewStringAttribute(s[1 : len(s)-1]), nil
	}

	// Boolean
	upperS := strings.ToUpper(s)
	if upperS == "TRUE" {
		return models.NewBoolAttribute(true), nil
	}
	if upperS == "FALSE" {
		return models.NewBoolAttribute(false), nil
	}

	// Null
	if upperS == "NULL" {
		return models.NewNullAttribute(), nil
	}

	// Number
	if _, err := strconv.ParseFloat(s, 64); err == nil {
		return models.NewNumberAttribute(s), nil
	}

	return nil, fmt.Errorf("unsupported literal: %s", s)
}

// splitValues splits a comma-separated list of values.
func (e *Evaluator) splitValues(s string) []string {
	var values []string
	var current strings.Builder
	depth := 0

	for _, ch := range s {
		switch ch {
		case '(':
			depth++
			current.WriteRune(ch)
		case ')':
			depth--
			current.WriteRune(ch)
		case ',':
			if depth == 0 {
				values = append(values, current.String())
				current.Reset()
			} else {
				current.WriteRune(ch)
			}
		default:
			current.WriteRune(ch)
		}
	}

	if current.Len() > 0 {
		values = append(values, current.String())
	}

	return values
}

// evaluateCondition evaluates a parsed condition against an item.
func (e *Evaluator) evaluateCondition(item models.Item, condition *Condition) (bool, error) {
	// Handle exists checks
	if condition.Exists != nil {
		_, exists := item[condition.Path]
		return exists == *condition.Exists, nil
	}

	// Get the attribute value from the item
	attrValue, exists := item[condition.Path]
	if !exists {
		// For comparisons, missing attribute is treated as NULL
		attrValue = models.NewNullAttribute()
	}

	switch condition.Operator {
	case "EQ":
		return e.compareValues(attrValue, condition.Value) == 0, nil
	case "NE":
		return e.compareValues(attrValue, condition.Value) != 0, nil
	case "LT":
		return e.compareValues(attrValue, condition.Value) < 0, nil
	case "LE":
		return e.compareValues(attrValue, condition.Value) <= 0, nil
	case "GT":
		return e.compareValues(attrValue, condition.Value) > 0, nil
	case "GE":
		return e.compareValues(attrValue, condition.Value) >= 0, nil
	case "BETWEEN":
		lower := condition.Values[0]
		upper := condition.Values[1]
		return e.compareValues(attrValue, lower) >= 0 && e.compareValues(attrValue, upper) <= 0, nil
	case "IN":
		for _, val := range condition.Values {
			if e.compareValues(attrValue, val) == 0 {
				return true, nil
			}
		}
		return false, nil
	default:
		return false, fmt.Errorf("unsupported operator: %s", condition.Operator)
	}
}

// compareValues compares two attribute values.
func (e *Evaluator) compareValues(a, b models.AttributeValue) int {
	// Handle NULL
	if _, aIsNull := a["NULL"]; aIsNull {
		if _, bIsNull := b["NULL"]; bIsNull {
			return 0
		}
		return -1
	}
	if _, bIsNull := b["NULL"]; bIsNull {
		return 1
	}

	// String comparison
	aStr, aIsStr := a.GetString()
	bStr, bIsStr := b.GetString()
	if aIsStr && bIsStr {
		if aStr < bStr {
			return -1
		} else if aStr > bStr {
			return 1
		}
		return 0
	}

	// Number comparison
	aNum, aIsNum := a.GetNumber()
	bNum, bIsNum := b.GetNumber()
	if aIsNum && bIsNum {
		aFloat, _ := strconv.ParseFloat(aNum, 64)
		bFloat, _ := strconv.ParseFloat(bNum, 64)
		if aFloat < bFloat {
			return -1
		} else if aFloat > bFloat {
			return 1
		}
		return 0
	}

	// Boolean comparison
	aBool, aIsBool := a.GetBool()
	bBool, bIsBool := b.GetBool()
	if aIsBool && bIsBool {
		if aBool == bBool {
			return 0
		}
		if !aBool {
			return -1
		}
		return 1
	}

	// Different types - compare type names
	return strings.Compare(e.typeName(a), e.typeName(b))
}

// typeName returns a string representation of the attribute type.
func (e *Evaluator) typeName(av models.AttributeValue) string {
	if _, ok := av["S"]; ok {
		return "S"
	}
	if _, ok := av["N"]; ok {
		return "N"
	}
	if _, ok := av["B"]; ok {
		return "B"
	}
	if _, ok := av["BOOL"]; ok {
		return "BOOL"
	}
	if _, ok := av["NULL"]; ok {
		return "NULL"
	}
	if _, ok := av["L"]; ok {
		return "L"
	}
	if _, ok := av["M"]; ok {
		return "M"
	}
	if _, ok := av["SS"]; ok {
		return "SS"
	}
	if _, ok := av["NS"]; ok {
		return "NS"
	}
	if _, ok := av["BS"]; ok {
		return "BS"
	}
	return "UNKNOWN"
}

// Condition represents a parsed condition expression.
type Condition struct {
	Operator string
	Path     string
	Value    models.AttributeValue
	Values   []models.AttributeValue
	Exists   *bool
}
