// Package storage provides PartiQL support for DynamoDB operations.
package storage

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/e6qu/dyscount/internal/models"
)

// PartiQLEngine handles PartiQL statement execution.
type PartiQLEngine struct {
	tableManager *TableManager
	itemManager  *ItemManager
}

// NewPartiQLEngine creates a new PartiQL engine.
func NewPartiQLEngine(tm *TableManager, im *ItemManager) *PartiQLEngine {
	return &PartiQLEngine{
		tableManager: tm,
		itemManager:  im,
	}
}

// ExecuteStatement executes a single PartiQL statement.
func (pe *PartiQLEngine) ExecuteStatement(req *models.ExecuteStatementRequest) (*models.ExecuteStatementResponse, error) {
	statement := strings.TrimSpace(req.Statement)
	
	// Parse the statement type
	upperStmt := strings.ToUpper(statement)
	
	switch {
	case strings.HasPrefix(upperStmt, "SELECT"):
		return pe.executeSelect(statement, req)
	case strings.HasPrefix(upperStmt, "INSERT"):
		return pe.executeInsert(statement, req)
	case strings.HasPrefix(upperStmt, "UPDATE"):
		return pe.executeUpdate(statement, req)
	case strings.HasPrefix(upperStmt, "DELETE"):
		return pe.executeDelete(statement, req)
	default:
		return nil, fmt.Errorf("unsupported PartiQL statement type")
	}
}

// BatchExecuteStatement executes multiple PartiQL statements.
func (pe *PartiQLEngine) BatchExecuteStatement(req *models.BatchExecuteStatementRequest) (*models.BatchExecuteStatementResponse, error) {
	var responses []models.BatchStatementResponse
	
	for _, stmt := range req.Statements {
		execReq := &models.ExecuteStatementRequest{
			Statement:      stmt.Statement,
			Parameters:     stmt.Parameters,
			ConsistentRead: stmt.ConsistentRead,
		}
		
		resp, err := pe.ExecuteStatement(execReq)
		if err != nil {
			responses = append(responses, models.BatchStatementResponse{
				Error: &models.ErrorResponse{
					Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
					Message: err.Error(),
				},
			})
			continue
		}
		
		// For SELECT, return the first item if any
		if len(resp.Items) > 0 {
			responses = append(responses, models.BatchStatementResponse{
				Item: resp.Items[0],
			})
		} else {
			responses = append(responses, models.BatchStatementResponse{})
		}
	}
	
	return &models.BatchExecuteStatementResponse{
		Responses: responses,
	}, nil
}

// executeSelect handles SELECT statements.
func (pe *PartiQLEngine) executeSelect(statement string, req *models.ExecuteStatementRequest) (*models.ExecuteStatementResponse, error) {
	// Simple parsing: SELECT * FROM "TableName" WHERE ...
	tableName, keyConditions, err := pe.parseSelectStatement(statement)
	if err != nil {
		return nil, err
	}
	
	// If no key conditions, perform Scan
	if len(keyConditions) == 0 {
		items, lastKey, err := pe.itemManager.Scan(tableName, "", req.Limit, nil, 0, 0)
		if err != nil {
			return nil, err
		}
		
		resp := &models.ExecuteStatementResponse{
			Items: items,
		}
		if lastKey != nil {
			resp.LastEvaluatedKey = lastKey
		}
		return resp, nil
	}
	
	// Perform Query with key conditions
	// For simplicity, we assume single partition key condition
	pkValue, ok := keyConditions["pk"]
	if !ok {
		return nil, fmt.Errorf("partition key condition required")
	}
	
	// Convert string conditions to Condition objects
	conditions := make(map[string]models.Condition)
	for k, v := range keyConditions {
		conditions[k] = models.Condition{
			ComparisonOperator: "EQ",
			AttributeValueList: []models.AttributeValue{models.NewStringAttribute(v)},
		}
	}
	
	items, lastKey, err := pe.itemManager.Query(tableName, "", pkValue, conditions, true, req.Limit, nil)
	if err != nil {
		return nil, err
	}
	
	resp := &models.ExecuteStatementResponse{
		Items: items,
	}
	if lastKey != nil {
		resp.LastEvaluatedKey = lastKey
	}
	return resp, nil
}

// executeInsert handles INSERT statements.
func (pe *PartiQLEngine) executeInsert(statement string, req *models.ExecuteStatementRequest) (*models.ExecuteStatementResponse, error) {
	// Parse: INSERT INTO "TableName" VALUE {'pk': 'value', ...}
	tableName, item, err := pe.parseInsertStatement(statement)
	if err != nil {
		return nil, err
	}
	
	_, err = pe.itemManager.PutItem(tableName, item, false)
	if err != nil {
		return nil, err
	}
	
	return &models.ExecuteStatementResponse{}, nil
}

// executeUpdate handles UPDATE statements.
func (pe *PartiQLEngine) executeUpdate(statement string, req *models.ExecuteStatementRequest) (*models.ExecuteStatementResponse, error) {
	// Parse: UPDATE "TableName" SET attr = value WHERE pk = value
	tableName, key, updates, err := pe.parseUpdateStatement(statement)
	if err != nil {
		return nil, err
	}
	
	// Build update expression
	var setParts []string
	for attr, value := range updates {
		setParts = append(setParts, fmt.Sprintf("%s = %s", attr, value))
	}
	updateExpr := "SET " + strings.Join(setParts, ", ")
	
	_, _, err = pe.itemManager.UpdateItem(tableName, key, updateExpr, nil, false)
	if err != nil {
		return nil, err
	}
	
	return &models.ExecuteStatementResponse{}, nil
}

