"""Centralized logging with OpenTelemetry integration"""

import logging
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

class CentralizedLogger:
    """Central logger with trace context injection"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)

        # Get log level from environment or default to INFO
        # Using MAVN_LOG_LEVEL to avoid conflict with Pydantic settings
        log_level_str = os.getenv('MAVN_LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        self.logger.setLevel(log_level)
        
        # Console handler with human-readable format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(self._get_console_formatter())

        # JSON handler for observability platforms
        json_handler = logging.StreamHandler(sys.stderr)
        json_handler.setLevel(log_level)
        json_handler.setFormatter(self._get_json_formatter())

        self.logger.addHandler(console_handler)
        self.logger.addHandler(json_handler)
    
    def _get_console_formatter(self) -> logging.Formatter:
        """Human-readable console format with colors"""
        class ConsoleFormatter(logging.Formatter):
            # ANSI color codes
            COLORS = {
                'DEBUG': '\033[36m',    # Cyan
                'INFO': '\033[32m',     # Green
                'WARNING': '\033[33m',  # Yellow
                'ERROR': '\033[31m',    # Red
                'CRITICAL': '\033[35m', # Magenta
            }
            RESET = '\033[0m'
            BOLD = '\033[1m'
            WHITE = '\033[37m'     # White color for message

            def format(self, record):
                # Add default values for missing fields
                record.trace_id = getattr(record, 'trace_id', 'no-trace')
                record.span_id = getattr(record, 'span_id', 'no-span')
                record.user_id = getattr(record, 'user_id', None)
                record.session_id = getattr(record, 'session_id', None)

                # Store original values
                levelname = record.levelname
                service_name = record.name
                original_msg = record.msg

                # Add color and bold to both level name and service name
                if levelname in self.COLORS:
                    color = self.COLORS[levelname]
                    record.levelname = f"{color}{self.BOLD}{levelname}{self.RESET}"
                    record.name = f"{color}{self.BOLD}{service_name}{self.RESET}"

                # Make the message bold and white
                record.msg = f"{self.WHITE}{self.BOLD}{original_msg}{self.RESET}"

                # Format the message
                formatted = super().format(record)

                # Reset values for other handlers
                record.levelname = levelname
                record.name = service_name
                record.msg = original_msg
                return formatted

        return ConsoleFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%H:%M:%S'
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
        kwargs['extra'] = kwargs.get('extra', {})

        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            kwargs['extra']['trace_id'] = format(span_context.trace_id, '032x')
            kwargs['extra']['span_id'] = format(span_context.span_id, '016x')
        else:
            # Provide default values when no span is active
            kwargs['extra']['trace_id'] = 'no-trace'
            kwargs['extra']['span_id'] = 'no-span'

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
                # Only record if exc_info is an actual exception, not True
                exc_info = kwargs.get('exc_info')
                if exc_info and exc_info is not True and hasattr(exc_info, '__traceback__'):
                    span.record_exception(exc_info)
            span.set_status(Status(StatusCode.ERROR, message))
    
    def critical(self, message: str, **kwargs):
        kwargs = self._inject_trace_context(kwargs)
        self.logger.critical(message, **kwargs)
