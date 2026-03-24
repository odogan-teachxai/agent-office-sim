#!/usr/bin/env python3
"""
Agent Office 3D Simulation — Full Game-like Visualization

A complete Pygame 3D visualization that integrates the entire simulation system:
- True 3D camera with yaw/pitch rotation
- Wall collision and A* pathfinding
- Task progress bars above agent heads
- Post creation bubbles
- Live terminal-style event log
- Full simulation integration (info-spread + office work)

Controls:
  - Left-click + drag: Rotate view (yaw)
  - Right-click + drag: Tilt view (pitch)
  - Scroll wheel: Zoom in/out
  - P: Pause/Resume simulation
  - R: Reset camera
  - Q or ESC: Quit
"""

import pygame
import math
import sys
import random
from collections import deque
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, '.')

from agent_office.agent import Agent, AgentType, JobRole, create_agent_from_type
from agent_office.network import SocialNetwork
from agent_office.post import Post, PostCategory, TruthValue
from agent_office.office import Office, OfficeTask, TaskType, TaskStatus
from agent_office.simulation import Simulation, SimulationEvent

# ============================================================================
# CONFIGURATION
# ============================================================================

SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 1000
FPS = 60

# 3D Camera settings
BASE_TILE_WIDTH = 90
BASE_TILE_HEIGHT = 45

# Office grid
GRID_WIDTH = 24
GRID_HEIGHT = 18

# Zoom limits
MIN_ZOOM = 0.4
MAX_ZOOM = 3.0
ZOOM_SPEED = 0.1

# Log panel
LOG_PANEL_WIDTH = 350
LOG_PANEL_HEIGHT = 300
LOG_MAX_ENTRIES = 50

# Colors
COLORS = {
    "background": (10, 15, 25),
    "floor": (55, 60, 70),
    "tile_light": (75, 80, 90),
    "tile_dark": (45, 50, 60),
    "text": (255, 255, 255),
    "text_shadow": (0, 0, 0),
    "agent": (220, 180, 140),
    "agent_outline": (100, 60, 30),
    # Departments
    "coding": (40, 80, 150),
    "testing": (40, 140, 80),
    "meeting": (150, 80, 40),
    "kitchen": (160, 140, 60),
    "lobby": (100, 100, 120),
    "design": (140, 60, 120),
    "sales": (60, 140, 140),
    "hr": (120, 60, 100),
    # Furniture
    "desk_top": (120, 80, 35),
    "desk_side": (85, 55, 25),
    "chair": (70, 50, 35),
    "computer": (25, 25, 30),
    "plant": (50, 100, 50),
    "sofa": (85, 50, 50),
    "counter": (180, 160, 140),
    # UI
    "log_bg": (20, 25, 35, 220),
    "log_text": (180, 200, 220),
    "progress_bg": (40, 40, 50),
    "progress_fill": (80, 200, 100),
    "bubble_bg": (255, 255, 200),
    "bubble_text": (20, 20, 20),
}

# ============================================================================
# 3D CAMERA WITH FULL ROTATION
# ============================================================================

