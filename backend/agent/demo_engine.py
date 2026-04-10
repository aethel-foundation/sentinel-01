"""
Sentinel-01 Demo Mode
AETHEL Finance Lab - Pre-configured Scenarios for Demonstration

Provides dramatic, observable regime transitions and agent behavior
for hackathon presentations and stakeholder demos.
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum

from .config import config, MarketRegime, ActionType
from .signal_engine import signal_engine, MarketSignal
from .risk_engine import risk_engine, PortfolioState
from .policy_engine import policy_engine
from .executor import executor
from .reputation_tracker import reputation_tracker


class DemoScenario(Enum):
    """Pre-configured demo scenarios"""
    NORMAL_TRADING = "normal_trading"      # Calm market, some trades
    VOLATILITY_SPIKE = "volatility_spike"  # Sudden volatility increase
    FLASH_CRASH = "flash_crash"            # 15%+ drop, crisis mode
    BULL_RUN = "bull_run"                  # Strong uptrend
    RECOVERY = "recovery"                  # Post-crash recovery
    GOVERNANCE_PAUSE = "governance_pause"  # External pause
    RISK_BLOCK = "risk_block"              # Trade blocked by risk engine
    FULL_CYCLE = "full_cycle"              # Complete market cycle


@dataclass
class ScenarioConfig:
    """Configuration for a demo scenario"""
    name: str
    description: str
    duration_cycles: int
    initial_price: float
    price_changes: List[float]  # % change per cycle
    volatility_levels: List[float]  # 0-1
    volume_multiplier: float
    expected_regime: MarketRegime
    expected_actions: List[ActionType]
    narrative: str


class DemoEngine:
    """
    Demo scenario engine for Sentinel-01.
    
    Generates controlled market conditions to demonstrate:
    - Regime transitions
    - Risk blocking behavior
    - Policy enforcement
    - ValidationArtifact generation
    - Emergency protocols
    """
    
    SCENARIOS = {
        DemoScenario.NORMAL_TRADING: ScenarioConfig(
            name="Normal Trading",
            description="Calm market with minor fluctuations",
            duration_cycles=10,
            initial_price=2500.0,
            price_changes=[0.5, -0.3, 0.8, -0.2, 0.4, 0.1, -0.5, 0.3, 0.2, -0.1],
            volatility_levels=[0.01, 0.01, 0.015, 0.01, 0.012, 0.01, 0.01, 0.015, 0.01, 0.01],
            volume_multiplier=1.0,
            expected_regime=MarketRegime.NORMAL,
            expected_actions=[ActionType.HOLD, ActionType.BUY],
            narrative="Market is stable. Agent monitors for opportunities while maintaining capital safety."
        ),
        
        DemoScenario.VOLATILITY_SPIKE: ScenarioConfig(
            name="Volatility Spike",
            description="Sudden increase in market volatility",
            duration_cycles=8,
            initial_price=2500.0,
            price_changes=[0.3, 2.5, -3.2, 4.1, -2.8, 1.5, -1.2, 0.5],
            volatility_levels=[0.01, 0.04, 0.06, 0.07, 0.055, 0.04, 0.03, 0.02],
            volume_multiplier=2.5,
            expected_regime=MarketRegime.VOLATILE,
            expected_actions=[ActionType.HOLD, ActionType.REDUCE_EXPOSURE],
            narrative="Volatility spikes! Agent shifts to defensive mode, reducing exposure."
        ),
        
        DemoScenario.FLASH_CRASH: ScenarioConfig(
            name="Flash Crash",
            description="Rapid 15%+ price decline triggering crisis mode",
            duration_cycles=6,
            initial_price=2500.0,
            price_changes=[-5.0, -8.0, -4.0, -2.0, 1.0, 2.0],
            volatility_levels=[0.02, 0.09, 0.12, 0.10, 0.08, 0.05],
            volume_multiplier=5.0,
            expected_regime=MarketRegime.CRISIS,
            expected_actions=[ActionType.HOLD, ActionType.EMERGENCY_EXIT],
            narrative="CRASH DETECTED! Agent enters CRISIS mode - capital preservation is MANDATORY."
        ),
        
        DemoScenario.BULL_RUN: ScenarioConfig(
            name="Bull Run",
            description="Strong sustained uptrend",
            duration_cycles=10,
            initial_price=2500.0,
            price_changes=[1.5, 2.0, 1.8, 2.5, 1.2, 1.8, 2.2, 1.5, 1.0, 0.8],
            volatility_levels=[0.015, 0.018, 0.02, 0.022, 0.02, 0.018, 0.02, 0.018, 0.015, 0.012],
            volume_multiplier=1.8,
            expected_regime=MarketRegime.NORMAL,
            expected_actions=[ActionType.BUY, ActionType.HOLD],
            narrative="Strong uptrend detected. Agent identifies opportunity within risk limits."
        ),
        
        DemoScenario.RECOVERY: ScenarioConfig(
            name="Recovery",
            description="Market recovery after crash",
            duration_cycles=8,
            initial_price=2000.0,  # Post-crash price
            price_changes=[3.0, 2.5, 1.8, 1.2, 0.8, 0.5, 0.3, 0.2],
            volatility_levels=[0.06, 0.05, 0.04, 0.035, 0.03, 0.025, 0.02, 0.015],
            volume_multiplier=1.5,
            expected_regime=MarketRegime.VOLATILE,
            expected_actions=[ActionType.HOLD, ActionType.BUY],
            narrative="Market recovering. Agent waits for volatility to normalize before re-entering."
        ),
        
        DemoScenario.RISK_BLOCK: ScenarioConfig(
            name="Risk Block Demo",
            description="Demonstrates risk engine blocking trades",
            duration_cycles=5,
            initial_price=2500.0,
            price_changes=[0.5, 0.8, 1.0, 0.5, 0.3],
            volatility_levels=[0.01, 0.01, 0.01, 0.01, 0.01],
            volume_multiplier=1.0,
            expected_regime=MarketRegime.NORMAL,
            expected_actions=[ActionType.HOLD],
            narrative="Agent wants to trade but risk limits prevent it. POLICY COMPLIANCE IS MANDATORY."
        ),
        
        DemoScenario.FULL_CYCLE: ScenarioConfig(
            name="Full Market Cycle",
            description="Complete cycle: normal → volatile → crash → recovery",
            duration_cycles=20,
            initial_price=2500.0,
            price_changes=[
                0.5, 0.8, 1.0,  # Normal
                2.5, -2.0, 3.0, -2.5,  # Volatile
                -5.0, -8.0, -4.0,  # Crash
                -1.0, 1.0, 2.0, 2.5, 1.8,  # Recovery start
                1.2, 0.8, 0.5, 0.3, 0.2  # Stabilization
            ],
            volatility_levels=[
                0.01, 0.01, 0.015,
                0.04, 0.05, 0.055, 0.06,
                0.09, 0.12, 0.10,
                0.08, 0.06, 0.05, 0.04, 0.035,
                0.03, 0.025, 0.02, 0.015, 0.01
            ],
            volume_multiplier=2.0,
            expected_regime=MarketRegime.NORMAL,
            expected_actions=[ActionType.HOLD, ActionType.BUY, ActionType.REDUCE_EXPOSURE],
            narrative="Complete market cycle demonstrating all regime transitions and agent responses."
        ),
    }
    
    def __init__(self):
        self._current_scenario: Optional[DemoScenario] = None
        self._scenario_cycle = 0
        self._scenario_config: Optional[ScenarioConfig] = None
        self._current_price = 2500.0
        self._scenario_history: List[Dict] = []
        self._is_running = False
    
    def get_available_scenarios(self) -> List[Dict]:
        """Get list of available demo scenarios"""
        return [
            {
                "id": scenario.value,
                "name": self.SCENARIOS[scenario].name,
                "description": self.SCENARIOS[scenario].description,
                "duration_cycles": self.SCENARIOS[scenario].duration_cycles,
                "expected_regime": self.SCENARIOS[scenario].expected_regime.value,
                "narrative": self.SCENARIOS[scenario].narrative,
            }
            for scenario in DemoScenario
        ]
    
    def start_scenario(self, scenario: DemoScenario) -> Dict:
        """Start a demo scenario"""
        self._current_scenario = scenario
        self._scenario_config = self.SCENARIOS[scenario]
        self._scenario_cycle = 0
        self._current_price = self._scenario_config.initial_price
        self._scenario_history = []
        self._is_running = True
        
        return {
            "status": "started",
            "scenario": scenario.value,
            "name": self._scenario_config.name,
            "description": self._scenario_config.description,
            "total_cycles": self._scenario_config.duration_cycles,
            "narrative": self._scenario_config.narrative,
        }
    
    def stop_scenario(self) -> Dict:
        """Stop current scenario"""
        self._is_running = False
        return {
            "status": "stopped",
            "completed_cycles": self._scenario_cycle,
            "history": self._scenario_history,
        }
    
    def get_demo_signal(self, asset: str = "ETH") -> MarketSignal:
        """
        Generate market signal based on current scenario state.
        
        Returns controlled signal for demo purposes.
        """
        if not self._is_running or not self._scenario_config:
            # Return normal random signal if no scenario
            return signal_engine.generate_mock_signal(asset, 2500.0)
        
        # Get scenario parameters for current cycle
        cycle_idx = min(self._scenario_cycle, len(self._scenario_config.price_changes) - 1)
        
        price_change_pct = self._scenario_config.price_changes[cycle_idx]
        volatility = self._scenario_config.volatility_levels[cycle_idx]
        
        # Update price
        self._current_price *= (1 + price_change_pct / 100)
        
        # Create controlled signal
        now = datetime.now(timezone.utc)
        
        # Compute trend based on recent price changes
        recent_changes = self._scenario_config.price_changes[:cycle_idx+1][-5:]
        trend_direction = sum(recent_changes) / len(recent_changes) / 10 if recent_changes else 0
        trend_strength = min(abs(trend_direction) * 2, 1.0)
        
        # Anomaly score based on extreme movements
        anomaly_score = 0.0
        if abs(price_change_pct) > 5:
            anomaly_score = min(abs(price_change_pct) / 15, 0.9)
        
        signal = MarketSignal(
            timestamp=now,
            asset=asset,
            price=self._current_price,
            volatility=volatility,
            trend_direction=max(-1, min(1, trend_direction)),
            trend_strength=trend_strength,
            liquidity_score=0.8 if volatility < 0.05 else 0.5,
            anomaly_score=anomaly_score,
            volume_24h=100_000_000 * self._scenario_config.volume_multiplier,
            price_change_24h=price_change_pct,
        )
        
        # Add to signal engine history
        signal_engine.price_history[asset] = signal_engine.price_history.get(asset, [])
        signal_engine.price_history[asset].append((now, self._current_price))
        
        # Increment cycle
        self._scenario_cycle += 1
        
        # Record history
        self._scenario_history.append({
            "cycle": self._scenario_cycle,
            "price": self._current_price,
            "price_change_pct": price_change_pct,
            "volatility": volatility,
            "regime": signal_engine.classify_regime(signal).value,
        })
        
        return signal
    
    def is_scenario_complete(self) -> bool:
        """Check if scenario has completed all cycles"""
        if not self._scenario_config:
            return True
        return self._scenario_cycle >= self._scenario_config.duration_cycles
    
    def get_scenario_status(self) -> Dict:
        """Get current scenario status"""
        if not self._current_scenario:
            return {"status": "idle", "available_scenarios": self.get_available_scenarios()}
        
        return {
            "status": "running" if self._is_running else "paused",
            "scenario": self._current_scenario.value,
            "name": self._scenario_config.name,
            "current_cycle": self._scenario_cycle,
            "total_cycles": self._scenario_config.duration_cycles,
            "current_price": self._current_price,
            "narrative": self._scenario_config.narrative,
            "history": self._scenario_history,
            "complete": self.is_scenario_complete(),
        }
    
    def get_narrative_for_cycle(self) -> str:
        """Get narrative description for current cycle"""
        if not self._scenario_config or not self._scenario_history:
            return "Initializing scenario..."
        
        latest = self._scenario_history[-1]
        regime = latest["regime"]
        price_change = latest["price_change_pct"]
        
        narratives = {
            "normal": [
                "Market stable. Agent monitoring for opportunities.",
                "Low volatility environment. Risk limits allow trading.",
                "Normal conditions. Evaluating trend signals.",
            ],
            "volatile": [
                "Volatility increasing! Switching to defensive mode.",
                "Market turbulence detected. Reducing position sizes.",
                "Elevated risk environment. Conservative stance.",
            ],
            "crisis": [
                "⚠️ CRISIS MODE ACTIVATED! Capital preservation mandatory.",
                "Extreme conditions detected. All trading suspended.",
                "Emergency protocol engaged. Protecting capital.",
            ],
        }
        
        regime_narratives = narratives.get(regime, ["Analyzing conditions..."])
        base_narrative = random.choice(regime_narratives)
        
        # Add price context
        if price_change > 2:
            base_narrative += f" (Price +{price_change:.1f}%)"
        elif price_change < -2:
            base_narrative += f" (Price {price_change:.1f}%)"
        
        return base_narrative


# Global demo engine instance
demo_engine = DemoEngine()
