// Package expression provides tests for expression parsing and evaluation.
package expression

import (
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestEvaluateCondition(t *testing.T) {
	tests := []struct {
		name           string
		item           models.Item
		condition      string
		names          map[string]string
		values         map[string]models.AttributeValue
		expectedResult bool
		expectError    bool
	}{
		// Basic comparisons
		{
			name:           "EQ match",
			item:           models.Item{"status": models.NewStringAttribute("active")},
			condition:      "status = :val",
			values:         map[string]models.AttributeValue{":val": models.NewStringAttribute("active")},
			expectedResult: true,
		},
		{
			name:           "EQ no match",
			item:           models.Item{"status": models.NewStringAttribute("inactive")},
			condition:      "status = :val",
			values:         map[string]models.AttributeValue{":val": models.NewStringAttribute("active")},
			expectedResult: false,
		},
		{
			name:           "NE match",
			item:           models.Item{"status": models.NewStringAttribute("inactive")},
			condition:      "status <> :val",
			values:         map[string]models.AttributeValue{":val": models.NewStringAttribute("active")},
			expectedResult: true,
		},
		{
			name:           "GT match",
			item:           models.Item{"age": models.NewNumberAttribute("25")},
			condition:      "age > :val",
			values:         map[string]models.AttributeValue{":val": models.NewNumberAttribute("18")},
			expectedResult: true,
		},
		{
			name:           "LT match",
			item:           models.Item{"age": models.NewNumberAttribute("15")},
			condition:      "age < :val",
			values:         map[string]models.AttributeValue{":val": models.NewNumberAttribute("18")},
			expectedResult: true,
		},
		// BETWEEN
		{
			name:           "BETWEEN match",
			item:           models.Item{"age": models.NewNumberAttribute("25")},
			condition:      "age BETWEEN :low AND :high",
			values:         map[string]models.AttributeValue{
				":low":  models.NewNumberAttribute("18"),
				":high": models.NewNumberAttribute("65"),
			},
			expectedResult: true,
		},
		{
			name:           "BETWEEN no match",
			item:           models.Item{"age": models.NewNumberAttribute("75")},
			condition:      "age BETWEEN :low AND :high",
			values:         map[string]models.AttributeValue{
				":low":  models.NewNumberAttribute("18"),
				":high": models.NewNumberAttribute("65"),
			},
			expectedResult: false,
		},
		// IN
		{
			name:           "IN match",
			item:           models.Item{"status": models.NewStringAttribute("active")},
			condition:      "status IN (:val1, :val2)",
			values:         map[string]models.AttributeValue{
				":val1": models.NewStringAttribute("active"),
				":val2": models.NewStringAttribute("pending"),
			},
			expectedResult: true,
		},
		{
			name:           "IN no match",
			item:           models.Item{"status": models.NewStringAttribute("deleted")},
			condition:      "status IN (:val1, :val2)",
			values:         map[string]models.AttributeValue{
				":val1": models.NewStringAttribute("active"),
				":val2": models.NewStringAttribute("pending"),
			},
			expectedResult: false,
		},
		// attribute_exists
		{
			name:           "attribute_exists true",
			item:           models.Item{"name": models.NewStringAttribute("John")},
			condition:      "attribute_exists(name)",
			expectedResult: true,
		},
		{
			name:           "attribute_exists false",
			item:           models.Item{"name": models.NewStringAttribute("John")},
			condition:      "attribute_exists(age)",
			expectedResult: false,
		},
		// attribute_not_exists
		{
			name:           "attribute_not_exists true",
			item:           models.Item{"name": models.NewStringAttribute("John")},
			condition:      "attribute_not_exists(age)",
			expectedResult: true,
		},
		{
			name:           "attribute_not_exists false",
			item:           models.Item{"name": models.NewStringAttribute("John")},
			condition:      "attribute_not_exists(name)",
			expectedResult: false,
		},
		// AND
		{
			name:      "AND both true",
			item:      models.Item{
				"status": models.NewStringAttribute("active"),
				"age":    models.NewNumberAttribute("25"),
			},
			condition:      "status = :status AND age > :age",
			values: map[string]models.AttributeValue{
				":status": models.NewStringAttribute("active"),
				":age":    models.NewNumberAttribute("18"),
			},
			expectedResult: true,
		},
		{
			name:      "AND first false",
			item:      models.Item{
				"status": models.NewStringAttribute("inactive"),
				"age":    models.NewNumberAttribute("25"),
			},
			condition:      "status = :status AND age > :age",
			values: map[string]models.AttributeValue{
				":status": models.NewStringAttribute("active"),
				":age":    models.NewNumberAttribute("18"),
			},
			expectedResult: false,
		},
		{
			name:      "AND second false",
			item:      models.Item{
				"status": models.NewStringAttribute("active"),
				"age":    models.NewNumberAttribute("15"),
			},
			condition:      "status = :status AND age > :age",
			values: map[string]models.AttributeValue{
				":status": models.NewStringAttribute("active"),
				":age":    models.NewNumberAttribute("18"),
			},
			expectedResult: false,
		},
		// OR
		{
			name:      "OR first true",
			item:      models.Item{
				"status": models.NewStringAttribute("active"),
				"age":    models.NewNumberAttribute("15"),
			},
			condition:      "status = :status OR age > :age",
			values: map[string]models.AttributeValue{
				":status": models.NewStringAttribute("active"),
				":age":    models.NewNumberAttribute("18"),
			},
			expectedResult: true,
		},
		{
			name:      "OR second true",
			item:      models.Item{
				"status": models.NewStringAttribute("inactive"),
				"age":    models.NewNumberAttribute("25"),
			},
			condition:      "status = :status OR age > :age",
			values: map[string]models.AttributeValue{
				":status": models.NewStringAttribute("active"),
				":age":    models.NewNumberAttribute("18"),
			},
			expectedResult: true,
		},
		{
			name:      "OR both false",
			item:      models.Item{
				"status": models.NewStringAttribute("inactive"),
				"age":    models.NewNumberAttribute("15"),
			},
			condition:      "status = :status OR age > :age",
			values: map[string]models.AttributeValue{
				":status": models.NewStringAttribute("active"),
				":age":    models.NewNumberAttribute("18"),
			},
			expectedResult: false,
		},
		// NOT
		{
			name:           "NOT true",
			item:           models.Item{"status": models.NewStringAttribute("inactive")},
			condition:      "NOT status = :val",
			values:         map[string]models.AttributeValue{":val": models.NewStringAttribute("active")},
			expectedResult: true,
		},
		{
			name:           "NOT false",
			item:           models.Item{"status": models.NewStringAttribute("active")},
			condition:      "NOT status = :val",
			values:         map[string]models.AttributeValue{":val": models.NewStringAttribute("active")},
			expectedResult: false,
		},
		// Complex nested
		{
			name:      "AND with OR",
			item:      models.Item{
				"type":   models.NewStringAttribute("user"),
				"status": models.NewStringAttribute("active"),
				"age":    models.NewNumberAttribute("25"),
			},
			condition:      "type = :type AND (status = :status OR age < :age)",
			values: map[string]models.AttributeValue{
				":type":   models.NewStringAttribute("user"),
				":status": models.NewStringAttribute("active"),
				":age":    models.NewNumberAttribute("18"),
			},
			expectedResult: true,
		},
		// begins_with
		{
			name:           "begins_with match",
			item:           models.Item{"email": models.NewStringAttribute("user@example.com")},
			condition:      "begins_with(email, :prefix)",
			values:         map[string]models.AttributeValue{":prefix": models.NewStringAttribute("user@")},
			expectedResult: true,
		},
		{
			name:           "begins_with no match",
			item:           models.Item{"email": models.NewStringAttribute("admin@example.com")},
			condition:      "begins_with(email, :prefix)",
			values:         map[string]models.AttributeValue{":prefix": models.NewStringAttribute("user@")},
			expectedResult: false,
		},
		// contains
		{
			name:           "contains string match",
			item:           models.Item{"description": models.NewStringAttribute("This is a test")},
			condition:      "contains(description, :substr)",
			values:         map[string]models.AttributeValue{":substr": models.NewStringAttribute("test")},
			expectedResult: true,
		},
		{
			name:           "contains string no match",
			item:           models.Item{"description": models.NewStringAttribute("This is a test")},
			condition:      "contains(description, :substr)",
			values:         map[string]models.AttributeValue{":substr": models.NewStringAttribute("hello")},
			expectedResult: false,
		},
		// Expression attribute names
		{
			name:           "expression attribute names",
			item:           models.Item{"status": models.NewStringAttribute("active")},
			condition:      "#s = :val",
			names:          map[string]string{"#s": "status"},
			values:         map[string]models.AttributeValue{":val": models.NewStringAttribute("active")},
			expectedResult: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			evaluator := NewEvaluator(tt.names, tt.values)
			result, err := evaluator.EvaluateCondition(tt.item, tt.condition)

			if tt.expectError {
				if err == nil {
					t.Errorf("Expected error but got none")
				}
				return
			}

			if err != nil {
				t.Errorf("Unexpected error: %v", err)
				return
			}

			if result != tt.expectedResult {
				t.Errorf("Expected %v but got %v", tt.expectedResult, result)
			}
		})
	}
}

func TestEvaluateConditionEmpty(t *testing.T) {
	evaluator := NewEvaluator(nil, nil)
	result, err := evaluator.EvaluateCondition(models.Item{}, "")
	if err != nil {
		t.Errorf("Unexpected error for empty condition: %v", err)
	}
	if !result {
		t.Error("Empty condition should return true")
	}
}
