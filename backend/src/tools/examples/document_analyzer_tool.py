"""Example document tool with multiple service dependencies"""

from typing import Any, Dict, Optional

from ..base_tool import (BaseTool, ToolCapability, ToolCategory,
                         ToolExecutionContext, ToolMetadata, ToolType)
from ..tool_decorators import register_tool


@register_tool("document_analyzer")
class DocumentAnalyzerTool(BaseTool):
    """Document analysis tool with multiple dependencies

    This demonstrates:
    - Multiple service injection (document_service, llm_service, vector_search_service)
    - Hybrid tool type (uses multiple backends)
    - Complex workflow coordination
    """

    def __init__(
        self,
        name: str,
        document_service=None,
        llm_service=None,
        vector_search_service=None,
        **kwargs
    ):
        """Initialize with required services

        Args:
            name: Tool name
            document_service: Required document service
            llm_service: Required LLM service
            vector_search_service: Optional vector search service
            **kwargs: Additional configuration

        Raises:
            ValueError: If required services are not provided
        """
        super().__init__(
            name,
            document_service=document_service,
            llm_service=llm_service,
            vector_search_service=vector_search_service,
            **kwargs
        )

        if not self.document_service:
            raise ValueError("DocumentAnalyzerTool requires document_service")
        if not self.llm_service:
            raise ValueError("DocumentAnalyzerTool requires llm_service")

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        """Analyze document using multiple services

        Args:
            input_data: Must contain 'document_id'
            context: Execution context

        Returns:
            Dict with comprehensive document analysis
        """
        self.validate_input(input_data)

        doc_id = input_data.get("document_id")

        # Use injected document service to fetch document
        document = await self.document_service.get_document(
            doc_id, trace_id=context.trace_id if context else None
        )

        # Use injected LLM service for analysis
        summary = await self.llm_service.summarize(
            text=document.content.text, trace_id=context.trace_id if context else None
        )

        entities = await self.llm_service.extract_entities(
            text=document.content.text, trace_id=context.trace_id if context else None
        )

        result = {
            "document_id": doc_id,
            "document_type": document.metadata.document_type,
            "summary": summary,
            "entities": entities,
            "word_count": len(document.content.text.split()),
        }

        # Optionally use vector search if available
        if self.vector_search_service:
            similar_docs = await self.vector_search_service.find_similar(
                document_id=doc_id,
                limit=5,
                trace_id=context.trace_id if context else None,
            )
            result["similar_documents"] = [doc["id"] for doc in similar_docs]

        return result

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            id="document_analyzer",
            name="Document Analyzer",
            description="Comprehensive document analysis using multiple services",
            version="1.0.0",
            category=ToolCategory.ANALYSIS,
            capabilities=[
                ToolCapability.TEXT_ANALYSIS,
                ToolCapability.ENTITY_RECOGNITION,
                ToolCapability.SUMMARIZATION,
                ToolCapability.SEMANTIC_SEARCH,
                ToolCapability.DATA_EXTRACTION,
            ],
            tool_type=ToolType.HYBRID,
            input_schema={
                "document_id": {
                    "type": "str",
                    "required": True,
                    "description": "ID of document to analyze",
                }
            },
            output_schema={
                "document_id": {"type": "str", "description": "Analyzed document ID"},
                "document_type": {"type": "str", "description": "Type of document"},
                "summary": {"type": "str", "description": "Document summary"},
                "entities": {"type": "list", "description": "Extracted entities"},
                "word_count": {"type": "int", "description": "Number of words"},
                "similar_documents": {
                    "type": "list",
                    "description": "IDs of similar documents",
                },
            },
            requires_llm=True,
            execution_time_estimate="medium",
            is_async=True,
            examples=[
                {
                    "input": {"document_id": "doc_123"},
                    "output": {
                        "document_id": "doc_123",
                        "document_type": "pdf",
                        "summary": "Document summary...",
                        "entities": ["Entity1", "Entity2"],
                        "word_count": 1500,
                        "similar_documents": ["doc_124", "doc_125"],
                    },
                }
            ],
        )