class Camera3D:
    """Full 3D camera with yaw/pitch rotation, pan and zoom."""
    
    def __init__(self):
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.yaw = 0.0      # Horizontal rotation (degrees)
        self.pitch = -25.0  # Vertical tilt (degrees, negative = looking down)
        
        self.rotating = False
        self.tilting = False
        self.panning = False
        self.last_mouse_pos = None
    
    @property
    def tile_width(self):
        return BASE_TILE_WIDTH * self.zoom
    
    @property
    def tile_height(self):
        return BASE_TILE_HEIGHT * self.zoom
    
    def world_to_screen(self, world_x: float, world_y: float, world_z: float = 0) -> tuple:
        """Convert 3D world coordinates to 2D screen with full rotation."""
        center_x = GRID_WIDTH / 2
        center_y = GRID_HEIGHT / 2
        
        # Translate to center
        dx = world_x - center_x
        dy = world_y - center_y
        
        # Apply yaw rotation (around Y axis)
        yaw_rad = math.radians(self.yaw)
        rot_x = dx * math.cos(yaw_rad) - dy * math.sin(yaw_rad)
        rot_y = dx * math.sin(yaw_rad) + dy * math.cos(yaw_rad)
        
        # Apply pitch rotation (tilting view)
        pitch_rad = math.radians(self.pitch)
        # Pitch affects how "tall" the Y axis appears
        tilted_y = rot_y * math.cos(pitch_rad) - world_z * math.sin(pitch_rad)
        tilted_z = rot_y * math.sin(pitch_rad) + world_z * math.cos(pitch_rad)
        
        # Isometric-like projection with perspective
        screen_x = (rot_x - tilted_y) * (self.tile_width / 2) + SCREEN_WIDTH // 2 + self.pan_x - LOG_PANEL_WIDTH // 2
        screen_y = (rot_x + tilted_y) * (self.tile_height / 2) + 200 + self.pan_y - tilted_z * self.zoom
        
        return (screen_x, screen_y)
    
    def handle_event(self, event):
        """Handle mouse events for 3D rotation, pan and zoom."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click - rotate yaw
                self.rotating = True
                self.last_mouse_pos = event.pos
            elif event.button == 3:  # Right click - tilt pitch
                self.tilting = True
                self.last_mouse_pos = event.pos
            elif event.button == 2:  # Middle click - pan
                self.panning = True
                self.last_mouse_pos = event.pos
            elif event.button == 4:  # Scroll up - zoom in
                self.zoom = min(MAX_ZOOM, self.zoom + ZOOM_SPEED)
            elif event.button == 5:  # Scroll down - zoom out
                self.zoom = max(MIN_ZOOM, self.zoom - ZOOM_SPEED)
        
        elif event.type == pygame.MOUSEBUTTONUP:
            self.rotating = False
            self.tilting = False
            self.panning = False
            self.last_mouse_pos = None
        
        elif event.type == pygame.MOUSEMOTION:
            if self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                
                if self.rotating:
                    self.yaw += dx * 0.5
                if self.tilting:
                    self.pitch = max(-60, min(20, self.pitch + dy * 0.3))
                if self.panning:
                    self.pan_x += dx
                    self.pan_y += dy
                
                self.last_mouse_pos = event.pos
    
    def reset(self):
        """Reset camera to default position."""
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.yaw = 0.0
        self.pitch = -25.0

# ============================================================================
# VISUAL POST BUBBLE
# ============================================================================

class PostBubble:
    """A floating bubble showing a post was created."""
    
    def __init__(self, agent_x: float, agent_y: float, text: str, duration: int = 120):
        self.x = agent_x
        self.y = agent_y
        self.text = text[:40] + "..." if len(text) > 40 else text
        self.duration = duration
        self.age = 0
        self.offset_y = 0
    
    def update(self):
        """Update bubble animation."""
        self.age += 1
        self.offset_y -= 0.3  # Float upward
        return self.age < self.duration
    
    def draw(self, surface, camera: Camera3D):
        """Draw the bubble."""
        screen_pos = camera.world_to_screen(self.x, self.y, 20)
        screen_y = screen_pos[1] + self.offset_y
        
        # Fade out
        alpha = max(0, 255 - int(255 * self.age / self.duration))
        
        # Bubble background
        font = pygame.font.SysFont("Arial", 11)
        text_surf = font.render(self.text, True, COLORS["bubble_text"])
        
        padding = 8
        bubble_w = text_surf.get_width() + padding * 2
        bubble_h = text_surf.get_height() + padding * 2
        
        bubble_x = screen_pos[0] - bubble_w // 2
        bubble_y = screen_y - bubble_h
        
        # Draw bubble
        pygame.draw.ellipse(surface, COLORS["bubble_bg"],
                           (bubble_x, bubble_y, bubble_w, bubble_h))
        pygame.draw.ellipse(surface, (180, 180, 140),
                           (bubble_x, bubble_y, bubble_w, bubble_h), 1)
        
        # Draw pointer to agent
        pygame.draw.polygon(surface, COLORS["bubble_bg"], [
            (screen_pos[0] - 5, bubble_y + bubble_h),
            (screen_pos[0] + 5, bubble_y + bubble_h),
            (screen_pos[0], screen_y - 5),
        ])
        
        surface.blit(text_surf, (bubble_x + padding, bubble_y + padding))

# ============================================================================
# 3D WALLS AND FLOOR
# ============================================================================

# Expanded office floor plan (24x18)
OFFICE_FLOOR = [
    [None]*6 + [("lobby", False)]*8 + [None]*10,
    [None]*5 + [("kitchen", True)]*5 + [("lobby", False)]*6 + [None]*8,
    [None]*4 + [("kitchen", True)]*6 + [("lobby", False)]*4 + [("meeting", True)]*4 + [None]*6,
    [None]*4 + [("kitchen", True)]*6 + [("lobby", False)]*4 + [("meeting", True)]*4 + [None]*6,
    [None]*3 + [("coding", True)]*7 + [("lobby", False)]*4 + [("meeting", True)]*4 + [None]*6,
    [None]*2 + [("coding", True)]*8 + [("lobby", False)]*4 + [("hr", True)]*4 + [None]*6,
    [None]*2 + [("coding", True)]*8 + [("lobby", False)]*4 + [("hr", True)]*4 + [None]*6,
    [None]*2 + [("coding", True)]*8 + [("lobby", False)]*4 + [("sales", True)]*5 + [None]*5,
    [None]*3 + [("design", True)]*6 + [("lobby", False)]*4 + [("sales", True)]*5 + [None]*5,
    [None]*3 + [("design", True)]*6 + [("lobby", False)]*4 + [("sales", True)]*5 + [None]*5,
    [None]*3 + [("design", True)]*6 + [("lobby", False)]*4 + [("testing", True)]*6 + [None]*4,
    [None]*6 + [("lobby", False)]*5 + [("testing", True)]*6 + [None]*4,
    [None]*6 + [("lobby", False)]*5 + [("testing", True)]*6 + [None]*4,
    [None]*24, [None]*24, [None]*24, [None]*24, [None]*24,
]

DEPARTMENT_LABELS = [
    (4, 4, "CODING", "coding"),
    (11, 3, "MEETING", "meeting"),
    (11, 6, "HR", "hr"),
    (11, 8, "SALES", "sales"),
    (5, 9, "DESIGN", "design"),
    (12, 11, "TESTING", "testing"),
    (5, 2, "KITCHEN", "kitchen"),
    (8, 0, "LOBBY", "lobby"),
]

# Wall collision map
WALL_COLLISION_MAP = [
    [True]*6 + [False]*8 + [True]*10,
    [True]*5 + [False]*11 + [True]*8,
    [True]*4 + [False]*14 + [True]*6,
    [True]*4 + [False]*14 + [True]*6,
    [True]*3 + [False]*15 + [True]*6,
    [True]*2 + [False]*16 + [True]*6,
    [True]*2 + [False]*16 + [True]*6,
    [True]*2 + [False]*17 + [True]*5,
    [True]*3 + [False]*15 + [True]*6,
    [True]*3 + [False]*15 + [True]*6,
    [True]*3 + [False]*17 + [True]*4,
    [True]*6 + [False]*14 + [True]*4,
    [True]*6 + [False]*14 + [True]*4,
    [True]*24, [True]*24, [True]*24, [True]*24, [True]*24,
]

# Walls for rendering (x1,y1,x2,y2,height,color)
DEPARTMENT_WALLS = [
    # Kitchen
    (4, 1, 9, 1, 22, "counter"),
    (4, 1, 4, 4, 22, "counter"),
    (9, 1, 9, 4, 22, "counter"),
    (4, 4, 7, 4, 22, "counter"),
    (8, 4, 9, 4, 22, "counter"),
    # Coding
    (2, 4, 10, 4, 20, "coding"),
    (2, 4, 2, 8, 20, "coding"),
    (10, 4, 10, 5, 20, "coding"),
    (10, 7, 10, 8, 20, "coding"),
    (2, 8, 4, 8, 20, "coding"),
    (5, 8, 10, 8, 20, "coding"),
    # Coding cubicles
    (4, 4, 4, 8, 14, "coding"),
    (7, 4, 7, 8, 14, "coding"),
    (2, 6, 10, 6, 14, "coding"),
    # Meeting
    (9, 2, 15, 2, 24, "meeting"),
    (9, 2, 9, 3, 24, "meeting"),
    (9, 4, 9, 6, 24, "meeting"),
    (15, 2, 15, 6, 24, "meeting"),
    (9, 6, 12, 6, 24, "meeting"),
    (13, 6, 15, 6, 24, "meeting"),
    # HR
    (9, 6, 15, 6, 22, "hr"),
    (9, 6, 9, 8, 22, "hr"),
    (15, 6, 15, 8, 22, "hr"),
    (9, 8, 11, 8, 22, "hr"),
    (12, 8, 15, 8, 22, "hr"),
    # Sales
    (9, 8, 15, 8, 20, "sales"),
    (9, 8, 9, 10, 20, "sales"),
    (9, 11, 9, 12, 20, "sales"),
    (15, 8, 15, 10, 20, "sales"),
    (15, 11, 15, 12, 20, "sales"),
    (9, 12, 11, 12, 20, "sales"),
    (13, 12, 15, 12, 20, "sales"),
    # Design
    (3, 8, 8, 8, 20, "design"),
    (3, 8, 3, 12, 20, "design"),
    (8, 8, 8, 10, 20, "design"),
    (8, 11, 8, 12, 20, "design"),
    (3, 12, 5, 12, 20, "design"),
    (6, 12, 8, 12, 20, "design"),
    # Testing
    (9, 11, 16, 11, 20, "testing"),
    (9, 11, 9, 13, 20, "testing"),
    (16, 11, 16, 13, 20, "testing"),
    (9, 13, 16, 13, 20, "testing"),
]

# Furniture
FURNITURE = [
    (3, 5, "desk"), (4, 5, "desk"), (5, 5, "desk"),
    (3, 6, "desk"), (4, 6, "desk"), (6, 6, "desk"),
    (3, 7, "desk"), (5, 7, "desk"),
    (10, 3, "sofa"), (11, 3, "sofa"), (12, 4, "desk"),
    (10, 6, "desk"), (12, 6, "desk"),
    (10, 8, "desk"), (11, 8, "desk"), (12, 8, "desk"),
    (10, 9, "desk"), (11, 9, "desk"),
    (4, 9, "desk"), (5, 9, "desk"), (4, 10, "desk"), (5, 10, "desk"),
    (11, 11, "desk"), (12, 11, "desk"), (13, 11, "desk"),
    (11, 12, "desk"), (12, 12, "desk"),
    (5, 2, "counter"), (6, 2, "counter"),
    (7, 1, "plant"), (9, 1, "plant"), (8, 4, "plant"),
    (8, 7, "plant"), (8, 10, "plant"),
]

# ============================================================================
# DRAWING FUNCTIONS
# ============================================================================

def draw_iso_tile(surface, x, y, color, camera: Camera3D, height: int = 0):
    """Draw isometric tile with optional height."""
    corners = [
        camera.world_to_screen(x, y, height),
        camera.world_to_screen(x + 1, y, height),
        camera.world_to_screen(x + 1, y + 1, height),
        camera.world_to_screen(x, y + 1, height),
    ]
    
    pygame.draw.polygon(surface, color, corners)
    outline = tuple(max(0, c - 30) for c in color)
    pygame.draw.polygon(surface, outline, corners, width=1)


def draw_wall(surface, x1, y1, x2, y2, height, color, camera: Camera3D):
    """Draw 3D wall."""
    p1 = camera.world_to_screen(x1, y1)
    p2 = camera.world_to_screen(x2, y2)
    p1_top = camera.world_to_screen(x1, y1, height)
    p2_top = camera.world_to_screen(x2, y2, height)
    
    wall_color = tuple(max(0, c - 15) for c in color)
    pygame.draw.polygon(surface, wall_color, [p1, p2, p2_top, p1_top])
    pygame.draw.line(surface, tuple(max(0, c - 35) for c in color), p1_top, p2_top, 2)


def draw_desk(surface, sx, sy, camera: Camera3D):
    """Draw 3D desk."""
    tw, th = camera.tile_width, camera.tile_height
    scale = camera.zoom
    
    # Desk top
    desk_w, desk_d, desk_h = tw * 0.75, th * 0.55, 14 * scale
    
    base = [(sx - desk_w/2, sy + desk_d/2), (sx + desk_w/2, sy + desk_d/2),
            (sx + desk_w/2, sy - desk_d/2), (sx - desk_w/2, sy - desk_d/2)]
    top = [(x, y - desk_h) for x, y in base]
    
    # Sides
    pygame.draw.polygon(surface, COLORS["desk_side"], [base[3], base[0], top[0], top[3]])
    pygame.draw.polygon(surface, tuple(c-20 for c in COLORS["desk_side"]), [base[0], base[1], top[1], top[0]])
    pygame.draw.polygon(surface, COLORS["desk_side"], [base[1], base[2], top[2], top[1]])
    
    # Top
    pygame.draw.polygon(surface, COLORS["desk_top"], top)
    
    # Chair
    chair_y = sy + th * 0.35
    pygame.draw.ellipse(surface, COLORS["chair"], (sx - tw*0.15, chair_y - th*0.08, tw*0.3, th*0.18))
    
    # Computer
    mon_w, mon_h = tw * 0.28, th * 0.35
    pygame.draw.rect(surface, COLORS["computer"], (sx - mon_w/2, top[0][1] - mon_h + 2, mon_w, mon_h))
    pygame.draw.rect(surface, (70, 90, 110), (sx - mon_w/2 + 2, top[0][1] - mon_h + 4, mon_w - 4, mon_h - 6))


def draw_plant(surface, sx, sy, camera: Camera3D):
    """Draw plant."""
    scale = camera.zoom
    pot_y = sy + camera.tile_height * 0.1
    
    pygame.draw.ellipse(surface, (110, 75, 55), (sx - 10*scale, pot_y - 6*scale, 20*scale, 12*scale))
    pygame.draw.ellipse(surface, (130, 85, 65), (sx - 12*scale, pot_y - 12*scale, 24*scale, 14*scale))
    
    for i in range(5):
        angle = -90 + i * 45
        rad = math.radians(angle)
        lx = sx + math.cos(rad) * 8 * scale
        ly = pot_y - 10*scale + math.sin(rad) * 4 * scale
        pygame.draw.ellipse(surface, COLORS["plant"], (lx - 4*scale, ly - 8*scale, 8*scale, 10*scale))


def draw_sofa(surface, sx, sy, camera: Camera3D):
    """Draw sofa."""
    tw, th = camera.tile_width, camera.tile_height
    
    # Back
    pygame.draw.rect(surface, COLORS["sofa"], (sx - tw*0.35, sy - th*0.45, tw*0.7, th*0.3))
    # Seat
    pygame.draw.rect(surface, (130, 75, 75), (sx - tw*0.4, sy - th*0.12, tw*0.8, th*0.25))


def draw_counter(surface, sx, sy, camera: Camera3D):
    """Draw counter."""
    tw, th = camera.tile_width, camera.tile_height
    scale = camera.zoom
    
    counter_w, counter_d, counter_h = tw * 0.85, th * 0.55, 20 * scale
    
    base = [(sx - counter_w/2, sy + counter_d/2), (sx + counter_w/2, sy + counter_d/2),
            (sx + counter_w/2, sy - counter_d/2), (sx - counter_w/2, sy - counter_d/2)]
    top = [(x, y - counter_h) for x, y in base]
    
    pygame.draw.polygon(surface, (160, 140, 120), [base[3], base[0], top[0], top[3]])
    pygame.draw.polygon(surface, (140, 120, 100), [base[0], base[1], top[1], top[0]])
    pygame.draw.polygon(surface, COLORS["counter"], top)
    
    # Coffee maker
    pygame.draw.rect(surface, (40, 40, 40), (sx - 8*scale, top[0][1] - 10*scale, 10*scale, 10*scale))
    pygame.draw.ellipse(surface, (80, 60, 40), (sx + 4*scale, top[0][1] - 8*scale, 8*scale, 8*scale))


# ============================================================================
# 3D VISUALIZATION AGENT
# ============================================================================

class VizAgent:
    """Visual agent with simulation integration."""
    
    def __init__(self, agent: Agent, grid_x: int, grid_y: int):
        self.agent = agent  # The actual simulation agent
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.target_x = grid_x
        self.target_y = grid_y
        
        # Animation
        self.walk_progress = 0.0
        self.walk_speed = 0.03
        self.walking = False
        self.bob_phase = 0.0
        
        # Visual
        self.role_colors = {
            JobRole.DEVELOPER: (60, 120, 200),
            JobRole.TESTER: (60, 200, 100),
            JobRole.PROJECT_MANAGER: (200, 100, 60),
            JobRole.JANITOR: (180, 160, 80),
            JobRole.DESIGNER: (200, 80, 160),
            JobRole.SALES_REP: (80, 180, 180),
            JobRole.HR_MANAGER: (160, 80, 140),
            JobRole.INTERN: (150, 150, 150),
        }
        self.color = self.role_colors.get(agent.job_role, (150, 150, 150))
        
        # Pathfinding
        self.path = []
        self.path_index = 0
        
        # UI elements
        self.post_bubbles = []
        self.task_progress = 0.0
    
    def set_target_with_path(self, target_x: int, target_y: int):
        """Set target using A* pathfinding."""
        start = (self.grid_x, self.grid_y)
        goal = (target_x, target_y)
        
        self.path = self._find_path(start, goal)
        self.path_index = 0
        
        if self.path:
            self._advance_path()
    
    def _find_path(self, start, goal):
        """Simple A* pathfinding."""
        if WALL_COLLISION_MAP[goal[1]][goal[0]]:
            return []
        
        import heapq
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        def neighbors(x, y):
            result = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    if not WALL_COLLISION_MAP[ny][nx]:
                        result.append((nx, ny))
            return result
        
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}
        
        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break
            for next_pos in neighbors(*current):
                new_cost = cost_so_far[current] + 1
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + heuristic(goal, next_pos)
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current
        
        if goal not in came_from:
            return []
        
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path
    
    def _advance_path(self):
        if self.path_index < len(self.path):
            self.target_x, self.target_y = self.path[self.path_index]
            self.walking = True
            self.walk_progress = 0.0
            self.path_index += 1
        else:
            self.path = []
            self.path_index = 0
    
    def update(self):
        """Update agent state."""
        if self.walking:
            self.walk_progress += self.walk_speed
            self.bob_phase += 0.25
            
            if self.walk_progress >= 1.0:
                self.walk_progress = 1.0
                self.walking = False
                self.grid_x = self.target_x
                self.grid_y = self.target_y
                self.bob_phase = 0.0
                
                if self.path:
                    self._advance_path()
        
        if not self.walking:
            self.bob_phase += 0.02
        
        # Update bubbles
        self.post_bubbles = [b for b in self.post_bubbles if b.update()]
    
    def add_post_bubble(self, text: str):
        """Add a post bubble above this agent."""
        self.post_bubbles.append(PostBubble(self.grid_x + 0.5, self.grid_y + 0.5, text))
    
    def get_screen_pos(self, camera: Camera3D):
        if self.walking:
            x = self.grid_x + (self.target_x - self.grid_x) * self.walk_progress
            y = self.grid_y + (self.target_y - self.grid_y) * self.walk_progress
        else:
            x, y = self.grid_x, self.grid_y
        return camera.world_to_screen(x, y)
    
    def draw(self, surface, camera: Camera3D):
        """Draw agent with task progress bar."""
        screen_x, screen_y = self.get_screen_pos(camera)
        
        bob = math.sin(self.bob_phase) * 2 * camera.zoom if (self.walking or self.bob_phase > 0) else 0
        scale = camera.zoom * 0.55
        
        # Body
        body_w, body_h = 11 * scale, 15 * scale
        body_y = screen_y - body_h - 5 * scale + bob
        
        pygame.draw.ellipse(surface, self.color, (screen_x - body_w/2, body_y, body_w, body_h))
        
        # Head
        head_r = 4.5 * scale
        head_y = body_y - head_r - 2 * scale
        pygame.draw.circle(surface, COLORS["agent"], (int(screen_x), int(head_y)), int(head_r))
        pygame.draw.arc(surface, (40, 30, 20),
                       (screen_x - head_r, head_y - head_r, head_r*2, head_r*2),
                       3.14, 0, 2)
        
        # Legs
        leg_y = body_y + body_h
        walk_offset = math.sin(self.bob_phase * 1.5) * 2 * scale if self.walking else 0
        pygame.draw.line(surface, (60, 60, 80),
                        (screen_x - 2*scale, leg_y),
                        (screen_x - 2*scale + walk_offset, leg_y + 7*scale), 2)
        pygame.draw.line(surface, (60, 60, 80),
                        (screen_x + 2*scale, leg_y),
                        (screen_x + 2*scale - walk_offset, leg_y + 7*scale), 2)
        
        # Task progress bar above head
        if self.task_progress > 0:
            bar_w, bar_h = 30 * scale, 5 * scale
            bar_x = screen_x - bar_w/2
            bar_y = head_y - head_r - 15 * scale
            
            # Background
            pygame.draw.rect(surface, COLORS["progress_bg"], (bar_x, bar_y, bar_w, bar_h))
            # Fill
            fill_w = bar_w * self.task_progress
            fill_color = COLORS["progress_fill"] if self.task_progress < 1.0 else (100, 255, 150)
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, fill_w, bar_h))
            # Border
            pygame.draw.rect(surface, (150, 150, 150), (bar_x, bar_y, bar_w, bar_h), 1)
        
        # Post bubbles
        for bubble in self.post_bubbles:
            bubble.draw(surface, camera)
        
        # Name label
        font = pygame.font.SysFont("Arial", int(9 * scale))
        label = font.render(self.agent.name, True, COLORS["text"])
        shadow = font.render(self.agent.name, True, COLORS["text_shadow"])
        surface.blit(shadow, (screen_x - label.get_width()//2 + 1, body_y - 14*scale + 1))
        surface.blit(label, (screen_x - label.get_width()//2, body_y - 14*scale))


# ============================================================================
# MAIN 3D VISUALIZATION
# ============================================================================

class Office3DVisualization:
    """Full 3D office simulation visualization."""
    
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Agent Office 3D Simulation")
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 13)
        self.font_title = pygame.font.SysFont("Arial", 15, bold=True)
        self.font_log = pygame.font.SysFont("Arial", 11)
        
        # Camera
        self.camera = Camera3D()
        
        # Simulation
        self.network = SocialNetwork()
        self.office = Office("TechCorp HQ")
        
        # Create office team agents and add to network
        team = [
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
        
        for agent in team:
            self.network.add_agent(agent)
            self.office.add_agent(agent)
        
        self.simulation = Simulation(
            self.network,
            tick_delay=0.0,  # No delay, we control timing
            office=self.office
        )
        
        # Create agents and place them
        self.viz_agents = []
        start_positions = [
            (4, 5), (5, 5), (6, 5), (4, 6),
            (10, 3), (11, 6), (10, 8), (11, 11),
            (4, 9), (5, 9)
        ]
        
        # Get agents from the simulation's network (agents are stored as dict)
        network_agents = list(self.simulation.network.agents.values())
        
        for i, (x, y) in enumerate(start_positions):
            if i < len(network_agents):
                viz_agent = VizAgent(network_agents[i], x, y)
                self.viz_agents.append(viz_agent)
        
        # Log entries
        self.log_entries = deque(maxlen=LOG_MAX_ENTRIES)
        
        # Setup simulation callbacks
        self._setup_callbacks()
        
        # State
        self.paused = False
        self.tick_counter = 0
        self.running = True
        
        # Initial log
        self._add_log("Simulation initialized")
        self._add_log(f"Agents: {len(self.viz_agents)}")
        self._add_log(f"Office: {self.office.name}")
    
    def _setup_callbacks(self):
        """Setup simulation event callbacks."""
        def on_simulation_event(event: SimulationEvent):
            self._add_log(f"[{event.agent_name}] {event.event_type}: {event.post_subject[:30]}")
        
        def on_office_event(event_type: str, agent, task):
            if event_type == "task_started":
                self._add_log(f"[{agent.name}] Started: {task.title[:25]}")
            elif event_type == "task_completed":
                self._add_log(f"[{agent.name}] Completed: {task.title[:25]}")
        
        self.simulation.on_event = on_simulation_event
        self.simulation.on_office_event = on_office_event
        
        # Post creation callback
        def on_post_created(post: Post, author, product_advanced=None):
            # Find the viz agent for this author
            for viz_agent in self.viz_agents:
                if viz_agent.agent.id == author.id:
                    viz_agent.add_post_bubble(post.subject)
                    break
            self._add_log(f"📢 [{author.name}] POST: {post.subject[:30]}")
        
        self.office.on_post_create = on_post_created
    
    def _add_log(self, text: str):
        """Add entry to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_entries.append(f"[{timestamp}] {text}")
    
    def handle_events(self):
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.camera.reset()
                elif event.key == pygame.K_p:
                    self.paused = not self.paused
                    self._add_log("PAUSED" if self.paused else "RESUMED")
            
            self.camera.handle_event(event)
    
    def update(self):
        """Update simulation and agents."""
        if self.paused:
            return
        
        # Run simulation tick
        try:
            events = self.simulation.tick()
        except Exception as e:
            self._add_log(f"Error: {str(e)[:40]}")
        
        # Update agents
        for viz_agent in self.viz_agents:
            viz_agent.update()
            
            # Update task progress
            if viz_agent.agent.current_task:
                # Find the task
                for task in self.office.tasks:
                    if task.title == viz_agent.agent.current_task:
                        viz_agent.task_progress = task.progress
                        break
            else:
                viz_agent.task_progress = 0.0
            
            # Random walking
            if not viz_agent.walking and random.random() < 0.01:
                # Pick random walkable target
                for _ in range(10):
                    tx = random.randint(1, GRID_WIDTH - 2)
                    ty = random.randint(1, GRID_HEIGHT - 2)
                    if not WALL_COLLISION_MAP[ty][tx]:
                        viz_agent.set_target_with_path(tx, ty)
                        break
        
        self.tick_counter += 1
    
    def draw_floor(self):
        """Draw office floor."""
        tiles = []
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cell = OFFICE_FLOOR[y][x] if y < len(OFFICE_FLOOR) and x < len(OFFICE_FLOOR[y]) else None
                if cell:
                    tiles.append((x, y, cell[0], cell[1]))
        
        tiles.sort(key=lambda t: t[0] + t[1])
        
        for x, y, dept, has_height in tiles:
            color = COLORS.get(dept, COLORS["floor"])
            if has_height:
                draw_iso_tile(self.screen, x, y, color, self.camera, height=8)
            else:
                draw_iso_tile(self.screen, x, y, color, self.camera)
    
    def draw_walls(self):
        """Draw walls."""
        for x1, y1, x2, y2, height, color_key in DEPARTMENT_WALLS:
            color = COLORS.get(color_key, COLORS["floor"])
            draw_wall(self.screen, x1, y1, x2, y2, height, color, self.camera)
    
    def draw_furniture(self):
        """Draw furniture."""
        for x, y, ftype in FURNITURE:
            pos = self.camera.world_to_screen(x + 0.5, y + 0.5)
            
            if ftype == "desk":
                draw_desk(self.screen, pos[0], pos[1], self.camera)
            elif ftype == "plant":
                draw_plant(self.screen, pos[0], pos[1], self.camera)
            elif ftype == "sofa":
                draw_sofa(self.screen, pos[0], pos[1], self.camera)
            elif ftype == "counter":
                draw_counter(self.screen, pos[0], pos[1], self.camera)
    
    def draw_labels(self):
        """Draw department labels."""
        for x, y, name, key in DEPARTMENT_LABELS:
            pos = self.camera.world_to_screen(x, y)
            font = pygame.font.SysFont("Arial", int(14 * self.camera.zoom), bold=True)
            text = font.render(name, True, COLORS["text"])
            shadow = font.render(name, True, COLORS["text_shadow"])
            self.screen.blit(shadow, (pos[0] - text.get_width()//2 + 1, pos[1] - 25 * self.camera.zoom + 1))
            self.screen.blit(text, (pos[0] - text.get_width()//2, pos[1] - 25 * self.camera.zoom))
    
    def draw_agents(self):
        """Draw all agents."""
        for viz_agent in self.viz_agents:
            viz_agent.draw(self.screen, self.camera)
    
    def draw_log_panel(self):
        """Draw terminal-style log panel."""
        panel_x = SCREEN_WIDTH - LOG_PANEL_WIDTH - 10
        panel_y = SCREEN_HEIGHT - LOG_PANEL_HEIGHT - 10
        
        # Background
        panel_rect = pygame.Rect(panel_x, panel_y, LOG_PANEL_WIDTH, LOG_PANEL_HEIGHT)
        s = pygame.Surface((LOG_PANEL_WIDTH, LOG_PANEL_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(s, COLORS["log_bg"], (0, 0, LOG_PANEL_WIDTH, LOG_PANEL_HEIGHT))
        self.screen.blit(s, (panel_x, panel_y))
        
        # Border
        pygame.draw.rect(self.screen, (80, 100, 120), panel_rect, 2)
        
        # Title
        title = self.font_title.render("📋 Simulation Log", True, COLORS["text"])
        self.screen.blit(title, (panel_x + 10, panel_y + 8))
        
        # Log entries (bottom-up)
        y = panel_y + LOG_PANEL_HEIGHT - 25
        for entry in reversed(list(self.log_entries)):
            if y < panel_y + 35:
                break
            text = self.font_log.render(entry[:45], True, COLORS["log_text"])
            self.screen.blit(text, (panel_x + 10, y))
            y -= 18
        
        # Stats
        stats = self.simulation.stats
        stats_text = self.font.render(
            f"Ticks: {stats.total_ticks} | Posts: {stats.total_posts} | Shares: {stats.total_shares}",
            True, (150, 180, 200)
        )
        self.screen.blit(stats_text, (panel_x + 10, panel_y + LOG_PANEL_HEIGHT - 22))
    
    def draw_ui(self):
        """Draw UI elements."""
        # Title
        title = self.font_title.render("🏢 TechCorp HQ — 3D Simulation", True, COLORS["text"])
        self.screen.blit(title, (20, 15))
        
        # Controls
        controls = self.font.render(
            "L-Drag: Rotate | R-Drag: Tilt | Scroll: Zoom | P: Pause | R: Reset | Q: Quit",
            True, COLORS["text"]
        )
        self.screen.blit(controls, (20, SCREEN_HEIGHT - 25))
        
        # Status
        status = "⏸ PAUSED" if self.paused else "▶ RUNNING"
        status_text = self.font.render(
            f"{status} | Tick: {self.tick_counter} | Agents: {len(self.viz_agents)}",
            True, COLORS["text"]
        )
        self.screen.blit(status_text, (20, 40))
        
        # Zoom
        zoom_text = self.font.render(f"Zoom: {self.camera.zoom:.1f}x | Yaw: {self.camera.yaw:.0f}°", True, COLORS["text"])
        self.screen.blit(zoom_text, (20, 60))
        
        # Legend
        legend_x = 20
        legend_y = 80
        legend = self.font_title.render("Departments:", True, COLORS["text"])
        self.screen.blit(legend, (legend_x, legend_y))
        
        depts = [("CODING", "coding"), ("TESTING", "testing"), ("MEETING", "meeting"),
                 ("KITCHEN", "kitchen"), ("DESIGN", "design"), ("SALES", "sales"),
                 ("HR", "hr"), ("LOBBY", "lobby")]
        
        for i, (name, key) in enumerate(depts):
            y = legend_y + 22 + i * 18
            pygame.draw.rect(self.screen, COLORS[key], (legend_x, y, 14, 14))
            text = self.font.render(name, True, COLORS["text"])
            self.screen.blit(text, (legend_x + 18, y + 1))
    
    def draw(self):
        """Main draw."""
        self.screen.fill(COLORS["background"])
        
        # Draw in depth order
        self.draw_floor()
        self.draw_walls()
        self.draw_furniture()
        self.draw_labels()
        self.draw_agents()
        
        # UI on top
        self.draw_ui()
        self.draw_log_panel()
        
        pygame.display.flip()
    
    def run(self):
        """Main loop."""
        print("🏢 Starting Agent Office 3D Simulation...")
        print("   Controls:")
        print("   - Left-click + drag: Rotate view (yaw)")
        print("   - Right-click + drag: Tilt view (pitch)")
        print("   - Scroll wheel: Zoom")
        print("   - P: Pause/Resume")
        print("   - R: Reset camera")
        print("   - Q: Quit")
        
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        print("👋 Visualization closed.")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    viz = Office3DVisualization()
    viz.run()


if __name__ == "__main__":
    main()
