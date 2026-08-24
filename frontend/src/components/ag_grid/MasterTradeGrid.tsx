import React, { useMemo, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, GridReadyEvent, GetRowIdParams, SizeColumnsToFitGridStrategy } from 'ag-grid-community';
import type { CompletedTradeRow } from '../../features/trades/types';
import { useCompletedTrades } from '../../features/trades/api';
import { defaultTradeColumnDefs } from '../../features/trades/TradeTable/columns';
import { myTheme } from './theme';
import './mastertradegrid.css';
import '../../features/trades/TradeTable/tradeTable.css';

interface MasterTradeGridProps {
  onGridReady?: (params: GridReadyEvent) => void;
}

export const MasterTradeGrid: React.FC<MasterTradeGridProps> = ({ onGridReady: externalOnGridReady }) => {
  const { data: rowData, isLoading } = useCompletedTrades();

  const defaultColDef = useMemo<ColDef<CompletedTradeRow>>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
  }), []);

  const columnDefs = useMemo<ColDef<CompletedTradeRow>[]>(() => defaultTradeColumnDefs, []);

  const autoSizeStrategy = useMemo<SizeColumnsToFitGridStrategy>(() => ({
    type: 'fitGridWidth',
  }), []);

  const handleGridReady = useCallback((params: GridReadyEvent) => {
    if (isLoading) params.api.showLoadingOverlay();
    if (externalOnGridReady) externalOnGridReady(params);
  }, [isLoading, externalOnGridReady]);

  const getRowId = useCallback(
    (params: GetRowIdParams<CompletedTradeRow>) => params.data.trade_package_id,
    []
  );

  return (
    <div className="master-trade-grid-container ag-theme-quartz-dark">
      <AgGridReact<CompletedTradeRow>
        theme={myTheme}
        rowData={rowData}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        autoSizeStrategy={autoSizeStrategy}
        rowHeight={42}
        onGridReady={handleGridReady}
        getRowId={getRowId}
      />
    </div>
  );
};