// executeDelete handles DELETE statements.
func (pe *PartiQLEngine) executeDelete(statement string, req *models.ExecuteStatementRequest) (*models.ExecuteStatementResponse, error) {
	// Parse: DELETE FROM "TableName" WHERE pk = value
	tableName, key, err := pe.parseDeleteStatement(statement)
	if err != nil {
		return nil, err
	}
	
	_, err = pe.itemManager.DeleteItem(tableName, key, false)
	if err != nil {
		return nil, err
	}
	
	return &models.ExecuteStatementResponse{}, nil
}

// parseSelectStatement parses a SELECT statement and extracts table name and conditions.
func (pe *PartiQLEngine) parseSelectStatement(statement string) (string, map[string]string, error) {
	// Simple regex-based parsing
	// SELECT * FROM "TableName" WHERE pk = 'value' AND sk = 'value'
	
	re := regexp.MustCompile(`(?i)SELECT\s+\*\s+FROM\s+["']?(\w+)["']?\s*(?:WHERE\s+(.+))?`)
	matches := re.FindStringSubmatch(statement)
	
	if len(matches) < 2 {
		return "", nil, fmt.Errorf("invalid SELECT statement")
	}
	
	tableName := matches[1]
	conditions := make(map[string]string)
	
	if len(matches) >= 3 && matches[2] != "" {
		whereClause := matches[2]
		// Parse simple conditions: pk = 'value' or pk = ?
		condRe := regexp.MustCompile(`(\w+)\s*=\s*['"]?([^'"\s]+)['"]?`)
		condMatches := condRe.FindAllStringSubmatch(whereClause, -1)
		for _, m := range condMatches {
			if len(m) >= 3 {
				conditions[m[1]] = m[2]
			}
		}
	}
	
	return tableName, conditions, nil
}

// parseInsertStatement parses an INSERT statement.
func (pe *PartiQLEngine) parseInsertStatement(statement string) (string, models.Item, error) {
	// INSERT INTO "TableName" VALUE {'pk': 'value', 'sk': 'value'}
	re := regexp.MustCompile(`(?i)INSERT\s+INTO\s+["']?(\w+)["']?\s+VALUE\s+(.+)`)
	matches := re.FindStringSubmatch(statement)
	
	if len(matches) < 3 {
		return "", nil, fmt.Errorf("invalid INSERT statement")
	}
	
	tableName := matches[1]
	valueJSON := matches[2]
	
	// Parse the value as JSON
	var item models.Item
	if err := json.Unmarshal([]byte(valueJSON), &item); err != nil {
		return "", nil, fmt.Errorf("failed to parse item: %w", err)
	}
	
	return tableName, item, nil
}

// parseUpdateStatement parses an UPDATE statement.
func (pe *PartiQLEngine) parseUpdateStatement(statement string) (string, models.Item, map[string]string, error) {
	// UPDATE "TableName" SET attr = value WHERE pk = value
	re := regexp.MustCompile(`(?i)UPDATE\s+["']?(\w+)["']?\s+SET\s+(.+)\s+WHERE\s+(.+)`)
	matches := re.FindStringSubmatch(statement)
	
	if len(matches) < 4 {
		return "", nil, nil, fmt.Errorf("invalid UPDATE statement")
	}
	
	tableName := matches[1]
	
	// Parse SET clause
	updates := make(map[string]string)
	setRe := regexp.MustCompile(`(\w+)\s*=\s*['"]?([^'",]+)['"]?`)
	setMatches := setRe.FindAllStringSubmatch(matches[2], -1)
	for _, m := range setMatches {
		if len(m) >= 3 {
			updates[m[1]] = m[2]
		}
	}
	
	// Parse WHERE clause for key
	key := make(models.Item)
	whereRe := regexp.MustCompile(`(\w+)\s*=\s*['"]?([^'"\s]+)['"]?`)
	whereMatches := whereRe.FindAllStringSubmatch(matches[3], -1)
	for _, m := range whereMatches {
		if len(m) >= 3 {
			key[m[1]] = models.NewStringAttribute(m[2])
		}
	}
	
	return tableName, key, updates, nil
}

// parseDeleteStatement parses a DELETE statement.
func (pe *PartiQLEngine) parseDeleteStatement(statement string) (string, models.Item, error) {
	// DELETE FROM "TableName" WHERE pk = value
	re := regexp.MustCompile(`(?i)DELETE\s+FROM\s+["']?(\w+)["']?\s+WHERE\s+(.+)`)
	matches := re.FindStringSubmatch(statement)
	
	if len(matches) < 3 {
		return "", nil, fmt.Errorf("invalid DELETE statement")
	}
	
	tableName := matches[1]
	
	// Parse WHERE clause for key
	key := make(models.Item)
	whereRe := regexp.MustCompile(`(\w+)\s*=\s*['"]?([^'"\s]+)['"]?`)
	whereMatches := whereRe.FindAllStringSubmatch(matches[2], -1)
	for _, m := range whereMatches {
		if len(m) >= 3 {
			key[m[1]] = models.NewStringAttribute(m[2])
		}
	}
	
	return tableName, key, nil
}
