"""Unit tests for API dependencies"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, Request

from src.api.dependencies import (
    get_current_user,
    PaginationParams,
    get_pagination,
    verify_trace_context,
    verify_api_key_ws
)


@pytest.fixture
def mock_request():
    """Create mock request"""
    request = Mock(spec=Request)
    request.state = Mock()
    request.headers = {}
    return request


class TestGetCurrentUser:
    """Test get_current_user dependency"""

    @pytest.mark.asyncio
    async def test_get_user_from_request_state(self, mock_request):
        """Test getting user from request state"""
        mock_request.state.user = {"user_id": "existing_user", "roles": ["admin"]}

        with patch('src.api.dependencies.get_settings'):
            user = await get_current_user(mock_request, None)

        assert user["user_id"] == "existing_user"
        assert "admin" in user["roles"]

    @pytest.mark.asyncio
    async def test_get_user_dev_mode_no_key(self, mock_request):
        """Test getting user in development mode without API key"""
        mock_settings = Mock()
        mock_settings.environment = "development"
        mock_settings.auth = Mock()
        mock_settings.auth.test_user = "test_user"
        mock_settings.auth.test_api_key = "test-key"

        with patch('src.api.dependencies.get_settings', return_value=mock_settings):
            user = await get_current_user(mock_request, None)

        assert user["user_id"] == "test_user"
        assert user["api_key"] == "development"
        assert "admin" in user["roles"]

    @pytest.mark.asyncio
    async def test_get_user_dev_mode_test_key(self, mock_request):
        """Test getting user with test API key in development"""
        mock_settings = Mock()
        mock_settings.environment = "development"
        mock_settings.auth = Mock()
        mock_settings.auth.test_api_key = "test-key"
        mock_settings.auth.test_user = "test_user"

        with patch('src.api.dependencies.get_settings', return_value=mock_settings):
            user = await get_current_user(mock_request, "test-key")

        assert user["user_id"] == "test_user"
        assert user["api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_get_user_dev_mode_any_key(self, mock_request):
        """Test getting user with any API key in development"""
        mock_settings = Mock()
        mock_settings.environment = "development"
        mock_settings.auth = Mock()
        mock_settings.auth.test_api_key = "test-key"

        with patch('src.api.dependencies.get_settings', return_value=mock_settings):
            user = await get_current_user(mock_request, "any-key-123")

        assert user["user_id"] == "user_any-key-"
        assert user["api_key"] == "any-key-123"
        assert "user" in user["roles"]

    @pytest.mark.asyncio
    async def test_get_user_no_key_required(self, mock_request):
        """Test that missing API key raises exception when required"""
        mock_settings = Mock()
        mock_settings.environment = "production"

        with patch('src.api.dependencies.get_settings', return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, None)

            assert exc_info.value.status_code == 401
            assert "API key required" in exc_info.value.detail


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


class TestVerifyTraceContext:
    """Test trace context verification"""

    @pytest.mark.asyncio
    async def test_verify_trace_from_state(self, mock_request):
        """Test getting trace context from request state"""
        mock_request.state.trace_id = "state-trace-id"
        mock_request.state.span_id = "state-span-id"

        context = await verify_trace_context(mock_request)

        assert context["trace_id"] == "state-trace-id"
        assert context["span_id"] == "state-span-id"

    @pytest.mark.asyncio
    async def test_verify_trace_from_w3c_header(self, mock_request):
        """Test extracting trace context from W3C traceparent header"""
        delattr(mock_request.state, "trace_id")
        delattr(mock_request.state, "span_id")
        mock_request.headers = {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        }

        context = await verify_trace_context(mock_request)

        assert context["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
        assert context["span_id"] == "00f067aa0ba902b7"

    @pytest.mark.asyncio
    async def test_verify_trace_empty(self, mock_request):
        """Test trace context when no trace information available"""
        delattr(mock_request.state, "trace_id")
        delattr(mock_request.state, "span_id")

        context = await verify_trace_context(mock_request)

        assert context == {}


class TestVerifyApiKeyWS:
    """Test WebSocket API key verification"""

    @pytest.mark.asyncio
    async def test_verify_ws_key_dev_no_key(self):
        """Test WebSocket auth in development without key"""
        with patch('src.api.dependencies.get_settings') as mock_settings:
            mock_settings.return_value.environment = "development"
            mock_settings.return_value.auth.test_user = "test_user"
            mock_settings.return_value.auth.test_api_key = "test-key"

            user = await verify_api_key_ws(None)

        assert user["user_id"] == "test_user"
        assert "admin" in user["roles"]

    @pytest.mark.asyncio
    async def test_verify_ws_key_dev_test_key(self):
        """Test WebSocket auth with test key"""
        with patch('src.api.dependencies.get_settings') as mock_settings:
            mock_settings.return_value.environment = "development"
            mock_settings.return_value.auth.test_api_key = "test-key"
            mock_settings.return_value.auth.test_user = "test_user"

            user = await verify_api_key_ws("test-key")

        assert user["user_id"] == "test_user"
        assert user["api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_verify_ws_key_dev_any_key(self):
        """Test WebSocket auth with any key in development"""
        with patch('src.api.dependencies.get_settings') as mock_settings:
            mock_settings.return_value.environment = "development"
            mock_settings.return_value.auth.test_api_key = "test-key"

            user = await verify_api_key_ws("some-key")

        assert user["user_id"] == "user_some-key"
        assert "user" in user["roles"]

    @pytest.mark.asyncio
    async def test_verify_ws_key_prod_no_key(self):
        """Test WebSocket auth in production without key"""
        with patch('src.api.dependencies.get_settings') as mock_settings:
            mock_settings.return_value.environment = "production"

            user = await verify_api_key_ws(None)

        assert user is None

    @pytest.mark.asyncio
    async def test_verify_ws_key_prod_with_key(self):
        """Test WebSocket auth in production with key (not implemented)"""
        with patch('src.api.dependencies.get_settings') as mock_settings:
            mock_settings.return_value.environment = "production"

            user = await verify_api_key_ws("prod-key")

        # Not implemented yet
        assert user is None