SELECT 
    strategy_type, 
    net_cash_flow,
    MAX(unique_strikes) AS unique_strikes,
    MAX(contract_legs) AS contract_legs,
    COUNT(DISTINCT combo_id) AS number_of_spreads,
    SUM(spread_units) / MAX(contract_legs) AS total_spread_contracts,
    COUNT(*) AS total_raw_db_rows
FROM broker_events
GROUP BY strategy_type, net_cash_flow
ORDER BY number_of_spreads DESC;