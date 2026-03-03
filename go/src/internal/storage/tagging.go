// Package storage provides tagging operations for DynamoDB tables.
package storage

import (
	"database/sql"
	"fmt"
	"os"

	"github.com/e6qu/dyscount/internal/models"
)

// TagResource adds or updates tags on a resource.
func (tm *TableManager) TagResource(tableName string, tags []models.Tag) error {
	dbPath := tm.getDBPath(tableName)

	// Check if table exists
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return fmt.Errorf("table not found: %s", tableName)
	}

	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Create tags table if not exists
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS __tags (
			key TEXT PRIMARY KEY,
			value TEXT NOT NULL
		)
	`)
	if err != nil {
		return fmt.Errorf("failed to create tags table: %w", err)
	}

	// Insert or replace tags
	for _, tag := range tags {
		_, err = db.Exec(
			"INSERT OR REPLACE INTO __tags (key, value) VALUES (?, ?)",
			tag.Key, tag.Value,
		)
		if err != nil {
			return fmt.Errorf("failed to store tag %s: %w", tag.Key, err)
		}
	}

	return nil
}

// UntagResource removes tags from a resource.
func (tm *TableManager) UntagResource(tableName string, tagKeys []string) error {
	dbPath := tm.getDBPath(tableName)

	// Check if table exists
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return fmt.Errorf("table not found: %s", tableName)
	}

	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Check if tags table exists
	var exists bool
	err = db.QueryRow(
		"SELECT 1 FROM sqlite_master WHERE type='table' AND name='__tags'",
	).Scan(&exists)
	if err != nil || !exists {
		// No tags to remove
		return nil
	}

	// Remove tags
	for _, key := range tagKeys {
		_, err = db.Exec("DELETE FROM __tags WHERE key = ?", key)
		if err != nil {
			return fmt.Errorf("failed to remove tag %s: %w", key, err)
		}
	}

	return nil
}

// ListTagsOfResource returns all tags for a resource.
func (tm *TableManager) ListTagsOfResource(tableName string) ([]models.Tag, error) {
	dbPath := tm.getDBPath(tableName)

	// Check if table exists
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("table not found: %s", tableName)
	}

	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Check if tags table exists
	var exists bool
	err = db.QueryRow(
		"SELECT 1 FROM sqlite_master WHERE type='table' AND name='__tags'",
	).Scan(&exists)
	if err != nil || !exists {
		// No tags yet
		return []models.Tag{}, nil
	}

	// Get all tags
	rows, err := db.Query("SELECT key, value FROM __tags")
	if err != nil {
		return nil, fmt.Errorf("failed to query tags: %w", err)
	}
	defer rows.Close()

	var tags []models.Tag
	for rows.Next() {
		var tag models.Tag
		if err := rows.Scan(&tag.Key, &tag.Value); err != nil {
			continue
		}
		tags = append(tags, tag)
	}

	return tags, nil
}
