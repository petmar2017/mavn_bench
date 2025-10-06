"""Unit tests for entity models"""

import pytest
import uuid
from src.models.entity import (
    Entity,
    EntityRelationship,
    DocumentEntities,
    EntityTypes,
    RelationshipTypes,
)


class TestEntity:
    """Test Entity model"""

    def test_entity_creation(self):
        """Test creating an entity"""
        entity = Entity(
            text="John Doe",
            entity_type="person",
            confidence=0.95,
        )

        assert entity.text == "John Doe"
        assert entity.entity_type == "person"
        assert entity.confidence == 0.95
        assert entity.entity_id  # Should auto-generate
        assert entity.metadata == {}

    def test_entity_with_metadata(self):
        """Test entity with metadata"""
        entity = Entity(
            text="Apple Inc.",
            entity_type="organization",
            confidence=0.9,
            metadata={"industry": "technology"},
        )

        assert entity.metadata["industry"] == "technology"

    def test_entity_with_positions(self):
        """Test entity with character positions"""
        entity = Entity(
            text="New York",
            entity_type="location",
            confidence=0.85,
            start_pos=10,
            end_pos=18,
        )

        assert entity.start_pos == 10
        assert entity.end_pos == 18

    def test_entity_with_normalized_value(self):
        """Test entity with normalized value (dates)"""
        entity = Entity(
            text="Jan 1, 2024",
            entity_type="date",
            confidence=0.9,
            normalized_value="2024-01-01",
        )

        assert entity.normalized_value == "2024-01-01"

    def test_entity_model_dump_lowercases_type(self):
        """Test that model_dump lowercases entity_type"""
        entity = Entity(
            text="Test",
            entity_type="PERSON",
            confidence=0.9,
        )

        data = entity.model_dump()
        assert data["entity_type"] == "person"

    def test_entity_confidence_validation(self):
        """Test confidence score validation"""
        # Valid confidence
        entity = Entity(text="Test", entity_type="person", confidence=0.5)
        assert entity.confidence == 0.5

        # Test boundaries
        entity_min = Entity(text="Test", entity_type="person", confidence=0.0)
        assert entity_min.confidence == 0.0

        entity_max = Entity(text="Test", entity_type="person", confidence=1.0)
        assert entity_max.confidence == 1.0


class TestEntityRelationship:
    """Test EntityRelationship model"""

    def test_relationship_creation(self):
        """Test creating a relationship"""
        rel = EntityRelationship(
            from_entity_id="entity-1",
            to_entity_id="entity-2",
            relationship_type="works_for",
            confidence=0.85,
        )

        assert rel.from_entity_id == "entity-1"
        assert rel.to_entity_id == "entity-2"
        assert rel.relationship_type == "works_for"
        assert rel.confidence == 0.85
        assert rel.relationship_id  # Should auto-generate

    def test_relationship_with_metadata(self):
        """Test relationship with metadata"""
        rel = EntityRelationship(
            from_entity_id="entity-1",
            to_entity_id="entity-2",
            relationship_type="located_in",
            confidence=0.9,
            metadata={"since": "2020"},
        )

        assert rel.metadata["since"] == "2020"

    def test_relationship_model_dump_lowercases_type(self):
        """Test that model_dump lowercases relationship_type"""
        rel = EntityRelationship(
            from_entity_id="entity-1",
            to_entity_id="entity-2",
            relationship_type="WORKS_FOR",
            confidence=0.8,
        )

        data = rel.model_dump()
        assert data["relationship_type"] == "works_for"


