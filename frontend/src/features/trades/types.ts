/**
 * Canonical API contract for one ProfitMax trade package.
 *
 * A row represents one grouped trade package, never an IBKR execution or an
 * individual option leg. Decimal values are JSON strings because the FastAPI
 * schema serializes Python Decimal exactly; convert them only at display or
 * calculation boundaries.
 */

export type ApiDecimal = string;
export type IsoDate = string;
export type IsoDateTime = string;

export type PackagePositionSide = 'Long' | 'Short' | 'Mixed' | 'Flat';

export type Weekday =
  | 'Monday'
  | 'Tuesday'
  | 'Wednesday'
  | 'Thursday'
  | 'Friday'
  | 'Saturday'
  | 'Sunday';

/** Payload consumed directly by the two-line AG Grid Spread cell renderer. */
export interface SpreadDisplaySchema {
  headline: string;
  detail: string;
  csv: string;
}

/**
 * Canonical FastAPI response for one completed or currently-open trade package.
 * `closed_at` and closed-trade metrics are null while the package remains open.
 */
export interface CompletedTradeRow {
  trade_package_id: string;
  opened_at: IsoDateTime;
  closed_at: IsoDateTime | null;
  total_duration_seconds: number | null;

  ticker: string;
  spread_display: SpreadDisplaySchema;
  strategy_name: string;

  strikes: ApiDecimal[];
  expiries: IsoDate[];
  open_position: boolean;
  dte_at_open: number | null;
  dte_by_expiry: Record<IsoDate, number>;
  position_side: PackagePositionSide;
  leg_net_quantities: Record<string, number>;

  realized_pnl: ApiDecimal;
  pnl_percentage: ApiDecimal | null;
  unrealized_pnl_percentage: ApiDecimal | null;
  currency: string;
  underlying: string | null;
  asset_type: string;

  net_open_cash_flow: ApiDecimal | null;
  net_close_cash_flow: ApiDecimal | null;
  open_vwap_by_leg: Record<string, ApiDecimal>;
  close_vwap_by_leg: Record<string, ApiDecimal>;

  total_buy_quantity: number;
  total_sell_quantity: number;
  tags: string[];
  total_commissions: ApiDecimal;
  total_fees: ApiDecimal;

  day: Weekday;
  month_day: number;
  trading_account: string;
  total_executions: number;
  month: number;
  gross_notional: ApiDecimal;
  tag_groups: string[];
  notes: string | null;

  current_pnl: ApiDecimal | null;
  stop_loss: ApiDecimal | null;
  profit_target: ApiDecimal | null;
  stop_loss_percentage: ApiDecimal | null;
  profit_target_percentage: ApiDecimal | null;

  positive_pnl_time_seconds: number | null;
  negative_pnl_time_seconds: number | null;
  max_running_pnl: ApiDecimal | null;
  min_running_pnl: ApiDecimal | null;
  trade_mae: ApiDecimal | null;
  trade_mfe: ApiDecimal | null;
  price_mae: ApiDecimal | null;
  price_mfe: ApiDecimal | null;
  mfe_mae_ratio: ApiDecimal | null;
  price_mfe_percentage: ApiDecimal | null;
  price_mae_percentage: ApiDecimal | null;
  tick_mfe: ApiDecimal | null;
  tick_mae: ApiDecimal | null;
  mfe_at: IsoDateTime | null;
  mae_at: IsoDateTime | null;
  time_till_mfe_seconds: number | null;
  time_till_mae_seconds: number | null;
  time_after_mfe_seconds: number | null;
  time_after_mae_seconds: number | null;
  eod_exit_pnl: ApiDecimal | null;
  eod_exit_efficiency: ApiDecimal | null;
  eod_exit_r_value: ApiDecimal | null;
}