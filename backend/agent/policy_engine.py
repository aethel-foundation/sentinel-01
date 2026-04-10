"""
Sentinel-01 Policy Engine
AETHEL Finance Lab - Regime Classification and Policy Enforcement

This module determines WHAT ACTIONS ARE ALLOWED based on market regime.
It does NOT decide what actions to take - that's the strategy layer.

Policy hierarchy:
1. Constitutional limits (config.py) - NEVER violated
2. Regime-based restrictions - Dynamic based on market conditions
3. Governance overrides - Can further restrict, never loosen
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional
from enum import Enum

from .config import config, MarketRegime, ActionType
from .signal_engine import MarketSignal


@dataclass
class PolicyDecision:
    """Policy decision for current regime"""
    timestamp: datetime
    regime: MarketRegime
    allowed_actions: Set[ActionType]
    blocked_actions: Set[ActionType]
    max_trade_size_pct: float  # Dynamic limit based on regime
    position_sizing_multiplier: float  # 0.0 to 1.0
    reason: str
    governance_override: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "regime": self.regime.value,
            "allowed_actions": [a.value for a in self.allowed_actions],
            "blocked_actions": [a.value for a in self.blocked_actions],
            "max_trade_size_pct": round(self.max_trade_size_pct, 2),
            "position_sizing_multiplier": round(self.position_sizing_multiplier, 2),
            "reason": self.reason,
            "governance_override": self.governance_override,
        }


class PolicyEngine:
    """
    Regime-based policy enforcement.
    
    Regime policies:
    - NORMAL: All actions allowed, full position sizing
    - VOLATILE: Reduced position sizing, careful entry
    - CRISIS: Only HOLD and REDUCE_EXPOSURE allowed
    - UNKNOWN: Conservative approach, limited actions
    """
    
    # Default regime policies
    REGIME_POLICIES = {
        MarketRegime.NORMAL: {
            "allowed": {ActionType.HOLD, ActionType.BUY, ActionType.SELL},
            "max_trade_pct": 2.0,  # Full limit from config
            "position_multiplier": 1.0,
            "reason": "Normal market conditions - standard trading allowed"
        },
        MarketRegime.VOLATILE: {
            "allowed": {ActionType.HOLD, ActionType.SELL, ActionType.REDUCE_EXPOSURE},
            "max_trade_pct": 1.0,  # Reduced
            "position_multiplier": 0.5,
            "reason": "Volatile conditions - defensive posture, reduced sizing"
        },
        MarketRegime.CRISIS: {
            "allowed": {ActionType.HOLD, ActionType.REDUCE_EXPOSURE, ActionType.EMERGENCY_EXIT},
            "max_trade_pct": 0.0,  # No new positions
            "position_multiplier": 0.0,
            "reason": "Crisis mode - capital preservation only, no new positions"
        },
        MarketRegime.UNKNOWN: {
            "allowed": {ActionType.HOLD},
            "max_trade_pct": 0.0,
            "position_multiplier": 0.0,
            "reason": "Unknown regime - holding until clarity"
        }
    }
    
    def __init__(self):
        self._governance_paused = False
        self._governance_restrictions: Set[ActionType] = set()
        self._current_regime = MarketRegime.UNKNOWN
    
    @property
    def is_paused(self) -> bool:
        """Check if governance has paused trading"""
        return self._governance_paused
    
    def set_governance_pause(self, paused: bool):
        """Set governance pause state"""
        self._governance_paused = paused
    
    def add_governance_restriction(self, action: ActionType):
        """Add governance-imposed restriction"""
        self._governance_restrictions.add(action)
    
    def remove_governance_restriction(self, action: ActionType):
        """Remove governance-imposed restriction"""
        self._governance_restrictions.discard(action)
    
    def clear_governance_restrictions(self):
        """Clear all governance restrictions"""
        self._governance_restrictions.clear()
    
    def get_policy(self, signal: MarketSignal) -> PolicyDecision:
        """
        Get current policy based on market signal.
        
        Args:
            signal: Current market signal
        
        Returns:
            PolicyDecision with allowed actions and constraints
        """
        now = datetime.now(timezone.utc)
        
        # Classify regime from signal
        regime = self._classify_regime(signal)
        self._current_regime = regime
        
        # Get base policy for regime
        policy = self.REGIME_POLICIES[regime]
        allowed_actions = policy["allowed"].copy()
        
        # Apply governance pause
        if self._governance_paused:
            return PolicyDecision(
                timestamp=now,
                regime=regime,
                allowed_actions={ActionType.HOLD},
                blocked_actions=set(ActionType) - {ActionType.HOLD},
                max_trade_size_pct=0.0,
                position_sizing_multiplier=0.0,
                reason="GOVERNANCE PAUSE: All trading suspended",
                governance_override=True
            )
        
        # Apply governance restrictions
        for restricted in self._governance_restrictions:
            allowed_actions.discard(restricted)
        
        blocked_actions = set(ActionType) - allowed_actions
        
        return PolicyDecision(
            timestamp=now,
            regime=regime,
            allowed_actions=allowed_actions,
            blocked_actions=blocked_actions,
            max_trade_size_pct=policy["max_trade_pct"],
            position_sizing_multiplier=policy["position_multiplier"],
            reason=policy["reason"],
            governance_override=len(self._governance_restrictions) > 0
        )
    
    def _classify_regime(self, signal: MarketSignal) -> MarketRegime:
        """
        Classify market regime from signal.
        Uses volatility as primary indicator.
        """
        thresholds = config.policy_thresholds
        
        # Crisis conditions
        if signal.volatility >= thresholds.volatility_crisis_threshold:
            return MarketRegime.CRISIS
        
        if signal.anomaly_score >= thresholds.anomaly_score_max:
            return MarketRegime.CRISIS
        
        # Volatile conditions
        if signal.volatility >= thresholds.volatility_volatile_max:
            return MarketRegime.VOLATILE
        
        # Normal conditions
        if signal.volatility <= thresholds.volatility_normal_max:
            return MarketRegime.NORMAL
        
        # Between normal and volatile - lean towards volatile
        return MarketRegime.VOLATILE
    
    def is_action_allowed(self, action: ActionType, policy: PolicyDecision) -> bool:
        """Check if specific action is allowed under current policy"""
        return action in policy.allowed_actions
    
    def get_current_regime(self) -> MarketRegime:
        """Get the current regime classification"""
        return self._current_regime
    
    def get_regime_summary(self) -> Dict:
        """Get summary of current policy state"""
        return {
            "current_regime": self._current_regime.value,
            "governance_paused": self._governance_paused,
            "governance_restrictions": [a.value for a in self._governance_restrictions],
            "regime_policies": {
                regime.value: {
                    "allowed": [a.value for a in policy["allowed"]],
                    "max_trade_pct": policy["max_trade_pct"],
                    "position_multiplier": policy["position_multiplier"],
                }
                for regime, policy in self.REGIME_POLICIES.items()
            }
        }


# Global policy engine instance
policy_engine = PolicyEngine()
