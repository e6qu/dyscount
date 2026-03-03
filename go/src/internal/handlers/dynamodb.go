// Package handlers provides HTTP handlers for DynamoDB API operations.
package handlers

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"

	"github.com/e6qu/dyscount/internal/models"
	"github.com/e6qu/dyscount/internal/storage"
)

// DynamoDBHandler handles DynamoDB API requests.
type DynamoDBHandler struct {
	tableManager *storage.TableManager
	itemManager  *storage.ItemManager
}

// NewDynamoDBHandler creates a new DynamoDBHandler.
func NewDynamoDBHandler(tm *storage.TableManager, im *storage.ItemManager) *DynamoDBHandler {
	return &DynamoDBHandler{
		tableManager: tm,
		itemManager:  im,
	}
}

// Handle handles DynamoDB API requests.
// @Summary DynamoDB API endpoint
// @Description Main DynamoDB-compatible endpoint
// @Accept json
// @Produce json
// @Param request body models.DynamoDBRequest true "DynamoDB operation request"
// @Success 200 {object} models.DynamoDBResponse
// @Failure 400 {object} models.ErrorResponse
// @Failure 500 {object} models.ErrorResponse
// @Router / [post]
func (h *DynamoDBHandler) Handle(c *gin.Context) {
	// Get X-Amz-Target header
	amzTarget := c.GetHeader("X-Amz-Target")
	if amzTarget == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Missing X-Amz-Target header",
		})
		return
	}

	// Extract operation name
	operation := amzTarget
	if idx := strings.LastIndex(amzTarget, "."); idx != -1 {
		operation = amzTarget[idx+1:]
	}

	// Parse request body
	var req models.DynamoDBRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	// Route to appropriate handler
	switch operation {
	case "CreateTable":
		h.handleCreateTable(c, &req)
	case "UpdateTable":
		h.handleUpdateTable(c, &req)
	case "DeleteTable":
		h.handleDeleteTable(c, &req)
	case "ListTables":
		h.handleListTables(c)
	case "DescribeTable":
		h.handleDescribeTable(c, &req)
	case "TagResource":
		h.handleTagResource(c, &req)
	case "UntagResource":
		h.handleUntagResource(c, &req)
	case "ListTagsOfResource":
		h.handleListTagsOfResource(c, &req)
	case "DescribeEndpoints":
		h.handleDescribeEndpoints(c)
	// Data plane operations
	case "GetItem":
		h.handleGetItem(c, &req)
	case "PutItem":
		h.handlePutItem(c, &req)
	case "UpdateItem":
		h.handleUpdateItem(c, &req)
	case "DeleteItem":
		h.handleDeleteItem(c, &req)
	case "Query":
		h.handleQuery(c, &req)
	case "Scan":
		h.handleScan(c, &req)
	case "BatchGetItem":
		h.handleBatchGetItem(c)
	case "BatchWriteItem":
		h.handleBatchWriteItem(c)
	case "TransactGetItems":
		h.handleTransactGetItems(c)
	case "TransactWriteItems":
		h.handleTransactWriteItems(c)
	case "UpdateTimeToLive":
		h.handleUpdateTimeToLive(c)
	case "DescribeTimeToLive":
		h.handleDescribeTimeToLive(c)
	case "CreateBackup":
		h.handleCreateBackup(c)
	case "DeleteBackup":
		h.handleDeleteBackup(c)
	case "ListBackups":
		h.handleListBackups(c)
	case "RestoreTableFromBackup":
		h.handleRestoreTableFromBackup(c)
	default:
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Unknown operation: %s", operation),
		})
	}
}

// handleGetItem handles GetItem requests.
func (h *DynamoDBHandler) handleGetItem(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	if len(req.Key) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Key cannot be empty",
		})
		return
	}

	item, err := h.itemManager.GetItem(req.TableName, req.Key, req.ConsistentRead)
	if err != nil {
		if strings.Contains(err.Error(), "table not found") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		Item: item,
	})
}

// handlePutItem handles PutItem requests.
func (h *DynamoDBHandler) handlePutItem(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	if len(req.Item) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Item cannot be empty",
		})
		return
	}

	returnOld := req.ReturnValues == "ALL_OLD"
	oldItem, err := h.itemManager.PutItem(req.TableName, req.Item, returnOld)
	if err != nil {
		if strings.Contains(err.Error(), "table not found") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.DynamoDBResponse{}
	if req.ReturnValues == "ALL_OLD" {
		resp.Attributes = oldItem
	}

	c.JSON(http.StatusOK, resp)
}

