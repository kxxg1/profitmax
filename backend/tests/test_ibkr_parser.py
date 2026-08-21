import duckdb

from app.core.db import get_db_connection
from app.services import ibkr_parser


def test_process_ibkr_flex_file_includes_buy_sell_and_notes(tmp_path, monkeypatch):
    xml_path = tmp_path / "sample_flex.xml"
    xml_path.write_text(
        """
        <FlexQueryResponse>
          <FlexStatements>
            <FlexStatement>
              <Trades>
                <Trade
                  assetCategory="OPT"
                  buySell="BUY"
                  dateTime="20260810;123000"
                  symbol="AAPL   260818C00100000"
                  underlyingSymbol="AAPL"
                  expiry="20260818"
                  strike="100"
                  putCall="C"
                  quantity="2"
                  tradePrice="1.23"
                  proceeds="-246"
                  ibCommission="1.23"
                  exchange="CBOE"
                  orderID="123"
                  tradeID="t1"
                  orderType="LMT"
                />
              </Trades>
            </FlexStatement>
          </FlexStatements>
        </FlexQueryResponse>
        """.strip()
    )

    monkeypatch.setattr(ibkr_parser, "DB_PATH", tmp_path / "profitmax.duckdb")
    get_db_connection().close()

    result = ibkr_parser.process_ibkr_flex_file(xml_path)

    assert result["status"] == "success"

    conn = duckdb.connect(str(tmp_path / "profitmax.duckdb"))
    try:
        row = conn.execute("SELECT buy_sell, notes FROM broker_executions").fetchone()
        assert row == ("BUY", "")
    finally:
        conn.close()
