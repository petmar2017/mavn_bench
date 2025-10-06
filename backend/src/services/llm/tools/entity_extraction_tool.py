"""Entity extraction tool for identifying named entities in text"""

import json
import re
import uuid
from typing import Dict, Any, List, Optional
from dateutil import parser as date_parser
from datetime import datetime

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool
from ....models.entity import Entity as EntityModel


@register_tool(LLMToolType.ENTITY_EXTRACTION)
class EntityExtractionTool(BaseLLMTool):
    """Tool for extracting named entities from text"""

    def _normalize_date(self, date_text: str) -> Optional[str]:
        """
        Normalize date text to ISO 8601 format (YYYY-MM-DD)

        Args:
            date_text: Original date text

        Returns:
            Normalized date in ISO 8601 format or None if parsing fails
        """
        try:
            parsed_date = date_parser.parse(date_text, fuzzy=True)
            return parsed_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            # If parsing fails, return None
            return None

    def _create_entity(
        self,
        text: str,
        entity_type: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EntityModel:
        """
        Create an Entity object with proper normalization

        Args:
            text: Entity text
            entity_type: Entity type
            confidence: Confidence score
            metadata: Additional metadata

        Returns:
            EntityModel instance
        """
        normalized_value = None

        # Normalize dates to ISO 8601 format
        if entity_type.upper() == "DATE":
            normalized_value = self._normalize_date(text)

        return EntityModel(
            entity_id=str(uuid.uuid4()),
            text=text,
            entity_type=entity_type.lower(),
            confidence=confidence,
            metadata=metadata or {},
            normalized_value=normalized_value
        )

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            name="entity_extraction",
            description="Extract named entities (people, organizations, locations, etc.) from text",
            version="1.0.0",
            capabilities=[
                ToolCapability.EXTRACTION,
                ToolCapability.TEXT_ANALYSIS
            ],
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Text to extract entities from"
                },
                "entity_types": {
                    "type": "list",
                    "required": False,
                    "default": ["PERSON", "ORGANIZATION", "LOCATION", "DATE", "MONEY", "PRODUCT", "EVENT"],
                    "description": "Types of entities to extract"
                }
            },
            output_schema={
                "entities": {
                    "type": "list",
                    "description": "List of extracted entities"
                }
            },
            max_input_length=500000,  # Can handle long documents via chunking
            supports_streaming=False
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute entity extraction

        Args:
            input_data: Must contain 'text', optionally 'entity_types'

        Returns:
            Dictionary with 'entities' key containing list of entity dictionaries
        """
        # Validate input
        self.validate_input(input_data)

        # Extract parameters
        text = input_data.get("text", "")
        entity_types = input_data.get("entity_types")

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return {"entities": []}

        # Use default entity types if not specified
        if not entity_types:
            entity_types = [
                "PERSON", "ORGANIZATION", "LOCATION", "DATE",
                "MONEY", "PRODUCT", "EVENT", "EMAIL", "PHONE"
            ]

        # Handle long documents by chunking
        max_chunk_size = 40000  # Leave room for prompt overhead
        if len(text) > max_chunk_size:
            entities = await self._extract_from_chunks(text, entity_types, max_chunk_size)
        else:
            # Prepare prompt
            prompt = self._prepare_prompt(text, entity_types)

            # Call LLM
            if self.llm_client:
                response = await self.call_llm(
                    prompt=prompt,
                    max_tokens=1000,  # Entities shouldn't need much
                    temperature=0.3  # Lower temperature for consistency
                )
                entities = self._parse_entities(response)
            else:
                # Fallback for testing
                entities = self._generate_fallback_entities(text, entity_types)

        return {"entities": [entity.model_dump() for entity in entities]}

    async def _extract_from_chunks(
        self,
        text: str,
        entity_types: List[str],
        chunk_size: int
    ) -> List[EntityModel]:
        """Extract entities from long text by processing in chunks

        Args:
            text: Full text to process
            entity_types: Types of entities to extract
            chunk_size: Maximum size of each chunk

        Returns:
            Combined list of unique entities from all chunks
        """
        entities_dict = {}  # Use dict to deduplicate by text

        # Split text into overlapping chunks to avoid missing entities at boundaries
        overlap = 500  # Characters of overlap between chunks
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - overlap if end < len(text) else end

        # Process each chunk
        for chunk in chunks:
            if self.llm_client:
                prompt = self._prepare_prompt(chunk, entity_types)
                response = await self.call_llm(
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=0.3
                )
                chunk_entities = self._parse_entities(response)
            else:
                chunk_entities = self._generate_fallback_entities(chunk, entity_types)

            # Deduplicate entities - keep highest confidence
            for entity in chunk_entities:
                key = (entity.text.lower(), entity.entity_type)
                if key not in entities_dict or entity.confidence > entities_dict[key].confidence:
                    entities_dict[key] = entity

        return list(entities_dict.values())

    def _prepare_prompt(self, text: str, entity_types: List[str]) -> str:
        """Prepare the entity extraction prompt"""
        types_str = ", ".join(entity_types)

        prompt_template = """Extract the following types of entities from the text: {types_str}

Return the result as a JSON array with objects containing:
- "text": the entity text
- "type": the entity type
- "confidence": confidence score (0-1)

Example format:
[
  {{"text": "John Smith", "type": "PERSON", "confidence": 0.95}},
  {{"text": "Google", "type": "ORGANIZATION", "confidence": 0.98}}
]

Text:
{text}

Entities (JSON format only):"""

        return self.prepare_prompt(
            prompt_template,
            types_str=types_str,
            text=text[:5000]  # Limit text length for prompt
        )

    def _parse_entities(self, response: str) -> List[EntityModel]:
        """Parse entities from LLM response"""
        entities = []

        # Clean response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith('```'):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])

        # Try to parse as JSON
        if response.strip().startswith('['):
            try:
                entity_data = json.loads(response)
                for item in entity_data:
                    if isinstance(item, dict) and "text" in item:
                        entity = self._create_entity(
                            text=item.get("text", ""),
                            entity_type=item.get("type", "UNKNOWN"),
                            confidence=float(item.get("confidence", 1.0)),
                            metadata=item.get("metadata")
                        )
                        entities.append(entity)
                return entities
            except (json.JSONDecodeError, ValueError):
                pass  # Fall through to text parsing

        # Fallback: parse as text lines
        lines = response.strip().split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    entity_type = parts[0].strip().upper()
                    entity_text = parts[1].strip()

                    # Clean up common formatting
                    entity_text = entity_text.strip('"\'')

                    entities.append(self._create_entity(
                        text=entity_text,
                        entity_type=entity_type,
                        confidence=0.8  # Default confidence for text parsing
                    ))

        return entities

    def _generate_fallback_entities(self, text: str, entity_types: List[str]) -> List[EntityModel]:
        """Generate basic entities without LLM using simple patterns"""
        entities = []

        # Email pattern
        if "EMAIL" in entity_types:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            for match in re.finditer(email_pattern, text):
                entities.append(self._create_entity(
                    text=match.group(),
                    entity_type="EMAIL",
                    confidence=0.9
                ))

        # Phone pattern (simple US format)
        if "PHONE" in entity_types:
            phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
            for match in re.finditer(phone_pattern, text):
                entities.append(self._create_entity(
                    text=match.group(),
                    entity_type="PHONE",
                    confidence=0.7
                ))

        # Date pattern (simple) - will be normalized by _create_entity
        if "DATE" in entity_types:
            date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
            for match in re.finditer(date_pattern, text, re.IGNORECASE):
                entities.append(self._create_entity(
                    text=match.group(),
                    entity_type="DATE",
                    confidence=0.8
                ))

        # Money pattern
        if "MONEY" in entity_types:
            money_pattern = r'\$[\d,]+(?:\.\d{2})?'
            for match in re.finditer(money_pattern, text):
                entities.append(self._create_entity(
                    text=match.group(),
                    entity_type="MONEY",
                    confidence=0.9
                ))

        return entities