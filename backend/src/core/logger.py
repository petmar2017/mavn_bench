"""Centralized logging with OpenTelemetry integration"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

class CentralizedLogger:
    """Central logger with trace context injection"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler with human-readable format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._get_console_formatter())
        
        # JSON handler for observability platforms
        json_handler = logging.StreamHandler(sys.stderr)
        json_handler.setFormatter(self._get_json_formatter())
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(json_handler)
    
    def _get_console_formatter(self) -> logging.Formatter:
        """Human-readable console format"""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _get_json_formatter(self) -> logging.Formatter:
        """JSON format for observability platforms"""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_obj = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': record.levelname,
                    'service': record.name,
                    'message': record.getMessage(),
                    'trace_id': getattr(record, 'trace_id', None),
                    'span_id': getattr(record, 'span_id', None),
                    'user_id': getattr(record, 'user_id', None),
                    'session_id': getattr(record, 'session_id', None),
                }
                return json.dumps(log_obj)
        return JsonFormatter()
    
    def _inject_trace_context(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Inject current trace context into log extras"""
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            kwargs['extra'] = kwargs.get('extra', {})
            kwargs['extra']['trace_id'] = format(span_context.trace_id, '032x')
            kwargs['extra']['span_id'] = format(span_context.span_id, '016x')
        return kwargs
    
    def debug(self, message: str, **kwargs):
        kwargs = self._inject_trace_context(kwargs)
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        kwargs = self._inject_trace_context(kwargs)
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        kwargs = self._inject_trace_context(kwargs)
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        kwargs = self._inject_trace_context(kwargs)
        self.logger.error(message, **kwargs)
        
        # Record exception in current span if available
        span = trace.get_current_span()
        if span and span.is_recording():
            if 'exc_info' in kwargs:
                span.record_exception(kwargs['exc_info'])
            span.set_status(Status(StatusCode.ERROR, message))
    
    def critical(self, message: str, **kwargs):
        kwargs = self._inject_trace_context(kwargs)
        self.logger.critical(message, **kwargs)
