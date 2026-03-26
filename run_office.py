#!/usr/bin/env python3
"""
Office Simulation Demo

Demonstrates the office task system with agents working on their jobs
while participating in the information spread network.
"""

import random
from datetime import datetime

from agent_office import (
    Agent, AgentType, JobRole, create_agent_from_type,
    Post, PostCategory, TruthValue, create_sample_posts,
    SocialNetwork, Simulation,
    Office, OfficeTask, TaskType, SAMPLE_TASKS
)
from agent_office.logger import SimulationLogger, Colors
from agent_office.demo_setup import build_demo_simulation


def print_task_board(office: Office):
    """Print the current task board."""
    print(office.get_task_board())
    print()


def run_office_simulation(
    num_ticks: int = 20,
    task_every_n_ticks: int = 3,
    verbose: bool = True
):
    """
    Run an office simulation with both work tasks and info spread.
    
    Args:
        num_ticks: How many simulation ticks to run
        task_every_n_ticks: Add a new task every N ticks
        verbose: Whether to print detailed output
    """
    
    # Setup colors
    colors = Colors()
    c = lambda text, color: f"{color}{text}{colors.ENDC}" if colors.ENDC else text
    
    print(c("\n" + "=" * 70, colors.CYAN + colors.BOLD))
    print(c("   🏢 AGENT OFFICE - WORK SIMULATION", colors.CYAN + colors.BOLD))
    print(c("=" * 70, colors.CYAN + colors.BOLD))
    
    # Shared demo setup (team, office, network, simulation, posts)
    team, office, network, sim = build_demo_simulation(
        num_initial_tasks=5,
        num_initial_posts=3,
        connect_office=False,
        verbose=True,
    )
    
    # Run simulation ticks - always show ALL actions
    print(c("🚀 Starting simulation...", colors.GREEN + colors.BOLD))
    print(c("-" * 70, colors.YELLOW))
    print("\nEach tick shows:")
    print("  📢 Info-spread events (posts being shared/verified/flagged)")
    print("  🔄 Office work in progress")
    print("  ✅ Office task completions")
    print("  📥 New tasks added periodically")
    print("-" * 70)
    
    for tick in range(num_ticks):
        print(c(f"\n[TICK {tick:03d}]", colors.CYAN + colors.BOLD))
        
        # === 1. Add new task periodically ===
        if tick > 0 and tick % task_every_n_ticks == 0:
            new_task = random.choice(SAMPLE_TASKS)
            task_copy = OfficeTask(
                title=new_task.title,
                description=new_task.description,
                task_type=new_task.task_type,
                difficulty=new_task.difficulty
            )
            office.add_task(task_copy)
            print(c(f"  📥 NEW TASK: {task_copy.title} ({task_copy.task_type.value})", colors.YELLOW))
        
        # === 2. Add new post periodically to keep info-spread alive ===
        if tick > 0 and tick % 5 == 0:
            new_post = random.choice(create_sample_posts())
            initial_agent = random.choice(team)
            sim.add_post(new_post, initial_agent)
            print(c(f"  📰 NEW POST by {initial_agent.name}: {new_post.subject[:35]}...", colors.BLUE))
        
        # === 3. Run info-spread tick ===
        events = sim.tick()
        
        # === 4. Run office tick (separate from sim since office not attached) ===
        office_completions = office.tick()
        
        # === 5. Print INFO-SPREAD section ===
        print("\n  📢 INFO-SPREAD:")
        if events:
            for event in events:
                job_role = event.details.get('job_role')
                job_str = f"| {job_role:15}" if job_role else "| no role        "
                behavior = event.behavior.replace('_', ' ').upper()
                print(f"      {event.agent_name:10} {job_str} → {behavior:20} | {event.post_subject[:30]}...")
        else:
            print("      (no activity)")
        
        # === 6. Print OFFICE WORK section ===
        print("\n  🔄 OFFICE WORK:")
        
        # Show in-progress tasks
        in_progress = office.get_in_progress_tasks()
        if in_progress:
            print(f"      In progress ({len(in_progress)} tasks):")
            for task in in_progress[:4]:
                agent = next((a for a in team if a.id == task.assigned_to), None)
                agent_name = agent.name if agent else "?"
                job = agent.job_role.value if agent and agent.job_role else "?"
                print(f"        • {agent_name:10} ({job:12}) → {task.title[:30]} ({task.progress:.0%})")
        else:
            print("      (no tasks in progress)")
        
        # Show completions
        if office_completions:
            print(f"\n      ✅ Completed this tick ({len(office_completions)}):")
            for agent, task, _ in office_completions:
                job = agent.job_role.value if agent.job_role else "?"
                print(f"        • {agent.name:10} | {job:15} → {task.title}")
        else:
            print("      (no completions this tick)")
    
    # Final summary
    print(c("\n" + "=" * 70, colors.CYAN + colors.BOLD))
    print(c("📊 SIMULATION COMPLETE", colors.GREEN + colors.BOLD))
    print(c("=" * 70, colors.CYAN + colors.BOLD))
    
    # Office stats
    stats = office.get_stats()
    print(c("\n📋 Office Statistics:", colors.HEADER + colors.BOLD))
    print(f"   Total tasks: {stats['total_tasks']}")
    print(f"   Completed: {stats['completed']}")
    print(f"   Pending: {stats['pending']}")
    print(f"   Ticks run: {stats['ticks']}")
    
    # Info spread stats
    print(c("\n📢 Information Spread Statistics:", colors.HEADER + colors.BOLD))
    print(f"   Total shares: {sim.stats.total_shares}")
    print(f"   Total flags: {sim.stats.total_flags}")
    print(f"   Posts in network: {len(sim.posts)}")
    
    # Agent activity summary
    print(c("\n👥 Agent Activity Summary:", colors.HEADER + colors.BOLD))
    for agent in sorted(team, key=lambda a: a.name):
        job = agent.job_role.value if agent.job_role else "?"
        tasks_done = len([t for t in office.completed_tasks if t.assigned_to == agent.id])
        print(f"   {agent.name:12} ({job:15}): "
              f"tasks={tasks_done}, shares={len(agent.posts_shared)}, "
              f"seen={len(agent.posts_seen)}")
    
    # Remaining tasks
    print_task_board(office)
    
    return office, sim


