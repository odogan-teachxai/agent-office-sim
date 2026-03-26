"""
Demo team factory — shared 9-agent office roster.

This module provides a single canonical definition of the demo office team
used by office-mode runner scripts. The team composition, ordering, IDs,
names, agent types, and job roles must NOT be changed without updating
all callers.

Usage:
    from agent_office.demo_team import create_demo_team
    team = create_demo_team()

The module is importable as part of the agent_office package, and also
works when run directly as a script (python3 agent_office/demo_team.py).
"""

# Ensure this module works whether imported as part of the package
# or run directly as a script (handles different sys.path contexts).
import sys
import os
try:
    from agent_office.agent import Agent, AgentType, JobRole, create_agent_from_type
except ModuleNotFoundError:
    # Running directly (e.g., python3 agent_office/demo_team.py)
    # Add repo root to sys.path so agent_office package is discoverable.
    _repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from agent_office.agent import Agent, AgentType, JobRole, create_agent_from_type


def create_demo_team() -> list[Agent]:
    """
    Create the canonical 9-agent office demo team.

    Agents:
        dev1/Alice      (CAUTIOUS_SHARER, DEVELOPER)
        dev2/Bob        (IMMEDIATE_SHARER, DEVELOPER)
        pm1/Carol       (INFLUENCER, PROJECT_MANAGER)
        tester1/David   (SKEPTIC, TESTER)
        designer1/Eve   (CAUTIOUS_SHARER, DESIGNER)
        janitor1/Frank  (LURKER, JANITOR)
        intern1/Grace   (IMMEDIATE_SHARER, INTERN)
        sales1/Henry    (INFLUENCER, SALES_REP)
        hr1/Ivy         (CAUTIOUS_SHARER, HR_MANAGER)

    Returns:
        List of 9 Agent objects in the above order.
    """
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
