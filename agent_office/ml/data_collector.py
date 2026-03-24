"""
Data Collection Module - Tracks early dissemination behavior for each post.

This module specifically focuses on:
- Early spread patterns (first N ticks)
- Agent type involvement
- Verification and sharing decisions
- Timing metrics that differentiate misinformation from accurate information
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from collections import defaultdict
import json

from ..agent import AgentType, AgentBehavior, JobRole
from ..post import Post, TruthValue


@dataclass
class AgentInteraction:
    """Record of a single agent's interaction with a post."""
    tick: int
    agent_id: str
    agent_name: str
    agent_type: AgentType
    behavior: AgentBehavior
    confidence: float
    trust_modifier: float
    from_agent_type: Optional[AgentType] = None
    from_agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    # Job role (NEW for office simulation)
    job_role: Optional[JobRole] = None


@dataclass 
class DisseminationRecord:
    """
    Complete record of a post's dissemination through the network.
    
    This captures all the data needed for ML analysis of how information spreads.
    """
    post_id: str
    post_subject: str
    post_category: str
    truth_value: str
    emotional_intensity: float
    credibility_score: float
    source_reliability: float
    
    # Early dissemination metrics (first N ticks)
    early_window_ticks: int = 10  # Default window for "early" spread
    
    # Tracking data
    interactions: list[AgentInteraction] = field(default_factory=list)
    shares_by_tick: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    views_by_tick: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    flags_by_tick: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    # Agent type tracking
    agent_types_seen: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    agent_types_shared: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    agent_types_flagged: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    agent_types_verified: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Job role tracking (NEW for office simulation)
    job_roles_seen: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    job_roles_shared: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    job_roles_flagged: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Timing metrics
    first_share_tick: Optional[int] = None
    first_flag_tick: Optional[int] = None
    peak_share_tick: Optional[int] = None
    last_activity_tick: Optional[int] = None
    
    # Final counts
    total_reach: int = 0
    total_shares: int = 0
    total_flags: int = 0
    total_ignores: int = 0
    total_verifications: int = 0
    
    def record_interaction(self, interaction: AgentInteraction) -> None:
        """Record an agent interaction with this post."""
        self.interactions.append(interaction)
        
        # Update timing
        if self.last_activity_tick is None or interaction.tick > self.last_activity_tick:
            self.last_activity_tick = interaction.tick
        
        # Track by tick
        self.views_by_tick[interaction.tick] += 1
        
        # Track by agent type
        agent_type_str = interaction.agent_type.value
        self.agent_types_seen[agent_type_str] += 1
        
        # Track by job role (NEW for office simulation)
        if interaction.job_role:
            job_role_str = interaction.job_role.value
            self.job_roles_seen[job_role_str] += 1
        
        # Track behavior-specific metrics
        if interaction.behavior in [AgentBehavior.SHARE_IMMEDIATELY, AgentBehavior.VERIFY_THEN_SHARE]:
            self.total_shares += 1
            self.shares_by_tick[interaction.tick] += 1
            self.agent_types_shared[agent_type_str] += 1
            
            # Track job role shares (NEW)
            if interaction.job_role:
                self.job_roles_shared[interaction.job_role.value] += 1
            
            if self.first_share_tick is None:
                self.first_share_tick = interaction.tick
            
            # Track peak
            current_tick_shares = self.shares_by_tick[interaction.tick]
            peak_shares = self.shares_by_tick.get(self.peak_share_tick or 0, 0)
            if current_tick_shares > peak_shares:
                self.peak_share_tick = interaction.tick
        
        if interaction.behavior == AgentBehavior.FLAG_AS_SUSPICIOUS:
            self.total_flags += 1
            self.flags_by_tick[interaction.tick] += 1
            self.agent_types_flagged[agent_type_str] += 1
            
            # Track job role flags (NEW)
            if interaction.job_role:
                self.job_roles_flagged[interaction.job_role.value] += 1
            
            if self.first_flag_tick is None:
                self.first_flag_tick = interaction.tick
        
        if interaction.behavior == AgentBehavior.IGNORE:
            self.total_ignores += 1
        
        if interaction.behavior in [AgentBehavior.VERIFY_THEN_SHARE, AgentBehavior.VERIFY_THEN_IGNORE]:
            self.total_verifications += 1
            self.agent_types_verified[agent_type_str] += 1
        
        self.total_reach += 1
    
    def get_early_metrics(self, window_ticks: Optional[int] = None) -> dict:
        """
        Get metrics specifically for the early dissemination window.
        
        This is crucial for ML - early patterns often predict later spread.
        """
        window = window_ticks or self.early_window_ticks
        
        early_interactions = [i for i in self.interactions if i.tick < window]
        
        # Early reach and shares
        early_reach = sum(1 for i in early_interactions)
        early_shares = sum(1 for i in early_interactions 
                         if i.behavior in [AgentBehavior.SHARE_IMMEDIATELY, AgentBehavior.VERIFY_THEN_SHARE])
        early_flags = sum(1 for i in early_interactions 
                        if i.behavior == AgentBehavior.FLAG_AS_SUSPICIOUS)
        early_ignores = sum(1 for i in early_interactions 
                          if i.behavior == AgentBehavior.IGNORE)
        early_verifications = sum(1 for i in early_interactions 
                                if i.behavior in [AgentBehavior.VERIFY_THEN_SHARE, AgentBehavior.VERIFY_THEN_IGNORE])
        
        # Early agent type distribution
        early_agent_types = defaultdict(int)
        early_sharing_types = defaultdict(int)
        early_flagging_types = defaultdict(int)
        
        # Early job role distribution (NEW)
        early_job_roles = defaultdict(int)
        early_job_roles_shared = defaultdict(int)
        early_job_roles_flagged = defaultdict(int)
        
        for i in early_interactions:
            early_agent_types[i.agent_type.value] += 1
            if i.behavior in [AgentBehavior.SHARE_IMMEDIATELY, AgentBehavior.VERIFY_THEN_SHARE]:
                early_sharing_types[i.agent_type.value] += 1
            if i.behavior == AgentBehavior.FLAG_AS_SUSPICIOUS:
                early_flagging_types[i.agent_type.value] += 1
            
            # Track job roles (NEW)
            if i.job_role:
                early_job_roles[i.job_role.value] += 1
                if i.behavior in [AgentBehavior.SHARE_IMMEDIATELY, AgentBehavior.VERIFY_THEN_SHARE]:
                    early_job_roles_shared[i.job_role.value] += 1
                if i.behavior == AgentBehavior.FLAG_AS_SUSPICIOUS:
                    early_job_roles_flagged[i.job_role.value] += 1
        
        # Early velocity (shares per tick)
        early_velocity = early_shares / max(1, window)
        
        # Average confidence of early sharers
        early_confidences = [i.confidence for i in early_interactions 
                            if i.behavior in [AgentBehavior.SHARE_IMMEDIATELY, AgentBehavior.VERIFY_THEN_SHARE]]
        avg_early_confidence = sum(early_confidences) / max(1, len(early_confidences))
        
        return {
            "early_window_ticks": window,
            "early_reach": early_reach,
            "early_shares": early_shares,
            "early_flags": early_flags,
            "early_ignores": early_ignores,
            "early_verifications": early_shares + early_ignores if early_verifications == 0 else early_verifications,
            "early_share_rate": early_shares / max(1, early_reach),
            "early_flag_rate": early_flags / max(1, early_reach),
            "early_velocity": early_velocity,
            "avg_early_confidence": avg_early_confidence,
            "early_agent_types_seen": dict(early_agent_types),
            "early_agent_types_shared": dict(early_sharing_types),
            "early_agent_types_flagged": dict(early_flagging_types),
            # Job role metrics (NEW)
            "early_job_roles": dict(early_job_roles),
            "early_job_roles_shared": dict(early_job_roles_shared),
            "early_job_roles_flagged": dict(early_job_roles_flagged),
        }
    
    def get_full_metrics(self) -> dict:
        """Get complete dissemination metrics for this post."""
        return {
            # Post characteristics
            "post_id": self.post_id,
            "post_subject": self.post_subject,
            "post_category": self.post_category,
            "truth_value": self.truth_value,
            "emotional_intensity": self.emotional_intensity,
            "credibility_score": self.credibility_score,
            "source_reliability": self.source_reliability,
            
            # Overall metrics
            "total_reach": self.total_reach,
            "total_shares": self.total_shares,
            "total_flags": self.total_flags,
            "total_ignores": self.total_ignores,
            "total_verifications": self.total_verifications,
            
            # Rates
            "share_rate": self.total_shares / max(1, self.total_reach),
            "flag_rate": self.total_flags / max(1, self.total_reach),
            "ignore_rate": self.total_ignores / max(1, self.total_reach),
            "verification_rate": self.total_verifications / max(1, self.total_reach),
            
            # Timing
            "first_share_tick": self.first_share_tick,
            "first_flag_tick": self.first_flag_tick,
            "peak_share_tick": self.peak_share_tick,
            "last_activity_tick": self.last_activity_tick,
            
            # Agent type distributions
            "agent_types_seen": dict(self.agent_types_seen),
            "agent_types_shared": dict(self.agent_types_shared),
            "agent_types_flagged": dict(self.agent_types_flagged),
            "agent_types_verified": dict(self.agent_types_verified),
            
            # Early metrics
            **{f"early_{k}": v for k, v in self.get_early_metrics().items() 
               if not isinstance(v, dict)}
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "post_id": self.post_id,
            "post_subject": self.post_subject,
            "post_category": self.post_category,
            "truth_value": self.truth_value,
            "emotional_intensity": self.emotional_intensity,
            "credibility_score": self.credibility_score,
            "source_reliability": self.source_reliability,
            "early_window_ticks": self.early_window_ticks,
            "interactions": [
                {
                    "tick": i.tick,
                    "agent_id": i.agent_id,
                    "agent_name": i.agent_name,
                    "agent_type": i.agent_type.value,
                    "behavior": i.behavior.value,
                    "confidence": i.confidence,
                    "trust_modifier": i.trust_modifier,
                    "from_agent_type": i.from_agent_type.value if i.from_agent_type else None,
                    "from_agent_id": i.from_agent_id,
                    "timestamp": i.timestamp.isoformat()
                }
                for i in self.interactions
            ],
            "shares_by_tick": dict(self.shares_by_tick),
            "views_by_tick": dict(self.views_by_tick),
            "flags_by_tick": dict(self.flags_by_tick),
            "agent_types_seen": dict(self.agent_types_seen),
            "agent_types_shared": dict(self.agent_types_shared),
            "agent_types_flagged": dict(self.agent_types_flagged),
            "agent_types_verified": dict(self.agent_types_verified),
            "first_share_tick": self.first_share_tick,
            "first_flag_tick": self.first_flag_tick,
            "peak_share_tick": self.peak_share_tick,
            "last_activity_tick": self.last_activity_tick,
            "total_reach": self.total_reach,
            "total_shares": self.total_shares,
            "total_flags": self.total_flags,
            "total_ignores": self.total_ignores,
            "total_verifications": self.total_verifications,
            "early_metrics": self.get_early_metrics(),
            "full_metrics": self.get_full_metrics()
        }


