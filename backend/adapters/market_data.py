"""
Sentinel-01 Market Data Adapter
AETHEL Foundation - External Data Integration

This adapter connects Sentinel-01 to external market data sources.
Currently supports CoinGecko API for real price data.
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger("sentinel-01.adapter")


@dataclass
class MarketData:
    """Standardized market data format"""
    asset: str
    price: float
    volume_24h: float
    price_change_24h: float
    market_cap: float
    timestamp: datetime
    source: str
    
    def to_dict(self) -> Dict:
        return {
            "asset": self.asset,
            "price": self.price,
            "volume_24h": self.volume_24h,
            "price_change_24h": self.price_change_24h,
            "market_cap": self.market_cap,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


class CoinGeckoAdapter:
    """
    CoinGecko API adapter for market data.
    
    Maps common asset symbols to CoinGecko IDs.
    Implements caching and rate limiting.
    """
    
    # Asset symbol to CoinGecko ID mapping
    ASSET_MAP = {
        "ETH": "ethereum",
        "BTC": "bitcoin",
        "USDT": "tether",
        "USDC": "usd-coin",
        "SOL": "solana",
        "MATIC": "matic-network",
        "LINK": "chainlink",
        "UNI": "uniswap",
        "AAVE": "aave",
    }
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("COINGECKO_API_KEY")
        self._cache: Dict[str, MarketData] = {}
        self._cache_ttl_seconds = 30  # Cache for 30 seconds
        self._last_request_time: Dict[str, datetime] = {}
        self._rate_limit_delay = 1.5  # Seconds between requests (free tier)
    
    def _get_coingecko_id(self, asset: str) -> str:
        """Convert asset symbol to CoinGecko ID"""
        return self.ASSET_MAP.get(asset.upper(), asset.lower())
    
    async def get_price(self, asset: str) -> Dict:
        """
        Get current price for an asset.
        
        Args:
            asset: Asset symbol (e.g., "ETH", "BTC")
        
        Returns:
            Dict with price data
        """
        # Check cache
        cached = self._get_cached(asset)
        if cached:
            return cached.to_dict()
        
        # Rate limiting
        await self._rate_limit()
        
        coin_id = self._get_coingecko_id(asset)
        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        }
        
        headers = {}
        if self._api_key:
            headers["x-cg-demo-api-key"] = self._api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if coin_id in data:
                            coin_data = data[coin_id]
                            market_data = MarketData(
                                asset=asset.upper(),
                                price=coin_data.get("usd", 0),
                                volume_24h=coin_data.get("usd_24h_vol", 0),
                                price_change_24h=coin_data.get("usd_24h_change", 0),
                                market_cap=coin_data.get("usd_market_cap", 0),
                                timestamp=datetime.now(timezone.utc),
                                source="coingecko",
                            )
                            
                            # Update cache
                            self._cache[asset.upper()] = market_data
                            
                            return market_data.to_dict()
                    
                    logger.warning(f"CoinGecko API error: {response.status}")
                    return self._get_fallback(asset)
                    
        except Exception as e:
            logger.error(f"CoinGecko request failed: {e}")
            return self._get_fallback(asset)
    
    async def get_multiple_prices(self, assets: List[str]) -> Dict[str, Dict]:
        """
        Get prices for multiple assets in one request.
        
        Args:
            assets: List of asset symbols
        
        Returns:
            Dict mapping asset to price data
        """
        # Rate limiting
        await self._rate_limit()
        
        coin_ids = [self._get_coingecko_id(a) for a in assets]
        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        }
        
        headers = {}
        if self._api_key:
            headers["x-cg-demo-api-key"] = self._api_key
        
        results = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for asset in assets:
                            coin_id = self._get_coingecko_id(asset)
                            if coin_id in data:
                                coin_data = data[coin_id]
                                market_data = MarketData(
                                    asset=asset.upper(),
                                    price=coin_data.get("usd", 0),
                                    volume_24h=coin_data.get("usd_24h_vol", 0),
                                    price_change_24h=coin_data.get("usd_24h_change", 0),
                                    market_cap=coin_data.get("usd_market_cap", 0),
                                    timestamp=datetime.now(timezone.utc),
                                    source="coingecko",
                                )
                                self._cache[asset.upper()] = market_data
                                results[asset.upper()] = market_data.to_dict()
                            else:
                                results[asset.upper()] = self._get_fallback(asset)
                    else:
                        logger.warning(f"CoinGecko API error: {response.status}")
                        for asset in assets:
                            results[asset.upper()] = self._get_fallback(asset)
                            
        except Exception as e:
            logger.error(f"CoinGecko request failed: {e}")
            for asset in assets:
                results[asset.upper()] = self._get_fallback(asset)
        
        return results
    
    async def get_historical(self, asset: str, days: int = 30) -> Dict:
        """
        Get historical price data.
        
        Args:
            asset: Asset symbol
            days: Number of days of history
        
        Returns:
            Dict with historical data
        """
        await self._rate_limit()
        
        coin_id = self._get_coingecko_id(asset)
        url = f"{self.BASE_URL}/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
        }
        
        headers = {}
        if self._api_key:
            headers["x-cg-demo-api-key"] = self._api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "asset": asset.upper(),
                            "days": days,
                            "prices": data.get("prices", []),
                            "volumes": data.get("total_volumes", []),
                            "market_caps": data.get("market_caps", []),
                            "source": "coingecko",
                        }
                    
                    return {"error": f"API error: {response.status}"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    def _get_cached(self, asset: str) -> Optional[MarketData]:
        """Get cached data if still valid"""
        cached = self._cache.get(asset.upper())
        if cached:
            age = (datetime.now(timezone.utc) - cached.timestamp).total_seconds()
            if age < self._cache_ttl_seconds:
                return cached
        return None
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        now = datetime.now(timezone.utc)
        last = self._last_request_time.get("global")
        
        if last:
            elapsed = (now - last).total_seconds()
            if elapsed < self._rate_limit_delay:
                await asyncio.sleep(self._rate_limit_delay - elapsed)
        
        self._last_request_time["global"] = datetime.now(timezone.utc)
    
    def _get_fallback(self, asset: str) -> Dict:
        """Get fallback data when API fails"""
        # Return cached data even if stale
        cached = self._cache.get(asset.upper())
        if cached:
            return cached.to_dict()
        
        # Return placeholder
        return {
            "asset": asset.upper(),
            "price": 0,
            "volume_24h": 0,
            "price_change_24h": 0,
            "market_cap": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "fallback",
            "error": "No data available",
        }


# Global adapter instance
coingecko_adapter = CoinGeckoAdapter()
