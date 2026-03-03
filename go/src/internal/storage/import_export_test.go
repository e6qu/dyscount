// Package storage provides tests for import/export operations.
package storage

import (
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/e6qu/dyscount/internal/models"
)

func TestImportExportManager_ExportTableToPointInTime(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-import-export-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	iem := NewImportExportManager(tempDir, "default")

	t.Run("Create Export", func(t *testing.T) {
		req := &models.ExportTableToPointInTimeRequest{
			TableArn:  "arn:aws:dynamodb:local:default:table/TestTable",
			S3Bucket:  "test-bucket",
			S3Prefix:  "exports/",
			ExportFormat: models.ExportFormatDynamoDBJSON,
			ExportType:   models.ExportTypeFullExport,
		}

		export, err := iem.ExportTableToPointInTime(req)
		if err != nil {
			t.Fatalf("ExportTableToPointInTime failed: %v", err)
		}

		if export.ExportArn == "" {
			t.Error("ExportArn should not be empty")
		}

		if export.ExportStatus != models.ExportStatusInProgress {
			t.Errorf("Expected status IN_PROGRESS, got %s", export.ExportStatus)
		}

		if export.TableName != "TestTable" {
			t.Errorf("Expected TableName=TestTable, got %s", export.TableName)
		}

		if export.S3Bucket != "test-bucket" {
			t.Errorf("Expected S3Bucket=test-bucket, got %s", export.S3Bucket)
		}
	})

	t.Run("Describe Export", func(t *testing.T) {
		// Create an export first
		req := &models.ExportTableToPointInTimeRequest{
			TableArn: "arn:aws:dynamodb:local:default:table/TestTable2",
			S3Bucket: "test-bucket",
		}

		export, err := iem.ExportTableToPointInTime(req)
		if err != nil {
			t.Fatalf("ExportTableToPointInTime failed: %v", err)
		}

		// Wait for completion
		time.Sleep(3 * time.Second)

		// Describe the export
		described, err := iem.DescribeExport(string(export.ExportArn))
		if err != nil {
			t.Fatalf("DescribeExport failed: %v", err)
		}

		if described.ExportArn != export.ExportArn {
			t.Errorf("ExportArn mismatch: expected %s, got %s", export.ExportArn, described.ExportArn)
		}

		// Status should be completed after the goroutine runs
		if described.ExportStatus != models.ExportStatusCompleted {
			t.Errorf("Expected status COMPLETED, got %s", described.ExportStatus)
		}
	})

	t.Run("Describe NonExistent Export", func(t *testing.T) {
		_, err := iem.DescribeExport("arn:aws:dynamodb:local:default:export/nonexistent")
		if err == nil {
			t.Error("Expected error for non-existent export")
		}
	})

	t.Run("List Exports", func(t *testing.T) {
		// Create a few exports
		for i := 0; i < 3; i++ {
			req := &models.ExportTableToPointInTimeRequest{
				TableArn: fmt.Sprintf("arn:aws:dynamodb:local:default:table/Table%d", i),
				S3Bucket: "test-bucket",
			}
			_, err := iem.ExportTableToPointInTime(req)
			if err != nil {
				t.Fatalf("ExportTableToPointInTime failed: %v", err)
			}
		}

		listReq := &models.ListExportsRequest{}
		resp, err := iem.ListExports(listReq)
		if err != nil {
			t.Fatalf("ListExports failed: %v", err)
		}

		if len(resp.ExportSummaries) < 3 {
			t.Errorf("Expected at least 3 exports, got %d", len(resp.ExportSummaries))
		}
	})

	t.Run("List Exports With Limit", func(t *testing.T) {
		listReq := &models.ListExportsRequest{
			MaxResults: 2,
		}
		resp, err := iem.ListExports(listReq)
		if err != nil {
			t.Fatalf("ListExports failed: %v", err)
		}

		if len(resp.ExportSummaries) > 2 {
			t.Errorf("Expected at most 2 exports, got %d", len(resp.ExportSummaries))
		}
	})
}

func TestImportExportManager_ImportTable(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-import-export-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	iem := NewImportExportManager(tempDir, "default")

	t.Run("Create Import", func(t *testing.T) {
		req := &models.ImportTableRequest{
			TableName:      "ImportedTable",
			S3BucketSource: "test-bucket",
			S3Prefix:       "imports/",
			ImportFormat:   models.ExportFormatDynamoDBJSON,
			KeySchema: []models.KeySchemaElement{
				{AttributeName: "pk", KeyType: "HASH"},
			},
			AttributeDefinitions: []models.AttributeDefinition{
				{AttributeName: "pk", AttributeType: "S"},
			},
		}

		imp, err := iem.ImportTable(req)
		if err != nil {
			t.Fatalf("ImportTable failed: %v", err)
		}

		if imp.ImportArn == "" {
			t.Error("ImportArn should not be empty")
		}

		if imp.ImportStatus != models.ImportStatusInProgress {
			t.Errorf("Expected status IN_PROGRESS, got %s", imp.ImportStatus)
		}

		if imp.TableName != "ImportedTable" {
			t.Errorf("Expected TableName=ImportedTable, got %s", imp.TableName)
		}
	})

	t.Run("Describe Import", func(t *testing.T) {
		// Create an import first
		req := &models.ImportTableRequest{
			TableName:      "ImportedTable2",
			S3BucketSource: "test-bucket",
			KeySchema: []models.KeySchemaElement{
				{AttributeName: "pk", KeyType: "HASH"},
			},
			AttributeDefinitions: []models.AttributeDefinition{
				{AttributeName: "pk", AttributeType: "S"},
			},
		}

		imp, err := iem.ImportTable(req)
		if err != nil {
			t.Fatalf("ImportTable failed: %v", err)
		}

		// Wait for completion
		time.Sleep(3 * time.Second)

		// Describe the import
		described, err := iem.DescribeImport(imp.ImportArn)
		if err != nil {
			t.Fatalf("DescribeImport failed: %v", err)
		}

		if described.ImportArn != imp.ImportArn {
			t.Errorf("ImportArn mismatch: expected %s, got %s", imp.ImportArn, described.ImportArn)
		}

		// Status should be completed after the goroutine runs
		if described.ImportStatus != models.ImportStatusCompleted {
			t.Errorf("Expected status COMPLETED, got %s", described.ImportStatus)
		}
	})

	t.Run("Describe NonExistent Import", func(t *testing.T) {
		_, err := iem.DescribeImport("arn:aws:dynamodb:local:default:import/nonexistent")
		if err == nil {
			t.Error("Expected error for non-existent import")
		}
	})

	t.Run("List Imports", func(t *testing.T) {
		// Create a few imports
		for i := 0; i < 3; i++ {
			req := &models.ImportTableRequest{
				TableName:      fmt.Sprintf("ImportedTable%d", i),
				S3BucketSource: "test-bucket",
				KeySchema: []models.KeySchemaElement{
					{AttributeName: "pk", KeyType: "HASH"},
				},
				AttributeDefinitions: []models.AttributeDefinition{
					{AttributeName: "pk", AttributeType: "S"},
				},
			}
			_, err := iem.ImportTable(req)
			if err != nil {
				t.Fatalf("ImportTable failed: %v", err)
			}
		}

		listReq := &models.ListImportsRequest{}
		resp, err := iem.ListImports(listReq)
		if err != nil {
			t.Fatalf("ListImports failed: %v", err)
		}

		if len(resp.ImportSummaries) < 3 {
			t.Errorf("Expected at least 3 imports, got %d", len(resp.ImportSummaries))
		}
	})
}
