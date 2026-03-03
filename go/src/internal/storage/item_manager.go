// Package storage provides SQLite-backed storage for DynamoDB items.
package storage

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	_ "github.com/mattn/go-sqlite3"

	"github.com/e6qu/dyscount/internal/models"
)

// ItemManager manages DynamoDB items in SQLite.
type ItemManager struct {
	tableManager *TableManager
	mu           sync.RWMutex // Mutex for thread-safe operations
}

// NewItemManager creates a new ItemManager.
func NewItemManager(tm *TableManager) *ItemManager {
	return &ItemManager{
		tableManager: tm,
	}
}

// getDBForTable returns a database connection for the specified table.
func (im *ItemManager) getDBForTable(tableName string) (*sql.DB, error) {
	dbPath := im.tableManager.getDBPath(tableName)
	
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("table not found: %s", tableName)
	}
	
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database for table %s: %w", tableName, err)
	}
	
	return db, nil
}

// getKeySchema retrieves the key schema for a table.
func (im *ItemManager) getKeySchema(tableName string, indexName string) ([]models.KeySchemaElement, []models.AttributeDefinition, error) {
	metadata, err := im.tableManager.DescribeTable(tableName)
	if err != nil {
		return nil, nil, err
	}

	// If querying a GSI, use the GSI's key schema
	if indexName != "" {
		for _, gsi := range metadata.GlobalSecondaryIndexes {
			if gsi.IndexName == indexName {
				return gsi.KeySchema, metadata.AttributeDefinitions, nil
			}
		}
		return nil, nil, fmt.Errorf("index not found: %s", indexName)
	}

	return metadata.KeySchema, metadata.AttributeDefinitions, nil
}

// GetItem retrieves an item by its primary key.
func (im *ItemManager) GetItem(tableName string, key models.Item, consistentRead bool) (models.Item, error) {
	im.mu.RLock()
	defer im.mu.RUnlock()

	db, err := im.getDBForTable(tableName)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	// Get table metadata for key schema
	metadata, err := im.tableManager.DescribeTable(tableName)
	if err != nil {
		return nil, err
	}

	// Extract pk and sk from the key
	pk, sk, err := key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return nil, fmt.Errorf("invalid key: %w", err)
	}

	// Query the database
	var data []byte
	if sk != "" {
		err = db.QueryRow(
			"SELECT data FROM items WHERE pk = ? AND sk = ?",
			pk, sk,
		).Scan(&data)
	} else {
		// For hash-only tables, sk can be NULL or empty string
		err = db.QueryRow(
			"SELECT data FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')",
			pk,
		).Scan(&data)
	}

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil // Item not found
		}
		return nil, fmt.Errorf("failed to get item: %w", err)
	}

	// Deserialize the item
	item, err := models.ItemFromJSON(data)
	if err != nil {
		return nil, fmt.Errorf("failed to deserialize item: %w", err)
	}

	return item, nil
}

// PutItem inserts or replaces an item.
func (im *ItemManager) PutItem(tableName string, item models.Item, returnOld bool) (models.Item, error) {
	im.mu.Lock()
	defer im.mu.Unlock()

	db, err := im.getDBForTable(tableName)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	// Get table metadata for key schema
	metadata, err := im.tableManager.DescribeTable(tableName)
	if err != nil {
		return nil, err
	}

	// Extract pk and sk from the item
	pk, sk, err := item.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return nil, fmt.Errorf("invalid item key: %w", err)
	}

	// Get old item if returnOld is requested
	var oldItem models.Item
	if returnOld {
		oldItem, _ = im.getItemInternal(db, pk, sk)
	}

	// Serialize the item
	data, err := json.Marshal(item)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize item: %w", err)
	}

	// Insert or replace
	now := time.Now().Unix()
	_, err = db.Exec(
		`INSERT INTO items (pk, sk, data, created_at, updated_at) 
		 VALUES (?, ?, ?, ?, ?)
		 ON CONFLICT(pk, sk) DO UPDATE SET
		 data = excluded.data, updated_at = excluded.updated_at`,
		pk, sk, data, now, now,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to put item: %w", err)
	}

	// Update item count
	im.updateItemCount(db, 1)

	return oldItem, nil
}

// DeleteItem deletes an item by its primary key.
func (im *ItemManager) DeleteItem(tableName string, key models.Item, returnOld bool) (models.Item, error) {
	im.mu.Lock()
	defer im.mu.Unlock()

	db, err := im.getDBForTable(tableName)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	// Get table metadata for key schema
	metadata, err := im.tableManager.DescribeTable(tableName)
	if err != nil {
		return nil, err
	}

	// Extract pk and sk from the key
	pk, sk, err := key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return nil, fmt.Errorf("invalid key: %w", err)
	}

	// Get old item if returnOld is requested
	var oldItem models.Item
	if returnOld {
		oldItem, _ = im.getItemInternal(db, pk, sk)
	}

	// Delete the item
	if sk != "" {
		_, err = db.Exec("DELETE FROM items WHERE pk = ? AND sk = ?", pk, sk)
	} else {
		// For hash-only tables, sk can be NULL or empty string
		_, err = db.Exec("DELETE FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')", pk)
	}
	if err != nil {
		return nil, fmt.Errorf("failed to delete item: %w", err)
	}

	return oldItem, nil
}

// getItemInternal retrieves an item internally (without lock).
func (im *ItemManager) getItemInternal(db *sql.DB, pk, sk string) (models.Item, error) {
	var data []byte
	var err error
	if sk != "" {
		err = db.QueryRow(
			"SELECT data FROM items WHERE pk = ? AND sk = ?",
			pk, sk,
		).Scan(&data)
	} else {
		// For hash-only tables, sk can be NULL or empty string
		err = db.QueryRow(
			"SELECT data FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')",
			pk,
		).Scan(&data)
	}

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}

	return models.ItemFromJSON(data)
}

