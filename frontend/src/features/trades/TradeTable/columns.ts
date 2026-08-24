import type { ColDef } from 'ag-grid-community';
import type { CompletedTradeRow } from '../types';
import { CompactSpreadCell } from '../../../components/ag_grid/cells/CompactSpreadCell';
import {
  formatCurrency,
  formatDateTime,
  formatDuration,
  formatPercentage,
} from './formatters';

const EMPTY_VALUE = '—';

const isEmpty = (value: unknown): value is null | undefined | '' =>
  value === null || value === undefined || value === '';

/**
 * Decimal values arrive as exact JSON strings from Pydantic. Number conversion
 * is deliberately limited to AG Grid display, filter, sort, and colour rules.
 */
const toFiniteNumber = (value: unknown): number | null => {
  if (isEmpty(value)) return null;

  const numericValue = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
};

const decimalComparator = (left: unknown, right: unknown): number => {
  const leftNumber = toFiniteNumber(left);
  const rightNumber = toFiniteNumber(right);

  if (leftNumber === null && rightNumber === null) return 0;
  if (leftNumber === null) return -1;
  if (rightNumber === null) return 1;
  return leftNumber - rightNumber;
};

const formatText = (value: unknown): string => (isEmpty(value) ? EMPTY_VALUE : String(value));

const formatList = (value: unknown): string =>
  Array.isArray(value) && value.length > 0 ? value.join(', ') : EMPTY_VALUE;

const formatRecord = (value: unknown): string =>
  value && typeof value === 'object' ? JSON.stringify(value) : EMPTY_VALUE;

const formatDecimalCurrency = (value: unknown): string => {
  const numericValue = toFiniteNumber(value);
  return numericValue === null ? EMPTY_VALUE : formatCurrency(numericValue);
};

const formatDecimalPercentage = (value: unknown): string => {
  const numericValue = toFiniteNumber(value);
  return numericValue === null ? EMPTY_VALUE : formatPercentage(numericValue);
};

const formatNullableDateTime = (value: unknown): string =>
  isEmpty(value) ? EMPTY_VALUE : formatDateTime(String(value));

const formatNullableDuration = (value: unknown): string => {
  const numericValue = toFiniteNumber(value);
  return numericValue === null ? EMPTY_VALUE : formatDuration(numericValue);
};

const formatNullableNumber = (value: unknown): string => {
  const numericValue = toFiniteNumber(value);
  return numericValue === null ? EMPTY_VALUE : new Intl.NumberFormat('en-US').format(numericValue);
};

const pnlClassRules = {
  'pnl-positive': (params: { value: unknown }) => (toFiniteNumber(params.value) ?? 0) > 0,
  'pnl-negative': (params: { value: unknown }) => (toFiniteNumber(params.value) ?? 0) < 0,
};

/**
 * Canonical AG Grid fields. `trade_package_id` is supplied to the grid's
 * getRowId callback; it is intentionally not a visible business column.
 */
