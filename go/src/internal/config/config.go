// Package config provides configuration management for Dyscount.
package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// Config holds all configuration for the application.
type Config struct {
	Server  ServerConfig
	Storage StorageConfig
	Auth    AuthConfig
	Logging LoggingConfig
	Metrics MetricsConfig
}

// ServerConfig holds HTTP server configuration.
type ServerConfig struct {
	Host string
	Port string
	Mode string // "debug" or "release"
}

// StorageConfig holds SQLite storage configuration.
type StorageConfig struct {
	DataDirectory string
	Namespace     string
}

// AuthConfig holds authentication configuration.
type AuthConfig struct {
	Mode           string // "local" or "production"
	AWSRegion      string
	AccessKeyID    string
	SecretAccessKey string
}

// LoggingConfig holds logging configuration.
type LoggingConfig struct {
	Level  string
	Format string // "json" or "text"
}

// MetricsConfig holds Prometheus metrics configuration.
type MetricsConfig struct {
	Enabled bool
	Port    string
	Path    string
}

// Load loads configuration from environment variables with defaults.
func Load() (*Config, error) {
	cfg := &Config{
		Server: ServerConfig{
			Host: getEnv("DYSCOUNT_SERVER_HOST", "0.0.0.0"),
			Port: getEnv("DYSCOUNT_SERVER_PORT", "8000"),
			Mode: getEnv("DYSCOUNT_SERVER_MODE", "debug"),
		},
		Storage: StorageConfig{
			DataDirectory: getEnv("DYSCOUNT_STORAGE_DATA_DIRECTORY", "./data"),
			Namespace:     getEnv("DYSCOUNT_STORAGE_NAMESPACE", "default"),
		},
		Auth: AuthConfig{
			Mode:            getEnv("DYSCOUNT_AUTH_MODE", "local"),
			AWSRegion:       getEnv("DYSCOUNT_AUTH_AWS_REGION", "eu-west-1"),
			AccessKeyID:     getEnv("DYSCOUNT_AUTH_ACCESS_KEY_ID", "local"),
			SecretAccessKey: getEnv("DYSCOUNT_AUTH_SECRET_ACCESS_KEY", "local"),
		},
		Logging: LoggingConfig{
			Level:  getEnv("DYSCOUNT_LOGGING_LEVEL", "info"),
			Format: getEnv("DYSCOUNT_LOGGING_FORMAT", "json"),
		},
		Metrics: MetricsConfig{
			Enabled: getEnvBool("DYSCOUNT_METRICS_ENABLED", true),
			Port:    getEnv("DYSCOUNT_METRICS_PORT", "9090"),
			Path:    getEnv("DYSCOUNT_METRICS_PATH", "/metrics"),
		},
	}

	// Ensure data directory exists
	dataDir, err := filepath.Abs(cfg.Storage.DataDirectory)
	if err != nil {
		return nil, fmt.Errorf("invalid data directory: %w", err)
	}
	cfg.Storage.DataDirectory = dataDir

	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create data directory: %w", err)
	}

	return cfg, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		b, err := strconv.ParseBool(strings.ToLower(value))
		if err == nil {
			return b
		}
	}
	return defaultValue
}
