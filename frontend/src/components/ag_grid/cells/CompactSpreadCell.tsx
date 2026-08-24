import type { ICellRendererParams } from 'ag-grid-community';
import type { CompletedTradeRow, SpreadDisplaySchema } from '../../../features/trades/types';

/**
 * Two-line renderer for the canonical `spread_display` API payload.
 *
 * Classification, strike ordering, expiry formatting, and CSV formatting are
 * backend responsibilities. This component only renders the supplied payload.
 */
export function CompactSpreadCell({
  value,
}: ICellRendererParams<CompletedTradeRow, SpreadDisplaySchema>) {
  if (!value) return <>—</>;

  const { headline, detail, csv } = value;

  return (
    <div className="compact-spread-grid-cell" title={csv}>
      <div className="compact-spread-heading">{headline}</div>
      <div className="compact-spread-subtitle">{detail}</div>
    </div>
  );
}