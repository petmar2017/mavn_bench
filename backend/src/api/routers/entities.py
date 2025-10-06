"""Entity management API endpoints"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ...core.logger import CentralizedLogger
from ...models.entity import EntityTypes, RelationshipTypes, Entity, EntityRelationship, DocumentEntities
from ...services.service_factory import ServiceFactory, ServiceType
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/entities", tags=["entities"])
logger = CentralizedLogger("EntitiesAPI")


class EntityTypesResponse(BaseModel):
    """Response model for entity types"""
    types: List[str] = Field(..., description="Available entity types")


class RelationshipTypesResponse(BaseModel):
    """Response model for relationship types"""
    types: List[str] = Field(..., description="Available relationship types")


class UpdateDocumentEntitiesRequest(BaseModel):
    """Request model for updating document entities"""
    entities: List[Entity] = Field(..., description="Updated entities list")
    relationships: List[EntityRelationship] = Field(default_factory=list, description="Entity relationships")


class DocumentEntitiesResponse(BaseModel):
    """Response model for document entities"""
    document_id: str
    entities: List[Entity]
    relationships: List[EntityRelationship]


@router.get("/types", response_model=EntityTypesResponse)
async def get_entity_types(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> EntityTypesResponse:
    """
    Get available entity types.

    Returns list of all supported entity types for entity extraction and editing.
    """
    logger.info(f"Entity types requested by {current_user.get('user_id', 'unknown')}")

    types = [entity_type.value for entity_type in EntityTypes]

    return EntityTypesResponse(types=types)


@router.get("/relationship-types", response_model=RelationshipTypesResponse)
async def get_relationship_types(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> RelationshipTypesResponse:
    """
    Get available relationship types.

    Returns list of all supported relationship types for entity relationships.
    """
    logger.info(f"Relationship types requested by {current_user.get('user_id', 'unknown')}")

    types = [rel_type.value for rel_type in RelationshipTypes]

    return RelationshipTypesResponse(types=types)


@router.get("/document/{document_id}", response_model=DocumentEntitiesResponse)
async def get_document_entities(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DocumentEntitiesResponse:
    """
    Get entities and relationships for a document.

    Args:
        document_id: Document ID

    Returns:
        Document entities and relationships
    """
    logger.info(f"Getting entities for document {document_id} by {current_user.get('user_id', 'unknown')}")

    try:
        # Get document service
        doc_service = ServiceFactory.create(ServiceType.DOCUMENT)

        # Load document
        document = await doc_service.get_document(
            document_id=document_id,
            user_id=current_user.get("user_id", "test")
        )

        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        # Extract entities and relationships from metadata
        entities_data = document.metadata.entities or []
        relationships_data = document.metadata.model_dump().get("relationships", [])

        # Convert to Entity objects
        entities = [Entity(**e) if isinstance(e, dict) else e for e in entities_data]
        relationships = [EntityRelationship(**r) if isinstance(r, dict) else r for r in relationships_data]

        return DocumentEntitiesResponse(
            document_id=document_id,
            entities=entities,
            relationships=relationships
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entities for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get entities: {str(e)}")


@router.post("/document/{document_id}", response_model=DocumentEntitiesResponse)
async def update_document_entities(
    document_id: str,
    request: UpdateDocumentEntitiesRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DocumentEntitiesResponse:
    """
    Update entities and relationships for a document.

    Args:
        document_id: Document ID
        request: Updated entities and relationships

    Returns:
        Updated document entities and relationships
    """
    logger.info(
        f"Updating entities for document {document_id} by {current_user.get('user_id', 'unknown')} "
        f"({len(request.entities)} entities, {len(request.relationships)} relationships)"
    )

    try:
        # Get document service
        doc_service = ServiceFactory.create(ServiceType.DOCUMENT)

        # Load document
        document = await doc_service.get_document(
            document_id=document_id,
            user_id=current_user.get("user_id", "test")
        )

        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        # Validate relationships reference existing entities
        entity_ids = {e.entity_id for e in request.entities}
        for rel in request.relationships:
            if rel.from_entity_id not in entity_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Relationship references non-existent entity: {rel.from_entity_id}"
                )
            if rel.to_entity_id not in entity_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Relationship references non-existent entity: {rel.to_entity_id}"
                )

        # Update document metadata with entities and relationships
        document.metadata.entities = [e.model_dump() for e in request.entities]

        # Add relationships to metadata (will need to update DocumentMetadata model)
        metadata_dict = document.metadata.model_dump()
        metadata_dict["relationships"] = [r.model_dump() for r in request.relationships]

        # Update document
        updated_document = await doc_service.update_document(
            document_id=document_id,
            updates={"metadata": metadata_dict},
            user_id=current_user.get("user_id", "test")
        )

        logger.info(f"Successfully updated entities for document {document_id}")

        return DocumentEntitiesResponse(
            document_id=document_id,
            entities=request.entities,
            relationships=request.relationships
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update entities for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update entities: {str(e)}")
