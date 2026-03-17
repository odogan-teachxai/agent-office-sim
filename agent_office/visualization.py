"""
Visualization Module - Real-time visualization of the Agent Office simulation.

This module provides a tkinter-based GUI that displays:
- Network graph with agents as nodes and connections as edges
- Real-time post spreading animation
- Color-coded agent states
- Live statistics panel
"""

import tkinter as tk
from tkinter import ttk, font
from typing import Optional, Callable, Dict, List, Set
from dataclasses import dataclass, field
from collections import defaultdict
import math
import random
import time
from datetime import datetime
import threading

from .agent import Agent, AgentType, AgentBehavior
from .post import Post, TruthValue
from .network import SocialNetwork
from .simulation import Simulation, SimulationEvent


# Color scheme
COLORS = {
    'background': '#1a1a2e',
    'panel_bg': '#16213e',
    'text': '#e8e8e8',
    'text_dim': '#a0a0a0',
    'edge': '#3a3a5a',
    'edge_active': '#6a6a9a',
    
    # Agent states
    'agent_default': '#4a4a6a',
    'agent_immediate_sharer': '#ff6b6b',
    'agent_cautious_sharer': '#4ecdc4',
    'agent_skeptic': '#45b7d1',
    'agent_influencer': '#f9ca24',
    'agent_lurker': '#95a5a6',
    
    # Post interaction states
    'received': '#3498db',
    'shared': '#2ecc71',
    'rejected': '#e74c3c',
    'flagged': '#e74c3c',
    
    # Truth values
    'true': '#2ecc71',
    'false': '#e74c3c',
    'mixed': '#f39c12',
    'unverified': '#9b59b6',
    
    # UI accents
    'accent': '#00d4ff',
    'success': '#2ecc71',
    'warning': '#f39c12',
    'danger': '#e74c3c',
}


@dataclass
class AgentVisual:
    """Visual representation of an agent."""
    agent: Agent
    x: float = 0.0
    y: float = 0.0
    canvas_id: Optional[int] = None
    label_id: Optional[int] = None
    current_state: str = 'default'  # default, received, shared, rejected, flagged
    pulse_animation: int = 0


@dataclass
class PostVisual:
    """Visual tracking of a post's spread."""
    post: Post
    agents_received: Set[str] = field(default_factory=set)
    agents_shared: Set[str] = field(default_factory=set)
    agents_rejected: Set[str] = field(default_factory=set)
    agents_flagged: Set[str] = field(default_factory=set)


