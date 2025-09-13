"""Tests for ServiceFactory"""

import pytest
from typing import Dict, Any

from src.services.service_factory import ServiceFactory, ServiceType
from src.services.base_service import BaseService
from src.services.document_service import DocumentService
from src.services.pdf_service import PDFService
from src.services.llm_service import LLMService


class TestServiceFactory:
    """Test suite for ServiceFactory"""

    @pytest.fixture(autouse=True)
    def cleanup_factory(self):
        """Clean up factory instances after each test"""
        yield
        ServiceFactory.clear_instances()

    def test_register_service(self):
        """Test registering a service class"""
        class TestService(BaseService):
            def __init__(self):
                super().__init__("TestService")

            async def health_check(self) -> Dict[str, Any]:
                return {"status": "healthy"}

        # Register service
        test_type = "test_service"
        ServiceFactory.register(test_type, TestService)

        # Verify registration
        assert test_type in ServiceFactory._services
        assert ServiceFactory._services[test_type] == TestService

    def test_create_document_service(self, temp_dir):
        """Test creating a DocumentService instance"""
        service = ServiceFactory.create(ServiceType.DOCUMENT)

        assert isinstance(service, DocumentService)
        assert service is not None

    def test_create_pdf_service(self):
        """Test creating a PDFService instance"""
        service = ServiceFactory.create(ServiceType.PDF)

        assert isinstance(service, PDFService)
        assert service is not None

    def test_create_llm_service(self):
        """Test creating an LLMService instance"""
        service = ServiceFactory.create(ServiceType.LLM)

        assert isinstance(service, LLMService)
        assert service is not None

    def test_singleton_pattern(self):
        """Test that singleton pattern works correctly"""
        # Create first instance
        service1 = ServiceFactory.create(ServiceType.DOCUMENT, singleton=True)

        # Create second instance with same type
        service2 = ServiceFactory.create(ServiceType.DOCUMENT, singleton=True)

        # Should be the same instance
        assert service1 is service2

    def test_non_singleton_creation(self):
        """Test creating non-singleton instances"""
        # Create first instance
        service1 = ServiceFactory.create(ServiceType.PDF, singleton=False)

        # Create second instance
        service2 = ServiceFactory.create(ServiceType.PDF, singleton=False)

        # Should be different instances
        assert service1 is not service2

    def test_unknown_service_type(self):
        """Test creating unknown service type raises error"""
        with pytest.raises(ValueError, match="Unknown service type"):
            ServiceFactory.create("unknown_type")

    def test_get_all_instances(self):
        """Test getting all singleton instances"""
        # Create some services
        doc_service = ServiceFactory.create(ServiceType.DOCUMENT)
        pdf_service = ServiceFactory.create(ServiceType.PDF)

        # Get all instances
        instances = ServiceFactory.get_all_instances()

        assert ServiceType.DOCUMENT in instances
        assert ServiceType.PDF in instances
        assert instances[ServiceType.DOCUMENT] is doc_service
        assert instances[ServiceType.PDF] is pdf_service

    def test_clear_instances(self):
        """Test clearing all singleton instances"""
        # Create some services
        ServiceFactory.create(ServiceType.DOCUMENT)
        ServiceFactory.create(ServiceType.PDF)

        # Verify they exist
        instances = ServiceFactory.get_all_instances()
        assert len(instances) > 0

        # Clear instances
        ServiceFactory.clear_instances()

        # Verify they're cleared
        instances = ServiceFactory.get_all_instances()
        assert len(instances) == 0

    def test_get_available_services(self):
        """Test getting list of available service types"""
        services = ServiceFactory.get_available_services()

        # Should include registered services
        assert ServiceType.DOCUMENT in services
        assert ServiceType.PDF in services
        assert ServiceType.LLM in services

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test running health checks on all services"""
        # Create some services
        ServiceFactory.create(ServiceType.DOCUMENT)
        ServiceFactory.create(ServiceType.PDF)

        # Run health checks
        health_status = await ServiceFactory.health_check_all()

        assert ServiceType.DOCUMENT in health_status
        assert ServiceType.PDF in health_status
        assert health_status[ServiceType.DOCUMENT]["status"] in ["healthy", "degraded", "error"]
        assert health_status[ServiceType.PDF]["status"] in ["healthy", "degraded", "error"]

    def test_dependency_injection(self, temp_dir):
        """Test that storage is injected if not provided"""
        # Create service without providing storage
        service = ServiceFactory.create(ServiceType.DOCUMENT)

        # Should have storage injected
        assert hasattr(service, 'storage')
        assert service.storage is not None

    def test_create_with_custom_kwargs(self):
        """Test creating service with custom kwargs"""
        from src.services.llm_service import LLMProvider

        # Create LLM service with custom provider
        service = ServiceFactory.create(
            ServiceType.LLM,
            singleton=False,
            provider=LLMProvider.ANTHROPIC
        )

        assert service.provider == LLMProvider.ANTHROPIC

    def test_service_registration_persistence(self):
        """Test that registered services persist across operations"""
        # Check initial registered services
        initial_count = len(ServiceFactory.get_available_services())

        # Create and clear instances
        ServiceFactory.create(ServiceType.DOCUMENT)
        ServiceFactory.clear_instances()

        # Registration should still exist
        final_count = len(ServiceFactory.get_available_services())
        assert initial_count == final_count