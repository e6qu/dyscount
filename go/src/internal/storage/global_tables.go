// Package storage provides Global Tables support.
package storage

import (
	"fmt"
	"sync"
	"time"

	"github.com/e6qu/dyscount/internal/models"
)

// GlobalTableManager manages DynamoDB Global Tables.
type GlobalTableManager struct {
	dataDirectory string
	namespace     string
	mu            sync.RWMutex
	globalTables  map[string]*models.GlobalTableDescription
}

// NewGlobalTableManager creates a new GlobalTableManager.
func NewGlobalTableManager(dataDirectory, namespace string) *GlobalTableManager {
	return &GlobalTableManager{
		dataDirectory: dataDirectory,
		namespace:     namespace,
		globalTables:  make(map[string]*models.GlobalTableDescription),
	}
}

// CreateGlobalTable creates a new global table.
func (gtm *GlobalTableManager) CreateGlobalTable(req *models.CreateGlobalTableRequest) (*models.GlobalTableDescription, error) {
	gtm.mu.Lock()
	defer gtm.mu.Unlock()

	// Check if global table already exists
	if _, exists := gtm.globalTables[req.GlobalTableName]; exists {
		return nil, fmt.Errorf("global table already exists: %s", req.GlobalTableName)
	}

	// Create global table description
	desc := &models.GlobalTableDescription{
		GlobalTableName:   req.GlobalTableName,
		GlobalTableStatus: models.GlobalTableStatusCreating,
		ReplicationGroup:  []models.ReplicaDescription{},
	}

	// Add replicas
	for _, replica := range req.ReplicationGroup {
		desc.ReplicationGroup = append(desc.ReplicationGroup, models.ReplicaDescription{
			RegionName:    replica.RegionName,
			ReplicaStatus: models.GlobalTableStatusCreating,
		})
	}

	gtm.globalTables[req.GlobalTableName] = desc

	// Simulate activation
	go gtm.activateGlobalTable(req.GlobalTableName)

	return desc, nil
}

// activateGlobalTable simulates the global table becoming active.
func (gtm *GlobalTableManager) activateGlobalTable(globalTableName string) {
	time.Sleep(2 * time.Second)

	gtm.mu.Lock()
	defer gtm.mu.Unlock()

	if desc, ok := gtm.globalTables[globalTableName]; ok {
		desc.GlobalTableStatus = models.GlobalTableStatusActive
		for i := range desc.ReplicationGroup {
			desc.ReplicationGroup[i].ReplicaStatus = models.GlobalTableStatusActive
		}
	}
}

// UpdateGlobalTable updates a global table (adds/removes replicas).
func (gtm *GlobalTableManager) UpdateGlobalTable(req *models.UpdateGlobalTableRequest) (*models.GlobalTableDescription, error) {
	gtm.mu.Lock()
	defer gtm.mu.Unlock()

	desc, exists := gtm.globalTables[req.GlobalTableName]
	if !exists {
		return nil, fmt.Errorf("global table not found: %s", req.GlobalTableName)
	}

	// Process replica updates
	for _, update := range req.ReplicaUpdates {
		if update.Create != nil {
			// Add new replica
			desc.ReplicationGroup = append(desc.ReplicationGroup, models.ReplicaDescription{
				RegionName:    update.Create.RegionName,
				ReplicaStatus: models.GlobalTableStatusCreating,
			})
		} else if update.Delete != nil {
			// Remove replica
			newGroup := []models.ReplicaDescription{}
			for _, r := range desc.ReplicationGroup {
				if r.RegionName != update.Delete.RegionName {
					newGroup = append(newGroup, r)
				}
			}
			desc.ReplicationGroup = newGroup
		}
	}

	desc.GlobalTableStatus = models.GlobalTableStatusUpdating

	// Simulate completion
	go gtm.activateGlobalTable(req.GlobalTableName)

	return desc, nil
}

// DescribeGlobalTable returns global table details.
func (gtm *GlobalTableManager) DescribeGlobalTable(globalTableName string) (*models.GlobalTableDescription, error) {
	gtm.mu.RLock()
	defer gtm.mu.RUnlock()

	if desc, ok := gtm.globalTables[globalTableName]; ok {
		return desc, nil
	}

	return nil, fmt.Errorf("global table not found: %s", globalTableName)
}

// ListGlobalTables lists all global tables.
func (gtm *GlobalTableManager) ListGlobalTables(limit int, exclusiveStartTableName string) ([]models.GlobalTable, string, error) {
	gtm.mu.RLock()
	defer gtm.mu.RUnlock()

	var tables []models.GlobalTable
	for name, desc := range gtm.globalTables {
		// Handle pagination
		if exclusiveStartTableName != "" && name <= exclusiveStartTableName {
			continue
		}

		replicas := []models.Replica{}
		for _, r := range desc.ReplicationGroup {
			replicas = append(replicas, models.Replica{RegionName: r.RegionName})
		}

		tables = append(tables, models.GlobalTable{
			GlobalTableName:  name,
			ReplicationGroup: replicas,
		})
	}

	// Apply limit
	var lastEvaluatedTableName string
	if limit > 0 && len(tables) > limit {
		tables = tables[:limit]
		lastEvaluatedTableName = tables[len(tables)-1].GlobalTableName
	}

	return tables, lastEvaluatedTableName, nil
}

// UpdateGlobalTableSettings updates global table settings.
func (gtm *GlobalTableManager) UpdateGlobalTableSettings(req *models.UpdateGlobalTableSettingsRequest) (*models.GlobalTableDescription, error) {
	gtm.mu.Lock()
	defer gtm.mu.Unlock()

	desc, exists := gtm.globalTables[req.GlobalTableName]
	if !exists {
		return nil, fmt.Errorf("global table not found: %s", req.GlobalTableName)
	}

	// Settings update logic would go here
	// For now, just return the current description

	return desc, nil
}

// DeleteGlobalTable deletes a global table.
func (gtm *GlobalTableManager) DeleteGlobalTable(globalTableName string) (*models.GlobalTableDescription, error) {
	gtm.mu.Lock()
	defer gtm.mu.Unlock()

	desc, exists := gtm.globalTables[globalTableName]
	if !exists {
		return nil, fmt.Errorf("global table not found: %s", globalTableName)
	}

	// Update status to deleting
	desc.GlobalTableStatus = models.GlobalTableStatusDeleting

	// Simulate deletion (remove from map after a brief delay)
	go func(name string) {
		time.Sleep(500 * time.Millisecond)
		gtm.mu.Lock()
		defer gtm.mu.Unlock()
		delete(gtm.globalTables, name)
	}(globalTableName)

	return desc, nil
}