class NetworkCanvas(tk.Canvas):
    """Canvas for drawing the social network graph."""
    
    def __init__(self, parent, width: int, height: int, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        bg=COLORS['background'], highlightthickness=0, **kwargs)
        
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.center_y = height // 2
        
        # Visual elements
        self.agent_visuals: Dict[str, AgentVisual] = {}
        self.post_visuals: Dict[str, PostVisual] = {}
        self.edge_ids: List[int] = []
        
        # Animation state
        self.active_edges: Set[tuple] = set()
        
    def calculate_layout(self, agents: List[Agent], network: SocialNetwork):
        """Calculate node positions using force-directed layout."""
        n = len(agents)
        if n == 0:
            return
        
        # Initial circular layout
        radius = min(self.width, self.height) * 0.35
        
        for i, agent in enumerate(agents):
            angle = 2 * math.pi * i / n
            x = self.center_x + radius * math.cos(angle)
            y = self.center_y + radius * math.sin(angle)
            
            self.agent_visuals[agent.id] = AgentVisual(
                agent=agent,
                x=x,
                y=y
            )
        
        # Simple force-directed adjustment
        for _ in range(50):
            self._apply_forces(network)
    
    def _apply_forces(self, network: SocialNetwork):
        """Apply force-directed layout forces."""
        agents = list(self.agent_visuals.values())
        n = len(agents)
        
        if n < 2:
            return
        
        # Repulsion between all nodes
        for i, av1 in enumerate(agents):
            fx, fy = 0.0, 0.0
            
            for j, av2 in enumerate(agents):
                if i == j:
                    continue
                
                dx = av1.x - av2.x
                dy = av1.y - av2.y
                dist = max(1, math.sqrt(dx*dx + dy*dy))
                
                # Repulsion force
                force = 500 / (dist * dist)
                fx += force * dx / dist
                fy += force * dy / dist
            
            # Attraction to connected nodes
            connections = network.connections.get(av1.agent.id, [])
            for conn in connections:
                other = self.agent_visuals.get(conn.followee_id)
                if other:
                    dx = other.x - av1.x
                    dy = other.y - av1.y
                    dist = max(1, math.sqrt(dx*dx + dy*dy))
                    force = dist * 0.01
                    fx += force * dx / dist
                    fy += force * dy / dist
            
            # Apply forces with damping
            av1.x += fx * 0.1
            av1.y += fy * 0.1
            
            # Keep within bounds
            margin = 50
            av1.x = max(margin, min(self.width - margin, av1.x))
            av1.y = max(margin, min(self.height - margin, av1.y))
    
    def draw_network(self, network: SocialNetwork):
        """Draw the complete network."""
        self.delete('all')
        self.edge_ids.clear()
        
        # Draw edges first (below nodes)
        for agent_id, connections in network.connections.items():
            av1 = self.agent_visuals.get(agent_id)
            if not av1:
                continue
            
            for conn in connections:
                av2 = self.agent_visuals.get(conn.followee_id)
                if not av2:
                    continue
                
                edge_id = self.create_line(
                    av1.x, av1.y, av2.x, av2.y,
                    fill=COLORS['edge'],
                    width=1,
                    tags='edge'
                )
                self.edge_ids.append(edge_id)
        
        # Draw nodes
        for agent_id, av in self.agent_visuals.items():
            self._draw_agent_node(av)
    
    def _draw_agent_node(self, av: AgentVisual):
        """Draw a single agent node."""
        # Determine color based on agent type
        type_colors = {
            AgentType.IMMEDIATE_SHARER: COLORS['agent_immediate_sharer'],
            AgentType.CAUTIOUS_SHARER: COLORS['agent_cautious_sharer'],
            AgentType.SKEPTIC: COLORS['agent_skeptic'],
            AgentType.INFLUENCER: COLORS['agent_influencer'],
            AgentType.LURKER: COLORS['agent_lurker'],
        }
        base_color = type_colors.get(av.agent.agent_type, COLORS['agent_default'])
        
        # Modify based on state
        state_colors = {
            'default': base_color,
            'received': COLORS['received'],
            'shared': COLORS['shared'],
            'rejected': COLORS['rejected'],
            'flagged': COLORS['flagged'],
        }
        color = state_colors.get(av.current_state, base_color)
        
        # Node size (influencers are bigger)
        radius = 20 if av.agent.agent_type == AgentType.INFLUENCER else 15
        
        # Draw glow effect for active states
        if av.current_state != 'default':
            glow_radius = radius + 5 + av.pulse_animation
            self.create_oval(
                av.x - glow_radius, av.y - glow_radius,
                av.x + glow_radius, av.y + glow_radius,
                fill='', outline=color, width=2,
                tags=('agent', 'glow', f'agent_{av.agent.id}')
            )
        
        # Draw node
        av.canvas_id = self.create_oval(
            av.x - radius, av.y - radius,
            av.x + radius, av.y + radius,
            fill=color, outline='white', width=2,
            tags=('agent', f'agent_{av.agent.id}')
        )
        
        # Draw label
        av.label_id = self.create_text(
            av.x, av.y + radius + 12,
            text=av.agent.name,
            fill=COLORS['text'],
            font=('Arial', 8),
            tags=('label', f'label_{av.agent.id}')
        )
    
    def update_agent_state(self, agent_id: str, state: str):
        """Update an agent's visual state."""
        av = self.agent_visuals.get(agent_id)
        if av:
            av.current_state = state
            av.pulse_animation = 10
            self._draw_agent_node(av)
    
    def animate_pulse(self):
        """Animate pulse effects on agents."""
        for av in self.agent_visuals.values():
            if av.pulse_animation > 0:
                av.pulse_animation -= 1
                if av.pulse_animation == 0 and av.current_state != 'default':
                    # Reset to default after animation
                    pass
                self._draw_agent_node(av)
    
    def highlight_edge(self, from_agent_id: str, to_agent_id: str, color: str):
        """Highlight an edge during post spread."""
        av1 = self.agent_visuals.get(from_agent_id)
        av2 = self.agent_visuals.get(to_agent_id)
        
        if av1 and av2:
            self.create_line(
                av1.x, av1.y, av2.x, av2.y,
                fill=color, width=3,
                tags='active_edge'
            )
    
    def clear_active_edges(self):
        """Clear highlighted edges."""
        self.delete('active_edge')


