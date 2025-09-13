"""FastAPI application with OpenTelemetry integration"""

from contextlib import asynccontextmanager
from typing import Dict, Any
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from ..core.config import get_settings
from ..core.logger import CentralizedLogger
from ..core.telemetry import setup_telemetry
from .dependencies import get_current_user
from .middleware.auth import AuthMiddleware
from .middleware.telemetry import TelemetryMiddleware
from .middleware.error_handler import ErrorHandlerMiddleware
from .routers import documents, process, websocket, search, logs
from .socketio_app import socket_app


# Initialize settings and logger
settings = get_settings()
logger = CentralizedLogger("API")
tracer = trace.get_tracer(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Mavn Bench API")

    # Setup OpenTelemetry
    if settings.telemetry.enabled:
        setup_telemetry()  # No arguments needed
        FastAPIInstrumentor().instrument_app(app)
        logger.info("OpenTelemetry instrumentation enabled")

    # Initialize services here if needed
    logger.info(f"API running in {settings.environment} mode")

    yield

    # Shutdown
    logger.info("Shutting down Mavn Bench API")
    # Cleanup resources here if needed


# Create FastAPI app
app = FastAPI(
    title="Mavn Bench API",
    description="Document processing platform with MCP tool integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id", "X-Span-Id"]
)

# Add custom middleware (order matters - bottom executes first)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(TelemetryMiddleware)
app.add_middleware(AuthMiddleware, settings=settings)

# Include routers
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(process.router, prefix="/api/process", tags=["processing"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])
app.include_router(logs.router, tags=["logging"])
# TODO: Implement tools router
# app.include_router(tools.router, prefix="/api/tools", tags=["tools"])

# Mount Socket.IO app at a specific path
app.mount("/socket.io", socket_app)


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {
        "name": "Mavn Bench API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/api/docs"
    }


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint with service status"""
    with tracer.start_as_current_span("health_check"):
        from ..services.service_factory import ServiceFactory

        # Get all service health statuses
        service_health = await ServiceFactory.health_check_all()

        # Determine overall health
        all_healthy = all(
            status.get("status") == "healthy"
            for status in service_health.values()
        )

        return {
            "status": "healthy" if all_healthy else "degraded",
            "services": service_health,
            "environment": settings.environment,
            "telemetry_enabled": settings.telemetry.enabled
        }


@app.get("/api/info")
async def api_info() -> Dict[str, Any]:
    """API information endpoint"""
    return {
        "name": "Mavn Bench API",
        "version": "1.0.0",
        "environment": settings.environment,
        "features": {
            "document_processing": True,
            "ai_operations": True,
            "mcp_tools": settings.mcp.enabled,
            "telemetry": settings.telemetry.enabled,
            "websocket": True
        },
        "supported_formats": [
            "pdf", "word", "excel", "json", "xml",
            "podcast", "youtube", "webpage", "markdown", "csv"
        ]
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"The requested resource was not found",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "trace_id": request.state.trace_id if hasattr(request.state, "trace_id") else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )