#!/usr/bin/env python3
"""
Live Office Simulation - Work Generates News!

This simulation shows the full connected flow:
1. Agents work on tasks
2. When tasks complete, agents post about their accomplishments
3. Posts spread through the network like any other news
4. Other agents react based on their traits (share/verify/ignore/flag)
5. The office feels ALIVE with gossip about work!
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
from agent_office.demo_setup import build_demo_simulation


def print_banner(text: str, color: str, width: int = 70):
    """Print a fancy banner."""
    colors = Colors()
    print(f"\n{color}{'=' * width}")
    print(f"   {text}")
    print(f"{'=' * width}{colors.ENDC}")


def format_job_role(agent: Agent) -> str:
    """Format agent's job role for display."""
    if agent.job_role:
        return f"{agent.job_role.value}"
    return "no role"


def run_live_office_simulation(num_ticks: int = 30):
    """
    Run a live office simulation where work generates news!
    """
    colors = Colors()
    c = lambda text, color: f"{color}{text}{colors.ENDC}"
    
    # Setup
    print_banner("🏢 LIVE OFFICE - Work Generates News!", colors.CYAN + colors.BOLD)
    
    # Shared demo setup (team, office, network, simulation with office attached)
    team, office, network, sim = build_demo_simulation(
        num_initial_tasks=5,
        num_initial_posts=2,
        connect_office=True,  # Office wired — task completions auto-inject posts
        verbose=False,  # We'll print our own UX below
    )
    
    print("\n👥 TEAM ROSTER:")
    print("-" * 60)
    for agent in team:
        job = format_job_role(agent)
        behavior = agent.agent_type.value.replace('_', ' ')
        print(f"  {agent.name:10} | {job:18} | {behavior}")
    
    print("\n📋 INITIAL TASKS:")
    print("-" * 60)
    for task in office.get_pending_tasks()[:5]:
        print(f"  + {task.title} ({task.task_type.value})")
    
    print(f"\n🌐 Network: {len(team)} agents, {network.get_network_stats()['total_connections']} connections")
    
    # Posts already added by build_demo_simulation
    print(f"📰 Added {len(sim.posts)} initial posts")
    
    # Run simulation
    print_banner("🚀 SIMULATION STARTING - Watch Work Become News!", colors.GREEN + colors.BOLD)
    print("\n💡 How it works:")
    print("   1. Agents work on tasks (shown in OFFICE WORK)")
    print("   2. When tasks complete → agents POST about it!")
    print("   3. Posts spread through network (INFO-SPREAD)")
    print("   4. Other agents react based on traits (share/verify/ignore)")
    print("-" * 70)
    
    for tick in range(num_ticks):
        print(f"\n{'─' * 70}")
        print(c(f"[TICK {tick:03d}]", colors.CYAN + colors.BOLD))
        print(f"{'─' * 70}")
        
        # Add new task periodically
        if tick > 0 and tick % 4 == 0:
            new_task = random.choice(SAMPLE_TASKS)
            task_copy = OfficeTask(
                title=new_task.title,
                description=new_task.description,
                task_type=new_task.task_type,
                difficulty=new_task.difficulty
            )
            office.add_task(task_copy)
            print(c(f"  📥 NEW TASK: {task_copy.title}", colors.YELLOW))
        
        # Run the integrated tick
        events = sim.tick()
        
        # Check what happened this tick
        office_completions = [e for e in sim.office_events if e['tick'] == tick]
        work_posts = [p for p in sim.work_posts_generated if p['tick'] == tick]
        
        # === OFFICE WORK SECTION ===
        print("\n  🏢 OFFICE WORK:")
        
        in_progress = office.get_in_progress_tasks()
        if in_progress:
            print(f"      In progress ({len(in_progress)} tasks):")
            for task in in_progress[:3]:
                agent = next((a for a in team if a.id == task.assigned_to), None)
                if agent:
                    print(f"        • {agent.name:10} ({format_job_role(agent):12}) → {task.title[:28]} ({task.progress:.0%})")
        
        if office_completions:
            print(f"\n      ✅ TASKS COMPLETED ({len(office_completions)}):")
            for e in office_completions:
                print(f"        ✓ {e['agent_name']:10} ({e['agent_job_role']:12}) finished: {e.get('task_title', 'Unknown')}")
        
        # === WORK POSTS GENERATED ===
        if work_posts:
            print("\n  📝 WORK POSTS CREATED (Task completions → News!):")
            for wp in work_posts:
                print(f"      🎉 {wp['agent_name']:10} posted: \"{wp['post_subject'][:40]}...\"")
        
        # === INFO-SPREAD SECTION ===
        print("\n  📢 INFO-SPREAD (Posts spreading + reactions):")
        
        if events:
            for event in events:
                job_role = event.details.get('job_role', 'unknown')
                behavior = event.behavior.replace('_', ' ').upper()
                post_subj = event.post_subject[:30]
                
                # Check if this is a work-generated post
                is_work_post = any(wp['post_id'] == event.post_id for wp in sim.work_posts_generated)
                work_indicator = "💼 " if is_work_post else "   "
                
                print(f"      {work_indicator}{event.agent_name:10} ({job_role:12}) → {behavior:20} | \"{post_subj}...\"")
                
                # Add commentary for interesting reactions
                if is_work_post:
                    if event.behavior == "share_immediately":
                        print(f"          └─ 💬 \"Great work! Everyone should see this!\"")
                    elif event.behavior == "flag_as_suspicious":
                        print(f"          └─ 💬 \"Wait, did they actually finish that?\"")
                    elif event.behavior == "verify_then_share":
                        print(f"          └─ 💬 \"Let me check if this is true first...\"")
        else:
            print("      (no info-spread activity this tick)")
        
        # Show work post spread summary periodically
        if tick % 5 == 0 and tick > 0:
            work_post_stats = []
            for wp in sim.work_posts_generated:
                post = sim.posts.get(wp['post_id'])
                if post:
                    work_post_stats.append(f"{wp['agent_name']}'s post: {post.share_count} shares")
            
            if work_post_stats:
                print("\n  📊 WORK POST SPREAD SUMMARY:")
                for stat in work_post_stats[-3:]:  # Show last 3
                    print(f"      📈 {stat}")
    
    # Final summary
    print_banner("📊 SIMULATION COMPLETE", colors.GREEN + colors.BOLD)
    
    # Stats
    print("\n📋 OFFICE STATISTICS:")
    office_stats = office.get_stats()
    print(f"   Total tasks: {office_stats['total_tasks']}")
    print(f"   Completed: {office_stats['completed']}")
    
    print("\n📝 WORK-GENERATED POSTS:")
    print(f"   Total work posts created: {len(sim.work_posts_generated)}")
    for wp in sim.work_posts_generated:
        post = sim.posts.get(wp['post_id'])
        if post:
            print(f"   • \"{wp['post_subject'][:40]}...\" by {wp['agent_name']} → {post.share_count} shares, {post.reach_count} reach")
    
    print("\n📢 INFO-SPREAD STATISTICS:")
    print(f"   Total shares: {sim.stats.total_shares}")
    print(f"   Total flags: {sim.stats.total_flags}")
    
    print("\n👥 AGENT ACTIVITY:")
    print(f"{'Name':<10} {'Job':<15} {'Tasks':>6} {'Posts':>6} {'Shares':>6}")
    print("-" * 50)
    for agent in sorted(team, key=lambda a: a.name):
        tasks = len([e for e in sim.office_events if e['agent_id'] == agent.id])
        posts_created = len([p for p in sim.work_posts_generated if p['agent_id'] == agent.id])
        shares = len(agent.posts_shared)
        job = format_job_role(agent)
        print(f"{agent.name:<10} {job:<15} {tasks:>6} {posts_created:>6} {shares:>6}")
    
    print("\n✅ The office is ALIVE! Work generates news, news spreads, agents gossip!")
    return sim, office


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Live Office - Work Generates News!")
    parser.add_argument(
        "--ticks", "-t",
        type=int,
        default=30,
        help="Number of simulation ticks (default: 30)"
    )
    
    args = parser.parse_args()
    
    run_live_office_simulation(num_ticks=args.ticks)


if __name__ == "__main__":
    main()