class StatsPanel(ttk.Frame):
    """Panel displaying real-time statistics."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(style='Dark.TFrame')
        
        # Statistics variables
        self.stats = {
            'total_shares': 0,
            'total_reach': 0,
            'total_flags': 0,
            'true_posts': 0,
            'false_posts': 0,
            'mixed_posts': 0,
            'unverified_posts': 0,
            'current_tick': 0,
            'posts_active': 0,
        }
        
        # Agent behavior counts
        self.behavior_counts = {
            'share_immediately': 0,
            'verify_then_share': 0,
            'verify_then_ignore': 0,
            'ignore': 0,
            'flag_as_suspicious': 0,
        }
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the statistics display widgets."""
        # Title
        title_label = tk.Label(
            self, text="📊 Live Statistics",
            font=('Arial', 14, 'bold'),
            fg=COLORS['accent'], bg=COLORS['panel_bg']
        )
        title_label.pack(pady=(10, 15))
        
        # Main stats frame
        stats_frame = tk.Frame(self, bg=COLORS['panel_bg'])
        stats_frame.pack(fill='x', padx=10)
        
        # Create stat labels
        self.stat_labels = {}
        
        stats_config = [
            ('tick', '⏱️ Tick', 'current_tick'),
            ('reach', '👥 Total Reach', 'total_reach'),
            ('shares', '📤 Total Shares', 'total_shares'),
            ('flags', '🚩 Flagged', 'total_flags'),
        ]
        
        for key, label, stat_key in stats_config:
            frame = tk.Frame(stats_frame, bg=COLORS['panel_bg'])
            frame.pack(fill='x', pady=3)
            
            tk.Label(
                frame, text=label,
                font=('Arial', 10),
                fg=COLORS['text_dim'], bg=COLORS['panel_bg'],
                anchor='w'
            ).pack(side='left')
            
            value_label = tk.Label(
                frame, text='0',
                font=('Arial', 12, 'bold'),
                fg=COLORS['text'], bg=COLORS['panel_bg'],
                anchor='e'
            )
            value_label.pack(side='right')
            
            self.stat_labels[key] = value_label
        
        # Separator
        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=10, padx=10)
        
        # Truth value section
        truth_frame = tk.Frame(self, bg=COLORS['panel_bg'])
        truth_frame.pack(fill='x', padx=10)
        
        tk.Label(
            truth_frame, text="📰 Post Truth Values",
            font=('Arial', 11, 'bold'),
            fg=COLORS['text'], bg=COLORS['panel_bg']
        ).pack(anchor='w', pady=(0, 5))
        
        truth_config = [
            ('true', '✓ True', COLORS['true'], 'true_posts'),
            ('false', '✗ False', COLORS['false'], 'false_posts'),
            ('mixed', '◐ Mixed', COLORS['mixed'], 'mixed_posts'),
            ('unverified', '? Unverified', COLORS['unverified'], 'unverified_posts'),
        ]
        
        self.truth_labels = {}
        for key, label, color, stat_key in truth_config:
            frame = tk.Frame(truth_frame, bg=COLORS['panel_bg'])
            frame.pack(fill='x', pady=2)
            
            tk.Label(
                frame, text=label,
                font=('Arial', 10),
                fg=color, bg=COLORS['panel_bg'],
                anchor='w'
            ).pack(side='left')
            
            value_label = tk.Label(
                frame, text='0',
                font=('Arial', 11, 'bold'),
                fg=color, bg=COLORS['panel_bg'],
                anchor='e'
            )
            value_label.pack(side='right')
            
            self.truth_labels[key] = value_label
        
        # Separator
        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=10, padx=10)
        
        # Behavior section
        behavior_frame = tk.Frame(self, bg=COLORS['panel_bg'])
        behavior_frame.pack(fill='x', padx=10)
        
        tk.Label(
            behavior_frame, text="🎭 Agent Behaviors",
            font=('Arial', 11, 'bold'),
            fg=COLORS['text'], bg=COLORS['panel_bg']
        ).pack(anchor='w', pady=(0, 5))
        
        behavior_config = [
            ('shared', '📤 Shared', COLORS['shared']),
            ('rejected', '❌ Rejected', COLORS['rejected']),
            ('flagged', '🚩 Flagged', COLORS['flagged']),
        ]
        
        self.behavior_labels = {}
        for key, label, color in behavior_config:
            frame = tk.Frame(behavior_frame, bg=COLORS['panel_bg'])
            frame.pack(fill='x', pady=2)
            
            tk.Label(
                frame, text=label,
                font=('Arial', 10),
                fg=color, bg=COLORS['panel_bg'],
                anchor='w'
            ).pack(side='left')
            
            value_label = tk.Label(
                frame, text='0',
                font=('Arial', 11, 'bold'),
                fg=color, bg=COLORS['panel_bg'],
                anchor='e'
            )
            value_label.pack(side='right')
            
            self.behavior_labels[key] = value_label
    
    def update_stats(self, stats: dict):
        """Update displayed statistics."""
        self.stats.update(stats)
        
        # Update main stats
        self.stat_labels['tick'].config(text=str(self.stats['current_tick']))
        self.stat_labels['reach'].config(text=str(self.stats['total_reach']))
        self.stat_labels['shares'].config(text=str(self.stats['total_shares']))
        self.stat_labels['flags'].config(text=str(self.stats['total_flags']))
        
        # Update truth values
        self.truth_labels['true'].config(text=str(self.stats['true_posts']))
        self.truth_labels['false'].config(text=str(self.stats['false_posts']))
        self.truth_labels['mixed'].config(text=str(self.stats['mixed_posts']))
        self.truth_labels['unverified'].config(text=str(self.stats['unverified_posts']))
    
    def update_behaviors(self, behavior: str):
        """Update behavior counts."""
        if behavior in self.behavior_counts:
            self.behavior_counts[behavior] += 1
        
        # Update display
        total_shared = (self.behavior_counts['share_immediately'] + 
                       self.behavior_counts['verify_then_share'])
        total_rejected = (self.behavior_counts['ignore'] + 
                         self.behavior_counts['verify_then_ignore'])
        total_flagged = self.behavior_counts['flag_as_suspicious']
        
        self.behavior_labels['shared'].config(text=str(total_shared))
        self.behavior_labels['rejected'].config(text=str(total_rejected))
        self.behavior_labels['flagged'].config(text=str(total_flagged))