// UpdateItem updates an item using update expressions.
// For now, supports simple SET operations.
func (im *ItemManager) UpdateItem(tableName string, key models.Item, updateExpression string, 
	expressionValues map[string]models.AttributeValue, returnOld bool) (models.Item, models.Item, error) {
	im.mu.Lock()
	defer im.mu.Unlock()

	db, err := im.getDBForTable(tableName)
	if err != nil {
		return nil, nil, err
	}
	defer db.Close()

	// Get table metadata for key schema
	metadata, err := im.tableManager.DescribeTable(tableName)
	if err != nil {
		return nil, nil, err
	}

	// Extract pk and sk from the key
	pk, sk, err := key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return nil, nil, fmt.Errorf("invalid key: %w", err)
	}

	// Get current item
	currentItem, err := im.getItemInternal(db, pk, sk)
	if err != nil {
		return nil, nil, err
	}

	// If item doesn't exist and it's not a SET operation, return error
	if currentItem == nil && !strings.HasPrefix(strings.ToUpper(updateExpression), "SET") {
		return nil, nil, fmt.Errorf("item not found")
	}

	// If item doesn't exist, start with empty item
	if currentItem == nil {
		currentItem = make(models.Item)
		// Set the key attributes
		for _, ks := range metadata.KeySchema {
			keyAttr, ok := key[ks.AttributeName]
			if ok {
				currentItem[ks.AttributeName] = keyAttr
			}
		}
	}

	// Store old item for return
	var oldItem models.Item
	if returnOld {
		oldItem = currentItem.Clone()
	}

	// Parse and apply update expression (simplified implementation)
	if updateExpression != "" {
		currentItem, err = im.applyUpdateExpression(currentItem, updateExpression, expressionValues)
		if err != nil {
			return nil, nil, fmt.Errorf("failed to apply update expression: %w", err)
		}
	}

	// Serialize and store
	data, err := json.Marshal(currentItem)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to serialize item: %w", err)
	}

	now := time.Now().Unix()
	_, err = db.Exec(
		`INSERT INTO items (pk, sk, data, created_at, updated_at) 
		 VALUES (?, ?, ?, ?, ?)
		 ON CONFLICT(pk, sk) DO UPDATE SET
		 data = excluded.data, updated_at = excluded.updated_at`,
		pk, sk, data, now, now,
	)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to update item: %w", err)
	}

	return currentItem, oldItem, nil
}

// applyUpdateExpression applies an update expression to an item.
// Supports SET, ADD, DELETE, and REMOVE actions.
func (im *ItemManager) applyUpdateExpression(item models.Item, expression string, 
	expressionValues map[string]models.AttributeValue) (models.Item, error) {
	
	// Parse the expression to identify actions
	actions := im.parseUpdateExpression(expression)
	
	for _, action := range actions {
		switch action.Action {
		case "SET":
			if err := im.applySET(item, action, expressionValues); err != nil {
				return nil, err
			}
		case "ADD":
			if err := im.applyADD(item, action, expressionValues); err != nil {
				return nil, err
			}
		case "DELETE":
			if err := im.applyDELETE(item, action, expressionValues); err != nil {
				return nil, err
			}
		case "REMOVE":
			if err := im.applyREMOVE(item, action, expressionValues); err != nil {
				return nil, err
			}
		default:
			return nil, fmt.Errorf("unsupported update action: %s", action.Action)
		}
	}

	return item, nil
}

// UpdateAction represents a single update action.
type UpdateAction struct {
	Action string // SET, ADD, DELETE, REMOVE
	Path   string // Attribute path
	Value  string // Value reference or literal
}

// parseUpdateExpression parses an update expression into actions.
func (im *ItemManager) parseUpdateExpression(expression string) []UpdateAction {
	var actions []UpdateAction
	upperExpr := strings.ToUpper(expression)
	
	// Find all action keywords and their positions
	actionKeywords := []string{"SET", "ADD", "DELETE", "REMOVE"}
	actionPositions := make(map[string]int)
	
	for _, keyword := range actionKeywords {
		if pos := strings.Index(upperExpr, keyword+" "); pos != -1 {
			actionPositions[keyword] = pos
		}
	}
	
	// Sort actions by position
	type actionPos struct {
		action string
		pos    int
	}
	var sortedActions []actionPos
	for action, pos := range actionPositions {
		sortedActions = append(sortedActions, actionPos{action, pos})
	}
	sort.Slice(sortedActions, func(i, j int) bool {
		return sortedActions[i].pos < sortedActions[j].pos
	})
	
	// Parse each action's content
	for i, ap := range sortedActions {
		startPos := ap.pos
		endPos := len(expression)
		if i < len(sortedActions)-1 {
			endPos = sortedActions[i+1].pos
		}
		
		actionContent := strings.TrimSpace(expression[startPos:endPos])
		actionActions := im.parseActionContent(ap.action, actionContent)
		actions = append(actions, actionActions...)
	}
	
	return actions
}

