/**
 * ToolsMenu Component
 *
 * Displays context-sensitive tools available for a document.
 * Shows which tools have been executed and allows execution of new tools.
 *
 * @module components/ToolsMenu
 */

import { useState } from 'react';
import { CheckCircle, Loader2 } from 'lucide-react';
import classNames from 'classnames';
import { getAvailableTools, type ToolDefinition } from '../../utils/toolsRegistry';
import type { DocumentMessage } from '../../types/document';
import styles from './ToolsMenu.module.css';

interface ToolsMenuProps {
  /** The document for which to show tools */
  document: DocumentMessage;
  /** Callback when a tool is successfully executed */
  onToolExecuted?: (toolId: string, result: any) => void;
  /** Callback when a tool execution fails */
  onToolError?: (toolId: string, error: Error) => void;
}

/**
 * ToolsMenu - Context-sensitive document tools panel
 */
export const ToolsMenu: React.FC<ToolsMenuProps> = ({
  document,
  onToolExecuted,
  onToolError,
}) => {
  const [executingTool, setExecutingTool] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const availableTools = getAvailableTools(
    document.metadata.document_type,
    document.tools || []
  );

  const executeTool = async (tool: ToolDefinition) => {
    // Prevent concurrent executions
    if (executingTool) {
      return;
    }

    // Confirm if required
    if (tool.requiresConfirmation) {
      const confirmed = window.confirm(
        `Execute ${tool.label}?\n\n${tool.description || ''}`
      );
      if (!confirmed) {
        return;
      }
    }

    setExecutingTool(tool.id);
    setError(null);

    try {
      const result = await tool.action(document.metadata.document_id);
      onToolExecuted?.(tool.id, result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(`Failed to execute ${tool.label}: ${error.message}`);
      onToolError?.(tool.id, error);
    } finally {
      setExecutingTool(null);
    }
  };

  const isToolExecuted = (toolId: string): boolean => {
    return (document.tools || []).includes(toolId);
  };

  if (availableTools.length === 0) {
    return (
      <div className={styles.toolsMenu}>
        <h3 className={styles.title}>Tools</h3>
        <div className={styles.emptyState}>
          <p>No tools available for this document type</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.toolsMenu}>
      <h3 className={styles.title}>Tools</h3>

      {error && (
        <div className={styles.error}>
          <p>{error}</p>
        </div>
      )}

      <div className={styles.toolsList}>
        {availableTools.map((tool) => {
          const Icon = tool.icon;
          const executed = isToolExecuted(tool.id);
          const executing = executingTool === tool.id;
          const disabled = executingTool !== null;

          return (
            <button
              key={tool.id}
              className={classNames(styles.toolButton, {
                [styles.executed]: executed,
                [styles.executing]: executing,
                [styles.disabled]: disabled && !executing,
              })}
              onClick={() => executeTool(tool)}
              disabled={disabled}
              title={tool.description || tool.label}
            >
              <div className={styles.toolIcon}>
                {executing ? (
                  <Loader2 size={18} className={styles.spinner} />
                ) : (
                  <Icon size={18} />
                )}
              </div>

              <span className={styles.toolLabel}>{tool.label}</span>

              {executed && !executing && (
                <CheckCircle size={14} className={styles.checkIcon} />
              )}
            </button>
          );
        })}
      </div>

      <div className={styles.footer}>
        <p className={styles.footerText}>
          {availableTools.length} tool{availableTools.length !== 1 ? 's' : ''} available
        </p>
      </div>
    </div>
  );
};
