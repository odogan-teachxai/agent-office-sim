"""
Logger module - Handles terminal output and JSON persistence for the simulation.

Uses Python's built-in logging module for terminal output.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import asdict
import sys

from .simulation import SimulationEvent, SimulationStats


# Module-level logger for agent_office
_logger = logging.getLogger("agent_office")


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class SimulationLogger:
    """
    Logger for the Agent Office simulation.
    
    Handles both terminal output (with colors) and JSON file persistence.
    """
    
    def __init__(
        self,
        output_dir: str = "output",
        log_file: Optional[str] = None,
        verbose: bool = True,
        use_colors: bool = True
    ):
        """
        Initialize the logger.
        
        Args:
            output_dir: Directory for output files
            log_file: Name of the JSON log file (auto-generated if None)
            verbose: Whether to print to terminal
            use_colors: Whether to use ANSI colors in terminal output
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"simulation_{timestamp}.json"
        
        self.log_file = self.output_dir / log_file
        self.verbose = verbose
        self.use_colors = use_colors and self._supports_color()
        
        # Set up stdlib logger for terminal output
        self._logger = logging.getLogger(f"agent_office.simulation.{id(self)}")
        self._logger.setLevel(logging.DEBUG if verbose else logging.WARNING)
        self._logger.handlers.clear()  # Avoid duplicate handlers
        
        if verbose:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            # Simple formatter; colors are embedded in messages via _colorize
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
        
        # Initialize log structure
        self.log_data = {
            "metadata": {
                "start_time": datetime.now().isoformat(),
                "log_file": str(self.log_file)
            },
            "events": [],
            "final_report": None
        }
        
        # Print header
        if self.verbose:
            self._print_header()
    
    def _supports_color(self) -> bool:
        """Check if terminal supports colors."""
        # Check if we're in a TTY
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if self.use_colors:
            return f"{color}{text}{Colors.ENDC}"
        return text
    
    def _print_header(self) -> None:
        """Print simulation header."""
        header = """
╔══════════════════════════════════════════════════════════════╗
║                    🏢 AGENT OFFICE 🏢                        ║
║           Social Network Information Spread Simulation        ║
╚══════════════════════════════════════════════════════════════╝
"""
        self._logger.info(self._colorize(header, Colors.CYAN + Colors.BOLD))
    
    def log_event(self, event: SimulationEvent) -> None:
        """
        Log a simulation event.
        
        Args:
            event: The simulation event to log
        """
        # Add to log data
        event_dict = {
            "timestamp": event.timestamp.isoformat(),
            "tick": event.tick,
            "event_type": event.event_type,
            "agent_id": event.agent_id,
            "agent_name": event.agent_name,
            "post_id": event.post_id,
            "post_subject": event.post_subject,
            "behavior": event.behavior,
            "details": event.details
        }
        self.log_data["events"].append(event_dict)
        
        # Print to terminal
        if self.verbose:
            self._print_event(event)
        
        # Write to file periodically
        self._write_to_file()
    
    def _print_event(self, event: SimulationEvent) -> None:
        """Print an event to the terminal with colors."""
        # Format timestamp
        time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
        
        # Choose color based on behavior
        behavior_colors = {
            "share_immediately": Colors.GREEN,
            "verify_then_share": Colors.BLUE,
            "verify_then_ignore": Colors.YELLOW,
            "ignore": Colors.ENDC,
            "flag_as_suspicious": Colors.RED
        }
        color = behavior_colors.get(event.behavior, Colors.ENDC)
        
        # Format behavior
        behavior_display = event.behavior.replace("_", " ").upper()
        
        # Format agent info - include job_role if available
        agent_type = event.details.get("agent_type", "unknown")
        job_role = event.details.get("job_role")
        post_truth = event.details.get("post_truth", "unknown")
        
        # Build agent display string
        if job_role:
            agent_display = f"{agent_type} | {job_role}"
        else:
            agent_display = agent_type
        
        # Truth indicator
        truth_indicator = self._get_truth_indicator(post_truth)
        
        # Print event line
        tick_str = f"[T{event.tick:04d}]"
        time_str_short = f"[{time_str}]"
        
        line = (
            f"{self._colorize(tick_str, Colors.CYAN)} "
            f"{self._colorize(time_str_short, Colors.BLUE)} "
            f"{self._colorize(event.agent_name, Colors.BOLD)} "
            f"({agent_display}) → "
            f"{self._colorize(behavior_display, color)} "
            f"{truth_indicator} "
            f'"{event.post_subject[:40]}..."'
        )
        
        self._logger.info(line)
        
        # Print additional details for interesting events
        if event.behavior in ["share_immediately", "verify_then_share", "flag_as_suspicious"]:
            details_line = (
                f"         └─ confidence: {event.details.get('confidence', 0):.2f}, "
                f"from: {event.details.get('from_agent', 'unknown')}, "
                f"trust: {event.details.get('trust_modifier', 0):.2f}"
            )
            self._logger.info(self._colorize(details_line, Colors.YELLOW))
    
    def _get_truth_indicator(self, truth_value: str) -> str:
        """Get a visual indicator for post truth value."""
        indicators = {
            "true": self._colorize("✓", Colors.GREEN),
            "false": self._colorize("✗", Colors.RED),
            "mixed": self._colorize("◐", Colors.YELLOW),
            "unverified": self._colorize("?", Colors.CYAN)
        }
        return indicators.get(truth_value, "?")
    
    def log_network_stats(self, stats: dict) -> None:
        """Log network statistics."""
        if self.verbose:
            self._logger.info(self._colorize("\n📊 Network Statistics:", Colors.HEADER + Colors.BOLD))
            self._logger.info(f"   Total Agents: {stats['total_agents']}")
            self._logger.info(f"   Total Connections: {stats['total_connections']}")
            self._logger.info(f"   Avg Connections/Agent: {stats['avg_connections_per_agent']}")
            
            self._logger.info(self._colorize("\n   Agent Types:", Colors.BOLD))
            for agent_type, count in stats['agent_type_distribution'].items():
                self._logger.info(f"     • {agent_type}: {count}")
            
            self._logger.info(self._colorize("\n   Most Influential:", Colors.BOLD))
            for agent in stats['most_influential']:
                self._logger.info(f"     ⭐ {agent['name']}: {agent['followers']} followers (influence: {agent['influence']:.2f})")
    
    def log_simulation_start(self, num_posts: int, num_agents: int) -> None:
        """Log simulation start."""
        if self.verbose:
            self._logger.info(self._colorize("\n🚀 Starting Simulation...", Colors.GREEN + Colors.BOLD))
            self._logger.info(f"   Agents: {num_agents}")
            self._logger.info(f"   Posts: {num_posts}")
            self._logger.info(self._colorize("\n📋 Event Log:", Colors.HEADER + Colors.BOLD))
            self._logger.info("─" * 80)
    
    def log_simulation_end(self, stats: SimulationStats, report: dict) -> None:
        """Log simulation end with final statistics."""
        self.log_data["final_report"] = report
        self.log_data["metadata"]["end_time"] = datetime.now().isoformat()
        
        if self.verbose:
            self._logger.info("─" * 80)
            self._logger.info(self._colorize("\n✅ Simulation Complete!\n", Colors.GREEN + Colors.BOLD))
            
            self._logger.info(self._colorize("📈 Simulation Statistics:", Colors.HEADER + Colors.BOLD))
            self._logger.info(f"   Total Ticks: {stats.total_ticks}")
            self._logger.info(f"   Total Shares: {stats.total_shares}")
            self._logger.info(f"   Total Flags: {stats.total_flags}")
            self._logger.info(f"   True Posts Shared: {stats.true_posts_shared}")
            self._logger.info(f"   False Posts Shared: {stats.false_posts_shared}")
            self._logger.info(f"   True/False Ratio: {stats.true_posts_shared / max(1, stats.false_posts_shared):.2f}")
            
            self._logger.info(self._colorize("\n📝 Post Statistics:", Colors.HEADER + Colors.BOLD))
            for post_stats in report.get('post_stats', []):
                truth_icon = "✓" if post_stats['truth_value'] == 'true' else "✗" if post_stats['truth_value'] == 'false' else "?"
                self._logger.info(f"   [{truth_icon}] {post_stats['subject'][:35]}...")
                self._logger.info(f"       Shares: {post_stats['share_count']}, Reach: {post_stats['reach_count']}, "
                      f"Virality: {post_stats['virality_score']:.2f}")
            
            self._logger.info(self._colorize("\n👥 Agent Statistics:", Colors.HEADER + Colors.BOLD))
            for agent_stats in sorted(report.get('agent_stats', []), key=lambda x: x['posts_shared'], reverse=True)[:5]:
                # Include job_role in display if available
                job_role = agent_stats.get('job_role')
                if job_role:
                    agent_display = f"{agent_stats['type']} | {job_role}"
                else:
                    agent_display = agent_stats['type']
                self._logger.info(f"   {agent_stats['name']} ({agent_display})")
                self._logger.info(f"       Shared: {agent_stats['posts_shared']}, Seen: {agent_stats['posts_seen']}, "
                      f"Rate: {agent_stats['share_rate']:.2f}")
        
        # Final write to file
        self._write_to_file()
        
        if self.verbose:
            self._logger.info(self._colorize(f"\n💾 Log saved to: {self.log_file}", Colors.CYAN))
    
    def _write_to_file(self) -> None:
        """Write log data to JSON file."""
        with open(self.log_file, 'w') as f:
            json.dump(self.log_data, f, indent=2, default=str)
    
    def get_log_file_path(self) -> Path:
        """Get the path to the log file."""
        return self.log_file
