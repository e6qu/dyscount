// Package models provides DynamoDB-compatible data models.
package models

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

// AttributeValue represents a DynamoDB attribute value with type information.
// This matches DynamoDB's typed JSON format.
type AttributeValue map[string]interface{}

// NewStringAttribute creates a string attribute value.
func NewStringAttribute(s string) AttributeValue {
	return AttributeValue{"S": s}
}

// NewNumberAttribute creates a number attribute value.
func NewNumberAttribute(n string) AttributeValue {
	return AttributeValue{"N": n}
}

// NewBinaryAttribute creates a binary attribute value (base64 encoded).
func NewBinaryAttribute(b []byte) AttributeValue {
	return AttributeValue{"B": base64.StdEncoding.EncodeToString(b)}
}

// NewStringSetAttribute creates a string set attribute value.
func NewStringSetAttribute(ss []string) AttributeValue {
	return AttributeValue{"SS": ss}
}

// NewNumberSetAttribute creates a number set attribute value.
func NewNumberSetAttribute(ns []string) AttributeValue {
	return AttributeValue{"NS": ns}
}

// NewBinarySetAttribute creates a binary set attribute value.
func NewBinarySetAttribute(bs [][]byte) AttributeValue {
	encoded := make([]string, len(bs))
	for i, b := range bs {
		encoded[i] = base64.StdEncoding.EncodeToString(b)
	}
	return AttributeValue{"BS": encoded}
}

// NewListAttribute creates a list attribute value.
func NewListAttribute(l []AttributeValue) AttributeValue {
	return AttributeValue{"L": l}
}

// NewMapAttribute creates a map attribute value.
func NewMapAttribute(m map[string]AttributeValue) AttributeValue {
	return AttributeValue{"M": m}
}

// NewBoolAttribute creates a boolean attribute value.
func NewBoolAttribute(b bool) AttributeValue {
	return AttributeValue{"BOOL": b}
}

// NewNullAttribute creates a null attribute value.
func NewNullAttribute() AttributeValue {
	return AttributeValue{"NULL": true}
}

// GetString extracts a string value from an AttributeValue.
func (av AttributeValue) GetString() (string, bool) {
	if s, ok := av["S"].(string); ok {
		return s, true
	}
	return "", false
}

// GetNumber extracts a number value (as string) from an AttributeValue.
func (av AttributeValue) GetNumber() (string, bool) {
	if n, ok := av["N"].(string); ok {
		return n, true
	}
	return "", false
}

// GetBinary extracts a binary value from an AttributeValue.
func (av AttributeValue) GetBinary() ([]byte, bool) {
	if b, ok := av["B"].(string); ok {
		data, err := base64.StdEncoding.DecodeString(b)
		if err != nil {
			return nil, false
		}
		return data, true
	}
	return nil, false
}

// GetBool extracts a boolean value from an AttributeValue.
func (av AttributeValue) GetBool() (bool, bool) {
	if b, ok := av["BOOL"].(bool); ok {
		return b, true
	}
	return false, false
}

// GetNull checks if the attribute is null.
func (av AttributeValue) GetNull() bool {
	if null, ok := av["NULL"].(bool); ok {
		return null
	}
	return false
}

// GetStringSet extracts a string set from an AttributeValue.
func (av AttributeValue) GetStringSet() ([]string, bool) {
	if ss, ok := av["SS"].([]interface{}); ok {
		result := make([]string, len(ss))
		for i, v := range ss {
			if s, ok := v.(string); ok {
				result[i] = s
			}
		}
		return result, true
	}
	return nil, false
}

// GetNumberSet extracts a number set from an AttributeValue.
func (av AttributeValue) GetNumberSet() ([]string, bool) {
	if ns, ok := av["NS"].([]interface{}); ok {
		result := make([]string, len(ns))
		for i, v := range ns {
			if n, ok := v.(string); ok {
				result[i] = n
			}
		}
		return result, true
	}
	return nil, false
}

// GetList extracts a list from an AttributeValue.
func (av AttributeValue) GetList() ([]AttributeValue, bool) {
	if l, ok := av["L"].([]interface{}); ok {
		result := make([]AttributeValue, len(l))
		for i, v := range l {
			if item, ok := v.(map[string]interface{}); ok {
				result[i] = AttributeValue(item)
			}
		}
		return result, true
	}
	return nil, false
}