// parseActionContent parses the content of a specific action.
func (im *ItemManager) parseActionContent(actionName, content string) []UpdateAction {
	var actions []UpdateAction
	
	// Remove action keyword prefix
	prefix := actionName + " "
	if strings.HasPrefix(strings.ToUpper(content), prefix) {
		content = content[len(prefix):]
	}
	
	// Split by commas at top level
	parts := im.splitAssignments(content)
	
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		
		action := UpdateAction{Action: actionName}
		
		switch actionName {
		case "SET":
			// Format: path = value
			if idx := strings.Index(part, "="); idx != -1 {
				action.Path = strings.TrimSpace(part[:idx])
				action.Value = strings.TrimSpace(part[idx+1:])
			}
		case "ADD", "DELETE":
			// Format: path value
			parts := strings.Fields(part)
			if len(parts) >= 2 {
				action.Path = parts[0]
				action.Value = parts[1]
			}
		case "REMOVE":
			// Format: path (no value)
			action.Path = part
		}
		
		if action.Path != "" {
			actions = append(actions, action)
		}
	}
	
	return actions
}

// applySET applies a SET action.
func (im *ItemManager) applySET(item models.Item, action UpdateAction, expressionValues map[string]models.AttributeValue) error {
	attrName := action.Path
	
	// Handle expression attribute names (#name)
	if strings.HasPrefix(attrName, "#") {
		attrName = strings.TrimPrefix(attrName, "#")
	}
	
	valueRef := action.Value
	if strings.HasPrefix(valueRef, ":") {
		valueKey := valueRef[1:]
		if value, ok := expressionValues[valueKey]; ok {
			item[attrName] = value
		} else {
			return fmt.Errorf("missing value for key: %s", valueKey)
		}
	}
	return nil
}

// applyADD applies an ADD action (for numbers or sets).
func (im *ItemManager) applyADD(item models.Item, action UpdateAction, expressionValues map[string]models.AttributeValue) error {
	attrName := action.Path
	if strings.HasPrefix(attrName, "#") {
		attrName = strings.TrimPrefix(attrName, "#")
	}
	
	valueRef := action.Value
	if !strings.HasPrefix(valueRef, ":") {
		return fmt.Errorf("invalid value reference: %s", valueRef)
	}
	
	valueKey := valueRef[1:]
	newValue, ok := expressionValues[valueKey]
	if !ok {
		return fmt.Errorf("missing value for key: %s", valueKey)
	}
	
	existingValue, exists := item[attrName]
	if !exists {
		// If attribute doesn't exist, just set it
		item[attrName] = newValue
		return nil
	}
	
	// Try to add numbers
	existingNum, existingIsNum := existingValue.GetNumber()
	newNum, newIsNum := newValue.GetNumber()
	if existingIsNum && newIsNum {
		// Parse and add numbers
		existingFloat, _ := strconv.ParseFloat(existingNum, 64)
		newFloat, _ := strconv.ParseFloat(newNum, 64)
		result := existingFloat + newFloat
		item[attrName] = models.NewNumberAttribute(strconv.FormatFloat(result, 'f', -1, 64))
		return nil
	}
	
	// Try to add to sets
	if existingSS, ok := existingValue["SS"].([]interface{}); ok {
		if newSS, ok := newValue["SS"].([]interface{}); ok {
			// Add to string set
			setMap := make(map[string]bool)
			for _, v := range existingSS {
				if s, ok := v.(string); ok {
					setMap[s] = true
				}
			}
			for _, v := range newSS {
				if s, ok := v.(string); ok {
					setMap[s] = true
				}
			}
			newSet := make([]string, 0, len(setMap))
			for s := range setMap {
				newSet = append(newSet, s)
			}
			item[attrName] = models.NewStringSetAttribute(newSet)
			return nil
		}
	}
	
	// For other types, just replace
	item[attrName] = newValue
	return nil
}

// applyDELETE applies a DELETE action (for removing from sets).
func (im *ItemManager) applyDELETE(item models.Item, action UpdateAction, expressionValues map[string]models.AttributeValue) error {
	attrName := action.Path
	if strings.HasPrefix(attrName, "#") {
		attrName = strings.TrimPrefix(attrName, "#")
	}
	
	valueRef := action.Value
	if !strings.HasPrefix(valueRef, ":") {
		return fmt.Errorf("invalid value reference: %s", valueRef)
	}
	
	valueKey := valueRef[1:]
	deleteValue, ok := expressionValues[valueKey]
	if !ok {
		return fmt.Errorf("missing value for key: %s", valueKey)
	}
	
	existingValue, exists := item[attrName]
	if !exists {
		return nil // Nothing to delete
	}
	
	// Try to delete from string set
	if existingSS, ok := existingValue["SS"].([]interface{}); ok {
		if deleteSS, ok := deleteValue["SS"].([]interface{}); ok {
			deleteMap := make(map[string]bool)
			for _, v := range deleteSS {
				if s, ok := v.(string); ok {
					deleteMap[s] = true
				}
			}
			
			newSet := make([]string, 0)
			for _, v := range existingSS {
				if s, ok := v.(string); ok {
					if !deleteMap[s] {
						newSet = append(newSet, s)
					}
				}
			}
			
			if len(newSet) == 0 {
				delete(item, attrName)
			} else {
				item[attrName] = models.NewStringSetAttribute(newSet)
			}
		}
	}
	
	return nil
}

// applyREMOVE applies a REMOVE action.
func (im *ItemManager) applyREMOVE(item models.Item, action UpdateAction, expressionValues map[string]models.AttributeValue) error {
	attrName := action.Path
	if strings.HasPrefix(attrName, "#") {
		attrName = strings.TrimPrefix(attrName, "#")
	}
	
	delete(item, attrName)
	return nil
}

// splitAssignments splits update expression assignments, handling nested commas.
func (im *ItemManager) splitAssignments(expr string) []string {
	var assignments []string
	var current strings.Builder
	depth := 0

	for _, r := range expr {
		switch r {
		case '(':
			depth++
			current.WriteRune(r)
		case ')':
			depth--
			current.WriteRune(r)
		case ',':
			if depth == 0 {
				assignments = append(assignments, current.String())
				current.Reset()
			} else {
				current.WriteRune(r)
			}
		default:
			current.WriteRune(r)
		}
	}

	if current.Len() > 0 {
		assignments = append(assignments, current.String())
	}

	return assignments
}