// handleUpdateItem handles UpdateItem requests.
func (h *DynamoDBHandler) handleUpdateItem(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	if len(req.Key) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Key cannot be empty",
		})
		return
	}

	if req.UpdateExpression == "" && len(req.AttributeUpdates) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "UpdateExpression or AttributeUpdates is required",
		})
		return
	}

	returnOld := req.ReturnValues == "ALL_OLD"
	newItem, oldItem, err := h.itemManager.UpdateItem(
		req.TableName, 
		req.Key, 
		req.UpdateExpression,
		req.ExpressionAttributeValues,
		returnOld,
	)
	if err != nil {
		if strings.Contains(err.Error(), "table not found") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.DynamoDBResponse{}
	switch req.ReturnValues {
	case "ALL_OLD":
		resp.Attributes = oldItem
	case "ALL_NEW":
		resp.Attributes = newItem
	case "NONE":
		// Return empty attributes
	}

	c.JSON(http.StatusOK, resp)
}

// handleDeleteItem handles DeleteItem requests.
func (h *DynamoDBHandler) handleDeleteItem(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	if len(req.Key) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Key cannot be empty",
		})
		return
	}

	returnOld := req.ReturnValues == "ALL_OLD"
	oldItem, err := h.itemManager.DeleteItem(req.TableName, req.Key, returnOld)
	if err != nil {
		if strings.Contains(err.Error(), "table not found") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.DynamoDBResponse{}
	if req.ReturnValues == "ALL_OLD" {
		resp.Attributes = oldItem
	}

	c.JSON(http.StatusOK, resp)
}

// handleQuery handles Query requests.
func (h *DynamoDBHandler) handleQuery(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	// Determine partition key value from KeyConditions or KeyConditionExpression
	// For simplicity, we'll use KeyConditions if provided
	var partitionKeyValue string
	var keyConditions map[string]models.Condition

	if len(req.KeyConditions) > 0 {
		keyConditions = req.KeyConditions
		// Extract partition key value from KeyConditions
		for attrName, condition := range req.KeyConditions {
			if condition.ComparisonOperator == "EQ" && len(condition.AttributeValueList) > 0 {
				if val, ok := condition.AttributeValueList[0].GetString(); ok {
					partitionKeyValue = val
				} else if val, ok := condition.AttributeValueList[0].GetNumber(); ok {
					partitionKeyValue = val
				}
				// Get the actual partition key name from table schema
				// For now, assume the first EQ condition is for partition key
				_ = attrName
				break
			}
		}
	}

	if partitionKeyValue == "" && req.KeyConditionExpression != "" {
		// Parse simple KeyConditionExpression like "pk = :pkval"
		// This is a simplified parser
		if idx := strings.Index(req.KeyConditionExpression, "="); idx != -1 {
			right := strings.TrimSpace(req.KeyConditionExpression[idx+1:])
			if strings.HasPrefix(right, ":") {
				valKey := right[1:]
				if val, ok := req.ExpressionAttributeValues[valKey]; ok {
					if s, ok := val.GetString(); ok {
						partitionKeyValue = s
					} else if n, ok := val.GetNumber(); ok {
						partitionKeyValue = n
					}
				}
			}
		}
	}

	if partitionKeyValue == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Partition key condition is required",
		})
		return
	}

	items, lastEvaluatedKey, err := h.itemManager.Query(
		req.TableName,
		req.IndexName,
		partitionKeyValue,
		keyConditions,
		req.ScanIndexForward,
		req.Limit,
		req.ExclusiveStartKey,
	)
	if err != nil {
		if strings.Contains(err.Error(), "table not found") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		Items:            items,
		Count:            len(items),
		ScannedCount:     len(items),
		LastEvaluatedKey: lastEvaluatedKey,
	})
}

// handleScan handles Scan requests.
func (h *DynamoDBHandler) handleScan(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	items, lastEvaluatedKey, err := h.itemManager.Scan(
		req.TableName,
		req.IndexName,
		req.Limit,
		req.ExclusiveStartKey,
		req.TotalSegments,
		req.Segment,
	)
	if err != nil {
		if strings.Contains(err.Error(), "table not found") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		Items:            items,
		Count:            len(items),
		ScannedCount:     len(items),
		LastEvaluatedKey: lastEvaluatedKey,
	})
}

func (h *DynamoDBHandler) handleCreateTable(c *gin.Context, req *models.DynamoDBRequest) {
	// Validate table name
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	// Validate key schema
	if len(req.KeySchema) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "KeySchema cannot be empty",
		})
		return
	}

	// Create table
	metadata, err := h.tableManager.CreateTable(req)
	if err != nil {
		if strings.Contains(err.Error(), "already exists") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceInUseException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		TableDescription: metadata,
	})
}

func (h *DynamoDBHandler) handleUpdateTable(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	// Build UpdateTableRequest
	updateReq := models.UpdateTableRequest{
		TableName:                   req.TableName,
		AttributeDefinitions:        req.AttributeDefinitions,
		BillingMode:                 req.BillingMode,
		ProvisionedThroughput:       req.ProvisionedThroughput,
	}

	// Parse GSI updates from request
	// Note: The DynamoDBRequest would need to be extended to include GSI updates
	// For now, we'll handle them if they're in the raw request body
	var rawReq struct {
		GlobalSecondaryIndexUpdates []models.GlobalSecondaryIndexUpdate `json:"GlobalSecondaryIndexUpdates"`
	}
	if err := c.ShouldBindJSON(&rawReq); err == nil {
		updateReq.GlobalSecondaryIndexUpdates = rawReq.GlobalSecondaryIndexUpdates
	}

	// Update table
	metadata, err := h.tableManager.UpdateTable(&updateReq)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		if strings.Contains(err.Error(), "already exists") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceInUseException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		TableDescription: metadata,
	})
}

func (h *DynamoDBHandler) handleDeleteTable(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	metadata, err := h.tableManager.DeleteTable(req.TableName)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	if metadata == nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
			Message: fmt.Sprintf("Table not found: %s", req.TableName),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		TableDescription: metadata,
	})
}

func (h *DynamoDBHandler) handleListTables(c *gin.Context) {
	// Parse request for pagination
	var req models.DynamoDBRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		// No request body or invalid, use defaults
		req.Limit = 0
		req.ExclusiveStartTableName = ""
	}

	tables, lastEvaluatedTableName, err := h.tableManager.ListTablesWithPagination(req.Limit, req.ExclusiveStartTableName)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		TableNames:             tables,
		LastEvaluatedTableName: lastEvaluatedTableName,
	})
}

func (h *DynamoDBHandler) handleDescribeTable(c *gin.Context, req *models.DynamoDBRequest) {
	if req.TableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Table name cannot be empty",
		})
		return
	}

	metadata, err := h.tableManager.DescribeTable(req.TableName)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		TableDescription: metadata,
	})
}

func (h *DynamoDBHandler) handleTagResource(c *gin.Context, req *models.DynamoDBRequest) {
	// Extract table name from ARN
	tableName := extractTableNameFromARN(req.ResourceARN)
	if tableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Invalid resource ARN",
		})
		return
	}

	// Tag the resource
	if err := h.tableManager.TagResource(tableName, req.Tags); err != nil {
		if err.Error() == fmt.Sprintf("table not found: %s", tableName) {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{})
}

func (h *DynamoDBHandler) handleUntagResource(c *gin.Context, req *models.DynamoDBRequest) {
	// Extract table name from ARN
	tableName := extractTableNameFromARN(req.ResourceARN)
	if tableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Invalid resource ARN",
		})
		return
	}

	// Untag the resource
	if err := h.tableManager.UntagResource(tableName, req.TagKeys); err != nil {
		if err.Error() == fmt.Sprintf("table not found: %s", tableName) {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{})
}

func (h *DynamoDBHandler) handleListTagsOfResource(c *gin.Context, req *models.DynamoDBRequest) {
	// Extract table name from ARN
	tableName := extractTableNameFromARN(req.ResourceARN)
	if tableName == "" {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "Invalid resource ARN",
		})
		return
	}

	// List tags
	tags, err := h.tableManager.ListTagsOfResource(tableName)
	if err != nil {
		if err.Error() == fmt.Sprintf("table not found: %s", tableName) {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Type:    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
				Message: err.Error(),
			})
			return
		}
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		Tags: tags,
	})
}

func (h *DynamoDBHandler) handleDescribeEndpoints(c *gin.Context) {
	c.JSON(http.StatusOK, models.DynamoDBResponse{
		Endpoints: []models.Endpoint{
			{
				Address:              "localhost:8080",
				CachePeriodInMinutes: 1440, // 24 hours
			},
		},
	})
}

func extractTableNameFromARN(arn string) string {
	if !strings.HasPrefix(arn, "arn:aws:dynamodb:") {
		return ""
	}

	parts := strings.Split(arn, "/")
	if len(parts) < 2 {
		return ""
	}

	return parts[len(parts)-1]
}

// handleBatchGetItem handles BatchGetItem requests.
func (h *DynamoDBHandler) handleBatchGetItem(c *gin.Context) {
	var req models.BatchGetItemRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	if len(req.RequestItems) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "RequestItems cannot be empty",
		})
		return
	}

	// Check total key count (max 100)
	totalKeys := 0
	for _, keysAndAttrs := range req.RequestItems {
		totalKeys += len(keysAndAttrs.Keys)
	}
	if totalKeys > 100 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "BatchGetItem can retrieve up to 100 items",
		})
		return
	}

	responses, unprocessedKeys, err := h.itemManager.BatchGetItem(req.RequestItems)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.BatchGetItemResponse{
		Responses:       responses,
		UnprocessedKeys: unprocessedKeys,
	}

	c.JSON(http.StatusOK, resp)
}

