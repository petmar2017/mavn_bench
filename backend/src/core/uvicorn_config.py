"""Custom uvicorn logging configuration for consistent log formatting"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any
from opentelemetry import trace


class UvicornJsonFormatter(logging.Formatter):
    """JSON formatter for uvicorn logs matching CentralizedLogger format"""

    def format(self, record):
        # Get current trace context if available
        trace_id = "no-trace"
        span_id = "no-span"

        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            trace_id = format(span_context.trace_id, '032x')
            span_id = format(span_context.span_id, '016x')

        # Build JSON log object matching CentralizedLogger format
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'service': record.name,
            'message': record.getMessage(),
            'trace_id': trace_id,
            'span_id': span_id,
            'user_id': getattr(record, 'user_id', None),
            'session_id': getattr(record, 'session_id', None),
        }

        return json.dumps(log_obj)


class UvicornConsoleFormatter(logging.Formatter):
    """Console formatter for uvicorn logs with colors matching CentralizedLogger"""

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
    WHITE = '\033[37m'

    def format(self, record):
        # Get levelname and service name
        levelname = record.levelname
        service_name = record.name

        # Add color and bold to level and service name
        if levelname in self.COLORS:
            color = self.COLORS[levelname]
            colored_level = f"{color}{self.BOLD}{levelname}{self.RESET}"
            colored_service = f"{color}{self.BOLD}{service_name}{self.RESET}"
        else:
            colored_level = levelname
            colored_service = service_name

        # Make message bold and white
        original_msg = record.getMessage()
        colored_msg = f"{self.WHITE}{self.BOLD}{original_msg}{self.RESET}"

        # Format: HH:MM:SS | LEVEL | SERVICE | MESSAGE
        return f"{self.formatTime(record, '%H:%M:%S')} | {colored_level:21s} | {colored_service:20s} | {colored_msg}"


def get_uvicorn_log_config() -> Dict[str, Any]:
    """Get uvicorn logging configuration matching CentralizedLogger pattern

    Outputs to both stdout (console) and stderr (JSON) like CentralizedLogger

    Returns:
        Logging configuration dict for uvicorn with dual output
    """
    # Check if JSON-only mode is enabled
    json_only = os.getenv('MAVN_LOG_JSON_ONLY', 'false').lower() == 'true'

    if json_only:
        # JSON-only mode for production
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "src.core.uvicorn_config.UvicornJsonFormatter",
                },
            },
            "handlers": {
                "json": {
                    "formatter": "json",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["json"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"handlers": ["json"], "level": "INFO", "propagate": False},
                "uvicorn.access": {"handlers": ["json"], "level": "INFO", "propagate": False},
            },
        }
    else:
        # Dual output mode for development (matches CentralizedLogger)
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "()": "src.core.uvicorn_config.UvicornConsoleFormatter",
                },
                "json": {
                    "()": "src.core.uvicorn_config.UvicornJsonFormatter",
                },
            },
            "handlers": {
                "console": {
                    "formatter": "console",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "json": {
                    "formatter": "json",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["console", "json"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"handlers": ["console", "json"], "level": "INFO", "propagate": False},
                "uvicorn.access": {"handlers": ["console", "json"], "level": "INFO", "propagate": False},
            },
        }


def configure_otel_logging():
    """Configure OpenTelemetry SDK logging to use JSON format or suppress"""
    # Suppress or redirect OpenTelemetry export warnings
    otel_loggers = [
        'opentelemetry.exporter.otlp.proto.grpc.trace_exporter',
        'opentelemetry.exporter.otlp.proto.grpc.metric_exporter',
        'opentelemetry.sdk.trace.export',
        'opentelemetry.sdk.metrics.export',
    ]

    for logger_name in otel_loggers:
        logger = logging.getLogger(logger_name)
        # Set to ERROR to suppress transient connection warnings
        logger.setLevel(logging.ERROR)

        # Add JSON formatter if no handlers exist
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(UvicornJsonFormatter())
            logger.addHandler(handler)