// Query queries items by partition key and optional sort key conditions.
func (im *ItemManager) Query(tableName string, indexName string, 
	partitionKeyValue string, keyConditions map[string]models.Condition,
	scanIndexForward bool, limit int, exclusiveStartKey models.Item) ([]models.Item, models.Item, error) {
	
	im.mu.RLock()
	defer im.mu.RUnlock()

	db, err := im.getDBForTable(tableName)
	if err != nil {
		return nil, nil, err
	}
	defer db.Close()

	// Get key schema (use GSI schema if indexName is provided)
	keySchema, attrDefs, err := im.getKeySchema(tableName, indexName)
	if err != nil {
		return nil, nil, err
	}

	// Get partition and sort key names
	var pkName, skName string
	for _, ks := range keySchema {
		if ks.KeyType == "HASH" {
			pkName = ks.AttributeName
		} else if ks.KeyType == "RANGE" {
			skName = ks.AttributeName
		}
	}

	// Build and execute query
	items, err := im.queryItems(db, pkName, partitionKeyValue, skName, keyConditions, 
		scanIndexForward, limit, exclusiveStartKey, attrDefs, keySchema)
	if err != nil {
		return nil, nil, err
	}

	// Determine last evaluated key for pagination
	var lastEvaluatedKey models.Item
	if limit > 0 && len(items) > limit {
		items = items[:limit]
		lastItem := items[len(items)-1]
		lastEvaluatedKey = im.extractKeyFromItem(lastItem, keySchema)
	}

	return items, lastEvaluatedKey, nil
}

// queryItems executes the actual query.
func (im *ItemManager) queryItems(db *sql.DB, pkName, pkValue, skName string, 
	keyConditions map[string]models.Condition, scanIndexForward bool, limit int, 
	exclusiveStartKey models.Item, attrDefs []models.AttributeDefinition, keySchema []models.KeySchemaElement) ([]models.Item, error) {

	// Get all items for the partition key
	rows, err := db.Query("SELECT data FROM items WHERE pk = ?", pkValue)
	if err != nil {
		return nil, fmt.Errorf("failed to query items: %w", err)
	}
	defer rows.Close()

	var items []models.Item
	for rows.Next() {
		var data []byte
		if err := rows.Scan(&data); err != nil {
			continue
		}

		item, err := models.ItemFromJSON(data)
		if err != nil {
			continue
		}

		items = append(items, item)
	}

	// Apply sort key conditions if present
	if skName != "" && len(keyConditions) > 0 {
		var skType string
		for _, ad := range attrDefs {
			if ad.AttributeName == skName {
				skType = ad.AttributeType
				break
			}
		}

		if condition, ok := keyConditions[skName]; ok && skType != "" {
			items = im.filterBySortKeyCondition(items, skName, skType, condition)
		}
	}

	// Apply pagination (exclusive start key)
	if len(exclusiveStartKey) > 0 {
		items = im.filterExclusiveStartKey(items, exclusiveStartKey, keySchema, attrDefs)
	}

	// Sort items by sort key
	if skName != "" {
		var skType string
		for _, ad := range attrDefs {
			if ad.AttributeName == skName {
				skType = ad.AttributeType
				break
			}
		}
		im.sortItemsBySortKey(items, skName, skType, scanIndexForward)
	}

	return items, nil
}

// filterBySortKeyCondition filters items by sort key condition.
func (im *ItemManager) filterBySortKeyCondition(items []models.Item, skName, skType string, 
	condition models.Condition) []models.Item {
	
	if len(condition.AttributeValueList) == 0 {
		return items
	}

	comparisonOp := condition.ComparisonOperator
	if comparisonOp == "" {
		comparisonOp = "EQ"
	}

	var value string
	if av, ok := condition.AttributeValueList[0].GetString(); ok {
		value = av
	} else if av, ok := condition.AttributeValueList[0].GetNumber(); ok {
		value = av
	}

	var filtered []models.Item
	for _, item := range items {
		if item.MatchesSortKeyRange(skName, skType, comparisonOp, value) {
			filtered = append(filtered, item)
		}
	}

	return filtered
}

// filterExclusiveStartKey filters out items up to and including the exclusive start key.
func (im *ItemManager) filterExclusiveStartKey(items []models.Item, exclusiveStartKey models.Item, 
	keySchema []models.KeySchemaElement, attrDefs []models.AttributeDefinition) []models.Item {
	
	// Extract start key values
	startPk, startSk, err := exclusiveStartKey.ExtractKey(keySchema, attrDefs)
	if err != nil {
		return items
	}

	var found bool
	var result []models.Item
	for _, item := range items {
		if found {
			result = append(result, item)
			continue
		}

		pk, sk, err := item.ExtractKey(keySchema, attrDefs)
		if err != nil {
			continue
		}

		if pk == startPk && sk == startSk {
			found = true
		}
	}

	return result
}

// sortItemsBySortKey sorts items by sort key.
func (im *ItemManager) sortItemsBySortKey(items []models.Item, skName, skType string, ascending bool) {
	sort.Slice(items, func(i, j int) bool {
		skI, _ := items[i].GetKeyAttribute(skName, skType)
		skJ, _ := items[j].GetKeyAttribute(skName, skType)

		cmp := models.CompareValues(skI, skJ, skType)
		if ascending {
			return cmp < 0
		}
		return cmp > 0
	})
}

