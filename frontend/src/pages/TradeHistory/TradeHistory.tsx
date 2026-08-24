import React, { useState, useMemo, useCallback } from 'react';
import type { GridApi } from 'ag-grid-community';
import { MasterTradeGrid } from '../../components/ag_grid/MasterTradeGrid';
import { defaultTradeColumnDefs } from '../../features/trades/TradeTable/columns';
import './TradeHistory.css';

const CustomCheckbox = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => (
  <button 
    type="button" 
    className={`custom-checkbox ${checked ? 'checked' : ''}`}
    onClick={(e) => {
      e.stopPropagation();
      onChange();
    }}
  >
    {checked && (
      <svg width="11" height="9" viewBox="0 0 12 10" fill="none">
        <path d="M1 5L4.5 8.5L11 1.5" stroke="#101826" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    )}
  </button>
);

const GripIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" className="drag-handle-icon">
    <circle cx="5" cy="3" r="1.5" />
    <circle cx="11" cy="3" r="1.5" />
    <circle cx="5" cy="8" r="1.5" />
    <circle cx="11" cy="8" r="1.5" />
    <circle cx="5" cy="13" r="1.5" />
    <circle cx="11" cy="13" r="1.5" />
  </svg>
);

const SearchIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" className="search-icon">
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

export default function TradeHistory() {
  const [gridApi, setGridApi] = useState<GridApi | null>(null);
  const [activeTab, setActiveTab] = useState<'columns' | 'filters' | 'actions' | null>('columns');
  const [columnSearch, setColumnSearch] = useState('');
  const [quickFilterText, setQuickFilterText] = useState('');
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);

  const initialColumns = useMemo(() => {
    return defaultTradeColumnDefs
      .map((col) => ({
        field: (col.field || col.colId || '') as string,
        headerName: (col.headerName || col.field || '') as string,
      }))
      .filter((col) => col.field !== '');
  }, []);

  const [columnOrder, setColumnOrder] = useState<string[]>(() => initialColumns.map((c) => c.field));
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>(() =>
    initialColumns.reduce((acc, col) => ({ ...acc, [col.field]: true }), {})
  );

  const handleGridReady = useCallback((params: { api: GridApi }) => {
    setGridApi(params.api);
  }, []);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    setQuickFilterText(text);
    if (gridApi) {
      gridApi.setGridOption('quickFilterText', text);
    }
  };

  const toggleColumn = (field: string) => {
    const nextVisible = !visibleColumns[field];
    setVisibleColumns((prev) => ({ ...prev, [field]: nextVisible }));
    if (gridApi) {
      gridApi.setColumnsVisible([field], nextVisible);
    }
  };

  const allSelected = useMemo(() => {
    return initialColumns.every((col) => visibleColumns[col.field]);
  }, [initialColumns, visibleColumns]);

  const toggleMasterSelect = () => {
    const nextState = !allSelected;
    const updatedVisibility = initialColumns.reduce(
      (acc, col) => ({ ...acc, [col.field]: nextState }),
      {}
    );
    setVisibleColumns(updatedVisibility);
    if (gridApi) {
      const allFields = initialColumns.map((col) => col.field);
      gridApi.setColumnsVisible(allFields, nextState);
    }
  };

  const handleDragStart = (index: number) => {
    setDraggedIdx(index);
  };

  const handleDragOver = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (draggedIdx === null || draggedIdx === targetIndex) return;

    const newOrder = [...columnOrder];
    const [draggedItem] = newOrder.splice(draggedIdx, 1);
    newOrder.splice(targetIndex, 0, draggedItem);

    setDraggedIdx(targetIndex);
    setColumnOrder(newOrder);

    if (gridApi) {
      gridApi.moveColumns([draggedItem], targetIndex);
    }
  };

  const handleDragEnd = () => {
    setDraggedIdx(null);
  };

  const filteredColumnFields = columnOrder.filter((field) => {
    const col = initialColumns.find((c) => c.field === field);
    return col?.headerName?.toLowerCase().includes(columnSearch.toLowerCase());
  });

  const exportCsv = () => gridApi?.exportDataAsCsv();
  const autoSizeAll = () => gridApi?.sizeColumnsToFit();

  return (
    <div className="trade-history-container">
      <div className="table-card-wrapper">
        <div className="grid-toolbar-slot">
          <div>
            <h2 className="trade-history-title">Transaction History</h2>
            <p className="trade-history-subtitle">
              Master Trade Journal &amp; Completed Spread Records
            </p>
          </div>
          <div className="search-input-wrapper">
            <SearchIcon />
            <input
              type="text"
              placeholder="Search all columns..."
              className="column-search-input"
              value={quickFilterText}
              onChange={handleSearchChange}
            />
          </div>
        </div>

        <div className="workspace-layout">
          <div className="grid-wrapper">
            <MasterTradeGrid onGridReady={handleGridReady} />
          </div>

          {activeTab && (
            <div className="sidebar-panel">
              {activeTab === 'columns' && (
                <>
                  <div className="columns-header-bar">
                    <CustomCheckbox checked={allSelected} onChange={toggleMasterSelect} />
                    <div className="search-input-wrapper">
                      <SearchIcon />
                      <input
                        type="text"
                        placeholder="Search..."
                        className="column-search-input"
                        value={columnSearch}
                        onChange={(e) => setColumnSearch(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="column-list">
                    {filteredColumnFields.map((field) => {
                      const col = initialColumns.find((c) => c.field === field);
                      const originalIdx = columnOrder.indexOf(field);
                      if (!col) return null;

                      return (
                        <div
                          key={field}
                          className={`column-item ${draggedIdx === originalIdx ? 'dragging' : ''}`}
                          draggable
                          onDragStart={() => handleDragStart(originalIdx)}
                          onDragOver={(e) => handleDragOver(e, originalIdx)}
                          onDragEnd={handleDragEnd}
                          onClick={() => toggleColumn(field)}
                        >
                          <CustomCheckbox
                            checked={!!visibleColumns[field]}
                            onChange={() => toggleColumn(field)}
                          />
                          <GripIcon />
                          <span className="column-label">{col.headerName}</span>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}

              {activeTab === 'filters' && (
                <>
                  <h3 className="sidebar-title">Quick Filters</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                    Filter directly within column headers or use the global search input above.
                  </p>
                </>
              )}

              {activeTab === 'actions' && (
                <>
                  <h3 className="sidebar-title">Table Actions</h3>
                  <button type="button" className="action-button" onClick={exportCsv}>
                    Export to CSV
                  </button>
                  <button type="button" className="action-button" onClick={autoSizeAll}>
                    Fit Columns to Screen
                  </button>
                </>
              )}
            </div>
          )}

          <div className="sidebar-tabs">
            <button
              type="button"
              className={`tab-button ${activeTab === 'columns' ? 'active' : ''}`}
              onClick={() => setActiveTab(activeTab === 'columns' ? null : 'columns')}
            >
              Columns
            </button>
            <button
              type="button"
              className={`tab-button ${activeTab === 'filters' ? 'active' : ''}`}
              onClick={() => setActiveTab(activeTab === 'filters' ? null : 'filters')}
            >
              Filters
            </button>
            <button
              type="button"
              className={`tab-button ${activeTab === 'actions' ? 'active' : ''}`}
              onClick={() => setActiveTab(activeTab === 'actions' ? null : 'actions')}
            >
              Table Actions
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}