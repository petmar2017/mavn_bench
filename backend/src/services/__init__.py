"""Services module for Mavn Bench"""

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from .document_service import DocumentService
from .pdf_service import PDFService
from .llm_service import LLMService, LLMProvider, Entity
from .transcription_service import TranscriptionService
from .web_scraping_service import WebScrapingService

__all__ = [
    # Base classes
    "BaseService",

    # Factory
    "ServiceFactory",
    "ServiceType",

    # Services
    "DocumentService",
    "PDFService",
    "LLMService",
    "TranscriptionService",
    "WebScrapingService",

    # Supporting classes
    "LLMProvider",
    "Entity",
]