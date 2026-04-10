"""
Sentinel-01 Risk Engine
AETHEL Foundation - Deterministic Pre-Trade Checklist

This module enforces the constitutional risk limits.
Every trade MUST pass the risk checklist before execution.
Capital preservation is mandatory - profit is secondary.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from enum import Enum

from agent.config import config, RiskLimits, ActionType
from agent.signal_engine import MarketSignal


class RiskCheckResult(Enum):
    """Result of individual risk check"""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class RiskCheck:
    """Individual risk check result"""
    check_name: str
    result: RiskCheckResult
    reason: str
    value: float = 0.0
    limit: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "check_name": self.check_name,
            "result": self.result.value,
            "reason": self.reason,
            "value": round(self.value, 4),
            "limit": round(self.limit, 4),
        }


@dataclass
class RiskAssessment:
    """Complete risk assessment for a proposed action"""
    timestamp: datetime
    action: ActionType
    asset: str
    amount: float
    checks: List[RiskCheck]
    approved: bool
    rejection_reasons: List[str]
    risk_score: float  # 0.0 (low risk) to 1.0 (high risk)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "asset": self.asset,
            "amount": round(self.amount, 2),
            "checks": [c.to_dict() for c in self.checks],
            "approved": self.approved,
            "rejection_reasons": self.rejection_reasons,
            "risk_score": round(self.risk_score, 4),
        }


@dataclass
class PortfolioState:
    """Current portfolio state"""
    total_value: float
    cash_balance: float
    positions: Dict[str, float] = field(default_factory=dict)  # asset -> value
    daily_pnl: float = 0.0
    peak_value: float = 0.0
    current_drawdown: float = 0.0
    trades_today: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "total_value": round(self.total_value, 2),
            "cash_balance": round(self.cash_balance, 2),
            "positions": {k: round(v, 2) for k, v in self.positions.items()},
            "daily_pnl": round(self.daily_pnl, 2),
            "peak_value": round(self.peak_value, 2),
            "current_drawdown": round(self.current_drawdown, 4),
            "trades_today": self.trades_today,
        }


class RiskEngine:
    """
    Deterministic risk assessment engine.
    
    Core principle: Every trade must pass ALL checks.
    A single failure = trade blocked.
    
    Risk checks:
    1. Drawdown limit
    2. Daily loss limit
    3. Single trade size limit
    4. Position size limit
    5. Liquidity requirement
    6. Volatility regime check
    7. Anomaly check
    """
    
    def __init__(self):
        self.limits = config.risk_limits
        self.thresholds = config.policy_thresholds
        self._portfolio: Optional[PortfolioState] = None
    
    def set_portfolio_state(self, portfolio: PortfolioState):
        """Update current portfolio state"""
        self._portfolio = portfolio
    
    def get_portfolio_state(self) -> Optional[PortfolioState]:
        """Get current portfolio state"""
        return self._portfolio
    
    def assess_trade(self, action: ActionType, asset: str, amount: float,
                     signal: MarketSignal) -> RiskAssessment:
        """
        Perform complete risk assessment for proposed trade.
        
        Args:
            action: Proposed action type
            asset: Target asset
            amount: Trade amount in USD
            signal: Current market signal
        
        Returns:
            RiskAssessment with all checks and final approval status
        """
        now = datetime.now(timezone.utc)
        checks: List[RiskCheck] = []
        rejection_reasons: List[str] = []
        
        # Ensure portfolio state exists
        if self._portfolio is None:
            return RiskAssessment(
                timestamp=now,
                action=action,
                asset=asset,
                amount=amount,
                checks=[RiskCheck(
                    check_name="portfolio_state",
                    result=RiskCheckResult.FAIL,
                    reason="Portfolio state not initialized"
                )],
                approved=False,
                rejection_reasons=["Portfolio state not initialized"],
                risk_score=1.0
            )
        
        # HOLD actions always pass
        if action == ActionType.HOLD:
            return RiskAssessment(
                timestamp=now,
                action=action,
                asset=asset,
                amount=0,
                checks=[RiskCheck(
                    check_name="hold_action",
                    result=RiskCheckResult.PASS,
                    reason="HOLD requires no risk checks"
                )],
                approved=True,
                rejection_reasons=[],
                risk_score=0.0
            )
        
        # Run all risk checks
        checks.append(self._check_drawdown())
        checks.append(self._check_daily_loss())
        checks.append(self._check_trade_size(amount))
        checks.append(self._check_position_size(asset, amount, action))
        checks.append(self._check_liquidity())
        checks.append(self._check_volatility(signal))
        checks.append(self._check_anomaly(signal))
        
        # Collect failures
        for check in checks:
            if check.result == RiskCheckResult.FAIL:
                rejection_reasons.append(check.reason)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(checks, signal)
        
        # Final approval: ALL checks must pass
        approved = len(rejection_reasons) == 0
        
        return RiskAssessment(
            timestamp=now,
            action=action,
            asset=asset,
            amount=amount,
            checks=checks,
            approved=approved,
            rejection_reasons=rejection_reasons,
            risk_score=risk_score
        )
    
    def _check_drawdown(self) -> RiskCheck:
        """Check if current drawdown exceeds limit"""
        current = self._portfolio.current_drawdown * 100
        limit = self.limits.max_drawdown_pct
        
        if current >= limit:
            return RiskCheck(
                check_name="drawdown_limit",
                result=RiskCheckResult.FAIL,
                reason=f"Drawdown {current:.2f}% exceeds limit {limit}%",
                value=current,
                limit=limit
            )
        elif current >= limit * 0.8:
            return RiskCheck(
                check_name="drawdown_limit",
                result=RiskCheckResult.WARN,
                reason=f"Drawdown {current:.2f}% approaching limit {limit}%",
                value=current,
                limit=limit
            )
        
        return RiskCheck(
            check_name="drawdown_limit",
            result=RiskCheckResult.PASS,
            reason=f"Drawdown {current:.2f}% within limit {limit}%",
            value=current,
            limit=limit
        )
    
    def _check_daily_loss(self) -> RiskCheck:
        """Check if daily loss exceeds limit"""
        if self._portfolio.total_value == 0:
            return RiskCheck(
                check_name="daily_loss_limit",
                result=RiskCheckResult.FAIL,
                reason="Portfolio value is zero",
                value=0,
                limit=self.limits.max_daily_loss_pct
            )
        
        daily_loss_pct = (-self._portfolio.daily_pnl / self._portfolio.total_value) * 100
        limit = self.limits.max_daily_loss_pct
        
        if daily_loss_pct >= limit:
            return RiskCheck(
                check_name="daily_loss_limit",
                result=RiskCheckResult.FAIL,
                reason=f"Daily loss {daily_loss_pct:.2f}% exceeds limit {limit}%",
                value=daily_loss_pct,
                limit=limit
            )
        
        return RiskCheck(
            check_name="daily_loss_limit",
            result=RiskCheckResult.PASS,
            reason=f"Daily loss {daily_loss_pct:.2f}% within limit {limit}%",
            value=daily_loss_pct,
            limit=limit
        )
    
    def _check_trade_size(self, amount: float) -> RiskCheck:
        """Check if single trade size exceeds limit"""
        trade_pct = (amount / self._portfolio.total_value) * 100 if self._portfolio.total_value > 0 else 100
        limit = self.limits.max_single_trade_pct
        
        if trade_pct > limit:
            return RiskCheck(
                check_name="trade_size_limit",
                result=RiskCheckResult.FAIL,
                reason=f"Trade size {trade_pct:.2f}% exceeds limit {limit}%",
                value=trade_pct,
                limit=limit
            )
        
        return RiskCheck(
            check_name="trade_size_limit",
            result=RiskCheckResult.PASS,
            reason=f"Trade size {trade_pct:.2f}% within limit {limit}%",
            value=trade_pct,
            limit=limit
        )
    
    def _check_position_size(self, asset: str, amount: float, action: ActionType) -> RiskCheck:
        """Check if resulting position would exceed limit"""
        current_position = self._portfolio.positions.get(asset, 0)
        
        if action == ActionType.BUY:
            new_position = current_position + amount
        elif action == ActionType.SELL:
            new_position = current_position - amount
        else:
            new_position = current_position
        
        position_pct = (new_position / self._portfolio.total_value) * 100 if self._portfolio.total_value > 0 else 0
        limit = self.limits.max_position_pct
        
        if position_pct > limit:
            return RiskCheck(
                check_name="position_size_limit",
                result=RiskCheckResult.FAIL,
                reason=f"Position size {position_pct:.2f}% would exceed limit {limit}%",
                value=position_pct,
                limit=limit
            )
        
        return RiskCheck(
            check_name="position_size_limit",
            result=RiskCheckResult.PASS,
            reason=f"Position size {position_pct:.2f}% within limit {limit}%",
            value=position_pct,
            limit=limit
        )
    
    def _check_liquidity(self) -> RiskCheck:
        """Check if liquidity ratio meets minimum requirement"""
        liquidity_ratio = self._portfolio.cash_balance / self._portfolio.total_value if self._portfolio.total_value > 0 else 0
        limit = self.limits.min_liquidity_ratio
        
        if liquidity_ratio < limit:
            return RiskCheck(
                check_name="liquidity_requirement",
                result=RiskCheckResult.FAIL,
                reason=f"Liquidity ratio {liquidity_ratio:.2f} below minimum {limit}",
                value=liquidity_ratio,
                limit=limit
            )
        
        return RiskCheck(
            check_name="liquidity_requirement",
            result=RiskCheckResult.PASS,
            reason=f"Liquidity ratio {liquidity_ratio:.2f} meets minimum {limit}",
            value=liquidity_ratio,
            limit=limit
        )
    
    def _check_volatility(self, signal: MarketSignal) -> RiskCheck:
        """Check if volatility is within acceptable range"""
        volatility = signal.volatility
        crisis_threshold = self.thresholds.volatility_crisis_threshold
        
        if volatility >= crisis_threshold:
            return RiskCheck(
                check_name="volatility_regime",
                result=RiskCheckResult.FAIL,
                reason=f"Crisis-level volatility {volatility:.2f} exceeds threshold {crisis_threshold}",
                value=volatility,
                limit=crisis_threshold
            )
        
        return RiskCheck(
            check_name="volatility_regime",
            result=RiskCheckResult.PASS,
            reason=f"Volatility {volatility:.2f} within acceptable range",
            value=volatility,
            limit=crisis_threshold
        )
    
    def _check_anomaly(self, signal: MarketSignal) -> RiskCheck:
        """Check for market anomalies"""
        anomaly = signal.anomaly_score
        limit = self.thresholds.anomaly_score_max
        
        if anomaly >= limit:
            return RiskCheck(
                check_name="anomaly_detection",
                result=RiskCheckResult.FAIL,
                reason=f"Anomaly score {anomaly:.2f} exceeds threshold {limit}",
                value=anomaly,
                limit=limit
            )
        
        return RiskCheck(
            check_name="anomaly_detection",
            result=RiskCheckResult.PASS,
            reason=f"Anomaly score {anomaly:.2f} within acceptable range",
            value=anomaly,
            limit=limit
        )
    
    def _calculate_risk_score(self, checks: List[RiskCheck], signal: MarketSignal) -> float:
        """Calculate overall risk score from checks and signal"""
        # Base score from failed/warned checks
        fail_count = sum(1 for c in checks if c.result == RiskCheckResult.FAIL)
        warn_count = sum(1 for c in checks if c.result == RiskCheckResult.WARN)
        
        check_score = (fail_count * 0.3 + warn_count * 0.1)
        
        # Add signal-based risk
        signal_score = (signal.volatility * 0.3 + signal.anomaly_score * 0.2)
        
        return min(1.0, check_score + signal_score)


# Global risk engine instance
risk_engine = RiskEngine()
