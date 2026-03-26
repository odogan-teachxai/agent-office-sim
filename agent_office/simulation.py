"""
Simulation module - Runs the information spread simulation.
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, TYPE_CHECKING
from datetime import datetime
from enum import Enum
import time
import random
from collections import deque

from .agent import Agent, AgentBehavior, AgentType, create_agent_from_type
from .post import Post, TruthValue
from .network import SocialNetwork

if TYPE_CHECKING:
    from .office import Office, OfficeTask


# =============================================================================
# Module-Level Constants
# =============================================================================

DEFAULT_BATCH_SIZE = 5  # Shares processed per tick


class SimulationState(Enum):
    """State of the simulation."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class SimulationEvent:
    """Represents an event during the simulation."""
    timestamp: datetime
    tick: int
    event_type: str
    agent_id: str
    agent_name: str
    post_id: str
    post_subject: str
    behavior: str
    details: dict = field(default_factory=dict)


@dataclass
class SimulationStats:
    """Statistics for the simulation run."""
    total_ticks: int = 0
    total_posts: int = 0
    total_shares: int = 0
    total_flags: int = 0
    true_posts_shared: int = 0
    false_posts_shared: int = 0
    avg_spread_time: float = 0.0
    
    def get_summary(self) -> dict:
        return {
            "total_ticks": self.total_ticks,
            "total_posts": self.total_posts,
            "total_shares": self.total_shares,
            "total_flags": self.total_flags,
            "true_posts_shared": self.true_posts_shared,
            "false_posts_shared": self.false_posts_shared,
            "true_false_ratio": self.true_posts_shared / max(1, self.false_posts_shared),
            "avg_spread_time": round(self.avg_spread_time, 2)
        }


