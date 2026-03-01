"""Middleware for dyscount-api."""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from .logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests with structured logging."""

    async def dispatch(self, request: Request, call_next):
        """Process the request and log details.
        
        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/endpoint in the chain.
            
        Returns:
            The HTTP response.
        """
        start_time = time.time()
        
        # Get request details
        method = request.method
        path = request.url.path
        amz_target = request.headers.get("X-Amz-Target", "")
        
        # Process the request
        response = await call_next(request)
        
        # Calculate duration
        process_time = time.time() - start_time
        duration_ms = round(process_time * 1000, 2)
        
        # Log request with structured data
        logger.info(
            "http_request",
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            x_amz_target=amz_target if amz_target else None,
        )
        
        # Add custom header with timing info
        response.headers["X-Process-Time"] = str(duration_ms)
        
        return response
