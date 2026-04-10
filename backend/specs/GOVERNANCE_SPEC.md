# Governance Specification
## Sentinel-01 - AETHEL Finance Lab

### Governance Principles

1. **Constitutional Control**: Governance overrides agent autonomy
2. **Transparency**: All proposals and votes are public
3. **Delayed Execution**: Changes require time-lock (except emergencies)
4. **Quorum Requirements**: Minimum participation for validity

### Governance Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| quorum_percentage | 51% | Required vote participation |
| proposal_duration_hours | 24h | Voting period |
| execution_delay_hours | 6h | Delay after approval |
| emergency_quorum_percentage | 66% | Emergency action quorum |
| min_members_for_quorum | 2 | Minimum active members |

### Proposal Types

| Type | Description | Quorum | Delay |
|------|-------------|--------|-------|
| PARAMETER_CHANGE | Modify risk limits | 51% | 6h |
| POLICY_UPDATE | Update policy thresholds | 51% | 6h |
| PAUSE_AGENT | Suspend trading | 51% | 6h |
| RESUME_AGENT | Resume trading | 51% | 6h |
| ADD_MEMBER | Add governance member | 51% | 6h |
| REMOVE_MEMBER | Remove member | 51% | 6h |
| EMERGENCY_ACTION | Crisis response | 66% | 0h |

### Proposal Lifecycle

```
PENDING → ACTIVE → PASSED/REJECTED → EXECUTED/EXPIRED
```

### Vote Types

- **FOR**: Support the proposal
- **AGAINST**: Oppose the proposal
- **ABSTAIN**: Neutral (counts toward quorum)

### Emergency Protocol

Emergency actions bypass normal delays but require:
- 66% quorum (elevated)
- Immediate execution capability
- Full audit trail

### Governance Bodies

1. **Members**: Voting participants with assigned voting power
2. **Proposers**: Members who can create proposals
3. **Executors**: System that implements passed proposals
