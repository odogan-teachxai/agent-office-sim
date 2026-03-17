#!/usr/bin/env python3
"""
Run the Agent Office Simulation with Terminal Visualization.

This script creates a simulation and displays it in the terminal
using ASCII art and colors.
"""

from agent_office import run_terminal_visualization

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   🏢 AGENT OFFICE - Terminal Visualization")
    print("=" * 60)
    print("\nThis visualization shows the social network and post")
    print("spreading dynamics in real-time using ASCII art.")
    print("\nLegend:")
    print("  🔴 Immediate Sharer - Shares without thinking")
    print("  🟢 Cautious Sharer - Verifies before sharing")
    print("  🔵 Skeptic - High skepticism, rarely shares")
    print("  🟡 Influencer - High network influence")
    print("  ⚪ Lurker - Reads but rarely shares")
    print("\nNode colors during simulation:")
    print("  Cyan = Received post")
    print("  Green = Shared post")
    print("  Red = Rejected/Flagged post")
    print("\n" + "=" * 60)
    
    run_terminal_visualization(
        num_agents=13,
        num_posts=6,
        animation_speed=0.2
    )
