import { useState, useEffect, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { Loader } from 'lucide-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import type { ColDef, ValueSetterParams } from 'ag-grid-community';
import type { DocumentMessage } from '../../services/api';
import { documentContentService } from '../../services/documentContent';
import styles from './ExcelViewer.module.css';

interface ExcelViewerProps {
  document: DocumentMessage;
  onCellChange?: () => void;
}

interface RowData {
  [key: string]: any;
}

export const ExcelViewer: React.FC<ExcelViewerProps> = ({
  document,
  onCellChange,
}) => {
  const [rowData, setRowData] = useState<RowData[]>([]);
  const [columnDefs, setColumnDefs] = useState<ColDef[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch and parse CSV or Excel data
    const loadContent = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const documentId = document.metadata.document_id;
        const contentData = await documentContentService.getContent(documentId);
        const text = contentData.text || contentData.formatted_content || contentData.raw_text || '';

          if (text) {
            const { columns, rows } = parseCSVContent(text);

            // Create column definitions for AG-Grid
            const colDefs: ColDef[] = columns.map(col => ({
              field: col,
              headerName: col,
              sortable: true,
              filter: true,
              resizable: true,
              editable: true,
              valueSetter: (params: ValueSetterParams) => {
                if (params.data[params.colDef.field!] !== params.newValue) {
                  params.data[params.colDef.field!] = params.newValue;
                  onCellChange?.();
                  return true;
                }
                return false;
              }
            }));

            setColumnDefs(colDefs);
            setRowData(rows);
          } else if (contentData.formatted_content) {
            // Try to parse from formatted content
            try {
              const data = JSON.parse(contentData.formatted_content);
              if (Array.isArray(data) && data.length > 0) {
                const columns = Object.keys(data[0]);
                const colDefs: ColDef[] = columns.map(col => ({
                  field: col,
                  headerName: col,
                  sortable: true,
                  filter: true,
                  resizable: true,
                  editable: true,
                  valueSetter: (params: ValueSetterParams) => {
                    if (params.data[params.colDef.field!] !== params.newValue) {
                      params.data[params.colDef.field!] = params.newValue;
                      onCellChange?.();
                      return true;
                    }
                    return false;
                  }
                }));
                setColumnDefs(colDefs);
                setRowData(data);
              }
            } catch (e) {
              console.error('Failed to parse formatted content:', e);
              setError('Failed to parse document content');
            }
          }
        } catch (err) {
          console.error('Failed to load document content:', err);
          setError('Failed to load document content');
        } finally {
          setIsLoading(false);
        }
      };

      loadContent();
    }, [document.metadata.document_id, onCellChange]);

  const defaultColDef = useMemo(() => ({
    flex: 1,
    minWidth: 100,
    resizable: true,
    sortable: true,
    filter: true,
  }), []);

  // Parse CSV content into columns and rows
  const parseCSVContent = (csvText: string): { columns: string[], rows: RowData[] } => {
    const lines = csvText.trim().split('\n');
    if (lines.length === 0) {
      return { columns: [], rows: [] };
    }

    // Parse header row
    const columns = parseCSVLine(lines[0]);

    // Parse data rows
    const rows: RowData[] = [];
    for (let i = 1; i < lines.length; i++) {
      const values = parseCSVLine(lines[i]);
      if (values.length === columns.length) {
        const row: RowData = {};
        columns.forEach((col, index) => {
          row[col] = values[index];
        });
        rows.push(row);
      }
    }

    return { columns, rows };
  };

  // Parse a single CSV line handling quoted values
  const parseCSVLine = (line: string): string[] => {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];

      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++; // Skip next quote
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }

    result.push(current.trim());
    return result;
  };

  const onGridReady = () => {
    // Auto-size columns when grid is ready
  };

  const exportToCSV = () => {
    const headers = columnDefs.map(col => col.field).join(',');
    const rows = rowData.map(row =>
      columnDefs.map(col => {
        const value = row[col.field!];
        // Quote values that contain commas or quotes
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      }).join(',')
    );
    const csv = [headers, ...rows].join('\n');

    // Download CSV file
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${document.metadata.name}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className={styles.excelViewer}>
        <div className={styles.loadingContainer}>
          <Loader size={32} className={styles.spinner} />
          <p>Loading spreadsheet data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.excelViewer}>
        <div className={styles.errorContainer}>
          <p className={styles.errorMessage}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.excelViewer}>
      <div className={styles.excelToolbar}>
        <button onClick={exportToCSV} className={styles.toolbarButton}>
          Export to CSV
        </button>
        <span className={styles.rowCount}>
          {rowData.length} rows × {columnDefs.length} columns
        </span>
      </div>

      <div className="ag-theme-alpine" style={{ height: '100%', width: '100%' }}>
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          onGridReady={onGridReady}
          animateRows={true}
          rowSelection="multiple"
          suppressRowClickSelection={true}
          enableCellTextSelection={true}
          ensureDomOrder={true}
        />
      </div>
    </div>
  );
};