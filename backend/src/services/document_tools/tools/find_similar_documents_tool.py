"""Find similar documents tool using vector search"""

from typing import Dict, Any, List, Optional

from ..base_tool import (
    BaseDocumentTool,
    DocumentToolMetadata,
    DocumentToolCapability,
    DocumentToolCategory
)
from ..tool_registry import DocumentToolType
from ..tool_decorators import register_document_tool
from ....models.document import DocumentType, DocumentMessage


@register_document_tool(DocumentToolType.FIND_SIMILAR_DOCUMENTS)
class FindSimilarDocumentsTool(BaseDocumentTool):
    """Tool for finding similar documents using vector search"""

    def get_metadata(self) -> DocumentToolMetadata:
        """Get tool metadata"""
        return DocumentToolMetadata(
            id="find_similar_documents",
            name="Find Similar Documents",
            description="Find documents similar to the current document using vector similarity",
            category=DocumentToolCategory.SEARCH,
            icon="search",
            version="1.0.0",
            capabilities=[
                DocumentToolCapability.SIMILARITY,
                DocumentToolCapability.ANALYSIS
            ],
            supported_document_types=[
                DocumentType.TEXT,
                DocumentType.MARKDOWN,
                DocumentType.PDF,
                DocumentType.WORD,
                DocumentType.WEBPAGE,
                DocumentType.JSON
            ],
            input_schema={
                "limit": {
                    "type": "int",
                    "required": False,
                    "default": 5,
                    "description": "Maximum number of similar documents to return"
                },
                "similarity_threshold": {
                    "type": "float",
                    "required": False,
                    "default": 0.7,
                    "description": "Minimum similarity score (0.0-1.0)"
                },
                "exclude_same_type": {
                    "type": "bool",
                    "required": False,
                    "default": False,
                    "description": "Exclude documents of the same type"
                },
                "include_content": {
                    "type": "bool",
                    "required": False,
                    "default": False,
                    "description": "Include content snippets in results"
                }
            },
            output_schema={
                "similar_documents": {
                    "type": "list",
                    "description": "List of similar documents with similarity scores"
                },
                "query_info": {
                    "type": "dict",
                    "description": "Information about the search query"
                },
                "statistics": {
                    "type": "dict",
                    "description": "Search statistics and metrics"
                }
            },
            requires_vector_search=True,
            execution_time_estimate="fast",
            batch_capable=False
        )

    async def execute(
        self,
        document: DocumentMessage,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute similarity search

        Args:
            document: Document to find similar documents for
            parameters: Search parameters

        Returns:
            List of similar documents with scores and metadata
        """
        # Validate input
        self.validate_input(document, parameters)

        parameters = parameters or {}
        limit = parameters.get("limit", 5)
        similarity_threshold = parameters.get("similarity_threshold", 0.7)
        exclude_same_type = parameters.get("exclude_same_type", False)
        include_content = parameters.get("include_content", False)

        # Extract content for similarity search
        query_text = self._extract_query_text(document)

        if not query_text:
            return {
                "similar_documents": [],
                "query_info": {
                    "query_length": 0,
                    "error": "No text content available for similarity search"
                },
                "statistics": {
                    "total_searched": 0,
                    "found_similar": 0,
                    "avg_similarity": 0.0
                }
            }

        # Perform vector search if service is available
        if self.vector_search_service:
            similar_docs = await self._vector_similarity_search(
                query_text, document, limit, similarity_threshold, exclude_same_type
            )
        else:
            # Fallback to keyword-based similarity
            similar_docs = await self._keyword_similarity_search(
                query_text, document, limit, similarity_threshold, exclude_same_type
            )

        # Enrich results with additional metadata
        enriched_docs = await self._enrich_results(similar_docs, include_content)

        # Generate statistics
        statistics = self._generate_search_statistics(similar_docs, query_text)

        return {
            "similar_documents": enriched_docs,
            "query_info": {
                "query_length": len(query_text),
                "query_preview": query_text[:100] + "..." if len(query_text) > 100 else query_text,
                "source_document_id": document.metadata.document_id,
                "source_document_type": document.metadata.document_type.value
            },
            "statistics": statistics
        }

    def _extract_query_text(self, document: DocumentMessage) -> str:
        """Extract text content suitable for similarity search"""
        if not document.content:
            return ""

        # Use formatted content if available, otherwise raw text
        query_text = document.content.formatted_content or document.content.text or ""

        # For JSON documents, extract meaningful text
        if document.metadata.document_type == DocumentType.JSON:
            query_text = self._extract_json_text(query_text)

        # Limit query length for performance
        max_query_length = 2000
        if len(query_text) > max_query_length:
            query_text = query_text[:max_query_length]

        return query_text.strip()

    def _extract_json_text(self, json_content: str) -> str:
        """Extract meaningful text from JSON content for similarity search"""
        try:
            import json
            data = json.loads(json_content)

            # Extract string values recursively
            text_parts = []

            def extract_strings(obj):
                if isinstance(obj, str):
                    # Skip very short strings and common technical terms
                    if len(obj) > 3 and not obj.isdigit():
                        text_parts.append(obj)
                elif isinstance(obj, dict):
                    for value in obj.values():
                        extract_strings(value)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_strings(item)

            extract_strings(data)
            return " ".join(text_parts)

        except json.JSONDecodeError:
            # If not valid JSON, return original content
            return json_content

    async def _vector_similarity_search(
        self,
        query_text: str,
        source_document: DocumentMessage,
        limit: int,
        threshold: float,
        exclude_same_type: bool
    ) -> List[Dict[str, Any]]:
        """Perform vector-based similarity search"""
        try:
            # Generate query embedding
            query_embedding = await self.vector_search_service.generate_embedding(query_text)

            # Search for similar documents
            search_results = await self.vector_search_service.similarity_search(
                query_vector=query_embedding,
                limit=limit * 2,  # Get more results to filter
                threshold=threshold
            )

            # Filter results
            filtered_results = []
            for result in search_results:
                # Skip the source document itself
                if result.get("document_id") == source_document.metadata.document_id:
                    continue

                # Skip same document type if requested
                if exclude_same_type and result.get("document_type") == source_document.metadata.document_type.value:
                    continue

                filtered_results.append({
                    "document_id": result.get("document_id"),
                    "similarity_score": result.get("score", 0.0),
                    "document_type": result.get("document_type"),
                    "title": result.get("title"),
                    "metadata": result.get("metadata", {}),
                    "method": "vector_search"
                })

                if len(filtered_results) >= limit:
                    break

            return filtered_results

        except Exception as e:
            # Fallback to keyword search if vector search fails
            return await self._keyword_similarity_search(
                query_text, source_document, limit, threshold, exclude_same_type
            )

    async def _keyword_similarity_search(
        self,
        query_text: str,
        source_document: DocumentMessage,
        limit: int,
        threshold: float,
        exclude_same_type: bool
    ) -> List[Dict[str, Any]]:
        """Fallback keyword-based similarity search"""
        # This is a simplified implementation
        # In a real system, you would query your document storage

        # Extract keywords from query
        keywords = self._extract_keywords(query_text)

        if not self.document_service:
            return []

        try:
            # Get all documents (in real implementation, this would be paginated)
            all_documents = await self.document_service.list_documents(limit=100)

            similar_docs = []

            for doc in all_documents:
                # Skip the source document
                if doc.metadata.document_id == source_document.metadata.document_id:
                    continue

                # Skip same document type if requested
                if exclude_same_type and doc.metadata.document_type == source_document.metadata.document_type:
                    continue

                # Calculate keyword-based similarity
                if doc.content and doc.content.text:
                    similarity = self._calculate_keyword_similarity(keywords, doc.content.text)

                    if similarity >= threshold:
                        similar_docs.append({
                            "document_id": doc.metadata.document_id,
                            "similarity_score": similarity,
                            "document_type": doc.metadata.document_type.value,
                            "title": doc.metadata.title,
                            "metadata": {
                                "created_at": doc.metadata.created_at.isoformat() if doc.metadata.created_at else None,
                                "file_size": doc.metadata.file_size,
                                "tags": doc.metadata.tags
                            },
                            "method": "keyword_search"
                        })

            # Sort by similarity score and limit results
            similar_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_docs[:limit]

        except Exception as e:
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for similarity matching"""
        # Simple keyword extraction (could be improved with NLP)
        import re

        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that',
            'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
            'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
            'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
            'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these',
            'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
            'had', 'having', 'do', 'does', 'did', 'doing', 'will', 'would', 'should', 'could',
            'can', 'may', 'might', 'must', 'shall'
        }

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter out stop words and short words
        keywords = [word for word in words if word not in stop_words and len(word) >= 3]

        # Get unique keywords
        return list(set(keywords))

    def _calculate_keyword_similarity(self, query_keywords: List[str], document_text: str) -> float:
        """Calculate similarity based on keyword overlap"""
        if not query_keywords:
            return 0.0

        document_text_lower = document_text.lower()
        matches = 0

        for keyword in query_keywords:
            if keyword in document_text_lower:
                matches += 1

        # Calculate Jaccard similarity coefficient
        return matches / len(query_keywords)

    async def _enrich_results(
        self,
        similar_docs: List[Dict[str, Any]],
        include_content: bool
    ) -> List[Dict[str, Any]]:
        """Enrich similarity results with additional metadata"""
        enriched_docs = []

        for doc in similar_docs:
            enriched_doc = doc.copy()

            # Add content snippet if requested and document service is available
            if include_content and self.document_service:
                try:
                    # Get document content
                    full_doc = await self.document_service.get_document(doc["document_id"])
                    if full_doc and full_doc.content and full_doc.content.text:
                        # Extract a snippet
                        content_text = full_doc.content.text
                        snippet_length = 200
                        enriched_doc["content_snippet"] = (
                            content_text[:snippet_length] + "..."
                            if len(content_text) > snippet_length
                            else content_text
                        )
                except Exception:
                    enriched_doc["content_snippet"] = "Content unavailable"

            # Add similarity interpretation
            score = enriched_doc["similarity_score"]
            if score >= 0.9:
                enriched_doc["similarity_level"] = "very_high"
            elif score >= 0.8:
                enriched_doc["similarity_level"] = "high"
            elif score >= 0.7:
                enriched_doc["similarity_level"] = "medium"
            else:
                enriched_doc["similarity_level"] = "low"

            enriched_docs.append(enriched_doc)

        return enriched_docs

    def _generate_search_statistics(
        self,
        similar_docs: List[Dict[str, Any]],
        query_text: str
    ) -> Dict[str, Any]:
        """Generate search statistics"""
        if not similar_docs:
            return {
                "total_searched": 0,
                "found_similar": 0,
                "avg_similarity": 0.0,
                "max_similarity": 0.0,
                "min_similarity": 0.0,
                "similarity_distribution": {}
            }

        scores = [doc["similarity_score"] for doc in similar_docs]

        # Calculate similarity distribution
        distribution = {"very_high": 0, "high": 0, "medium": 0, "low": 0}
        for score in scores:
            if score >= 0.9:
                distribution["very_high"] += 1
            elif score >= 0.8:
                distribution["high"] += 1
            elif score >= 0.7:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1

        return {
            "total_searched": len(similar_docs),  # Simplified
            "found_similar": len(similar_docs),
            "avg_similarity": sum(scores) / len(scores),
            "max_similarity": max(scores),
            "min_similarity": min(scores),
            "similarity_distribution": distribution,
            "query_keywords": len(self._extract_keywords(query_text))
        }