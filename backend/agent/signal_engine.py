"""
Sentinel-01 Signal Engine
AETHEL Foundation - Market Signal Detection

Generates market signals: volatility, trend, liquidity, anomaly detection.
This module is OBSERVATIONAL ONLY - it does not make trading decisions.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from enum import Enum
import statistics

from agent.config import config, MarketRegime


@dataclass
class MarketSignal:
    """Market signal data container"""
    timestamp: datetime
    asset: str
    price: float
    volatility: float  # 0.0 to 1.0
    trend_direction: float  # -1.0 (bearish) to 1.0 (bullish)
    trend_strength: float  # 0.0 to 1.0
    liquidity_score: float  # 0.0 to 1.0
    anomaly_score: float  # 0.0 to 1.0
    volume_24h: float
    price_change_24h: float
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "asset": self.asset,
            "price": self.price,
            "volatility": round(self.volatility, 4),
            "trend_direction": round(self.trend_direction, 4),
            "trend_strength": round(self.trend_strength, 4),
            "liquidity_score": round(self.liquidity_score, 4),
            "anomaly_score": round(self.anomaly_score, 4),
            "volume_24h": self.volume_24h,
            "price_change_24h": round(self.price_change_24h, 4),
        }


class SignalEngine:
    """
    Market signal generation and analysis.
    
    Core responsibilities:
    - Process raw market data into actionable signals
    - Detect volatility regimes
    - Identify trend direction and strength
    - Assess liquidity conditions
    - Flag anomalies
    """
    
    def __init__(self):
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.max_history_length = 1000
        self._mock_mode = config.simulation.enabled
    
    def process_market_data(self, asset: str, price: float, volume: float, 
                            price_change_24h: float = 0.0) -> MarketSignal:
        """
        Process raw market data and generate signals.
        
        Args:
            asset: Asset symbol (e.g., "ETH", "BTC")
            price: Current price in USD
            volume: 24h trading volume
            price_change_24h: 24h price change percentage
        
        Returns:
            MarketSignal with computed indicators
        """
        now = datetime.now(timezone.utc)
        
        # Update price history
        if asset not in self.price_history:
            self.price_history[asset] = []
        
        self.price_history[asset].append((now, price))
        
        # Trim history
        if len(self.price_history[asset]) > self.max_history_length:
            self.price_history[asset] = self.price_history[asset][-self.max_history_length:]
        
        # Compute signals
        volatility = self._compute_volatility(asset)
        trend_direction, trend_strength = self._compute_trend(asset)
        liquidity_score = self._compute_liquidity_score(volume, price)
        anomaly_score = self._compute_anomaly_score(asset, price, volume, price_change_24h)
        
        return MarketSignal(
            timestamp=now,
            asset=asset,
            price=price,
            volatility=volatility,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            liquidity_score=liquidity_score,
            anomaly_score=anomaly_score,
            volume_24h=volume,
            price_change_24h=price_change_24h,
        )
    
    def _compute_volatility(self, asset: str) -> float:
        """Compute volatility from recent price history"""
        history = self.price_history.get(asset, [])
        
        if len(history) < 2:
            return 0.0
        
        # Use last 20 prices for volatility calculation
        recent_prices = [p for _, p in history[-20:]]
        
        if len(recent_prices) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(recent_prices)):
            if recent_prices[i-1] > 0:
                ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Standard deviation of returns
        try:
            vol = statistics.stdev(returns) if len(returns) > 1 else abs(returns[0])
        except:
            vol = 0.0
        
        # Normalize to 0-1 range (assuming max vol of 20%)
        return min(vol / 0.2, 1.0)
    
    def _compute_trend(self, asset: str) -> Tuple[float, float]:
        """
        Compute trend direction and strength.
        
        Returns:
            Tuple of (direction: -1 to 1, strength: 0 to 1)
        """
        history = self.price_history.get(asset, [])
        
        if len(history) < 5:
            return 0.0, 0.0
        
        recent_prices = [p for _, p in history[-20:]]
        
        if len(recent_prices) < 5:
            return 0.0, 0.0
        
        # Simple linear regression for trend
        n = len(recent_prices)
        x_mean = (n - 1) / 2
        y_mean = sum(recent_prices) / n
        
        numerator = sum((i - x_mean) * (p - y_mean) for i, p in enumerate(recent_prices))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0, 0.0
        
        slope = numerator / denominator
        
        # Normalize slope to direction (-1 to 1)
        price_range = max(recent_prices) - min(recent_prices) if recent_prices else 1
        if price_range == 0:
            price_range = 1
        
        direction = max(-1.0, min(1.0, slope / (price_range / n) * 10))
        
        # Strength based on R-squared
        ss_tot = sum((p - y_mean) ** 2 for p in recent_prices)
        ss_res = sum((p - (y_mean + slope * (i - x_mean))) ** 2 
                     for i, p in enumerate(recent_prices))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        strength = max(0.0, min(1.0, r_squared))
        
        return direction, strength
    
    def _compute_liquidity_score(self, volume: float, price: float) -> float:
        """
        Compute liquidity score based on volume.
        Higher volume = better liquidity.
        """
        if volume <= 0 or price <= 0:
            return 0.0
        
        # Volume in USD terms
        volume_usd = volume
        
        # Score based on volume thresholds
        # $1B+ daily volume = 1.0, $100M = 0.8, $10M = 0.5, $1M = 0.3
        if volume_usd >= 1_000_000_000:
            return 1.0
        elif volume_usd >= 100_000_000:
            return 0.8
        elif volume_usd >= 10_000_000:
            return 0.5
        elif volume_usd >= 1_000_000:
            return 0.3
        else:
            return 0.1
    
    def _compute_anomaly_score(self, asset: str, price: float, 
                               volume: float, price_change_24h: float) -> float:
        """
        Detect anomalies in market data.
        High score = potential manipulation or unusual activity.
        """
        anomaly_factors = []
        
        # Extreme price change
        if abs(price_change_24h) > 20:
            anomaly_factors.append(0.8)
        elif abs(price_change_24h) > 10:
            anomaly_factors.append(0.5)
        elif abs(price_change_24h) > 5:
            anomaly_factors.append(0.2)
        
        # Price deviation from recent history
        history = self.price_history.get(asset, [])
        if len(history) >= 10:
            recent_prices = [p for _, p in history[-10:]]
            avg_price = sum(recent_prices) / len(recent_prices)
            if avg_price > 0:
                deviation = abs(price - avg_price) / avg_price
                if deviation > 0.1:
                    anomaly_factors.append(min(deviation * 5, 1.0))
        
        return max(anomaly_factors) if anomaly_factors else 0.0
    
    def classify_regime(self, signal: MarketSignal) -> MarketRegime:
        """
        Classify current market regime based on signal.
        
        Returns:
            MarketRegime enum value
        """
        thresholds = config.policy_thresholds
        
        # Crisis conditions (EMERGENCY)
        if (signal.volatility >= thresholds.volatility_crisis_threshold or
            signal.anomaly_score >= thresholds.anomaly_score_max):
            return MarketRegime.EMERGENCY
        
        # Volatile conditions (RISK_OFF)
        if signal.volatility >= thresholds.volatility_volatile_max:
            return MarketRegime.RISK_OFF
        
        # Normal conditions (RISK_ON)
        if signal.volatility <= thresholds.volatility_normal_max:
            return MarketRegime.RISK_ON
        
        return MarketRegime.NEUTRAL
    
    def generate_mock_signal(self, asset: str, base_price: float) -> MarketSignal:
        """
        Generate mock market signal for simulation.
        
        Args:
            asset: Asset symbol
            base_price: Base price to generate around
        
        Returns:
            MarketSignal with simulated values
        """
        # Add random walk to price
        volatility_factor = config.simulation.mock_market_volatility
        price_change = base_price * random.gauss(0, volatility_factor)
        new_price = max(base_price + price_change, base_price * 0.5)  # Floor at 50%
        
        # Generate realistic volume
        volume = random.uniform(50_000_000, 500_000_000)
        
        # 24h change
        price_change_24h = random.gauss(0, 3)  # Typically -3% to +3%
        
        return self.process_market_data(
            asset=asset,
            price=new_price,
            volume=volume,
            price_change_24h=price_change_24h
        )


# Global signal engine instance
signal_engine = SignalEngine()
