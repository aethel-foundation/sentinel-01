"""
Sentinel-01 API Server
AETHEL Foundation - FastAPI Backend

Main API server for Sentinel-01 dashboard and external integrations.
Provides endpoints for:
- Agent status and control
- Market data
- Governance
- Validation artifacts
- Emergency protocol
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import Sentinel-01 modules
from agent.config import config, MarketRegime, ActionType
from agent.main import agent, Sentinel01Agent
from agent.signal_engine import signal_engine
from agent.risk_engine import risk_engine
from agent.policy_engine import policy_engine
from agent.executor import executor
from agent.reputation_tracker import reputation_tracker
from governance.governance import governance, ProposalType, VoteType
from governance.emergency_protocol import emergency_protocol, EmergencyLevel, EmergencyType
from adapters.market_data import coingecko_adapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel-01.api")

# MongoDB connection (optional — falls back to in-memory if not configured)
mongo_url = os.environ.get('MONGO_URL', '')
db_name = os.environ.get('DB_NAME', 'sentinel_01')
db = None
client = None

if mongo_url:
    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        logger.info("MongoDB connected")
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}. Running in-memory only.")
else:
    logger.info("No MONGO_URL set. Running in-memory only (demo mode).")

# FastAPI app
app = FastAPI(
    title="Sentinel-01 API",
    description="AETHEL Foundation - ERC-8004 Capital Protection Agent",
    version="0.1.0"
)

api_router = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Pydantic Models ==============

class AgentStatus(BaseModel):
    agent_id: str
    version: str
    policy_hash: str
    running: bool
    cycle_count: int
    simulation_mode: bool
    current_regime: str
    portfolio: Optional[Dict[str, Any]]
    metrics: Dict[str, Any]

class MarketDataResponse(BaseModel):
    asset: str
    price: float
    volume_24h: float
    price_change_24h: float
    market_cap: float
    timestamp: str
    source: str

class CycleResult(BaseModel):
    artifact_id: str
    timestamp: str
    regime: str
    action_taken: str
    portfolio_value: float

class ProposalCreate(BaseModel):
    proposal_type: str
    title: str
    description: str
    proposer_id: str
    parameters: Dict[str, Any]

class VoteCreate(BaseModel):
    voter_id: str
    vote_type: str
    reason: Optional[str] = ""

class EmergencyTrigger(BaseModel):
    emergency_type: str
    level: str
    triggered_by: str
    reason: str

# ============== Agent Endpoints ==============

@api_router.get("/")
async def root():
    return {
        "name": "Sentinel-01",
        "organization": "AETHEL Foundation",
        "version": config.identity.version,
        "status": "operational"
    }

@api_router.get("/agent/status", response_model=AgentStatus)
async def get_agent_status():
    """Get current agent status"""
    status = agent.get_status()
    return AgentStatus(**status)

@api_router.get("/agent/config")
async def get_agent_config():
    """Get agent configuration"""
    return config.to_dict()

@api_router.post("/agent/start")
async def start_agent(background_tasks: BackgroundTasks, cycles: Optional[int] = None):
    """Start the agent"""
    if agent._running:
        raise HTTPException(status_code=400, detail="Agent is already running")
    
    # Connect market data source
    agent.set_market_data_source(coingecko_adapter)
    
    # Start in background
    background_tasks.add_task(agent.run, cycles, 5)
    
    return {"status": "started", "cycles": cycles or "infinite"}

@api_router.post("/agent/stop")
async def stop_agent():
    """Stop the agent"""
    agent.stop()
    return {"status": "stopped"}

@api_router.post("/agent/cycle")
async def run_single_cycle(asset: str = "ETH"):
    """Run a single decision cycle"""
    if not agent._running:
        # Connect market data if needed
        if not agent._market_data_source:
            agent.set_market_data_source(coingecko_adapter)
    
    artifact = await agent.run_cycle(asset)

    # Persist to MongoDB if available
    if db is not None:
        try:
            await db.validation_artifacts.insert_one(artifact.to_dict())
        except Exception as e:
            logger.warning(f"DB write skipped: {e}")

    return {
        "artifact_id": artifact.artifact_id,
        "timestamp": artifact.timestamp.isoformat(),
        "regime": artifact.regime.value,
        "action_taken": artifact.action_taken.value,
        "artifact_hash": artifact.artifact_hash,
    }

# ============== Market Data Endpoints ==============

@api_router.get("/market/price/{asset}")
async def get_market_price(asset: str):
    """Get current price for an asset"""
    data = await coingecko_adapter.get_price(asset)
    return data

@api_router.get("/market/prices")
async def get_multiple_prices(assets: str = "ETH,BTC"):
    """Get prices for multiple assets (comma-separated)"""
    asset_list = [a.strip() for a in assets.split(",")]
    data = await coingecko_adapter.get_multiple_prices(asset_list)
    return data

@api_router.get("/market/historical/{asset}")
async def get_historical_data(asset: str, days: int = 30):
    """Get historical price data"""
    data = await coingecko_adapter.get_historical(asset, days)
    return data

@api_router.get("/market/signal/{asset}")
async def get_market_signal(asset: str):
    """Get processed market signal for an asset"""
    # Fetch real data
    market_data = await coingecko_adapter.get_price(asset)
    
    # Process through signal engine
    signal = signal_engine.process_market_data(
        asset=asset,
        price=market_data.get("price", 0),
        volume=market_data.get("volume_24h", 0),
        price_change_24h=market_data.get("price_change_24h", 0)
    )
    
    # Classify regime
    regime = signal_engine.classify_regime(signal)
    
    return {
        "signal": signal.to_dict(),
        "regime": regime.value,
    }

# ============== Risk & Policy Endpoints ==============

@api_router.get("/risk/limits")
async def get_risk_limits():
    """Get current risk limits"""
    return {
        "max_drawdown_pct": config.risk_limits.max_drawdown_pct,
        "max_single_trade_pct": config.risk_limits.max_single_trade_pct,
        "max_daily_loss_pct": config.risk_limits.max_daily_loss_pct,
        "max_position_pct": config.risk_limits.max_position_pct,
        "min_liquidity_ratio": config.risk_limits.min_liquidity_ratio,
        "max_leverage": config.risk_limits.max_leverage,
        "stop_loss_pct": config.risk_limits.stop_loss_pct,
    }

@api_router.get("/policy/summary")
async def get_policy_summary():
    """Get policy engine summary"""
    return policy_engine.get_regime_summary()

@api_router.get("/policy/current")
async def get_current_policy(asset: str = "ETH"):
    """Get current policy based on market conditions"""
    market_data = await coingecko_adapter.get_price(asset)
    
    signal = signal_engine.process_market_data(
        asset=asset,
        price=market_data.get("price", 0),
        volume=market_data.get("volume_24h", 0),
        price_change_24h=market_data.get("price_change_24h", 0)
    )
    
    policy = policy_engine.get_policy(signal)
    return policy.to_dict()

# ============== Portfolio Endpoints ==============

@api_router.get("/portfolio/state")
async def get_portfolio_state():
    """Get current portfolio state"""
    portfolio = risk_engine.get_portfolio_state()
    if not portfolio:
        return {"error": "Portfolio not initialized"}
    return portfolio.to_dict()

@api_router.get("/portfolio/history")
async def get_execution_history():
    """Get trade execution history"""
    return executor.get_execution_history()

# ============== Validation Artifacts Endpoints ==============

@api_router.get("/artifacts/recent")
async def get_recent_artifacts(count: int = 10):
    """Get recent validation artifacts"""
    return reputation_tracker.get_recent_artifacts(count)

@api_router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Get specific artifact by ID"""
    artifact = reputation_tracker.get_artifact_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact

