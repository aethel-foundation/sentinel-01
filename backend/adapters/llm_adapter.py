import os
import json
import logging
from typing import Dict, Any, Optional
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_adapter")

class LLMAdapter:
    """
    Sovereign Cognitive Adapter for Sentinel-01.
    Connects the deterministic risk engine to a reasoning LLM core.
    """
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "mock").lower()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def get_trade_decision(self, market_data: Dict[str, Any], risk_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submits market context to the LLM and requests a structured trade intent.
        """
        logger.info(f"Requesting trade decision from LLM provider: {self.provider}")
        
        prompt = self._build_prompt(market_data, risk_profile)
        
        if self.provider == "openai" and self.api_key:
            return self._call_openai(prompt)
        elif self.provider == "ollama":
            return self._call_ollama(prompt)
        else:
            return self._mock_decision(market_data)

    def _build_prompt(self, market_data: Dict[str, Any], risk_profile: Dict[str, Any]) -> str:
        return f"""
YOU ARE SENTINEL-01, a Sovereign Capital Protection Agent for AETHEL Foundation.
Your mission is to analyze market signals and propose a trade intent.

MARKET CONTEXT:
- Asset: {market_data.get('asset', 'ETH')}
- Current Price: ${market_data.get('price')}
- Regime: {market_data.get('regime')}
- RSI: {market_data.get('rsi')}
- Volatility: {market_data.get('volatility')}

RISK PROFILE:
- Max Drawdown: {risk_profile.get('max_drawdown')}%
- Max Position Size: {risk_profile.get('max_pos_size')} ETH

TASK:
Decide whether to BUY, SELL, or HOLD.
Provide a concise reasoning.

OUTPUT FORMAT (STRICT JSON):
{{
  "action": "BUY" | "SELL" | "HOLD",
  "amount": float,
  "reasoning": "string explaining the decision based on signals"
}}
"""

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [{"role": "system", "content": prompt}],
                "response_format": { "type": "json_object" }
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            return json.loads(content)
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            return self._fallback_error("OpenAI failure")

    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        try:
            data = {
                "model": "qwen2.5-coder",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            response = requests.post(f"{self.ollama_url}/api/generate", json=data)
            response.raise_for_status()
            return json.loads(response.json()['response'])
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return self._fallback_error("Ollama failure")

    def _mock_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        # Simulation logic if no LLM is available
        rsi = market_data.get('rsi', 50)
        if rsi < 35:
            return {"action": "BUY", "amount": 0.1, "reasoning": "Market oversold (RSI < 35)."}
        elif rsi > 70:
            return {"action": "SELL", "amount": 0.1, "reasoning": "Market overbought (RSI > 70)."}
        return {"action": "HOLD", "amount": 0.0, "reasoning": "Wait for clearer signal."}

    def _fallback_error(self, message: str) -> Dict[str, Any]:
        return {"action": "HOLD", "amount": 0.0, "reasoning": f"Fallback due to {message}"}
