"""
Sentinel-01 Reputation Tracker
AETHEL Finance Lab - ValidationArtifacts and Reputation Metrics

This module generates ValidationArtifacts for every decision cycle
and maintains the agent's reputation metrics.

Every decision, including "doing nothing", is logged and hashed.
This creates an auditable trail for on-chain verification.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum

from .config import config, MarketRegime, ActionType
from .signal_engine import MarketSignal
from .risk_engine import RiskAssessment
from .policy_engine import PolicyDecision
from .executor import TradeIntent, ExecutionResult


@dataclass
class ValidationArtifact:
    """
    ERC-8004 ValidationArtifact.
    
    Records every decision cycle with full context.
    Published to Validation Registry for on-chain auditability.
    """
    artifact_id: str
    timestamp: datetime
    agent_id: str
    cycle_number: int
    
    # Input state
    market_signal: Dict
    portfolio_state: Dict
    regime: MarketRegime
    
    # Decision
    policy_decision: Dict
    risk_assessment: Optional[Dict]
    action_taken: ActionType
    
    # Outcome
    trade_intent: Optional[Dict]
    execution_result: Optional[Dict]
    
    # Hashes for verification
    policy_hash: str
    artifact_hash: str = ""
    
    def __post_init__(self):
        if not self.artifact_hash:
            self.artifact_hash = self.compute_hash()
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of artifact"""
        data = {
            "artifact_id": self.artifact_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "cycle_number": self.cycle_number,
            "regime": self.regime.value,
            "action_taken": self.action_taken.value,
            "policy_hash": self.policy_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            "artifact_id": self.artifact_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "cycle_number": self.cycle_number,
            "market_signal": self.market_signal,
            "portfolio_state": self.portfolio_state,
            "regime": self.regime.value,
            "policy_decision": self.policy_decision,
            "risk_assessment": self.risk_assessment,
            "action_taken": self.action_taken.value,
            "trade_intent": self.trade_intent,
            "execution_result": self.execution_result,
            "policy_hash": self.policy_hash,
            "artifact_hash": self.artifact_hash,
        }


@dataclass
class ReputationMetrics:
    """
    Agent reputation metrics.
    
    Tracks performance for on-chain reputation system.
    """
    total_cycles: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    policy_violations: int = 0  # Should always be 0
    risk_blocks: int = 0  # Trades blocked by risk engine
    total_pnl: float = 0.0
    max_drawdown_experienced: float = 0.0
    uptime_percentage: float = 100.0
    governance_compliance: float = 100.0  # % of governance directives followed
    
    def to_dict(self) -> Dict:
        return {
            "total_cycles": self.total_cycles,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "policy_violations": self.policy_violations,
            "risk_blocks": self.risk_blocks,
            "total_pnl": round(self.total_pnl, 2),
            "max_drawdown_experienced": round(self.max_drawdown_experienced, 4),
            "uptime_percentage": round(self.uptime_percentage, 2),
            "governance_compliance": round(self.governance_compliance, 2),
            "success_rate": round(
                self.successful_trades / max(self.successful_trades + self.failed_trades, 1) * 100, 2
            ),
        }


