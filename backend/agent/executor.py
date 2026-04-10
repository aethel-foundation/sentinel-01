"""
Sentinel-01 Executor
AETHEL Finance Lab - Trade Intent Building and Execution

This module builds ERC-8004 compliant TradeIntents and handles execution.
In simulation mode, executes against mock state.
In production, interfaces with ERC-8004 Risk Router.

IMPORTANT: Executor does NOT make decisions.
It only executes validated, approved actions.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, List
from enum import Enum

from .config import config, ActionType
from .risk_engine import RiskAssessment, PortfolioState


class IntentStatus(Enum):
    """TradeIntent execution status"""
    PENDING = "pending"
    SIGNED = "signed"
    SUBMITTED = "submitted"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class TradeIntent:
    """
    ERC-8004 TradeIntent structure.
    
    Represents a proposed trade with full audit trail.
    """
    intent_id: str
    timestamp: datetime
    agent_id: str
    action: ActionType
    asset: str
    amount: float
    price: float
    policy_hash: str
    risk_assessment_hash: str
    signature: str = ""
    status: IntentStatus = IntentStatus.PENDING
    execution_result: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "intent_id": self.intent_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "action": self.action.value,
            "asset": self.asset,
            "amount": round(self.amount, 6),
            "price": round(self.price, 2),
            "policy_hash": self.policy_hash,
            "risk_assessment_hash": self.risk_assessment_hash,
            "signature": self.signature,
            "status": self.status.value,
            "execution_result": self.execution_result,
        }
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of intent"""
        data = {
            "intent_id": self.intent_id,
            "agent_id": self.agent_id,
            "action": self.action.value,
            "asset": self.asset,
            "amount": self.amount,
            "price": self.price,
            "policy_hash": self.policy_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


@dataclass
class ExecutionResult:
    """Result of trade execution"""
    success: bool
    intent_id: str
    executed_amount: float
    executed_price: float
    fees: float
    error_message: Optional[str] = None
    tx_hash: Optional[str] = None  # For on-chain execution
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "intent_id": self.intent_id,
            "executed_amount": round(self.executed_amount, 6),
            "executed_price": round(self.executed_price, 2),
            "fees": round(self.fees, 4),
            "error_message": self.error_message,
            "tx_hash": self.tx_hash,
        }


