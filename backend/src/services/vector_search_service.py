"""Vector search service using Qdrant

This service handles:
- Document embedding generation
- Vector storage in Qdrant
- Similarity search
- Hybrid search with metadata filtering
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import uuid4

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue,
        SearchRequest, SearchParams
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from .base_service import BaseService
from .llm_service import LLMService
from ..models.document import DocumentMessage, DocumentMetadata, DocumentContent
from ..core.config import get_settings
from ..core.logger import CentralizedLogger


class VectorSearchService(BaseService):
    """Service for vector-based document search using Qdrant"""

    def __init__(self):
        """Initialize vector search service"""
        super().__init__("VectorSearchService")
        self.settings = get_settings()
        self.logger = CentralizedLogger("VectorSearchService")

        # Initialize LLM service for embeddings
        self.llm_service = LLMService()

        # Qdrant configuration
        self.collection_name = "documents"
        self.vector_size = 384  # Using smaller size for demo, normally 1536 for ada-002

        # Mock storage for when Qdrant is not available
        self.mock_storage = {}  # document_id -> (document, embeddings)

        # Initialize Qdrant client if available
        if QDRANT_AVAILABLE:
            self.client = QdrantClient(
                host=getattr(self.settings, 'qdrant_host', 'localhost'),
                port=getattr(self.settings, 'qdrant_port', 6333)
            )
            # Ensure collection exists
            asyncio.create_task(self._ensure_collection())
        else:
            self.client = None
            self.logger.warning("Qdrant client not available, using mock implementation")

    async def _ensure_collection(self):
        """Ensure the Qdrant collection exists"""
        if not self.client:
            return

        try:
            collections = await asyncio.to_thread(
                self.client.get_collections
            )

            if self.collection_name not in [c.name for c in collections.collections]:
                await asyncio.to_thread(
                    self.client.create_collection,
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                self.logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            self.logger.error(f"Failed to ensure collection: {str(e)}")

    async def index_document(
        self,
        document: DocumentMessage,
        force_reindex: bool = False
    ) -> bool:
        """Index a document for vector search

        Args:
            document: Document to index
            force_reindex: Force reindexing even if document exists

        Returns:
            Success status
        """
        with self.traced_operation(
            "index_document",
            document_id=document.metadata.document_id,
            force_reindex=force_reindex
        ):
            try:
                doc_id = document.metadata.document_id

                # Check if already indexed (unless forcing)
                if not force_reindex and await self.document_exists(doc_id):
                    self.logger.info(f"Document {doc_id} already indexed")
                    return True

                # Generate embeddings
                text = document.content.formatted_content or document.content.raw_text
                if not text:
                    self.logger.warning(f"No text content for document {doc_id}")
                    return False

                embeddings = await self.llm_service.generate_embeddings(text[:8000])  # Limit text

                # Prepare metadata
                metadata = {
                    "document_id": doc_id,
                    "document_type": str(document.metadata.document_type),
                    "name": document.metadata.name,
                    "created_user": document.metadata.created_user,
                    "created_timestamp": document.metadata.created_timestamp.isoformat(),
                    "tags": document.metadata.tags or [],
                    "summary": document.metadata.summary or ""
                }

                # Store in Qdrant
                if self.client:
                    point = PointStruct(
                        id=str(uuid4()),
                        vector=embeddings,
                        payload=metadata
                    )

                    await asyncio.to_thread(
                        self.client.upsert,
                        collection_name=self.collection_name,
                        points=[point]
                    )
                else:
                    # Mock storage - store in memory
                    self.mock_storage[doc_id] = (document, embeddings)
                    self.logger.info(f"Mock: Indexed document {doc_id}")

                self.logger.info(f"Successfully indexed document {doc_id}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to index document: {str(e)}")
                raise

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        threshold: float = 0.7
    ) -> List[Tuple[DocumentMessage, float]]:
        """Search for similar documents

        Args:
            query: Search query
            limit: Maximum results
            filters: Metadata filters
            threshold: Similarity threshold (0-1)

        Returns:
            List of (DocumentMessage, score) tuples
        """
        # Validate query
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        with self.traced_operation(
            "search",
            query=query[:100],
            limit=limit,
            threshold=threshold
        ):
            try:
                # Generate query embeddings
                query_embeddings = await self.llm_service.generate_embeddings(query)

                if self.client:
                    # Build filter if provided
                    qdrant_filter = None
                    if filters:
                        conditions = []
                        for key, value in filters.items():
                            conditions.append(
                                FieldCondition(
                                    key=key,
                                    match=MatchValue(value=value)
                                )
                            )
                        if conditions:
                            qdrant_filter = Filter(must=conditions)

                    # Perform search
                    results = await asyncio.to_thread(
                        self.client.search,
                        collection_name=self.collection_name,
                        query_vector=query_embeddings,
                        limit=limit,
                        query_filter=qdrant_filter,
                        score_threshold=threshold
                    )

                    # Convert results to DocumentMessage
                    documents = []
                    for result in results:
                        metadata = DocumentMetadata(
                            document_id=result.payload["document_id"],
                            document_type=result.payload["document_type"],
                            name=result.payload["name"],
                            created_user=result.payload["created_user"],
                            updated_user=result.payload["created_user"]
                        )
                        # Create DocumentMessage with empty content for search results
                        doc_message = DocumentMessage(
                            metadata=metadata,
                            content=DocumentContent()  # Empty content for search results
                        )
                        documents.append((doc_message, result.score))

                    self.logger.info(f"Found {len(documents)} similar documents")
                    return documents

                else:
                    # Mock search results
                    self.logger.info("Mock: Returning sample search results")
                    if limit == 0:
                        return []
                    mock_metadata = DocumentMetadata(
                        document_id="mock_doc_1",
                        document_type="pdf",
                        name="Mock Document",
                        created_user="system",
                        updated_user="system"
                    )
                    mock_doc = DocumentMessage(
                        metadata=mock_metadata,
                        content=DocumentContent()
                    )
                    return [(mock_doc, 0.85)]

            except Exception as e:
                self.logger.error(f"Search failed: {str(e)}")
                raise

    async def find_similar(
        self,
        document_id: str,
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[DocumentMessage, float]]:
        """Find documents similar to a given document

        Args:
            document_id: Source document ID
            limit: Maximum results
            threshold: Similarity threshold

        Returns:
            List of similar DocumentMessage objects with scores
        """
        with self.traced_operation(
            "find_similar",
            document_id=document_id,
            limit=limit
        ):
            try:
                if self.client:
                    # First, get the document's vector
                    results = await asyncio.to_thread(
                        self.client.scroll,
                        collection_name=self.collection_name,
                        scroll_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="document_id",
                                    match=MatchValue(value=document_id)
                                )
                            ]
                        ),
                        limit=1
                    )

                    if not results[0]:
                        self.logger.warning(f"Document {document_id} not found in index")
                        return []

                    # Use the document's vector to find similar
                    doc_vector = results[0][0].vector

                    similar = await asyncio.to_thread(
                        self.client.search,
                        collection_name=self.collection_name,
                        query_vector=doc_vector,
                        limit=limit + 1,  # +1 to exclude self
                        score_threshold=threshold
                    )

                    # Convert and filter out the source document
                    documents = []
                    for result in similar:
                        if result.payload["document_id"] != document_id:
                            metadata = DocumentMetadata(
                                document_id=result.payload["document_id"],
                                document_type=result.payload["document_type"],
                                name=result.payload["name"],
                                created_user=result.payload["created_user"],
                                updated_user=result.payload["created_user"]
                            )
                            documents.append((metadata, result.score))

                    self.logger.info(f"Found {len(documents)} similar documents")
                    return documents[:limit]

                else:
                    # Mock results
                    return []

            except Exception as e:
                self.logger.error(f"Find similar failed: {str(e)}")
                raise

    async def delete_document(self, document_id: str) -> bool:
        """Remove a document from the vector index

        Args:
            document_id: Document to remove

        Returns:
            Success status
        """
        with self.traced_operation("delete_document", document_id=document_id):
            try:
                if self.client:
                    # Find and delete by document_id
                    await asyncio.to_thread(
                        self.client.delete,
                        collection_name=self.collection_name,
                        points_selector=Filter(
                            must=[
                                FieldCondition(
                                    key="document_id",
                                    match=MatchValue(value=document_id)
                                )
                            ]
                        )
                    )
                    self.logger.info(f"Deleted document {document_id} from index")
                    return True
                else:
                    # Mock deletion
                    if document_id in self.mock_storage:
                        del self.mock_storage[document_id]
                        self.logger.info(f"Mock: Deleted document {document_id}")
                        return True
                    return False

            except Exception as e:
                self.logger.error(f"Failed to delete document: {str(e)}")
                return False

    async def document_exists(self, document_id: str) -> bool:
        """Check if a document is indexed

        Args:
            document_id: Document to check

        Returns:
            True if indexed
        """
        with self.traced_operation("document_exists", document_id=document_id):
            try:
                if self.client:
                    results = await asyncio.to_thread(
                        self.client.scroll,
                        collection_name=self.collection_name,
                        scroll_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="document_id",
                                    match=MatchValue(value=document_id)
                                )
                            ]
                        ),
                        limit=1
                    )
                    exists = len(results[0]) > 0
                    self.logger.debug(f"Document {document_id} exists: {exists}")
                    return exists
                else:
                    # Check mock storage
                    exists = document_id in self.mock_storage
                    self.logger.debug(f"Mock: Document {document_id} exists: {exists}")
                    return exists

            except Exception as e:
                self.logger.error(f"Failed to check document existence: {str(e)}")
                return False

    async def reindex_all(self, documents: List[DocumentMessage]) -> int:
        """Reindex all documents

        Args:
            documents: Documents to index

        Returns:
            Number of documents indexed
        """
        with self.traced_operation("reindex_all", count=len(documents)):
            indexed = 0
            for document in documents:
                try:
                    if await self.index_document(document, force_reindex=True):
                        indexed += 1
                except Exception as e:
                    self.logger.error(f"Failed to index {document.metadata.document_id}: {str(e)}")

            self.logger.info(f"Reindexed {indexed}/{len(documents)} documents")
            return indexed

    async def health_check(self) -> Dict[str, Any]:
        """Check service health

        Returns:
            Health status
        """
        with self.traced_operation("health_check"):
            try:
                if self.client:
                    # Check Qdrant connection
                    collections = await asyncio.to_thread(
                        self.client.get_collections
                    )

                    # Get collection info
                    collection_info = None
                    for collection in collections.collections:
                        if collection.name == self.collection_name:
                            collection_info = await asyncio.to_thread(
                                self.client.get_collection,
                                collection_name=self.collection_name
                            )
                            break

                    return {
                        "service": "VectorSearchService",
                        "status": "healthy",
                        "qdrant_available": True,
                        "collection_exists": collection_info is not None,
                        "vector_count": collection_info.vectors_count if collection_info else 0,
                        "vector_size": self.vector_size
                    }
                else:
                    return {
                        "service": "VectorSearchService",
                        "status": "degraded",
                        "qdrant_available": False,
                        "message": "Using mock implementation"
                    }

            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                return {
                    "service": "VectorSearchService",
                    "status": "unhealthy",
                    "error": str(e)
                }


# Register with factory
from .service_factory import ServiceFactory, ServiceType
ServiceFactory.register(ServiceType.VECTOR_SEARCH, VectorSearchService)