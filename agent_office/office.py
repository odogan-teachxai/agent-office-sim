"""
Office module - Task management and office work simulation.

This module provides a simple task system where agents with job roles
can be assigned work, complete tasks, and generate office activity.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import random
import uuid

from .agent import Agent, JobRole
from .post import Post, PostCategory, TruthValue


class TaskStatus(Enum):
    """Status of an office task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskType(Enum):
    """Types of office tasks, aligned with job roles."""
    CODING = "coding"           # For DEVELOPER
    TESTING = "testing"         # For TESTER
    PLANNING = "planning"       # For PROJECT_MANAGER
    CLEANING = "cleaning"       # For JANITOR
    DESIGNING = "designing"     # For DESIGNER
    LEARNING = "learning"       # For INTERN
    SELLING = "selling"         # For SALES_REP
    HIRING = "hiring"           # For HR_MANAGER
    MEETING = "meeting"         # Any role
    ADMIN = "admin"             # Any role


@dataclass
class OfficeTask:
    """
    Represents a unit of work in the office.
    
    Attributes:
        id: Unique task identifier
        title: Human-readable task name
        description: Detailed task description
        task_type: Category of work
        status: Current task state
        assigned_to: Agent ID who is working on this (None = unassigned)
        created_by: Agent ID who created/requested this task
        difficulty: How hard the task is (0.1 - 1.0)
        progress: Completion percentage (0.0 - 1.0)
        created_at: When task was created
        completed_at: When task was finished (None if not done)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    task_type: TaskType = TaskType.ADMIN
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    difficulty: float = 0.5
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate and clamp values."""
        self.difficulty = max(0.1, min(1.0, self.difficulty))
        self.progress = max(0.0, min(1.0, self.progress))
    
    def is_assigned(self) -> bool:
        """Check if task has an assignee."""
        return self.assigned_to is not None
    
    def is_done(self) -> bool:
        """Check if task is completed."""
        return self.status == TaskStatus.DONE
    
    def work_on(self, amount: float = 0.2) -> bool:
        """
        Progress the task by the given amount.
        Returns True if task just completed.
        """
        if self.status in [TaskStatus.DONE, TaskStatus.BLOCKED]:
            return False
        
        self.status = TaskStatus.IN_PROGRESS
        self.progress += amount / self.difficulty  # Harder tasks need more work
        
        if self.progress >= 1.0:
            self.progress = 1.0
            self.status = TaskStatus.DONE
            self.completed_at = datetime.now()
            return True
        return False
    
    def assign_to(self, agent: Agent) -> None:
        """Assign this task to an agent."""
        self.assigned_to = agent.id
        agent.current_task = self.title
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.IN_PROGRESS
    
    def unassign(self) -> None:
        """Remove assignment from this task."""
        self.assigned_to = None
        if self.status == TaskStatus.IN_PROGRESS:
            self.status = TaskStatus.PENDING
    
    def get_stats(self) -> dict:
        """Get task statistics."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.task_type.value,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "progress": round(self.progress * 100, 1),
            "difficulty": self.difficulty
        }
    
    def __repr__(self) -> str:
        return f"OfficeTask({self.title}, {self.status.value}, {self.progress:.0%})"


# Products that agents can work on (software, projects, etc.)
class ProductStatus(Enum):
    """Status of a product being developed."""
    PLANNING = "planning"
    IN_DEVELOPMENT = "in_development"
    TESTING = "testing"
    READY = "ready"
    SHIPPED = "shipped"


@dataclass
class Product:
    """
    A product being developed by the office (software, feature, etc.)
    
    Tasks contribute to product progress. When enough related tasks complete,
    the product advances to the next stage.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    product_type: TaskType = TaskType.CODING  # What type of work this product involves
    status: ProductStatus = ProductStatus.PLANNING
    
    # Progress tracking
    tasks_completed: int = 0
    tasks_required: int = 5  # Tasks needed to advance stage
    total_tasks_contributed: int = 0
    
    # Contributors
    contributors: set = field(default_factory=set)  # agent_ids who contributed
    
    # Timeline
    created_at: datetime = field(default_factory=datetime.now)
    started_development: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    
    def contribute_task(self, agent: Agent, task: OfficeTask) -> bool:
        """
        Record a task contribution to this product.
        Returns True if product advanced to next stage.
        """
        self.tasks_completed += 1
        self.total_tasks_contributed += 1
        self.contributors.add(agent.id)
        
        # Check for stage advancement
        if self.tasks_completed >= self.tasks_required:
            return self._advance_stage()
        return False
    
    def _advance_stage(self) -> bool:
        """Advance product to next stage. Returns True if advanced."""
        self.tasks_completed = 0
        self.tasks_required += 2  # Each stage needs more work
        
        if self.status == ProductStatus.PLANNING:
            self.status = ProductStatus.IN_DEVELOPMENT
            self.started_development = datetime.now()
            return True
        elif self.status == ProductStatus.IN_DEVELOPMENT:
            self.status = ProductStatus.TESTING
            return True
        elif self.status == ProductStatus.TESTING:
            self.status = ProductStatus.READY
            self.ready_at = datetime.now()
            return True
        elif self.status == ProductStatus.READY:
            self.status = ProductStatus.SHIPPED
            self.shipped_at = datetime.now()
            return True
        return False
    
    def get_progress(self) -> float:
        """Get overall progress (0.0 to 1.0)."""
        stage_progress = {
            ProductStatus.PLANNING: 0.0,
            ProductStatus.IN_DEVELOPMENT: 0.25,
            ProductStatus.TESTING: 0.6,
            ProductStatus.READY: 0.9,
            ProductStatus.SHIPPED: 1.0
        }
        base = stage_progress.get(self.status, 0.0)
        # Add partial progress within stage
        if self.status != ProductStatus.SHIPPED:
            base += (self.tasks_completed / max(1, self.tasks_required)) * 0.2
        return min(1.0, base)
    
    def __repr__(self) -> str:
        return f"Product({self.name}, {self.status.value}, {self.get_progress():.0%})"