class ReputationTracker:
    """
    Manages ValidationArtifacts and reputation metrics.
    
    Responsibilities:
    - Generate ValidationArtifact for every cycle
    - Update reputation metrics
    - Prepare artifacts for Validation Registry publishing
    - Provide audit trail access
    """
    
    def __init__(self):
        self._cycle_number = 0
        self._artifacts: List[ValidationArtifact] = []
        self._metrics = ReputationMetrics()
        self._max_artifacts = 10000  # Keep last N artifacts in memory
    
    def record_cycle(
        self,
        signal: MarketSignal,
        portfolio_state: Dict,
        policy: PolicyDecision,
        assessment: Optional[RiskAssessment],
        action: ActionType,
        intent: Optional[TradeIntent],
        result: Optional[ExecutionResult]
    ) -> ValidationArtifact:
        """
        Record a complete decision cycle.
        
        Args:
            signal: Market signal for this cycle
            portfolio_state: Current portfolio state
            policy: Policy decision
            assessment: Risk assessment (None for HOLD)
            action: Action taken
            intent: TradeIntent (None for HOLD)
            result: Execution result (None for HOLD or blocked)
        
        Returns:
            ValidationArtifact for this cycle
        """
        now = datetime.now(timezone.utc)
        self._cycle_number += 1
        
        artifact = ValidationArtifact(
            artifact_id=str(uuid.uuid4()),
            timestamp=now,
            agent_id=config.identity.agent_id,
            cycle_number=self._cycle_number,
            market_signal=signal.to_dict(),
            portfolio_state=portfolio_state,
            regime=policy.regime,
            policy_decision=policy.to_dict(),
            risk_assessment=assessment.to_dict() if assessment else None,
            action_taken=action,
            trade_intent=intent.to_dict() if intent else None,
            execution_result=result.to_dict() if result else None,
            policy_hash=config.identity.policy_hash,
        )
        
        # Store artifact
        self._artifacts.append(artifact)
        if len(self._artifacts) > self._max_artifacts:
            self._artifacts = self._artifacts[-self._max_artifacts:]
        
        # Update metrics
        self._update_metrics(action, assessment, result)
        
        return artifact
    
    def _update_metrics(
        self,
        action: ActionType,
        assessment: Optional[RiskAssessment],
        result: Optional[ExecutionResult]
    ):
        """Update reputation metrics based on cycle outcome"""
        self._metrics.total_cycles += 1
        
        # Track risk blocks
        if assessment and not assessment.approved:
            self._metrics.risk_blocks += 1
        
        # Track trade outcomes
        if result:
            if result.success:
                self._metrics.successful_trades += 1
            else:
                self._metrics.failed_trades += 1
    
    def update_pnl(self, pnl: float, drawdown: float):
        """Update P&L and drawdown metrics"""
        self._metrics.total_pnl = pnl
        self._metrics.max_drawdown_experienced = max(
            self._metrics.max_drawdown_experienced,
            drawdown
        )
    
    def record_policy_violation(self):
        """Record a policy violation (should never happen)"""
        self._metrics.policy_violations += 1
        self._metrics.governance_compliance = max(
            0,
            100 - (self._metrics.policy_violations / max(self._metrics.total_cycles, 1) * 100)
        )
    
    def get_metrics(self) -> ReputationMetrics:
        """Get current reputation metrics"""
        return self._metrics
    
    def get_recent_artifacts(self, count: int = 10) -> List[Dict]:
        """Get most recent artifacts"""
        return [a.to_dict() for a in self._artifacts[-count:]]
    
    def get_artifact_by_id(self, artifact_id: str) -> Optional[Dict]:
        """Get specific artifact by ID"""
        for artifact in self._artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact.to_dict()
        return None
    
    def get_cycle_summary(self) -> Dict:
        """Get summary of all cycles"""
        return {
            "total_cycles": self._cycle_number,
            "artifacts_stored": len(self._artifacts),
            "metrics": self._metrics.to_dict(),
            "latest_artifact": self._artifacts[-1].to_dict() if self._artifacts else None,
        }
    
    def prepare_for_registry(self, artifact: ValidationArtifact) -> Dict:
        """
        Prepare artifact for Validation Registry publishing.
        
        In production, this would format the artifact for on-chain storage.
        
        TODO: Implement actual registry publishing:
        1. Serialize artifact to bytes
        2. Sign with agent key
        3. Submit to Validation Registry contract
        """
        return {
            "artifact_hash": artifact.artifact_hash,
            "agent_id": artifact.agent_id,
            "cycle_number": artifact.cycle_number,
            "timestamp": artifact.timestamp.isoformat(),
            "regime": artifact.regime.value,
            "action": artifact.action_taken.value,
            "policy_hash": artifact.policy_hash,
            # Full artifact data would be stored off-chain (IPFS, etc.)
            # Only hash goes on-chain
            "ready_for_chain": True,
        }


# Global reputation tracker instance
reputation_tracker = ReputationTracker()
