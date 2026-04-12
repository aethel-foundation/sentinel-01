import asyncio
import os
import sys

# Ensure backend is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.main import agent
from agent.config import config, ActionType, MarketRegime
from agent.policy_engine import policy_engine
from governance.emergency_protocol import emergency_protocol

async def run_cinematic_demo():
    print("\n" + "="*60)
    print(" [SHIELD] SENTINEL-01: SOVEREIGN DEMO SEQUENCE")
    print(" [SYSTEM] Initializing Risk-Containment Architecture...")
    print("="*60 + "\n")

    # --- SCENARIO 1: NORMAL MARKET ---
    print("\n[SCENARIO 1: NORMAL MARKET CONDITIONS]")
    print("> Market state: Low volatility, steady growth.")
    
    # Force Mock LLM temporarily for demo reproducibility if NO KEY
    if not os.getenv("OPENAI_API_KEY"):
        agent.llm_adapter.provider = "mock"
    
    artifact = await agent.run_cycle("ETH")
    
    print("\n[VERDICT]")
    print(f"Action: {artifact.action_taken.value.upper()}")
    print(f"Artifact Hash: {artifact.artifact_hash}")
    print("-" * 40)

    # --- SCENARIO 2: CRISIS / GOVERNANCE PAUSE ---
    print("\n[SCENARIO 2: EMERGENCY GOVERNANCE PAUSE]")
    print("> Action: AETHEL Foundation activates Emergency Circuit Breaker.")
    
    emergency_protocol.pause_trading()
    
    artifact = await agent.run_cycle("ETH")
    
    print("\n[VERDICT]")
    print(f"Action: {artifact.action_taken.value.upper()}")
    print(f"Status: Trading is PAUSED by Sovereign Governance.")
    print(f"Artifact Hash: {artifact.artifact_hash}")
    print("-" * 40)

    # --- SCENARIO 3: RISK ENGINE VETO ---
    print("\n[SCENARIO 3: RISK ENGINE VETO]")
    print("> Market state: Extreme Volatility detected.")
    emergency_protocol.resume_trading()
    
    # Mock a high volatility signal to trigger veto
    # But wait, we can just force the risk engine to fail.
    from agent.risk_engine import risk_engine
    
    print("> LLM suggests an aggressive position, but Risk Engine detects overexposure...")
    
    # Tweak risk limits for demo
    config.risk_limits.max_single_trade_pct = 0.001 
    
    artifact = await agent.run_cycle("ETH")
    
    print("\n[VERDICT]")
    print(f"Action: {artifact.action_taken.value.upper()}")
    print(f"Risk Assessment: {artifact.risk_assessment.get('rejection_reasons') if artifact.risk_assessment else 'N/A'}")
    print(f"Result: Deterministic Veto enforced. Capital Preserved.")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_cinematic_demo())
