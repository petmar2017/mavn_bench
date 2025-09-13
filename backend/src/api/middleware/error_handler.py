"""Global error handling middleware"""

import traceback
from typing import Any, Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...core.logger import CentralizedLogger


logger = CentralizedLogger("ErrorHandler")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling"""

    async def dispatch(self, request: Request, call_next):
        """Process request with error handling

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response or error response
        """
        try:
            response = await call_next(request)
            return response

        except ValueError as e:
            # Handle validation errors
            logger.warning(f"Validation error: {str(e)}")
            return self._error_response(
                request,
                status_code=400,
                error="Bad Request",
                message=str(e)
            )

        except PermissionError as e:
            # Handle permission errors
            logger.warning(f"Permission denied: {str(e)}")
            return self._error_response(
                request,
                status_code=403,
                error="Forbidden",
                message="You don't have permission to access this resource"
            )

        except FileNotFoundError as e:
            # Handle not found errors
            logger.warning(f"Resource not found: {str(e)}")
            return self._error_response(
                request,
                status_code=404,
                error="Not Found",
                message=str(e)
            )

        except TimeoutError as e:
            # Handle timeout errors
            logger.error(f"Request timeout: {str(e)}")
            return self._error_response(
                request,
                status_code=504,
                error="Gateway Timeout",
                message="The request timed out"
            )

        except Exception as e:
            # Handle all other errors
            error_id = self._get_error_id(request)
            logger.error(
                f"Unhandled error [{error_id}]: {str(e)}",
                exc_info=True,
                extra={
                    "error_id": error_id,
                    "path": request.url.path,
                    "method": request.method,
                    "trace_id": getattr(request.state, "trace_id", None)
                }
            )

            # Don't expose internal errors in production
            if hasattr(request.app.state, "settings"):
                settings = request.app.state.settings
                if settings.environment == "production":
                    message = "An internal error occurred"
                    details = None
                else:
                    message = str(e)
                    details = {
                        "type": type(e).__name__,
                        "traceback": traceback.format_exc().split("\n")
                    }
            else:
                message = str(e)
                details = None

            return self._error_response(
                request,
                status_code=500,
                error="Internal Server Error",
                message=message,
                error_id=error_id,
                details=details
            )

    def _error_response(
        self,
        request: Request,
        status_code: int,
        error: str,
        message: str,
        error_id: str = None,
        details: Dict[str, Any] = None
    ) -> JSONResponse:
        """Create standardized error response

        Args:
            request: Request object
            status_code: HTTP status code
            error: Error type
            message: Error message
            error_id: Unique error ID
            details: Additional error details

        Returns:
            JSON error response
        """
        content = {
            "error": error,
            "message": message,
            "path": str(request.url.path),
            "method": request.method
        }

        # Add trace context if available
        if hasattr(request.state, "trace_id"):
            content["trace_id"] = request.state.trace_id
        if hasattr(request.state, "span_id"):
            content["span_id"] = request.state.span_id

        # Add error ID if provided
        if error_id:
            content["error_id"] = error_id

        # Add details if provided
        if details:
            content["details"] = details

        return JSONResponse(
            status_code=status_code,
            content=content
        )

    def _get_error_id(self, request: Request) -> str:
        """Generate unique error ID

        Args:
            request: Request object

        Returns:
            Error ID string
        """
        import uuid
        error_id = str(uuid.uuid4())
        return error_id