"""Entity models for document entity extraction and relationships"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


class EntityTypes(str, Enum):
    """Standard entity types for extraction"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    MONEY = "money"
    PRODUCT = "product"
    EVENT = "event"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    UNKNOWN = "unknown"


class RelationshipTypes(str, Enum):
    """Standard relationship types between entities"""
    WORKS_FOR = "works_for"
    EMPLOYED_BY = "employed_by"
    LOCATED_IN = "located_in"
    FOUNDED_BY = "founded_by"
    FOUNDED = "founded"
    PART_OF = "part_of"
    SUBSIDIARY_OF = "subsidiary_of"
    OCCURRED_ON = "occurred_on"
    OCCURRED_AT = "occurred_at"
    ASSOCIATED_WITH = "associated_with"
    MENTIONS = "mentions"
    OWNS = "owns"
    MANAGES = "manages"
    MEMBER_OF = "member_of"


class Entity(BaseModel):
    """Enhanced entity model with relationships support"""
    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique entity identifier")
    text: str = Field(..., description="Original entity text from document")
    entity_type: str = Field(..., description="Type of entity (person, organization, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional entity metadata")
    start_pos: Optional[int] = Field(None, description="Start character position in text")
    end_pos: Optional[int] = Field(None, description="End character position in text")
    normalized_value: Optional[str] = Field(None, description="Normalized value (e.g., ISO 8601 date)")

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override to ensure consistent serialization"""
        data = super().model_dump(**kwargs)
        # Ensure entity_type is lowercase for consistency
        if 'entity_type' in data and data['entity_type']:
            data['entity_type'] = data['entity_type'].lower()
        return data


class EntityRelationship(BaseModel):
    """Relationship between two entities"""
    relationship_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique relationship identifier")
    from_entity_id: str = Field(..., description="Source entity ID")
    to_entity_id: str = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional relationship metadata")

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override to ensure consistent serialization"""
        data = super().model_dump(**kwargs)
        # Ensure relationship_type is lowercase for consistency
        if 'relationship_type' in data and data['relationship_type']:
            data['relationship_type'] = data['relationship_type'].lower()
        return data


class DocumentEntities(BaseModel):
    """Container for document entities and their relationships"""
    entities: List[Entity] = Field(default_factory=list, description="List of extracted entities")
    relationships: List[EntityRelationship] = Field(default_factory=list, description="List of entity relationships")

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        for entity in self.entities:
            if entity.entity_id == entity_id:
                return entity
        return None

    def get_relationships_for_entity(self, entity_id: str) -> List[EntityRelationship]:
        """Get all relationships involving an entity"""
        return [
            rel for rel in self.relationships
            if rel.from_entity_id == entity_id or rel.to_entity_id == entity_id
        ]

    def add_entity(self, entity: Entity) -> None:
        """Add entity to collection"""
        # Ensure entity_id is unique
        if any(e.entity_id == entity.entity_id for e in self.entities):
            entity.entity_id = str(uuid.uuid4())
        self.entities.append(entity)

    def add_relationship(self, relationship: EntityRelationship) -> None:
        """Add relationship to collection"""
        # Validate entities exist
        if not self.get_entity_by_id(relationship.from_entity_id):
            raise ValueError(f"From entity {relationship.from_entity_id} not found")
        if not self.get_entity_by_id(relationship.to_entity_id):
            raise ValueError(f"To entity {relationship.to_entity_id} not found")

        # Ensure relationship_id is unique
        if any(r.relationship_id == relationship.relationship_id for r in self.relationships):
            relationship.relationship_id = str(uuid.uuid4())

        self.relationships.append(relationship)
