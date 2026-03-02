package main

import (
	"log"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"

	"github.com/e6qu/dyscount/internal/config"
	"github.com/e6qu/dyscount/internal/handlers"
	"github.com/e6qu/dyscount/internal/storage"
)

// @title Dyscount API
// @version 0.1.0
// @description DynamoDB-compatible API service written in Go
// @host localhost:8000
// @BasePath /
func main() {
	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Setup storage
	tableManager, err := storage.NewTableManager(cfg.Storage.DataDirectory, cfg.Storage.Namespace)
	if err != nil {
		log.Fatalf("Failed to initialize storage: %v", err)
	}

	// Setup Gin
	if cfg.Server.Mode == "release" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.Default()

	// Health check endpoint
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "healthy"})
	})

	// Prometheus metrics endpoint
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// Swagger documentation
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	// DynamoDB API endpoint
	dynamoHandler := handlers.NewDynamoDBHandler(tableManager)
	r.POST("/", dynamoHandler.Handle)

	// Start server
	addr := cfg.Server.Host + ":" + cfg.Server.Port
	log.Printf("Starting Dyscount server on %s", addr)
	if err := r.Run(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
		os.Exit(1)
	}
}
