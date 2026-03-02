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
}

// NewDynamoDBHandler creates a new DynamoDBHandler.
func NewDynamoDBHandler(tm *storage.TableManager) *DynamoDBHandler {
	return &DynamoDBHandler{tableManager: tm}
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
	default:
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#ValidationException",
			Message: fmt.Sprintf("Unknown operation: %s", operation),
		})
	}
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
	tables, err := h.tableManager.ListTables()
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Type:    "com.amazonaws.dynamodb.v20120810#InternalServerError",
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.DynamoDBResponse{
		TableNames: tables,
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

	// TODO: Implement tag storage
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

	// TODO: Implement tag removal
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

	// TODO: Implement tag listing
	c.JSON(http.StatusOK, models.DynamoDBResponse{
		Tags: []models.Tag{},
	})
}

func (h *DynamoDBHandler) handleDescribeEndpoints(c *gin.Context) {
	c.JSON(http.StatusOK, models.DynamoDBResponse{
		Endpoints: []models.Endpoint{
			{
				Address:              "localhost:8000",
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