def demo_task_assignment():
    """Demo: Manual task assignment and completion."""
    colors = Colors()
    c = lambda text, color: f"{color}{text}{colors.ENDC}" if colors.ENDC else text
    
    print(c("\n" + "=" * 70, Colors.CYAN + Colors.BOLD))
    print(c("   📝 DEMO: Task Assignment & Completion", Colors.CYAN + Colors.BOLD))
    print(c("=" * 70, Colors.CYAN + Colors.BOLD))
    
    # Create a simple team
    dev = create_agent_from_type("dev1", "Alice", AgentType.CAUTIOUS_SHARER, JobRole.DEVELOPER)
    tester = create_agent_from_type("tester1", "Bob", AgentType.SKEPTIC, JobRole.TESTER)
    
    office = Office("Test Office")
    office.add_agent(dev)
    office.add_agent(tester)
    
    # Create specific tasks
    coding_task = OfficeTask(
        title="Implement login feature",
        task_type=TaskType.CODING,
        difficulty=0.6
    )
    testing_task = OfficeTask(
        title="Test authentication flow",
        task_type=TaskType.TESTING,
        difficulty=0.5
    )
    
    office.add_task(coding_task)
    office.add_task(testing_task)
    
    print("\n📋 Initial task board:")
    print_task_board(office)
    
    # Manually assign tasks
    print("📝 Assigning tasks...")
    office.assign_task(coding_task, dev)
    print(f"  ✓ '{coding_task.title}' → {dev.name} ({dev.job_role.value})")
    
    office.assign_task(testing_task, tester)
    print(f"  ✓ '{testing_task.title}' → {tester.name} ({tester.job_role.value})")
    
    print("\n📋 After assignment:")
    print_task_board(office)
    
    # Simulate work
    print("\n⚙️  Simulating work...")
    for i in range(10):
        completed = office.tick()
        if completed:
            for agent, task in completed:
                print(f"  ✅ Tick {i+1}: {agent.name} completed '{task.title}'!")
    
    print("\n📋 Final task board:")
    print_task_board(office)
    
    print(f"\n✅ Demo complete! {len(office.completed_tasks)} tasks finished.")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Office - Work Simulation")
    parser.add_argument(
        "--ticks", "-t",
        type=int,
        default=20,
        help="Number of simulation ticks (default: 20)"
    )
    parser.add_argument(
        "--demo", "-d",
        action="store_true",
        help="Run task assignment demo only"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Less verbose output"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        demo_task_assignment()
    else:
        run_office_simulation(
            num_ticks=args.ticks,
            verbose=not args.quiet
        )


if __name__ == "__main__":
    main()