// handleBatchWriteItem handles BatchWriteItem requests.
func (h *DynamoDBHandler) handleBatchWriteItem(c *gin.Context) {
	var req models.BatchWriteItemRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	if len(req.RequestItems) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "RequestItems cannot be empty",
		})
		return
	}

	// Check total item count (max 25)
	totalItems := 0
	for _, writeRequests := range req.RequestItems {
		totalItems += len(writeRequests)
	}
	if totalItems > 25 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "BatchWriteItem can write up to 25 items",
		})
		return
	}

	unprocessedItems, err := h.itemManager.BatchWriteItem(req.RequestItems)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.BatchWriteItemResponse{
		UnprocessedItems: unprocessedItems,
	}

	c.JSON(http.StatusOK, resp)
}

// handleTransactGetItems handles TransactGetItems requests.
func (h *DynamoDBHandler) handleTransactGetItems(c *gin.Context) {
	var req models.TransactGetItemsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	if len(req.TransactItems) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "TransactItems cannot be empty",
		})
		return
	}

	if len(req.TransactItems) > 25 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "TransactItems can contain up to 25 items",
		})
		return
	}

	responses, err := h.itemManager.TransactGetItems(req.TransactItems)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.TransactGetItemsResponse{
		Responses: responses,
	}

	c.JSON(http.StatusOK, resp)
}

// handleTransactWriteItems handles TransactWriteItems requests.
func (h *DynamoDBHandler) handleTransactWriteItems(c *gin.Context) {
	var req models.TransactWriteItemsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	if len(req.TransactItems) == 0 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "TransactItems cannot be empty",
		})
		return
	}

	if len(req.TransactItems) > 25 {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: "TransactItems can contain up to 25 items",
		})
		return
	}

	err := h.itemManager.TransactWriteItems(req.TransactItems)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.TransactWriteItemsResponse{}
	c.JSON(http.StatusOK, resp)
}


// handleUpdateTimeToLive handles UpdateTimeToLive requests.
func (h *DynamoDBHandler) handleUpdateTimeToLive(c *gin.Context) {
	var req models.UpdateTimeToLiveRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	ttlDesc, err := h.tableManager.UpdateTimeToLive(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.UpdateTimeToLiveResponse{
		TimeToLiveDescription: *ttlDesc,
	}
	c.JSON(http.StatusOK, resp)
}

// handleDescribeTimeToLive handles DescribeTimeToLive requests.
func (h *DynamoDBHandler) handleDescribeTimeToLive(c *gin.Context) {
	var req models.DescribeTimeToLiveRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	ttlDesc, err := h.tableManager.DescribeTimeToLive(req.TableName)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.DescribeTimeToLiveResponse{
		TimeToLiveDescription: *ttlDesc,
	}
	c.JSON(http.StatusOK, resp)
}


// handleCreateBackup handles CreateBackup requests.
func (h *DynamoDBHandler) handleCreateBackup(c *gin.Context) {
	var req models.CreateBackupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	backupDesc, err := h.tableManager.CreateBackup(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.CreateBackupResponse{
		BackupDescription: *backupDesc,
	}
	c.JSON(http.StatusOK, resp)
}

// handleDeleteBackup handles DeleteBackup requests.
func (h *DynamoDBHandler) handleDeleteBackup(c *gin.Context) {
	var req models.DeleteBackupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	backupDesc, err := h.tableManager.DeleteBackup(req.BackupArn)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.DeleteBackupResponse{
		BackupDescription: *backupDesc,
	}
	c.JSON(http.StatusOK, resp)
}

// handleListBackups handles ListBackups requests.
func (h *DynamoDBHandler) handleListBackups(c *gin.Context) {
	var req models.ListBackupsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		// Empty body is allowed
		req = models.ListBackupsRequest{}
	}

	backups, err := h.tableManager.ListBackups(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.ListBackupsResponse{
		BackupSummaries: backups,
	}
	c.JSON(http.StatusOK, resp)
}

// handleRestoreTableFromBackup handles RestoreTableFromBackup requests.
func (h *DynamoDBHandler) handleRestoreTableFromBackup(c *gin.Context) {
	var req models.RestoreTableFromBackupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	metadata, err := h.tableManager.RestoreTableFromBackup(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	resp := models.RestoreTableFromBackupResponse{
		TableDescription: *metadata,
	}
	c.JSON(http.StatusOK, resp)
}
