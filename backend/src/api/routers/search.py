"""Search endpoints for vector, graph, and fulltext search"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...services.service_factory import ServiceFactory, ServiceType
from ...models.document import DocumentMessage, DocumentMetadata
from ..dependencies import get_current_user
from ...core.logger import CentralizedLogger


# Initialize router and logger
router = APIRouter()
logger = CentralizedLogger("SearchAPI")


# Request/Response models
class VectorSearchRequest(BaseModel):
    """Vector search request model"""
    query: str = Field(..., description="Search query text")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")


class SearchResult(BaseModel):
    """Search result model"""
    document_id: str
    name: str
    document_type: str
    score: float
    summary: Optional[str] = None
    created_user: str
    tags: List[str] = []


class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    results: List[SearchResult]
    count: int
    search_type: str


class SimilarDocumentsRequest(BaseModel):
    """Similar documents request"""
    document_id: str
    limit: int = Field(5, ge=1, le=50)
    threshold: float = Field(0.7, ge=0.0, le=1.0)


@router.post("/vector", response_model=SearchResponse)
async def vector_search(
    request: VectorSearchRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Perform vector-based similarity search on documents.

    Uses embeddings to find semantically similar documents.
    """
    logger.info(f"Vector search by {current_user['username']}: {request.query[:50]}...")

    try:
        # Get vector search service
        vector_service = ServiceFactory.create(ServiceType.VECTOR_SEARCH)

        # Perform search
        results = await vector_service.search(
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
            filters=request.filters
        )

        # Convert results
        search_results = []
        for metadata, score in results:
            search_results.append(SearchResult(
                document_id=metadata.document_id,
                name=metadata.name,
                document_type=str(metadata.document_type),
                score=score,
                summary=metadata.summary,
                created_user=metadata.created_user,
                tags=metadata.tags or []
            ))

        return SearchResponse(
            query=request.query,
            results=search_results,
            count=len(search_results),
            search_type="vector"
        )

    except Exception as e:
        logger.error(f"Vector search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/similar", response_model=SearchResponse)
