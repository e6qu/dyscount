// Package storage provides import/export support for DynamoDB operations.
package storage

import (
	"fmt"
	"regexp"
	"sync"
	"time"

	"github.com/e6qu/dyscount/internal/models"
	"github.com/google/uuid"
)

// ImportExportManager manages import and export operations.
type ImportExportManager struct {
	dataDirectory string
	namespace     string
	exports       map[string]*models.ExportDescription
	imports       map[string]*models.ImportDescription
	mu            sync.RWMutex
}

// NewImportExportManager creates a new ImportExportManager.
func NewImportExportManager(dataDirectory, namespace string) *ImportExportManager {
	return &ImportExportManager{
		dataDirectory: dataDirectory,
		namespace:     namespace,
		exports:       make(map[string]*models.ExportDescription),
		imports:       make(map[string]*models.ImportDescription),
	}
}

// ExportTableToPointInTime exports a table to S3.
func (iem *ImportExportManager) ExportTableToPointInTime(req *models.ExportTableToPointInTimeRequest) (*models.ExportDescription, error) {
	// Generate export ARN
	exportID := uuid.New().String()
	exportArn := fmt.Sprintf("arn:aws:dynamodb:local:%s:export/%s", iem.namespace, exportID)
	
	// Extract table name from ARN
	tableName := extractTableNameFromARN(req.TableArn)
	if tableName == "" {
		tableName = "unknown"
	}
	
	exportDesc := &models.ExportDescription{
		ExportArn:    exportArn,
		ExportStatus: models.ExportStatusInProgress,
		ExportTime:   time.Now().Unix(),
		TableArn:     req.TableArn,
		TableName:    tableName,
		S3Bucket:     req.S3Bucket,
		S3Prefix:     req.S3Prefix,
		ExportFormat: req.ExportFormat,
		ExportType:   req.ExportType,
	}
	
	if exportDesc.ExportFormat == "" {
		exportDesc.ExportFormat = models.ExportFormatDynamoDBJSON
	}
	if exportDesc.ExportType == "" {
		exportDesc.ExportType = models.ExportTypeFullExport
	}
	
	iem.mu.Lock()
	iem.exports[exportArn] = exportDesc
	iem.mu.Unlock()
	
	// Simulate export completion in background
	go iem.completeExport(exportArn)
	
	return exportDesc, nil
}

// completeExport simulates export completion.
func (iem *ImportExportManager) completeExport(exportArn string) {
	time.Sleep(2 * time.Second)
	
	iem.mu.Lock()
	defer iem.mu.Unlock()
	
	if export, ok := iem.exports[exportArn]; ok {
		export.ExportStatus = models.ExportStatusCompleted
		export.ItemCount = 100 // Simulated
		export.ProcessedBytes = 1024 * 1024 // Simulated 1MB
	}
}

// DescribeExport returns export details.
func (iem *ImportExportManager) DescribeExport(exportArn string) (*models.ExportDescription, error) {
	iem.mu.RLock()
	defer iem.mu.RUnlock()
	
	if export, ok := iem.exports[exportArn]; ok {
		return export, nil
	}
	
	return nil, fmt.Errorf("export not found: %s", exportArn)
}

// ListExports lists all exports.
func (iem *ImportExportManager) ListExports(req *models.ListExportsRequest) (*models.ListExportsResponse, error) {
	iem.mu.RLock()
	defer iem.mu.RUnlock()
	
	var summaries []models.ExportSummary
	for _, export := range iem.exports {
		// Filter by table ARN if specified
		if req.TableArn != "" && export.TableArn != req.TableArn {
			continue
		}
		
		summaries = append(summaries, models.ExportSummary{
			ExportArn:    string(export.ExportArn),
			ExportStatus: export.ExportStatus,
			ExportType:   export.ExportType,
		})
	}
	
	// Apply limit
	if req.MaxResults > 0 && len(summaries) > req.MaxResults {
		summaries = summaries[:req.MaxResults]
	}
	
	return &models.ListExportsResponse{
		ExportSummaries: summaries,
	}, nil
}

// ImportTable imports a table from S3.
func (iem *ImportExportManager) ImportTable(req *models.ImportTableRequest) (*models.ImportDescription, error) {
	// Generate import ARN
	importID := uuid.New().String()
	importArn := fmt.Sprintf("arn:aws:dynamodb:local:%s:import/%s", iem.namespace, importID)
	
	importDesc := &models.ImportDescription{
		ImportArn:      importArn,
		ImportStatus:   models.ImportStatusInProgress,
		TableName:      req.TableName,
		S3BucketSource: req.S3BucketSource,
		S3Prefix:       req.S3Prefix,
		ImportFormat:   req.ImportFormat,
	}
	
	if importDesc.ImportFormat == "" {
		importDesc.ImportFormat = models.ExportFormatDynamoDBJSON
	}
	
	iem.mu.Lock()
	iem.imports[importArn] = importDesc
	iem.mu.Unlock()
	
	// Simulate import completion in background
	go iem.completeImport(importArn)
	
	return importDesc, nil
}

// completeImport simulates import completion.
func (iem *ImportExportManager) completeImport(importArn string) {
	time.Sleep(2 * time.Second)
	
	iem.mu.Lock()
	defer iem.mu.Unlock()
	
	if imp, ok := iem.imports[importArn]; ok {
		imp.ImportStatus = models.ImportStatusCompleted
		imp.ItemCount = 100 // Simulated
		imp.ProcessedBytes = 1024 * 1024 // Simulated 1MB
	}
}

// DescribeImport returns import details.
func (iem *ImportExportManager) DescribeImport(importArn string) (*models.ImportDescription, error) {
	iem.mu.RLock()
	defer iem.mu.RUnlock()
	
	if imp, ok := iem.imports[importArn]; ok {
		return imp, nil
	}
	
	return nil, fmt.Errorf("import not found: %s", importArn)
}

// ListImports lists all imports.
func (iem *ImportExportManager) ListImports(req *models.ListImportsRequest) (*models.ListImportsResponse, error) {
	iem.mu.RLock()
	defer iem.mu.RUnlock()
	
	var summaries []models.ImportSummary
	for _, imp := range iem.imports {
		summaries = append(summaries, models.ImportSummary{
			ImportArn:    imp.ImportArn,
			ImportStatus: imp.ImportStatus,
		})
	}
	
	// Apply limit
	if req.MaxResults > 0 && len(summaries) > req.MaxResults {
		summaries = summaries[:req.MaxResults]
	}
	
	return &models.ListImportsResponse{
		ImportSummaries: summaries,
	}, nil
}

// extractTableNameFromARN extracts table name from an ARN.
func extractTableNameFromARN(arn string) string {
	// Simple extraction: arn:aws:dynamodb:local:namespace:table/TableName
	// or arn:aws:dynamodb:local:default:table/TableName
	re := regexp.MustCompile(`table/(\w+)`)
	matches := re.FindStringSubmatch(arn)
	if len(matches) >= 2 {
		return matches[1]
	}
	return ""
}