# Sample products for the office to work on
SAMPLE_PRODUCTS = [
    Product(name="Mobile App v2.0", description="Complete redesign of mobile experience", product_type=TaskType.CODING, tasks_required=6),
    Product(name="AI Chatbot", description="Customer support automation bot", product_type=TaskType.CODING, tasks_required=8),
    Product(name="Security Audit", description="Annual security review and fixes", product_type=TaskType.TESTING, tasks_required=5),
    Product(name="Brand Redesign", description="New logo and brand guidelines", product_type=TaskType.DESIGNING, tasks_required=4),
    Product(name="Q4 Planning", description="Quarterly roadmap and OKRs", product_type=TaskType.PLANNING, tasks_required=3),
    Product(name="Database Migration", description="Move to new cloud infrastructure", product_type=TaskType.CODING, tasks_required=10),
]


# Sample tasks for demonstration
SAMPLE_TASKS = [
    OfficeTask(
        title="Fix login bug",
        description="Users can't log in with special characters in password",
        task_type=TaskType.CODING,
        difficulty=0.7
    ),
    OfficeTask(
        title="Write tests for auth module",
        description="Add unit tests for the new authentication system",
        task_type=TaskType.TESTING,
        difficulty=0.5
    ),
    OfficeTask(
        title="Clean kitchen",
        description="Empty dishwasher, wipe counters, restock coffee",
        task_type=TaskType.CLEANING,
        difficulty=0.2
    ),
    OfficeTask(
        title="Organize team meeting",
        description="Schedule and prepare agenda for weekly sync",
        task_type=TaskType.PLANNING,
        difficulty=0.3
    ),
    OfficeTask(
        title="Design new landing page",
        description="Create mockups for the marketing site redesign",
        task_type=TaskType.DESIGNING,
        difficulty=0.6
    ),
    OfficeTask(
        title="Learn Python basics",
        description="Complete online course modules 1-3",
        task_type=TaskType.LEARNING,
        difficulty=0.4
    ),
    OfficeTask(
        title="Call potential client",
        description="Follow up with Acme Corp about the proposal",
        task_type=TaskType.SELLING,
        difficulty=0.5
    ),
    OfficeTask(
        title="Review intern applications",
        description="Screen resumes for summer internship program",
        task_type=TaskType.HIRING,
        difficulty=0.4
    ),
    OfficeTask(
        title="Update documentation",
        description="Add API changes to the developer docs",
        task_type=TaskType.ADMIN,
        difficulty=0.3
    ),
    OfficeTask(
        title="Refactor legacy code",
        description="Clean up the old payment processing module",
        task_type=TaskType.CODING,
        difficulty=0.8
    ),
]