class TestDocumentEntities:
    """Test DocumentEntities container"""

    def test_document_entities_creation(self):
        """Test creating document entities container"""
        doc_entities = DocumentEntities()

        assert doc_entities.entities == []
        assert doc_entities.relationships == []

    def test_add_entity(self):
        """Test adding entity to container"""
        doc_entities = DocumentEntities()
        entity = Entity(
            text="Test",
            entity_type="person",
            confidence=0.9,
        )

        doc_entities.add_entity(entity)
        assert len(doc_entities.entities) == 1
        assert doc_entities.entities[0] == entity

    def test_add_entity_generates_unique_id(self):
        """Test that duplicate entity IDs are regenerated"""
        doc_entities = DocumentEntities()

        entity1 = Entity(
            entity_id="same-id",
            text="Entity 1",
            entity_type="person",
            confidence=0.9,
        )
        entity2 = Entity(
            entity_id="same-id",
            text="Entity 2",
            entity_type="person",
            confidence=0.9,
        )

        doc_entities.add_entity(entity1)
        doc_entities.add_entity(entity2)

        assert len(doc_entities.entities) == 2
        assert doc_entities.entities[0].entity_id != doc_entities.entities[1].entity_id

    def test_get_entity_by_id(self):
        """Test getting entity by ID"""
        doc_entities = DocumentEntities()
        entity = Entity(
            text="Test",
            entity_type="person",
            confidence=0.9,
        )
        doc_entities.add_entity(entity)

        found = doc_entities.get_entity_by_id(entity.entity_id)
        assert found == entity

    def test_get_entity_by_id_not_found(self):
        """Test getting non-existent entity"""
        doc_entities = DocumentEntities()

        found = doc_entities.get_entity_by_id("non-existent")
        assert found is None

    def test_add_relationship(self):
        """Test adding relationship"""
        doc_entities = DocumentEntities()

        # Add entities first
        entity1 = Entity(text="John", entity_type="person", confidence=0.9)
        entity2 = Entity(text="Apple", entity_type="organization", confidence=0.9)
        doc_entities.add_entity(entity1)
        doc_entities.add_entity(entity2)

        # Add relationship
        rel = EntityRelationship(
            from_entity_id=entity1.entity_id,
            to_entity_id=entity2.entity_id,
            relationship_type="works_for",
            confidence=0.85,
        )
        doc_entities.add_relationship(rel)

        assert len(doc_entities.relationships) == 1
        assert doc_entities.relationships[0] == rel

    def test_add_relationship_invalid_from_entity(self):
        """Test adding relationship with non-existent from_entity"""
        doc_entities = DocumentEntities()

        entity = Entity(text="Test", entity_type="person", confidence=0.9)
        doc_entities.add_entity(entity)

        rel = EntityRelationship(
            from_entity_id="non-existent",
            to_entity_id=entity.entity_id,
            relationship_type="works_for",
            confidence=0.8,
        )

        with pytest.raises(ValueError, match="From entity .* not found"):
            doc_entities.add_relationship(rel)

    def test_add_relationship_invalid_to_entity(self):
        """Test adding relationship with non-existent to_entity"""
        doc_entities = DocumentEntities()

        entity = Entity(text="Test", entity_type="person", confidence=0.9)
        doc_entities.add_entity(entity)

        rel = EntityRelationship(
            from_entity_id=entity.entity_id,
            to_entity_id="non-existent",
            relationship_type="works_for",
            confidence=0.8,
        )

        with pytest.raises(ValueError, match="To entity .* not found"):
            doc_entities.add_relationship(rel)

    def test_get_relationships_for_entity(self):
        """Test getting relationships for an entity"""
        doc_entities = DocumentEntities()

        # Add entities
        entity1 = Entity(text="John", entity_type="person", confidence=0.9)
        entity2 = Entity(text="Apple", entity_type="organization", confidence=0.9)
        entity3 = Entity(text="Microsoft", entity_type="organization", confidence=0.9)
        doc_entities.add_entity(entity1)
        doc_entities.add_entity(entity2)
        doc_entities.add_entity(entity3)

        # Add relationships
        rel1 = EntityRelationship(
            from_entity_id=entity1.entity_id,
            to_entity_id=entity2.entity_id,
            relationship_type="works_for",
            confidence=0.85,
        )
        rel2 = EntityRelationship(
            from_entity_id=entity3.entity_id,
            to_entity_id=entity1.entity_id,
            relationship_type="employs",
            confidence=0.8,
        )
        doc_entities.add_relationship(rel1)
        doc_entities.add_relationship(rel2)

        # Get relationships for entity1
        entity1_rels = doc_entities.get_relationships_for_entity(entity1.entity_id)
        assert len(entity1_rels) == 2
        assert rel1 in entity1_rels
        assert rel2 in entity1_rels

        # Get relationships for entity2
        entity2_rels = doc_entities.get_relationships_for_entity(entity2.entity_id)
        assert len(entity2_rels) == 1
        assert rel1 in entity2_rels


class TestEntityTypes:
    """Test EntityTypes enum"""

    def test_entity_types_values(self):
        """Test all entity types are defined"""
        expected_types = {
            "person",
            "organization",
            "location",
            "date",
            "money",
            "product",
            "event",
            "email",
            "phone",
            "url",
            "unknown",
        }

        actual_types = {t.value for t in EntityTypes}
        assert actual_types == expected_types


class TestRelationshipTypes:
    """Test RelationshipTypes enum"""

    def test_relationship_types_values(self):
        """Test all relationship types are defined"""
        expected_types = {
            "works_for",
            "employed_by",
            "located_in",
            "founded_by",
            "founded",
            "part_of",
            "subsidiary_of",
            "occurred_on",
            "occurred_at",
            "associated_with",
            "mentions",
            "owns",
            "manages",
            "member_of",
        }

        actual_types = {t.value for t in RelationshipTypes}
        assert actual_types == expected_types
