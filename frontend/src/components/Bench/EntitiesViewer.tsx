import { useState, useEffect } from 'react';
import { Edit2, Save, X, ChevronDown, ChevronRight } from 'lucide-react';
import classNames from 'classnames';
import { documentApi } from '../../services/api';
import { entityApi } from '../../services/entityApi';
import { logger } from '../../services/logging';
import type { Entity } from '../../types/document';
import styles from './EntitiesViewer.module.css';

interface EntitiesViewerProps {
  documentId: string;
  entities: Entity[];
  onEntitiesUpdate?: (entities: Entity[]) => void;
}

export const EntitiesViewer: React.FC<EntitiesViewerProps> = ({
  documentId,
  entities: initialEntities,
  onEntitiesUpdate,
}) => {
  const [entities, setEntities] = useState<Entity[]>(initialEntities);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedEntity, setEditedEntity] = useState<Entity | null>(null);
  const [groupedEntities, setGroupedEntities] = useState<Record<string, Entity[]>>({});
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set());
  const [isSaving, setIsSaving] = useState(false);
  const [availableEntityTypes, setAvailableEntityTypes] = useState<string[]>([]);

  // Fetch available entity types from API
  useEffect(() => {
    const fetchEntityTypes = async () => {
      try {
        const types = await entityApi.getEntityTypes();
        setAvailableEntityTypes(types);
      } catch (error) {
        logger.error('Failed to fetch entity types', { error });
        // Fallback to hardcoded types
        setAvailableEntityTypes(['person', 'organization', 'location', 'date', 'money', 'unknown']);
      }
    };

    fetchEntityTypes();
  }, []);

  useEffect(() => {
    // Group entities by type
    const grouped: Record<string, Entity[]> = {};
    entities.forEach(entity => {
      const type = entity.entity_type || 'unknown';
      if (!grouped[type]) {
        grouped[type] = [];
      }
      grouped[type].push(entity);
    });
    setGroupedEntities(grouped);

    // Expand all types by default
    setExpandedTypes(new Set(Object.keys(grouped)));
  }, [entities]);

  const handleEditEntity = (index: number) => {
    setEditingIndex(index);
    setEditedEntity({ ...entities[index] });
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditedEntity(null);
  };

  const handleSaveEntity = async () => {
    if (editingIndex === null || !editedEntity) return;

    setIsSaving(true);
    try {
      // Update the entities array
      const updatedEntities = [...entities];
      updatedEntities[editingIndex] = editedEntity;
      setEntities(updatedEntities);

      // Update the document metadata
      await documentApi.updateDocument(documentId, {
        metadata: {
          entities: updatedEntities,
        },
      });

      logger.info('Entity updated successfully', { documentId, entity: editedEntity });
      onEntitiesUpdate?.(updatedEntities);

      setEditingIndex(null);
      setEditedEntity(null);
    } catch (error) {
      logger.error('Failed to update entity', { documentId, error });
      alert('Failed to save entity changes');
    } finally {
      setIsSaving(false);
    }
  };

  const toggleEntityType = (type: string) => {
    const newExpanded = new Set(expandedTypes);
    if (newExpanded.has(type)) {
      newExpanded.delete(type);
    } else {
      newExpanded.add(type);
    }
    setExpandedTypes(newExpanded);
  };

  const getEntityTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      PERSON: '#3b82f6',
      ORGANIZATION: '#8b5cf6',
      LOCATION: '#10b981',
      DATE: '#f59e0b',
      MONEY: '#ef4444',
      UNKNOWN: '#6b7280',
    };
    return colors[type] || colors.UNKNOWN;
  };

  if (entities.length === 0) {
    return (
      <div className={styles.emptyState}>
        <p>No entities extracted yet</p>
        <p className={styles.hint}>Use the "Extract Entities" tool to analyze this document</p>
      </div>
    );
  }

  return (
    <div className={styles.entitiesViewer}>
      <div className={styles.header}>
        <h3>Extracted Entities ({entities.length})</h3>
      </div>

      <div className={styles.entitiesList}>
        {Object.entries(groupedEntities).map(([type, typeEntities]) => (
          <div key={type} className={styles.entityGroup}>
            <div
              className={styles.entityGroupHeader}
              onClick={() => toggleEntityType(type)}
            >
              <div className={styles.groupHeaderLeft}>
                {expandedTypes.has(type) ? (
                  <ChevronDown size={16} />
                ) : (
                  <ChevronRight size={16} />
                )}
                <span
                  className={styles.entityTypeBadge}
                  style={{ backgroundColor: getEntityTypeColor(type) }}
                >
                  {type}
                </span>
                <span className={styles.entityCount}>({typeEntities.length})</span>
              </div>
            </div>

            {expandedTypes.has(type) && (
              <div className={styles.entityGroupContent}>
                {typeEntities.map((entity, groupIndex) => {
                  const globalIndex = entities.findIndex(e => e === entity);
                  const isEditing = editingIndex === globalIndex;

                  return (
                    <div
                      key={groupIndex}
                      className={classNames(styles.entityItem, {
                        [styles.editing]: isEditing,
                      })}
                    >
                      {isEditing && editedEntity ? (
                        <div className={styles.editForm}>
                          <div className={styles.formRow}>
                            <label>Text:</label>
                            <input
                              type="text"
                              value={editedEntity.text}
                              onChange={(e) =>
                                setEditedEntity({ ...editedEntity, text: e.target.value })
                              }
                              className={styles.input}
                            />
                          </div>
                          {editedEntity.entity_type.toLowerCase() === 'date' && (
                            <div className={styles.formRow}>
                              <label>Date Value:</label>
                              <input
                                type="date"
                                value={editedEntity.normalized_value || ''}
                                onChange={(e) =>
                                  setEditedEntity({
                                    ...editedEntity,
                                    normalized_value: e.target.value,
                                  })
                                }
                                className={styles.input}
                              />
                            </div>
                          )}
                          <div className={styles.formRow}>
                            <label>Type:</label>
                            <input
                              type="text"
                              list="entity-types-datalist"
                              value={editedEntity.entity_type}
                              onChange={(e) =>
                                setEditedEntity({
                                  ...editedEntity,
                                  entity_type: e.target.value,
                                })
                              }
                              className={styles.input}
                              placeholder="Select or type entity type"
                            />
                            <datalist id="entity-types-datalist">
                              {availableEntityTypes.map((type) => (
                                <option key={type} value={type}>
                                  {type.charAt(0).toUpperCase() + type.slice(1)}
                                </option>
                              ))}
                            </datalist>
                          </div>
                          <div className={styles.formRow}>
                            <label>Confidence:</label>
                            <input
                              type="number"
                              min="0"
                              max="1"
                              step="0.1"
                              value={editedEntity.confidence}
                              onChange={(e) =>
                                setEditedEntity({
                                  ...editedEntity,
                                  confidence: parseFloat(e.target.value),
                                })
                              }
                              className={styles.input}
                            />
                          </div>
                          <div className={styles.formActions}>
                            <button
                              onClick={handleSaveEntity}
                              disabled={isSaving}
                              className={styles.saveButton}
                            >
                              <Save size={16} />
                              {isSaving ? 'Saving...' : 'Save'}
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              disabled={isSaving}
                              className={styles.cancelButton}
                            >
                              <X size={16} />
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className={styles.entityContent}>
                          <div className={styles.entityText}>
                            {entity.text}
                            {entity.entity_type.toLowerCase() === 'date' && entity.normalized_value && (
                              <span className={styles.normalizedDate}>
                                {' '}({entity.normalized_value})
                              </span>
                            )}
                          </div>
                          <div className={styles.entityMeta}>
                            <span className={styles.confidence}>
                              {(entity.confidence * 100).toFixed(0)}% confidence
                            </span>
                            <button
                              onClick={() => handleEditEntity(globalIndex)}
                              className={styles.editButton}
                              title="Edit entity"
                            >
                              <Edit2 size={14} />
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
