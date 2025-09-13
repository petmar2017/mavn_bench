"""Telemetry middleware for W3C trace context propagation"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from ...core.logger import CentralizedLogger


logger = CentralizedLogger("TelemetryMiddleware")
tracer = trace.get_tracer(__name__)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware for OpenTelemetry trace context propagation"""

    async def dispatch(self, request: Request, call_next):
        """Process request with trace context

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with trace headers
        """
        # Extract or create trace context
        trace_id, span_id = self._extract_trace_context(request)

        # Store in request state for access in handlers
        request.state.trace_id = trace_id
        request.state.span_id = span_id

        # Create span for this request
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname,
                "http.target": request.url.path,
                "trace.id": trace_id,
                "span.id": span_id
            }
        ) as span:
            try:
                # Add user context if available
                if hasattr(request.state, "user"):
                    span.set_attribute("user.id", request.state.user.get("user_id"))

                # Process request
                response = await call_next(request)

                # Set span status based on response
                if response.status_code >= 400:
                    span.set_status(
                        Status(StatusCode.ERROR, f"HTTP {response.status_code}")
                    )
                else:
                    span.set_status(Status(StatusCode.OK))

                # Add response attributes
                span.set_attribute("http.status_code", response.status_code)

                # Add trace headers to response
                response.headers["X-Trace-Id"] = trace_id
                response.headers["X-Span-Id"] = span_id

                # Add W3C traceparent header
                trace_context = span.get_span_context()
                if trace_context.is_valid:
                    traceparent = f"00-{format(trace_context.trace_id, '032x')}-{format(trace_context.span_id, '016x')}-01"
                    response.headers["traceparent"] = traceparent

                logger.debug(
                    f"Request completed: {request.method} {request.url.path} "
                    f"Status: {response.status_code} "
                    f"Trace: {trace_id}"
                )

                return response

            except Exception as e:
                # Log error and set span status
                logger.error(f"Request failed: {str(e)}", exc_info=True)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    def _extract_trace_context(self, request: Request) -> tuple[str, str]:
        """Extract or create W3C trace context

        Args:
            request: Incoming request

        Returns:
            Tuple of (trace_id, span_id)
        """
        # Check for W3C traceparent header
        traceparent = request.headers.get("traceparent")
        if traceparent:
            try:
                # Parse W3C traceparent format: version-trace_id-span_id-flags
                parts = traceparent.split("-")
                if len(parts) >= 3:
                    trace_id = parts[1]
                    parent_span_id = parts[2]
                    # Generate new span ID for this request
                    span_id = self._generate_span_id()
                    logger.debug(f"Extracted trace context: {trace_id}/{span_id}")
                    return trace_id, span_id
            except Exception as e:
                logger.warning(f"Failed to parse traceparent header: {e}")

        # Check for custom trace headers
        trace_id = request.headers.get("X-Trace-Id")
        span_id = request.headers.get("X-Span-Id")

        # Generate new IDs if not present
        if not trace_id:
            trace_id = self._generate_trace_id()
            logger.debug(f"Generated new trace ID: {trace_id}")

        if not span_id:
            span_id = self._generate_span_id()

        return trace_id, span_id

    def _generate_trace_id(self) -> str:
        """Generate W3C compliant trace ID (32 hex chars)"""
        return uuid.uuid4().hex

    def _generate_span_id(self) -> str:
        """Generate W3C compliant span ID (16 hex chars)"""
        return uuid.uuid4().hex[:16]