"""Embedding generation tool for creating vector representations of text"""

from typing import Dict, Any, List, Optional

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool


@register_tool(LLMToolType.EMBEDDING)
class EmbeddingTool(BaseLLMTool):
    """Tool for generating text embeddings"""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            name="embedding",
            description="Generate vector embeddings for text",
            version="1.0.0",
            capabilities=[
                ToolCapability.EMBEDDING_GENERATION
            ],
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Text to generate embeddings for"
                },
                "model": {
                    "type": "str",
                    "required": False,
                    "default": "text-embedding-ada-002",
                    "description": "Embedding model to use"
                }
            },
            output_schema={
                "embeddings": {
                    "type": "list",
                    "description": "Vector embeddings"
                },
                "dimensions": {
                    "type": "int",
                    "description": "Number of dimensions in the embedding"
                }
            },
            max_input_length=8000,  # OpenAI's limit for ada-002
            supports_streaming=False,
            requires_api_key=True
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute embedding generation

        Args:
            input_data: Must contain 'text', optionally 'model'

        Returns:
            Dictionary with 'embeddings' and 'dimensions' keys
        """
        # Validate input
        self.validate_input(input_data)

        # Extract parameters
        text = input_data.get("text", "")
        model = input_data.get("model", "text-embedding-ada-002")

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return {
                "embeddings": [],
                "dimensions": 0
            }

        # Generate embeddings
        if self.llm_client:
            embeddings = await self._generate_embeddings(text, model)
        else:
            # Fallback for testing
            embeddings = self._generate_mock_embeddings(text)

        return {
            "embeddings": embeddings,
            "dimensions": len(embeddings)
        }

    async def _generate_embeddings(
        self,
        text: str,
        model: str
    ) -> List[float]:
        """Generate embeddings using the LLM client

        Note: This assumes the LLM client has an embeddings API.
        For OpenAI, this would use the embeddings endpoint.
        For Anthropic, embeddings are not directly supported.
        """
        # This would be implemented by the LLM service
        # which has access to the actual API clients
        if hasattr(self.llm_client, 'generate_embeddings'):
            return await self.llm_client.generate_embeddings(text, model)
        else:
            # If no embeddings API, return mock
            return self._generate_mock_embeddings(text)

    def _generate_mock_embeddings(self, text: str) -> List[float]:
        """Generate mock embeddings for testing"""
        import hashlib
        import random

        # Use text hash as seed for reproducible mock embeddings
        text_hash = hashlib.md5(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)
        random.seed(seed)

        # Generate mock embeddings
        # OpenAI's ada-002 has 1536 dimensions, but we'll use fewer for mock
        dimensions = 384
        embeddings = [random.random() * 2 - 1 for _ in range(dimensions)]

        # Normalize to unit vector (common for embeddings)
        magnitude = sum(x**2 for x in embeddings) ** 0.5
        if magnitude > 0:
            embeddings = [x / magnitude for x in embeddings]

        return embeddings