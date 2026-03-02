// Package storage provides SQLite-backed storage for DynamoDB items.
package storage

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"sort"
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

// applyUpdateExpression applies a simple SET update expression to an item.
func (im *ItemManager) applyUpdateExpression(item models.Item, expression string, 
	expressionValues map[string]models.AttributeValue) (models.Item, error) {
	
	// Simple parser for SET expressions
	// Format: SET attr1 = :val1, attr2 = :val2, ...
	upperExpr := strings.ToUpper(expression)
	if !strings.HasPrefix(upperExpr, "SET ") {
		return nil, fmt.Errorf("unsupported update expression: %s", expression)
	}

	// Remove SET prefix
	expr := expression[4:]

	// Split by commas
	assignments := im.splitAssignments(expr)

	for _, assignment := range assignments {
		assignment = strings.TrimSpace(assignment)
		parts := strings.SplitN(assignment, "=", 2)
		if len(parts) != 2 {
			return nil, fmt.Errorf("invalid assignment: %s", assignment)
		}

		attrName := strings.TrimSpace(parts[0])
		valueRef := strings.TrimSpace(parts[1])

		// Check for expression attribute names (:#name -> actual name)
		if strings.HasPrefix(attrName, "#") {
			// For simplicity, keep the reference name
			attrName = strings.TrimPrefix(attrName, "#")
		}

		// Look up value in expression values
		if strings.HasPrefix(valueRef, ":") {
			valueKey := valueRef[1:] // Remove leading :
			if value, ok := expressionValues[valueKey]; ok {
				item[attrName] = value
			} else {
				return nil, fmt.Errorf("missing value for key: %s", valueKey)
			}
		}
	}

	return item, nil
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
