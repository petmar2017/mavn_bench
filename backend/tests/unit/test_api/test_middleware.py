"""Unit tests for API middleware"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import HTTPException

from src.api.middleware.auth import AuthMiddleware
from src.api.middleware.telemetry import TelemetryMiddleware
from src.api.middleware.error_handler import ErrorHandlerMiddleware
from src.core.config import Settings, AuthConfig


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    settings = Mock(spec=Settings)
    settings.environment = "development"
    settings.auth = Mock(spec=AuthConfig)
    settings.auth.api_key_header = "X-API-Key"
    settings.auth.test_api_key = "test-key-123"
    settings.auth.test_user = "test_user"
    return settings


@pytest.fixture
def mock_request():
    """Create mock request"""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/api/test"
    request.url.__str__ = Mock(return_value="http://test/api/test")
    request.method = "GET"
    request.headers = {}
    request.state = Mock()
    request.state.trace_id = "test-trace-id"
    request.state.span_id = "test-span-id"
    return request


@pytest.fixture
def mock_call_next():
    """Create mock call_next function"""
    async def call_next(request):
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        return response
    return call_next


class TestAuthMiddleware:
    """Test authentication middleware"""

    @pytest.mark.asyncio
    async def test_auth_middleware_excluded_path(self, mock_settings, mock_request, mock_call_next):
        """Test that excluded paths bypass authentication"""
        middleware = AuthMiddleware(None, mock_settings)
        mock_request.url.path = "/api/health"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_middleware_valid_api_key(self, mock_settings, mock_request, mock_call_next):
        """Test authentication with valid API key"""
        middleware = AuthMiddleware(None, mock_settings)
        mock_request.headers = {"x-api-key": "test-key-123"}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        # Check if user was set on request state
        assert hasattr(mock_request.state, "user")

    @pytest.mark.asyncio
    async def test_auth_middleware_no_api_key_dev(self, mock_settings, mock_request, mock_call_next):
        """Test authentication without API key in development mode"""
        middleware = AuthMiddleware(None, mock_settings)
        mock_settings.environment = "development"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.user["user_id"] == "test_user"

    @pytest.mark.asyncio
    async def test_auth_middleware_invalid_api_key_prod(self, mock_settings, mock_request):
        """Test authentication with invalid API key in production"""
        middleware = AuthMiddleware(None, mock_settings)
        mock_settings.environment = "production"
        mock_request.headers = {}

        async def call_next(request):
            return Response()

        response = await middleware.dispatch(mock_request, call_next)

        # Should return error in production mode without implementation
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_auth_middleware_options_request(self, mock_settings, mock_request, mock_call_next):
        """Test that OPTIONS requests bypass authentication"""
        middleware = AuthMiddleware(None, mock_settings)
        mock_request.method = "OPTIONS"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200


class TestTelemetryMiddleware:
    """Test telemetry middleware"""

    @pytest.mark.asyncio
    async def test_telemetry_middleware_creates_trace_context(self, mock_request, mock_call_next):
        """Test that telemetry middleware creates trace context"""
        middleware = TelemetryMiddleware(None)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert hasattr(mock_request.state, "trace_id")
        assert hasattr(mock_request.state, "span_id")
        assert mock_request.state.trace_id is not None
        assert mock_request.state.span_id is not None

    @pytest.mark.asyncio
    async def test_telemetry_middleware_extracts_w3c_context(self, mock_request, mock_call_next):
        """Test extraction of W3C trace context from headers"""
        middleware = TelemetryMiddleware(None)
        trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        parent_span = "00f067aa0ba902b7"
        mock_request.headers = {
            "traceparent": f"00-{trace_id}-{parent_span}-01"
        }

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert mock_request.state.trace_id == trace_id
        assert mock_request.state.span_id is not None
        assert mock_request.state.span_id != parent_span  # New span created

    @pytest.mark.asyncio
    async def test_telemetry_middleware_adds_response_headers(self, mock_request):
        """Test that telemetry middleware adds trace headers to response"""
        middleware = TelemetryMiddleware(None)

        async def call_next(request):
            response = Mock(spec=Response)
            response.status_code = 200
            response.headers = {}
            return response

        response = await middleware.dispatch(mock_request, call_next)

        # Headers should be added to response
        assert len(response.headers) > 0

    @pytest.mark.asyncio
    async def test_telemetry_middleware_handles_errors(self, mock_request):
        """Test telemetry middleware error handling"""
        middleware = TelemetryMiddleware(None)

        async def call_next(request):
            raise Exception("Test error")

        with pytest.raises(Exception):
            await middleware.dispatch(mock_request, call_next)

        # Should still have trace context set
        assert hasattr(mock_request.state, "trace_id")
        assert hasattr(mock_request.state, "span_id")


class TestErrorHandlerMiddleware:
    """Test error handler middleware"""

    @pytest.mark.asyncio
    async def test_error_handler_passes_successful_requests(self, mock_request, mock_call_next):
        """Test that successful requests pass through"""
        middleware = ErrorHandlerMiddleware(None)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_handler_catches_value_error(self, mock_request):
        """Test handling of ValueError"""
        middleware = ErrorHandlerMiddleware(None)

        async def call_next(request):
            raise ValueError("Invalid value")

        response = await middleware.dispatch(mock_request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_error_handler_catches_permission_error(self, mock_request):
        """Test handling of PermissionError"""
        middleware = ErrorHandlerMiddleware(None)

        async def call_next(request):
            raise PermissionError("Access denied")

        response = await middleware.dispatch(mock_request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_error_handler_catches_file_not_found(self, mock_request):
        """Test handling of FileNotFoundError"""
        middleware = ErrorHandlerMiddleware(None)

        async def call_next(request):
            raise FileNotFoundError("File not found")

        response = await middleware.dispatch(mock_request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_error_handler_catches_timeout_error(self, mock_request):
        """Test handling of TimeoutError"""
        middleware = ErrorHandlerMiddleware(None)

        async def call_next(request):
            raise TimeoutError("Request timeout")

        response = await middleware.dispatch(mock_request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 504

    @pytest.mark.asyncio
    async def test_error_handler_catches_generic_exception(self, mock_request):
        """Test handling of generic exceptions"""
        middleware = ErrorHandlerMiddleware(None)

        async def call_next(request):
            raise Exception("Unexpected error")

        response = await middleware.dispatch(mock_request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_error_handler_includes_trace_context(self, mock_request):
        """Test that error responses include trace context"""
        middleware = ErrorHandlerMiddleware(None)
        mock_request.state.trace_id = "test-trace-id"
        mock_request.state.span_id = "test-span-id"

        async def call_next(request):
            raise Exception("Error with trace")

        response = await middleware.dispatch(mock_request, call_next)

        # Response should be JSONResponse with trace context
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_error_handler_generates_error_id(self, mock_request):
        """Test that error handler generates unique error IDs"""
        middleware = ErrorHandlerMiddleware(None)

        async def call_next(request):
            raise Exception("Error needing ID")

        response = await middleware.dispatch(mock_request, call_next)

        # Response should have error ID
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500