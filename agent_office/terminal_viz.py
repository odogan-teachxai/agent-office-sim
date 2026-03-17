"""
Terminal-based Visualization for Agent Office simulation.

This module provides a text-based visualization that works in any terminal,
showing the network structure and post spreading dynamics using ASCII art.
"""

import time
import os
import sys
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
from collections import defaultdict
import random
import math

from .agent import Agent, AgentType, AgentBehavior
from .post import Post, TruthValue
from .network import SocialNetwork
from .simulation import Simulation, SimulationEvent


# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


# Agent type symbols and colors
AGENT_STYLES = {
    AgentType.IMMEDIATE_SHARER: ('🔴', Colors.RED, 'IMM'),
    AgentType.CAUTIOUS_SHARER: ('🟢', Colors.GREEN, 'CAU'),
    AgentType.SKEPTIC: ('🔵', Colors.BLUE, 'SKP'),
    AgentType.INFLUENCER: ('🟡', Colors.YELLOW, 'INF'),
    AgentType.LURKER: ('⚪', Colors.WHITE, 'LRK'),
}

# State colors
STATE_COLORS = {
    'default': Colors.WHITE,
    'received': Colors.CYAN,
    'shared': Colors.GREEN,
    'rejected': Colors.RED,
    'flagged': Colors.MAGENTA,
}

# Truth value colors
TRUTH_COLORS = {
    'true': Colors.GREEN,
    'false': Colors.RED,
    'mixed': Colors.YELLOW,
    'unverified': Colors.MAGENTA,
}


@dataclass
class AgentPosition:
    """Position of an agent in the terminal grid."""
    agent: Agent
    row: int
    col: int
    state: str = 'default'