@api_router.get("/artifacts/summary")
async def get_artifacts_summary():
    """Get summary of all cycles and artifacts"""
    return reputation_tracker.get_cycle_summary()

# ============== Reputation Metrics Endpoints ==============

@api_router.get("/reputation/metrics")
async def get_reputation_metrics():
    """Get agent reputation metrics"""
    return reputation_tracker.get_metrics().to_dict()

# ============== Governance Endpoints ==============

@api_router.get("/governance/status")
async def get_governance_status():
    """Get governance system status"""
    return governance.get_governance_status()

@api_router.get("/governance/members")
async def get_governance_members():
    """Get all governance members"""
    return [m.to_dict() for m in governance.get_active_members()]

@api_router.get("/governance/proposals")
async def get_proposals(active_only: bool = False):
    """Get governance proposals"""
    if active_only:
        return governance.get_active_proposals()
    return governance.get_all_proposals()

@api_router.get("/governance/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    """Get specific proposal"""
    proposal = governance.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal

@api_router.post("/governance/proposals")
async def create_proposal(proposal: ProposalCreate):
    """Create a new governance proposal"""
    try:
        proposal_type = ProposalType(proposal.proposal_type)
        created = governance.create_proposal(
            proposal_type=proposal_type,
            title=proposal.title,
            description=proposal.description,
            proposer_id=proposal.proposer_id,
            parameters=proposal.parameters,
        )
        
        # Persist to MongoDB if available
        if db is not None:
            try:
                await db.proposals.insert_one(created.to_dict())
            except Exception as e:
                logger.warning(f"DB write skipped: {e}")

        return created.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/governance/proposals/{proposal_id}/vote")
async def vote_on_proposal(proposal_id: str, vote: VoteCreate):
    """Vote on a proposal"""
    try:
        vote_type = VoteType(vote.vote_type)
        governance.vote(
            proposal_id=proposal_id,
            voter_id=vote.voter_id,
            vote_type=vote_type,
            reason=vote.reason or "",
        )
        return {"status": "vote recorded"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/governance/proposals/{proposal_id}/execute")
async def execute_proposal(proposal_id: str):
    """Execute a passed proposal"""
    try:
        result = governance.execute_proposal(proposal_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============== Emergency Protocol Endpoints ==============

@api_router.get("/emergency/status")
async def get_emergency_status():
    """Get emergency protocol status"""
    return emergency_protocol.get_status()

@api_router.get("/emergency/history")
async def get_emergency_history():
    """Get emergency event history"""
    return emergency_protocol.get_event_history()

@api_router.post("/emergency/trigger")
async def trigger_emergency(trigger: EmergencyTrigger):
    """Manually trigger an emergency"""
    try:
        emergency_type = EmergencyType(trigger.emergency_type)
        level = EmergencyLevel(trigger.level)
        
        event = emergency_protocol.trigger_manual_emergency(
            emergency_type=emergency_type,
            level=level,
            triggered_by=trigger.triggered_by,
            reason=trigger.reason,
        )
        return event.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/emergency/pause")
async def pause_trading():
    """Pause all trading"""
    emergency_protocol.pause_trading()
    return {"status": "trading paused"}

@api_router.post("/emergency/resume")
async def resume_trading():
    """Resume trading"""
    emergency_protocol.resume_trading()
    return {"status": "trading resumed"}

@api_router.post("/emergency/close-all")
async def close_all_positions():
    """Emergency: Close all positions"""
    result = emergency_protocol.close_all_positions()
    return result

@api_router.post("/emergency/resolve/{event_id}")
async def resolve_emergency(event_id: str, notes: str = ""):
    """Resolve an emergency event"""
    success = emergency_protocol.resolve_emergency(event_id, notes)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found or already resolved")
    return {"status": "resolved"}

# Include router
app.include_router(api_router)

@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    logger.info("Sentinel-01 API starting...")
    logger.info(f"Policy Hash: {config.identity.policy_hash[:16]}...")

    # Create indexes only if MongoDB is available
    if db is not None:
        try:
            await db.validation_artifacts.create_index("artifact_id")
            await db.validation_artifacts.create_index("timestamp")
            await db.proposals.create_index("proposal_id")
        except Exception as e:
            logger.warning(f"DB index creation skipped: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    agent.stop()
    if client:
        client.close()
    logger.info("Sentinel-01 API stopped")
