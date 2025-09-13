"""Base service class with OpenTelemetry integration"""

from contextlib import contextmanager
from typing import Optional, Dict, Any
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import asyncio
from functools import wraps

from ..core.logger import CentralizedLogger
from ..core.config import get_settings

class BaseService:
    """Base service class with automatic tracing and logging"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.tracer = trace.get_tracer(service_name)
        self.logger = CentralizedLogger(service_name)
        self.settings = get_settings()
    
    @contextmanager
    def traced_operation(self, operation_name: str, **attributes):
        """Context manager for traced operations"""
        with self.tracer.start_as_current_span(operation_name) as span:
            # Set common attributes
            span.set_attributes({
                "service.name": self.service_name,
                "operation.name": operation_name,
                **attributes
            })
            
            try:
                self.logger.info(f"Starting {operation_name}", 
                               extra={"attributes": attributes})
                yield span
                span.set_status(Status(StatusCode.OK))
                self.logger.info(f"Completed {operation_name}")
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                self.logger.error(f"Error in {operation_name}: {str(e)}", 
                                exc_info=True)
                raise
    
    def trace_async(self, operation_name: str = None):
        """Decorator for async methods with automatic tracing"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                op_name = operation_name or f"{self.service_name}.{func.__name__}"
                with self.traced_operation(op_name, **kwargs):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    async def validate_api_key(self, api_key: str, user_id: str, session_id: str) -> bool:
        """Validate API key and set trace context"""
        with self.traced_operation("validate_api_key",
                                  user_id=user_id,
                                  session_id=session_id):
            # Check for test mode
            if api_key == self.settings.auth.test_api_key:
                self.logger.info(f"Test mode authentication for user: {user_id}")
                return True
            
            # TODO: Implement real API key validation
            return False
    
    async def with_timeout(self, coro, timeout_seconds: int = 30):
        """Execute coroutine with timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            self.logger.error(f"Operation timed out after {timeout_seconds} seconds")
            raise
