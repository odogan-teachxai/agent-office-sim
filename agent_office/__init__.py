"""
Agent Office - Social Network Information Spread Simulation

A simulation system that models how information spreads through a social network,
tracking user behaviors, post characteristics, and spread patterns.

Features:
- Agent-based simulation with diverse user behaviors
- Post characteristics including truth value and emotional intensity
- Early dissemination tracking for ML analysis
- Dataset generation pipeline for misinformation detection
- Simple ML models for classification
- Real-time visualization of network and post spreading (requires tkinter)
- Terminal-based visualization (no dependencies)
- Full TUI application with model comparison
"""

__version__ = "2.0.0"
__author__ = "Agent Office Team"

from .agent import Agent, AgentBehavior, AgentType, JobRole, create_agent_from_type
from .post import Post, PostCategory, TruthValue, create_sample_posts
from .network import SocialNetwork
from .simulation import Simulation, create_default_simulation
from .logger import SimulationLogger
from .pipeline import DataGenerationPipeline
from .tui_app import TUIApp, run_tui_app
from .terminal_viz import TerminalVisualizer, run_terminal_visualization
from .office import (
    Office, OfficeTask, TaskType, TaskStatus, SAMPLE_TASKS,
    Product, ProductStatus, SAMPLE_PRODUCTS
)

# Optional GUI visualization (requires tkinter)
try:
    from .visualization import SimulationVisualizer, create_visualization
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    SimulationVisualizer = None
    create_visualization = None

__all__ = [
    # Core simulation
    "Agent",
    "AgentBehavior", 
    "AgentType",
    "JobRole",
    "create_agent_from_type",
    "Post",
    "PostCategory",
    "TruthValue",
    "create_sample_posts",
    "SocialNetwork",
    "Simulation",
    "create_default_simulation",
    "SimulationLogger",
    # Office simulation
    "Office",
    "OfficeTask",
    "TaskType",
    "TaskStatus",
    "SAMPLE_TASKS",
    "Product",
    "ProductStatus",
    "SAMPLE_PRODUCTS",
    # ML Pipeline
    "DataGenerationPipeline",
    # Visualization
    "VISUALIZATION_AVAILABLE",
    "SimulationVisualizer",
    "create_visualization",
    "TerminalVisualizer",
    "run_terminal_visualization",
    # TUI Application
    "TUIApp",
    "run_tui_app",
]