class Executor:
    """
    Trade executor with simulation and production modes.
    
    Responsibilities:
    - Build TradeIntents from approved actions
    - Sign intents (EIP-712 in production)
    - Execute against simulation state or submit to Risk Router
    - Track execution history
    """
    
    def __init__(self):
        self._simulation_mode = config.simulation.enabled
        self._portfolio: Optional[PortfolioState] = None
        self._execution_history: List[TradeIntent] = []
        self._prices: Dict[str, float] = {}  # Asset -> price cache
    
    def set_portfolio_state(self, portfolio: PortfolioState):
        """Set current portfolio state"""
        self._portfolio = portfolio
    
    def get_portfolio_state(self) -> Optional[PortfolioState]:
        """Get current portfolio state"""
        return self._portfolio
    
    def update_price(self, asset: str, price: float):
        """Update asset price cache"""
        self._prices[asset] = price
    
    def build_intent(self, action: ActionType, asset: str, amount: float,
                     assessment: RiskAssessment) -> TradeIntent:
        """
        Build a TradeIntent from approved action.
        
        Args:
            action: Action to execute
            asset: Target asset
            amount: Trade amount in USD
            assessment: Risk assessment (must be approved)
        
        Returns:
            TradeIntent ready for signing
        """
        now = datetime.now(timezone.utc)
        
        # Get current price
        price = self._prices.get(asset, 0.0)
        
        # Hash the risk assessment
        assessment_hash = hashlib.sha256(
            json.dumps(assessment.to_dict(), sort_keys=True).encode()
        ).hexdigest()
        
        intent = TradeIntent(
            intent_id=str(uuid.uuid4()),
            timestamp=now,
            agent_id=config.identity.agent_id,
            action=action,
            asset=asset,
            amount=amount,
            price=price,
            policy_hash=config.identity.policy_hash,
            risk_assessment_hash=assessment_hash,
        )
        
        return intent
    
    def sign_intent(self, intent: TradeIntent) -> TradeIntent:
        """
        Sign the TradeIntent.
        
        In production: EIP-712 signature with agent's private key
        In simulation: Placeholder signature
        """
        if self._simulation_mode:
            # Simulation: use hash as placeholder signature
            intent.signature = f"SIM_SIG_{intent.compute_hash()[:16]}"
        else:
            # TODO: Implement EIP-712 signing with real key
            # This would use web3.py or similar library:
            # from eth_account.messages import encode_typed_data
            # signed = account.sign_message(encode_typed_data(intent.to_eip712()))
            # intent.signature = signed.signature.hex()
            intent.signature = f"PLACEHOLDER_SIG_{intent.compute_hash()[:16]}"
        
        intent.status = IntentStatus.SIGNED
        return intent
    
    def execute(self, intent: TradeIntent) -> ExecutionResult:
        """
        Execute a signed TradeIntent.
        
        In simulation mode: Update mock portfolio state
        In production: Submit to ERC-8004 Risk Router
        """
        if intent.status != IntentStatus.SIGNED:
            return ExecutionResult(
                success=False,
                intent_id=intent.intent_id,
                executed_amount=0,
                executed_price=0,
                fees=0,
                error_message="Intent must be signed before execution"
            )
        
        intent.status = IntentStatus.SUBMITTED
        
        if self._simulation_mode:
            result = self._execute_simulation(intent)
        else:
            result = self._execute_production(intent)
        
        # Update intent status
        if result.success:
            intent.status = IntentStatus.EXECUTED
        else:
            intent.status = IntentStatus.FAILED
        
        intent.execution_result = result.to_dict()
        self._execution_history.append(intent)
        
        return result
    
    def _execute_simulation(self, intent: TradeIntent) -> ExecutionResult:
        """Execute against simulation portfolio"""
        if self._portfolio is None:
            return ExecutionResult(
                success=False,
                intent_id=intent.intent_id,
                executed_amount=0,
                executed_price=0,
                fees=0,
                error_message="Portfolio not initialized"
            )
        
        # Simulate fees (0.1%)
        fees = intent.amount * 0.001
        net_amount = intent.amount - fees
        
        if intent.action == ActionType.HOLD:
            return ExecutionResult(
                success=True,
                intent_id=intent.intent_id,
                executed_amount=0,
                executed_price=intent.price,
                fees=0,
            )
        
        if intent.action == ActionType.BUY:
            if self._portfolio.cash_balance < intent.amount:
                return ExecutionResult(
                    success=False,
                    intent_id=intent.intent_id,
                    executed_amount=0,
                    executed_price=intent.price,
                    fees=0,
                    error_message="Insufficient cash balance"
                )
            
            # Update portfolio
            self._portfolio.cash_balance -= intent.amount
            current_position = self._portfolio.positions.get(intent.asset, 0)
            self._portfolio.positions[intent.asset] = current_position + net_amount
            self._portfolio.trades_today += 1
            
            return ExecutionResult(
                success=True,
                intent_id=intent.intent_id,
                executed_amount=net_amount,
                executed_price=intent.price,
                fees=fees,
                tx_hash=f"SIM_TX_{intent.intent_id[:8]}"
            )
        
        if intent.action in (ActionType.SELL, ActionType.REDUCE_EXPOSURE, ActionType.EMERGENCY_EXIT):
            current_position = self._portfolio.positions.get(intent.asset, 0)
            sell_amount = min(intent.amount, current_position)
            
            if sell_amount <= 0:
                return ExecutionResult(
                    success=False,
                    intent_id=intent.intent_id,
                    executed_amount=0,
                    executed_price=intent.price,
                    fees=0,
                    error_message="No position to sell"
                )
            
            # Update portfolio
            self._portfolio.positions[intent.asset] = current_position - sell_amount
            self._portfolio.cash_balance += (sell_amount - fees)
            self._portfolio.trades_today += 1
            
            return ExecutionResult(
                success=True,
                intent_id=intent.intent_id,
                executed_amount=sell_amount,
                executed_price=intent.price,
                fees=fees,
                tx_hash=f"SIM_TX_{intent.intent_id[:8]}"
            )
        
        return ExecutionResult(
            success=False,
            intent_id=intent.intent_id,
            executed_amount=0,
            executed_price=intent.price,
            fees=0,
            error_message=f"Unknown action type: {intent.action.value}"
        )
    
    def _execute_production(self, intent: TradeIntent) -> ExecutionResult:
        """
        Submit to ERC-8004 Risk Router.
        
        TODO: Implement real on-chain execution:
        1. Connect to Risk Router contract
        2. Submit signed TradeIntent
        3. Wait for confirmation
        4. Parse execution result
        """
        # Placeholder for production execution
        return ExecutionResult(
            success=False,
            intent_id=intent.intent_id,
            executed_amount=0,
            executed_price=intent.price,
            fees=0,
            error_message="Production execution not yet implemented"
        )
    
    def get_execution_history(self) -> List[Dict]:
        """Get execution history"""
        return [intent.to_dict() for intent in self._execution_history]
    
    def get_pending_intents(self) -> List[TradeIntent]:
        """Get intents that haven't been executed yet"""
        return [i for i in self._execution_history 
                if i.status in (IntentStatus.PENDING, IntentStatus.SIGNED)]


# Global executor instance
executor = Executor()
