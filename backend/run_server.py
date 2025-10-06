#!/usr/bin/env python
"""Production-ready server startup script with consistent logging"""

import uvicorn
from src.core.config import get_settings
from src.core.uvicorn_config import get_uvicorn_log_config

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
        log_config=get_uvicorn_log_config()
    )
