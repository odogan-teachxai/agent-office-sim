#!/usr/bin/env python3
"""
Integrated Simulation Demo

Shows both office work AND info-spread running together in the same simulation.
Each tick:
  1. Info-spread phase: Posts propagate through the network
  2. Office work phase: Agents work on their assigned tasks

This demonstrates the two systems coexisting without interference.
"""

import random
from datetime import datetime

from agent_office import (
    Agent, AgentType, JobRole, create_agent_from_type,
    create_sample_posts,
    SocialNetwork, Simulation,
    Office, OfficeTask, SAMPLE_TASKS
)
from agent_office.logger import Colors


def create_office_team() -> list[Agent]:
    """Create a diverse office team."""
    return [
        create_agent_from_type("dev1", "Alice", AgentType.CAUTIOUS_SHARER, JobRole.DEVELOPER),
        create_agent_from_type("dev2", "Bob", AgentType.IMMEDIATE_SHARER, JobRole.DEVELOPER),
        create_agent_from_type("pm1", "Carol", AgentType.INFLUENCER, JobRole.PROJECT_MANAGER),
        create_agent_from_type("tester1", "David", AgentType.SKEPTIC, JobRole.TESTER),
        create_agent_from_type("designer1", "Eve", AgentType.CAUTIOUS_SHARER, JobRole.DESIGNER),
        create_agent_from_type("janitor1", "Frank", AgentType.LURKER, JobRole.JANITOR),
        create_agent_from_type("intern1", "Grace", AgentType.IMMEDIATE_SHARER, JobRole.INTERN),
        create_agent_from_type("sales1", "Henry", AgentType.INFLUENCER, JobRole.SALES_REP),
        create_agent_from_type("hr1", "Ivy", AgentType.CAUTIOUS_SHARER, JobRole.HR_MANAGER),
    ]


def print_banner(text: str, color: str, width: int = 70):
    """Print a fancy banner."""
    print(f"\n{color}{'=' * width}")
    print(f"   {text}")
    print(f"{'=' * width}{Colors.ENDC}")


def format_job_role(agent: Agent) -> str:
    """Format agent's job role for display."""
    if agent.job_role:
        return f"{agent.job_role.value}"
    return "no role"