class PostInfoPanel(ttk.Frame):
    """Panel showing current post information."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style='Dark.TFrame')
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create widgets for post info display."""
        # Title
        tk.Label(
            self, text="📬 Current Post",
            font=('Arial', 12, 'bold'),
            fg=COLORS['accent'], bg=COLORS['panel_bg']
        ).pack(pady=(10, 5))
        
        # Post subject
        self.subject_label = tk.Label(
            self, text="Waiting for post...",
            font=('Arial', 10),
            fg=COLORS['text'], bg=COLORS['panel_bg'],
            wraplength=200,
            justify='left'
        )
        self.subject_label.pack(fill='x', padx=10, pady=5)
        
        # Truth value
        self.truth_label = tk.Label(
            self, text="",
            font=('Arial', 11, 'bold'),
            fg=COLORS['text'], bg=COLORS['panel_bg']
        )
        self.truth_label.pack(fill='x', padx=10, pady=2)
        
        # Stats
        self.stats_label = tk.Label(
            self, text="",
            font=('Arial', 9),
            fg=COLORS['text_dim'], bg=COLORS['panel_bg']
        )
        self.stats_label.pack(fill='x', padx=10, pady=5)
    
    def update_post(self, post: Optional[Post]):
        """Update the displayed post information."""
        if post is None:
            self.subject_label.config(text="Waiting for post...")
            self.truth_label.config(text="")
            self.stats_label.config(text="")
            return
        
        # Update subject
        subject = post.subject[:50] + "..." if len(post.subject) > 50 else post.subject
        self.subject_label.config(text=subject)
        
        # Update truth value with color
        truth_colors = {
            'true': COLORS['true'],
            'false': COLORS['false'],
            'mixed': COLORS['mixed'],
            'unverified': COLORS['unverified'],
        }
        truth_value = post.truth_value.value
        color = truth_colors.get(truth_value, COLORS['text'])
        
        truth_icons = {'true': '✓', 'false': '✗', 'mixed': '◐', 'unverified': '?'}
        icon = truth_icons.get(truth_value, '?')
        
        self.truth_label.config(
            text=f"{icon} {truth_value.upper()}",
            fg=color
        )
        
        # Update stats
        self.stats_label.config(
            text=f"Shares: {post.share_count} | Reach: {post.reach_count}"
        )