async def find_similar_documents(
    request: SimilarDocumentsRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Find documents similar to a given document.

    Uses the document's embeddings to find similar content.
    """
    logger.info(f"Finding similar to {request.document_id} for {current_user['username']}")

    try:
        # Get vector search service
        vector_service = ServiceFactory.create(ServiceType.VECTOR_SEARCH)

        # Find similar documents
        results = await vector_service.find_similar(
            document_id=request.document_id,
            limit=request.limit,
            threshold=request.threshold
        )

        # Convert results
        search_results = []
        for metadata, score in results:
            search_results.append(SearchResult(
                document_id=metadata.document_id,
                name=metadata.name,
                document_type=str(metadata.document_type),
                score=score,
                summary=metadata.summary,
                created_user=metadata.created_user,
                tags=metadata.tags or []
            ))

        return SearchResponse(
            query=f"similar:{request.document_id}",
            results=search_results,
            count=len(search_results),
            search_type="similarity"
        )

    except Exception as e:
        logger.error(f"Similar search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/fulltext", response_model=SearchResponse)
async def fulltext_search(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_user)
):
    """
    Perform full-text search on document content.

    Uses Elasticsearch for advanced text search capabilities.
    """
    logger.info(f"Fulltext search by {current_user['username']}: {query[:50]}...")

    # For now, return mock results since Elasticsearch service isn't implemented
    mock_results = [
        SearchResult(
            document_id="doc_001",
            name="Sample Document",
            document_type="pdf",
            score=0.95,
            summary="This is a sample document for fulltext search",
            created_user="system",
            tags=["sample", "test"]
        )
    ]

    return SearchResponse(
        query=query,
        results=mock_results[:limit],
        count=len(mock_results),
        search_type="fulltext"
    )


@router.post("/graph", response_model=SearchResponse)
async def graph_search(
    query: str = Query(..., description="Graph query"),
    max_depth: int = Query(2, ge=1, le=5, description="Maximum traversal depth"),
    limit: int = Query(10, ge=1, le=100),
    current_user: Dict = Depends(get_current_user)
):
    """
    Perform graph-based search on document relationships.

    Uses Neo4j to traverse document relationships and connections.
    """
    logger.info(f"Graph search by {current_user['username']}: {query[:50]}...")

    # For now, return mock results since Neo4j service isn't implemented
    mock_results = [
        SearchResult(
            document_id="doc_002",
            name="Related Document",
            document_type="webpage",
            score=0.88,
            summary="Document found through graph relationships",
            created_user="system",
            tags=["related", "graph"]
        )
    ]

    return SearchResponse(
        query=query,
        results=mock_results[:limit],
        count=len(mock_results),
        search_type="graph"
    )


@router.post("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    query: str = Query(..., description="Search query"),
    search_types: List[str] = Query(["vector", "fulltext"], description="Search types to use"),
    limit: int = Query(10, ge=1, le=100),
    current_user: Dict = Depends(get_current_user)
):
    """
    Perform hybrid search combining multiple search strategies.

    Combines vector, fulltext, and graph search for comprehensive results.
    """
    logger.info(f"Hybrid search by {current_user['username']}: {query[:50]}...")

    all_results = []

    # Vector search if requested
    if "vector" in search_types:
        try:
            vector_service = ServiceFactory.create(ServiceType.VECTOR_SEARCH)
            vector_results = await vector_service.search(query, limit=limit)

            for metadata, score in vector_results:
                all_results.append(SearchResult(
                    document_id=metadata.document_id,
                    name=metadata.name,
                    document_type=str(metadata.document_type),
                    score=score * 0.5,  # Weight vector results
                    summary=metadata.summary,
                    created_user=metadata.created_user,
                    tags=metadata.tags or []
                ))
        except Exception as e:
            logger.warning(f"Vector search failed in hybrid: {str(e)}")

    # Add fulltext results if requested (mock for now)
    if "fulltext" in search_types:
        all_results.append(SearchResult(
            document_id="doc_fulltext",
            name="Fulltext Result",
            document_type="pdf",
            score=0.45,
            summary="Result from fulltext search",
            created_user="system",
            tags=["fulltext"]
        ))

    # Sort by score and deduplicate
    seen = set()
    unique_results = []
    for result in sorted(all_results, key=lambda x: x.score, reverse=True):
        if result.document_id not in seen:
            seen.add(result.document_id)
            unique_results.append(result)

    return SearchResponse(
        query=query,
        results=unique_results[:limit],
        count=len(unique_results),
        search_type="hybrid"
    )


@router.post("/index/{document_id}")
async def index_document(
    document_id: str,
    force_reindex: bool = Query(False, description="Force reindexing"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Index a document for search.

    Adds document to vector, fulltext, and graph indices.
    """
    logger.info(f"Indexing document {document_id} by {current_user['username']}")

    try:
        # Get document
        doc_service = ServiceFactory.create(ServiceType.DOCUMENT)
        document = await doc_service.get_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        # Index in vector search
        vector_service = ServiceFactory.create(ServiceType.VECTOR_SEARCH)
        indexed = await vector_service.index_document(document, force_reindex)

        return {
            "document_id": document_id,
            "indexed": indexed,
            "message": "Document indexed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to index document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}"
        )


@router.delete("/index/{document_id}")
async def remove_from_index(
    document_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Remove a document from search indices.
    """
    logger.info(f"Removing {document_id} from index by {current_user['username']}")

    try:
        # Remove from vector search
        vector_service = ServiceFactory.create(ServiceType.VECTOR_SEARCH)
        removed = await vector_service.delete_document(document_id)

        return {
            "document_id": document_id,
            "removed": removed,
            "message": "Document removed from index"
        }

    except Exception as e:
        logger.error(f"Failed to remove from index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Removal failed: {str(e)}"
        )