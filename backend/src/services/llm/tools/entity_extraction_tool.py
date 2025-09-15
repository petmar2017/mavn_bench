"""Entity extraction tool for identifying named entities in text"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool


@dataclass
class Entity:
    """Represents an extracted entity"""
    text: str
    entity_type: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "text": self.text,
            "type": self.entity_type,
            "confidence": self.confidence,
            "metadata": self.metadata or {}
        }


@register_tool(LLMToolType.ENTITY_EXTRACTION)
class EntityExtractionTool(BaseLLMTool):
    """Tool for extracting named entities from text"""

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
            max_input_length=50000,
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

        return {"entities": [entity.to_dict() for entity in entities]}

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

    def _parse_entities(self, response: str) -> List[Entity]:
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
                        entity = Entity(
                            text=item.get("text", ""),
                            entity_type=item.get("type", "UNKNOWN"),
                            confidence=float(item.get("confidence", 1.0))
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

                    entities.append(Entity(
                        text=entity_text,
                        entity_type=entity_type,
                        confidence=0.8  # Default confidence for text parsing
                    ))

        return entities

    def _generate_fallback_entities(self, text: str, entity_types: List[str]) -> List[Entity]:
        """Generate basic entities without LLM using simple patterns"""
        entities = []

        # Simple pattern matching for common entity types
        import re

        # Email pattern
        if "EMAIL" in entity_types:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            for match in re.finditer(email_pattern, text):
                entities.append(Entity(
                    text=match.group(),
                    entity_type="EMAIL",
                    confidence=0.9
                ))

        # Phone pattern (simple US format)
        if "PHONE" in entity_types:
            phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
            for match in re.finditer(phone_pattern, text):
                entities.append(Entity(
                    text=match.group(),
                    entity_type="PHONE",
                    confidence=0.7
                ))

        # Date pattern (simple)
        if "DATE" in entity_types:
            date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
            for match in re.finditer(date_pattern, text, re.IGNORECASE):
                entities.append(Entity(
                    text=match.group(),
                    entity_type="DATE",
                    confidence=0.8
                ))

        # Money pattern
        if "MONEY" in entity_types:
            money_pattern = r'\$[\d,]+(?:\.\d{2})?'
            for match in re.finditer(money_pattern, text):
                entities.append(Entity(
                    text=match.group(),
                    entity_type="MONEY",
                    confidence=0.9
                ))

        return entities