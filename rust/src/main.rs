//! Dyscount - DynamoDB-compatible API service written in Rust
//! 
//! This is the main entry point for the Rust implementation of Dyscount.

mod handlers;
mod items;
mod models;
mod storage;

use axum::{
    routing::{get, post},
    Router,
};
use std::net::SocketAddr;
use std::sync::Arc;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use crate::handlers::{dynamodb_handler, health_check, AppState};
use crate::items::ItemManager;
use crate::storage::TableManager;

/// Default configuration
const DEFAULT_HOST: &str = "127.0.0.1";
const DEFAULT_PORT: u16 = 8000;
const DEFAULT_DATA_DIR: &str = "./data";
const DEFAULT_NAMESPACE: &str = "default";

/// Application configuration
#[derive(Debug, Clone)]
struct Config {
    host: String,
    port: u16,
    data_directory: String,
    namespace: String,
}

impl Config {
    /// Load configuration from environment variables
    fn from_env() -> Self {
        Self {
            host: std::env::var("DYSCOUNT_HOST").unwrap_or_else(|_| DEFAULT_HOST.to_string()),
            port: std::env::var("DYSCOUNT_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(DEFAULT_PORT),
            data_directory: std::env::var("DYSCOUNT_DATA_DIR")
                .unwrap_or_else(|_| DEFAULT_DATA_DIR.to_string()),
            namespace: std::env::var("DYSCOUNT_NAMESPACE")
                .unwrap_or_else(|_| DEFAULT_NAMESPACE.to_string()),
        }
    }
}

#[tokio::main]
async fn main() {
    // Initialize tracing
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    
    tracing::subscriber::set_global_default(subscriber)
        .expect("Failed to set tracing subscriber");

    // Load configuration
    let config = Config::from_env();
    info!("Starting Dyscount with config: {:?}", config);

    // Initialize table manager
    let table_manager = Arc::new(
        TableManager::new(&config.data_directory, &config.namespace)
            .expect("Failed to initialize table manager")
    );

    // Initialize item manager
    let item_manager = Arc::new(ItemManager::new(table_manager.clone()));

    // Create application state
    let app_state = AppState { table_manager, item_manager };

    // Build router
    let app = Router::new()
        .route("/", post(dynamodb_handler))
        .route("/health", get(health_check))
        .with_state(app_state);

    // Start server
    let addr = SocketAddr::from((
        config.host.parse::<std::net::IpAddr>().expect("Invalid host"),
        config.port,
    ));

    info!("Dyscount server listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod integration_tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use tower::ServiceExt;

    fn create_test_app() -> Router {
        // Use a unique temp directory for each test run
        let temp_dir = std::env::temp_dir()
            .join(format!("dyscount_test_{}", std::process::id()));
        // Ignore errors - directory might not exist
        let _ = std::fs::remove_dir_all(&temp_dir);
        // Create the directory
        std::fs::create_dir_all(&temp_dir).unwrap();
        
        let table_manager = Arc::new(
            TableManager::new(&temp_dir, "test").unwrap()
        );
        let item_manager = Arc::new(ItemManager::new(table_manager.clone()));
        let app_state = AppState { table_manager, item_manager };

        Router::new()
            .route("/", post(dynamodb_handler))
            .route("/health", get(health_check))
            .with_state(app_state)
    }

    #[tokio::test]
    async fn test_health_check() {
        let app = create_test_app();

        let response = app
            .oneshot(Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_create_table() {
        let app = create_test_app();

        let request_body = serde_json::json!({
            "TableName": "TestTable",
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            "BillingMode": "PAY_PER_REQUEST"
        });

        let response = app
            .oneshot(Request::builder()
                .method("POST")
                .uri("/")
                .header("X-Amz-Target", "DynamoDB_20120810.CreateTable")
                .header("Content-Type", "application/json")
                .body(Body::from(request_body.to_string()))
                .unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_missing_amz_target() {
        let app = create_test_app();

        let response = app
            .oneshot(Request::builder()
                .method("POST")
                .uri("/")
                .header("Content-Type", "application/json")
                .body(Body::from("{}"))
                .unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }
}
