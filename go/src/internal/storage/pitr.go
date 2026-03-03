// Package storage provides Point-in-Time Recovery (PITR) support.
package storage

import (
	"database/sql"
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/e6qu/dyscount/internal/models"
)

// PITRManager manages Point-in-Time Recovery.
type PITRManager struct {
	dataDirectory string
	namespace     string
	mu            sync.RWMutex
	settings      map[string]*models.ContinuousBackupsDescription
}

// NewPITRManager creates a new PITRManager.
func NewPITRManager(dataDirectory, namespace string) *PITRManager {
	return &PITRManager{
		dataDirectory: dataDirectory,
		namespace:     namespace,
		settings:      make(map[string]*models.ContinuousBackupsDescription),
	}
}

// UpdateContinuousBackups enables or disables PITR.
func (pm *PITRManager) UpdateContinuousBackups(tableName string, enabled bool) (*models.ContinuousBackupsDescription, error) {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	status := models.PointInTimeRecoveryStatusDisabled
	if enabled {
		status = models.PointInTimeRecoveryStatusEnabled
	}

	desc := &models.ContinuousBackupsDescription{
		ContinuousBackupsStatus: status,
	}

	if enabled {
		now := time.Now().Unix()
		desc.PointInTimeRecoveryDescription = &models.PointInTimeRecoveryDescription{
			PointInTimeRecoveryStatus:  status,
			EarliestRestorableDateTime: now - 35*24*60*60, // 35 days ago
			LatestRestorableDateTime:   now,
		}
	}

	pm.settings[tableName] = desc
	return desc, nil
}

// DescribeContinuousBackups returns PITR status.
func (pm *PITRManager) DescribeContinuousBackups(tableName string) (*models.ContinuousBackupsDescription, error) {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	if desc, ok := pm.settings[tableName]; ok {
		// Update latest restorable time if enabled
		if desc.PointInTimeRecoveryDescription != nil {
			desc.PointInTimeRecoveryDescription.LatestRestorableDateTime = time.Now().Unix()
		}
		return desc, nil
	}

	// Default is disabled
	return &models.ContinuousBackupsDescription{
		ContinuousBackupsStatus: models.PointInTimeRecoveryStatusDisabled,
	}, nil
}

// RestoreTableToPointInTime restores a table to a specific point in time.
func (tm *TableManager) RestoreTableToPointInTime(req *models.RestoreTableToPointInTimeRequest) (*models.TableMetadata, error) {
	// Check if source table exists
	sourceDBPath := tm.getDBPath(req.SourceTableName)
	if _, err := os.Stat(sourceDBPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("source table not found: %s", req.SourceTableName)
	}

	// Check if target table already exists
	targetDBPath := tm.getDBPath(req.TargetTableName)
	if _, err := os.Stat(targetDBPath); err == nil {
		return nil, fmt.Errorf("target table already exists: %s", req.TargetTableName)
	}

	// Get source table metadata
	sourceMetadata, err := tm.DescribeTable(req.SourceTableName)
	if err != nil {
		return nil, fmt.Errorf("failed to get source table metadata: %w", err)
	}

	// Copy the database file
	if err := tm.copyFile(sourceDBPath, targetDBPath); err != nil {
		return nil, fmt.Errorf("failed to restore table: %w", err)
	}

	// Update metadata for restored table
	db, err := sql.Open("sqlite3", targetDBPath)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	// Update table name in metadata
	sourceMetadata.TableName = req.TargetTableName
	sourceMetadata.TableARN = fmt.Sprintf("arn:aws:dynamodb:local:%s:table/%s", tm.namespace, req.TargetTableName)
	sourceMetadata.CreationDateTime = time.Now()

	// Store updated metadata
	if err := tm.storeTableMetadata(db, sourceMetadata); err != nil {
		return nil, err
	}

	return sourceMetadata, nil
}
