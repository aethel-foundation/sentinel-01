# Risk Policy Specification
## Sentinel-01 - AETHEL Foundation

### Capital Protection Limits

These limits are **CONSTITUTIONAL** - the agent CANNOT violate them under any circumstances.

| Parameter | Value | Description |
|-----------|-------|-------------|
| max_drawdown_pct | 5.0% | Maximum portfolio drawdown |
| max_single_trade_pct | 2.0% | Maximum single trade size |
| max_daily_loss_pct | 3.0% | Maximum daily loss |
| max_position_pct | 20.0% | Maximum single position |
| min_liquidity_ratio | 30.0% | Minimum cash/liquidity |
| max_leverage | 1.0x | No leverage allowed |
| stop_loss_pct | 2.0% | Per-position stop loss |

### Pre-Trade Checklist

Every trade MUST pass ALL checks:

1. **Drawdown Check**: Current drawdown < max_drawdown_pct
2. **Daily Loss Check**: Today's loss < max_daily_loss_pct
3. **Trade Size Check**: Proposed trade < max_single_trade_pct
4. **Position Size Check**: Resulting position < max_position_pct
5. **Liquidity Check**: Cash ratio >= min_liquidity_ratio
6. **Volatility Check**: Not in crisis-level volatility
7. **Anomaly Check**: No market anomalies detected

### Risk Score Calculation

```
risk_score = (failed_checks * 0.3) + (warn_checks * 0.1) 
           + (volatility * 0.3) + (anomaly_score * 0.2)
```

A single FAIL = trade blocked. No exceptions.

### Policy Hash

The `POLICY_HASH` is computed deterministically from risk limits and thresholds:

```python
policy_data = {
    "risk_limits": {...},
    "policy_thresholds": {...}
}
POLICY_HASH = sha256(json.dumps(policy_data, sort_keys=True))
```

This hash is published on-chain and verified with every trade.