class TerminalVisualizer:
    """
    Terminal-based visualization for the Agent Office simulation.
    
    Uses ASCII art and ANSI colors to display the network and
    post spreading dynamics in real-time.
    """
    
    def __init__(
        self,
        width: int = 80,
        height: int = 30,
        animation_speed: float = 0.3
    ):
        """
        Initialize the terminal visualizer.
        
        Args:
            width: Terminal width in characters
            height: Terminal height in lines
            animation_speed: Seconds between updates
        """
        self.width = width
        self.height = height
        self.animation_speed = animation_speed
        
        self.network: Optional[SocialNetwork] = None
        self.simulation: Optional[Simulation] = None
        
        self.agent_positions: Dict[str, AgentPosition] = {}
        self.grid: List[List[str]] = []
        
        # Statistics
        self.stats = {
            'tick': 0,
            'total_shares': 0,
            'total_reach': 0,
            'total_flags': 0,
            'true_posts': 0,
            'false_posts': 0,
        }
        
        self.behavior_counts = defaultdict(int)
        self.current_post: Optional[Post] = None
        
        self._running = False
    
    def set_network(self, network: SocialNetwork):
        """Set the network to visualize."""
        self.network = network
        self._calculate_positions()
    
    def set_simulation(self, simulation: Simulation):
        """Set the simulation to visualize."""
        self.simulation = simulation
    
    def _calculate_positions(self):
        """Calculate agent positions using circular layout."""
        if not self.network:
            return
        
        agents = self.network.get_all_agents()
        n = len(agents)
        
        if n == 0:
            return
        
        # Calculate grid dimensions for network area
        net_width = self.width - 25  # Leave space for stats panel
        net_height = self.height - 8  # Leave space for header/footer
        
        center_x = net_width // 2
        center_y = net_height // 2
        radius = min(center_x, center_y) - 3
        
        for i, agent in enumerate(agents):
            angle = 2 * math.pi * i / n - math.pi / 2  # Start from top
            col = int(center_x + radius * math.cos(angle))
            row = int(center_y + radius * math.sin(angle))
            
            self.agent_positions[agent.id] = AgentPosition(
                agent=agent,
                row=row,
                col=col
            )
    
    def _clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def _move_cursor(self, row: int, col: int):
        """Move cursor to position."""
        print(f'\033[{row};{col}H', end='')
    
    def _create_grid(self):
        """Create an empty grid."""
        self.grid = [[' ' for _ in range(self.width)] for _ in range(self.height)]
    
    def _draw_header(self):
        """Draw the header section."""
        header = "🏢 AGENT OFFICE - Live Simulation"
        self._print_centered(header, 0, Colors.BOLD + Colors.CYAN)
        
        # Separator
        self._print_at(1, 0, '─' * self.width, Colors.DIM)
    
    def _draw_stats_panel(self):
        """Draw the statistics panel on the right side."""
        start_col = self.width - 23
        
        # Panel header
        self._print_at(2, start_col, '┌' + '─' * 21 + '┐', Colors.DIM)
        self._print_at(3, start_col, '│ 📊 STATISTICS      │', Colors.BOLD + Colors.CYAN)
        self._print_at(4, start_col, '├' + '─' * 21 + '┤', Colors.DIM)
        
        # Stats
        stats_lines = [
            (f'Tick: {self.stats["tick"]}', Colors.WHITE),
            (f'Reach: {self.stats["total_reach"]}', Colors.WHITE),
            (f'Shares: {self.stats["total_shares"]}', Colors.GREEN),
            (f'Flags: {self.stats["total_flags"]}', Colors.RED),
        ]
        
        for i, (text, color) in enumerate(stats_lines):
            self._print_at(5 + i, start_col, f'│ {text:<19}│', color)
        
        # Truth values
        self._print_at(9, start_col, '├' + '─' * 21 + '┤', Colors.DIM)
        self._print_at(10, start_col, '│ 📰 POSTS           │', Colors.BOLD + Colors.CYAN)
        self._print_at(11, start_col, '├' + '─' * 21 + '┤', Colors.DIM)
        
        truth_lines = [
            (f'✓ True: {self.stats["true_posts"]}', TRUTH_COLORS['true']),
            (f'✗ False: {self.stats["false_posts"]}', TRUTH_COLORS['false']),
        ]
        
        for i, (text, color) in enumerate(truth_lines):
            self._print_at(12 + i, start_col, f'│ {text:<19}│', color)
        
        # Behaviors
        self._print_at(14, start_col, '├' + '─' * 21 + '┤', Colors.DIM)
        self._print_at(15, start_col, '│ 🎭 BEHAVIORS       │', Colors.BOLD + Colors.CYAN)
        self._print_at(16, start_col, '├' + '─' * 21 + '┤', Colors.DIM)
        
        shared = self.behavior_counts.get('share_immediately', 0) + \
                 self.behavior_counts.get('verify_then_share', 0)
        rejected = self.behavior_counts.get('ignore', 0) + \
                   self.behavior_counts.get('verify_then_ignore', 0)
        flagged = self.behavior_counts.get('flag_as_suspicious', 0)
        
        behavior_lines = [
            (f'📤 Shared: {shared}', Colors.GREEN),
            (f'❌ Rejected: {rejected}', Colors.RED),
            (f'🚩 Flagged: {flagged}', Colors.MAGENTA),
        ]
        
        for i, (text, color) in enumerate(behavior_lines):
            self._print_at(17 + i, start_col, f'│ {text:<19}│', color)
        
        self._print_at(20, start_col, '└' + '─' * 21 + '┘', Colors.DIM)
    
    def _draw_network(self):
        """Draw the network graph."""
        net_width = self.width - 25
        
        # Draw edges
        if self.network:
            for agent_id, connections in self.network.connections.items():
                pos1 = self.agent_positions.get(agent_id)
                if not pos1:
                    continue
                
                for conn in connections:
                    pos2 = self.agent_positions.get(conn.followee_id)
                    if not pos2:
                        continue
                    
                    self._draw_line(pos1.col, pos1.row, pos2.col, pos2.row)
        
        # Draw nodes
        for agent_id, pos in self.agent_positions.items():
            self._draw_agent(pos)
    
    def _draw_agent(self, pos: AgentPosition):
        """Draw a single agent node."""
        symbol, type_color, abbrev = AGENT_STYLES.get(
            pos.agent.agent_type, 
            ('⚪', Colors.WHITE, '???')
        )
        
        state_color = STATE_COLORS.get(pos.state, Colors.WHITE)
        
        # Use state color if not default
        color = state_color if pos.state != 'default' else type_color
        
        # Draw node
        row = pos.row + 3  # Offset for header
        col = pos.col + 2  # Offset for border
        
        # Node character
        node_char = '●' if pos.agent.agent_type == AgentType.INFLUENCER else '○'
        
        # Add glow effect for active states
        if pos.state != 'default':
            self._print_at(row, col - 1, f'({node_char})', color + Colors.BOLD)
        else:
            self._print_at(row, col, node_char, color)
        
        # Draw name below
        name = pos.agent.name[:6]
        self._print_at(row + 1, col - len(name)//2, name, Colors.DIM)
    
    def _draw_line(self, x1: int, y1: int, x2: int, y2: int):
        """Draw a simple line between two points."""
        # Simple line drawing using characters
        dx = x2 - x1
        dy = y2 - y1
        
        steps = max(abs(dx), abs(dy), 1)
        
        for i in range(1, steps):
            t = i / steps
            x = int(x1 + dx * t)
            y = int(y1 + dy * t)
            
            row = y + 3
            col = x + 2
            
            if 0 <= row < self.height and 0 <= col < self.width - 25:
                # Use different characters for different angles
                if abs(dx) > abs(dy):
                    char = '─'
                elif abs(dy) > abs(dx):
                    char = '│'
                else:
                    char = '╲' if (dx * dy) > 0 else '╱'
                
                self._print_at(row, col, char, Colors.DIM)
    
    def _draw_current_post(self):
        """Draw information about the current post."""
        row = self.height - 5
        
        self._print_at(row, 0, '─' * (self.width - 25), Colors.DIM)
        
        if self.current_post:
            truth_color = TRUTH_COLORS.get(self.current_post.truth_value.value, Colors.WHITE)
            truth_icon = {'true': '✓', 'false': '✗', 'mixed': '◐', 'unverified': '?'}
            icon = truth_icon.get(self.current_post.truth_value.value, '?')
            
            subject = self.current_post.subject[:50]
            if len(self.current_post.subject) > 50:
                subject += '...'
            
            self._print_at(row + 1, 2, f'📬 Current Post:', Colors.BOLD + Colors.CYAN)
            self._print_at(row + 2, 2, f'   {icon} {subject}', truth_color)
            self._print_at(row + 3, 2, 
                          f'   Shares: {self.current_post.share_count} | '
                          f'Reach: {self.current_post.reach_count}',
                          Colors.DIM)
        else:
            self._print_at(row + 1, 2, '📬 Waiting for post...', Colors.DIM)
    
    def _draw_legend(self):
        """Draw the legend."""
        row = self.height - 5
        col = self.width - 23
        
        self._print_at(row, col, '┌' + '─' * 21 + '┐', Colors.DIM)
        self._print_at(row + 1, col, '│ 📋 LEGEND          │', Colors.BOLD + Colors.CYAN)
        self._print_at(row + 2, col, '│ ○ Node  ● Influencer│', Colors.DIM)
        self._print_at(row + 3, col, '│ Green=Shared Red=Flg│', Colors.DIM)
        self._print_at(row + 4, col, '└' + '─' * 21 + '┘', Colors.DIM)
    
    def _print_at(self, row: int, col: int, text: str, color: str = ''):
        """Print text at a specific position."""
        if 0 <= row < self.height and 0 <= col < self.width:
            self._move_cursor(row + 1, col + 1)
            print(f'{color}{text}{Colors.RESET}', end='')
    
    def _print_centered(self, text: str, row: int, color: str = ''):
        """Print centered text."""
        col = (self.width - len(text)) // 2
        self._print_at(row, col, text, color)
    
    def _update_agent_state(self, agent_id: str, state: str):
        """Update an agent's visual state."""
        if agent_id in self.agent_positions:
            self.agent_positions[agent_id].state = state
    
    def _process_event(self, event: SimulationEvent):
        """Process a simulation event."""
        # Update current post
        if self.simulation:
            post = self.simulation.posts.get(event.post_id)
            if post:
                self.current_post = post
        
        # Determine state
        state_map = {
            'share_immediately': 'shared',
            'verify_then_share': 'shared',
            'verify_then_ignore': 'rejected',
            'ignore': 'rejected',
            'flag_as_suspicious': 'flagged',
        }
        
        state = state_map.get(event.behavior, 'default')
        self._update_agent_state(event.agent_id, state)
        
        # Update behavior counts
        self.behavior_counts[event.behavior] += 1
    
    def _update_statistics(self):
        """Update statistics from simulation."""
        if not self.simulation:
            return
        
        truth_counts = {'true': 0, 'false': 0, 'mixed': 0, 'unverified': 0}
        total_shares = 0
        total_reach = 0
        total_flags = 0
        
        for post in self.simulation.posts.values():
            truth_counts[post.truth_value.value] += 1
            total_shares += post.share_count
            total_reach += post.reach_count
            total_flags += post.flagged_count
        
        self.stats = {
            'tick': self.simulation.current_tick,
            'total_shares': total_shares,
            'total_reach': total_reach,
            'total_flags': total_flags,
            'true_posts': truth_counts['true'],
            'false_posts': truth_counts['false'],
        }
    
    def _render_frame(self):
        """Render a single frame."""
        self._clear_screen()
        self._draw_header()
        self._draw_stats_panel()
        self._draw_network()
        self._draw_current_post()
        self._draw_legend()
        
        # Instructions
        self._print_at(self.height - 1, 0, 
                      'Press Ctrl+C to stop', Colors.DIM)
        
        sys.stdout.flush()
    
    def run(self):
        """Run the visualization."""
        self._running = True
        
        try:
            while self._running:
                # Render current state
                self._render_frame()
                
                # Run simulation step
                if self.simulation:
                    events = self.simulation.tick()
                    
                    for event in events:
                        self._process_event(event)
                    
                    self._update_statistics()
                    
                    # Check if simulation is done
                    if not events and not self.simulation.pending_shares:
                        self._render_frame()
                        self._print_at(self.height - 1, 0, 
                                      '✅ Simulation complete! Press Ctrl+C to exit.',
                                      Colors.GREEN + Colors.BOLD)
                        sys.stdout.flush()
                        self._running = False
                        break
                
                time.sleep(self.animation_speed)
                
        except KeyboardInterrupt:
            self._clear_screen()
            print(f'\n{Colors.YELLOW}Simulation stopped by user.{Colors.RESET}\n')
    
    def stop(self):
        """Stop the visualization."""
        self._running = False


def run_terminal_visualization(
    num_agents: int = 13,
    num_posts: int = 6,
    animation_speed: float = 0.3
):
    """
    Create and run a terminal-based visualization.
    
    Args:
        num_agents: Number of agents in the network
        num_posts: Number of posts to simulate
        animation_speed: Seconds between frames
    """
    from .agent import create_agent_from_type
    from .post import create_sample_posts
    
    # Create network
    network = SocialNetwork()
    
    # Create agents
    agent_types = list(AgentType)
    agent_names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve",
        "Frank", "Grace", "Henry", "Ivy", "Jack",
        "Kate", "Leo", "Mia"
    ]
    
    for i in range(num_agents):
        agent_type = agent_types[i % len(agent_types)]
        name = agent_names[i] if i < len(agent_names) else f"Agent_{i}"
        agent = create_agent_from_type(f"agent_{i}", name, agent_type)
        network.add_agent(agent)
    
    # Create connections
    network.create_preferential_attachment_network(avg_connections=3)
    
    # Create simulation
    simulation = Simulation(network, tick_delay=0.1)
    
    # Add posts
    all_posts = create_sample_posts()
    posts_to_use = random.sample(all_posts, min(num_posts, len(all_posts)))
    
    influencers = [a for a in network.get_all_agents() 
                   if a.agent_type == AgentType.INFLUENCER]
    
    for post in posts_to_use:
        if influencers and random.random() < 0.6:
            initial_agent = random.choice(influencers)
        else:
            initial_agent = random.choice(network.get_all_agents())
        
        simulation.add_post(post, initial_agent)
    
    # Create and run visualizer
    visualizer = TerminalVisualizer(animation_speed=animation_speed)
    visualizer.set_network(network)
    visualizer.set_simulation(simulation)
    
    print(f"\n{Colors.CYAN}Starting terminal visualization...{Colors.RESET}")
    print(f"Network: {num_agents} agents, {len(network.connections)} connections")
    print(f"Posts: {num_posts}")
    print(f"\n{Colors.YELLOW}Press Ctrl+C to stop{Colors.RESET}\n")
    time.sleep(1)
    
    visualizer.run()
