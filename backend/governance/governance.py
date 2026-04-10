"""
Sentinel-01 Governance
AETHEL Finance Lab - Constitutional Control Layer

This module implements the governance framework that controls Sentinel-01.
The agent CANNOT override governance decisions.

Governance controls:
- Risk parameter changes
- Policy threshold updates
- Agent pause/resume
- Emergency actions
- Member management
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from enum import Enum

import sys
sys.path.append('..')
from agent.config import config


class ProposalType(Enum):
    """Types of governance proposals"""
    PARAMETER_CHANGE = "parameter_change"
    POLICY_UPDATE = "policy_update"
    PAUSE_AGENT = "pause_agent"
    RESUME_AGENT = "resume_agent"
    EMERGENCY_ACTION = "emergency_action"
    ADD_MEMBER = "add_member"
    REMOVE_MEMBER = "remove_member"


class ProposalStatus(Enum):
    """Proposal lifecycle status"""
    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class VoteType(Enum):
    """Vote options"""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


@dataclass
class GovernanceMember:
    """Governance member/voter"""
    member_id: str
    address: str  # Wallet address or identifier
    voting_power: float = 1.0
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "member_id": self.member_id,
            "address": self.address,
            "voting_power": self.voting_power,
            "joined_at": self.joined_at.isoformat(),
            "is_active": self.is_active,
        }


@dataclass
class Vote:
    """Individual vote on a proposal"""
    voter_id: str
    vote_type: VoteType
    voting_power: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "voter_id": self.voter_id,
            "vote_type": self.vote_type.value,
            "voting_power": self.voting_power,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
        }


@dataclass
class Proposal:
    """Governance proposal"""
    proposal_id: str
    proposal_type: ProposalType
    title: str
    description: str
    proposer_id: str
    created_at: datetime
    voting_ends_at: datetime
    execution_delay_hours: int
    
    # Proposal content
    parameters: Dict  # The actual changes being proposed
    
    # Voting state
    status: ProposalStatus = ProposalStatus.PENDING
    votes: List[Vote] = field(default_factory=list)
    votes_for: float = 0.0
    votes_against: float = 0.0
    votes_abstain: float = 0.0
    
    # Execution
    executed_at: Optional[datetime] = None
    execution_result: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type.value,
            "title": self.title,
            "description": self.description,
            "proposer_id": self.proposer_id,
            "created_at": self.created_at.isoformat(),
            "voting_ends_at": self.voting_ends_at.isoformat(),
            "execution_delay_hours": self.execution_delay_hours,
            "parameters": self.parameters,
            "status": self.status.value,
            "votes": [v.to_dict() for v in self.votes],
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "votes_abstain": self.votes_abstain,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "execution_result": self.execution_result,
            "quorum_reached": self.quorum_reached,
            "passed": self.passed,
        }
    
    @property
    def quorum_reached(self) -> bool:
        """Check if quorum is reached"""
        total_votes = self.votes_for + self.votes_against + self.votes_abstain
        return total_votes >= config.governance.quorum_percentage
    
    @property
    def passed(self) -> bool:
        """Check if proposal passed"""
        if not self.quorum_reached:
            return False
        return self.votes_for > self.votes_against


class Governance:
    """
    Constitutional governance layer.
    
    The governance system ensures:
    - All parameter changes go through proposals
    - Quorum requirements are met
    - Execution delays are respected
    - Emergency protocols can override normal flow
    """
    
    def __init__(self):
        self._members: Dict[str, GovernanceMember] = {}
        self._proposals: Dict[str, Proposal] = {}
        self._executed_hashes: Set[str] = set()
        
        # Initialize with default admin member
        self._add_default_admin()
    
    def _add_default_admin(self):
        """Add default admin member"""
        admin = GovernanceMember(
            member_id="admin",
            address="0x0000000000000000000000000000000000000001",
            voting_power=100.0,
        )
        self._members[admin.member_id] = admin
    
    def add_member(self, member_id: str, address: str, voting_power: float = 1.0) -> GovernanceMember:
        """Add a new governance member"""
        member = GovernanceMember(
            member_id=member_id,
            address=address,
            voting_power=voting_power,
        )
        self._members[member_id] = member
        return member
    
    def remove_member(self, member_id: str) -> bool:
        """Remove a governance member"""
        if member_id in self._members:
            self._members[member_id].is_active = False
            return True
        return False
    
    def get_member(self, member_id: str) -> Optional[GovernanceMember]:
        """Get a governance member"""
        return self._members.get(member_id)
    
    def get_active_members(self) -> List[GovernanceMember]:
        """Get all active members"""
        return [m for m in self._members.values() if m.is_active]
    
    def get_total_voting_power(self) -> float:
        """Get total voting power of active members"""
        return sum(m.voting_power for m in self.get_active_members())
    
    def create_proposal(
        self,
        proposal_type: ProposalType,
        title: str,
        description: str,
        proposer_id: str,
        parameters: Dict,
    ) -> Proposal:
        """
        Create a new governance proposal.
        
        Args:
            proposal_type: Type of proposal
            title: Short title
            description: Detailed description
            proposer_id: ID of the proposer
            parameters: Proposal-specific parameters
        
        Returns:
            Created Proposal
        """
        # Verify proposer is an active member
        proposer = self.get_member(proposer_id)
        if not proposer or not proposer.is_active:
            raise ValueError(f"Proposer {proposer_id} is not an active member")
        
        now = datetime.now(timezone.utc)
        
        # Determine execution delay
        execution_delay = config.governance.execution_delay_hours
        if proposal_type == ProposalType.EMERGENCY_ACTION:
            execution_delay = 0  # Emergency actions execute immediately
        
        proposal = Proposal(
            proposal_id=str(uuid.uuid4()),
            proposal_type=proposal_type,
            title=title,
            description=description,
            proposer_id=proposer_id,
            created_at=now,
            voting_ends_at=now + timedelta(hours=config.governance.proposal_duration_hours),
            execution_delay_hours=execution_delay,
            parameters=parameters,
            status=ProposalStatus.ACTIVE,
        )
        
        self._proposals[proposal.proposal_id] = proposal
        return proposal
    
    def vote(self, proposal_id: str, voter_id: str, vote_type: VoteType, 
             reason: str = "") -> bool:
        """
        Cast a vote on a proposal.
        
        Args:
            proposal_id: ID of the proposal
            voter_id: ID of the voter
            vote_type: FOR, AGAINST, or ABSTAIN
            reason: Optional reason for the vote
        
        Returns:
            True if vote was recorded
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if proposal.status != ProposalStatus.ACTIVE:
            raise ValueError(f"Proposal is not active (status: {proposal.status.value})")
        
        # Check voting period
        now = datetime.now(timezone.utc)
        if now > proposal.voting_ends_at:
            proposal.status = ProposalStatus.EXPIRED
            raise ValueError("Voting period has ended")
        
        # Verify voter
        voter = self.get_member(voter_id)
        if not voter or not voter.is_active:
            raise ValueError(f"Voter {voter_id} is not an active member")
        
        # Check if already voted
        for existing_vote in proposal.votes:
            if existing_vote.voter_id == voter_id:
                raise ValueError(f"Voter {voter_id} has already voted")
        
        # Record vote
        vote = Vote(
            voter_id=voter_id,
            vote_type=vote_type,
            voting_power=voter.voting_power,
            reason=reason,
        )
        proposal.votes.append(vote)
        
        # Update tallies
        if vote_type == VoteType.FOR:
            proposal.votes_for += voter.voting_power
        elif vote_type == VoteType.AGAINST:
            proposal.votes_against += voter.voting_power
        else:
            proposal.votes_abstain += voter.voting_power
        
        return True
    
    def finalize_proposal(self, proposal_id: str) -> Proposal:
        """
        Finalize a proposal after voting ends.
        
        Returns:
            Updated Proposal with final status
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        now = datetime.now(timezone.utc)
        
        # Check if voting period ended
        if now < proposal.voting_ends_at:
            raise ValueError("Voting period has not ended")
        
        if proposal.status == ProposalStatus.ACTIVE:
            if proposal.passed:
                proposal.status = ProposalStatus.PASSED
            else:
                proposal.status = ProposalStatus.REJECTED
        
        return proposal
    
    def execute_proposal(self, proposal_id: str) -> Dict:
        """
        Execute a passed proposal.
        
        Returns:
            Execution result
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        # Finalize if needed
        if proposal.status == ProposalStatus.ACTIVE:
            self.finalize_proposal(proposal_id)
        
        if proposal.status != ProposalStatus.PASSED:
            raise ValueError(f"Proposal cannot be executed (status: {proposal.status.value})")
        
        # Check execution delay
        now = datetime.now(timezone.utc)
        execution_time = proposal.voting_ends_at + timedelta(hours=proposal.execution_delay_hours)
        if now < execution_time:
            raise ValueError(f"Execution delay not met. Can execute after {execution_time.isoformat()}")
        
        # Execute based on proposal type
        result = self._execute_proposal_action(proposal)
        
        proposal.status = ProposalStatus.EXECUTED
        proposal.executed_at = now
        proposal.execution_result = result
        
        return result
    
    def _execute_proposal_action(self, proposal: Proposal) -> Dict:
        """Execute the actual proposal action"""
        
        if proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
            return self._execute_parameter_change(proposal.parameters)
        
        elif proposal.proposal_type == ProposalType.POLICY_UPDATE:
            return self._execute_policy_update(proposal.parameters)
        
        elif proposal.proposal_type == ProposalType.PAUSE_AGENT:
            return self._execute_pause_agent()
        
        elif proposal.proposal_type == ProposalType.RESUME_AGENT:
            return self._execute_resume_agent()
        
        elif proposal.proposal_type == ProposalType.ADD_MEMBER:
            return self._execute_add_member(proposal.parameters)
        
        elif proposal.proposal_type == ProposalType.REMOVE_MEMBER:
            return self._execute_remove_member(proposal.parameters)
        
        elif proposal.proposal_type == ProposalType.EMERGENCY_ACTION:
            return self._execute_emergency_action(proposal.parameters)
        
        return {"success": False, "error": "Unknown proposal type"}
    
    def _execute_parameter_change(self, params: Dict) -> Dict:
        """Execute parameter change"""
        changes = []
        
        if "max_drawdown_pct" in params:
            config.risk_limits.max_drawdown_pct = params["max_drawdown_pct"]
            changes.append(f"max_drawdown_pct = {params['max_drawdown_pct']}")
        
        if "max_single_trade_pct" in params:
            config.risk_limits.max_single_trade_pct = params["max_single_trade_pct"]
            changes.append(f"max_single_trade_pct = {params['max_single_trade_pct']}")
        
        if "max_daily_loss_pct" in params:
            config.risk_limits.max_daily_loss_pct = params["max_daily_loss_pct"]
            changes.append(f"max_daily_loss_pct = {params['max_daily_loss_pct']}")
        
        # Recompute policy hash
        config.identity.policy_hash = config.identity.compute_policy_hash(
            config.risk_limits, config.policy_thresholds
        )
        
        return {
            "success": True,
            "changes": changes,
            "new_policy_hash": config.identity.policy_hash,
        }
    
    def _execute_policy_update(self, params: Dict) -> Dict:
        """Execute policy threshold update"""
        changes = []
        
        if "volatility_crisis_threshold" in params:
            config.policy_thresholds.volatility_crisis_threshold = params["volatility_crisis_threshold"]
            changes.append(f"volatility_crisis_threshold = {params['volatility_crisis_threshold']}")
        
        # Recompute policy hash
        config.identity.policy_hash = config.identity.compute_policy_hash(
            config.risk_limits, config.policy_thresholds
        )
        
        return {
            "success": True,
            "changes": changes,
            "new_policy_hash": config.identity.policy_hash,
        }
    
    def _execute_pause_agent(self) -> Dict:
        """Pause the agent via policy engine"""
        from agent.policy_engine import policy_engine
        policy_engine.set_governance_pause(True)
        return {"success": True, "action": "Agent paused"}
    
    def _execute_resume_agent(self) -> Dict:
        """Resume the agent via policy engine"""
        from agent.policy_engine import policy_engine
        policy_engine.set_governance_pause(False)
        return {"success": True, "action": "Agent resumed"}
    
    def _execute_add_member(self, params: Dict) -> Dict:
        """Add a new governance member"""
        member = self.add_member(
            member_id=params["member_id"],
            address=params["address"],
            voting_power=params.get("voting_power", 1.0),
        )
        return {"success": True, "member": member.to_dict()}
    
    def _execute_remove_member(self, params: Dict) -> Dict:
        """Remove a governance member"""
        success = self.remove_member(params["member_id"])
        return {"success": success, "member_id": params["member_id"]}
    
    def _execute_emergency_action(self, params: Dict) -> Dict:
        """Execute emergency action"""
        action = params.get("action")
        
        if action == "close_all_positions":
            from agent.policy_engine import policy_engine
            policy_engine.set_governance_pause(True)
            return {"success": True, "action": "Emergency: Closed all positions, agent paused"}
        
        return {"success": False, "error": f"Unknown emergency action: {action}"}
    
    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get a proposal by ID"""
        proposal = self._proposals.get(proposal_id)
        return proposal.to_dict() if proposal else None
    
    def get_active_proposals(self) -> List[Dict]:
        """Get all active proposals"""
        return [p.to_dict() for p in self._proposals.values() 
                if p.status == ProposalStatus.ACTIVE]
    
    def get_all_proposals(self) -> List[Dict]:
        """Get all proposals"""
        return [p.to_dict() for p in self._proposals.values()]
    
    def get_governance_status(self) -> Dict:
        """Get governance system status"""
        return {
            "total_members": len(self._members),
            "active_members": len(self.get_active_members()),
            "total_voting_power": self.get_total_voting_power(),
            "quorum_percentage": config.governance.quorum_percentage,
            "proposal_duration_hours": config.governance.proposal_duration_hours,
            "execution_delay_hours": config.governance.execution_delay_hours,
            "active_proposals": len(self.get_active_proposals()),
            "total_proposals": len(self._proposals),
        }


# Global governance instance
governance = Governance()