class LegendPanel(ttk.Frame):
    """Panel showing the legend for agent types."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style='Dark.TFrame')
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create legend widgets."""
        tk.Label(
            self, text="📋 Legend",
            font=('Arial', 11, 'bold'),
            fg=COLORS['accent'], bg=COLORS['panel_bg']
        ).pack(pady=(10, 5))
        
        # Agent types
        agent_types = [
            ('🔴 Immediate Sharer', COLORS['agent_immediate_sharer']),
            ('🟢 Cautious Sharer', COLORS['agent_cautious_sharer']),
            ('🔵 Skeptic', COLORS['agent_skeptic']),
            ('🟡 Influencer', COLORS['agent_influencer']),
            ('⚪ Lurker', COLORS['agent_lurker']),
        ]
        
        for text, color in agent_types:
            frame = tk.Frame(self, bg=COLORS['panel_bg'])
            frame.pack(fill='x', padx=10, pady=1)
            
            # Color indicator
            canvas = tk.Canvas(frame, width=12, height=12, 
                             bg=COLORS['panel_bg'], highlightthickness=0)
            canvas.pack(side='left', padx=(0, 5))
            canvas.create_oval(2, 2, 10, 10, fill=color, outline='white')
            
            tk.Label(
                frame, text=text,
                font=('Arial', 9),
                fg=COLORS['text_dim'], bg=COLORS['panel_bg']
            ).pack(side='left')
        
        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=5, padx=10)
        
        # States
        tk.Label(
            self, text="Node States:",
            font=('Arial', 10, 'bold'),
            fg=COLORS['text'], bg=COLORS['panel_bg']
        ).pack(anchor='w', padx=10, pady=(5, 2))
        
        states = [
            ('Received', COLORS['received']),
            ('Shared', COLORS['shared']),
            ('Rejected/Flagged', COLORS['rejected']),
        ]
        
        for text, color in states:
            frame = tk.Frame(self, bg=COLORS['panel_bg'])
            frame.pack(fill='x', padx=10, pady=1)
            
            canvas = tk.Canvas(frame, width=12, height=12,
                             bg=COLORS['panel_bg'], highlightthickness=0)
            canvas.pack(side='left', padx=(0, 5))
            canvas.create_oval(2, 2, 10, 10, fill=color, outline='white')
            
            tk.Label(
                frame, text=text,
                font=('Arial', 9),
                fg=COLORS['text_dim'], bg=COLORS['panel_bg']
            ).pack(side='left')


