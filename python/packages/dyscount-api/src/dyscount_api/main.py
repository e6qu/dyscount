"""Main FastAPI application for dyscount-api."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from dyscount_core.config import Config

from .dependencies import get_config
from .logging import setup_logging
from .middleware import LoggingMiddleware
from .routes import tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    setup_logging()
    yield
    # Shutdown


def create_app(config: Config | None = None) -> FastAPI:
    """Create and configure the FastAPI application.
    
    Args:
        config: Optional configuration object. If not provided, uses default.
        
    Returns:
        Configured FastAPI application instance.
    """
    if config is None:
        config = Config()
    
    app = FastAPI(
        title="Dyscount",
        description="DynamoDB-compatible API service",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # Add middleware
    app.add_middleware(LoggingMiddleware)
    
    # Include routes
    app.include_router(tables.router)
    
    # Override dependency to use the provided config
    from .dependencies import get_config
    app.dependency_overrides[get_config] = lambda: config
    
    return app


def main():
    """Entry point for running the server via command line."""
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


# Entry point for uvicorn
app = create_app()


if __name__ == "__main__":
    main()