export const defaultTradeColumnDefs: ColDef<CompletedTradeRow>[] = [
  {
    field: 'opened_at',
    headerName: 'Open Timestamp',
    initialWidth: 160,
    minWidth: 140,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatNullableDateTime(params.value),
  },
  {
    field: 'closed_at',
    headerName: 'Close Timestamp',
    initialWidth: 160,
    minWidth: 140,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatNullableDateTime(params.value),
  },
  {
    field: 'total_duration_seconds',
    headerName: 'Total Duration',
    initialWidth: 130,
    minWidth: 110,
    type: 'numericColumn',
    comparator: decimalComparator,
    filter: 'agNumberColumnFilter',
    valueFormatter: (params) => formatNullableDuration(params.value),
  },
  {
    field: 'ticker',
    headerName: 'Ticker',
    initialWidth: 100,
    minWidth: 90,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatText(params.value),
  },
  {
    field: 'spread_display',
    headerName: 'Spread',
    flex: 2,
    minWidth: 250,
    cellRenderer: CompactSpreadCell,
    filter: 'agTextColumnFilter',
    filterValueGetter: (params) => params.data?.spread_display.csv ?? '',
    tooltipValueGetter: (params) => params.data?.spread_display.csv ?? EMPTY_VALUE,
    comparator: (left, right) =>
      String(left?.csv ?? '').localeCompare(String(right?.csv ?? '')),
  },
  {
    field: 'strategy_name',
    headerName: 'Strategy',
    initialWidth: 170,
    minWidth: 140,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatText(params.value),
  },
  {
    field: 'position_side',
    headerName: 'Position',
    initialWidth: 100,
    minWidth: 90,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatText(params.value),
  },
  {
    field: 'gross_notional',
    headerName: 'Total Volume',
    initialWidth: 145,
    minWidth: 120,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    filterValueGetter: (params) => toFiniteNumber(params.data?.gross_notional),
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'dte_at_open',
    headerName: 'DTE (Open)',
    initialWidth: 110,
    minWidth: 90,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableNumber(params.value),
  },
  {
    field: 'realized_pnl',
    headerName: 'PnL',
    initialWidth: 130,
    minWidth: 110,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    filterValueGetter: (params) => toFiniteNumber(params.data?.realized_pnl),
    valueFormatter: (params) => formatDecimalCurrency(params.value),
    cellClassRules: pnlClassRules,
  },
  {
    field: 'pnl_percentage',
    headerName: '% Return',
    initialWidth: 110,
    minWidth: 90,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    filterValueGetter: (params) => toFiniteNumber(params.data?.pnl_percentage),
    valueFormatter: (params) => formatDecimalPercentage(params.value),
    cellClassRules: pnlClassRules,
  },
  {
    field: 'total_commissions',
    headerName: 'Total Commission',
    initialWidth: 150,
    minWidth: 120,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    filterValueGetter: (params) => toFiniteNumber(params.data?.total_commissions),
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'total_executions',
    headerName: 'Total Executions',
    initialWidth: 130,
    minWidth: 100,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableNumber(params.value),
  },

  // Hidden columns remain available to the column chooser and exports.
  {
    field: 'strikes',
    headerName: 'Strikes',
    hide: true,
    filter: 'agTextColumnFilter',
    filterValueGetter: (params) => params.data?.strikes.join('/') ?? '',
    valueFormatter: (params) => formatList(params.value),
  },
  {
    field: 'expiries',
    headerName: 'Expiries',
    hide: true,
    filter: 'agTextColumnFilter',
    filterValueGetter: (params) => params.data?.expiries.join(', ') ?? '',
    valueFormatter: (params) => formatList(params.value),
  },
  {
    field: 'open_position',
    headerName: 'Open Position',
    hide: true,
    filter: 'agSetColumnFilter',
    valueFormatter: (params) => (params.value ? 'Open' : 'Closed'),
  },
  {
    field: 'dte_by_expiry',
    headerName: 'DTE by Expiry',
    hide: true,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatRecord(params.value),
  },
  {
    field: 'leg_net_quantities',
    headerName: 'Leg Net Quantities',
    hide: true,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatRecord(params.value),
  },
  {
    field: 'unrealized_pnl_percentage',
    headerName: 'Unrealized % Return',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalPercentage(params.value),
  },
  { field: 'currency', headerName: 'Currency', hide: true, filter: 'agTextColumnFilter' },
  { field: 'underlying', headerName: 'Underlying', hide: true, filter: 'agTextColumnFilter' },
  { field: 'asset_type', headerName: 'Asset Type', hide: true, filter: 'agTextColumnFilter' },
  {
    field: 'net_open_cash_flow',
    headerName: 'Open Price',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'net_close_cash_flow',
    headerName: 'Close Price',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'open_vwap_by_leg',
    headerName: 'Open VWAP by Leg',
    hide: true,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatRecord(params.value),
  },
  {
    field: 'close_vwap_by_leg',
    headerName: 'Close VWAP by Leg',
    hide: true,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatRecord(params.value),
  },
  {
    field: 'total_buy_quantity',
    headerName: 'Total Buy Quantity',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableNumber(params.value),
  },
  {
    field: 'total_sell_quantity',
    headerName: 'Total Sell Quantity',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableNumber(params.value),
  },
  {
    field: 'tags',
    headerName: 'Tags',
    hide: true,
    filter: 'agTextColumnFilter',
    filterValueGetter: (params) => params.data?.tags.join(', ') ?? '',
    valueFormatter: (params) => formatList(params.value),
  },
  {
    field: 'total_fees',
    headerName: 'Total Fees',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  { field: 'day', headerName: 'Day', hide: true, filter: 'agTextColumnFilter' },
  {
    field: 'month_day',
    headerName: 'Month day',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
  },
  { field: 'trading_account', headerName: 'Trading Account', hide: true, filter: 'agTextColumnFilter' },
  {
    field: 'month',
    headerName: 'Month',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
  },
  {
    field: 'tag_groups',
    headerName: 'Tag Groups',
    hide: true,
    filter: 'agTextColumnFilter',
    filterValueGetter: (params) => params.data?.tag_groups.join(', ') ?? '',
    valueFormatter: (params) => formatList(params.value),
  },
  { field: 'notes', headerName: 'Notes', hide: true, filter: 'agTextColumnFilter' },
  {
    field: 'current_pnl',
    headerName: 'Current PnL',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
    cellClassRules: pnlClassRules,
  },
  {
    field: 'stop_loss',
    headerName: 'Stop Loss',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'profit_target',
    headerName: 'Profit Target',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'stop_loss_percentage',
    headerName: 'Stop Loss (%)',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalPercentage(params.value),
  },
  {
    field: 'profit_target_percentage',
    headerName: 'Profit Target (%)',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalPercentage(params.value),
  },
  {
    field: 'positive_pnl_time_seconds',
    headerName: 'Positive PnL Time',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableDuration(params.value),
  },
  {
    field: 'negative_pnl_time_seconds',
    headerName: 'Negative PnL Time',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableDuration(params.value),
  },
  {
    field: 'max_running_pnl',
    headerName: 'Max Running PnL',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'min_running_pnl',
    headerName: 'Min Running PnL',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'trade_mae',
    headerName: 'Trade MAE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'trade_mfe',
    headerName: 'Trade MFE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'price_mae',
    headerName: 'Price MAE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatText(params.value),
  },
  {
    field: 'price_mfe',
    headerName: 'Price MFE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatText(params.value),
  },
  {
    field: 'mfe_mae_ratio',
    headerName: 'MFE/MAE Ratio',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatText(params.value),
  },
  {
    field: 'price_mfe_percentage',
    headerName: 'Price MFE (%)',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalPercentage(params.value),
  },
  {
    field: 'price_mae_percentage',
    headerName: 'Price MAE (%)',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalPercentage(params.value),
  },
  {
    field: 'tick_mfe',
    headerName: 'Tick MFE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatText(params.value),
  },
  {
    field: 'tick_mae',
    headerName: 'Tick MAE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatText(params.value),
  },
  {
    field: 'mfe_at',
    headerName: 'MFE Date',
    hide: true,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatNullableDateTime(params.value),
  },
  {
    field: 'mae_at',
    headerName: 'MAE Date',
    hide: true,
    filter: 'agTextColumnFilter',
    valueFormatter: (params) => formatNullableDateTime(params.value),
  },
  {
    field: 'time_till_mfe_seconds',
    headerName: 'Time till MFE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableDuration(params.value),
  },
  {
    field: 'time_till_mae_seconds',
    headerName: 'Time till MAE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableDuration(params.value),
  },
  {
    field: 'time_after_mfe_seconds',
    headerName: 'Time after MFE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableDuration(params.value),
  },
  {
    field: 'time_after_mae_seconds',
    headerName: 'Time after MAE',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatNullableDuration(params.value),
  },
  {
    field: 'eod_exit_pnl',
    headerName: 'EOD Exit PnL',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalCurrency(params.value),
  },
  {
    field: 'eod_exit_efficiency',
    headerName: 'EOD Exit Efficiency',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatDecimalPercentage(params.value),
  },
  {
    field: 'eod_exit_r_value',
    headerName: 'EOD Exit R-value',
    hide: true,
    type: 'numericColumn',
    filter: 'agNumberColumnFilter',
    comparator: decimalComparator,
    valueFormatter: (params) => formatText(params.value),
  },
];