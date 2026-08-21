import React, { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, GridApi } from 'ag-grid-community';

import { 
  ModuleRegistry, 
  AllCommunityModule, 
  themeQuartz 
} from 'ag-grid-community';

import './TradeHistory.css';

ModuleRegistry.registerModules([AllCommunityModule]);

// AG Grid Custom Theme Builder Integration
export const myTheme = themeQuartz.withParams({
  accentColor: "#1D5FED",
  backgroundColor: "#111C34",
  borderColor: "#CCC8C829",
  borderRadius: 6,
  browserColorScheme: "dark",
  buttonActiveBorder: true,
  buttonHoverBorder: true,
  cellHorizontalPaddingScale: 1,
  checkboxCheckedBackgroundColor: "#1F51F4",
  chromeBackgroundColor: {
    ref: "foregroundColor",
    mix: 0.07,
    onto: "backgroundColor"
  },
  fontFamily: {
    googleFont: "Roboto"
  },
  fontSize: 14,
  fontWeight: 300, // Enables Roboto Light for grid rows
  foregroundColor: "#FFF",
  headerBackgroundColor: "#232C3E",
  headerFontWeight: 500,
  headerVerticalPaddingScale: 0.9977901786,
  iconSize: 16,
  oddRowBackgroundColor: "#122747",
  spacing: 8,
  tabBarBorder: true,
  wrapperBorderRadius: 8
});

// Icon Components
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

const formatCurrency = (value: number | null | undefined) => {
  if (value == null || isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const fetchTrades = async () => {
  const response = await fetch('http://localhost:8000/api/v1/trades/');
  if (!response.ok) throw new Error(`Failed to fetch trades: ${response.status}`);
  const data = await response.json();
  return Array.isArray(data) ? data : data.spread_executions || [];
};

export default function TradeHistory() {
  const [gridApi, setGridApi] = useState<GridApi | null>(null);
  const [activeTab, setActiveTab] = useState<'columns' | 'filters' | 'actions' | null>('columns');
  const [columnSearch, setColumnSearch] = useState('');
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);

  const initialColumns: (ColDef & { field: string })[] = useMemo(() => [
    { field: 'underlying', headerName: 'Ticker', width: 100, pinned: 'left' },
    { field: 'strategy_type', headerName: 'Strategy', width: 170 },
    { field: 'execution_side', headerName: 'Side', width: 100 },
    { field: 'net_cash_flow', headerName: 'Type', width: 100 },
    { field: 'spread_units', headerName: 'Qty', width: 80 },
    { field: 'contract_legs', headerName: 'Legs', width: 80 },
    { field: 'unique_strikes', headerName: 'Strikes', width: 90 },
    { field: 'dte', headerName: 'DTE', width: 80 },
    { field: 'entry_fill_cashflow', headerName: 'Fill Cash Flow', width: 140, valueFormatter: (params) => formatCurrency(params.value) },
    { field: 'total_commissions', headerName: 'Commissions', width: 130, valueFormatter: (params) => formatCurrency(params.value) },
    { field: 'entry_efficiency_pct', headerName: 'Efficiency %', width: 120, valueFormatter: (p) => p.value == null ? '—' : `${(p.value * 100).toFixed(2)}%` },
    { field: 'order_type', headerName: 'Order Type', width: 110 },
    { field: 'order_id', headerName: 'Order ID', width: 140 },
    { field: 'order_reference', headerName: 'Order Ref', width: 130 },
    { field: 'is_user_overridden', headerName: 'Overridden', width: 110 },
    { field: 'created_at', headerName: 'Ingested At', width: 170, valueFormatter: (p) => p.value ? new Date(p.value).toLocaleString() : '—' },
  ], []);

  const [columnOrder, setColumnOrder] = useState<string[]>(() => initialColumns.map(c => c.field));
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>(() =>
    initialColumns.reduce((acc, col) => ({ ...acc, [col.field]: true }), {})
  );

  const { data: rowData, isLoading, isError, error } = useQuery({
    queryKey: ['trades'],
    queryFn: fetchTrades,
  });

  const onGridReady = useCallback((params: { api: GridApi }) => {
    setGridApi(params.api);
  }, []);

  const colDefs = useMemo(() => {
    const colMap = new Map(initialColumns.map((col) => [col.field, col]));
    return columnOrder
      .map((field) => colMap.get(field))
      .filter((col): col is ColDef & { field: string } => col !== undefined)
      .map((col) => ({
        ...col,
        hide: !visibleColumns[col.field],
      }));
  }, [initialColumns, columnOrder, visibleColumns]);

  const allSelected = useMemo(() => {
    return initialColumns.every((col) => visibleColumns[col.field]);
  }, [initialColumns, visibleColumns]);

  const toggleMasterSelect = () => {
    const nextState = !allSelected;
    setVisibleColumns(
      initialColumns.reduce((acc, col) => ({ ...acc, [col.field]: nextState }), {})
    );
  };

  const toggleColumn = (field: string) => {
    setVisibleColumns((prev) => ({ ...prev, [field]: !prev[field] }));
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

  if (isLoading) return <div className="status-loading">Fetching executions from DuckDB...</div>;
  if (isError) return <div className="status-error">Error: {(error as Error).message}</div>;

  return (
    <div className="trade-history-container">
      <div className="table-card-wrapper">
        {/* Top Toolbar Slot for future controls & feature buttons */}
        <div className="grid-toolbar-slot">
          <div>
            <h2 className="trade-history-title">Trade History & Reconstruction</h2>
            <p className="trade-history-subtitle">
              Live view of your geometric execution fingerprints.
            </p>
          </div>
          {/* Place feature buttons or actions here */}
        </div>

        <div className="workspace-layout">
          <div className="grid-wrapper">
            <AgGridReact
              theme={myTheme}
              rowData={rowData}
              columnDefs={colDefs}
              defaultColDef={{ sortable: true, filter: true, resizable: true }}
              rowSelection="single"
              pagination={true}
              paginationPageSize={50}
              onGridReady={onGridReady}
            />
          </div>

          {/* Side Tool Panel */}
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
                    Click column headers in the table to apply advanced filters.
                  </p>
                </>
              )}

              {activeTab === 'actions' && (
                <>
                  <h3 className="sidebar-title">Table Actions</h3>
                  <button className="action-button" onClick={exportCsv}>Export to CSV</button>
                  <button className="action-button" onClick={autoSizeAll}>Fit Columns to Screen</button>
                </>
              )}
            </div>
          )}

          {/* Vertical Tabs Bar */}
          <div className="sidebar-tabs">
            <button
              className={`tab-button ${activeTab === 'columns' ? 'active' : ''}`}
              onClick={() => setActiveTab(activeTab === 'columns' ? null : 'columns')}
            >
              Columns
            </button>
            <button
              className={`tab-button ${activeTab === 'filters' ? 'active' : ''}`}
              onClick={() => setActiveTab(activeTab === 'filters' ? null : 'filters')}
            >
              Filters
            </button>
            <button
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