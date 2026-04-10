"""
Sentinel-01 Main Loop
AETHEL Finance Lab - Agent Orchestration

This is the main decision loop for Sentinel-01.
It orchestrates all modules in a continuous cycle:

1. Fetch market data
2. Generate signals
3. Classify regime
4. Get policy constraints
5. Decide candidate action
6. Risk assessment
7. Execute if approved
8. Record validation artifact
9. Repeat
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import random

from .config import config, MarketRegime, ActionType
from .signal_engine import signal_engine, MarketSignal
from .risk_engine import risk_engine, RiskAssessment, PortfolioState
from .policy_engine import policy_engine, PolicyDecision
from .executor import executor, TradeIntent, ExecutionResult
from .reputation_tracker import reputation_tracker, ValidationArtifact

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("sentinel-01")


class Sentinel01Agent:
    """
    Main Sentinel-01 Agent class.
    
    Core beliefs:
    - Capital preservation is mandatory
    - Profit is secondary
    - Policy compliance is non-negotiable
    - Every decision must be auditable
    """
    
    def __init__(self):
        self._running = False
        self._cycle_count = 0
        self._initial_capital = config.simulation.initial_capital
        self._portfolio: Optional[PortfolioState] = None
        self._market_data_source = None  # Set by adapter
        self._last_prices: Dict[str, float] = {
            "ETH": 2500.0,  # Default starting prices
            "BTC": 45000.0,
        }
        
        # Initialize portfolio
        self._initialize_portfolio()
        
        logger.info(f"Sentinel-01 initialized")
        logger.info(f"Policy Hash: {config.identity.policy_hash[:16]}...")
        logger.info(f"Simulation Mode: {config.simulation.enabled}")
        logger.info(f"Initial Capital: ${self._initial_capital:,.2f}")
    
    def _initialize_portfolio(self):
        """Initialize portfolio state"""
        self._portfolio = PortfolioState(
            total_value=self._initial_capital,
            cash_balance=self._initial_capital,
            positions={},
            daily_pnl=0.0,
            peak_value=self._initial_capital,
            current_drawdown=0.0,
            trades_today=0,
        )
        
        # Sync with risk engine and executor
        risk_engine.set_portfolio_state(self._portfolio)
        executor.set_portfolio_state(self._portfolio)
    
    def set_market_data_source(self, source):
        """Set external market data source (adapter)"""
        self._market_data_source = source
    
    async def fetch_market_data(self, asset: str) -> MarketSignal:
        """
        Fetch market data for asset.
        Uses external source if available, otherwise generates mock data.
        """
        if self._market_data_source:
            try:
                data = await self._market_data_source.get_price(asset)
                return signal_engine.process_market_data(
                    asset=asset,
                    price=data.get("price", self._last_prices.get(asset, 0)),
                    volume=data.get("volume_24h", 0),
                    price_change_24h=data.get("price_change_24h", 0)
                )
            except Exception as e:
                logger.warning(f"External data source failed: {e}, using mock data")
        
        # Generate mock data in simulation mode
        base_price = self._last_prices.get(asset, 1000)
        signal = signal_engine.generate_mock_signal(asset, base_price)
        self._last_prices[asset] = signal.price
        executor.update_price(asset, signal.price)
        return signal
    
    def decide_candidate_action(self, signal: MarketSignal, 
                                 policy: PolicyDecision) -> tuple[ActionType, str, float]:
        """
        Decide candidate action based on signal and policy.
        
        This is the minimal strategy layer. It proposes an action,
        but the risk engine has final say.
        
        Returns:
            Tuple of (action, asset, amount)
        """
        # Default: HOLD
        if ActionType.HOLD not in policy.allowed_actions:
            # This should never happen
            logger.error("HOLD not in allowed actions - policy error")
            return ActionType.HOLD, signal.asset, 0.0
        
        # In crisis or unknown regime, always hold
        if policy.regime in (MarketRegime.CRISIS, MarketRegime.UNKNOWN):
            return ActionType.HOLD, signal.asset, 0.0
        
        # Simple trend-following strategy
        trend_threshold = config.policy_thresholds.trend_strength_min
        
        # Strong uptrend + low volatility = consider buying
        if (signal.trend_direction > 0.3 and 
            signal.trend_strength > trend_threshold and
            signal.volatility < config.policy_thresholds.volatility_volatile_max and
            ActionType.BUY in policy.allowed_actions):
            
            # Calculate trade size based on policy limits
            max_trade = self._portfolio.total_value * (policy.max_trade_size_pct / 100)
            trade_size = max_trade * policy.position_sizing_multiplier
            
            if trade_size > 100:  # Minimum trade size
                return ActionType.BUY, signal.asset, trade_size
        
        # Strong downtrend = consider reducing exposure
        if (signal.trend_direction < -0.3 and 
            signal.trend_strength > trend_threshold):
            
            current_position = self._portfolio.positions.get(signal.asset, 0)
            if current_position > 0 and ActionType.SELL in policy.allowed_actions:
                sell_amount = current_position * 0.5  # Sell half
                return ActionType.SELL, signal.asset, sell_amount
        
        return ActionType.HOLD, signal.asset, 0.0
    
    def update_portfolio_state(self):
        """Update portfolio metrics after trades"""
        # Calculate total value
        total_position_value = sum(self._portfolio.positions.values())
        self._portfolio.total_value = self._portfolio.cash_balance + total_position_value
        
        # Update peak and drawdown
        if self._portfolio.total_value > self._portfolio.peak_value:
            self._portfolio.peak_value = self._portfolio.total_value
        
        self._portfolio.current_drawdown = (
            (self._portfolio.peak_value - self._portfolio.total_value) / 
            self._portfolio.peak_value
        ) if self._portfolio.peak_value > 0 else 0
        
        # Update P&L
        self._portfolio.daily_pnl = self._portfolio.total_value - self._initial_capital
        
        # Sync with risk engine
        risk_engine.set_portfolio_state(self._portfolio)
        executor.set_portfolio_state(self._portfolio)
        
        # Update reputation tracker
        reputation_tracker.update_pnl(
            self._portfolio.daily_pnl,
            self._portfolio.current_drawdown
        )
    
    async def run_cycle(self, asset: str = "ETH") -> ValidationArtifact:
        """
        Run a single decision cycle.
        
        Returns:
            ValidationArtifact for this cycle
        """
        self._cycle_count += 1
        logger.info(f"=== Cycle {self._cycle_count} ===")
        
        # Step 1: Fetch market data
        signal = await self.fetch_market_data(asset)
        logger.info(f"Signal: {asset} @ ${signal.price:,.2f} | Vol: {signal.volatility:.2%} | Trend: {signal.trend_direction:+.2f}")
        
        # Step 2: Get policy constraints
        policy = policy_engine.get_policy(signal)
        logger.info(f"Regime: {policy.regime.value} | Allowed: {[a.value for a in policy.allowed_actions]}")
        
        # Step 3: Decide candidate action
        action, target_asset, amount = self.decide_candidate_action(signal, policy)
        logger.info(f"Candidate: {action.value} {target_asset} ${amount:,.2f}")
        
        # Step 4: Risk assessment
        assessment: Optional[RiskAssessment] = None
        intent: Optional[TradeIntent] = None
        result: Optional[ExecutionResult] = None
        
        if action != ActionType.HOLD:
            assessment = risk_engine.assess_trade(action, target_asset, amount, signal)
            
            if assessment.approved:
                logger.info(f"Risk: APPROVED (score: {assessment.risk_score:.2f})")
                
                # Step 5: Build and execute
                intent = executor.build_intent(action, target_asset, amount, assessment)
                intent = executor.sign_intent(intent)
                result = executor.execute(intent)
                
                if result.success:
                    logger.info(f"Executed: {result.executed_amount:.2f} @ ${result.executed_price:,.2f}")
                else:
                    logger.warning(f"Execution failed: {result.error_message}")
                    action = ActionType.HOLD  # Revert to HOLD
            else:
                logger.warning(f"Risk: BLOCKED - {assessment.rejection_reasons}")
                action = ActionType.HOLD
        else:
            logger.info("Action: HOLD")
        
        # Step 6: Update portfolio state
        self.update_portfolio_state()
        logger.info(f"Portfolio: ${self._portfolio.total_value:,.2f} | Drawdown: {self._portfolio.current_drawdown:.2%}")
        
        # Step 7: Record validation artifact
        artifact = reputation_tracker.record_cycle(
            signal=signal,
            portfolio_state=self._portfolio.to_dict(),
            policy=policy,
            assessment=assessment,
            action=action,
            intent=intent,
            result=result
        )
        logger.info(f"Artifact: {artifact.artifact_hash[:16]}...")
        
        return artifact
    
    async def run(self, cycles: Optional[int] = None, interval_seconds: int = 5):
        """
        Run the agent continuously or for specified cycles.
        
        Args:
            cycles: Number of cycles to run (None = infinite)
            interval_seconds: Seconds between cycles
        """
        self._running = True
        cycle = 0
        
        logger.info("Sentinel-01 starting...")
        logger.info(f"Cycles: {'Infinite' if cycles is None else cycles}")
        logger.info(f"Interval: {interval_seconds}s")
        
        while self._running:
            try:
                # Rotate through supported assets
                assets = config.simulation.supported_assets
                asset = assets[cycle % len(assets)]
                
                await self.run_cycle(asset)
                
                cycle += 1
                if cycles is not None and cycle >= cycles:
                    break
                
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Agent stopped by user")
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(interval_seconds)
        
        self._running = False
        logger.info("Sentinel-01 stopped")
    
    def stop(self):
        """Stop the agent"""
        self._running = False
    
    def get_status(self) -> Dict:
        """Get current agent status"""
        return {
            "agent_id": config.identity.agent_id,
            "version": config.identity.version,
            "policy_hash": config.identity.policy_hash,
            "running": self._running,
            "cycle_count": self._cycle_count,
            "simulation_mode": config.simulation.enabled,
            "current_regime": policy_engine.get_current_regime().value,
            "portfolio": self._portfolio.to_dict() if self._portfolio else None,
            "metrics": reputation_tracker.get_metrics().to_dict(),
        }


# Global agent instance
agent = Sentinel01Agent()


async def main():
    """Main entry point for standalone execution"""
    try:
        await agent.run(cycles=50, interval_seconds=3)
    except KeyboardInterrupt:
        agent.stop()
    finally:
        summary = reputation_tracker.get_cycle_summary()
        logger.info("=== Session Summary ===")
        logger.info(f"Total Cycles: {summary['total_cycles']}")
        logger.info(f"Metrics: {summary['metrics']}")


if __name__ == "__main__":
    asyncio.run(main())