# Post templates for work accomplishments - makes the office feel alive!
TASK_COMPLETION_POSTS = {
    TaskType.CODING: [
        ("Just fixed a tricky bug!", "Finally tracked down that issue. Code is working smoothly now.", PostCategory.NEWS),
        ("Shipped new feature", "Pushed the latest update. Ready for testing!", PostCategory.NEWS),
        ("Refactor complete", "Cleaned up the legacy code. Much better now.", PostCategory.NEWS),
        ("Code review done", "Reviewed the team's PRs. Great work everyone!", PostCategory.NEWS),
    ],
    TaskType.TESTING: [
        ("Found a critical bug!", "Caught an issue before it hit production. Phew!", PostCategory.NEWS),
        ("All tests passing", "Green checkmarks across the board. Solid release.", PostCategory.NEWS),
        ("QA complete", "Finished testing the new build. Looking good!", PostCategory.NEWS),
        ("Bug report filed", "Documented some issues for the dev team to fix.", PostCategory.NEWS),
    ],
    TaskType.PLANNING: [
        ("Sprint planning done", "Set the roadmap for next week. Exciting stuff ahead!", PostCategory.NEWS),
        ("Project milestone reached", "Hit our target ahead of schedule!", PostCategory.NEWS),
        ("Team sync complete", "Great meeting everyone. Clear priorities set.", PostCategory.NEWS),
        ("Strategy updated", "Refined our approach based on feedback.", PostCategory.NEWS),
    ],
    TaskType.CLEANING: [
        ("Kitchen is spotless!", "Restocked the coffee too. You're welcome!", PostCategory.GOSSIP),
        ("Office cleanup done", "Everything organized and tidy. Feels good.", PostCategory.GOSSIP),
        ("Supplies restocked", "Paper, pens, snacks - all refilled!", PostCategory.GOSSIP),
        ("Break room refreshed", "Clean mugs and fresh coffee ready to go.", PostCategory.GOSSIP),
    ],
    TaskType.DESIGNING: [
        ("New mockups ready", "Check out the latest designs! Thoughts?", PostCategory.ENTERTAINMENT),
        ("Design system updated", "Refined our component library. Consistency is key!", PostCategory.NEWS),
        ("UI polish complete", "Those micro-interactions are smooth now.", PostCategory.ENTERTAINMENT),
        ("Brand assets done", "New logos and guidelines are ready.", PostCategory.NEWS),
    ],
    TaskType.LEARNING: [
        ("Finished my course!", "Learned so much this week. Time to apply it!", PostCategory.NEWS),
        ("New certification", "Leveled up my skills. Official now!", PostCategory.NEWS),
        ("Training complete", "Thanks to everyone who mentored me!", PostCategory.NEWS),
        ("Finally understand it!", "That concept clicked. Feels great!", PostCategory.NEWS),
    ],
    TaskType.SELLING: [
        ("Closed a big deal!", "New client signed. Great quarter ahead!", PostCategory.NEWS),
        ("Pitch went well", "Client loved our proposal. Fingers crossed!", PostCategory.NEWS),
        ("Demo success", "Product demo knocked it out of the park!", PostCategory.NEWS),
        ("New partnership", "Exciting collaboration in the works!", PostCategory.NEWS),
    ],
    TaskType.HIRING: [
        ("Welcome to the team!", "Found an amazing new hire. Starting next month!", PostCategory.GOSSIP),
        ("Interview marathon done", "Met some incredible candidates today.", PostCategory.GOSSIP),
        ("Team is growing", "Hiring is going great. Lots of talent out there!", PostCategory.NEWS),
        ("Onboarding planned", "New joiners will have a smooth first week!", PostCategory.NEWS),
    ],
    TaskType.MEETING: [
        ("Productive meeting!", "Got a lot done in that sync. Action items sent.", PostCategory.NEWS),
        ("Brainstorming session", "Some brilliant ideas came out of that!", PostCategory.NEWS),
        ("Stakeholder update", "Presented our progress. Positive feedback!", PostCategory.NEWS),
        ("Retrospective done", "Good discussion on how we can improve.", PostCategory.NEWS),
    ],
    TaskType.ADMIN: [
        ("Paperwork done", "Finally cleared that backlog. Relief!", PostCategory.NEWS),
        ("Documentation updated", "Wiki is current again. Check it out!", PostCategory.NEWS),
        ("Reports filed", "All the admin tasks caught up. Feels good!", PostCategory.NEWS),
        ("Inbox zero!", "Cleared all my emails. Rare achievement!", PostCategory.GOSSIP),
    ],
}