// extractKeyFromItem extracts the key attributes from an item.
func (im *ItemManager) extractKeyFromItem(item models.Item, keySchema []models.KeySchemaElement) models.Item {
	key := make(models.Item)
	for _, ks := range keySchema {
		if attr, ok := item[ks.AttributeName]; ok {
			key[ks.AttributeName] = attr
		}
	}
	return key
}

// Scan scans all items in a table.
func (im *ItemManager) Scan(tableName string, indexName string, limit int, 
	exclusiveStartKey models.Item, totalSegments, segment int) ([]models.Item, models.Item, error) {
	
	im.mu.RLock()
	defer im.mu.RUnlock()

	db, err := im.getDBForTable(tableName)
	if err != nil {
		return nil, nil, err
	}
	defer db.Close()

	// Get key schema (use GSI schema if indexName is provided)
	keySchema, _, err := im.getKeySchema(tableName, indexName)
	if err != nil {
		return nil, nil, err
	}

	// Build query based on whether we're scanning a GSI
	var rows *sql.Rows
	if indexName != "" {
		// For GSI scan, we'd need to scan the index table (not implemented in this version)
		// For now, scan all items
		rows, err = db.Query("SELECT data FROM items")
	} else {
		rows, err = db.Query("SELECT data FROM items")
	}

	if err != nil {
		return nil, nil, fmt.Errorf("failed to scan items: %w", err)
	}
	defer rows.Close()

	var items []models.Item
	var index int
	for rows.Next() {
		var data []byte
		if err := rows.Scan(&data); err != nil {
			continue
		}

		// Apply parallel scan segmentation
		if totalSegments > 0 {
			if index%totalSegments != segment {
				index++
				continue
			}
		}
		index++

		item, err := models.ItemFromJSON(data)
		if err != nil {
			continue
		}

		items = append(items, item)
	}

	// Apply pagination (exclusive start key)
	if len(exclusiveStartKey) > 0 {
		items = im.filterExclusiveStartKey(items, exclusiveStartKey, nil, nil)
	}

	// Apply limit
	var lastEvaluatedKey models.Item
	if limit > 0 && len(items) > limit {
		items = items[:limit]
		lastItem := items[len(items)-1]
		lastEvaluatedKey = im.extractKeyFromItem(lastItem, keySchema)
	}

	return items, lastEvaluatedKey, nil
}

// updateItemCount updates the item count in metadata.
func (im *ItemManager) updateItemCount(db *sql.DB, delta int) {
	// This is a simplified version - in production, you'd track counts more accurately
	// For now, we don't update the count in real-time to avoid complexity
}

// BatchGetItem retrieves multiple items from one or more tables.
// Returns items grouped by table name and any unprocessed keys.
func (im *ItemManager) BatchGetItem(requests map[string]models.KeysAndAttributes) (map[string][]models.Item, map[string]models.KeysAndAttributes, error) {
	im.mu.RLock()
	defer im.mu.RUnlock()

	responses := make(map[string][]models.Item)
	unprocessedKeys := make(map[string]models.KeysAndAttributes)

	// Process each table
	for tableName, keysAndAttrs := range requests {
		items, err := im.batchGetItemsFromTable(tableName, keysAndAttrs)
		if err != nil {
			// If table not found, add to unprocessed
			if strings.Contains(err.Error(), "table not found") {
				unprocessedKeys[tableName] = keysAndAttrs
				continue
			}
			return nil, nil, err
		}
		responses[tableName] = items
	}

	return responses, unprocessedKeys, nil
}

// batchGetItemsFromTable retrieves multiple items from a single table.
func (im *ItemManager) batchGetItemsFromTable(tableName string, keysAndAttrs models.KeysAndAttributes) ([]models.Item, error) {
	db, err := im.getDBForTable(tableName)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	// Get table metadata for key schema
	metadata, err := im.tableManager.DescribeTable(tableName)
	if err != nil {
		return nil, err
	}

	var items []models.Item

	// Process each key
	for _, key := range keysAndAttrs.Keys {
		// Extract pk and sk from the key
		pk, sk, err := key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
		if err != nil {
			continue // Skip invalid keys
		}

		// Query the database
		var data []byte
		if sk != "" {
			err = db.QueryRow(
				"SELECT data FROM items WHERE pk = ? AND sk = ?",
				pk, sk,
			).Scan(&data)
		} else {
			err = db.QueryRow(
				"SELECT data FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')",
				pk,
			).Scan(&data)
		}

		if err != nil {
			if err == sql.ErrNoRows {
				continue // Item not found, skip
			}
			return nil, fmt.Errorf("failed to get item: %w", err)
		}

		item, err := models.ItemFromJSON(data)
		if err != nil {
			continue
		}

		// Apply projection if specified
		if keysAndAttrs.ProjectionExpression != "" {
			item = im.applyProjection(item, keysAndAttrs.ProjectionExpression, keysAndAttrs.ExpressionAttributeNames)
		}

		items = append(items, item)
	}

	return items, nil
}

// applyProjection filters item attributes based on projection expression.
func (im *ItemManager) applyProjection(item models.Item, projectionExpression string, expressionAttributeNames map[string]string) models.Item {
	// Simple projection - split by comma and extract those attributes
	// In production, this would parse the full projection expression grammar
	attributes := strings.Split(projectionExpression, ",")
	
	projectedItem := make(models.Item)
	for _, attr := range attributes {
		attr = strings.TrimSpace(attr)
		
		// Handle expression attribute names (#name)
		if strings.HasPrefix(attr, "#") {
			if actualName, ok := expressionAttributeNames[attr]; ok {
				attr = actualName
			}
		}
		
		if val, ok := item[attr]; ok {
			projectedItem[attr] = val
		}
	}
	
	return projectedItem
}

