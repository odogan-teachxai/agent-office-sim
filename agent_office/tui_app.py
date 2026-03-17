#!/usr/bin/env python3
"""
TUI Application for Agent Office - Terminal User Interface

A complete terminal-based application with:
- Network visualization
- Real-time simulation
- Model comparison with ASCII plots
- Interactive controls

Uses curses for proper terminal handling.
"""

import curses
import time
import math
import random
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict

from .agent import Agent, AgentType, AgentBehavior, create_agent_from_type
from .post import Post, create_sample_posts
from .network import SocialNetwork
from .simulation import Simulation
from .ml.ml_pipeline import MLPipeline, TrainingConfig, LogisticRegressionModel, SVMModel
from .ml.dataset_builder import DatasetBuilder
from .ml.feature_extractor import FeatureExtractor
from .ml.data_collector import EarlyDisseminationTracker


# Color pairs for curses
COLOR_PAIRS = {
    'default': 1,
    'red': 2,
    'green': 3,
    'yellow': 4,
    'blue': 5,
    'magenta': 6,
    'cyan': 7,
    'white': 8,
    'black': 9,
    'highlight': 10,
}


@dataclass
class AgentNode:
    """Visual representation of an agent in the network."""
    agent: Agent
    x: int
    y: int
    state: str = 'default'


