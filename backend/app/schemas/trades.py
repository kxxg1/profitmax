"""Canonical Pydantic v2 contract for ProfitMax completed-trade grid rows.

This model is the API projection for one *trade package*, never for an
individual IBKR execution or option leg.  The classifier owns package grouping
and strategy identification; this module validates and serializes the already
grouped result for FastAPI and AG Grid.

Money and prices deliberately use :class:`decimal.Decimal`.  JSON responses
therefore emit these values as strings, preserving broker precision instead of
silently converting them to binary floating point in JavaScript.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, TypeAlias, cast

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.config import JsonDict

__all__ = [
    "CompletedTradeRow",
    "PackagePositionSide",
    "SpreadDisplaySchema",
    "Weekday",
    "completed_trade_from_duckdb_row",
    "completed_trade_grid_payload",
]


# Domain types are intentionally separate from DuckDB physical types.  The
# persistence migration should map Money and Price to explicit DECIMAL(p, s),
# UTCDateTime to TIMESTAMPS, and lists to DuckDB LIST columns or normalised
# child tables.  Do not put DuckDB VARCHAR in this Pydantic contract.
NonEmptyText: TypeAlias = Annotated[str, Field(min_length=1, max_length=2_000)]
Ticker: TypeAlias = Annotated[
    str,
    Field(
        min_length=1,
        max_length=16,
        pattern=r"^[A-Z0-9][A-Z0-9.\-]{0,15}$",
        description="Uppercase underlying identifier, not an option contract symbol.",
    ),
]
CurrencyCode: TypeAlias = Annotated[
    str,
    Field(pattern=r"^[A-Z]{3}$", description="ISO 4217 currency code."),
]
Money: TypeAlias = Annotated[
    Decimal,
    Field(max_digits=24, decimal_places=8, description="Exact monetary amount."),
]
NonNegativeMoney: TypeAlias = Annotated[
    Decimal,
    Field(ge=0, max_digits=24, decimal_places=8, description="Exact non-negative monetary amount."),
]
Price: TypeAlias = Annotated[
    Decimal,
    Field(max_digits=24, decimal_places=8, description="Exact price or price distance."),
]
Percent: TypeAlias = Annotated[
    Decimal,
    Field(max_digits=16, decimal_places=8, description="Percentage expressed as 100 = 100%."),
]
NonNegativeInt: TypeAlias = Annotated[int, Field(ge=0)]
MonthNumber: TypeAlias = Annotated[int, Field(ge=1, le=12)]
MonthDay: TypeAlias = Annotated[int, Field(ge=1, le=31)]


class Weekday(str, Enum):
    """Exchange-local weekday derived from ``opened_at``."""

    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class PackagePositionSide(str, Enum):
    """Aggregate package direction; per-leg positions stay in ``leg_net_quantities``."""

    LONG = "Long"
    SHORT = "Short"
    MIXED = "Mixed"
    FLAT = "Flat"


def _metadata(label: str, source: str, definition: str, formula: str) -> JsonDict:
    """Return schema metadata retained from the data dictionary."""

    return {
        "label": label,
        "source": source,
        "definition": definition,
        "formula": formula,
    }


class SpreadDisplaySchema(BaseModel):
    """Exact two-line renderer payload for the AG Grid ``Spread`` column.

    ``headline`` is the first line. ``detail`` is always the second line:
    recognised strategies use their strategy name, custom packages use the
    ordered strikes plus the logical option-leg count (for example
    ``7400/7470/7555 · 3L``), and stock-only packages use ``Long Stock`` or
    ``Short Stock``. ``csv`` is deterministically derived so it cannot drift
    from the two displayed lines.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)

    headline: NonEmptyText = Field(description="First visual line of the Spread cell.")
    detail: NonEmptyText = Field(description="Second visual line of the Spread cell.")
    csv: str | None = Field(
        default=None,
        description="Single-line export/tool-tip representation: 'headline | detail'.",
    )

    @field_validator("headline", "detail")
    @classmethod
    def _single_line_text(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("Spread headline and detail must each be a single line.")
        return value

    @model_validator(mode="after")
    def _derive_or_validate_csv(self) -> "SpreadDisplaySchema":
        expected = f"{self.headline} | {self.detail}"
        if self.csv is None:
            self.csv = expected
        elif self.csv != expected:
            raise ValueError("spread_display.csv must equal 'headline | detail'.")
        return self


class CompletedTradeRow(BaseModel):
    """Validated completed-trade package projection used by FastAPI and AG Grid.

    ``from_attributes=True`` supports ORM/record-like objects.  A normal
    DuckDB ``fetchall()`` result is a tuple, not an attribute object; use
    :func:`completed_trade_from_duckdb_row` to pair that tuple with its SELECT
    column names before validating it.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Identity and chronological package state.
    trade_package_id: NonEmptyText = Field(
        ...,
        json_schema_extra=_metadata(
            "Trade ID",
            "System",
            "Stable package primary key used by AG Grid getRowId and FastAPI routes.",
            "Deterministic package UUID or immutable parser key; never an execution ID.",
        ),
    )
    opened_at: AwareDatetime = Field(
        ...,
        json_schema_extra=_metadata(
            "Open Timestamp",
            "Calculated (DuckDB)",
            "Timestamp of the first execution that creates the grouped package position.",
            "min(execution_timestamp for opening fills in trade_group)",
        ),
    )
    closed_at: AwareDatetime | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Close Timestamp",
            "Calculated (DuckDB)",
            "Timestamp of the final execution that reduces every package leg to zero; NULL while open.",
            "max(execution_timestamp for closing fills) only when every net_leg_qty = 0",
        ),
    )
    total_duration_seconds: NonNegativeInt | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Total Duration",
            "Calculated (DuckDB)",
            "Elapsed seconds from first opening fill to final close; NULL while open.",
            "closed_at - opened_at",
        ),
    )

    # Canonical grid identity, display, and classifier fields.
    ticker: Ticker = Field(
        ...,
        json_schema_extra=_metadata(
            "Ticker",
            "Calculated (Python Projection)",
            "Canonical uppercase economic underlying; never an option contract symbol.",
            "one underlying -> that ticker; otherwise MULTI",
        ),
    )
    spread_display: SpreadDisplaySchema = Field(
        ...,
        json_schema_extra=_metadata(
            "Spread",
            "Calculated (Python Presentation Projection)",
            "Structured two-line payload showing the actual package structure.",
            "Recognised: strikes + strategy; Custom Multi-Leg: strikes + logical option-leg count; stock-only: Long Stock or Short Stock.",
        ),
    )
    strategy_name: NonEmptyText = Field(
        ...,
        json_schema_extra=_metadata(
            "Strategy",
            "Calculated (Python Classification)",
            "Canonical package classification displayed in the Strategy chip.",
            "Stock-only => Long Stock/Short Stock; recognised geometry => registered label; unrecognised multi-leg => Custom Multi-Leg; ambiguous => Review Required.",
        ),
    )

    # Structured option and position data.  Do not reconstruct these from
    # ``spread_display`` or its CSV export string.
    strikes: tuple[Price, ...] = Field(
        default_factory=tuple,
        json_schema_extra=_metadata(
            "Strikes",
            "Calculated (Python Projection)",
            "Ordered option strikes used by the logical opening legs; empty for stock-only packages.",
            "preserve classifier display order from normalised opening legs",
        ),
    )
    expiries: tuple[date, ...] = Field(
        default_factory=tuple,
        json_schema_extra=_metadata(
            "Expiries",
            "Calculated (Python Projection)",
            "Ordered option expiry dates used by the logical opening legs; empty for stock-only packages.",
            "preserve distinct expiry order from normalised opening legs",
        ),
    )
    open_position: bool = Field(
        ...,
        json_schema_extra=_metadata(
            "Open Position",
            "Calculated (DuckDB)",
            "True when any package leg has non-zero net quantity at the valuation timestamp.",
            "any(sum(signed_quantity) by conid != 0)",
        ),
    )
    dte_at_open: NonNegativeInt | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "DTE (Open)",
            "Calculated (DuckDB)",
            "DTE of the nearest option expiry at opening; NULL for stock-only packages.",
            "min(expiry - date(opened_at in exchange_timezone))",
        ),
    )
    dte_by_expiry: dict[date, NonNegativeInt] = Field(
        default_factory=dict,
        description="Complete per-expiry DTE mapping. Required to retain calendar/diagonal information.",
    )
    position_side: PackagePositionSide = Field(
        ...,
        json_schema_extra=_metadata(
            "Position",
            "Calculated (Python Projection)",
            "Aggregate package direction; per-contract signed quantities are stored separately.",
            "derive Long, Short, Mixed, or Flat from net_quantity_by_conid",
        ),
    )
    leg_net_quantities: dict[str, int] = Field(
        default_factory=dict,
        description="Signed net quantity keyed by immutable contract/conid identifier.",
    )

    # Amounts are Decimal, not float.  API JSON serializes Decimal as a string.
    realized_pnl: Money = Field(
        ...,
        json_schema_extra=_metadata(
            "PnL",
            "Calculated (DuckDB)",
            "Net realised package PnL after commissions and fees, in currency.",
            "sum(signed fill cash flow) - sum(commission) - sum(other fees)",
        ),
    )
    pnl_percentage: Percent | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "% Return",
            "Calculated (DuckDB)",
            "Realised PnL as a percentage of explicitly defined entry capital at risk.",
            "100 * realized_pnl / capital_at_risk when capital_at_risk > 0",
        ),
    )
    unrealized_pnl_percentage: Percent | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Unrealized % Return",
            "Calculated (market data + executions)",
            "Marked unrealised PnL as a percentage of the same capital-at-risk denominator.",
            "100 * current_pnl / capital_at_risk when capital_at_risk > 0",
        ),
    )
    currency: CurrencyCode = Field(
        ...,
        json_schema_extra=_metadata(
            "Currency",
            "IBKR Raw",
            "ISO currency in which package amounts are denominated.",
            "direct value; a multi-currency package must be normalised before this projection",
        ),
    )
    underlying: Ticker | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Underlying",
            "IBKR Raw / Derived Fallback",
            "Derivative underlying identifier; for stock or future it is normally the traded symbol.",
            "UnderlyingSymbol when present; otherwise Symbol",
        ),
    )
    asset_type: NonEmptyText = Field(
        ...,
        json_schema_extra=_metadata(
            "Asset Type",
            "Calculated (Python Projection)",
            "Package asset-class summary, for example OPT, STK, FUT, or MIXED.",
            "unique leg asset classes -> only value or MIXED",
        ),
    )
    net_open_cash_flow: Money | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Open Price",
            "Calculated (DuckDB)",
            "Package-level opening cash flow, not a per-leg VWAP; positive is received and negative is paid.",
            "sum(+qty*price*multiplier for SELL opening fills; -qty*price*multiplier for BUY opening fills)",
        ),
    )
    net_close_cash_flow: Money | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Close Price",
            "Calculated (DuckDB)",
            "Package-level closing cash flow, not a per-leg VWAP; positive is received and negative is paid.",
            "sum(+qty*price*multiplier for SELL closing fills; -qty*price*multiplier for BUY closing fills)",
        ),
    )
    open_vwap_by_leg: dict[str, Price] = Field(
        default_factory=dict,
        description="Entry VWAP by immutable contract/conid; kept distinct from package cash flow.",
    )
    close_vwap_by_leg: dict[str, Price] = Field(
        default_factory=dict,
        description="Exit VWAP by immutable contract/conid; kept distinct from package cash flow.",
    )
    total_buy_quantity: NonNegativeInt = Field(
        ...,
        json_schema_extra=_metadata(
            "Total Buy Quantity",
            "Calculated (DuckDB)",
            "Total units bought across all package executions; zero when there are no buys.",
            "coalesce(sum(quantity where side = BUY), 0)",
        ),
    )
    total_sell_quantity: NonNegativeInt = Field(
        ...,
        json_schema_extra=_metadata(
            "Total Sell Quantity",
            "Calculated (DuckDB)",
            "Total units sold across all package executions; zero when there are no sells.",
            "coalesce(sum(quantity where side = SELL), 0)",
        ),
    )
    tags: tuple[NonEmptyText, ...] = Field(
        default_factory=tuple,
        json_schema_extra=_metadata(
            "Tags",
            "User Input / Application",
            "User-assigned labels describing setup, mistake, rule adherence, or market context.",
            "ordered distinct tag names linked through the trade_tag join table",
        ),
    )
    total_commissions: NonNegativeMoney = Field(
        default=Decimal("0"),
        json_schema_extra=_metadata(
            "Total Commission",
            "Calculated (DuckDB)",
            "Total brokerage commission for all package executions.",
            "coalesce(sum(IBCommission), 0)",
        ),
    )
    total_fees: NonNegativeMoney = Field(
        default=Decimal("0"),
        json_schema_extra=_metadata(
            "Total Fees",
            "Calculated (DuckDB)",
            "Non-commission exchange, regulatory, tax, and transaction fees.",
            "coalesce(sum(non_commission_fee_components), 0)",
        ),
    )

    # Calendar, account, journal, and turnover fields.
    day: Weekday = Field(
        ...,
        json_schema_extra=_metadata(
            "Day",
            "Calculated (DuckDB)",
            "Exchange-local weekday on which the package opened.",
            "day_name(opened_at in exchange_timezone)",
        ),
    )
    month_day: MonthDay = Field(
        ...,
        json_schema_extra=_metadata(
            "Month day",
            "Calculated (DuckDB)",
            "Exchange-local day of month on which the package opened.",
            "date(opened_at in exchange_timezone).day",
        ),
    )
    trading_account: NonEmptyText = Field(
        ...,
        json_schema_extra=_metadata(
            "Trading Account",
            "IBKR Raw",
            "IBKR account identifier owning the package executions.",
            "direct value",
        ),
    )
    total_executions: NonNegativeInt = Field(
        ...,
        json_schema_extra=_metadata(
            "Total Executions",
            "Calculated (DuckDB)",
            "Number of distinct execution fills in the package.",
            "count distinct IBExecutionID; otherwise count unique normalised fill rows",
        ),
    )
    month: MonthNumber = Field(
        ...,
        json_schema_extra=_metadata(
            "Month",
            "Calculated (DuckDB)",
            "Exchange-local calendar month in which the package opened, from 1 to 12.",
            "date(opened_at in exchange_timezone).month",
        ),
    )
    gross_notional: NonNegativeMoney = Field(
        ...,
        json_schema_extra=_metadata(
            "Total Volume",
            "Calculated (DuckDB)",
            "Gross executed native-currency notional before fees; it is not spread units.",
            "sum(abs(quantity) * trade_price * multiplier for all fills)",
        ),
    )
    tag_groups: tuple[NonEmptyText, ...] = Field(
        default_factory=tuple,
        json_schema_extra=_metadata(
            "Tag Groups",
            "User Input / Application",
            "Parent categories associated with assigned tags, such as Setup, Regime, or Process.",
            "ordered distinct parent groups of assigned tags",
        ),
    )
    notes: str | None = Field(
        default=None,
        max_length=20_000,
        json_schema_extra=_metadata(
            "Notes",
            "User Input / Application",
            "Free-text journal annotation. Broker Notes/Codes belong in a separate broker_note field.",
            "user-entered text",
        ),
    )

    # Dynamic management and spread-level excursion analytics.
    current_pnl: Money | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Current PnL",
            "Calculated (market data + executions)",
            "Economic package PnL at the valuation timestamp, including marked open-leg value.",
            "executed signed cash flows + marked remaining-leg value - costs",
        ),
    )
    stop_loss: NonNegativeMoney | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Stop Loss",
            "User Input / Application",
            "Planned maximum loss stored as a positive currency amount.",
            "user-defined loss limit",
        ),
    )
    profit_target: NonNegativeMoney | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Profit Target",
            "User Input / Application",
            "Planned profit target stored as a positive currency amount.",
            "user-defined profit target",
        ),
    )
    stop_loss_percentage: Percent | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Stop Loss (%)",
            "Calculated (DuckDB)",
            "Stop-loss amount as a percentage of entry capital at risk.",
            "100 * stop_loss / capital_at_risk when capital_at_risk > 0",
        ),
    )
    profit_target_percentage: Percent | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Profit Target (%)",
            "Calculated (DuckDB)",
            "Profit-target amount as a percentage of entry capital at risk.",
            "100 * profit_target / capital_at_risk when capital_at_risk > 0",
        ),
    )
    positive_pnl_time_seconds: NonNegativeInt | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Positive PnL Time",
            "Calculated (market data + executions)",
            "Elapsed seconds for which marked package PnL was strictly positive.",
            "sum(snapshot interval where current_pnl > 0)",
        ),
    )
    negative_pnl_time_seconds: NonNegativeInt | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Negative PnL Time",
            "Calculated (market data + executions)",
            "Elapsed seconds for which marked package PnL was strictly negative.",
            "sum(snapshot interval where current_pnl < 0)",
        ),
    )
    max_running_pnl: Money | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Max Running PnL",
            "Calculated (market data + executions)",
            "Highest marked package PnL reached during the trade.",
            "max(current_pnl by snapshot)",
        ),
    )
    min_running_pnl: Money | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Min Running PnL",
            "Calculated (market data + executions)",
            "Lowest marked package PnL reached during the trade.",
            "min(current_pnl by snapshot)",
        ),
    )
    trade_mae: Money | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Trade MAE",
            "Calculated (market data + executions)",
            "Maximum adverse package PnL excursion; retained as a negative currency amount.",
            "min(current_pnl by snapshot)",
        ),
    )
    trade_mfe: Money | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Trade MFE",
            "Calculated (market data + executions)",
            "Maximum favourable package PnL excursion.",
            "max(current_pnl by snapshot)",
        ),
    )
    price_mae: Price | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Price MAE",
            "Calculated (market data + executions)",
            "Largest adverse movement in the marked package-price series; negative under the signed convention.",
            "min(direction * (package_price_t - entry_package_price))",
        ),
    )
    price_mfe: Price | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Price MFE",
            "Calculated (market data + executions)",
            "Largest favourable movement in the marked package-price series.",
            "max(direction * (package_price_t - entry_package_price))",
        ),
    )
    mfe_mae_ratio: Decimal | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "MFE/MAE Ratio",
            "Calculated (market data + executions)",
            "Favourable PnL excursion divided by the absolute adverse PnL excursion.",
            "trade_mfe / abs(trade_mae) only when trade_mae < 0",
        ),
    )
    price_mfe_percentage: Percent | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Price MFE (%)",
            "Calculated (market data + executions)",
            "Price MFE normalised by absolute entry package price.",
            "100 * price_mfe / abs(entry_package_price) when entry_package_price != 0",
        ),
    )
    price_mae_percentage: Percent | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Price MAE (%)",
            "Calculated (market data + executions)",
            "Price MAE normalised by absolute entry package price; negative under the signed convention.",
            "100 * price_mae / abs(entry_package_price) when entry_package_price != 0",
        ),
    )
    tick_mfe: Decimal | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Tick MFE",
            "Calculated (market data + executions)",
            "Favourable price excursion expressed in minimum-tick units; may be fractional for midpoint/theoretical marks.",
            "price_mfe / min_tick",
        ),
    )
    tick_mae: Decimal | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Tick MAE",
            "Calculated (market data + executions)",
            "Adverse price excursion expressed in minimum-tick units; negative under the signed convention.",
            "price_mae / min_tick",
        ),
    )
    mfe_at: AwareDatetime | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "MFE Date",
            "Calculated (market data + executions)",
            "Earliest timestamp at which package PnL equals Trade MFE.",
            "min(snapshot_at where current_pnl = trade_mfe)",
        ),
    )
    mae_at: AwareDatetime | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "MAE Date",
            "Calculated (market data + executions)",
            "Earliest timestamp at which package PnL equals Trade MAE.",
            "min(snapshot_at where current_pnl = trade_mae)",
        ),
    )
    time_till_mfe_seconds: NonNegativeInt | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Time till MFE",
            "Calculated (market data + executions)",
            "Seconds from package entry to the first MFE timestamp.",
            "mfe_at - opened_at",
        ),
    )
    time_till_mae_seconds: NonNegativeInt | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Time till MAE",
            "Calculated (market data + executions)",
            "Seconds from package entry to the first MAE timestamp.",
            "mae_at - opened_at",
        ),
    )
    time_after_mfe_seconds: NonNegativeInt | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Time after MFE",
            "Calculated (market data + executions)",
            "Seconds from first MFE timestamp to final close.",
            "closed_at - mfe_at",
        ),
    )
    time_after_mae_seconds: NonNegativeInt | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "Time after MAE",
            "Calculated (market data + executions)",
            "Seconds from first MAE timestamp to final close.",
            "closed_at - mae_at",
        ),
    )
    eod_exit_pnl: Money | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "EOD Exit PnL",
            "Calculated (market data + executions)",
            "Simulated net package PnL if final closing fills used regular-session close marks.",
            "recompute PnL after replacing final closing fill prices with EOD liquidation marks",
        ),
    )
    eod_exit_efficiency: Percent | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "EOD Exit Efficiency",
            "Calculated (market data + executions)",
            "Percentage of positive EOD-simulated PnL captured by the actual exit.",
            "100 * realized_pnl / eod_exit_pnl only when eod_exit_pnl > 0",
        ),
    )
    eod_exit_r_value: Decimal | None = Field(
        default=None,
        json_schema_extra=_metadata(
            "EOD Exit R-value",
            "Calculated (market data + executions)",
            "EOD-simulated PnL in R, where one R is the planned stop-loss amount.",
            "eod_exit_pnl / stop_loss only when stop_loss > 0",
        ),
    )

    @field_validator("ticker", "currency", "underlying", mode="before")
    @classmethod
    def _normalise_market_identifiers(cls, value: Any) -> Any:
        if value is None:
            return None
        return str(value).strip().upper()

    @field_validator("asset_type", mode="before")
    @classmethod
    def _normalise_asset_type(cls, value: Any) -> str:
        return str(value).strip().upper()

    @model_validator(mode="before")
    @classmethod
    def _normalise_legacy_input_keys(cls, data: Any) -> Any:
        """Accept only lossless legacy input names during the frontend migration."""

        if not isinstance(data, Mapping):
            return data

        values = dict(data)
        aliases = {
            "symbol": "ticker",
            "compactSpread": "spread_display",
            "compact_spread": "spread_display",
            "strategy": "strategy_name",
            "total_volume": "gross_notional",
            "spread_units": "gross_notional",
            "open_price": "net_open_cash_flow",
            "close_price": "net_close_cash_flow",
        }
        for legacy_name, canonical_name in aliases.items():
            if canonical_name not in values and legacy_name in values:
                values[canonical_name] = values.pop(legacy_name)

        # The prior CSV accidentally named Tags as strategy_type.  Accept the
        # old input only at this migration boundary, never as a canonical field.
        if "tags" not in values and "strategy_type" in values:
            old_tags = values.pop("strategy_type")
            values["tags"] = (old_tags,) if isinstance(old_tags, str) else old_tags

        if "spread_display" not in values and "symbols_display" in values:
            raise ValueError(
                "symbols_display is a legacy flattened string and cannot safely be parsed "
                "into spread_display. Select the structured spread payload from the backend."
            )
        return values

    @model_validator(mode="after")
    def _validate_package_invariants(self) -> "CompletedTradeRow":
        if self.closed_at is not None and cast(datetime, self.closed_at) < cast(datetime, self.opened_at):
            raise ValueError("closed_at cannot be earlier than opened_at.")
        if self.closed_at is None and not self.open_position:
            raise ValueError("An unclosed package must have open_position=True.")
        if self.closed_at is not None and self.open_position:
            raise ValueError("A closed package must have open_position=False.")
        if self.total_duration_seconds is not None and self.closed_at is None:
            raise ValueError("total_duration_seconds requires closed_at.")
        if self.dte_at_open is None and self.dte_by_expiry:
            raise ValueError("dte_at_open must be the nearest DTE when dte_by_expiry is populated.")

        stock_strategy = self.strategy_name in {"Long Stock", "Short Stock"}
        if stock_strategy:
            if self.strikes or self.expiries:
                raise ValueError("Stock-only packages cannot contain option strikes or expiries.")
            if self.spread_display.detail != self.strategy_name:
                raise ValueError("Stock-only Spread detail must match the Long/Short Stock strategy.")
        if self.strategy_name == "Custom Multi-Leg" and not self.strikes:
            raise ValueError("Custom Multi-Leg packages require option strikes for the Spread display.")
        return self

    @property
    def symbols_display(self) -> str:
        """Deprecated flattened display fallback for existing callers.

        New code must render ``spread_display.headline`` and
        ``spread_display.detail`` independently.  This property is retained so
        existing service code can migrate without reparsing display strings.
        """

        return self.spread_display.csv or f"{self.spread_display.headline} | {self.spread_display.detail}"


def completed_trade_from_duckdb_row(
    columns: Sequence[str],
    row: Mapping[str, Any] | Sequence[Any],
) -> CompletedTradeRow:
    """Validate a DuckDB SELECT row without relying on ``from_attributes``.

    For a standard ``cursor.fetchall()`` result, pass
    ``[description[0] for description in cursor.description]`` and one returned
    tuple.  SQL must alias fields to the canonical names in this module.
    """

    if isinstance(row, Mapping):
        return CompletedTradeRow.model_validate(row)
    if isinstance(row, (str, bytes)):
        raise TypeError("DuckDB row must be a mapping or a non-string sequence.")
    if len(columns) != len(row):
        raise ValueError(
            f"DuckDB column/value count mismatch: {len(columns)} columns for {len(row)} values."
        )
    if len(set(columns)) != len(columns):
        raise ValueError("DuckDB SELECT contains duplicate column names; alias every selected field uniquely.")
    return CompletedTradeRow.model_validate(dict(zip(columns, row, strict=True)))


def completed_trade_grid_payload(
    row: CompletedTradeRow,
    *,
    include_legacy_aliases: bool = False,
) -> dict[str, Any]:
    """Return a JSON-safe AG Grid payload at the API boundary.

    The canonical payload contains ``ticker``, ``spread_display``, and
    ``strategy_name``.  Enable legacy aliases only while the existing React
    code is being migrated; remove that endpoint option once all consumers use
    the canonical fields.
    """

    payload = row.model_dump(mode="json")
    if include_legacy_aliases:
        payload.update(
            {
                "symbol": payload["ticker"],
                "symbols_display": row.symbols_display,
                "compactSpread": payload["spread_display"],
                "strategy": payload["strategy_name"],
                "total_volume": payload["gross_notional"],
                "open_price": payload["net_open_cash_flow"],
                "close_price": payload["net_close_cash_flow"],
            }
        )
    return payload