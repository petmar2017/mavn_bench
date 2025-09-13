"""API Dependencies for dependency injection"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader

from ..core.config import get_settings
from ..services.service_factory import ServiceFactory, ServiceType
from ..storage.storage_factory import StorageFactory


# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header)
) -> Dict[str, Any]:
    """Get current user from API key

    Args:
        request: FastAPI request object
        api_key: API key from header

    Returns:
        User information dictionary

    Raises:
        HTTPException: If API key is invalid
    """
    settings = get_settings()

    # Get user from request state (set by auth middleware)
    if hasattr(request.state, "user"):
        return request.state.user

    # For development, allow test API key
    if settings.environment == "development":
        if api_key == settings.auth.test_api_key or api_key is None:
            return {
                "user_id": settings.auth.test_user,
                "api_key": api_key or "development",
                "roles": ["admin"]
            }

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # TODO: Implement actual API key validation
    # For now, accept any non-empty key in development
    if settings.environment == "development" and api_key:
        return {
            "user_id": f"user_{api_key[:8]}",
            "api_key": api_key,
            "roles": ["user"]
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )


async def get_document_service():
    """Get document service instance"""
    return ServiceFactory.create(ServiceType.DOCUMENT)


async def get_pdf_service():
    """Get PDF service instance"""
    return ServiceFactory.create(ServiceType.PDF)


async def get_llm_service():
    """Get LLM service instance"""
    return ServiceFactory.create(ServiceType.LLM)


async def get_storage():
    """Get storage instance"""
    return StorageFactory.get_default()


class PaginationParams:
    """Common pagination parameters"""

    def __init__(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ):
        """Initialize pagination parameters

        Args:
            limit: Maximum number of items to return (1-100)
            offset: Number of items to skip
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
        """
        # Validate limit
        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        # Validate offset
        if offset < 0:
            offset = 0

        # Validate sort order
        if sort_order not in ["asc", "desc"]:
            sort_order = "asc"

        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.sort_order = sort_order

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "limit": self.limit,
            "offset": self.offset,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order
        }


async def get_pagination(
    limit: int = 10,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: str = "asc"
) -> PaginationParams:
    """Get pagination parameters

    Args:
        limit: Maximum number of items to return
        offset: Number of items to skip
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)

    Returns:
        PaginationParams object
    """
    return PaginationParams(limit, offset, sort_by, sort_order)


async def verify_trace_context(request: Request) -> Dict[str, str]:
    """Extract and verify W3C trace context from request

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with trace_id and span_id
    """
    trace_context = {}

    # Get from request state (set by telemetry middleware)
    if hasattr(request.state, "trace_id"):
        trace_context["trace_id"] = request.state.trace_id
    if hasattr(request.state, "span_id"):
        trace_context["span_id"] = request.state.span_id

    # Get from headers if not in state
    if not trace_context.get("trace_id"):
        traceparent = request.headers.get("traceparent")
        if traceparent:
            # Parse W3C traceparent header
            parts = traceparent.split("-")
            if len(parts) >= 3:
                trace_context["trace_id"] = parts[1]
                trace_context["span_id"] = parts[2]

    return trace_context


async def get_transcription_service():
    """Get transcription service instance"""
    return ServiceFactory.create(ServiceType.TRANSCRIPTION)


async def get_web_scraping_service():
    """Get web scraping service instance"""
    return ServiceFactory.create(ServiceType.WEB_SCRAPING)


async def verify_api_key_ws(api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Verify API key for WebSocket connections

    Args:
        api_key: API key from query parameter

    Returns:
        User information dictionary or None if invalid
    """
    settings = get_settings()

    # For development, allow test API key or no key
    if settings.environment == "development":
        if api_key == settings.auth.test_api_key or api_key is None:
            return {
                "user_id": settings.auth.test_user,
                "api_key": api_key or "development",
                "roles": ["admin"]
            }
        # Accept any non-empty key in development
        if api_key:
            return {
                "user_id": f"user_{api_key[:8]}",
                "api_key": api_key,
                "roles": ["user"]
            }

    # In production, require valid API key
    if not api_key:
        return None

    # TODO: Implement actual API key validation
    return None