class TUIApp:
    """
    Terminal User Interface Application for Agent Office.
    
    Features:
    - Interactive network visualization
    - Real-time simulation with controls
    - Model training and comparison
    - ASCII-based plots and charts
    """
    
    def __init__(self):
        """Initialize the TUI application."""
        self.stdscr = None
        self.running = False
        self.current_view = 'main'  # main, simulation, model_comparison
        
        # Simulation components
        self.network: Optional[SocialNetwork] = None
        self.simulation: Optional[Simulation] = None
        self.agent_nodes: Dict[str, AgentNode] = {}
        
        # Model comparison
        self.model_results: Optional[Dict] = None
        self.dataset_builder: Optional[DatasetBuilder] = None
        
        # UI state
        self.selected_option = 0
        self.message = ""
        self.message_color = 'white'
        
        # Stats
        self.stats = {
            'tick': 0,
            'shares': 0,
            'reach': 0,
            'flags': 0,
            'true_posts': 0,
            'false_posts': 0,
        }
        
        self.behavior_counts = defaultdict(int)
        self.current_post: Optional[Post] = None
        
    def run(self):
        """Main entry point for the TUI application."""
        curses.wrapper(self._main_loop)
    
    def _main_loop(self, stdscr):
        """Main application loop."""
        self.stdscr = stdscr
        
        # Setup curses
        self._setup_curses()
        
        self.running = True
        
        while self.running:
            try:
                # Render current view
                if self.current_view == 'main':
                    self._render_main_menu()
                elif self.current_view == 'simulation':
                    self._render_simulation()
                    # Auto-run one step per frame if simulation active
                    if self.simulation and (self.simulation.pending_shares or self.simulation.current_tick < 50):
                        self._run_simulation_step()
                        time.sleep(0.05)  # Small delay for visibility
                elif self.current_view == 'model_comparison':
                    self._render_model_comparison()
                
                # Handle input
                self._handle_input()
                
            except Exception as e:
                self._show_message(f"Error: {str(e)}", 'red')
    
    def _setup_curses(self):
        """Setup curses configuration."""
        curses.curs_set(0)  # Hide cursor
        self.stdscr.timeout(100)  # Wait up to 100ms for input (prevents busy loop)
        self.stdscr.keypad(True)
        
        # Initialize colors
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            
            # Define color pairs
            curses.init_pair(1, curses.COLOR_WHITE, -1)      # default
            curses.init_pair(2, curses.COLOR_RED, -1)        # red
            curses.init_pair(3, curses.COLOR_GREEN, -1)      # green
            curses.init_pair(4, curses.COLOR_YELLOW, -1)     # yellow
            curses.init_pair(5, curses.COLOR_BLUE, -1)      # blue
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)   # magenta
            curses.init_pair(7, curses.COLOR_CYAN, -1)      # cyan
            curses.init_pair(8, curses.COLOR_WHITE, -1)     # white
            curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_CYAN)  # highlight
    
    def _get_color(self, color_name: str) -> int:
        """Get curses color pair for a color name."""
        return curses.color_pair(COLOR_PAIRS.get(color_name, 1))
    
    def _clear(self):
        """Clear the screen (use erase for less flickering)."""
        self.stdscr.erase()
    
    def _draw_box(self, y: int, x: int, height: int, width: int, title: str = "", color: str = 'default'):
        """Draw a box with optional title."""
        cp = self._get_color(color)
        
        # Top border
        self.stdscr.addch(y, x, '┌', cp)
        for i in range(width - 2):
            self.stdscr.addch(y, x + 1 + i, '─', cp)
        self.stdscr.addch(y, x + width - 1, '┐', cp)
        
        # Sides
        for i in range(height - 2):
            self.stdscr.addch(y + 1 + i, x, '│', cp)
            self.stdscr.addch(y + 1 + i, x + width - 1, '│', cp)
        
        # Bottom border
        self.stdscr.addch(y + height - 1, x, '└', cp)
        for i in range(width - 2):
            self.stdscr.addch(y + height - 1, x + 1 + i, '─', cp)
        self.stdscr.addch(y + height - 1, x + width - 1, '┘', cp)
        
        # Title
        if title:
            title_str = f" {title} "
            self.stdscr.addstr(y, x + 2, title_str, cp | curses.A_BOLD)
    
    def _write(self, y: int, x: int, text: str, color: str = 'default', bold: bool = False):
        """Write text at position."""
        try:
            cp = self._get_color(color)
            if bold:
                cp |= curses.A_BOLD
            self.stdscr.addstr(y, x, text, cp)
        except curses.error:
            pass
    
    def _show_message(self, msg: str, color: str = 'white'):
        """Show a message at the bottom of screen."""
        self.message = msg
        self.message_color = color
    
    # ==================== MAIN MENU ====================
    
    def _render_main_menu(self):
        """Render the main menu."""
        self._clear()
        
        height, width = self.stdscr.getmaxyx()
        
        # Title
        title = "🏢 AGENT OFFICE - Social Network Simulation"
        self._write(2, (width - len(title)) // 2, title, 'cyan', bold=True)
        
        # Subtitle
        subtitle = "Misinformation Spread Analysis & ML Training Platform"
        self._write(4, (width - len(subtitle)) // 2, subtitle, 'white')
        
        # Menu options
        options = [
            ("▶ Run Simulation", "Watch information spread through the network"),
            ("🤖 Train & Compare Models", "Train LR and SVM, compare performance"),
            ("📊 View Model Results", "View training history and plots"),
            ("❓ Help", "Show usage instructions"),
            ("✖ Exit", "Exit the application"),
        ]
        
        menu_y = 8
        menu_x = (width - 50) // 2
        
        self._draw_box(menu_y - 2, menu_x - 2, len(options) * 2 + 5, 54, "Main Menu")
        
        for i, (option, desc) in enumerate(options):
            y = menu_y + i * 2
            
            # Highlight selected
            if i == self.selected_option:
                self._write(y, menu_x, "→ ", 'yellow')
                self._write(y, menu_x + 3, option, 'cyan', bold=True)
                self._write(y + 1, menu_x + 3, f"  {desc}", 'cyan')
            else:
                self._write(y, menu_x, "  ", 'white')
                self._write(y, menu_x + 3, option, 'white')
                self._write(y + 1, menu_x + 3, f"  {desc}", 'white')
        
        # Footer
        self._write(height - 3, (width - 40) // 2, "Use ↑↓ to navigate, Enter to select", 'white')
        
        # Message
        if self.message:
            self._write(height - 1, (width - len(self.message)) // 2, self.message, self.message_color)
        
        self.stdscr.refresh()
    
    # ==================== SIMULATION VIEW ====================
    
    def _init_simulation(self):
        """Initialize the simulation."""
        self.network = SocialNetwork()
        
        # Create agents
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
            self.network.add_agent(agent)
            agents.append(agent)
        
        # Create connections
        self.network.create_preferential_attachment_network(avg_connections=3)
        
        # Calculate node positions
        self._calculate_node_positions()
        
        # Create simulation
        self.simulation = Simulation(self.network, tick_delay=0.1)
        
        # Add posts
        all_posts = create_sample_posts()
        posts_to_use = random.sample(all_posts, min(6, len(all_posts)))
        
        influencers = [a for a in agents if a.agent_type == AgentType.INFLUENCER]
        
        for post in posts_to_use:
            if influencers and random.random() < 0.6:
                initial_agent = random.choice(influencers)
            else:
                initial_agent = random.choice(agents)
            self.simulation.add_post(post, initial_agent)
        
        # Reset stats
        self.stats = {k: 0 for k in self.stats}
        self.behavior_counts = defaultdict(int)
        
        self._show_message("Simulation initialized! Press SPACE to start/pause, Q to quit", 'green')
    
    def _calculate_node_positions(self):
        """Calculate agent node positions for visualization."""
        if not self.network:
            return
        
        height, width = self.stdscr.getmaxyx()
        
        # Network area dimensions
        net_width = width - 35  # Leave space for stats panel
        net_height = height - 8
        
        center_x = net_width // 2
        center_y = net_height // 2
        radius = min(center_x, center_y) - 4
        
        agents = self.network.get_all_agents()
        n = len(agents)
        
        for i, agent in enumerate(agents):
            angle = 2 * math.pi * i / n - math.pi / 2
            x = int(center_x + radius * math.cos(angle))
            y = int(center_y + radius * math.sin(angle) * 0.5)  # Elliptical for better terminal display
            
            self.agent_nodes[agent.id] = AgentNode(
                agent=agent,
                x=max(2, min(net_width - 2, x)),
                y=max(2, min(net_height - 2, y))
            )
    
    def _render_simulation(self):
        """Render the simulation view."""
        self._clear()
        
        height, width = self.stdscr.getmaxyx()
        
        # Header
        self._write(0, 2, "🏢 AGENT OFFICE - Live Simulation", 'cyan', bold=True)
        self._write(0, width - 25, "Press Q to return", 'yellow')
        
        # Draw stats panel
        self._draw_stats_panel(width - 32, 2)
        
        # Draw network
        self._draw_network()
        
        # Draw current post info
        self._draw_post_info(height - 6)
        
        # Draw legend
        self._draw_legend(height - 6, width - 32)
        
        # Message
        if self.message:
            self._write(height - 1, 2, self.message, self.message_color)
        
        self.stdscr.refresh()
    
    def _draw_stats_panel(self, x: int, y: int):
        """Draw the statistics panel."""
        self._draw_box(y, x, 18, 30, "📊 Statistics")
        
        stats_lines = [
            (f"Tick: {self.stats['tick']}", 'white'),
            (f"Reach: {self.stats['reach']}", 'white'),
            (f"Shares: {self.stats['shares']}", 'green'),
            (f"Flags: {self.stats['flags']}", 'red'),
        ]
        
        for i, (text, color) in enumerate(stats_lines):
            self._write(y + 2 + i, x + 2, text, color)
        
        # Truth values
        self._write(y + 7, x + 2, "─── Posts ───", 'white')
        self._write(y + 8, x + 2, f"✓ True: {self.stats['true_posts']}", 'green')
        self._write(y + 9, x + 2, f"✗ False: {self.stats['false_posts']}", 'red')
        
        # Behaviors
        shared = self.behavior_counts.get('share_immediately', 0) + \
                 self.behavior_counts.get('verify_then_share', 0)
        rejected = self.behavior_counts.get('ignore', 0) + \
                   self.behavior_counts.get('verify_then_ignore', 0)
        flagged = self.behavior_counts.get('flag_as_suspicious', 0)
        
        self._write(y + 11, x + 2, "─── Behaviors ───", 'white')
        self._write(y + 12, x + 2, f"📤 Shared: {shared}", 'green')
        self._write(y + 13, x + 2, f"❌ Rejected: {rejected}", 'red')
        self._write(y + 14, x + 2, f"🚩 Flagged: {flagged}", 'magenta')
    
    def _draw_network(self):
        """Draw the network graph."""
        if not self.network or not self.agent_nodes:
            return
        
        height, width = self.stdscr.getmaxyx()
        net_width = width - 35
        
        # Draw edges (simplified)
        for agent_id, connections in self.network.connections.items():
            node1 = self.agent_nodes.get(agent_id)
            if not node1:
                continue
            
            for conn in connections:
                node2 = self.agent_nodes.get(conn.followee_id)
                if not node2:
                    continue
                
                # Draw simple line between nodes
                self._draw_simple_line(node1.x, node1.y, node2.x, node2.y, 'white')
        
        # Draw nodes
        for agent_id, node in self.agent_nodes.items():
            self._draw_agent_node(node)
    
    def _draw_simple_line(self, x1: int, y1: int, x2: int, y2: int, color: str):
        """Draw a simple line between two points."""
        # Simple Bresenham-ish line
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        
        if dx > dy:
            steps = dx
        else:
            steps = dy
        
        if steps == 0:
            return
        
        x_inc = (x2 - x1) / steps
        y_inc = (y2 - y1) / steps
        
        for i in range(steps):
            x = int(x1 + x_inc * i)
            y = int(y1 + y_inc * i)
            
            if 0 <= y < 30 and 0 <= x < 100:
                try:
                    self.stdscr.addch(y + 2, x + 2, '·', self._get_color('white'))
                except:
                    pass
    
    def _draw_agent_node(self, node: AgentNode):
        """Draw an agent node."""
        # Determine color based on type and state
        type_colors = {
            AgentType.IMMEDIATE_SHARER: 'red',
            AgentType.CAUTIOUS_SHARER: 'green',
            AgentType.SKEPTIC: 'blue',
            AgentType.INFLUENCER: 'yellow',
            AgentType.LURKER: 'white',
        }
        
        state_colors = {
            'default': type_colors.get(node.agent.agent_type, 'white'),
            'received': 'cyan',
            'shared': 'green',
            'rejected': 'red',
            'flagged': 'magenta',
        }
        
        color = state_colors.get(node.state, 'white')
        
        # Draw node character
        if node.agent.agent_type == AgentType.INFLUENCER:
            char = '◆'
        else:
            char = '●' if node.state == 'shared' else '○'
        
        y = node.y + 2
        x = node.x + 2
        
        try:
            self.stdscr.addch(y, x, char, self._get_color(color) | curses.A_BOLD)
            
            # Draw name below
            name = node.agent.name[:4]
            self._write(y + 1, x - 1, name, 'white')
        except:
            pass
    
    def _draw_post_info(self, y: int):
        """Draw current post information."""
        height, width = self.stdscr.getmaxyx()
        
        self._draw_box(y, 2, 5, width - 40, "📬 Current Post")
        
        if self.current_post:
            truth_color = {
                'true': 'green',
                'false': 'red',
                'mixed': 'yellow',
                'unverified': 'magenta'
            }.get(self.current_post.truth_value.value, 'white')
            
            truth_icon = {'true': '✓', 'false': '✗', 'mixed': '◐', 'unverified': '?'}
            icon = truth_icon.get(self.current_post.truth_value.value, '?')
            
            subject = self.current_post.subject[:50]
            if len(self.current_post.subject) > 50:
                subject += "..."
            
            self._write(y + 2, 4, f"{icon} {subject}", truth_color, bold=True)
            self._write(y + 3, 4, 
                       f"Shares: {self.current_post.share_count} | Reach: {self.current_post.reach_count}",
                       'white')
        else:
            self._write(y + 2, 4, "Waiting for post...", 'white')
    
    def _draw_legend(self, y: int, x: int):
        """Draw the legend."""
        self._draw_box(y, x, 5, 30, "📋 Legend")
        
        self._write(y + 2, x + 2, "○ Node  ◆ Influencer", 'white')
        self._write(y + 3, x + 2, "Green=Shared Red=Flag", 'white')
    
    def _run_simulation_step(self):
        """Run a single simulation step."""
        if not self.simulation:
            return
        
        events = self.simulation.tick()
        
        for event in events:
            # Update current post
            post = self.simulation.posts.get(event.post_id)
            if post:
                self.current_post = post
            
            # Update agent state
            state_map = {
                'share_immediately': 'shared',
                'verify_then_share': 'shared',
                'verify_then_ignore': 'rejected',
                'ignore': 'rejected',
                'flag_as_suspicious': 'flagged',
            }
            
            state = state_map.get(event.behavior, 'default')
            if event.agent_id in self.agent_nodes:
                self.agent_nodes[event.agent_id].state = state
            
            # Update behavior counts
            self.behavior_counts[event.behavior] += 1
        
        # Update stats
        self._update_stats()
        
        return events
    
    def _update_stats(self):
        """Update statistics from simulation."""
        if not self.simulation:
            return
        
        truth_counts = {'true': 0, 'false': 0}
        total_shares = 0
        total_reach = 0
        total_flags = 0
        
        for post in self.simulation.posts.values():
            truth_counts[post.truth_value.value] = truth_counts.get(post.truth_value.value, 0) + 1
            total_shares += post.share_count
            total_reach += post.reach_count
            total_flags += post.flagged_count
        
        self.stats = {
            'tick': self.simulation.current_tick,
            'shares': total_shares,
            'reach': total_reach,
            'flags': total_flags,
            'true_posts': truth_counts.get('true', 0),
            'false_posts': truth_counts.get('false', 0),
        }
    
    # ==================== MODEL COMPARISON VIEW ====================
    
    def _train_models(self):
        """Train models and show comparison."""
        self._show_message("Training models... This may take a moment.", 'yellow')
        self._render_training_progress()
        
        try:
            # Generate dataset
            feature_extractor = FeatureExtractor(early_window_ticks=10)
            self.dataset_builder = DatasetBuilder(feature_extractor=feature_extractor, random_seed=42)
            
            # Run simulations to generate data
            tracker = EarlyDisseminationTracker(early_window_ticks=10)
            
            for sim_num in range(30):  # 30 simulations for training
                self._run_data_simulation(tracker, sim_num)
                
                # Update progress
                progress = int((sim_num + 1) / 30 * 100)
                self._render_training_progress(progress, "Generating dataset...")
            
            # Build dataset
            self.dataset_builder.add_records_from_tracker(tracker)
            
            # Train models
            config = TrainingConfig(
                learning_rate=0.01,
                num_epochs=20,
                regularization=0.01,
                random_seed=42,
                batch_size=32,
                validation_split=0.15
            )
            
            ml_pipeline = MLPipeline(config, feature_extractor)
            
            # Train and compare (train_and_compare creates trainer internally)
            results = ml_pipeline.train_and_compare(self.dataset_builder, verbose=False)
            
            self.model_results = {
                'training_results': results['training_results'],
                'evaluation_results': results['evaluation_results'],
                'comparison_report': ml_pipeline.comparison_report
            }
            
            self._show_message("Training complete! Loading results...", 'green')
            self._render_training_progress(100, "Complete!")
            time.sleep(0.5)  # Brief pause to show completion
            self.current_view = 'model_comparison'
            
        except Exception as e:
            self._show_message(f"Error during training: {str(e)}", 'red')
    
    def _run_data_simulation(self, tracker: EarlyDisseminationTracker, seed: int):
        """Run a single simulation for data generation."""
        random.seed(seed)
        
        network = SocialNetwork()
        agents = []
        
        for i in range(13):
            agent_type = list(AgentType)[i % 5]
            agent = create_agent_from_type(f"agent_{i}", f"Agent_{i}", agent_type)
            network.add_agent(agent)
            tracker.register_agent(agent.id, agent.agent_type)
            agents.append(agent)
        
        network.create_preferential_attachment_network(avg_connections=4)
        
        simulation = Simulation(network, tick_delay=0.01)
        
        posts = create_sample_posts()
        for post in random.sample(posts, min(6, len(posts))):
            tracker.register_post(post)
            simulation.add_post(post, random.choice(agents))
        
        simulation.run(max_ticks=100, stop_when_idle=True, idle_threshold=5)
        
        # Record events
        for event in simulation.events:
            tracker.record_event(
                tick=event.tick,
                post_id=event.post_id,
                agent_id=event.agent_id,
                agent_name=event.agent_name,
                behavior=event.behavior,
                confidence=event.details.get('confidence', 0.5),
                trust_modifier=event.details.get('trust_modifier', 0.5)
            )
    
    def _render_training_progress(self, progress: int = 0, status: str = "Initializing..."):
        """Render training progress screen."""
        self._clear()
        
        height, width = self.stdscr.getmaxyx()
        
        # Title
        self._write(4, (width - 30) // 2, "🤖 Training Models", 'cyan', bold=True)
        
        # Progress bar
        bar_width = 50
        bar_x = (width - bar_width) // 2
        bar_y = 8
        
        filled = int(bar_width * progress / 100)
        
        self._write(bar_y - 1, bar_x, status, 'white')
        
        # Draw progress bar
        self._write(bar_y, bar_x, "[" + "=" * filled + " " * (bar_width - filled) + "]", 'green')
        self._write(bar_y + 1, bar_x + bar_width // 2 - 4, f"{progress}%", 'white')
        
        # Info
        info_lines = [
            "Generating training data from simulations...",
            "Training Logistic Regression and SVM models...",
            "Comparing model performance...",
        ]
        
        for i, line in enumerate(info_lines):
            color = 'green' if i <= progress // 33 else 'white'
            self._write(12 + i, (width - len(line)) // 2, line, color)
        
        self.stdscr.refresh()
    
    def _render_model_comparison(self):
        """Render the model comparison view."""
        self._clear()
        
        height, width = self.stdscr.getmaxyx()
        
        # Header
        self._write(0, 2, "📊 Model Comparison Results", 'cyan', bold=True)
        self._write(0, width - 25, "Press Q to return", 'yellow')
        
        if not self.model_results:
            self._write(5, (width - 30) // 2, "No model results available.", 'red')
            self._write(7, (width - 40) // 2, "Press T to train models first.", 'white')
            self.stdscr.refresh()
            return
        
        # Draw comparison boxes
        self._draw_model_stats_box(2, 2, "Logistic Regression", 
                                   self.model_results['evaluation_results'].get('Logistic Regression', {}))
        
        self._draw_model_stats_box(2, width // 2, "SVM",
                                   self.model_results['evaluation_results'].get('SVM', {}))
        
        # Draw comparison chart
        self._draw_comparison_chart(14, 2)
        
        # Draw training history plot
        self._draw_training_plot(22, 2)
        
        # Summary
        comparison = self.model_results.get('comparison_report', {})
        best_model = comparison.get('best_model', 'N/A')
        
        self._write(height - 3, 2, f"Best Model: {best_model}", 'green', bold=True)
        
        self.stdscr.refresh()
    
    def _draw_model_stats_box(self, y: int, x: int, model_name: str, metrics: Dict):
        """Draw a model statistics box."""
        width = 40
        self._draw_box(y, x, 11, width, model_name)
        
        if not metrics:
            self._write(y + 2, x + 2, "No data available", 'red')
            return
        
        stats = [
            ("Accuracy", f"{metrics.get('accuracy', 0):.1%}", 'green'),
            ("Precision", f"{metrics.get('precision', 0):.1%}", 'cyan'),
            ("Recall", f"{metrics.get('recall', 0):.1%}", 'cyan'),
            ("F1 Score", f"{metrics.get('f1_score', 0):.1%}", 'yellow'),
            ("AUC-ROC", f"{metrics.get('auc_roc', 0):.1%}", 'magenta'),
        ]
        
        for i, (name, value, color) in enumerate(stats):
            self._write(y + 2 + i, x + 2, f"{name}:", 'white')
            self._write(y + 2 + i, x + 20, value, color, bold=True)
        
        # Confusion matrix
        cm = metrics.get('confusion_matrix', {})
        self._write(y + 8, x + 2, f"TP:{cm.get('true_positives', 0)} TN:{cm.get('true_negatives', 0)}", 'green')
        self._write(y + 9, x + 2, f"FP:{cm.get('false_positives', 0)} FN:{cm.get('false_negatives', 0)}", 'red')
    
    def _draw_comparison_chart(self, y: int, x: int):
        """Draw ASCII bar chart comparing models."""
        height, width = self.stdscr.getmaxyx()
        
        self._draw_box(y, x, 7, width - 4, "📈 Accuracy Comparison")
        
        if not self.model_results:
            return
        
        lr_acc = self.model_results['evaluation_results'].get('Logistic Regression', {}).get('accuracy', 0)
        svm_acc = self.model_results['evaluation_results'].get('SVM', {}).get('accuracy', 0)
        
        # Draw bars
        max_bar_width = 30
        
        lr_bar = int(lr_acc * max_bar_width)
        svm_bar = int(svm_acc * max_bar_width)
        
        self._write(y + 2, x + 2, "LR  [" + "█" * lr_bar + " " * (max_bar_width - lr_bar) + f"] {lr_acc:.1%}", 'green')
        self._write(y + 3, x + 2, "SVM [" + "█" * svm_bar + " " * (max_bar_width - svm_bar) + f"] {svm_acc:.1%}", 'cyan')
        
        # Difference
        diff = lr_acc - svm_acc
        if diff > 0:
            self._write(y + 5, x + 2, f"Logistic Regression is better by {diff:.1%}", 'green')
        elif diff < 0:
            self._write(y + 5, x + 2, f"SVM is better by {abs(diff):.1%}", 'cyan')
        else:
            self._write(y + 5, x + 2, "Models have equal accuracy", 'yellow')
    
    def _draw_training_plot(self, y: int, x: int):
        """Draw ASCII training history plot."""
        height, width = self.stdscr.getmaxyx()
        
        self._draw_box(y, x, 8, width - 4, "📉 Training History")
        
        if not self.model_results or 'training_results' not in self.model_results:
            return
        
        # Get training history
        lr_history = self.model_results['training_results'].get('Logistic Regression', {}).get('training_history', [])
        svm_history = self.model_results['training_results'].get('SVM', {}).get('training_history', [])
        
        if not lr_history and not svm_history:
            return
        
        # Draw axes
        plot_width = width - 10
        plot_height = 4
        
        self._write(y + 2, x + 4, "Accuracy", 'white')
        
        # Draw plot area
        for row in range(plot_height):
            self._write(y + 3 + row, x + 2, "│", 'white')
        
        self._write(y + 3 + plot_height, x + 2, "└" + "─" * (plot_width - 4), 'white')
        self._write(y + 3 + plot_height + 1, x + 4, "Epoch", 'white')
        
        # Plot points
        if lr_history:
            max_epochs = len(lr_history)
            for i, epoch_data in enumerate(lr_history):
                col = x + 4 + int(i * (plot_width - 8) / max_epochs)
                acc = epoch_data.get('train_accuracy', 0)
                row = y + 3 + plot_height - int(acc * plot_height)
                
                if 0 <= row < height and 0 <= col < width:
                    try:
                        self.stdscr.addch(row, col, '●', self._get_color('green'))
                    except:
                        pass
        
        if svm_history:
            max_epochs = len(svm_history)
            for i, epoch_data in enumerate(svm_history):
                col = x + 4 + int(i * (plot_width - 8) / max_epochs)
                acc = epoch_data.get('train_accuracy', 0)
                row = y + 3 + plot_height - int(acc * plot_height)
                
                if 0 <= row < height and 0 <= col < width:
                    try:
                        self.stdscr.addch(row, col, '◆', self._get_color('cyan'))
                    except:
                        pass
        
        # Legend
        self._write(y + 2, x + plot_width - 15, "● LR  ◆ SVM", 'white')
    
    # ==================== INPUT HANDLING ====================
    
    def _handle_input(self):
        """Handle user input."""
        try:
            key = self.stdscr.getch()
        except:
            return
        
        if key == -1:
            return
        
        if self.current_view == 'main':
            self._handle_main_menu_input(key)
        elif self.current_view == 'simulation':
            self._handle_simulation_input(key)
        elif self.current_view == 'model_comparison':
            self._handle_comparison_input(key)
    
    def _handle_main_menu_input(self, key):
        """Handle input in main menu."""
        if key == curses.KEY_UP:
            self.selected_option = max(0, self.selected_option - 1)
        elif key == curses.KEY_DOWN:
            self.selected_option = min(4, self.selected_option + 1)
        elif key == ord('\n') or key == ord('\r'):
            if self.selected_option == 0:
                # Run simulation
                self.current_view = 'simulation'
                self._init_simulation()
            elif self.selected_option == 1:
                # Train models
                self._train_models()
            elif self.selected_option == 2:
                # View results
                if self.model_results:
                    self.current_view = 'model_comparison'
                else:
                    self._show_message("No model results. Train models first (option 2).", 'red')
            elif self.selected_option == 3:
                # Help
                self._show_help()
            elif self.selected_option == 4:
                # Exit
                self.running = False
        elif key == ord('q') or key == ord('Q'):
            self.running = False
    
    def _handle_simulation_input(self, key):
        """Handle input in simulation view."""
        if key == ord(' ') or key == ord('s') or key == ord('S'):
            # Run simulation step
            events = self._run_simulation_step()
            
            if not events and self.simulation and not self.simulation.pending_shares:
                self._show_message("Simulation complete! Press Q to return.", 'green')
            else:
                self._show_message("Running... Press SPACE to continue, Q to quit", 'cyan')
        
        elif key == ord('r') or key == ord('R'):
            # Reset simulation
            self._init_simulation()
        
        elif key == ord('q') or key == ord('Q'):
            # Return to main menu
            self.current_view = 'main'
            self._show_message("", 'white')
    
    def _handle_comparison_input(self, key):
        """Handle input in comparison view."""
        if key == ord('q') or key == ord('Q'):
            self.current_view = 'main'
            self._show_message("", 'white')
        elif key == ord('t') or key == ord('T'):
            self._train_models()
    
    def _show_help(self):
        """Show help screen."""
        self._clear()
        
        height, width = self.stdscr.getmaxyx()
        
        self._write(2, (width - 20) // 2, "❓ Help", 'cyan', bold=True)
        
        help_text = [
            "",
            "Agent Office is a social network simulation platform",
            "that models how information (and misinformation)",
            "spreads through a network of agents.",
            "",
            "KEYBOARD CONTROLS:",
            "  ↑↓     Navigate menu",
            "  Enter  Select option",
            "  Space  Run simulation step",
            "  R      Reset simulation",
            "  T      Train models",
            "  Q      Return/Quit",
            "",
            "AGENT TYPES:",
            "  🔴 Immediate Sharer - Shares without thinking",
            "  🟢 Cautious Sharer - Verifies before sharing",
            "  🔵 Skeptic - High skepticism, rarely shares",
            "  🟡 Influencer - High network influence",
            "  ⚪ Lurker - Reads but rarely shares",
            "",
            "Press any key to return...",
        ]
        
        for i, line in enumerate(help_text):
            self._write(4 + i, (width - len(line)) // 2, line, 'white')
        
        self.stdscr.refresh()
        
        # Wait for key
        self.stdscr.nodelay(0)
        self.stdscr.getch()
        self.stdscr.nodelay(1)


def run_tui_app():
    """Main entry point for the TUI application."""
    import sys
    
    # Check if we have a proper terminal
    if not sys.stdout.isatty():
        print("\n" + "=" * 60)
        print("🏢 AGENT OFFICE - TUI Application")
        print("=" * 60)
        print("\nThis application requires an interactive terminal (TTY).")
        print("\nPlease run this script directly in a terminal:")
        print("  python3 run_tui.py")
        print("\nAlternatively, use the pipeline for non-interactive use:")
        print("  python3 run_pipeline.py")
        print("\n" + "=" * 60)
        return
    
    try:
        app = TUIApp()
        app.run()
    except Exception as e:
        print(f"\nError running TUI: {e}")
        print("\nFalling back to simple terminal mode...")
        _run_simple_terminal_mode()


def _run_simple_terminal_mode():
    """Run a simple terminal-based interface without curses."""
    import time
    import sys
    
    print("\n" + "=" * 60)
    print("🏢 AGENT OFFICE - Simple Terminal Mode")
    print("=" * 60)
    print("\nOptions:")
    print("  1. Run Simulation")
    print("  2. Train & Compare Models")
    print("  3. Exit")
    print()
    
    while True:
        try:
            choice = input("Select option (1-3): ").strip()
            
            if choice == '1':
                _run_simple_simulation()
            elif choice == '2':
                _run_simple_training()
            elif choice == '3':
                print("\nGoodbye!")
                break
            else:
                print("Invalid option. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            break


def _run_simple_simulation():
    """Run a simple simulation with terminal output."""
    print("\n" + "-" * 50)
    print("Running Simulation...")
    print("-" * 50)
    
    # Initialize
    network = SocialNetwork()
    
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
    
    network.create_preferential_attachment_network(avg_connections=3)
    
    simulation = Simulation(network, tick_delay=0.1)
    
    all_posts = create_sample_posts()
    posts_to_use = random.sample(all_posts, min(6, len(all_posts)))
    
    influencers = [a for a in agents if a.agent_type == AgentType.INFLUENCER]
    
    for post in posts_to_use:
        if influencers and random.random() < 0.6:
            initial_agent = random.choice(influencers)
        else:
            initial_agent = random.choice(agents)
        simulation.add_post(post, initial_agent)
    
    print(f"\nNetwork: {len(agents)} agents, {sum(len(c) for c in network.connections.values())} connections")
    print(f"Posts: {len(posts_to_use)}")
    print()
    
    # Run simulation
    def on_event(event):
        truth_icons = {'true': '✓', 'false': '✗', 'mixed': '◐', 'unverified': '?'}
        post = simulation.posts.get(event.post_id)
        if post:
            icon = truth_icons.get(post.truth_value.value, '?')
            print(f"  [T{event.tick:03d}] {event.agent_name} → {event.behavior} {icon} {post.subject[:35]}...")
    
    simulation.on_event = on_event
    simulation.run(max_ticks=100, stop_when_idle=True, idle_threshold=10)
    
    # Print summary
    print("\n" + "-" * 50)
    print("Simulation Complete!")
    print("-" * 50)
    
    total_shares = sum(p.share_count for p in simulation.posts.values())
    total_reach = sum(p.reach_count for p in simulation.posts.values())
    
    print(f"Total Shares: {total_shares}")
    print(f"Total Reach: {total_reach}")
    print()


def _run_simple_training():
    """Run model training with terminal output."""
    print("\n" + "-" * 50)
    print("Training Models...")
    print("-" * 50)
    
    # Generate data
    print("\nGenerating training data...")
    
    feature_extractor = FeatureExtractor(early_window_ticks=10)
    dataset_builder = DatasetBuilder(feature_extractor=feature_extractor, random_seed=42)
    tracker = EarlyDisseminationTracker(early_window_ticks=10)
    
    for sim_num in range(30):
        _run_data_simulation_for_training(tracker, sim_num)
        if (sim_num + 1) % 10 == 0:
            print(f"  Generated {sim_num + 1}/30 simulations...")
    
    dataset_builder.add_records_from_tracker(tracker)
    print(f"\nDataset: {len(dataset_builder)} samples")
    
    # Train models
    print("\nTraining Logistic Regression and SVM...")
    
    config = TrainingConfig(
        learning_rate=0.01,
        num_epochs=20,
        regularization=0.01,
        random_seed=42,
        batch_size=32,
        validation_split=0.15
    )
    
    ml_pipeline = MLPipeline(config, feature_extractor)
    
    # train_and_compare creates the trainer internally
    results = ml_pipeline.train_and_compare(dataset_builder, verbose=False)
    
    # Print results
    print("\n" + "=" * 50)
    print("MODEL COMPARISON RESULTS")
    print("=" * 50)
    
    for model_name in ["Logistic Regression", "SVM"]:
        metrics = results['evaluation_results'].get(model_name, {})
        print(f"\n{model_name}:")
        print(f"  Accuracy:  {metrics.get('accuracy', 0):.1%}")
        print(f"  Precision: {metrics.get('precision', 0):.1%}")
        print(f"  Recall:    {metrics.get('recall', 0):.1%}")
        print(f"  F1 Score:  {metrics.get('f1_score', 0):.1%}")
        print(f"  AUC-ROC:   {metrics.get('auc_roc', 0):.1%}")
    
    comparison = ml_pipeline.comparison_report
    print(f"\nBest Model: {comparison.get('best_model', 'N/A')}")
    print()


def _run_data_simulation_for_training(tracker: EarlyDisseminationTracker, seed: int):
    """Run a single simulation for data generation."""
    random.seed(seed)
    
    network = SocialNetwork()
    agents = []
    
    for i in range(13):
        agent_type = list(AgentType)[i % 5]
        agent = create_agent_from_type(f"agent_{i}", f"Agent_{i}", agent_type)
        network.add_agent(agent)
        tracker.register_agent(agent.id, agent.agent_type)
        agents.append(agent)
    
    network.create_preferential_attachment_network(avg_connections=4)
    
    simulation = Simulation(network, tick_delay=0.01)
    
    posts = create_sample_posts()
    for post in random.sample(posts, min(6, len(posts))):
        tracker.register_post(post)
        simulation.add_post(post, random.choice(agents))
    
    simulation.run(max_ticks=100, stop_when_idle=True, idle_threshold=5)
    
    for event in simulation.events:
        tracker.record_event(
            tick=event.tick,
            post_id=event.post_id,
            agent_id=event.agent_id,
            agent_name=event.agent_name,
            behavior=event.behavior,
            confidence=event.details.get('confidence', 0.5),
            trust_modifier=event.details.get('trust_modifier', 0.5)
        )