// GetMap extracts a map from an AttributeValue.
func (av AttributeValue) GetMap() (map[string]AttributeValue, bool) {
	if m, ok := av["M"].(map[string]interface{}); ok {
		result := make(map[string]AttributeValue)
		for k, v := range m {
			if item, ok := v.(map[string]interface{}); ok {
				result[k] = AttributeValue(item)
			}
		}
		return result, true
	}
	return nil, false
}

// GetType returns the type of the attribute value.
func (av AttributeValue) GetType() string {
	for k := range av {
		switch k {
		case "S", "N", "B", "SS", "NS", "BS", "L", "M", "BOOL", "NULL":
			return k
		}
	}
	return ""
}

// Item represents a DynamoDB item as a map of attribute names to attribute values.
type Item map[string]AttributeValue

// GetKeyAttribute extracts a key attribute value as string for comparison.
func (item Item) GetKeyAttribute(name string, keyType string) (string, error) {
	attr, ok := item[name]
	if !ok {
		return "", fmt.Errorf("attribute not found: %s", name)
	}

	switch keyType {
	case "S":
		if s, ok := attr.GetString(); ok {
			return s, nil
		}
		return "", fmt.Errorf("attribute %s is not a string", name)
	case "N":
		if n, ok := attr.GetNumber(); ok {
			return n, nil
		}
		return "", fmt.Errorf("attribute %s is not a number", name)
	case "B":
		if b, ok := attr.GetBinary(); ok {
			return base64.StdEncoding.EncodeToString(b), nil
		}
		return "", fmt.Errorf("attribute %s is not binary", name)
	default:
		return "", fmt.Errorf("unsupported key type: %s", keyType)
	}
}

// Clone creates a deep copy of an item.
func (item Item) Clone() Item {
	if item == nil {
		return nil
	}
	clone := make(Item, len(item))
	for k, v := range item {
		clone[k] = cloneAttributeValue(v)
	}
	return clone
}

// cloneAttributeValue creates a deep copy of an attribute value.
func cloneAttributeValue(av AttributeValue) AttributeValue {
	if av == nil {
		return nil
	}
	clone := make(AttributeValue, len(av))
	for k, v := range av {
		switch k {
		case "L":
			if list, ok := v.([]interface{}); ok {
				newList := make([]interface{}, len(list))
				for i, item := range list {
					if m, ok := item.(map[string]interface{}); ok {
						newList[i] = cloneAttributeValue(AttributeValue(m))
					}
				}
				clone[k] = newList
			}
		case "M":
			if m, ok := v.(map[string]interface{}); ok {
				newMap := make(map[string]interface{})
				for mk, mv := range m {
					if inner, ok := mv.(map[string]interface{}); ok {
						newMap[mk] = cloneAttributeValue(AttributeValue(inner))
					}
				}
				clone[k] = newMap
			}
		default:
			clone[k] = v
		}
	}
	return clone
}

// ToJSON serializes an item to JSON bytes.
func (item Item) ToJSON() ([]byte, error) {
	return json.Marshal(item)
}

// ItemFromJSON deserializes JSON bytes to an item.
func ItemFromJSON(data []byte) (Item, error) {
	var item Item
	if err := json.Unmarshal(data, &item); err != nil {
		return nil, err
	}
	return item, nil
}

// ExtractKey extracts the key attributes (pk, sk) from an item based on key schema.
func (item Item) ExtractKey(keySchema []KeySchemaElement, attrDefs []AttributeDefinition) (pk, sk string, err error) {
	var pkName, skName, pkType, skType string

	for _, ks := range keySchema {
		if ks.KeyType == "HASH" {
			pkName = ks.AttributeName
			// Find type from attribute definitions
			for _, ad := range attrDefs {
				if ad.AttributeName == pkName {
					pkType = ad.AttributeType
					break
				}
			}
		} else if ks.KeyType == "RANGE" {
			skName = ks.AttributeName
			// Find type from attribute definitions
			for _, ad := range attrDefs {
				if ad.AttributeName == skName {
					skType = ad.AttributeType
					break
				}
			}
		}
	}

	if pkName == "" {
		return "", "", fmt.Errorf("no HASH key found in key schema")
	}

	pk, err = item.GetKeyAttribute(pkName, pkType)
	if err != nil {
		return "", "", fmt.Errorf("failed to get partition key: %w", err)
	}

	if skName != "" {
		sk, err = item.GetKeyAttribute(skName, skType)
		if err != nil {
			return "", "", fmt.Errorf("failed to get sort key: %w", err)
		}
	}

	return pk, sk, nil
}