class EarlyDisseminationTracker:
    """
    Tracks early dissemination behavior for all posts in a simulation.
    
    This is the main data collection component that integrates with the simulation
    to capture ML-ready data about how information spreads.
    """
    
    def __init__(self, early_window_ticks: int = 10):
        """
        Initialize the tracker.
        
        Args:
            early_window_ticks: Number of ticks to consider as "early" dissemination
        """
        self.early_window_ticks = early_window_ticks
        self.records: dict[str, DisseminationRecord] = {}
        self.agent_registry: dict[str, AgentType] = {}  # agent_id -> AgentType
        self.job_role_registry: dict[str, JobRole] = {}  # agent_id -> JobRole (NEW)
    
    def register_agent(self, agent_id: str, agent_type: AgentType, job_role: Optional[JobRole] = None) -> None:
        """Register an agent for tracking."""
        self.agent_registry[agent_id] = agent_type
        if job_role:
            self.job_role_registry[agent_id] = job_role
    
    def register_post(self, post: Post) -> None:
        """Register a post for tracking."""
        if post.id not in self.records:
            self.records[post.id] = DisseminationRecord(
                post_id=post.id,
                post_subject=post.subject,
                post_category=post.category.value,
                truth_value=post.truth_value.value,
                emotional_intensity=post.emotional_intensity,
                credibility_score=post.credibility_score,
                source_reliability=post.source_reliability,
                early_window_ticks=self.early_window_ticks
            )
    
    def record_event(
        self,
        tick: int,
        post_id: str,
        agent_id: str,
        agent_name: str,
        behavior,  # Can be AgentBehavior enum or string
        confidence: float,
        trust_modifier: float,
        from_agent_id: Optional[str] = None
    ) -> None:
        """Record a simulation event for data collection."""
        if post_id not in self.records:
            return
        
        record = self.records[post_id]
        agent_type = self.agent_registry.get(agent_id, AgentType.CAUTIOUS_SHARER)
        from_agent_type = self.agent_registry.get(from_agent_id) if from_agent_id else None
        job_role = self.job_role_registry.get(agent_id)  # NEW: Get job role
        
        # Convert string behavior to enum if needed
        if isinstance(behavior, str):
            behavior = AgentBehavior(behavior)
        
        interaction = AgentInteraction(
            tick=tick,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            behavior=behavior,
            confidence=confidence,
            trust_modifier=trust_modifier,
            from_agent_type=from_agent_type,
            from_agent_id=from_agent_id,
            job_role=job_role  # NEW: Include job role
        )
        
        record.record_interaction(interaction)
    
    def get_record(self, post_id: str) -> Optional[DisseminationRecord]:
        """Get the dissemination record for a post."""
        return self.records.get(post_id)
    
    def get_all_records(self) -> list[DisseminationRecord]:
        """Get all dissemination records."""
        return list(self.records.values())
    
    def get_records_by_truth(self, truth_value: str) -> list[DisseminationRecord]:
        """Get records filtered by truth value."""
        return [r for r in self.records.values() if r.truth_value == truth_value]
    
    def get_summary(self) -> dict:
        """Get a summary of all collected data."""
        true_records = self.get_records_by_truth("true")
        false_records = self.get_records_by_truth("false")
        mixed_records = self.get_records_by_truth("mixed")
        unverified_records = self.get_records_by_truth("unverified")
        
        def avg_metric(records: list[DisseminationRecord], metric: str) -> float:
            values = [getattr(r, metric) for r in records]
            return sum(values) / max(1, len(values))
        
        return {
            "total_posts": len(self.records),
            "total_interactions": sum(len(r.interactions) for r in self.records.values()),
            "by_truth_value": {
                "true": len(true_records),
                "false": len(false_records),
                "mixed": len(mixed_records),
                "unverified": len(unverified_records)
            },
            "avg_metrics_by_truth": {
                "true": {
                    "avg_reach": avg_metric(true_records, "total_reach"),
                    "avg_shares": avg_metric(true_records, "total_shares"),
                    "avg_flags": avg_metric(true_records, "total_flags"),
                },
                "false": {
                    "avg_reach": avg_metric(false_records, "total_reach"),
                    "avg_shares": avg_metric(false_records, "total_shares"),
                    "avg_flags": avg_metric(false_records, "total_flags"),
                }
            }
        }
    
    def export_to_json(self, filepath: str) -> None:
        """Export all records to a JSON file."""
        data = {
            "metadata": {
                "early_window_ticks": self.early_window_ticks,
                "total_posts": len(self.records),
                "export_time": datetime.now().isoformat()
            },
            "records": [r.to_dict() for r in self.records.values()],
            "summary": self.get_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
