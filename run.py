#!/usr/bin/env python3
"""
Quick run script for Agent Office simulation.
"""

from agent_office.main import run_simulation

if __name__ == "__main__":
    print("Starting Agent Office Simulation...")
    print("=" * 60)
    
    run_simulation(
        num_agents=13,      # 13 diverse agents
        num_posts=8,        # 8 different posts
        tick_delay=0.3,     # 0.3 second between updates
        max_ticks=500,      # Max 500 ticks
        verbose=True        # Show detailed output
    )
    
    print("\n" + "=" * 60)
    print("Simulation complete! Check the 'output/' directory for JSON logs.")
