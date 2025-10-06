"""Custom uvicorn logging configuration for consistent log formatting"""

import logging
import sys
from typing import Dict, Any

# ANSI color codes matching CentralizedLogger
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


class UvicornFormatter(logging.Formatter):
    """Custom formatter for uvicorn logs matching CentralizedLogger format"""

    def format(self, record):
        # Get levelname and service name
        levelname = record.levelname
        service_name = record.name

        # Add color and bold to level and service name
        if levelname in COLORS:
            color = COLORS[levelname]
            colored_level = f"{color}{BOLD}{levelname}{RESET}"
            colored_service = f"{color}{BOLD}{service_name}{RESET}"
        else:
            colored_level = levelname
            colored_service = service_name

        # Make message bold and white
        original_msg = record.getMessage()
        colored_msg = f"{WHITE}{BOLD}{original_msg}{RESET}"

        # Format: HH:MM:SS | LEVEL | SERVICE | MESSAGE
        formatted = f"%(asctime)s | {colored_level:21s} | {colored_service:20s} | {colored_msg}"

        # Create a new formatter with the custom format
        formatter = logging.Formatter(formatted, datefmt='%H:%M:%S')
        return formatter.format(record)


def get_uvicorn_log_config() -> Dict[str, Any]:
    """Get uvicorn logging configuration matching centralized logger format

    Returns:
        Logging configuration dict for uvicorn
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "src.core.uvicorn_config.UvicornFormatter",
            },
            "access": {
                "()": "src.core.uvicorn_config.UvicornFormatter",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }


def configure_otel_logging():
    """Configure OpenTelemetry SDK logging to use centralized format"""
    # Suppress or redirect OpenTelemetry export warnings
    otel_loggers = [
        'opentelemetry.exporter.otlp.proto.grpc.trace_exporter',
        'opentelemetry.exporter.otlp.proto.grpc.metric_exporter',
        'opentelemetry.sdk.trace.export',
        'opentelemetry.sdk.metrics.export',
    ]

    for logger_name in otel_loggers:
        logger = logging.getLogger(logger_name)
        # Set to WARNING to suppress transient connection errors
        logger.setLevel(logging.WARNING)

        # Add custom handler with our formatter
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(UvicornFormatter())
            logger.addHandler(handler)