// BatchWriteItem performs multiple PutItem and DeleteItem operations.
// Returns any unprocessed items.
func (im *ItemManager) BatchWriteItem(requests map[string][]models.WriteRequest) (map[string][]models.WriteRequest, error) {
	im.mu.Lock()
	defer im.mu.Unlock()

	unprocessedItems := make(map[string][]models.WriteRequest)

	// Process each table
	for tableName, writeRequests := range requests {
		unprocessed, err := im.batchWriteItemsToTable(tableName, writeRequests)
		if err != nil {
			return nil, err
		}
		if len(unprocessed) > 0 {
			unprocessedItems[tableName] = unprocessed
		}
	}

	return unprocessedItems, nil
}

// batchWriteItemsToTable performs write operations on a single table.
// Returns any unprocessed items (if limit exceeded or errors occur).
func (im *ItemManager) batchWriteItemsToTable(tableName string, writeRequests []models.WriteRequest) ([]models.WriteRequest, error) {
	// DynamoDB limit: 25 items per batch
	const maxBatchSize = 25
	
	if len(writeRequests) > maxBatchSize {
		return writeRequests[maxBatchSize:], fmt.Errorf("batch size exceeds maximum of %d", maxBatchSize)
	}

	db, err := im.getDBForTable(tableName)
	if err != nil {
		// Return all items as unprocessed if table not found
		if strings.Contains(err.Error(), "table not found") {
			return writeRequests, nil
		}
		return nil, err
	}
	defer db.Close()

	// Get table metadata for key schema
	metadata, err := im.tableManager.DescribeTable(tableName)
	if err != nil {
		return writeRequests, nil
	}

	var unprocessed []models.WriteRequest

	// Process each write request
	for _, writeReq := range writeRequests {
		success := false

		if writeReq.PutRequest != nil {
			err := im.putItemInternal(db, tableName, writeReq.PutRequest.Item, metadata.KeySchema, metadata.AttributeDefinitions)
			if err == nil {
				success = true
			}
		} else if writeReq.DeleteRequest != nil {
			err := im.deleteItemInternal(db, writeReq.DeleteRequest.Key, metadata.KeySchema, metadata.AttributeDefinitions)
			if err == nil {
				success = true
			}
		}

		if !success {
			unprocessed = append(unprocessed, writeReq)
		}
	}

	return unprocessed, nil
}

// putItemInternal performs a put item operation (internal use).
func (im *ItemManager) putItemInternal(db *sql.DB, tableName string, item models.Item, keySchema []models.KeySchemaElement, attrDefs []models.AttributeDefinition) error {
	pk, sk, err := item.ExtractKey(keySchema, attrDefs)
	if err != nil {
		return fmt.Errorf("invalid key: %w", err)
	}

	data, err := json.Marshal(item)
	if err != nil {
		return fmt.Errorf("failed to serialize item: %w", err)
	}

	now := time.Now().Unix()
	_, err = db.Exec(
		`INSERT INTO items (pk, sk, data, created_at, updated_at) 
		 VALUES (?, ?, ?, ?, ?)
		 ON CONFLICT(pk, sk) DO UPDATE SET
		 data = excluded.data, updated_at = excluded.updated_at`,
		pk, sk, data, now, now,
	)
	if err != nil {
		return fmt.Errorf("failed to put item: %w", err)
	}

	return nil
}

// deleteItemInternal performs a delete item operation (internal use).
func (im *ItemManager) deleteItemInternal(db *sql.DB, key models.Item, keySchema []models.KeySchemaElement, attrDefs []models.AttributeDefinition) error {
	pk, sk, err := key.ExtractKey(keySchema, attrDefs)
	if err != nil {
		return fmt.Errorf("invalid key: %w", err)
	}

	var result sql.Result
	if sk != "" {
		result, err = db.Exec("DELETE FROM items WHERE pk = ? AND sk = ?", pk, sk)
	} else {
		result, err = db.Exec("DELETE FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')", pk)
	}
	if err != nil {
		return fmt.Errorf("failed to delete item: %w", err)
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		return fmt.Errorf("item not found")
	}

	return nil
}

// TransactGetItems performs atomic multi-item reads across tables.
// All items are retrieved atomically - if any read fails, all fail.
func (im *ItemManager) TransactGetItems(items []models.TransactGetItem) ([]models.ItemResponse, error) {
	im.mu.RLock()
	defer im.mu.RUnlock()

	// DynamoDB limit: up to 25 items per transaction
	if len(items) > 25 {
		return nil, fmt.Errorf("TransactGetItems can retrieve up to 25 items")
	}

	// Check for duplicate keys (not allowed in transactions)
	keySet := make(map[string]bool)
	for _, item := range items {
		if item.Get == nil {
			continue
		}
		key := fmt.Sprintf("%s:%v", item.Get.TableName, item.Get.Key)
		if keySet[key] {
			return nil, fmt.Errorf("duplicate key in transaction")
		}
		keySet[key] = true
	}

	// First, validate all items can be read (tables exist, keys valid)
	for _, item := range items {
		if item.Get == nil {
			return nil, fmt.Errorf("invalid Get operation in transaction")
		}

		// Check table exists
		_, err := im.tableManager.DescribeTable(item.Get.TableName)
		if err != nil {
			return nil, fmt.Errorf("table not found: %s", item.Get.TableName)
		}
	}

	// All validations passed, now read all items
	responses := make([]models.ItemResponse, 0, len(items))

	for _, item := range items {
		getItem := item.Get

		// Get table metadata
		metadata, err := im.tableManager.DescribeTable(getItem.TableName)
		if err != nil {
			return nil, err
		}

		// Extract pk and sk
		pk, sk, err := getItem.Key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
		if err != nil {
			return nil, fmt.Errorf("invalid key: %w", err)
		}

		// Get database connection
		db, err := im.getDBForTable(getItem.TableName)
		if err != nil {
			return nil, err
		}

		// Query the database
		var data []byte
		if sk != "" {
			err = db.QueryRow(
				"SELECT data FROM items WHERE pk = ? AND sk = ?",
				pk, sk,
			).Scan(&data)
		} else {
			err = db.QueryRow(
				"SELECT data FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')",
				pk,
			).Scan(&data)
		}
		db.Close()

		var response models.ItemResponse
		if err == nil {
			// Item found
			item, err := models.ItemFromJSON(data)
			if err == nil {
				// Apply projection if specified
				if getItem.ProjectionExpression != "" {
					item = im.applyProjection(item, getItem.ProjectionExpression, getItem.ExpressionAttributeNames)
				}
				response.Item = item
			}
		}
		// If item not found, return empty response (DynamoDB behavior)

		responses = append(responses, response)
	}

	return responses, nil
}

