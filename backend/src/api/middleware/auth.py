"""Authentication middleware for API key validation"""

from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...core.config import Settings
from ...core.logger import CentralizedLogger


logger = CentralizedLogger("AuthMiddleware")


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication"""

    def __init__(self, app, settings: Settings):
        """Initialize auth middleware

        Args:
            app: FastAPI application
            settings: Application settings
        """
        super().__init__(app)
        self.settings = settings
        self.excluded_paths = [
            "/",
            "/api/health",
            "/api/info",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json"
        ]

    async def dispatch(self, request: Request, call_next):
        """Process request for authentication

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from next handler or error response
        """
        # Skip auth for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get(self.settings.auth.api_key_header)

        # Validate API key
        if not api_key:
            # Allow no key in development mode for testing
            if self.settings.environment == "development":
                request.state.user = {
                    "user_id": self.settings.auth.test_user,
                    "api_key": "development",
                    "roles": ["admin"]
                }
                return await call_next(request)

            logger.warning(f"Missing API key for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "API key required"
                }
            )

        # Validate API key (simplified for now)
        if self.settings.environment == "development":
            # Accept test API key or any key in development
            if api_key == self.settings.auth.test_api_key:
                user = {
                    "user_id": self.settings.auth.test_user,
                    "api_key": api_key,
                    "roles": ["admin"]
                }
            else:
                user = {
                    "user_id": f"user_{api_key[:8] if len(api_key) >= 8 else api_key}",
                    "api_key": api_key,
                    "roles": ["user"]
                }
            request.state.user = user
        else:
            # TODO: Implement production API key validation
            # This would typically check against a database or auth service
            logger.error(f"API key validation not implemented for production")
            return JSONResponse(
                status_code=501,
                content={
                    "error": "Not Implemented",
                    "message": "Production authentication not yet implemented"
                }
            )

        # Log authenticated request
        logger.debug(
            f"Authenticated request: {request.method} {request.url.path} "
            f"by {request.state.user['user_id']}"
        )

        # Continue to next middleware/handler
        response = await call_next(request)
        return response