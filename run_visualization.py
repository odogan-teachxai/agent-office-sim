#!/usr/bin/env python3
"""
Run the Agent Office Simulation with Real-Time Visualization.

This script creates a simulation and launches a visual interface
showing the network graph and post spreading dynamics.
"""

import random
from agent_office import (
    Agent, AgentType, create_agent_from_type,
    Post, create_sample_posts,
    SocialNetwork,
    Simulation,
    SimulationVisualizer,
    create_visualization
)


def create_visualization_simulation():
    """Create a simulation optimized for visualization."""
    # Create network
    network = SocialNetwork()
    
    # Create agents with different types
    agent_configs = [
        ("Alice", AgentType.IMMEDIATE_SHARER),
        ("Bob", AgentType.IMMEDIATE_SHARER),
        ("Charlie", AgentType.CAUTIOUS_SHARER),
        ("Diana", AgentType.CAUTIOUS_SHARER),
        ("Eve", AgentType.SKEPTIC),
        ("Frank", AgentType.SKEPTIC),
        ("Grace", AgentType.INFLUENCER),
        ("Henry", AgentType.INFLUENCER),
        ("Ivy", AgentType.LURKER),
        ("Jack", AgentType.LURKER),
        ("Kate", AgentType.CAUTIOUS_SHARER),
        ("Leo", AgentType.IMMEDIATE_SHARER),
        ("Mia", AgentType.SKEPTIC),
    ]
    
    agents = []
    for i, (name, agent_type) in enumerate(agent_configs):
        agent = create_agent_from_type(f"agent_{i}", name, agent_type)
        network.add_agent(agent)
        agents.append(agent)
    
    # Create network connections
    network.create_preferential_attachment_network(avg_connections=3)
    
    # Create simulation (without running it yet)
    simulation = Simulation(
        network=network,
        tick_delay=0.1  # Will be controlled by visualizer
    )
    
    # Add posts with different characteristics
    posts = [
        Post(
            subject="New Study Shows Benefits of Regular Exercise",
            content="A comprehensive study confirms health benefits.",
            category="health",
            truth_value="true",
            emotional_intensity=0.3,
            credibility_score=0.9,
            source_reliability=0.95
        ),
        Post(
            subject="SHOCKING: Celebrities Secretly Running Government!",
            content="Insiders reveal shocking truth!",
            category="gossip",
            truth_value="false",
            emotional_intensity=0.9,
            credibility_score=0.2,
            source_reliability=0.1
        ),
        Post(
            subject="Scientists Discover New Species in Deep Ocean",
            content="Marine biologists identify unknown species.",
            category="science",
            truth_value="true",
            emotional_intensity=0.5,
            credibility_score=0.85,
            source_reliability=0.9
        ),
        Post(
            subject="Miracle Cure Found - Doctors Don't Want You to Know",
            content="A simple ingredient cures all diseases!",
            category="health",
            truth_value="false",
            emotional_intensity=0.95,
            credibility_score=0.1,
            source_reliability=0.05
        ),
        Post(
            subject="Climate Change: What They're Not Telling You",
            content="Mixed information about climate impacts.",
            category="politics",
            truth_value="mixed",
            emotional_intensity=0.7,
            credibility_score=0.5,
            source_reliability=0.4
        ),
        Post(
            subject="Local Library Announces Summer Reading Program",
            content="Free program for children starting next month.",
            category="news",
            truth_value="true",
            emotional_intensity=0.2,
            credibility_score=0.85,
            source_reliability=0.9
        ),
    ]
    
    # Add posts to simulation with initial agents
    for post in posts:
        # Choose an initial agent (prefer influencers for initial posts)
        influencers = [a for a in agents if a.agent_type == AgentType.INFLUENCER]
        if influencers and random.random() < 0.6:
            initial_agent = random.choice(influencers)
        else:
            initial_agent = random.choice(agents)
        
        simulation.add_post(post, initial_agent)
    
    return network, simulation


def main():
    """Main entry point for visualization."""
    print("\n" + "=" * 60)
    print("   🏢 AGENT OFFICE - Simulation Visualizer")
    print("=" * 60)
    print("\nInitializing simulation...")
    
    # Create simulation
    network, simulation = create_visualization_simulation()
    
    print(f"Created network with {len(network.agents)} agents")
    print(f"Added {len(simulation.posts)} posts to simulate")
    print("\nLaunching visualization window...")
    print("\nControls:")
    print("  • Click 'Start' to begin the simulation")
    print("  • Click 'Pause' to pause at any time")
    print("  • Click 'Reset' to restart the simulation")
    print("  • Use the speed slider to adjust animation speed")
    print("\n" + "=" * 60)
    
    # Create and run visualization
    visualizer = create_visualization(
        network, 
        simulation,
        title="Agent Office - Live Simulation"
    )
    
    visualizer.run()


if __name__ == "__main__":
    main()