class SimulationVisualizer:
    """
    Main visualization class for the Agent Office simulation.
    
    Provides a real-time visual representation of the social network
    and post spreading dynamics.
    """
    
    def __init__(
        self,
        title: str = "Agent Office - Simulation Visualizer",
        width: int = 1200,
        height: int = 800
    ):
        """Initialize the visualizer."""
        self.title = title
        self.width = width
        self.height = height
        
        # Main window
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg=COLORS['background'])
        
        # Configure styles
        self._configure_styles()
        
        # Create main layout
        self._create_layout()
        
        # State
        self.network: Optional[SocialNetwork] = None
        self.simulation: Optional[Simulation] = None
        self.current_post: Optional[Post] = None
        self.is_running = False
        
        # Animation
        self.animation_speed = 500  # ms between updates
        self.after_id = None
    
    def _configure_styles(self):
        """Configure ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Dark.TFrame', background=COLORS['panel_bg'])
        style.configure('Dark.TLabel', background=COLORS['panel_bg'], 
                       foreground=COLORS['text'])
        style.configure('Dark.TButton', background=COLORS['accent'],
                       foreground='white')
    
    def _create_layout(self):
        """Create the main layout."""
        # Main container
        main_frame = tk.Frame(self.root, bg=COLORS['background'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left panel (canvas)
        left_frame = tk.Frame(main_frame, bg=COLORS['background'])
        left_frame.pack(side='left', fill='both', expand=True)
        
        # Canvas for network visualization
        canvas_width = self.width - 280
        canvas_height = self.height - 100
        
        self.canvas = NetworkCanvas(left_frame, width=canvas_width, height=canvas_height)
        self.canvas.pack(fill='both', expand=True)
        
        # Control bar
        control_frame = tk.Frame(left_frame, bg=COLORS['panel_bg'], height=40)
        control_frame.pack(fill='x', pady=(10, 0))
        
        # Control buttons
        self.start_btn = tk.Button(
            control_frame, text="▶ Start", 
            command=self._on_start,
            bg=COLORS['success'], fg='white',
            font=('Arial', 10, 'bold'),
            width=10
        )
        self.start_btn.pack(side='left', padx=10, pady=5)
        
        self.pause_btn = tk.Button(
            control_frame, text="⏸ Pause",
            command=self._on_pause,
            bg=COLORS['warning'], fg='white',
            font=('Arial', 10, 'bold'),
            width=10,
            state='disabled'
        )
        self.pause_btn.pack(side='left', padx=5, pady=5)
        
        self.reset_btn = tk.Button(
            control_frame, text="🔄 Reset",
            command=self._on_reset,
            bg=COLORS['danger'], fg='white',
            font=('Arial', 10, 'bold'),
            width=10
        )
        self.reset_btn.pack(side='left', padx=5, pady=5)
        
        # Speed control
        tk.Label(
            control_frame, text="Speed:",
            bg=COLORS['panel_bg'], fg=COLORS['text'],
            font=('Arial', 10)
        ).pack(side='left', padx=(20, 5), pady=5)
        
        self.speed_scale = tk.Scale(
            control_frame, from_=100, to=2000,
            orient='horizontal', length=150,
            bg=COLORS['panel_bg'], fg=COLORS['text'],
            highlightthickness=0,
            command=self._on_speed_change
        )
        self.speed_scale.set(500)
        self.speed_scale.pack(side='left', padx=5, pady=5)
        
        # Right panel (stats and info)
        right_frame = tk.Frame(main_frame, bg=COLORS['panel_bg'], width=250)
        right_frame.pack(side='right', fill='y', padx=(10, 0))
        right_frame.pack_propagate(False)
        
        # Stats panel
        self.stats_panel = StatsPanel(right_frame)
        self.stats_panel.pack(fill='x', pady=5)
        
        # Post info panel
        self.post_info_panel = PostInfoPanel(right_frame)
        self.post_info_panel.pack(fill='x', pady=5)
        
        # Legend panel
        self.legend_panel = LegendPanel(right_frame)
        self.legend_panel.pack(fill='x', pady=5)
    
    def set_network(self, network: SocialNetwork):
        """Set the network to visualize."""
        self.network = network
        agents = network.get_all_agents()
        
        # Calculate layout
        self.canvas.calculate_layout(agents, network)
        
        # Draw initial network
        self.canvas.draw_network(network)
    
    def set_simulation(self, simulation: Simulation):
        """Set the simulation to visualize."""
        self.simulation = simulation
    
    def _on_start(self):
        """Handle start button click."""
        if self.simulation:
            self.is_running = True
            self.start_btn.config(state='disabled')
            self.pause_btn.config(state='normal')
            self._run_simulation_step()
    
    def _on_pause(self):
        """Handle pause button click."""
        self.is_running = False
        self.start_btn.config(state='normal')
        self.pause_btn.config(state='disabled')
        
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
    
    def _on_reset(self):
        """Handle reset button click."""
        self.is_running = False
        self.start_btn.config(state='normal')
        self.pause_btn.config(state='disabled')
        
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        
        # Reset agent states
        for av in self.canvas.agent_visuals.values():
            av.current_state = 'default'
            av.pulse_animation = 0
        
        # Redraw network
        if self.network:
            self.canvas.draw_network(self.network)
        
        # Reset stats
        self.stats_panel.stats = {k: 0 for k in self.stats_panel.stats}
        self.stats_panel.behavior_counts = {k: 0 for k in self.stats_panel.behavior_counts}
        self.stats_panel.update_stats({})
    
    def _on_speed_change(self, value):
        """Handle speed slider change."""
        self.animation_speed = int(value)
    
    def _run_simulation_step(self):
        """Run a single step of the simulation."""
        if not self.is_running or not self.simulation:
            return
        
        # Run simulation tick
        events = self.simulation.tick()
        
        # Process events
        for event in events:
            self._process_event(event)
        
        # Update statistics
        self._update_statistics()
        
        # Animate
        self.canvas.animate_pulse()
        self.canvas.clear_active_edges()
        
        # Schedule next step
        if self.is_running and (events or self.simulation.pending_shares):
            self.after_id = self.root.after(self.animation_speed, self._run_simulation_step)
        else:
            # Simulation complete
            self.is_running = False
            self.start_btn.config(state='normal')
            self.pause_btn.config(state='disabled')
    
    def _process_event(self, event: SimulationEvent):
        """Process a simulation event and update visualization."""
        # Get agent visual
        av = self.canvas.agent_visuals.get(event.agent_id)
        if not av:
            return
        
        # Update current post
        if self.simulation:
            post = self.simulation.posts.get(event.post_id)
            if post:
                self.current_post = post
                self.post_info_panel.update_post(post)
        
        # Determine state based on behavior
        state_map = {
            'share_immediately': 'shared',
            'verify_then_share': 'shared',
            'verify_then_ignore': 'rejected',
            'ignore': 'rejected',
            'flag_as_suspicious': 'flagged',
        }
        
        state = state_map.get(event.behavior, 'default')
        
        # Update agent visual
        self.canvas.update_agent_state(event.agent_id, state)
        
        # Update behavior counts
        self.stats_panel.update_behaviors(event.behavior)
        
        # Highlight edge if from another agent
        if event.details.get('from_agent'):
            from_name = event.details['from_agent']
            # Find from agent ID
            for aid, aav in self.canvas.agent_visuals.items():
                if aav.agent.name == from_name:
                    color = COLORS['shared'] if state == 'shared' else COLORS['rejected']
                    self.canvas.highlight_edge(aid, event.agent_id, color)
                    break
    
    def _update_statistics(self):
        """Update the statistics panel."""
        if not self.simulation:
            return
        
        # Count posts by truth value
        truth_counts = {'true': 0, 'false': 0, 'mixed': 0, 'unverified': 0}
        total_shares = 0
        total_reach = 0
        total_flags = 0
        
        for post in self.simulation.posts.values():
            truth_counts[post.truth_value.value] += 1
            total_shares += post.share_count
            total_reach += post.reach_count
            total_flags += post.flagged_count
        
        stats = {
            'current_tick': self.simulation.current_tick,
            'total_shares': total_shares,
            'total_reach': total_reach,
            'total_flags': total_flags,
            'true_posts': truth_counts['true'],
            'false_posts': truth_counts['false'],
            'mixed_posts': truth_counts['mixed'],
            'unverified_posts': truth_counts['unverified'],
        }
        
        self.stats_panel.update_stats(stats)
    
    def run(self):
        """Start the visualization main loop."""
        self.root.mainloop()
    
    def close(self):
        """Close the visualization window."""
        self.is_running = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.root.destroy()


def create_visualization(
    network: SocialNetwork,
    simulation: Simulation,
    title: str = "Agent Office - Simulation Visualizer"
) -> SimulationVisualizer:
    """
    Create and return a visualization for a simulation.
    
    Args:
        network: The social network to visualize
        simulation: The simulation to run
        title: Window title
        
    Returns:
        SimulationVisualizer instance
    """
    visualizer = SimulationVisualizer(title=title)
    visualizer.set_network(network)
    visualizer.set_simulation(simulation)
    return visualizer