def create_task_completion_post(task: OfficeTask, agent: Agent) -> Post:
    """
    Create a post about a completed task.
    This connects office work to the info-spread network.
    """
    # Get templates for this task type
    templates = TASK_COMPLETION_POSTS.get(task.task_type, TASK_COMPLETION_POSTS[TaskType.ADMIN])
    
    # Pick a random template
    subject, content, category = random.choice(templates)
    
    # Personalize it with agent's name and task title
    personalized_subject = f"{agent.name}: {subject}"
    personalized_content = f"{content}\n\nJust completed: {task.title}"
    
    # Create the post
    post = Post(
        subject=personalized_subject,
        content=personalized_content,
        category=category,
        truth_value=TruthValue.TRUE,  # Work accomplishments are true!
        emotional_intensity=random.uniform(0.3, 0.6),  # Moderate excitement
        credibility_score=0.8,  # Work posts are credible
        source_reliability=0.9,  # From known colleagues
        author_id=agent.id  # Track who created this post
    )
    
    return post


def get_preferred_task_types(job_role: JobRole) -> list[TaskType]:
    """Get the task types a job role prefers to work on."""
    preferences = {
        JobRole.DEVELOPER: [TaskType.CODING, TaskType.ADMIN],
        JobRole.TESTER: [TaskType.TESTING, TaskType.CODING],
        JobRole.PROJECT_MANAGER: [TaskType.PLANNING, TaskType.MEETING, TaskType.ADMIN],
        JobRole.JANITOR: [TaskType.CLEANING],
        JobRole.DESIGNER: [TaskType.DESIGNING],
        JobRole.INTERN: [TaskType.LEARNING, TaskType.ADMIN, TaskType.CODING],
        JobRole.SALES_REP: [TaskType.SELLING, TaskType.MEETING],
        JobRole.HR_MANAGER: [TaskType.HIRING, TaskType.MEETING, TaskType.PLANNING],
    }
    return preferences.get(job_role, [TaskType.ADMIN])


