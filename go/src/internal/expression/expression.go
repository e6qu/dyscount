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

// parseCondition parses a condition expression with support for logical operators.
func (e *Evaluator) parseCondition(expr string) (*Condition, error) {
	expr = strings.TrimSpace(expr)
	
	// Parse logical expression tree
	node, err := e.parseLogicalExpr(expr)
	if err != nil {
		return nil, err
	}
	
	return node, nil
}

// parseLogicalExpr parses logical expressions (AND, OR, NOT).
func (e *Evaluator) parseLogicalExpr(expr string) (*Condition, error) {
	expr = strings.TrimSpace(expr)
	
	// Strip outer parentheses
	expr = e.stripOuterParens(expr)
	upperExpr := strings.ToUpper(expr)
	
	// Handle NOT operator (highest precedence among logical operators)
	if strings.HasPrefix(upperExpr, "NOT ") {
		operand, err := e.parseLogicalExpr(expr[4:])
		if err != nil {
			return nil, err
		}
		return &Condition{
			Operator: "NOT",
			Operands: []*Condition{operand},
		}, nil
	}
	
	// Handle AND operator (lower precedence than NOT)
	if andIdx := e.findLogicalOperator(expr, "AND"); andIdx != -1 {
		left, err := e.parseLogicalExpr(expr[:andIdx])
		if err != nil {
			return nil, err
		}
		right, err := e.parseLogicalExpr(expr[andIdx+4:])
		if err != nil {
			return nil, err
		}
		return &Condition{
			Operator: "AND",
			Operands: []*Condition{left, right},
		}, nil
	}
	
	// Handle OR operator (lowest precedence)
	if orIdx := e.findLogicalOperator(expr, "OR"); orIdx != -1 {
		left, err := e.parseLogicalExpr(expr[:orIdx])
		if err != nil {
			return nil, err
		}
		right, err := e.parseLogicalExpr(expr[orIdx+3:])
		if err != nil {
			return nil, err
		}
		return &Condition{
			Operator: "OR",
			Operands: []*Condition{left, right},
		}, nil
	}
	
	// No logical operators - parse simple condition
	return e.parseSimpleCondition(expr)
}

// stripOuterParens removes matching outer parentheses from an expression.
func (e *Evaluator) stripOuterParens(expr string) string {
	expr = strings.TrimSpace(expr)
	for len(expr) >= 2 && expr[0] == '(' && expr[len(expr)-1] == ')' {
		// Make sure the parentheses are matching (not something like "(a) AND (b)")
		if e.isMatchingParen(expr, 0, len(expr)-1) {
			expr = strings.TrimSpace(expr[1 : len(expr)-1])
		} else {
			break
		}
	}
	return expr
}

// isMatchingParen checks if the parentheses at start and end are matching.
func (e *Evaluator) isMatchingParen(expr string, start, end int) bool {
	depth := 0
	for i := start; i <= end; i++ {
		if expr[i] == '(' {
			depth++
		} else if expr[i] == ')' {
			depth--
			if depth == 0 && i < end {
				// Found closing paren before end, so start paren doesn't match end
				return false
			}
		}
	}
	return depth == 0
}

// findLogicalOperator finds the top-level logical operator (not inside parentheses).
// It also avoids matching AND when it's part of a BETWEEN expression.
func (e *Evaluator) findLogicalOperator(expr, op string) int {
	upperExpr := strings.ToUpper(expr)
	opLen := len(op)
	depth := 0
	
	for i := 0; i <= len(upperExpr)-opLen; i++ {
		ch := upperExpr[i]
		
		switch ch {
		case '(':
			depth++
		case ')':
			depth--
		default:
			if depth == 0 && strings.HasPrefix(upperExpr[i:], op) {
				// Make sure it's a whole word (preceded by space or start, followed by space or end)
				if i == 0 || upperExpr[i-1] == ' ' {
					afterIdx := i + opLen
					if afterIdx >= len(upperExpr) || upperExpr[afterIdx] == ' ' {
						// For AND, make sure it's not part of a BETWEEN expression
						if op == "AND" {
							// Check if there's a BETWEEN before this AND
							if e.isBetweenAnd(upperExpr, i) != -1 {
								continue // Skip this AND, it's part of BETWEEN
							}
							// Also check for "BETWEEN ... AND ..." pattern
							if e.isPartOfBetweenExpression(upperExpr, i) {
								continue // Skip this AND
							}
						}
						return i
					}
				}
			}
		}
	}
	
	return -1
}