// Compare compares two items for equality.
func (item Item) Compare(other Item) bool {
	if len(item) != len(other) {
		return false
	}
	for k, v := range item {
		otherV, ok := other[k]
		if !ok {
			return false
		}
		if !compareAttributeValues(v, otherV) {
			return false
		}
	}
	return true
}

// compareAttributeValues compares two attribute values for equality.
func compareAttributeValues(a, b AttributeValue) bool {
	if len(a) != len(b) {
		return false
	}
	for k, v := range a {
		otherV, ok := b[k]
		if !ok {
			return false
		}
		// Handle nested types
		switch k {
		case "L":
			listA, okA := v.([]interface{})
			listB, okB := otherV.([]interface{})
			if !okA || !okB || len(listA) != len(listB) {
				return false
			}
			for i := range listA {
				mapA, okA := listA[i].(map[string]interface{})
				mapB, okB := listB[i].(map[string]interface{})
				if !okA || !okB || !compareAttributeValues(AttributeValue(mapA), AttributeValue(mapB)) {
					return false
				}
			}
		case "M":
			mapA, okA := v.(map[string]interface{})
			mapB, okB := otherV.(map[string]interface{})
			if !okA || !okB || len(mapA) != len(mapB) {
				return false
			}
			for mk, mv := range mapA {
				innerA, okA := mv.(map[string]interface{})
				innerB, okB := mapB[mk].(map[string]interface{})
				if !okA || !okB || !compareAttributeValues(AttributeValue(innerA), AttributeValue(innerB)) {
					return false
				}
			}
		default:
			// Simple comparison for scalar types
			if fmt.Sprintf("%v", v) != fmt.Sprintf("%v", otherV) {
				return false
			}
		}
	}
	return true
}

// MatchesKeyCondition checks if an item matches a key condition (pk = value).
func (item Item) MatchesKeyCondition(pkName, pkValue string, attrDefs []AttributeDefinition) bool {
	attr, ok := item[pkName]
	if !ok {
		return false
	}

	// Get the type of the partition key
	var pkType string
	for _, ad := range attrDefs {
		if ad.AttributeName == pkName {
			pkType = ad.AttributeType
			break
		}
	}

	switch pkType {
	case "S":
		if s, ok := attr.GetString(); ok {
			return s == pkValue
		}
	case "N":
		if n, ok := attr.GetNumber(); ok {
			return n == pkValue
		}
	case "B":
		if b, ok := attr.GetBinary(); ok {
			return base64.StdEncoding.EncodeToString(b) == pkValue
		}
	}
	return false
}

// MatchesSortKeyRange checks if an item's sort key is within a range.
func (item Item) MatchesSortKeyRange(skName, skType string, comparisonOp string, value string) bool {
	attr, ok := item[skName]
	if !ok {
		return false
	}

	var itemValue string
	switch skType {
	case "S":
		if s, ok := attr.GetString(); ok {
			itemValue = s
		}
	case "N":
		if n, ok := attr.GetNumber(); ok {
			itemValue = n
		}
	case "B":
		if b, ok := attr.GetBinary(); ok {
			itemValue = base64.StdEncoding.EncodeToString(b)
		}
	}

	if itemValue == "" {
		return false
	}

	switch comparisonOp {
	case "EQ":
		return itemValue == value
	case "LT":
		return compareValues(itemValue, value, skType) < 0
	case "LE":
		return compareValues(itemValue, value, skType) <= 0
	case "GT":
		return compareValues(itemValue, value, skType) > 0
	case "GE":
		return compareValues(itemValue, value, skType) >= 0
	case "BEGINS_WITH":
		return strings.HasPrefix(itemValue, value)
	default:
		return false
	}
}

// compareValues compares two values of the same type.
// Returns -1 if a < b, 0 if a == b, 1 if a > b.
func compareValues(a, b, valueType string) int {
	switch valueType {
	case "N":
		numA, errA := strconv.ParseFloat(a, 64)
		numB, errB := strconv.ParseFloat(b, 64)
		if errA != nil || errB != nil {
			return strings.Compare(a, b)
		}
		if numA < numB {
			return -1
		} else if numA > numB {
			return 1
		}
		return 0
	default:
		return strings.Compare(a, b)
	}
}

// CompareValues is a public version of compareValues for use by other packages.
// Returns -1 if a < b, 0 if a == b, 1 if a > b.
func CompareValues(a, b, valueType string) int {
	return compareValues(a, b, valueType)
}
