"""
Sentinel-01 Configuration
AETHEL Finance Lab - Risk-First ERC-8004 Agent

Active risk parameters and policy constants.
These values define the agent's operational boundaries.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import hashlib
import json


class MarketRegime(Enum):
    """Market regime classification for policy decisions"""
    NORMAL = "normal"
    VOLATILE = "volatile"
    CRISIS = "crisis"
    UNKNOWN = "unknown"


class ActionType(Enum):
    """Allowed action types"""
    HOLD = "hold"
    BUY = "buy"
    SELL = "sell"
    REDUCE_EXPOSURE = "reduce_exposure"
    EMERGENCY_EXIT = "emergency_exit"


@dataclass
class RiskLimits:
    """Capital protection limits - NEVER exceeded"""
    max_drawdown_pct: float = 5.0  # Maximum allowed drawdown percentage
    max_single_trade_pct: float = 2.0  # Maximum single trade as % of portfolio
    max_daily_loss_pct: float = 3.0  # Maximum daily loss percentage
    max_position_pct: float = 20.0  # Maximum single position size
    min_liquidity_ratio: float = 0.3  # Minimum cash/liquidity ratio
    max_leverage: float = 1.0  # No leverage by default
    stop_loss_pct: float = 2.0  # Per-position stop loss


@dataclass
class PolicyThresholds:
    """Policy thresholds for regime classification"""
    volatility_normal_max: float = 0.02  # 2% daily volatility
    volatility_volatile_max: float = 0.05  # 5% daily volatility
    volatility_crisis_threshold: float = 0.08  # 8%+ = crisis
    
    trend_strength_min: float = 0.3  # Minimum trend strength for action
    liquidity_warning_threshold: float = 0.5  # Low liquidity warning
    anomaly_score_max: float = 0.7  # Max anomaly before blocking trades


@dataclass
class GovernanceConfig:
    """Governance parameters"""
    quorum_percentage: float = 51.0  # Required vote percentage
    proposal_duration_hours: int = 24  # Voting period
    execution_delay_hours: int = 6  # Delay after approval
    emergency_quorum_percentage: float = 66.0  # Emergency actions need higher quorum
    min_members_for_quorum: int = 2  # Minimum members to reach quorum


@dataclass
class AgentIdentity:
    """ERC-8004 Agent Identity"""
    agent_id: str = "sentinel-01"
    organization: str = "AETHEL Finance Lab"
    version: str = "0.1.0"
    erc8004_compatible: bool = True
    policy_hash: str = ""  # Computed at deployment
    
    def compute_policy_hash(self, risk_limits: RiskLimits, policy_thresholds: PolicyThresholds) -> str:
        """Compute deterministic hash of policy configuration"""
        policy_data = {
            "risk_limits": {
                "max_drawdown_pct": risk_limits.max_drawdown_pct,
                "max_single_trade_pct": risk_limits.max_single_trade_pct,
                "max_daily_loss_pct": risk_limits.max_daily_loss_pct,
                "max_position_pct": risk_limits.max_position_pct,
                "min_liquidity_ratio": risk_limits.min_liquidity_ratio,
                "max_leverage": risk_limits.max_leverage,
                "stop_loss_pct": risk_limits.stop_loss_pct,
            },
            "policy_thresholds": {
                "volatility_normal_max": policy_thresholds.volatility_normal_max,
                "volatility_volatile_max": policy_thresholds.volatility_volatile_max,
                "volatility_crisis_threshold": policy_thresholds.volatility_crisis_threshold,
                "trend_strength_min": policy_thresholds.trend_strength_min,
                "liquidity_warning_threshold": policy_thresholds.liquidity_warning_threshold,
                "anomaly_score_max": policy_thresholds.anomaly_score_max,
            }
        }
        policy_json = json.dumps(policy_data, sort_keys=True)
        return hashlib.sha256(policy_json.encode()).hexdigest()


@dataclass
class SimulationConfig:
    """Simulation mode configuration"""
    enabled: bool = True
    initial_capital: float = 100000.0  # USD
    supported_assets: List[str] = field(default_factory=lambda: ["ETH", "BTC"])
    tick_interval_seconds: int = 5  # Simulation tick rate
    mock_market_volatility: float = 0.03  # Base volatility for mock data


class Config:
    """Main configuration container"""
    
    def __init__(self):
        self.risk_limits = RiskLimits()
        self.policy_thresholds = PolicyThresholds()
        self.governance = GovernanceConfig()
        self.identity = AgentIdentity()
        self.simulation = SimulationConfig()
        
        # Compute policy hash
        self.identity.policy_hash = self.identity.compute_policy_hash(
            self.risk_limits, 
            self.policy_thresholds
        )
        
        # Environment overrides
        self._load_env_overrides()
    
    def _load_env_overrides(self):
        """Load configuration from environment variables"""
        if os.environ.get("SENTINEL_MAX_DRAWDOWN"):
            self.risk_limits.max_drawdown_pct = float(os.environ["SENTINEL_MAX_DRAWDOWN"])
        if os.environ.get("SENTINEL_SIMULATION"):
            self.simulation.enabled = os.environ["SENTINEL_SIMULATION"].lower() == "true"
        if os.environ.get("SENTINEL_INITIAL_CAPITAL"):
            self.simulation.initial_capital = float(os.environ["SENTINEL_INITIAL_CAPITAL"])
    
    def to_dict(self) -> Dict:
        """Export configuration as dictionary"""
        return {
            "agent_id": self.identity.agent_id,
            "version": self.identity.version,
            "policy_hash": self.identity.policy_hash,
            "risk_limits": {
                "max_drawdown_pct": self.risk_limits.max_drawdown_pct,
                "max_single_trade_pct": self.risk_limits.max_single_trade_pct,
                "max_daily_loss_pct": self.risk_limits.max_daily_loss_pct,
                "max_position_pct": self.risk_limits.max_position_pct,
                "min_liquidity_ratio": self.risk_limits.min_liquidity_ratio,
            },
            "simulation_mode": self.simulation.enabled,
        }


# Global configuration instance
config = Config()
