"""
Demo setup utilities — shared scaffolding for office-mode runner scripts.

This module provides a single place to construct the common demo environment:
- A 9-agent team (via create_demo_team)
- An Office with agents added
- Initial tasks sampled from SAMPLE_TASKS
- A SocialNetwork with preferential attachment
- A Simulation (optionally with Office attached)
- Initial posts injected

Each runner script calls build_demo_simulation() to get the scaffold,
then implements its own tick loop and output formatting.

This module does NOT run any simulation — it only builds the setup.
"""

import random
from typing import Optional

from .agent import Agent
from .post import create_sample_posts
from .network import SocialNetwork
from .simulation import Simulation
from .office import Office, SAMPLE_TASKS
from .demo_team import create_demo_team


def build_demo_simulation(
    num_initial_tasks: int = 5,
    num_initial_posts: int = 3,
    connect_office: bool = False,
    avg_connections: int = 3,
    verbose: bool = False,
    random_seed: Optional[int] = None,
) -> tuple[list[Agent], Office, SocialNetwork, Simulation]:
    """
    Build the common demo scaffolding and return the components.

    Args:
        num_initial_tasks: How many random tasks to add initially.
        num_initial_posts: How many random posts to inject initially.
        connect_office: If True, Simulation is created with office attached
                        (task completions will auto-inject posts).
        avg_connections: Average connections per agent in the network.
        verbose: If True, prints roster, tasks, network stats, and post count.
        random_seed: Optional seed for reproducible random behavior.

    Returns:
        (team, office, network, simulation)
    """
    from .logger import Colors
    colors = Colors()
    c = lambda text, color: f"{color}{text}{colors.ENDC}" if colors.ENDC else text

    # Apply seed at the very start for full reproducibility
    if random_seed is not None:
        random.seed(random_seed)

    # Team
    team = create_demo_team()

    # Office
    office = Office("TechCorp HQ")
    for agent in team:
        office.add_agent(agent)

    # Initial tasks
    initial_tasks = random.sample(SAMPLE_TASKS, min(num_initial_tasks, len(SAMPLE_TASKS)))
    for task in initial_tasks:
        office.add_task(task)

    # Network
    network = SocialNetwork()
    for agent in team:
        network.add_agent(agent)
    network.create_preferential_attachment_network(avg_connections=avg_connections)

    # Simulation
    if connect_office:
        sim = Simulation(
            network=network,
            tick_delay=0,
            on_event=None,
            office=office,
            on_office_event=None,
            random_seed=random_seed,
        )
    else:
        sim = Simulation(network=network, tick_delay=0, random_seed=random_seed)

    # Initial posts
    posts = create_sample_posts()
    selected_posts = random.sample(posts, min(num_initial_posts, len(posts)))
    for post in selected_posts:
        initial_agent = random.choice(team)
        sim.add_post(post, initial_agent)

    # Optional verbose output (matches typical runner prints)
    if verbose:
        # Roster
        print("\n" + "=" * 60)
        print("👥 OFFICE TEAM ROSTER")
        print("=" * 60)
        for agent in team:
            job = agent.job_role.value if agent.job_role else "no role"
            behavior = agent.agent_type.value
            print(f"  {agent.name:12} | {job:18} | {behavior}")
        print()

        # Tasks
        print(c("📋 Adding initial tasks...", colors.HEADER + colors.BOLD))
        for task in initial_tasks:
            print(f"  + {task.title} ({task.task_type.value}, difficulty: {task.difficulty})")
        print(office.get_task_board())
        print()

        # Network
        print(c("🌐 Network created with preferential attachment", colors.BLUE))
        print(f"   Total connections: {network.get_network_stats()['total_connections']}")
        print()

        # Posts
        print(c(f"📰 Added {len(selected_posts)} posts to the network", colors.BLUE))
        print()

    return team, office, network, sim