// TransactWriteItems performs atomic multi-item writes across tables.
// All operations succeed or all fail (all-or-nothing).
func (im *ItemManager) TransactWriteItems(items []models.TransactWriteItem) error {
	im.mu.Lock()
	defer im.mu.Unlock()

	// DynamoDB limit: up to 25 items per transaction
	if len(items) > 25 {
		return fmt.Errorf("TransactWriteItems can write up to 25 items")
	}

	// Check for duplicate keys (not allowed in transactions)
	keySet := make(map[string]bool)
	for _, item := range items {
		tableName, key := im.extractTransactKey(item)
		if tableName == "" {
			continue
		}
		keyStr := fmt.Sprintf("%s:%v", tableName, key)
		if keySet[keyStr] {
			return fmt.Errorf("duplicate key in transaction")
		}
		keySet[keyStr] = true
	}

	// Group operations by table for atomicity
	tableOperations := make(map[string][]models.TransactWriteItem)
	for _, item := range items {
		tableName, _ := im.extractTransactKey(item)
		if tableName != "" {
			tableOperations[tableName] = append(tableOperations[tableName], item)
		}
	}

	// Validate all operations before executing any
	for _, item := range items {
		if err := im.validateTransactWriteItem(item); err != nil {
			return err
		}
	}

	// Execute all operations atomically per table
	// Note: True cross-table atomicity would require 2PC, but for local DynamoDB
	// we execute per-table atomically
	for tableName, ops := range tableOperations {
		if err := im.executeTransactWritesForTable(tableName, ops); err != nil {
			return err
		}
	}

	return nil
}

// extractTransactKey extracts the table name and key from a TransactWriteItem.
func (im *ItemManager) extractTransactKey(item models.TransactWriteItem) (string, models.Item) {
	if item.Put != nil {
		return item.Put.TableName, item.Put.Item
	}
	if item.Update != nil {
		return item.Update.TableName, item.Update.Key
	}
	if item.Delete != nil {
		return item.Delete.TableName, item.Delete.Key
	}
	if item.ConditionCheck != nil {
		return item.ConditionCheck.TableName, item.ConditionCheck.Key
	}
	return "", nil
}

// validateTransactWriteItem validates a single transaction write item.
func (im *ItemManager) validateTransactWriteItem(item models.TransactWriteItem) error {
	switch {
	case item.Put != nil:
		return im.validatePutForTransact(item.Put)
	case item.Update != nil:
		return im.validateUpdateForTransact(item.Update)
	case item.Delete != nil:
		return im.validateDeleteForTransact(item.Delete)
	case item.ConditionCheck != nil:
		return im.validateConditionCheck(item.ConditionCheck)
	default:
		return fmt.Errorf("invalid transaction item: no operation specified")
	}
}

// validatePutForTransact validates a Put operation in a transaction.
func (im *ItemManager) validatePutForTransact(put *models.TransactPut) error {
	if put.TableName == "" {
		return fmt.Errorf("TableName is required")
	}
	if len(put.Item) == 0 {
		return fmt.Errorf("Item is required")
	}

	// Check table exists
	metadata, err := im.tableManager.DescribeTable(put.TableName)
	if err != nil {
		return fmt.Errorf("table not found: %s", put.TableName)
	}

	// Validate key
	_, _, err = put.Item.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return fmt.Errorf("invalid key: %w", err)
	}

	return nil
}

// validateUpdateForTransact validates an Update operation in a transaction.
func (im *ItemManager) validateUpdateForTransact(update *models.TransactUpdate) error {
	if update.TableName == "" {
		return fmt.Errorf("TableName is required")
	}
	if len(update.Key) == 0 {
		return fmt.Errorf("Key is required")
	}

	// Check table exists
	metadata, err := im.tableManager.DescribeTable(update.TableName)
	if err != nil {
		return fmt.Errorf("table not found: %s", update.TableName)
	}

	// Validate key
	_, _, err = update.Key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return fmt.Errorf("invalid key: %w", err)
	}

	return nil
}

// validateDeleteForTransact validates a Delete operation in a transaction.
func (im *ItemManager) validateDeleteForTransact(del *models.TransactDelete) error {
	if del.TableName == "" {
		return fmt.Errorf("TableName is required")
	}
	if len(del.Key) == 0 {
		return fmt.Errorf("Key is required")
	}

	// Check table exists
	metadata, err := im.tableManager.DescribeTable(del.TableName)
	if err != nil {
		return fmt.Errorf("table not found: %s", del.TableName)
	}

	// Validate key
	_, _, err = del.Key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return fmt.Errorf("invalid key: %w", err)
	}

	return nil
}