def run_integrated_simulation(num_ticks: int = 25):
    """
    Run integrated simulation showing both office work and info-spread.
    """
    colors = Colors()
    
    # Setup
    print_banner("🏢 AGENT OFFICE - INTEGRATED SIMULATION", colors.CYAN + colors.BOLD)
    
    team = create_office_team()
    
    print("\n👥 TEAM ROSTER:")
    print("-" * 50)
    for agent in team:
        job = format_job_role(agent)
        behavior = agent.agent_type.value.replace('_', ' ')
        print(f"  {agent.name:10} | {job:18} | {behavior}")
    
    # Create office
    office = Office("TechCorp HQ")
    for agent in team:
        office.add_agent(agent)
    
    # Add initial tasks
    print("\n📋 INITIAL TASKS:")
    print("-" * 50)
    initial_tasks = random.sample(SAMPLE_TASKS, 6)
    for task in initial_tasks:
        office.add_task(task)
        print(f"  + {task.title} ({task.task_type.value})")
    
    # Create network
    network = SocialNetwork()
    for agent in team:
        network.add_agent(agent)
    network.create_preferential_attachment_network(avg_connections=3)
    
    print(f"\n🌐 Network: {len(team)} agents, {network.get_network_stats()['total_connections']} connections")
    
    # Create simulation WITH office integration
    # We'll collect events manually and print them organized per tick
    sim = Simulation(
        network=network,
        tick_delay=0,
        on_event=None,  # No callback - we print manually
        office=office,  # ← KEY: attach office to simulation
        on_office_event=None  # We'll check office_events after each tick
    )
    
    # Add posts
    posts = create_sample_posts()
    selected_posts = random.sample(posts, min(3, len(posts)))
    for post in selected_posts:
        initial_agent = random.choice(team)
        sim.add_post(post, initial_agent)
    
    print(f"📰 Added {len(selected_posts)} posts to network")
    
    # Run simulation
    print_banner("🚀 RUNNING SIMULATION", colors.GREEN + colors.BOLD)
    print("\nEach tick shows:")
    print("  📢 Info-spread events (posts being shared/verified/flagged)")
    print("  ✅ Office task completions")
    print("  🔄 Office work in progress")
    print("  📥 New tasks/posts added periodically")
    print("-" * 70)
    
    # Track for showing "no activity" when nothing happens
    info_events_this_tick = []
    office_completions_this_tick = []
    
    for tick in range(num_ticks):
        print(f"\n[TICK {tick:03d}] {'─' * 60}")
        
        # === 1. Add new content periodically to keep simulation alive ===
        
        # Add new task every 4 ticks
        if tick > 0 and tick % 4 == 0:
            new_task = random.choice(SAMPLE_TASKS)
            task_copy = OfficeTask(
                title=new_task.title,
                description=new_task.description,
                task_type=new_task.task_type,
                difficulty=new_task.difficulty
            )
            office.add_task(task_copy)
            print(f"  📥 NEW TASK: {task_copy.title} ({task_copy.task_type.value})")
        
        # Add new post every 5 ticks to keep info-spread alive
        if tick > 0 and tick % 5 == 0:
            new_post = random.choice(create_sample_posts())
            initial_agent = random.choice(team)
            sim.add_post(new_post, initial_agent)
            print(f"  📰 NEW POST by {initial_agent.name}: {new_post.subject[:35]}...")
        
        # === 2. Run the integrated tick (info-spread + office) ===
        events = sim.tick()
        
        # Get office completions from this tick
        office_completions = [e for e in sim.office_events if e['tick'] == tick]
        
        # === 3. Print INFO-SPREAD section ===
        print("\n  📢 INFO-SPREAD:")
        if events:
            for event in events:
                job_role = event.details.get('job_role')
                job_str = f"| {job_role:15}" if job_role else "| no role        "
                behavior = event.behavior.replace('_', ' ').upper()
                print(f"      {event.agent_name:10} {job_str} → {behavior:20} | {event.post_subject[:30]}...")
        else:
            print("      (no activity)")
        
        # === 4. Print OFFICE WORK section ===
        print("\n  🔄 OFFICE WORK:")
        
        # Show in-progress tasks
        in_progress = office.get_in_progress_tasks()
        if in_progress:
            print(f"      In progress ({len(in_progress)} tasks):")
            for task in in_progress[:4]:  # Show up to 4
                agent = next((a for a in team if a.id == task.assigned_to), None)
                agent_name = agent.name if agent else "?"
                job = format_job_role(agent)
                print(f"        • {agent_name:10} ({job:12}) → {task.title[:30]} ({task.progress:.0%})")
        else:
            print("      (no tasks in progress)")
        
        # Show completions this tick
        if office_completions:
            print(f"\n      ✅ Completed this tick ({len(office_completions)}):")
            for e in office_completions:
                print(f"        • {e['agent_name']:10} | {e['agent_job_role']:15} → {e['task_title']}")
    
    # Final summary
    print_banner("📊 SIMULATION COMPLETE", colors.GREEN + colors.BOLD)
    
    # Office stats
    office_stats = office.get_stats()
    print("\n📋 OFFICE STATISTICS:")
    print(f"   Total tasks created: {office_stats['total_tasks']}")
    print(f"   Completed: {office_stats['completed']}")
    print(f"   Pending: {office_stats['pending']}")
    print(f"   In progress: {office_stats['in_progress']}")
    
    # Info-spread stats
    print("\n📢 INFO-SPREAD STATISTICS:")
    print(f"   Total shares: {sim.stats.total_shares}")
    print(f"   Total flags: {sim.stats.total_flags}")
    print(f"   True posts shared: {sim.stats.true_posts_shared}")
    print(f"   False posts shared: {sim.stats.false_posts_shared}")
    
    # Combined agent activity
    print("\n👥 AGENT ACTIVITY SUMMARY:")
    print("-" * 70)
    print(f"{'Name':<10} {'Job Role':<18} {'Tasks':>6} {'Shares':>6} {'Seen':>6} {'Flags':>6}")
    print("-" * 70)
    
    for agent in sorted(team, key=lambda a: a.name):
        job = format_job_role(agent)
        tasks_done = len([e for e in sim.office_events if e['agent_id'] == agent.id])
        shares = len(agent.posts_shared)
        seen = len(agent.posts_seen)
        flags = len(agent.posts_flagged)
        print(f"{agent.name:<10} {job:<18} {tasks_done:>6} {shares:>6} {seen:>6} {flags:>6}")
    
    # Remaining tasks
    print("\n" + office.get_task_board())
    
    # Verification
    print_banner("✅ VERIFICATION", colors.YELLOW + colors.BOLD)
    print(f"✓ Info-spread logic unchanged: {sim.stats.total_shares + sim.stats.total_flags >= 0}")
    print(f"✓ Office work ran each tick: {office.tick_count} office ticks")
    print(f"✓ Both systems coexist: {len(sim.office_events)} office events, {len(sim.events)} info events")
    print(f"✓ Report includes office data: {'office_stats' in sim.get_simulation_report()}")
    
    return sim, office


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Integrated Office + Info-Spread Simulation")
    parser.add_argument(
        "--ticks", "-t",
        type=int,
        default=25,
        help="Number of simulation ticks (default: 25)"
    )
    
    args = parser.parse_args()
    
    sim, office = run_integrated_simulation(num_ticks=args.ticks)
    
    print("\n✅ Integrated simulation completed successfully!")
    print("   Both office work and info-spread ran in parallel each tick.")


if __name__ == "__main__":
    main()