class Simulation:
    """
    Main simulation engine for the Agent Office.
    
    Manages the flow of information through the social network,
    tracking how posts spread between agents.
    
    Can optionally run office work simulation alongside info-spread.
    """
    
    def __init__(
        self,
        network: SocialNetwork,
        tick_delay: float = 0.5,
        on_event: Optional[Callable[[SimulationEvent], None]] = None,
        office: Optional['Office'] = None,
        on_office_event: Optional[Callable[[str, 'Agent', Optional['OfficeTask']], None]] = None,
        random_seed: Optional[int] = None
    ):
        """
        Initialize the simulation.
        
        Args:
            network: The social network to simulate
            tick_delay: Delay between simulation ticks (seconds)
            on_event: Callback function for simulation events (info-spread)
            office: Optional Office instance for work simulation
            on_office_event: Callback for office events (event_type, agent, task)
            random_seed: Optional seed for reproducible random behavior
        """
        self.network = network
        self.tick_delay = tick_delay
        self.on_event = on_event
        self.office = office
        self.on_office_event = on_office_event
        self.random_seed = random_seed
        
        # Apply seed immediately for full reproducibility from Simulation creation onward
        # This covers agent evaluation, office work, and the tick loop
        if random_seed is not None:
            random.seed(random_seed)
        
        self.state = SimulationState.IDLE
        self.current_tick = 0
        self.posts: dict[str, Post] = {}
        self.pending_shares: deque = deque()  # (post_id, from_agent_id, to_agent_id, tick_created)
        self.events: list[SimulationEvent] = []
        self.stats = SimulationStats()
        
        # Track spread timing
        self.post_first_seen: dict[str, int] = {}  # post_id -> tick first seen
        self.post_last_shared: dict[str, int] = {}  # post_id -> tick last shared
        
        # Office events tracking (separate from info-spread events)
        self.office_events: list[dict] = []
        
        # Track work-generated posts (for logging)
        self.work_posts_generated: list[dict] = []
        
        # Connect office to simulation if provided
        if self.office:
            self._connect_office()
    
    def add_post(self, post: Post, initial_agent: Optional[Agent] = None) -> None:
        """
        Add a post to the simulation.
        
        Args:
            post: The post to add
            initial_agent: The agent who creates/posts this (optional)
        """
        self.posts[post.id] = post
        self.stats.total_posts += 1
        
        if initial_agent:
            post.author_id = initial_agent.id
            post.record_view()
            initial_agent.record_post_seen(post.id)
            
            # Queue shares to all followers
            self._queue_shares_to_followers(post, initial_agent)
    
    def _connect_office(self) -> None:
        """
        Connect the office to this simulation.
        When office tasks complete, the generated posts will be injected into
        the info-spread network.
        """
        def on_work_post_created(post: Post, agent: Agent, product=None) -> None:
            """Callback when office work generates a post."""
            # Log the work post creation
            from .office import Product
            self.work_posts_generated.append({
                'tick': self.current_tick,
                'post_id': post.id,
                'post_subject': post.subject,
                'agent_id': agent.id,
                'agent_name': agent.name,
                'agent_job_role': agent.job_role.value if agent.job_role else None,
                'product_advanced': product is not None,
                'product_name': product.name if product else None
            })
            
            # Inject the post into the simulation (it spreads like any other post!)
            self.add_post(post, agent)
            
            # Trigger callback if set
            if self.on_office_event:
                self.on_office_event("work_post_created", agent, None)
        
        # Set the callback on the office
        self.office.on_post_create = on_work_post_created
    
    def _queue_shares_to_followers(self, post: Post, from_agent: Agent) -> None:
        """Queue shares of a post to all followers of an agent."""
        followers = self.network.get_followers(from_agent.id)
        
        for follower in followers:
            if not follower.has_seen_post(post.id):
                self.pending_shares.append((
                    post.id,
                    from_agent.id,
                    follower.id,
                    self.current_tick
                ))
    
    def _process_pending_share(self) -> Optional[SimulationEvent]:
        """Process a pending share from the queue."""
        if not self.pending_shares:
            return None
        
        post_id, from_agent_id, to_agent_id, tick_created = self.pending_shares.popleft()
        
        post = self.posts.get(post_id)
        to_agent = self.network.get_agent(to_agent_id)
        from_agent = self.network.get_agent(from_agent_id)
        
        if not post or not to_agent or not from_agent:
            return None
        
        # Skip if agent already saw this post
        if to_agent.has_seen_post(post.id):
            return None
        
        # Record that agent has seen the post
        to_agent.record_post_seen(post.id)
        to_agent.total_shares_received += 1
        post.record_view()
        
        # Track timing
        if post.id not in self.post_first_seen:
            self.post_first_seen[post.id] = self.current_tick
        
        # Get connection info for trust/strength
        connection = self.network.get_connection(to_agent_id, from_agent_id)
        trust_modifier = connection.trust_level if connection else 0.5
        
        # Agent evaluates the post
        behavior, confidence = to_agent.evaluate_post(post)
        
        # Create event
        event = SimulationEvent(
            timestamp=datetime.now(),
            tick=self.current_tick,
            event_type="post_received",
            agent_id=to_agent.id,
            agent_name=to_agent.name,
            post_id=post.id,
            post_subject=post.subject,
            behavior=behavior.value,
            details={
                "from_agent": from_agent.name,
                "confidence": round(confidence, 3),
                "trust_modifier": round(trust_modifier, 3),
                "agent_type": to_agent.agent_type.value,
                "job_role": to_agent.job_role.value if to_agent.job_role else None,
                "post_truth": post.truth_value.value,
                "post_category": post.category.value,
                "emotional_intensity": post.emotional_intensity
            }
        )
        
        self.events.append(event)
        
        # Process behavior
        if behavior in [AgentBehavior.SHARE_IMMEDIATELY, AgentBehavior.VERIFY_THEN_SHARE]:
            self._handle_share(to_agent, post, behavior)
        elif behavior == AgentBehavior.FLAG_AS_SUSPICIOUS:
            self._handle_flag(to_agent, post)
        
        return event
    
    def _handle_share(self, agent: Agent, post: Post, behavior: AgentBehavior) -> None:
        """Handle an agent sharing a post."""
        agent.record_post_shared(post.id)
        post.record_share(agent.id)
        self.stats.total_shares += 1
        
        # Track true/false shares
        if post.truth_value.is_true():
            self.stats.true_posts_shared += 1
        elif post.truth_value.is_false():
            self.stats.false_posts_shared += 1
        
        self.post_last_shared[post.id] = self.current_tick
        
        # Queue shares to followers
        self._queue_shares_to_followers(post, agent)
    
    def _handle_flag(self, agent: Agent, post: Post) -> None:
        """Handle an agent flagging a post as suspicious."""
        agent.record_post_flagged(post.id)
        post.record_flag()
        self.stats.total_flags += 1
    
    def tick(self) -> list[SimulationEvent]:
        """
        Run a single simulation tick.
        
        Each tick consists of:
        1. Info-spread phase: Process pending post shares
        2. Office work phase (optional): Agents work on tasks
        
        Returns:
            List of info-spread events that occurred during this tick
        """
        events_this_tick = []
        
        # === PHASE 1: INFO-SPREAD SIMULATION (unchanged) ===
        # Process a batch of pending shares
        batch_size = min(len(self.pending_shares), DEFAULT_BATCH_SIZE)
        for _ in range(batch_size):
            event = self._process_pending_share()
            if event:
                events_this_tick.append(event)
        
        # === PHASE 2: OFFICE WORK (optional, runs alongside) ===
        if self.office:
            completed_tasks = self.office.tick()
            for agent, task, product in completed_tasks:
                office_event = {
                    "tick": self.current_tick,
                    "event_type": "task_completed",
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_job_role": agent.job_role.value if agent.job_role else None,
                    "task_id": task.id,
                    "task_title": task.title,
                    "task_type": task.task_type.value,
                    "product_advanced": product is not None,
                    "product_name": product.name if product else None
                }
                self.office_events.append(office_event)
                
                # Trigger callback if set
                if self.on_office_event:
                    self.on_office_event("task_completed", agent, task)
        
        self.current_tick += 1
        self.stats.total_ticks = self.current_tick
        
        return events_this_tick
    
    def run(
        self, 
        max_ticks: int = 1000,
        stop_when_idle: bool = True,
        idle_threshold: int = 10
    ) -> SimulationStats:
        """
        Run the simulation.
        
        Args:
            max_ticks: Maximum number of ticks to run
            stop_when_idle: Stop if no activity for idle_threshold ticks
            idle_threshold: Number of ticks without activity before stopping
            
        Returns:
            Simulation statistics
        """
        self.state = SimulationState.RUNNING
        idle_ticks = 0
        
        while self.current_tick < max_ticks and self.state == SimulationState.RUNNING:
            events = self.tick()
            
            # Call event callback for each event
            for event in events:
                if self.on_event:
                    self.on_event(event)
            
            # Check for idle state
            if not events and not self.pending_shares:
                idle_ticks += 1
                if stop_when_idle and idle_ticks >= idle_threshold:
                    break
            else:
                idle_ticks = 0
            
            time.sleep(self.tick_delay)
        
        self.state = SimulationState.COMPLETED
        self._calculate_final_stats()
        
        return self.stats
    
    def _calculate_final_stats(self) -> None:
        """Calculate final statistics after simulation completes."""
        # Calculate average spread time
        spread_times = []
        for post_id in self.post_first_seen:
            if post_id in self.post_last_shared:
                spread_time = self.post_last_shared[post_id] - self.post_first_seen[post_id]
                spread_times.append(spread_time)
        
        if spread_times:
            self.stats.avg_spread_time = sum(spread_times) / len(spread_times)
    
    def pause(self) -> None:
        """Pause the simulation."""
        self.state = SimulationState.PAUSED
    
    def resume(self) -> None:
        """Resume the simulation."""
        self.state = SimulationState.RUNNING
    
    def get_post_stats(self) -> list[dict]:
        """Get statistics for all posts."""
        return [post.get_stats() for post in self.posts.values()]
    
    def get_agent_stats(self) -> list[dict]:
        """Get statistics for all agents."""
        return [agent.get_stats() for agent in self.network.get_all_agents()]
    
    def get_simulation_report(self) -> dict:
        """Get a comprehensive simulation report."""
        report = {
            "simulation_info": {
                "state": self.state.value,
                "total_ticks": self.current_tick,
                "total_events": len(self.events),
                "has_office": self.office is not None
            },
            "network_stats": self.network.get_network_stats(),
            "simulation_stats": self.stats.get_summary(),
            "post_stats": self.get_post_stats(),
            "agent_stats": self.get_agent_stats()
        }
        
        # Add office data if office is enabled
        if self.office:
            report["office_stats"] = self.office.get_stats()
            report["office_events"] = self.office_events
            report["work_posts_generated"] = self.work_posts_generated
            report["work_post_count"] = len(self.work_posts_generated)
        
        return report