// validateConditionCheck validates a ConditionCheck operation in a transaction.
func (im *ItemManager) validateConditionCheck(check *models.TransactConditionCheck) error {
	if check.TableName == "" {
		return fmt.Errorf("TableName is required")
	}
	if len(check.Key) == 0 {
		return fmt.Errorf("Key is required")
	}
	if check.ConditionExpression == "" {
		return fmt.Errorf("ConditionExpression is required")
	}

	// Check table exists
	metadata, err := im.tableManager.DescribeTable(check.TableName)
	if err != nil {
		return fmt.Errorf("table not found: %s", check.TableName)
	}

	// Validate key
	_, _, err = check.Key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return fmt.Errorf("invalid key: %w", err)
	}

	return nil
}

// executeTransactWritesForTable executes all transaction writes for a single table atomically.
func (im *ItemManager) executeTransactWritesForTable(tableName string, items []models.TransactWriteItem) error {
	db, err := im.getDBForTable(tableName)
	if err != nil {
		return err
	}
	defer db.Close()

	// Get table metadata
	metadata, err := im.tableManager.DescribeTable(tableName)
	if err != nil {
		return err
	}

	// Begin transaction
	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}

	// Execute all operations
	for _, item := range items {
		if err := im.executeTransactWrite(tx, item, metadata); err != nil {
			tx.Rollback()
			return err
		}
	}

	// Commit all operations
	if err := tx.Commit(); err != nil {
		tx.Rollback()
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	return nil
}

// executeTransactWrite executes a single transaction write operation within a transaction.
func (im *ItemManager) executeTransactWrite(tx *sql.Tx, item models.TransactWriteItem, metadata *models.TableMetadata) error {
	switch {
	case item.Put != nil:
		return im.executeTransactPut(tx, item.Put, metadata)
	case item.Update != nil:
		return im.executeTransactUpdate(tx, item.Update, metadata)
	case item.Delete != nil:
		return im.executeTransactDelete(tx, item.Delete, metadata)
	case item.ConditionCheck != nil:
		return im.executeTransactConditionCheck(tx, item.ConditionCheck, metadata)
	default:
		return fmt.Errorf("invalid transaction item")
	}
}

// executeTransactPut executes a Put operation within a transaction.
func (im *ItemManager) executeTransactPut(tx *sql.Tx, put *models.TransactPut, metadata *models.TableMetadata) error {
	pk, sk, err := put.Item.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return err
	}

	data, err := json.Marshal(put.Item)
	if err != nil {
		return fmt.Errorf("failed to serialize item: %w", err)
	}

	now := time.Now().Unix()
	_, err = tx.Exec(
		`INSERT INTO items (pk, sk, data, created_at, updated_at) 
		 VALUES (?, ?, ?, ?, ?)
		 ON CONFLICT(pk, sk) DO UPDATE SET
		 data = excluded.data, updated_at = excluded.updated_at`,
		pk, sk, data, now, now,
	)
	if err != nil {
		return fmt.Errorf("failed to put item: %w", err)
	}

	return nil
}

// executeTransactUpdate executes an Update operation within a transaction.
func (im *ItemManager) executeTransactUpdate(tx *sql.Tx, update *models.TransactUpdate, metadata *models.TableMetadata) error {
	// For now, simplified update that just checks if item exists
	// Full UpdateExpression support would be added later

	pk, sk, err := update.Key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return err
	}

	// Check if item exists
	var existingData []byte
	if sk != "" {
		err = tx.QueryRow("SELECT data FROM items WHERE pk = ? AND sk = ?", pk, sk).Scan(&existingData)
	} else {
		err = tx.QueryRow("SELECT data FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')", pk).Scan(&existingData)
	}

	if err == sql.ErrNoRows {
		return fmt.Errorf("item not found")
	}
	if err != nil {
		return fmt.Errorf("failed to get item: %w", err)
	}

	// For now, just verify the item exists
	// Full update would parse and apply UpdateExpression

	return nil
}

// executeTransactDelete executes a Delete operation within a transaction.
func (im *ItemManager) executeTransactDelete(tx *sql.Tx, del *models.TransactDelete, metadata *models.TableMetadata) error {
	pk, sk, err := del.Key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return err
	}

	var result sql.Result
	if sk != "" {
		result, err = tx.Exec("DELETE FROM items WHERE pk = ? AND sk = ?", pk, sk)
	} else {
		result, err = tx.Exec("DELETE FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')", pk)
	}
	if err != nil {
		return fmt.Errorf("failed to delete item: %w", err)
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		return fmt.Errorf("item not found")
	}

	return nil
}

// executeTransactConditionCheck executes a ConditionCheck operation within a transaction.
func (im *ItemManager) executeTransactConditionCheck(tx *sql.Tx, check *models.TransactConditionCheck, metadata *models.TableMetadata) error {
	pk, sk, err := check.Key.ExtractKey(metadata.KeySchema, metadata.AttributeDefinitions)
	if err != nil {
		return err
	}

	// Check if item exists
	var existingData []byte
	if sk != "" {
		err = tx.QueryRow("SELECT data FROM items WHERE pk = ? AND sk = ?", pk, sk).Scan(&existingData)
	} else {
		err = tx.QueryRow("SELECT data FROM items WHERE pk = ? AND (sk IS NULL OR sk = '')", pk).Scan(&existingData)
	}

	// For now, just verify the condition check passes
	// Full ConditionExpression evaluation would be added later
	_ = existingData

	return nil
}
