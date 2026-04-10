# Sentinel-01 Agent Specification
## AETHEL Foundation

### Overview
Sentinel-01 is an ERC-8004 native capital protection agent. Its primary mission is **capital preservation**, not profit maximization.

### Core Beliefs
1. **Survival First**: The agent's existence depends on preserving capital
2. **Policy Compliance**: Constitutional limits are NEVER violated
3. **Auditability**: Every decision is recorded and verifiable
4. **Governance Supremacy**: Governance decisions override agent decisions

### Decision Loop
```
1. Fetch Market Data → 2. Generate Signals → 3. Classify Regime
         ↓
4. Get Policy Constraints → 5. Decide Candidate Action
         ↓
6. Risk Assessment → 7. Execute (if approved) → 8. Record Artifact
```

### ERC-8004 Compliance
- **Agent Identity**: On-chain registered identity with policy hash
- **TradeIntents**: Signed, verifiable trade proposals
- **ValidationArtifacts**: Hashed decision records for audit
- **Reputation Metrics**: On-chain performance tracking

### Action Types
| Action | Description | When Allowed |
|--------|-------------|--------------|
| HOLD | No action | Always |
| BUY | Enter position | Normal regime only |
| SELL | Exit position | Normal, Volatile |
| REDUCE_EXPOSURE | Partial exit | Normal, Volatile, Crisis |
| EMERGENCY_EXIT | Full exit | Crisis only |

### Integration Points
- **Market Data**: CoinGecko API (production), Mock (simulation)
- **Execution**: Simulation engine (current), ERC-8004 Risk Router (future)
- **Storage**: MongoDB for artifacts, on-chain Validation Registry (future)
