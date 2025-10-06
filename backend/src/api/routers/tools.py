"""API endpoints for document tool management and recommendations"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from opentelemetry import trace

from ...services.document_tools import (
    DocumentToolRegistry,
    DocumentToolType,
    DocumentToolCategory,
    DocumentToolCapability,
    initialize_document_tools
)
from ...services.service_factory import ServiceFactory, ServiceType
from ...models.document import DocumentMessage, DocumentType


router = APIRouter(prefix="/tools", tags=["tools"])
tracer = trace.get_tracer(__name__)


class ToolRecommendationRequest(BaseModel):
    """Request model for tool recommendations"""
    document_id: str = Field(..., description="ID of the document to get recommendations for")
    max_recommendations: int = Field(default=5, ge=1, le=20, description="Maximum number of recommendations")
    categories: Optional[List[DocumentToolCategory]] = Field(default=None, description="Filter by tool categories")
    capabilities: Optional[List[DocumentToolCapability]] = Field(default=None, description="Filter by capabilities")


class ToolExecutionRequest(BaseModel):
    """Request model for tool execution"""
    document_id: str = Field(..., description="ID of the document to process")
    tool_type: DocumentToolType = Field(..., description="Type of tool to execute")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Tool-specific parameters")


class ToolRecommendation(BaseModel):
    """Tool recommendation response model"""
    tool_type: str
    tool_name: str
    tool_icon: str
    tool_category: str
    score: float
    reasoning: str
    applicable: bool
    metadata: Dict[str, Any]


class ToolExecutionResult(BaseModel):
    """Tool execution result response model"""
    success: bool
    tool_type: str
    execution_time: float
    result: Dict[str, Any]
    error: Optional[str] = None


class ToolInfo(BaseModel):
    """Tool information response model"""
    id: str
    name: str
    description: str
    category: str
    icon: str
    version: str
    capabilities: List[str]
    supported_document_types: List[str]
    execution_time_estimate: str
    batch_capable: bool
    requires_llm: bool
    requires_vector_search: bool


async def get_document_service():
    """Dependency to get document service"""
    return ServiceFactory.create(ServiceType.DOCUMENT)


async def get_llm_service():
    """Dependency to get LLM service"""
    try:
        return ServiceFactory.create(ServiceType.LLM)
    except ValueError:
        return None


async def get_vector_search_service():
    """Dependency to get vector search service"""
    try:
        return ServiceFactory.create(ServiceType.VECTOR_SEARCH)
    except ValueError:
        return None


@router.get("/", response_model=Dict[str, Any])
async def list_tools():
    """Get information about all available document tools"""
    with tracer.start_as_current_span("list_tools"):
        try:
            tool_info = DocumentToolRegistry.get_tool_info()
            stats = DocumentToolRegistry.get_stats()

            return {
                "tools": tool_info,
                "statistics": stats
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.get("/categories", response_model=List[str])
async def list_tool_categories():
    """Get list of available tool categories"""
    with tracer.start_as_current_span("list_tool_categories"):
        return [category.value for category in DocumentToolCategory]


@router.get("/capabilities", response_model=List[str])
async def list_tool_capabilities():
    """Get list of available tool capabilities"""
    with tracer.start_as_current_span("list_tool_capabilities"):
        return [capability.value for capability in DocumentToolCapability]


@router.get("/{tool_type}", response_model=ToolInfo)
async def get_tool_info(tool_type: DocumentToolType):
    """Get detailed information about a specific tool"""
    with tracer.start_as_current_span("get_tool_info") as span:
        span.set_attribute("tool.type", tool_type.value)
        try:
            metadata = DocumentToolRegistry.get_tool_metadata(tool_type)
            if not metadata:
                raise HTTPException(status_code=404, detail=f"Tool {tool_type} not found")

            return ToolInfo(
                id=metadata.id,
                name=metadata.name,
                description=metadata.description,
                category=metadata.category.value,
                icon=metadata.icon,
                version=metadata.version,
                capabilities=[cap.value for cap in metadata.capabilities],
                supported_document_types=[dt.value for dt in metadata.supported_document_types],
                execution_time_estimate=metadata.execution_time_estimate,
                batch_capable=metadata.batch_capable,
                requires_llm=metadata.requires_llm,
                requires_vector_search=metadata.requires_vector_search
            )

        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=f"Failed to get tool info: {str(e)}")


@router.post("/recommendations", response_model=List[ToolRecommendation])
async def get_tool_recommendations(
    request: ToolRecommendationRequest,
    document_service=Depends(get_document_service),
    llm_service=Depends(get_llm_service),
    vector_search_service=Depends(get_vector_search_service)
):
    """Get tool recommendations for a specific document"""
    with tracer.start_as_current_span("get_tool_recommendations") as span:
        span.set_attribute("document.id", request.document_id)
        try:
            # Get the document
            document = await document_service.get_document(request.document_id)
            if not document:
                raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found")

            # Get recommendations
            recommendations = DocumentToolRegistry.get_recommendations_for_document(
                document=document,
                document_service=document_service,
                llm_service=llm_service,
                vector_search_service=vector_search_service,
                max_recommendations=request.max_recommendations
            )

            # Filter by categories if specified
            if request.categories:
                category_values = [cat.value for cat in request.categories]
                recommendations = [
                    rec for rec in recommendations
                    if rec["tool_category"] in category_values
                ]

            # Filter by capabilities if specified
            if request.capabilities:
                capability_values = [cap.value for cap in request.capabilities]
                filtered_recommendations = []
                for rec in recommendations:
                    tool_metadata = DocumentToolRegistry.get_tool_metadata(
                        DocumentToolType(rec["tool_type"])
                    )
                    if tool_metadata:
                        tool_capabilities = [cap.value for cap in tool_metadata.capabilities]
                        if any(cap in tool_capabilities for cap in capability_values):
                            filtered_recommendations.append(rec)
                recommendations = filtered_recommendations

            # Convert to response model
            return [
                ToolRecommendation(
                    tool_type=rec["tool_type"],
                    tool_name=rec["tool_name"],
                    tool_icon=rec["tool_icon"],
                    tool_category=rec["tool_category"],
                    score=rec["score"],
                    reasoning=rec["reasoning"],
                    applicable=rec["applicable"],
                    metadata=rec["metadata"]
                )
                for rec in recommendations
            ]

        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.post("/execute", response_model=ToolExecutionResult)
async def execute_tool(
    request: ToolExecutionRequest,
    document_service=Depends(get_document_service),
    llm_service=Depends(get_llm_service),
    vector_search_service=Depends(get_vector_search_service)
):
    """Execute a tool on a specific document"""
    with tracer.start_as_current_span("execute_tool") as span:
        span.set_attribute("document.id", request.document_id)
        span.set_attribute("tool.type", request.tool_type.value)
        import time

        start_time = time.time()

        try:
            # Get the document
            document = await document_service.get_document(request.document_id)
            if not document:
                raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found")

            # Create tool instance
            tool = DocumentToolRegistry.create(
                tool_type=request.tool_type,
                document_service=document_service,
                llm_service=llm_service,
                vector_search_service=vector_search_service,
                singleton=False  # Don't cache for execution
            )

            # Execute tool
            result = await tool.execute_with_validation(
                document=document,
                parameters=request.parameters
            )

            execution_time = time.time() - start_time

            return ToolExecutionResult(
                success=True,
                tool_type=request.tool_type.value,
                execution_time=execution_time,
                result=result
            )

        except ValueError as e:
            # Input validation error
            execution_time = time.time() - start_time
            return ToolExecutionResult(
                success=False,
                tool_type=request.tool_type.value,
                execution_time=execution_time,
                result={},
                error=f"Validation error: {str(e)}"
            )

        except Exception as e:
            execution_time = time.time() - start_time
            if isinstance(e, HTTPException):
                raise

            return ToolExecutionResult(
                success=False,
                tool_type=request.tool_type.value,
                execution_time=execution_time,
                result={},
                error=f"Execution error: {str(e)}"
            )


@router.get("/document-types/{document_type}/tools", response_model=List[str])
async def get_tools_for_document_type(document_type: DocumentType):
    """Get list of tools that support a specific document type"""
    with tracer.start_as_current_span("get_tools_for_document_type") as span:
        span.set_attribute("document.type", document_type.value)
        try:
            compatible_tools = DocumentToolRegistry.find_tools_by_document_type(document_type)
            return [tool.value for tool in compatible_tools]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get tools for document type: {str(e)}")


@router.get("/capabilities/{capability}/tools", response_model=List[str])
async def get_tools_by_capability(capability: DocumentToolCapability):
    """Get list of tools with a specific capability"""
    with tracer.start_as_current_span("get_tools_by_capability") as span:
        span.set_attribute("tool.capability", capability.value)
        try:
            matching_tools = DocumentToolRegistry.find_tools_by_capability(capability)
            return [tool.value for tool in matching_tools]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get tools by capability: {str(e)}")


@router.get("/categories/{category}/tools", response_model=List[str])
async def get_tools_by_category(category: DocumentToolCategory):
    """Get list of tools in a specific category"""
    with tracer.start_as_current_span("get_tools_by_category") as span:
        span.set_attribute("tool.category", category.value)
        try:
            matching_tools = DocumentToolRegistry.find_tools_by_category(category)
            return [tool.value for tool in matching_tools]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get tools by category: {str(e)}")


@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_tools():
    """Initialize the document tool system (admin endpoint)"""
    with tracer.start_as_current_span("initialize_tools"):
        try:
            init_result = initialize_document_tools()
            return {
                "success": True,
                "initialization_result": init_result
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize tools: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check for the tools system"""
    with tracer.start_as_current_span("tools_health_check"):
        try:
            stats = DocumentToolRegistry.get_stats()
            available_tools = DocumentToolRegistry.get_available_tools()

            return {
                "status": "healthy",
                "total_tools": len(available_tools),
                "statistics": stats,
                "available_tools": [tool.value for tool in available_tools]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }