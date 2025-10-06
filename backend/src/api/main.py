"""FastAPI application with OpenTelemetry integration"""

from contextlib import asynccontextmanager
from typing import Dict, Any
import os
import shutil
from pathlib import Path

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
from .routers import documents, queue, process, websocket, search, logs, tools
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

    # Clean up old temp files on startup (older than 1 hour)
    project_root = Path(__file__).parent.parent.parent.parent
    temp_dir = project_root / "temp"
    if temp_dir.exists():
        # Remove only old files in temp directory (older than 1 hour)
        import time
        current_time = time.time()
        one_hour_ago = current_time - 3600
        cleaned_count = 0
        for item in temp_dir.iterdir():
            try:
                # Check file modification time
                if item.is_file() and item.stat().st_mtime < one_hour_ago:
                    item.unlink()
                    cleaned_count += 1
                elif item.is_dir() and item.stat().st_mtime < one_hour_ago:
                    shutil.rmtree(item)
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to clean temp file {item}: {e}")
        if cleaned_count > 0:
            logger.info(f"Cleaned {cleaned_count} old files from temp directory: {temp_dir}")
    else:
        # Create temp directory if it doesn't exist
        temp_dir.mkdir(exist_ok=True)
        logger.info(f"Created temp directory: {temp_dir}")

    # Setup OpenTelemetry
    if settings.telemetry.enabled:
        setup_telemetry()  # No arguments needed
        FastAPIInstrumentor().instrument_app(app)
        logger.info("OpenTelemetry instrumentation enabled")

        # Configure OpenTelemetry logging to match centralized format
        from ..core.uvicorn_config import configure_otel_logging
        configure_otel_logging()

    # Initialize services
    from ..services.queue_service import queue_service
    from .routers.websocket import manager

    # Import DocumentProcessor to register it
    from ..services import document_processor

    # Inject WebSocket service into queue service
    queue_service.set_websocket_service(manager)

    # Initialize document tools system
    from ..services.document_tools import initialize_document_tools
    tool_init_result = initialize_document_tools()
    logger.info(f"Initialized {tool_init_result['registered_tools']} document tools")

    # Start queue processing
    await queue_service.start_processing()
    logger.info("Queue processing started")

    logger.info(f"API running in {settings.environment} mode")

    yield

    # Shutdown
    logger.info("Shutting down Mavn Bench API")

    # Stop queue processing
    await queue_service.stop_processing()
    logger.info("Queue processing stopped")


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
app.include_router(queue.router, tags=["queue"])
app.include_router(process.router, prefix="/api/process", tags=["processing"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])
app.include_router(logs.router, tags=["logging"])
# TODO: Implement tools router
app.include_router(tools.router, prefix="/api", tags=["tools"])

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


@app.post("/api/client-logs")
async def receive_client_logs(request: Dict[str, Any]) -> Dict[str, str]:
    """Receive and log client-side logs from the frontend"""
    logger = CentralizedLogger("ClientLogs")

    logs = request.get("logs", [])
    session_id = request.get("sessionId", "unknown")

    for log_entry in logs:
        level = log_entry.get("level", "info")
        message = f"[Frontend] {log_entry.get('message', '')}"
        context = log_entry.get("context", {})

        # Add session ID to context
        context["sessionId"] = session_id
        context["url"] = log_entry.get("url", "")
        context["timestamp"] = log_entry.get("timestamp", "")

        # Log at appropriate level
        if level == "debug":
            logger.debug(message, context)
        elif level == "info":
            logger.info(message, context)
        elif level == "warning":
            logger.warning(message, context)
        elif level == "error":
            logger.error(message, context, exc_info=log_entry.get("stackTrace"))
        else:
            logger.info(message, context)

    return {"status": "ok", "received": len(logs)}


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
    from ..core.uvicorn_config import get_uvicorn_log_config

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning",
        log_config=get_uvicorn_log_config()
    )