// isBetweenAnd checks if this AND is part of a "BETWEEN ... AND" pattern
func (e *Evaluator) isBetweenAnd(upperExpr string, andIdx int) int {
	// Look backwards for BETWEEN
	beforeAnd := upperExpr[:andIdx]
	// Check if there's a BETWEEN (not inside parens) before this AND
	if strings.Contains(beforeAnd, " BETWEEN ") {
		// Find the last BETWEEN
		betweenIdx := strings.LastIndex(beforeAnd, " BETWEEN ")
		if betweenIdx != -1 {
			// Check if the BETWEEN is at the same paren depth as the AND
			// and there's no other logical operator between them
			return betweenIdx
		}
	}
	return -1
}

// isPartOfBetweenExpression checks if this AND is part of a BETWEEN expression
func (e *Evaluator) isPartOfBetweenExpression(upperExpr string, andIdx int) bool {
	// Simple heuristic: if there's a BETWEEN somewhere before this AND
	// and no other logical operator (AND/OR) between the BETWEEN and this AND
	beforeAnd := upperExpr[:andIdx]
	
	// Find the last BETWEEN before this AND
	betweenIdx := strings.LastIndex(beforeAnd, " BETWEEN ")
	if betweenIdx == -1 {
		return false
	}
	
	// Check if there's another logical operator between BETWEEN and AND
	betweenSection := beforeAnd[betweenIdx:]
	if strings.Contains(betweenSection, " AND ") || strings.Contains(betweenSection, " OR ") {
		// There's another logical operator, so this AND might be a logical operator
		return false
	}
	
	return true
}

// parseSimpleCondition parses a simple condition without logical operators.
func (e *Evaluator) parseSimpleCondition(expr string) (*Condition, error) {
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
	
	// Handle begins_with function
	if strings.HasPrefix(upperExpr, "BEGINS_WITH(") {
		return e.parseBeginsWith(expr)
	}
	
	// Handle contains function
	if strings.HasPrefix(upperExpr, "CONTAINS(") {
		return e.parseContains(expr)
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

// parseBeginsWith parses a begins_with function call.
func (e *Evaluator) parseBeginsWith(expr string) (*Condition, error) {
	// Extract arguments: begins_with(path, prefix)
	args, err := e.extractFunctionArgs(expr, "begins_with")
	if err != nil {
		return nil, err
	}
	if len(args) != 2 {
		return nil, fmt.Errorf("begins_with requires 2 arguments")
	}
	
	path := e.resolveAttributeName(strings.TrimSpace(args[0]))
	prefix, err := e.resolveValue(strings.TrimSpace(args[1]))
	if err != nil {
		return nil, err
	}
	
	return &Condition{
		Operator: "BEGINS_WITH",
		Path:     path,
		Value:    prefix,
	}, nil
}

// parseContains parses a contains function call.
func (e *Evaluator) parseContains(expr string) (*Condition, error) {
	// Extract arguments: contains(path, operand)
	args, err := e.extractFunctionArgs(expr, "contains")
	if err != nil {
		return nil, err
	}
	if len(args) != 2 {
		return nil, fmt.Errorf("contains requires 2 arguments")
	}
	
	path := e.resolveAttributeName(strings.TrimSpace(args[0]))
	operand, err := e.resolveValue(strings.TrimSpace(args[1]))
	if err != nil {
		return nil, err
	}
	
	return &Condition{
		Operator: "CONTAINS",
		Path:     path,
		Value:    operand,
	}, nil
}

// extractFunctionArgs extracts all arguments from a function call.
func (e *Evaluator) extractFunctionArgs(expr, funcName string) ([]string, error) {
	prefix := funcName + "("
	start := strings.Index(strings.ToLower(expr), strings.ToLower(prefix))
	if start == -1 {
		return nil, fmt.Errorf("invalid %s expression", funcName)
	}
	
	start += len(prefix)
	end := strings.LastIndex(expr, ")")
	if end == -1 || end <= start {
		return nil, fmt.Errorf("invalid %s expression: missing closing paren", funcName)
	}
	
	// Split by comma, respecting parentheses
	argsStr := expr[start:end]
	return e.splitValues(argsStr), nil
}

// parseBetween parses a BETWEEN condition.
func (e *Evaluator) parseBetween(expr string) (*Condition, error) {
	upperExpr := strings.ToUpper(expr)
	betweenIdx := strings.Index(upperExpr, " BETWEEN ")
	
	if betweenIdx == -1 {
		return nil, fmt.Errorf("invalid BETWEEN expression: %s", expr)
	}

	path := strings.TrimSpace(expr[:betweenIdx])
	path = e.resolveAttributeName(path)

	// Find the AND that comes after BETWEEN - it must be at the top level (not inside parens)
	afterBetween := expr[betweenIdx+9:]
	
	// Find the AND that separates lower and upper bounds
	andIdx := e.findAndForBetween(afterBetween)
	if andIdx == -1 {
		return nil, fmt.Errorf("invalid BETWEEN expression, missing AND: %s", expr)
	}

	lowerBound := strings.TrimSpace(afterBetween[:andIdx])
	upperBound := strings.TrimSpace(afterBetween[andIdx+4:]) // +4 for "AND "

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

// findAndForBetween finds the AND that separates lower and upper bounds in a BETWEEN expression.
// It finds the first AND at depth 0.
func (e *Evaluator) findAndForBetween(expr string) int {
	upperExpr := strings.ToUpper(expr)
	depth := 0
	
	for i := 0; i < len(upperExpr)-3; i++ {
		ch := upperExpr[i]
		
		switch ch {
		case '(':
			depth++
		case ')':
			depth--
		default:
			if depth == 0 && upperExpr[i:i+4] == "AND " {
				return i
			}
		}
	}
	
	// Also check for AND at the end (without trailing space)
	if depth == 0 && len(upperExpr) >= 3 && upperExpr[len(upperExpr)-3:] == "AND" {
		return len(upperExpr) - 3
	}
	
	return -1
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
	// Handle logical operators
	switch condition.Operator {
	case "AND":
		for _, operand := range condition.Operands {
			result, err := e.evaluateCondition(item, operand)
			if err != nil {
				return false, err
			}
			if !result {
				return false, nil
			}
		}
		return true, nil
	case "OR":
		for _, operand := range condition.Operands {
			result, err := e.evaluateCondition(item, operand)
			if err != nil {
				return false, err
			}
			if result {
				return true, nil
			}
		}
		return false, nil
	case "NOT":
		if len(condition.Operands) != 1 {
			return false, fmt.Errorf("NOT requires exactly 1 operand")
		}
		result, err := e.evaluateCondition(item, condition.Operands[0])
		if err != nil {
			return false, err
		}
		return !result, nil
	}

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
	case "BEGINS_WITH":
		return e.evaluateBeginsWith(attrValue, condition.Value), nil
	case "CONTAINS":
		return e.evaluateContains(attrValue, condition.Value), nil
	default:
		return false, fmt.Errorf("unsupported operator: %s", condition.Operator)
	}
}

// evaluateBeginsWith checks if a string attribute begins with a prefix.
func (e *Evaluator) evaluateBeginsWith(attrValue, prefix models.AttributeValue) bool {
	attrStr, ok := attrValue.GetString()
	if !ok {
		return false
	}
	prefixStr, ok := prefix.GetString()
	if !ok {
		return false
	}
	return strings.HasPrefix(attrStr, prefixStr)
}

// evaluateContains checks if a string or set contains a value.
func (e *Evaluator) evaluateContains(attrValue, operand models.AttributeValue) bool {
	// Check string contains
	if attrStr, ok := attrValue.GetString(); ok {
		if opStr, ok := operand.GetString(); ok {
			return strings.Contains(attrStr, opStr)
		}
		return false
	}
	
	// Check set contains
	// String set
	if attrSS, ok := attrValue["SS"].([]interface{}); ok {
		if opStr, ok := operand.GetString(); ok {
			for _, v := range attrSS {
				if vs, ok := v.(string); ok && vs == opStr {
					return true
				}
			}
		}
	}
	// Number set
	if attrNS, ok := attrValue["NS"].([]interface{}); ok {
		if opNum, ok := operand.GetNumber(); ok {
			for _, v := range attrNS {
				if vs, ok := v.(string); ok && vs == opNum {
					return true
				}
			}
		}
	}
	
	// Check list contains
	if attrList, ok := attrValue["L"].([]interface{}); ok {
		for _, item := range attrList {
			if itemAV, ok := item.(map[string]interface{}); ok {
				if e.compareValues(models.AttributeValue(itemAV), operand) == 0 {
					return true
				}
			}
		}
	}
	
	return false
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
	Operands []*Condition // For logical operators (AND, OR, NOT)
}
