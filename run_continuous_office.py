#!/usr/bin/env python3
"""
Continuous Office Simulation - A Living, Breathing Office

This simulation runs indefinitely, showing a live office where:
- Agents work on tasks in their respective job roles
- Tasks contribute to product development (software, features, etc.)
- Products progress through stages: Planning → Development → Testing → Ready → Shipped
- When tasks complete, agents post about their work
- Posts spread through the network with reactions based on traits
- Press 'P' to pause/resume the simulation
- Press 'Q' or Ctrl+C to quit

The office generates new tasks and products automatically as needed.
"""

import sys
import time
import random
import threading
import os
from datetime import datetime
from typing import Optional

# Keyboard handling - platform specific
try:
    import termios
    import tty
    import select
    POSIX = True
except ImportError:
    POSIX = False
    import msvcrt

from agent_office import (
    Agent, AgentType, JobRole, create_agent_from_type,
    create_sample_posts, Post, PostCategory, TruthValue,
    SocialNetwork, Simulation,
    Office, OfficeTask, SAMPLE_TASKS, SAMPLE_PRODUCTS,
    TaskType
)
from agent_office.logger import Colors


class ContinuousOfficeSimulation:
    """
    A continuous office simulation that runs until manually stopped.
    Supports pause/resume with 'P' key.
    """
    
    def __init__(self, tick_delay: float = 1.0):
        self.tick_delay = tick_delay
        self.paused = False
        self.running = True
        self.tick_count = 0
        
        # Setup colors
        self.colors = Colors()
        self.c = lambda text, color: f"{color}{text}{self.colors.ENDC}"
        
        # Create office team
        self.team = self._create_team()
        
        # Create office with products
        self.office = Office("TechCorp HQ")
        for agent in self.team:
            self.office.add_agent(agent)
        
        # Add initial products
        for product in SAMPLE_PRODUCTS[:3]:
            self.office.add_product(product)
        
        # Add initial tasks
        self._generate_tasks(5)
        
        # Create network
        self.network = SocialNetwork()
        for agent in self.team:
            self.network.add_agent(agent)
        self.network.create_preferential_attachment_network(avg_connections=3)
        
        # Create simulation
        self.sim = Simulation(
            network=self.network,
            tick_delay=0,
            on_event=None,
            office=self.office,
            on_office_event=None
        )
        
        # Add some initial posts
        self._add_random_posts(2)
        
        # Statistics tracking
        self.stats = {
            'tasks_completed': 0,
            'products_shipped': 0,
            'products_advanced': 0,
            'posts_created': 0,
            'total_shares': 0,
            'total_flags': 0
        }
        
        # Recent events for display
        self.recent_events: list[str] = []
        self.max_events = 15
        
        # Keyboard thread
        self.keyboard_thread: Optional[threading.Thread] = None
    
    def _create_team(self) -> list[Agent]:
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
    
    def _generate_tasks(self, count: int):
        """Generate new tasks for the office."""
        for _ in range(count):
            template = random.choice(SAMPLE_TASKS)
            task = OfficeTask(
                title=template.title,
                description=template.description,
                task_type=template.task_type,
                difficulty=random.uniform(0.3, 0.8)
            )
            self.office.add_task(task)
    
    def _add_random_posts(self, count: int):
        """Add random initial posts."""
        posts = create_sample_posts()
        for post in random.sample(posts, min(count, len(posts))):
            agent = random.choice(self.team)
            self.sim.add_post(post, agent)
    
    def _get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """Find agent by ID."""
        for agent in self.team:
            if agent.id == agent_id:
                return agent
        return None
    
    def _add_event(self, message: str):
        """Add an event to the recent events list."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_events.append(f"[{timestamp}] {message}")
        if len(self.recent_events) > self.max_events:
            self.recent_events.pop(0)
    
    def _clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _draw_dashboard(self):
        """Draw the live dashboard."""
        self._clear_screen()
        
        c = self.c
        colors = self.colors
        
        # Header
        print(c("╔" + "═" * 78 + "╗", colors.CYAN + colors.BOLD))
        status = "⏸️  PAUSED" if self.paused else "▶️  RUNNING"
        header_text = f"🏢 TECHCORP HQ - Continuous Office Simulation - {status} - Tick {self.tick_count}"
        print(c("║" + header_text.center(78) + "║", colors.CYAN + colors.BOLD))
        print(c("╚" + "═" * 78 + "╝", colors.CYAN + colors.BOLD))
        
        # Products Section
        print(c("\n📦 ACTIVE PRODUCTS", colors.GREEN + colors.BOLD))
        print("-" * 80)
        active_products = self.office.get_active_products()[:5]
        if active_products:
            for product in active_products:
                progress_bar = self._make_progress_bar(product.get_progress(), 20)
                status_icon = {
                    'planning': '📋',
                    'in_development': '💻',
                    'testing': '🧪',
                    'ready': '✅',
                    'shipped': '🚀'
                }.get(product.status.value, '•')
                
                contributors = len(product.contributors)
                print(f"  {status_icon} {product.name:25} {progress_bar} "
                      f"{product.get_progress():>3.0%} | {product.status.value:15} | "
                      f"{contributors} contributors")
        else:
            print("  (No active products - all shipped!)")
        
        # Team Activity Section
        print(c("\n👥 TEAM ACTIVITY", colors.YELLOW + colors.BOLD))
        print("-" * 80)
        print(f"  {'Name':<10} {'Role':<18} {'Status':<25} {'Current Task':<20}")
        print("  " + "-" * 76)
        
        for agent in sorted(self.team, key=lambda a: a.name):
            job = agent.job_role.value if agent.job_role else "none"
            
            # Find current task
            agent_tasks = self.office.get_tasks_for_agent(agent)
            in_progress = [t for t in agent_tasks if t.status.value == 'in_progress']
            
            if in_progress:
                task = in_progress[0]
                status = f"Working ({task.progress:.0%})"
                task_name = task.title[:18]
            elif agent_tasks:
                status = "📋 Assigned"
                task_name = agent_tasks[0].title[:18]
            else:
                status = "🟢 Available"
                task_name = "-"
            
            print(f"  {agent.name:<10} {job:<18} {status:<25} {task_name:<20}")
        
        # Recent Events Section
        print(c("\n📰 RECENT EVENTS (Press 'P' to pause/resume, 'Q' to quit)", colors.HEADER + colors.BOLD))
        print("-" * 80)
        if self.recent_events:
            for event in self.recent_events[-10:]:
                print(f"  {event}")
        else:
            print("  (Waiting for events...)")
        
        # Statistics Section
        print(c("\n📊 STATISTICS", colors.BLUE + colors.BOLD))
        print("-" * 80)
        office_stats = self.office.get_stats()
        print(f"  Tasks: {office_stats['completed']} completed | {office_stats['in_progress']} in progress | "
              f"{office_stats['pending']} pending")
        print(f"  Products: {office_stats['shipped_products']} shipped | {office_stats['active_products']} active | "
              f"{office_stats['products_ready_to_ship']} ready")
        print(f"  Info Spread: {self.sim.stats.total_shares} shares | {self.sim.stats.total_flags} flags | "
              f"{len(self.sim.posts)} posts active")
        
        # Footer
        print("\n" + "─" * 80)
        print("  Controls: [P] Pause/Resume  [Q] Quit")
    
    def _make_progress_bar(self, progress: float, width: int = 20) -> str:
        """Create a text progress bar."""
        filled = int(progress * width)
        empty = width - filled
        return "█" * filled + "░" * empty
    
    def _check_keyboard(self):
        """Check for keyboard input (platform specific)."""
        if POSIX:
            return self._check_keyboard_posix()
        else:
            return self._check_keyboard_windows()
    
    def _check_keyboard_posix(self) -> Optional[str]:
        """Check for keyboard input on POSIX systems."""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None
    
    def _check_keyboard_windows(self) -> Optional[str]:
        """Check for keyboard input on Windows."""
        if msvcrt.kbhit():
            return msvcrt.getch().decode('utf-8', errors='ignore')
        return None
    
    def _keyboard_loop(self):
        """Background thread for keyboard handling."""
        # Setup terminal for raw input on POSIX
        old_settings = None
        if POSIX:
            try:
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except:
                # Not a real terminal, skip keyboard handling
                return
        
        try:
            while self.running:
                key = self._check_keyboard()
                if key:
                    key = key.upper()
                    if key == 'P':
                        self.paused = not self.paused
                        status = "PAUSED" if self.paused else "RESUMED"
                        self._add_event(f"⏸️  Simulation {status} by user")
                    elif key == 'Q':
                        self.running = False
                        self._add_event("🛑 Quit requested by user")
                time.sleep(0.05)
        finally:
            # Restore terminal settings on POSIX
            if POSIX and old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except:
                    pass
    
    def _generate_dynamic_content(self):
        """Generate new tasks and posts dynamically."""
        # Generate new tasks if running low
        pending = self.office.get_pending_tasks()
        if len(pending) < 3:
            self._generate_tasks(random.randint(2, 4))
            self._add_event(f"📥 Generated {random.randint(2, 4)} new tasks")
        
        # Generate new products if all shipped
        active = self.office.get_active_products()
        if len(active) == 0:
            from agent_office.office import Product, TaskType
            new_product = Product(
                name=f"Project {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Omega'])}",
                description="Auto-generated initiative",
                product_type=random.choice([TaskType.CODING, TaskType.DESIGNING, TaskType.PLANNING]),
                tasks_required=random.randint(4, 8)
            )
            self.office.add_product(new_product)
            self._add_event(f"🎯 New product created: {new_product.name}")
        
        # Occasionally add random info posts
        if random.random() < 0.1:  # 10% chance per tick
            posts = create_sample_posts()
            post = random.choice(posts)
            agent = random.choice(self.team)
            self.sim.add_post(post, agent)
            self.stats['posts_created'] += 1
    
    def _process_events(self):
        """Process simulation events and update display."""
        # Run one tick
        events = self.sim.tick()
        self.tick_count += 1
        
        # Process info-spread events
        for event in events:
            self.stats['total_shares'] += 1
            
            # Determine if it's a work post
            is_work = any(wp['post_id'] == event.post_id for wp in self.sim.work_posts_generated)
            
            if is_work and random.random() < 0.3:  # Only show some reactions
                emoji = "💼"
                behavior = event.behavior.replace('_', ' ').title()
                self._add_event(f"{emoji} {event.agent_name} {behavior}: {event.post_subject[:25]}...")
        
        # Process office events
        tick_office_events = [e for e in self.sim.office_events if e['tick'] == self.sim.current_tick - 1]
        
        for e in tick_office_events:
            if e['event_type'] == 'task_completed':
                self.stats['tasks_completed'] += 1
                
                # Task completion event
                agent_name = e['agent_name']
                task_title = e['task_title'][:20]
                self._add_event(f"✅ {agent_name} completed: {task_title}")
                
                # Product advancement
                if e.get('product_advanced'):
                    product_name = e.get('product_name', 'Unknown')
                    self.stats['products_advanced'] += 1
                    self._add_event(f"🚀 Product '{product_name}' advanced to next stage!")
        
        # Check for shipped products
        for product in self.office.shipped_products:
            if not hasattr(product, '_shipped_logged'):
                product._shipped_logged = True
                self.stats['products_shipped'] += 1
                self._add_event(f"🎉 PRODUCT SHIPPED: {product.name}!")
                
                # Create celebration post
                celebration_post = Post(
                    subject=f"🚀 {product.name} is LIVE!",
                    content=f"We're excited to announce that {product.name} has been shipped! "
                            f"Thanks to all {len(product.contributors)} team members who contributed. "
                            f"Total development time: {product.total_tasks_contributed} tasks completed.",
                    category=PostCategory.NEWS,
                    truth_value=TruthValue.TRUE,
                    emotional_intensity=0.8,
                    credibility_score=1.0,
                    source_reliability=1.0
                )
                # Find a PM or random agent to post
                pms = [a for a in self.team if a.job_role == JobRole.PROJECT_MANAGER]
                poster = random.choice(pms) if pms else random.choice(self.team)
                self.sim.add_post(celebration_post, poster)
    
    def run(self):
        """Run the continuous simulation."""
        # Start keyboard thread
        self.keyboard_thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        self.keyboard_thread.start()
        
        try:
            # Initial display
            self._draw_dashboard()
            
            while self.running:
                if not self.paused:
                    # Process simulation tick
                    self._process_events()
                    
                    # Generate dynamic content
                    self._generate_dynamic_content()
                    
                    # Update display
                    self._draw_dashboard()
                
                # Sleep for tick delay
                time.sleep(self.tick_delay)
                
        except KeyboardInterrupt:
            self.running = False
            print("\n\n🛑 Simulation stopped by user.")
        finally:
            self.running = False
            if self.keyboard_thread:
                self.keyboard_thread.join(timeout=1.0)
        
        # Final summary
        self._show_final_summary()
    
    def _show_final_summary(self):
        """Show final simulation summary."""
        self._clear_screen()
        c = self.c
        colors = self.colors
        
        print(c("╔" + "═" * 78 + "╗", colors.GREEN + colors.BOLD))
        print(c("║" + "SIMULATION COMPLETE".center(78) + "║", colors.GREEN + colors.BOLD))
        print(c("╚" + "═" * 78 + "╝", colors.GREEN + colors.BOLD))
        
        print(f"\n📊 Final Statistics:")
        print(f"  Total Ticks: {self.tick_count}")
        print(f"  Tasks Completed: {self.stats['tasks_completed']}")
        print(f"  Products Shipped: {self.stats['products_shipped']}")
        print(f"  Products Advanced: {self.stats['products_advanced']}")
        print(f"  Posts Created: {self.stats['posts_created']}")
        print(f"  Total Shares: {self.sim.stats.total_shares}")
        print(f"  Total Flags: {self.sim.stats.total_flags}")
        
        print(f"\n📦 Products:")
        for product in self.office.products:
            status_icon = "🚀" if product.status.value == 'shipped' else "📦"
            print(f"  {status_icon} {product.name}: {product.status.value} ({product.get_progress():.0%})")
        
        print(f"\n👥 Team Contributions:")
        for agent in sorted(self.team, key=lambda a: a.name):
            tasks = len([e for e in self.sim.office_events 
                        if e['agent_id'] == agent.id and e['event_type'] == 'task_completed'])
            shares = len(agent.posts_shared)
            print(f"  {agent.name:10} ({agent.job_role.value:15}): {tasks:3} tasks, {shares:3} shares")
        
        print(f"\n{c('Thanks for running the TechCorp simulation!', colors.GREEN)}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Continuous Office Simulation - A Living, Breathing Office"
    )
    parser.add_argument(
        "--speed", "-s",
        type=float,
        default=1.0,
        help="Simulation speed in seconds per tick (default: 1.0)"
    )
    
    args = parser.parse_args()
    
    print("\n🏢 Starting Continuous Office Simulation...")
    print("   Press 'P' to pause/resume")
    print("   Press 'Q' or Ctrl+C to quit\n")
    time.sleep(2)
    
    sim = ContinuousOfficeSimulation(tick_delay=args.speed)
    sim.run()


if __name__ == "__main__":
    main()
