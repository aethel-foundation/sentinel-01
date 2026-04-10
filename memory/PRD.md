# Sentinel-01 - Product Requirements Document

## Project Overview

**Project**: Sentinel-01  
**Organization**: AETHEL Finance Lab  
**Version**: 0.1.0  
**Created**: 2026-04-10  
**Status**: MVP Complete - Demo Ready

## Mission Statement

Build a capital-protection-first ERC-8004 agent with constitutional governance, auditable validation artifacts, and a clean path from simulation to sandbox/testnet deployment.

**Primary principle**: Profit is secondary; policy compliance and capital preservation are mandatory.

## User Personas

1. **Institutional Risk Managers** - Need auditable, policy-compliant trading agents
2. **DeFi Protocol Operators** - Need autonomous treasury management
3. **Hackathon Judges** - Need to understand risk-first architecture quickly
4. **Developers** - Need clean code for ERC-8004 integration

## Core Requirements (Static)

### Constitutional Risk Limits
- Max Drawdown: 5%
- Max Single Trade: 2%
- Max Daily Loss: 3%
- Max Position: 20%
- Min Liquidity: 30%
- Max Leverage: 1x

### Market Regimes
- NORMAL: All actions allowed
- VOLATILE: Defensive posture
- CRISIS: HOLD only
- UNKNOWN: Conservative

### ERC-8004 Compliance
- TradeIntent structure and signing
- ValidationArtifact generation
- Policy hash computation
- Reputation metrics tracking

## What's Been Implemented (2026-04-10)

### Backend (Python/FastAPI)
- [x] Agent core modules (config, signal_engine, risk_engine, policy_engine, executor, reputation_tracker)
- [x] Main orchestration loop
- [x] Constitutional governance system
- [x] Emergency protocol
- [x] CoinGecko market data adapter
- [x] RESTful API (20+ endpoints)
- [x] MongoDB integration for artifacts

### Frontend (React)
- [x] Professional dark-mode dashboard
- [x] Overview tab (portfolio, metrics, positions, artifacts)
- [x] Market tab (real-time ETH/BTC prices)
- [x] Artifacts tab (ValidationArtifact explorer)
- [x] Governance tab (proposals, voting, stats)
- [x] Risk tab (limits visualization, reputation metrics)
- [x] Run Cycle / Pause / Resume controls

### Specifications
- [x] AGENT_SPEC.md
- [x] RISK_POLICY_SPEC.md
- [x] GOVERNANCE_SPEC.md
- [x] SKILL.md
- [x] SYSTEM_PROMPT.md

### Documentation
- [x] README.md (English)
- [x] README.pt.md (Portuguese)

## Prioritized Backlog

### P0 - Critical for Hackathon
- [x] Working simulation
- [x] Dashboard visualization
- [x] Real market data
- [x] ValidationArtifact generation

### P1 - High Priority
- [ ] EIP-712 signing with real keys
- [ ] On-chain ValidationArtifact publishing
- [ ] Connect to ERC-8004 Identity Registry
- [ ] Connect to Risk Router contract

### P2 - Medium Priority
- [ ] Historical data charts
- [ ] Proposal creation UI
- [ ] Member management UI
- [ ] Mobile responsive improvements

### P3 - Future
- [ ] Multi-asset support beyond ETH/BTC
- [ ] Custom strategy plugins
- [ ] Alert/notification system
- [ ] Advanced analytics dashboard

## Technical Architecture

```
Frontend (React) → Backend API (FastAPI) → Agent Core → Market Adapter
                                           ↓
                              Governance ← Policy Engine ← Risk Engine
                                           ↓
                              Reputation Tracker → MongoDB
```

## API Endpoints Summary

| Category | Endpoints |
|----------|-----------|
| Agent | /agent/status, /agent/cycle, /agent/start, /agent/stop |
| Market | /market/price/{asset}, /market/prices, /market/signal/{asset} |
| Risk | /risk/limits, /policy/summary, /policy/current |
| Governance | /governance/status, /governance/proposals, /governance/proposals/{id}/vote |
| Emergency | /emergency/status, /emergency/pause, /emergency/resume, /emergency/close-all |
| Artifacts | /artifacts/recent, /artifacts/{id}, /artifacts/summary |
| Reputation | /reputation/metrics |

## Next Tasks

1. Prepare demo presentation for hackathon
2. Test with various market scenarios
3. Document ERC-8004 integration points clearly
4. Create video walkthrough