class Office:
    """
    Manages office tasks and work assignments.
    
    This is a simple task board system where agents can:
    - Be assigned tasks based on their job role
    - Work on tasks (progress toward completion)
    - Complete tasks (which generates posts that spread through the network!)
    """
    
    def __init__(self, name: str = "Agent Office", on_post_create: Optional[callable] = None):
        """
        Initialize the office.
        
        Args:
            name: Office name
            on_post_create: Callback when a task completion creates a post.
                           Signature: (post: Post, author: Agent) -> None
        """
        self.name = name
        self.tasks: list[OfficeTask] = []
        self.completed_tasks: list[OfficeTask] = []
        self.agents: list[Agent] = []
        self.tick_count = 0
        
        # Products being developed
        self.products: list[Product] = []
        self.shipped_products: list[Product] = []
        self.current_product_index: int = 0  # Which product tasks should contribute to
        
        # Callbacks for integration with simulation
        self.on_task_complete: Optional[callable] = None  # (task, agent) -> None
        self.on_post_create: Optional[callable] = on_post_create  # (post, agent) -> None
        self.on_product_shipped: Optional[callable] = None  # (product) -> None (NEW)
        
        # Track posts generated by work (for logging)
        self.work_posts: list[tuple[Post, Agent, OfficeTask]] = []
        
        # Track product progress events
        self.product_events: list[dict] = []
    
    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the office."""
        if agent not in self.agents:
            self.agents.append(agent)
    
    def add_task(self, task: OfficeTask) -> None:
        """Add a task to the office backlog."""
        self.tasks.append(task)
    
    def add_product(self, product: Product) -> None:
        """Add a product to be developed."""
        self.products.append(product)
    
    def get_active_products(self) -> list[Product]:
        """Get products that are not yet shipped."""
        return [p for p in self.products if p.status != ProductStatus.SHIPPED]
    
    def get_current_focus_product(self) -> Optional[Product]:
        """Get the product that new tasks should contribute to."""
        active = self.get_active_products()
        if not active:
            return None
        # Cycle through active products
        return active[self.current_product_index % len(active)]
    
    def _contribute_to_product(self, task: OfficeTask, agent: Agent) -> Optional[Product]:
        """
        Contribute a completed task to a product.
        Returns the product if it advanced to next stage, None otherwise.
        """
        # Find a matching product for this task type
        product = self.get_current_focus_product()
        if product and product.product_type == task.task_type:
            advanced = product.contribute_task(agent, task)
            
            event = {
                'tick': self.tick_count,
                'product_id': product.id,
                'product_name': product.name,
                'agent_id': agent.id,
                'agent_name': agent.name,
                'task_title': task.title,
                'progress': product.get_progress(),
                'status': product.status.value,
                'advanced': advanced
            }
            self.product_events.append(event)
            
            if advanced:
                # Check if product shipped
                if product.status == ProductStatus.SHIPPED:
                    self.shipped_products.append(product)
                    if self.on_product_shipped:
                        self.on_product_shipped(product)
                # Move to next product for variety
                self.current_product_index += 1
            
            return product if advanced else None
        return None
    
    def get_pending_tasks(self) -> list[OfficeTask]:
        """Get all tasks that haven't been started."""
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]
    
    def get_in_progress_tasks(self) -> list[OfficeTask]:
        """Get all tasks currently being worked on."""
        return [t for t in self.tasks if t.status == TaskStatus.IN_PROGRESS]
    
    def get_tasks_for_agent(self, agent: Agent) -> list[OfficeTask]:
        """Get all tasks assigned to a specific agent."""
        return [t for t in self.tasks if t.assigned_to == agent.id]
    
    def assign_task(self, task: OfficeTask, agent: Agent) -> bool:
        """
        Assign a task to an agent.
        Returns True if successful.
        """
        if task.is_done():
            return False
        
        # Unassign from previous agent if any
        if task.is_assigned():
            prev_agent = self._get_agent_by_id(task.assigned_to)
            if prev_agent:
                prev_agent.current_task = None
        
        task.assign_to(agent)
        return True
    
    def auto_assign_task(self, task: OfficeTask) -> bool:
        """
        Try to assign a task to the best available agent based on job role.
        Returns True if assigned successfully.
        """
        if task.is_assigned() or task.is_done():
            return False
        
        # Find agents who can do this task type
        preferred_roles = self._get_roles_for_task_type(task.task_type)
        
        # Look for available agents (not busy with hard tasks)
        available = []
        for agent in self.agents:
            if agent.job_role in preferred_roles:
                current_tasks = self.get_tasks_for_agent(agent)
                # Check if agent is overloaded
                hard_tasks = sum(1 for t in current_tasks if t.difficulty > 0.6 and not t.is_done())
                if hard_tasks < 2:  # Can take more work
                    available.append(agent)
        
        if available:
            # Pick randomly from available
            chosen = random.choice(available)
            return self.assign_task(task, chosen)
        
        return False
    
    def work_on_task(self, agent: Agent, work_amount: float = 0.2) -> Optional[tuple[OfficeTask, Optional[Product]]]:
        """
        Have an agent work on their assigned task.
        Returns (task, product_advanced) if completed, None otherwise.
        When a task completes, contributes to product and generates a post!
        """
        agent_tasks = self.get_tasks_for_agent(agent)
        
        # Find an in-progress task
        for task in agent_tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                just_completed = task.work_on(work_amount * agent.productivity)
                
                if just_completed:
                    agent.current_task = None
                    self.completed_tasks.append(task)
                    self.tasks.remove(task)
                    
                    # 🎉 TASK COMPLETE! Contribute to product development
                    product_advanced = self._contribute_to_product(task, agent)
                    
                    # Generate a post about the accomplishment
                    work_post = create_task_completion_post(task, agent)
                    self.work_posts.append((work_post, agent, task))
                    
                    # Inject post into simulation if callback is set
                    if self.on_post_create:
                        self.on_post_create(work_post, agent, product_advanced)
                    
                    # Also trigger the old callback if set
                    if self.on_task_complete:
                        self.on_task_complete(task, agent)
                    
                    return task, product_advanced
                return None
        
        # No in-progress task, try to pick up a pending one
        pending = self.get_pending_tasks()
        if pending and agent.job_role:
            preferred_types = get_preferred_task_types(agent.job_role)
            # Find preferred tasks
            preferred = [t for t in pending if t.task_type in preferred_types]
            if preferred:
                task = random.choice(preferred)
                self.assign_task(task, agent)
                return None
        
        return None
    
    def agent_do_work(self, agent: Agent) -> Optional[tuple[OfficeTask, Optional[Product]]]:
        """
        Main entry point for an agent to do office work.
        Handles both continuing existing tasks and picking up new ones.
        Returns (completed_task, product_advanced) if any, None otherwise.
        """
        if not agent.job_role:
            return None
        
        return self.work_on_task(agent)
    
    def tick(self) -> list[tuple[Agent, OfficeTask, Optional[Product]]]:
        """
        Run one office tick - all agents do work.
        Returns list of (agent, completed_task, product_advanced) for tasks finished this tick.
        """
        completed = []
        
        for agent in self.agents:
            if agent.job_role:
                result = self.agent_do_work(agent)
                if result:
                    task, product = result
                    completed.append((agent, task, product))
        
        self.tick_count += 1
        return completed
    
    def get_stats(self) -> dict:
        """Get office statistics."""
        active_products = self.get_active_products()
        return {
            "name": self.name,
            "total_tasks": len(self.tasks) + len(self.completed_tasks),
            "pending": len(self.get_pending_tasks()),
            "in_progress": len(self.get_in_progress_tasks()),
            "completed": len(self.completed_tasks),
            "agents": len(self.agents),
            "ticks": self.tick_count,
            # Product stats
            "total_products": len(self.products),
            "active_products": len(active_products),
            "shipped_products": len(self.shipped_products),
            "products_ready_to_ship": len([p for p in active_products if p.status == ProductStatus.READY])
        }
    
    def get_task_board(self) -> str:
        """Get a formatted string showing the task board."""
        lines = [f"\n📋 {self.name} - Task Board", "=" * 50]
        
        lines.append("\n🔄 IN PROGRESS:")
        in_progress = self.get_in_progress_tasks()
        if in_progress:
            for t in in_progress:
                agent_name = self._get_agent_name(t.assigned_to) or "Unassigned"
                lines.append(f"  [{t.progress:>3.0%}] {t.title} ({agent_name})")
        else:
            lines.append("  (none)")
        
        lines.append("\n📥 PENDING:")
        pending = self.get_pending_tasks()[:5]  # Show first 5
        if pending:
            for t in pending:
                lines.append(f"  [NEW] {t.title} ({t.task_type.value})")
            if len(self.get_pending_tasks()) > 5:
                lines.append(f"  ... and {len(self.get_pending_tasks()) - 5} more")
        else:
            lines.append("  (none)")
        
        lines.append(f"\n✅ COMPLETED: {len(self.completed_tasks)} tasks")
        
        return "\n".join(lines)
    
    def _get_agent_by_id(self, agent_id: Optional[str]) -> Optional[Agent]:
        """Look up an agent by ID."""
        if not agent_id:
            return None
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None
    
    def _get_agent_name(self, agent_id: Optional[str]) -> Optional[str]:
        """Get an agent's name by ID."""
        agent = self._get_agent_by_id(agent_id)
        return agent.name if agent else None
    
    def _get_roles_for_task_type(self, task_type: TaskType) -> list[JobRole]:
        """Get job roles that can do a given task type."""
        mapping = {
            TaskType.CODING: [JobRole.DEVELOPER, JobRole.INTERN],
            TaskType.TESTING: [JobRole.TESTER, JobRole.DEVELOPER],
            TaskType.PLANNING: [JobRole.PROJECT_MANAGER, JobRole.HR_MANAGER],
            TaskType.CLEANING: [JobRole.JANITOR],
            TaskType.DESIGNING: [JobRole.DESIGNER],
            TaskType.LEARNING: [JobRole.INTERN],
            TaskType.SELLING: [JobRole.SALES_REP],
            TaskType.HIRING: [JobRole.HR_MANAGER],
            TaskType.MEETING: list(JobRole),  # Anyone can attend meetings
            TaskType.ADMIN: list(JobRole),    # Anyone can do admin
        }
        return mapping.get(task_type, list(JobRole))
    
    def __repr__(self) -> str:
        return f"Office({self.name}, tasks={len(self.tasks)}, agents={len(self.agents)})"
