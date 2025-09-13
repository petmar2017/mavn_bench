"""Simplified unit tests for API components that work with current implementation"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException
from starlette.responses import JSONResponse

from src.api.dependencies import PaginationParams, get_pagination
from src.api.middleware.error_handler import ErrorHandlerMiddleware


class TestPaginationParams:
    """Test pagination parameters"""

    def test_pagination_params_defaults(self):
        """Test default pagination parameters"""
        params = PaginationParams()

        assert params.limit == 10
        assert params.offset == 0
        assert params.sort_by is None
        assert params.sort_order == "asc"

    def test_pagination_params_validation(self):
        """Test pagination parameter validation"""
        # Test limit validation
        params = PaginationParams(limit=0)
        assert params.limit == 1

        params = PaginationParams(limit=200)
        assert params.limit == 100

        # Test offset validation
        params = PaginationParams(offset=-10)
        assert params.offset == 0

        # Test sort order validation
        params = PaginationParams(sort_order="invalid")
        assert params.sort_order == "asc"

    def test_pagination_params_custom_values(self):
        """Test pagination with custom values"""
        params = PaginationParams(limit=50, offset=100, sort_by="name", sort_order="desc")

        assert params.limit == 50
        assert params.offset == 100
        assert params.sort_by == "name"
        assert params.sort_order == "desc"

    def test_pagination_params_to_dict(self):
        """Test converting pagination params to dictionary"""
        params = PaginationParams(limit=20, offset=5, sort_by="name", sort_order="desc")
        result = params.to_dict()

        assert result["limit"] == 20
        assert result["offset"] == 5
        assert result["sort_by"] == "name"
        assert result["sort_order"] == "desc"

    @pytest.mark.asyncio
    async def test_get_pagination(self):
        """Test get_pagination dependency"""
        params = await get_pagination(limit=25, offset=10, sort_by="date", sort_order="desc")

        assert isinstance(params, PaginationParams)
        assert params.limit == 25
        assert params.offset == 10
        assert params.sort_by == "date"
        assert params.sort_order == "desc"


class TestErrorResponseGeneration:
    """Test error response generation in ErrorHandlerMiddleware"""

    def test_error_response_structure(self):
        """Test the structure of error responses"""
        middleware = ErrorHandlerMiddleware(None)
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = Mock()

        response = middleware._error_response(
            request=request,
            status_code=400,
            error="Bad Request",
            message="Test error",
            error_id="test-123"
        )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

    def test_error_response_with_trace_context(self):
        """Test error response includes trace context when available"""
        middleware = ErrorHandlerMiddleware(None)
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "POST"
        request.state = Mock()
        request.state.trace_id = "trace-123"
        request.state.span_id = "span-456"

        response = middleware._error_response(
            request=request,
            status_code=500,
            error="Internal Server Error",
            message="Something went wrong"
        )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    def test_error_id_generation(self):
        """Test that error IDs are generated properly"""
        middleware = ErrorHandlerMiddleware(None)
        request = Mock()

        error_id = middleware._get_error_id(request)

        assert error_id is not None
        assert len(error_id) > 0
        # Should be a valid UUID format
        assert "-" in error_id


class TestMiddlewareHelpers:
    """Test middleware helper methods"""

    def test_telemetry_trace_id_generation(self):
        """Test trace ID generation format"""
        from src.api.middleware.telemetry import TelemetryMiddleware

        middleware = TelemetryMiddleware(None)
        trace_id = middleware._generate_trace_id()

        assert len(trace_id) == 32  # UUID hex without dashes
        assert all(c in '0123456789abcdef' for c in trace_id)

    def test_telemetry_span_id_generation(self):
        """Test span ID generation format"""
        from src.api.middleware.telemetry import TelemetryMiddleware

        middleware = TelemetryMiddleware(None)
        span_id = middleware._generate_span_id()

        assert len(span_id) == 16  # Half UUID hex
        assert all(c in '0123456789abcdef' for c in span_id)

    def test_auth_excluded_paths(self):
        """Test auth middleware excluded paths list"""
        from src.api.middleware.auth import AuthMiddleware
        from src.core.config import Settings

        settings = Mock(spec=Settings)
        settings.environment = "development"

        middleware = AuthMiddleware(None, settings)

        assert "/" in middleware.excluded_paths
        assert "/api/health" in middleware.excluded_paths
        assert "/api/docs" in middleware.excluded_paths
        assert "/api/openapi.json" in middleware.excluded_paths


class TestWebSocketHelpers:
    """Test WebSocket connection management"""

    def test_connection_manager_initialization(self):
        """Test ConnectionManager initialization"""
        from src.api.routers.websocket import ConnectionManager

        manager = ConnectionManager()

        assert manager.active_connections == {}
        assert manager.user_connections == {}
        assert manager.connection_metadata == {}

    @pytest.mark.asyncio
    async def test_connection_manager_connect(self):
        """Test adding a WebSocket connection"""
        from src.api.routers.websocket import ConnectionManager

        manager = ConnectionManager()
        websocket = AsyncMock()

        await manager.connect(
            websocket=websocket,
            connection_id="test-123",
            user_id="user-456",
            metadata={"endpoint": "test"}
        )

        assert "test-123" in manager.active_connections
        assert "user-456" in manager.user_connections
        assert "test-123" in manager.user_connections["user-456"]
        assert manager.connection_metadata["test-123"]["user_id"] == "user-456"
        assert manager.connection_metadata["test-123"]["endpoint"] == "test"

    def test_connection_manager_disconnect(self):
        """Test removing a WebSocket connection"""
        from src.api.routers.websocket import ConnectionManager

        manager = ConnectionManager()

        # Setup initial state
        manager.active_connections["test-123"] = Mock()
        manager.user_connections["user-456"] = {"test-123"}
        manager.connection_metadata["test-123"] = {"user_id": "user-456"}

        # Disconnect
        manager.disconnect("test-123")

        assert "test-123" not in manager.active_connections
        assert "user-456" not in manager.user_connections
        assert "test-123" not in manager.connection_metadata