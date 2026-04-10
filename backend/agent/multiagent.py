"""
Sentinel-01 Multi-Agent Integration Layer
AETHEL Finance Lab - CLAW Ecosystem & Agent Network Integration

This module provides integration with:
- CLAW Ecosystem (OpenClaw, ClawHub skills)
- Agent-to-Agent Protocol (A2A) for multi-agent coordination
- Model Context Protocol (MCP) for tool integration
- ERC-8004 Agent Network for on-chain identity
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import asyncio
import logging

logger = logging.getLogger("sentinel-01.multiagent")


class AgentCapability(Enum):
    """Sentinel-01 advertised capabilities"""
    RISK_ASSESSMENT = "risk_assessment"
    REGIME_CLASSIFICATION = "regime_classification"
    TRADE_VALIDATION = "trade_validation"
    PORTFOLIO_MONITORING = "portfolio_monitoring"
    EMERGENCY_RESPONSE = "emergency_response"
    MARKET_SIGNAL_GENERATION = "market_signal_generation"
    GOVERNANCE_VOTING = "governance_voting"


class ProtocolType(Enum):
    """Supported communication protocols"""
    MCP = "mcp"          # Model Context Protocol
    A2A = "a2a"          # Agent-to-Agent Protocol
    ERC8004 = "erc8004"  # On-chain identity
    CLAW = "claw"        # CLAW ecosystem


@dataclass
class AgentCard:
    """
    ERC-8004 Agent Card - Sentinel-01's on-chain identity.
    
    This is what other agents see when they discover Sentinel-01.
    """
    agent_id: str
    name: str
    description: str
    version: str
    organization: str
    
    # ERC-8004 Identity
    chain_id: int = 8453  # Base
    identity_registry: str = ""  # Contract address
    agent_nft_id: Optional[int] = None
    
    # Capabilities
    capabilities: List[AgentCapability] = field(default_factory=list)
    
    # Endpoints
    endpoints: Dict[str, str] = field(default_factory=dict)
    
    # Policy
    policy_hash: str = ""
    risk_limits_hash: str = ""
    
    # Reputation
    reputation_score: float = 100.0
    total_validations: int = 0
    successful_validations: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_erc8004_uri(self) -> Dict:
        """Generate ERC-8004 compliant agent card URI"""
        return {
            "$schema": "https://eips.ethereum.org/EIPS/eip-8004#agent-card",
            "agentId": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "organization": self.organization,
            "chainId": self.chain_id,
            "capabilities": [c.value for c in self.capabilities],
            "endpoints": {
                "a2a": self.endpoints.get("a2a", ""),
                "mcp": self.endpoints.get("mcp", ""),
                "api": self.endpoints.get("api", ""),
            },
            "policy": {
                "policyHash": self.policy_hash,
                "riskLimitsHash": self.risk_limits_hash,
            },
            "reputation": {
                "score": self.reputation_score,
                "totalValidations": self.total_validations,
                "successRate": (self.successful_validations / max(self.total_validations, 1)) * 100,
            },
            "metadata": {
                "createdAt": self.created_at.isoformat(),
                "updatedAt": self.updated_at.isoformat(),
            }
        }


@dataclass
class AgentMessage:
    """Message structure for A2A communication"""
    message_id: str
    sender_id: str
    receiver_id: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "messageId": self.message_id,
            "senderId": self.sender_id,
            "receiverId": self.receiver_id,
            "messageType": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "signature": self.signature,
        }


@dataclass
class MCPTool:
    """MCP Tool Definition for Sentinel-01"""
    name: str
    description: str
    input_schema: Dict
    handler: Optional[Callable] = None
    
    def to_mcp_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class MultiAgentHub:
    """
    Multi-Agent Integration Hub for Sentinel-01.
    
    Enables:
    1. ERC-8004 identity registration and discovery
    2. A2A communication with other agents
    3. MCP tool exposure for LLM integration
    4. CLAW ecosystem skill publishing
    """
    
    def __init__(self, agent_config):
        self.config = agent_config
        self._agent_card = self._create_agent_card()
        self._registered_tools: Dict[str, MCPTool] = {}
        self._connected_agents: Dict[str, AgentCard] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._message_queue: List[AgentMessage] = []
        
        # Register default tools
        self._register_default_tools()
    
    def _create_agent_card(self) -> AgentCard:
        """Create Sentinel-01's agent card"""
        from .config import config
        
        return AgentCard(
            agent_id=config.identity.agent_id,
            name="Sentinel-01",
            description="Risk-first capital protection agent with constitutional governance",
            version=config.identity.version,
            organization=config.identity.organization,
            capabilities=[
                AgentCapability.RISK_ASSESSMENT,
                AgentCapability.REGIME_CLASSIFICATION,
                AgentCapability.TRADE_VALIDATION,
                AgentCapability.PORTFOLIO_MONITORING,
                AgentCapability.EMERGENCY_RESPONSE,
                AgentCapability.MARKET_SIGNAL_GENERATION,
                AgentCapability.GOVERNANCE_VOTING,
            ],
            policy_hash=config.identity.policy_hash,
            endpoints={
                "api": "/api",
                "a2a": "/api/a2a",
                "mcp": "/api/mcp",
            }
        )
    
    def _register_default_tools(self):
        """Register Sentinel-01's MCP tools"""
        
        # Risk Assessment Tool
        self.register_tool(MCPTool(
            name="assess_trade_risk",
            description="Assess risk for a proposed trade. Returns risk score and approval status.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
                    "asset": {"type": "string"},
                    "amount": {"type": "number"},
                    "price": {"type": "number"},
                },
                "required": ["action", "asset", "amount"]
            }
        ))
        
        # Regime Classification Tool
        self.register_tool(MCPTool(
            name="classify_market_regime",
            description="Classify current market regime based on volatility and signals.",
            input_schema={
                "type": "object",
                "properties": {
                    "asset": {"type": "string"},
                    "volatility": {"type": "number"},
                    "price_change_24h": {"type": "number"},
                },
                "required": ["asset"]
            }
        ))
        
        # Portfolio State Tool
        self.register_tool(MCPTool(
            name="get_portfolio_state",
            description="Get current portfolio state including positions, cash, and drawdown.",
            input_schema={
                "type": "object",
                "properties": {},
            }
        ))
        
        # Risk Limits Tool
        self.register_tool(MCPTool(
            name="get_risk_limits",
            description="Get constitutional risk limits that govern agent behavior.",
            input_schema={
                "type": "object",
                "properties": {},
            }
        ))
        
        # Validation Artifact Tool
        self.register_tool(MCPTool(
            name="get_validation_artifacts",
            description="Get recent validation artifacts for audit trail.",
            input_schema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "default": 10},
                },
            }
        ))
        
        # Emergency Status Tool
        self.register_tool(MCPTool(
            name="get_emergency_status",
            description="Get emergency protocol status.",
            input_schema={
                "type": "object",
                "properties": {},
            }
        ))
    
    def register_tool(self, tool: MCPTool):
        """Register an MCP tool"""
        self._registered_tools[tool.name] = tool
        logger.info(f"Registered MCP tool: {tool.name}")
    
    def get_mcp_manifest(self) -> Dict:
        """Get MCP server manifest"""
        return {
            "name": "sentinel-01-mcp",
            "version": self._agent_card.version,
            "description": self._agent_card.description,
            "tools": [tool.to_mcp_schema() for tool in self._registered_tools.values()],
            "resources": [],
            "prompts": [
                {
                    "name": "risk_assessment_prompt",
                    "description": "Prompt for risk assessment workflow",
                    "arguments": [
                        {"name": "trade_details", "required": True}
                    ]
                }
            ]
        }
    
    def get_agent_card(self) -> Dict:
        """Get agent card for discovery"""
        return self._agent_card.to_erc8004_uri()
    
    async def handle_a2a_message(self, message: AgentMessage) -> Dict:
        """
        Handle incoming A2A message from another agent.
        
        Supported message types:
        - discover: Return agent capabilities
        - request_risk_assessment: Assess trade risk
        - request_regime: Get current regime
        - request_validation: Validate a trade intent
        - governance_vote_request: Request governance vote
        """
        message_type = message.message_type
        
        if message_type == "discover":
            return {
                "type": "discovery_response",
                "agent_card": self.get_agent_card(),
            }
        
        elif message_type == "request_risk_assessment":
            from .risk_engine import risk_engine
            from .signal_engine import signal_engine
            
            payload = message.payload
            asset = payload.get("asset", "ETH")
            
            # Get current signal
            signal = signal_engine.generate_mock_signal(asset, payload.get("price", 2500))
            
            # Assess risk
            from .config import ActionType
            action = ActionType(payload.get("action", "hold"))
            assessment = risk_engine.assess_trade(
                action=action,
                asset=asset,
                amount=payload.get("amount", 0),
                signal=signal
            )
            
            return {
                "type": "risk_assessment_response",
                "approved": assessment.approved,
                "risk_score": assessment.risk_score,
                "checks": [c.to_dict() for c in assessment.checks],
                "rejection_reasons": assessment.rejection_reasons,
            }
        
        elif message_type == "request_regime":
            from .policy_engine import policy_engine
            
            return {
                "type": "regime_response",
                "regime": policy_engine.get_current_regime().value,
                "summary": policy_engine.get_regime_summary(),
            }
        
        elif message_type == "request_validation":
            from .reputation_tracker import reputation_tracker
            
            return {
                "type": "validation_response",
                "recent_artifacts": reputation_tracker.get_recent_artifacts(5),
                "metrics": reputation_tracker.get_metrics().to_dict(),
            }
        
        else:
            return {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
            }
    
    def create_outgoing_message(self, receiver_id: str, message_type: str, 
                                 payload: Dict) -> AgentMessage:
        """Create an outgoing A2A message"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=self._agent_card.agent_id,
            receiver_id=receiver_id,
            message_type=message_type,
            payload=payload,
        )
        
        # Sign message (placeholder for real signing)
        message.signature = f"SIG_{hashlib.sha256(json.dumps(message.to_dict(), sort_keys=True).encode()).hexdigest()[:16]}"
        
        return message
    
    async def discover_agent(self, agent_uri: str) -> Optional[AgentCard]:
        """
        Discover another agent via ERC-8004 registry or direct URI.
        
        TODO: Implement real discovery via:
        - ERC-8004 Identity Registry contract
        - ENS resolution
        - Direct API call
        """
        logger.info(f"Discovering agent: {agent_uri}")
        # Placeholder for real discovery
        return None
    
    def get_claw_skill_manifest(self) -> Dict:
        """
        Generate ClawHub skill manifest for CLAW ecosystem integration.
        
        This allows Sentinel-01 to be discovered and used by CLAW agents.
        """
        return {
            "skill_id": "sentinel-01-risk-engine",
            "name": "Sentinel-01 Risk Engine",
            "description": "Constitutional risk assessment for DeFi trading",
            "version": self._agent_card.version,
            "author": "AETHEL Finance Lab",
            "category": "defi/risk-management",
            "tags": ["risk", "defi", "trading", "capital-protection", "erc-8004"],
            "endpoints": {
                "assess_risk": "/api/risk/assess",
                "get_limits": "/api/risk/limits",
                "get_regime": "/api/policy/current",
            },
            "schema": {
                "input": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "asset": {"type": "string"},
                        "amount": {"type": "number"},
                    }
                },
                "output": {
                    "type": "object",
                    "properties": {
                        "approved": {"type": "boolean"},
                        "risk_score": {"type": "number"},
                        "regime": {"type": "string"},
                    }
                }
            },
            "pricing": {
                "model": "free",  # or "per-call", "subscription"
            },
            "trust": {
                "erc8004_registered": True,
                "policy_hash": self._agent_card.policy_hash,
                "governance_controlled": True,
            }
        }
    
    def get_integration_status(self) -> Dict:
        """Get multi-agent integration status"""
        return {
            "agent_id": self._agent_card.agent_id,
            "protocols": {
                "mcp": {
                    "enabled": True,
                    "tools_count": len(self._registered_tools),
                    "tools": list(self._registered_tools.keys()),
                },
                "a2a": {
                    "enabled": True,
                    "connected_agents": len(self._connected_agents),
                },
                "erc8004": {
                    "enabled": True,
                    "chain_id": self._agent_card.chain_id,
                    "registered": self._agent_card.agent_nft_id is not None,
                },
                "claw": {
                    "enabled": True,
                    "skill_published": False,  # TODO: Track actual publication
                },
            },
            "capabilities": [c.value for c in self._agent_card.capabilities],
            "policy_hash": self._agent_card.policy_hash,
        }


# Global multi-agent hub instance
multiagent_hub = None

def get_multiagent_hub():
    """Get or create multi-agent hub"""
    global multiagent_hub
    if multiagent_hub is None:
        from .config import config
        multiagent_hub = MultiAgentHub(config)
    return multiagent_hub