def create_default_simulation(
    num_agents: int = 10,
    num_posts: int = 5,
    tick_delay: float = 0.3,
    on_event: Optional[Callable[[SimulationEvent], None]] = None
) -> Simulation:
    """
    Create a default simulation with random agents and posts.
    
    Args:
        num_agents: Number of agents to create
        num_posts: Number of posts to create
        tick_delay: Delay between ticks
        on_event: Event callback function
        
    Returns:
        Configured Simulation instance
    """
    from .post import create_sample_posts
    
    # Create network
    network = SocialNetwork()
    
    # Create agents with different types
    agent_types = list(AgentType)
    agent_names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve",
        "Frank", "Grace", "Henry", "Ivy", "Jack",
        "Kate", "Leo", "Mia", "Noah", "Olivia"
    ]
    
    for i in range(num_agents):
        agent_type = agent_types[i % len(agent_types)]
        name = agent_names[i] if i < len(agent_names) else f"Agent_{i}"
        agent = create_agent_from_type(f"agent_{i}", name, agent_type)
        network.add_agent(agent)
    
    # Create network connections using preferential attachment
    network.create_preferential_attachment_network(avg_connections=3)
    
    # Create simulation
    sim = Simulation(network, tick_delay=tick_delay, on_event=on_event)
    
    # Add posts
    all_posts = create_sample_posts()
    selected_posts = random.sample(all_posts, min(num_posts, len(all_posts)))
    
    for post in selected_posts:
        # Choose a random agent to be the initial poster
        initial_agent = random.choice(network.get_all_agents())
        sim.add_post(post, initial_agent)
    
    return sim
