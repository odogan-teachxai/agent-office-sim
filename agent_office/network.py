"""
Social Network module - Manages connections and relationships between agents.
"""

from dataclasses import dataclass, field
from typing import Optional
import random
from collections import defaultdict

from .agent import Agent, AgentType


@dataclass
class Connection:
    """Represents a connection between two agents."""
    follower_id: str
    followee_id: str
    strength: float = 0.5  # How strong the connection is (0.0 - 1.0)
    trust_level: float = 0.5  # How much the follower trusts the followee
    
    def __post_init__(self):
        self.strength = max(0.0, min(1.0, self.strength))
        self.trust_level = max(0.0, min(1.0, self.trust_level))


class SocialNetwork:
    """
    Manages the social network of agents and their connections.
    
    The network is represented as a directed graph where edges represent
    "follows" relationships. When an agent shares a post, it reaches
    all of their followers.
    """
    
    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.connections: dict[str, list[Connection]] = defaultdict(list)
        self.reverse_connections: dict[str, list[Connection]] = defaultdict(list)
    
    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the network."""
        self.agents[agent.id] = agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def add_connection(
        self, 
        follower_id: str, 
        followee_id: str,
        strength: float = 0.5,
        trust_level: float = 0.5
    ) -> bool:
        """
        Add a connection (follow relationship) between two agents.
        
        Args:
            follower_id: ID of the agent who follows
            followee_id: ID of the agent being followed
            strength: Connection strength (0.0 - 1.0)
            trust_level: Trust level (0.0 - 1.0)
            
        Returns:
            True if connection was added, False if agents don't exist
        """
        if follower_id not in self.agents or followee_id not in self.agents:
            return False
        
        # Check if connection already exists
        for conn in self.connections[follower_id]:
            if conn.followee_id == followee_id:
                # Update existing connection
                conn.strength = strength
                conn.trust_level = trust_level
                return True
        
        # Create new connection
        connection = Connection(
            follower_id=follower_id,
            followee_id=followee_id,
            strength=strength,
            trust_level=trust_level
        )
        
        self.connections[follower_id].append(connection)
        self.reverse_connections[followee_id].append(connection)
        return True
    
    def remove_connection(self, follower_id: str, followee_id: str) -> bool:
        """Remove a connection between two agents."""
        self.connections[follower_id] = [
            c for c in self.connections[follower_id] 
            if c.followee_id != followee_id
        ]
        self.reverse_connections[followee_id] = [
            c for c in self.reverse_connections[followee_id]
            if c.follower_id != follower_id
        ]
        return True
    
    def get_followers(self, agent_id: str) -> list[Agent]:
        """Get all followers of an agent."""
        followers = []
        for conn in self.reverse_connections[agent_id]:
            follower = self.agents.get(conn.follower_id)
            if follower:
                followers.append(follower)
        return followers
    
    def get_following(self, agent_id: str) -> list[Agent]:
        """Get all agents that an agent follows."""
        following = []
        for conn in self.connections[agent_id]:
            followee = self.agents.get(conn.followee_id)
            if followee:
                following.append(followee)
        return following
    
    def get_connection(self, follower_id: str, followee_id: str) -> Optional[Connection]:
        """Get the connection between two agents."""
        for conn in self.connections[follower_id]:
            if conn.followee_id == followee_id:
                return conn
        return None
    
    def get_all_agents(self) -> list[Agent]:
        """Get all agents in the network."""
        return list(self.agents.values())
    
    def get_influential_agents(self, top_n: int = 5) -> list[Agent]:
        """Get the most influential agents based on follower count."""
        agent_follower_counts = []
        for agent in self.agents.values():
            follower_count = len(self.get_followers(agent.id))
            agent_follower_counts.append((agent, follower_count))
        
        # Sort by follower count (descending)
        agent_follower_counts.sort(key=lambda x: x[1], reverse=True)
        return [agent for agent, _ in agent_follower_counts[:top_n]]
    
    def get_network_stats(self) -> dict:
        """Get statistics about the network."""
        total_connections = sum(len(conns) for conns in self.connections.values())
        avg_connections = total_connections / max(1, len(self.agents))
        
        agent_type_distribution = defaultdict(int)
        for agent in self.agents.values():
            agent_type_distribution[agent.agent_type.value] += 1
        
        return {
            "total_agents": len(self.agents),
            "total_connections": total_connections,
            "avg_connections_per_agent": round(avg_connections, 2),
            "agent_type_distribution": dict(agent_type_distribution),
            "most_influential": [
                {"name": a.name, "influence": a.influence, "followers": len(self.get_followers(a.id))}
                for a in self.get_influential_agents(3)
            ]
        }
    
    def create_random_connections(self, connection_probability: float = 0.3) -> None:
        """
        Create random connections between agents.
        
        Args:
            connection_probability: Probability that any two agents are connected
        """
        agent_ids = list(self.agents.keys())
        
        for follower_id in agent_ids:
            for followee_id in agent_ids:
                if follower_id == followee_id:
                    continue
                
                if random.random() < connection_probability:
                    # Influence affects connection strength
                    followee = self.agents[followee_id]
                    strength = 0.3 + (followee.influence * 0.5)
                    trust_level = 0.5 + random.uniform(-0.2, 0.2)
                    
                    self.add_connection(
                        follower_id, 
                        followee_id,
                        strength=strength,
                        trust_level=trust_level
                    )
    
    def create_preferential_attachment_network(self, avg_connections: int = 3) -> None:
        """
        Create a network using preferential attachment (rich-get-richer).
        
        Influential agents tend to get more followers.
        """
        agent_ids = list(self.agents.keys())
        
        for agent_id in agent_ids:
            # Decide how many people this agent will follow
            num_to_follow = random.randint(1, avg_connections * 2)
            
            # Weight by influence (preferential attachment)
            weights = []
            for other_id in agent_ids:
                if other_id == agent_id:
                    weights.append(0)
                else:
                    other_agent = self.agents[other_id]
                    # Higher influence = higher chance of being followed
                    weights.append(other_agent.influence + 0.1)
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
                
                # Select agents to follow
                num_to_follow = min(num_to_follow, len(agent_ids) - 1)
                followees = random.choices(agent_ids, weights=weights, k=num_to_follow)
                
                for followee_id in set(followees):  # Remove duplicates
                    if followee_id != agent_id:
                        followee = self.agents[followee_id]
                        self.add_connection(
                            agent_id,
                            followee_id,
                            strength=0.3 + (followee.influence * 0.5),
                            trust_level=0.4 + (followee.influence * 0.3)
                        )
    
    def __repr__(self) -> str:
        return f"SocialNetwork(agents={len(self.agents)}, connections={sum(len(c) for c in self.connections.values())})"
