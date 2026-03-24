#!/usr/bin/env python3
"""
Agent Office - Main Entry Point

Run the social network information spread simulation.
"""

import argparse
import random
from datetime import datetime

from .agent import Agent, AgentType, create_agent_from_type
from .post import Post, PostCategory, TruthValue, create_sample_posts
from .network import SocialNetwork
from .simulation import Simulation, create_default_simulation
from .logger import SimulationLogger


def create_custom_agents() -> list[Agent]:
    """Create a diverse set of agents with different characteristics."""
    # Import JobRole for assigning office roles
    from .agent import JobRole
    job_roles = list(JobRole)
    
    agents = [
        # Immediate Sharers - Low skepticism, high gullibility
        create_agent_from_type("agent_0", "Alice", AgentType.IMMEDIATE_SHARER, job_role=job_roles[0]),
        create_agent_from_type("agent_1", "Bob", AgentType.IMMEDIATE_SHARER, job_role=job_roles[1]),
        
        # Cautious Sharers - Balanced, moderate verification
        create_agent_from_type("agent_2", "Charlie", AgentType.CAUTIOUS_SHARER, job_role=job_roles[2]),
        create_agent_from_type("agent_3", "Diana", AgentType.CAUTIOUS_SHARER, job_role=job_roles[3]),
        
        # Skeptics - High skepticism, thorough verification
        create_agent_from_type("agent_4", "Eve", AgentType.SKEPTIC, job_role=job_roles[4]),
        create_agent_from_type("agent_5", "Frank", AgentType.SKEPTIC, job_role=job_roles[5]),
        
        # Influencers - High influence, moderate behavior
        create_agent_from_type("agent_6", "Grace", AgentType.INFLUENCER, job_role=job_roles[6]),
        create_agent_from_type("agent_7", "Henry", AgentType.INFLUENCER, job_role=job_roles[7]),
        
        # Lurkers - Low sharing, high threshold
        create_agent_from_type("agent_8", "Ivy", AgentType.LURKER, job_role=job_roles[0]),
        create_agent_from_type("agent_9", "Jack", AgentType.LURKER, job_role=job_roles[2]),
        
        # Additional agents for variety
        create_agent_from_type("agent_10", "Kate", AgentType.CAUTIOUS_SHARER, job_role=job_roles[1]),
        create_agent_from_type("agent_11", "Leo", AgentType.IMMEDIATE_SHARER, job_role=job_roles[4]),
        create_agent_from_type("agent_12", "Mia", AgentType.SKEPTIC, job_role=job_roles[6]),
    ]
    
    return agents


def run_simulation(
    num_agents: int = 13,
    num_posts: int = 8,
    tick_delay: float = 0.3,
    max_ticks: int = 500,
    verbose: bool = True
) -> dict:
    """
    Run the Agent Office simulation.
    
    Args:
        num_agents: Number of agents in the network
        num_posts: Number of posts to simulate
        tick_delay: Delay between simulation ticks
        max_ticks: Maximum number of ticks to run
        verbose: Whether to print detailed output
        
    Returns:
        Simulation report dictionary
    """
    # Initialize logger
    logger = SimulationLogger(verbose=verbose)
    
    # Create network
    network = SocialNetwork()
    
    # Create and add agents
    all_agents = create_custom_agents()
    agents_to_use = all_agents[:num_agents]
    
    for agent in agents_to_use:
        network.add_agent(agent)
    
    # Create network connections (preferential attachment for realistic structure)
    network.create_preferential_attachment_network(avg_connections=4)
    
    # Log network stats
    network_stats = network.get_network_stats()
    logger.log_network_stats(network_stats)
    
    # Create simulation with logger callback
    def on_event(event):
        logger.log_event(event)
    
    simulation = Simulation(
        network=network,
        tick_delay=tick_delay,
        on_event=on_event
    )
    
    # Create and add posts
    all_posts = create_sample_posts()
    posts_to_use = random.sample(all_posts, min(num_posts, len(all_posts)))
    
    # Assign initial posters (prioritize influencers for initial posts)
    influencers = [a for a in agents_to_use if a.agent_type == AgentType.INFLUENCER]
    other_agents = [a for a in agents_to_use if a.agent_type != AgentType.INFLUENCER]
    
    for i, post in enumerate(posts_to_use):
        # Influencers are more likely to create initial posts
        if influencers and i < len(influencers):
            initial_agent = influencers[i % len(influencers)]
        else:
            initial_agent = random.choice(agents_to_use)
        
        simulation.add_post(post, initial_agent)
    
    # Log simulation start
    logger.log_simulation_start(num_posts, num_agents)
    
    # Run simulation
    stats = simulation.run(max_ticks=max_ticks, stop_when_idle=True, idle_threshold=15)
    
    # Get final report
    report = simulation.get_simulation_report()
    
    # Log simulation end
    logger.log_simulation_end(stats, report)
    
    return report


def main():
    """Main entry point for the simulation."""
    parser = argparse.ArgumentParser(
        description="Agent Office - Social Network Information Spread Simulation"
    )
    parser.add_argument(
        "--agents", "-a",
        type=int,
        default=13,
        help="Number of agents in the network (default: 13)"
    )
    parser.add_argument(
        "--posts", "-p",
        type=int,
        default=8,
        help="Number of posts to simulate (default: 8)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.3,
        help="Delay between ticks in seconds (default: 0.3)"
    )
    parser.add_argument(
        "--max-ticks", "-m",
        type=int,
        default=500,
        help="Maximum number of simulation ticks (default: 500)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress terminal output (still saves to JSON)"
    )
    
    args = parser.parse_args()
    
    report = run_simulation(
        num_agents=args.agents,
        num_posts=args.posts,
        tick_delay=args.delay,
        max_ticks=args.max_ticks,
        verbose=not args.quiet
    )
    
    return report


if __name__ == "__main__":
    main()
