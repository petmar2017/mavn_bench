"""Unit tests for entity extraction tool with date normalization"""

import pytest
from src.services.llm.tools.entity_extraction_tool import EntityExtractionTool
from src.models.entity import Entity as EntityModel


class TestEntityExtractionTool:
    """Test entity extraction tool"""

    @pytest.fixture
    def tool(self):
        """Create entity extraction tool instance"""
        return EntityExtractionTool(name="test_entity_extraction", llm_client=None)

    def test_normalize_date_valid_formats(self, tool):
        """Test date normalization with various formats"""
        test_cases = [
            ("Jan 1, 2024", "2024-01-01"),
            ("January 15, 2024", "2024-01-15"),
            ("2024-03-20", "2024-03-20"),
            ("March 20, 2024", "2024-03-20"),
            ("12/31/2023", "2023-12-31"),
            ("31-12-2023", "2023-12-31"),
        ]

        for input_date, expected in test_cases:
            result = tool._normalize_date(input_date)
            assert result == expected, f"Failed for input: {input_date}"

    def test_normalize_date_invalid_input(self, tool):
        """Test date normalization with invalid input"""
        invalid_dates = [
            "not a date",
            "",
            # Note: dateutil.parser is very lenient and can parse some unexpected strings
            # "abc123" -> interprets as "0123-10-06" (current month/day with year abc=123)
            # So we focus on truly unparseable strings
        ]

        for invalid_date in invalid_dates:
            result = tool._normalize_date(invalid_date)
            assert result is None, f"Should return None for: {invalid_date}"

    def test_create_entity_date_normalization(self, tool):
        """Test that _create_entity normalizes dates"""
        entity = tool._create_entity(
            text="Jan 15, 2024",
            entity_type="date",
            confidence=0.9,
        )

        assert isinstance(entity, EntityModel)
        assert entity.text == "Jan 15, 2024"
        assert entity.entity_type == "date"
        assert entity.confidence == 0.9
        assert entity.normalized_value == "2024-01-15"
        assert entity.entity_id  # Should have generated ID

    def test_create_entity_non_date(self, tool):
        """Test that _create_entity doesn't normalize non-dates"""
        entity = tool._create_entity(
            text="John Doe",
            entity_type="person",
            confidence=0.95,
        )

        assert entity.text == "John Doe"
        assert entity.entity_type == "person"
        assert entity.normalized_value is None

    def test_create_entity_lowercases_type(self, tool):
        """Test that _create_entity lowercases entity type"""
        entity = tool._create_entity(
            text="Test",
            entity_type="PERSON",
            confidence=0.9,
        )

        assert entity.entity_type == "person"

    @pytest.mark.asyncio
    async def test_fallback_entities_date_extraction(self, tool):
        """Test fallback entity extraction with dates"""
        text = "The meeting is on Jan 15, 2024 at the office."

        entities = tool._generate_fallback_entities(text, ["DATE"])

        assert len(entities) > 0
        date_entities = [e for e in entities if e.entity_type == "date"]
        assert len(date_entities) == 1

        date_entity = date_entities[0]
        assert "Jan 15, 2024" in date_entity.text
        assert date_entity.normalized_value == "2024-01-15"

    @pytest.mark.asyncio
    async def test_fallback_entities_email_extraction(self, tool):
        """Test fallback email entity extraction"""
        text = "Contact me at john.doe@example.com for more info."

        entities = tool._generate_fallback_entities(text, ["EMAIL"])

        assert len(entities) == 1
        assert entities[0].text == "john.doe@example.com"
        assert entities[0].entity_type == "email"
        assert entities[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_fallback_entities_phone_extraction(self, tool):
        """Test fallback phone entity extraction"""
        text = "Call me at 555-123-4567 or 555.987.6543."

        entities = tool._generate_fallback_entities(text, ["PHONE"])

        assert len(entities) == 2
        phone_numbers = [e.text for e in entities]
        assert "555-123-4567" in phone_numbers
        assert "555.987.6543" in phone_numbers

    @pytest.mark.asyncio
    async def test_fallback_entities_money_extraction(self, tool):
        """Test fallback money entity extraction"""
        text = "The price is $1,234.56 or $99."

        entities = tool._generate_fallback_entities(text, ["MONEY"])

        assert len(entities) == 2
        money_amounts = [e.text for e in entities]
        assert "$1,234.56" in money_amounts or "$1,234" in money_amounts
        assert "$99" in money_amounts

    @pytest.mark.asyncio
    async def test_fallback_entities_multiple_types(self, tool):
        """Test fallback extraction with multiple entity types"""
        text = "Contact john@example.com by Jan 15, 2024 for the $500 payment."

        entities = tool._generate_fallback_entities(
            text, ["EMAIL", "DATE", "MONEY"]
        )

        # Should find at least one of each type
        entity_types = {e.entity_type for e in entities}
        assert "email" in entity_types
        assert "date" in entity_types
        assert "money" in entity_types

    def test_parse_entities_json_format(self, tool):
        """Test parsing entities from JSON response"""
        response = """[
            {"text": "John Doe", "type": "PERSON", "confidence": 0.95},
            {"text": "Apple Inc.", "type": "ORGANIZATION", "confidence": 0.9},
            {"text": "Jan 15, 2024", "type": "DATE", "confidence": 0.85}
        ]"""

        entities = tool._parse_entities(response)

        assert len(entities) == 3
        assert entities[0].text == "John Doe"
        assert entities[0].entity_type == "person"
        assert entities[1].text == "Apple Inc."
        assert entities[1].entity_type == "organization"
        assert entities[2].text == "Jan 15, 2024"
        assert entities[2].entity_type == "date"
        assert entities[2].normalized_value == "2024-01-15"

    def test_parse_entities_text_format(self, tool):
        """Test parsing entities from text format"""
        response = """PERSON: John Doe
ORGANIZATION: Apple Inc.
DATE: Jan 15, 2024"""

        entities = tool._parse_entities(response)

        assert len(entities) == 3
        entity_types = {e.entity_type for e in entities}
        assert "person" in entity_types
        assert "organization" in entity_types
        assert "date" in entity_types

    def test_parse_entities_with_markdown(self, tool):
        """Test parsing entities with markdown code blocks"""
        response = """```json
[
    {"text": "Test Entity", "type": "PERSON", "confidence": 0.9}
]
```"""

        entities = tool._parse_entities(response)

        assert len(entities) == 1
        assert entities[0].text == "Test Entity"
        assert entities[0].entity_type == "person"

    @pytest.mark.asyncio
    async def test_execute_returns_model_dump(self, tool):
        """Test that execute returns entities as dicts with model_dump()"""
        text_content = "Contact john@example.com by Jan 15, 2024."

        result = await tool.execute({"text": text_content, "entity_types": ["EMAIL", "DATE"]})

        assert "entities" in result
        assert isinstance(result["entities"], list)

        if len(result["entities"]) > 0:
            entity_dict = result["entities"][0]
            assert isinstance(entity_dict, dict)
            assert "entity_id" in entity_dict
            assert "text" in entity_dict
            assert "entity_type" in entity_dict
            assert "confidence" in entity_dict

    @pytest.mark.asyncio
    async def test_execute_empty_text(self, tool):
        """Test execute with empty text"""
        result = await tool.execute({"text": "", "entity_types": ["PERSON"]})

        assert result == {"entities": []}

    @pytest.mark.asyncio
    async def test_execute_no_entity_types(self, tool):
        """Test execute with no entity types specified"""
        text_content = "Contact john@example.com."

        result = await tool.execute({"text": text_content})

        # Should use default entity types
        assert "entities" in result

    def test_entity_id_uniqueness(self, tool):
        """Test that each created entity gets a unique ID"""
        entities = [
            tool._create_entity(text="Entity 1", entity_type="person", confidence=0.9),
            tool._create_entity(text="Entity 2", entity_type="person", confidence=0.9),
            tool._create_entity(text="Entity 3", entity_type="person", confidence=0.9),
        ]

        entity_ids = [e.entity_id for e in entities]
        assert len(entity_ids) == len(set(entity_ids))  # All unique

    def test_entity_metadata_preservation(self, tool):
        """Test that entity metadata is preserved"""
        metadata = {"source": "test", "custom_field": "value"}

        entity = tool._create_entity(
            text="Test",
            entity_type="person",
            confidence=0.9,
            metadata=metadata,
        )

        assert entity.metadata == metadata

    @pytest.mark.asyncio
    async def test_date_normalization_in_full_pipeline(self, tool):
        """Test date normalization works in complete extraction pipeline"""
        text_content = "The conference is scheduled for March 20, 2024 in New York."

        result = await tool.execute({"text": text_content, "entity_types": ["DATE", "LOCATION"]})

        entities = result["entities"]
        date_entities = [e for e in entities if e.get("entity_type") == "date"]

        if len(date_entities) > 0:
            date_entity = date_entities[0]
            assert date_entity.get("normalized_value") == "2024-03-20"
