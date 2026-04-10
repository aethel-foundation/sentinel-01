"""
Sentinel-01 Emergency Protocol
AETHEL Finance Lab - Crisis Response System

This module handles emergency situations that require immediate action
without waiting for normal governance processes.

Emergency conditions:
- Extreme market volatility
- Security breach detection
- Critical system failure
- Governance override (requires elevated quorum)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum

import sys
sys.path.append('..')
from agent.config import config


class EmergencyLevel(Enum):
    """Emergency severity levels"""
    WARNING = "warning"      # Elevated monitoring
    ALERT = "alert"          # Reduced trading
    CRITICAL = "critical"    # Trading suspended
    LOCKDOWN = "lockdown"    # Full system lockdown


class EmergencyType(Enum):
    """Types of emergencies"""
    MARKET_CRASH = "market_crash"
    VOLATILITY_SPIKE = "volatility_spike"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    SECURITY_BREACH = "security_breach"
    SYSTEM_FAILURE = "system_failure"
    GOVERNANCE_OVERRIDE = "governance_override"


@dataclass
class EmergencyEvent:
    """Record of an emergency event"""
    event_id: str
    timestamp: datetime
    emergency_type: EmergencyType
    level: EmergencyLevel
    triggered_by: str  # System or governance member
    reason: str
    action_taken: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "emergency_type": self.emergency_type.value,
            "level": self.level.value,
            "triggered_by": self.triggered_by,
            "reason": self.reason,
            "action_taken": self.action_taken,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
        }


class EmergencyProtocol:
    """
    Emergency response system.
    
    Provides immediate circuit breakers that can:
    - Pause all trading
    - Close all positions
    - Lock governance
    - Alert operators
    
    Emergency actions bypass normal governance delays
    but require elevated quorum for manual triggers.
    """
    
    # Thresholds for automatic emergency triggers
    AUTO_TRIGGERS = {
        "volatility_spike": 0.15,  # 15% volatility triggers alert
        "drawdown_critical": 0.08,  # 8% drawdown triggers critical
        "liquidity_crisis": 0.1,   # 10% liquidity drop triggers alert
    }
    
    def __init__(self):
        self._current_level = EmergencyLevel.WARNING
        self._events: List[EmergencyEvent] = []
        self._is_locked = False
        self._pause_trading = False
    
    @property
    def is_emergency_active(self) -> bool:
        """Check if any emergency is active"""
        return self._current_level in (EmergencyLevel.CRITICAL, EmergencyLevel.LOCKDOWN)
    
    @property
    def is_trading_paused(self) -> bool:
        """Check if trading is paused"""
        return self._pause_trading
    
    def check_automatic_triggers(
        self,
        volatility: float,
        drawdown: float,
        liquidity_change: float
    ) -> Optional[EmergencyEvent]:
        """
        Check if any automatic emergency triggers are met.
        
        Args:
            volatility: Current market volatility (0-1)
            drawdown: Current portfolio drawdown (0-1)
            liquidity_change: Change in liquidity (negative = decrease)
        
        Returns:
            EmergencyEvent if triggered, None otherwise
        """
        import uuid
        now = datetime.now(timezone.utc)
        
        # Volatility spike
        if volatility >= self.AUTO_TRIGGERS["volatility_spike"]:
            return self._trigger_emergency(
                event_id=str(uuid.uuid4()),
                emergency_type=EmergencyType.VOLATILITY_SPIKE,
                level=EmergencyLevel.ALERT,
                triggered_by="system",
                reason=f"Volatility spike detected: {volatility:.2%}",
            )
        
        # Critical drawdown
        if drawdown >= self.AUTO_TRIGGERS["drawdown_critical"]:
            return self._trigger_emergency(
                event_id=str(uuid.uuid4()),
                emergency_type=EmergencyType.MARKET_CRASH,
                level=EmergencyLevel.CRITICAL,
                triggered_by="system",
                reason=f"Critical drawdown: {drawdown:.2%}",
            )
        
        # Liquidity crisis
        if liquidity_change <= -self.AUTO_TRIGGERS["liquidity_crisis"]:
            return self._trigger_emergency(
                event_id=str(uuid.uuid4()),
                emergency_type=EmergencyType.LIQUIDITY_CRISIS,
                level=EmergencyLevel.ALERT,
                triggered_by="system",
                reason=f"Liquidity crisis: {liquidity_change:.2%} change",
            )
        
        return None
    
    def _trigger_emergency(
        self,
        event_id: str,
        emergency_type: EmergencyType,
        level: EmergencyLevel,
        triggered_by: str,
        reason: str,
    ) -> EmergencyEvent:
        """
        Trigger an emergency event and take appropriate action.
        """
        now = datetime.now(timezone.utc)
        
        # Determine action based on level
        action = self._get_emergency_action(level)
        
        event = EmergencyEvent(
            event_id=event_id,
            timestamp=now,
            emergency_type=emergency_type,
            level=level,
            triggered_by=triggered_by,
            reason=reason,
            action_taken=action,
        )
        
        self._events.append(event)
        self._current_level = level
        
        # Execute emergency action
        self._execute_emergency_action(level)
        
        return event
    
    def _get_emergency_action(self, level: EmergencyLevel) -> str:
        """Get action description for emergency level"""
        actions = {
            EmergencyLevel.WARNING: "Elevated monitoring activated",
            EmergencyLevel.ALERT: "Trading reduced, risk limits tightened",
            EmergencyLevel.CRITICAL: "Trading suspended, positions monitored",
            EmergencyLevel.LOCKDOWN: "Full lockdown, all positions closed",
        }
        return actions.get(level, "Unknown action")
    
    def _execute_emergency_action(self, level: EmergencyLevel):
        """Execute the emergency action"""
        from agent.policy_engine import policy_engine
        
        if level == EmergencyLevel.WARNING:
            # Just monitoring, no action
            pass
        
        elif level == EmergencyLevel.ALERT:
            # Tighten risk limits temporarily
            config.risk_limits.max_single_trade_pct *= 0.5
            config.risk_limits.max_position_pct *= 0.5
        
        elif level == EmergencyLevel.CRITICAL:
            # Pause trading
            self._pause_trading = True
            policy_engine.set_governance_pause(True)
        
        elif level == EmergencyLevel.LOCKDOWN:
            # Full lockdown
            self._pause_trading = True
            self._is_locked = True
            policy_engine.set_governance_pause(True)
            # In production, would also trigger position closing
    
    def trigger_manual_emergency(
        self,
        emergency_type: EmergencyType,
        level: EmergencyLevel,
        triggered_by: str,
        reason: str,
    ) -> EmergencyEvent:
        """
        Manually trigger an emergency.
        Called by governance with elevated quorum.
        """
        import uuid
        
        return self._trigger_emergency(
            event_id=str(uuid.uuid4()),
            emergency_type=emergency_type,
            level=level,
            triggered_by=triggered_by,
            reason=reason,
        )
    
    def resolve_emergency(self, event_id: str, resolution_notes: str = "") -> bool:
        """
        Resolve an emergency event.
        
        Args:
            event_id: ID of the event to resolve
            resolution_notes: Notes about the resolution
        
        Returns:
            True if resolved successfully
        """
        from agent.policy_engine import policy_engine
        
        for event in self._events:
            if event.event_id == event_id and not event.resolved:
                event.resolved = True
                event.resolved_at = datetime.now(timezone.utc)
                event.resolution_notes = resolution_notes
                
                # Check if all emergencies are resolved
                active_emergencies = [e for e in self._events if not e.resolved]
                if not active_emergencies:
                    self._current_level = EmergencyLevel.WARNING
                    self._pause_trading = False
                    self._is_locked = False
                    policy_engine.set_governance_pause(False)
                    
                    # Reset risk limits
                    config.risk_limits = config.risk_limits.__class__()
                
                return True
        
        return False
    
    def pause_trading(self):
        """Manually pause trading"""
        from agent.policy_engine import policy_engine
        
        self._pause_trading = True
        policy_engine.set_governance_pause(True)
    
    def resume_trading(self):
        """Manually resume trading"""
        from agent.policy_engine import policy_engine
        
        if not self._is_locked:
            self._pause_trading = False
            policy_engine.set_governance_pause(False)
    
    def close_all_positions(self) -> Dict:
        """
        Emergency: Close all positions.
        
        In production, this would:
        1. Get all open positions
        2. Create emergency sell orders
        3. Execute immediately
        """
        from agent.executor import executor
        
        portfolio = executor.get_portfolio_state()
        if not portfolio:
            return {"success": False, "error": "No portfolio state"}
        
        closed_positions = []
        for asset, value in portfolio.positions.items():
            if value > 0:
                # In simulation, just mark as closed
                closed_positions.append({
                    "asset": asset,
                    "value": value,
                    "status": "closed"
                })
        
        # Reset positions
        portfolio.cash_balance += sum(portfolio.positions.values())
        portfolio.positions = {}
        
        return {
            "success": True,
            "closed_positions": closed_positions,
            "total_value_recovered": sum(p["value"] for p in closed_positions),
        }
    
    def get_status(self) -> Dict:
        """Get emergency protocol status"""
        return {
            "current_level": self._current_level.value,
            "is_emergency_active": self.is_emergency_active,
            "is_trading_paused": self._pause_trading,
            "is_locked": self._is_locked,
            "active_events": [
                e.to_dict() for e in self._events if not e.resolved
            ],
            "total_events": len(self._events),
        }
    
    def get_event_history(self) -> List[Dict]:
        """Get all emergency events"""
        return [e.to_dict() for e in self._events]


# Global emergency protocol instance
emergency_protocol = EmergencyProtocol()
