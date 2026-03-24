#!/usr/bin/env python3
"""
Agent Office 3D Visualization — Isometric Office Floor Plan with Wall Collision

A Pygame-based isometric view of the office with:
- Wall collision detection (agents cannot walk through walls)
- A* pathfinding (agents find paths through doorways)
- Enhanced 3D furniture
- Expanded office space (20x16 grid)
- Multiple agents walking between rooms

Controls:
  - Left-click + drag: Pan view
  - Scroll wheel: Zoom in/out
  - R: Reset camera
  - Q or ESC: Quit
"""

import pygame
import math
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 60

# Isometric tile dimensions (base, will be scaled by zoom) - larger for more space
BASE_TILE_WIDTH = 80
BASE_TILE_HEIGHT = 40

# Office grid size (in tiles) - expanded for bigger departments
GRID_WIDTH = 20
GRID_HEIGHT = 16

# Zoom limits
MIN_ZOOM = 0.5
MAX_ZOOM = 2.5
ZOOM_SPEED = 0.1

# Colors
COLORS = {
    "background": (15, 15, 25),
    "floor": (70, 70, 80),
    "tile_light": (90, 90, 100),
    "tile_dark": (60, 60, 70),
    "text": (255, 255, 255),
    "text_shadow": (0, 0, 0),
    "agent": (220, 180, 140),      # Skin tone
    "agent_outline": (100, 60, 30),
    # Department colors
    "coding": (50, 90, 160),       # Blue
    "testing": (50, 160, 90),      # Green
    "meeting": (160, 90, 50),      # Orange
    "kitchen": (180, 160, 70),     # Yellow
    "lobby": (120, 120, 140),      # Gray
    "design": (160, 70, 140),      # Pink/Magenta
    "sales": (80, 160, 160),       # Cyan
    "hr": (140, 70, 120),          # Purple
    # Furniture colors
    "desk_top": (139, 90, 43),
    "desk_side": (100, 65, 30),
    "chair": (80, 60, 40),
    "computer": (30, 30, 35),
    "plant": (60, 120, 60),
    "sofa": (100, 60, 60),
    "counter": (200, 180, 160),
}

# ============================================================================
# ISOMETRIC UTILITIES (with zoom support)
# ============================================================================

class IsometricCamera:
    """Isometric camera with pan and zoom (no rotation)."""
    
    def __init__(self):
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        self.dragging = False
        self.last_mouse_pos = None
    
    @property
    def tile_width(self):
        return BASE_TILE_WIDTH * self.zoom
    
    @property
    def tile_height(self):
        return BASE_TILE_HEIGHT * self.zoom
    
    def iso_to_screen(self, iso_x: float, iso_y: float, iso_z: float = 0) -> tuple:
        """Convert isometric grid to screen coordinates."""
        screen_x = (iso_x - iso_y) * (self.tile_width / 2) + SCREEN_WIDTH // 2 + self.pan_x
        screen_y = (iso_x + iso_y) * (self.tile_height / 2) + 150 + self.pan_y - iso_z * self.zoom
        return (screen_x, screen_y)
    
    def screen_to_iso(self, screen_x: float, screen_y: float) -> tuple:
        """Convert screen to isometric grid coordinates."""
        rel_x = screen_x - SCREEN_WIDTH // 2 - self.pan_x
        rel_y = screen_y - 150 - self.pan_y
        
        iso_x = (rel_x / (self.tile_width / 2) + rel_y / (self.tile_height / 2)) / 2
        iso_y = (rel_y / (self.tile_height / 2) - rel_x / (self.tile_width / 2)) / 2
        return (iso_x, iso_y)
    
    def handle_event(self, event):
        """Handle mouse events for pan and zoom."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click - start drag (pan only)
                self.dragging = True
                self.last_mouse_pos = event.pos
            elif event.button == 4:  # Scroll up - zoom in
                self.zoom = min(MAX_ZOOM, self.zoom + ZOOM_SPEED)
            elif event.button == 5:  # Scroll down - zoom out
                self.zoom = max(MIN_ZOOM, self.zoom - ZOOM_SPEED)
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                self.last_mouse_pos = None
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging and self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                self.pan_x += dx
                self.pan_y += dy
                self.last_mouse_pos = event.pos
    
    def reset(self):
        """Reset camera to default position."""
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0


def draw_iso_tile(surface: pygame.Surface, iso_x: int, iso_y: int, 
                  color: tuple, camera: IsometricCamera):
    """Draw a single isometric tile."""
    corners = [
        camera.iso_to_screen(iso_x, iso_y),
        camera.iso_to_screen(iso_x + 1, iso_y),
        camera.iso_to_screen(iso_x + 1, iso_y + 1),
        camera.iso_to_screen(iso_x, iso_y + 1),
    ]
    
    pygame.draw.polygon(surface, color, corners)
    outline = tuple(max(0, c - 30) for c in color)
    pygame.draw.polygon(surface, outline, corners, width=1)


def draw_iso_tile_with_height(surface: pygame.Surface, iso_x: int, iso_y: int,
                              color: tuple, height: int, camera: IsometricCamera):
    """Draw an isometric tile with 3D block effect."""
    base_corners = [
        camera.iso_to_screen(iso_x, iso_y),
        camera.iso_to_screen(iso_x + 1, iso_y),
        camera.iso_to_screen(iso_x + 1, iso_y + 1),
        camera.iso_to_screen(iso_x, iso_y + 1),
    ]
    
    # Scale height by zoom
    scaled_height = height * camera.zoom
    top_corners = [(x, y - scaled_height) for x, y in base_corners]
    
    # Top face
    pygame.draw.polygon(surface, color, top_corners)
    
    # Left face (darker)
    left_color = tuple(max(0, c - 40) for c in color)
    pygame.draw.polygon(surface, left_color, 
                        [top_corners[3], top_corners[2], base_corners[2], base_corners[3]])
    
    # Right face (even darker)
    right_color = tuple(max(0, c - 60) for c in color)
    pygame.draw.polygon(surface, right_color,
                        [top_corners[1], top_corners[2], base_corners[2], base_corners[1]])
    
    # Outlines
    outline = tuple(max(0, c - 30) for c in color)
    pygame.draw.polygon(surface, outline, top_corners, width=1)


def draw_wall(surface: pygame.Surface, x1: float, y1: float, x2: float, y2: float,
              height: float, color: tuple, camera: IsometricCamera):
    """Draw a 3D wall between two points."""
    # Base corners
    p1 = camera.iso_to_screen(x1, y1)
    p2 = camera.iso_to_screen(x2, y2)
    
    # Top corners (with height)
    p1_top = camera.iso_to_screen(x1, y1, height)
    p2_top = camera.iso_to_screen(x2, y2, height)
    
    # Draw wall face
    wall_color = tuple(max(0, c - 20) for c in color)
    pygame.draw.polygon(surface, wall_color, [p1, p2, p2_top, p1_top])
    
    # Top edge
    pygame.draw.line(surface, tuple(max(0, c - 40) for c in color), p1_top, p2_top, 2)


def draw_cubicle_wall(surface: pygame.Surface, x: float, y: float, 
                      width: float, depth: float, height: float, color: tuple, camera: IsometricCamera):
    """Draw a cubicle partition wall."""
    # Back wall
    draw_wall(surface, x, y, x + width, y, height, color, camera)
    # Side wall
    draw_wall(surface, x, y, x, y + depth, height, color, camera)


# ============================================================================
# OFFICE FLOOR PLAN DEFINITION
# ============================================================================

# Define the office floor plan as a 2D grid
# Each cell: (department_key, has_height)
# None = empty/void (won't draw tile)

# Expanded 20x16 office floor plan with proper rooms and doorways
# Each cell: (department_key, has_height)
# None = empty/void (won't draw tile)

OFFICE_FLOOR = [
    # Row 0: Entrance/Lobby top
    [None, None, None, None, None, ("lobby", False), ("lobby", False), ("lobby", False), ("lobby", False), ("lobby", False), None, None, None, None, None, None, None, None, None, None],
    # Row 1: Lobby + Kitchen
    [None, None, None, None, ("kitchen", True), ("kitchen", True), ("kitchen", True), ("lobby", False), ("lobby", False), ("lobby", False), ("lobby", False), ("lobby", False), None, None, None, None, None, None, None, None],
    # Row 2: Kitchen + Lobby + Meeting
    [None, None, None, ("kitchen", True), ("kitchen", True), ("kitchen", True), ("kitchen", True), ("lobby", False), ("lobby", False), ("meeting", True), ("meeting", True), ("meeting", True), ("meeting", True), None, None, None, None, None, None, None],
    # Row 3: Kitchen + Lobby + Meeting
    [None, None, None, ("kitchen", True), ("kitchen", True), ("kitchen", True), ("kitchen", True), ("lobby", False), ("lobby", False), ("meeting", True), ("meeting", True), ("meeting", True), ("meeting", True), None, None, None, None, None, None, None],
    # Row 4: Coding + Lobby + Meeting
    [None, None, ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("lobby", False), ("lobby", False), ("meeting", True), ("meeting", True), ("meeting", True), ("meeting", True), None, None, None, None, None, None, None],
    # Row 5: Coding + Lobby + HR
    [None, ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("lobby", False), ("lobby", False), ("hr", True), ("hr", True), ("hr", True), ("hr", True), None, None, None, None, None, None, None],
    # Row 6: Coding + Lobby + HR
    [None, ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("lobby", False), ("lobby", False), ("hr", True), ("hr", True), ("hr", True), ("hr", True), None, None, None, None, None, None, None],
    # Row 7: Coding + Lobby + Sales
    [None, ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("coding", True), ("lobby", False), ("lobby", False), ("sales", True), ("sales", True), ("sales", True), ("sales", True), None, None, None, None, None, None, None],
    # Row 8: Design + Lobby + Sales
    [None, None, ("design", True), ("design", True), ("design", True), ("design", True), ("design", True), ("lobby", False), ("lobby", False), ("sales", True), ("sales", True), ("sales", True), ("sales", True), None, None, None, None, None, None, None],
    # Row 9: Design + Lobby + Sales
    [None, None, ("design", True), ("design", True), ("design", True), ("design", True), ("design", True), ("lobby", False), ("lobby", False), ("sales", True), ("sales", True), ("sales", True), ("sales", True), None, None, None, None, None, None, None],
    # Row 10: Design + Lobby + Testing
    [None, None, ("design", True), ("design", True), ("design", True), ("design", True), ("design", True), ("lobby", False), ("lobby", False), ("testing", True), ("testing", True), ("testing", True), ("testing", True), None, None, None, None, None, None, None],
    # Row 11: Lobby + Testing
    [None, None, None, None, None, None, ("lobby", False), ("lobby", False), ("lobby", False), ("testing", True), ("testing", True), ("testing", True), ("testing", True), ("testing", True), None, None, None, None, None, None],
    # Row 12: Testing
    [None, None, None, None, None, None, ("lobby", False), ("lobby", False), ("lobby", False), ("testing", True), ("testing", True), ("testing", True), ("testing", True), ("testing", True), None, None, None, None, None, None],
    # Row 13-15: Empty
    [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
    [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
    [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
]

DEPARTMENT_LABELS = [
    (3, 5, "CODING", "coding"),
    (10, 3, "MEETING", "meeting"),
    (10, 6, "HR", "hr"),
    (10, 8, "SALES", "sales"),
    (4, 9, "DESIGN", "design"),
    (11, 11, "TESTING", "testing"),
    (4, 2, "KITCHEN", "kitchen"),
    (7, 0, "LOBBY", "lobby"),
]

# Wall collision map - True = wall/blocked, False = walkable
# This defines which tiles agents can walk on
WALL_COLLISION_MAP = [
    [True, True, True, True, True, False, False, False, False, False, True, True, True, True, True, True, True, True, True, True],
    [True, True, True, True, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True, True],
    [True, True, True, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, True, True, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True],
    [True, True, True, True, True, True, False, False, False, False, False, False, False, False, True, True, True, True, True, True],
    [True, True, True, True, True, True, False, False, False, False, False, False, False, False, True, True, True, True, True, True],
    [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True],
    [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True],
    [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True],
]

# Doorways - agents must use these to enter/exit rooms
# Format: (x, y, connects_to_room)
DOORWAYS = [
    # Kitchen door
    (6, 3, "kitchen"),
    # Coding doors
    (1, 6, "coding"),
    (6, 5, "coding"),
    # Meeting doors
    (8, 3, "meeting"),
    (11, 5, "meeting"),
    # HR door
    (8, 6, "hr"),
    # Sales doors
    (8, 8, "sales"),
    (11, 10, "sales"),
    # Design doors
    (2, 8, "design"),
    (6, 10, "design"),
    # Testing doors
    (8, 11, "testing"),
    (13, 11, "testing"),
]

# Department walls for visual rendering only (collision is handled by WALL_COLLISION_MAP)
# Format: (x1, y1, x2, y2, height, color_key)
DEPARTMENT_WALLS = [
    # Kitchen walls with door gap at (6,3)
    (3, 1, 7, 1, 20, "counter"),      # Top
    (3, 1, 3, 4, 20, "counter"),      # Left
    (7, 1, 7, 3, 20, "counter"),      # Right top
    (7, 4, 7, 4, 20, "counter"),      # Right bottom (gap at y=3)
    (3, 4, 6, 4, 20, "counter"),      # Bottom left
    (7, 4, 7, 4, 20, "counter"),      # Bottom right
    
    # Coding area walls with doors
    (1, 4, 7, 4, 18, "coding"),       # Top
    (1, 4, 1, 8, 18, "coding"),       # Left
    (7, 4, 7, 5, 18, "coding"),       # Right top
    (7, 7, 7, 8, 18, "coding"),       # Right bottom (gap at y=6)
    (1, 8, 2, 8, 18, "coding"),       # Bottom left (gap at x=1,y=6)
    (3, 8, 7, 8, 18, "coding"),       # Bottom right
    
    # Internal coding cubicles (lower height)
    (3, 4, 3, 8, 12, "coding"),
    (5, 4, 5, 8, 12, "coding"),
    (1, 6, 7, 6, 12, "coding"),
    
    # Meeting room walls
    (8, 2, 13, 2, 22, "meeting"),     # Top
    (8, 2, 8, 3, 22, "meeting"),      # Left top
    (8, 4, 8, 6, 22, "meeting"),      # Left bottom (gap at y=3)
    (13, 2, 13, 6, 22, "meeting"),    # Right
    (8, 6, 10, 6, 22, "meeting"),     # Bottom left (gap at x=11,y=5)
    (12, 6, 13, 6, 22, "meeting"),    # Bottom right
    
    # HR office walls
    (8, 6, 13, 6, 20, "hr"),          # Top
    (8, 6, 8, 8, 20, "hr"),           # Left (gap at y=6)
    (13, 6, 13, 8, 20, "hr"),         # Right
    (8, 8, 10, 8, 20, "hr"),          # Bottom left (gap at x=8,y=6)
    (11, 8, 13, 8, 20, "hr"),         # Bottom right
    
    # Sales area walls
    (8, 8, 13, 8, 18, "sales"),       # Top
    (8, 8, 8, 8, 18, "sales"),        # Left (gap at y=8)
    (8, 10, 8, 12, 18, "sales"),      # Left bottom
    (13, 8, 13, 10, 18, "sales"),     # Right top
    (13, 11, 13, 12, 18, "sales"),    # Right bottom (gap at y=10)
    (8, 12, 10, 12, 18, "sales"),     # Bottom left
    (12, 12, 13, 12, 18, "sales"),    # Bottom right
    
    # Design studio walls
    (2, 8, 7, 8, 18, "design"),       # Top (gap at x=2,y=8)
    (2, 8, 2, 12, 18, "design"),      # Left
    (7, 8, 7, 10, 18, "design"),      # Right top
    (7, 11, 7, 12, 18, "design"),     # Right bottom (gap at y=10)
    (2, 12, 4, 12, 18, "design"),     # Bottom left
    (6, 12, 7, 12, 18, "design"),     # Bottom right
    
    # Testing lab walls
    (8, 11, 14, 11, 18, "testing"),   # Top (gap at x=8,y=11)
    (8, 11, 8, 13, 18, "testing"),    # Left
    (14, 11, 14, 13, 18, "testing"),  # Right (gap at x=13,y=11)
    (8, 13, 14, 13, 18, "testing"),   # Bottom
]


# ============================================================================
# A* PATHFINDING FOR WALL AVOIDANCE
# ============================================================================

import heapq

def heuristic(a, b):
    """Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def get_neighbors(x, y):
    """Get walkable neighboring tiles."""
    neighbors = []
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
            if not WALL_COLLISION_MAP[ny][nx]:  # Walkable
                neighbors.append((nx, ny))
    return neighbors

def find_path(start, goal):
    """
    A* pathfinding algorithm.
    Returns a list of (x, y) tuples from start to goal, or empty list if no path.
    """
    if WALL_COLLISION_MAP[goal[1]][goal[0]]:
        return []  # Goal is blocked
    
    frontier = []
    heapq.heappush(frontier, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}
    
    while frontier:
        _, current = heapq.heappop(frontier)
        
        if current == goal:
            break
        
        for next_pos in get_neighbors(*current):
            new_cost = cost_so_far[current] + 1
            if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                cost_so_far[next_pos] = new_cost
                priority = new_cost + heuristic(goal, next_pos)
                heapq.heappush(frontier, (priority, next_pos))
                came_from[next_pos] = current
    
    # Reconstruct path
    if goal not in came_from:
        return []  # No path found
    
    path = []
    current = goal
    while current != start:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


# ============================================================================
# ENHANCED 3D FURNITURE DRAWING
# ============================================================================

def draw_desk(surface, screen_x, screen_y, camera):
    """Draw an enhanced desk with 3D depth, drawers, and computer."""
    tw, th = camera.tile_width, camera.tile_height
    scale = camera.zoom
    
    # Desk dimensions
    desk_w = tw * 0.8
    desk_d = th * 0.6
    desk_h = 12 * scale  # Height off ground
    
    # Desk top (isometric rectangle with height)
    top_z = -desk_h
    desk_top = [
        camera.iso_to_screen(0, 0, top_z/scale),  # Placeholder - calculate offsets
    ]
    
    # Calculate actual desk corners with 3D effect
    hw, hd = desk_w/2, desk_d/2
    
    # Base corners (on floor)
    base_bl = (screen_x - hw, screen_y + hd * 0.5)
    base_br = (screen_x + hw, screen_y + hd * 0.5)
    base_fl = (screen_x - hw, screen_y - hd * 0.5)
    base_fr = (screen_x + hw, screen_y - hd * 0.5)
    
    # Top corners (elevated)
    top_offset = -desk_h
    top_bl = (base_bl[0], base_bl[1] + top_offset)
    top_br = (base_br[0], base_br[1] + top_offset)
    top_fl = (base_fl[0], base_fl[1] + top_offset)
    top_fr = (base_fr[0], base_fr[1] + top_offset)
    
    # Draw desk sides (3D effect)
    # Left side
    pygame.draw.polygon(surface, COLORS["desk_side"], 
                       [base_bl, base_fl, top_fl, top_bl])
    # Right side
    pygame.draw.polygon(surface, tuple(c-20 for c in COLORS["desk_side"]),
                       [base_br, base_fr, top_fr, top_br])
    # Front
    pygame.draw.polygon(surface, COLORS["desk_side"],
                       [base_fl, base_fr, top_fr, top_fl])
    
    # Desk top surface
    pygame.draw.polygon(surface, COLORS["desk_top"], [top_bl, top_br, top_fr, top_fl])
    pygame.draw.polygon(surface, tuple(c-30 for c in COLORS["desk_top"]), 
                       [top_bl, top_br, top_fr, top_fl], width=1)
    
    # Drawers on front
    drawer_w = desk_w * 0.25
    drawer_h = desk_h * 0.6
    for i in range(3):
        drawer_x = screen_x - desk_w*0.35 + i * (drawer_w + 4)
        pygame.draw.rect(surface, (100, 65, 30),
                        (drawer_x, base_fl[1] - drawer_h - 2, drawer_w, drawer_h))
        # Drawer handle
        pygame.draw.rect(surface, (60, 40, 20),
                        (drawer_x + drawer_w*0.3, base_fl[1] - drawer_h*0.5, 
                         drawer_w*0.4, 2))
    
    # Chair with backrest
    chair_y = screen_y + th * 0.4
    # Chair seat
    pygame.draw.ellipse(surface, COLORS["chair"], 
                       (screen_x - tw*0.18, chair_y - th*0.1, tw*0.36, th*0.25))
    # Chair back
    pygame.draw.ellipse(surface, tuple(c-20 for c in COLORS["chair"]),
                       (screen_x - tw*0.15, chair_y - th*0.35, tw*0.3, th*0.2))
    # Chair legs
    for dx in [-0.1, 0.1]:
        pygame.draw.line(surface, (50, 40, 30),
                        (screen_x + tw*dx, chair_y + th*0.1),
                        (screen_x + tw*dx, chair_y + th*0.35), 2)
    
    # Computer monitor with stand
    mon_w, mon_h = tw * 0.3, th * 0.4
    stand_w, stand_h = mon_w * 0.2, th * 0.15
    
    # Monitor stand
    pygame.draw.rect(surface, (40, 40, 40),
                    (screen_x - stand_w/2, top_fl[1] + top_offset + 2, stand_w, stand_h))
    # Monitor base
    pygame.draw.ellipse(surface, (50, 50, 50),
                       (screen_x - stand_w, top_fl[1] + top_offset + stand_h, stand_w*2, 4))
    
    # Monitor screen (angled back slightly)
    mon_top = top_fl[1] + top_offset - mon_h + 2
    pygame.draw.rect(surface, COLORS["computer"],
                    (screen_x - mon_w/2, mon_top, mon_w, mon_h))
    # Screen
    pygame.draw.rect(surface, (80, 100, 120),
                    (screen_x - mon_w/2 + 3, mon_top + 3, mon_w - 6, mon_h - 6))
    # Screen content (code lines)
    for i in range(4):
        pygame.draw.rect(surface, (40, 60, 80),
                        (screen_x - mon_w/2 + 6, mon_top + 8 + i*5, mon_w*0.6 - i*3, 2))
    # Screen glow effect
    pygame.draw.line(surface, (100, 130, 150),
                    (screen_x - mon_w/2 + 2, mon_top + mon_h - 2),
                    (screen_x + mon_w/2 - 2, mon_top + mon_h - 2), 1)


def draw_plant(surface, screen_x, screen_y, camera):
    """Draw an enhanced plant with pot, soil, and multiple leaves."""
    tw, th = camera.tile_width, camera.tile_height
    scale = camera.zoom
    
    # Pot with 3D depth
    pot_w, pot_h = 14 * scale, 12 * scale
    pot_top = screen_y + th * 0.15
    
    # Pot body (truncated cone look)
    pygame.draw.ellipse(surface, (100, 70, 50),
                       (screen_x - pot_w*0.4, pot_top - pot_h*0.3, pot_w*0.8, pot_h*0.5))
    pygame.draw.ellipse(surface, (120, 80, 60),
                       (screen_x - pot_w*0.5, pot_top - pot_h, pot_w, pot_h*0.6))
    # Pot rim
    pygame.draw.ellipse(surface, (140, 100, 70),
                       (screen_x - pot_w*0.55, pot_top - pot_h - 3, pot_w*1.1, 6))
    
    # Soil
    pygame.draw.ellipse(surface, (60, 40, 30),
                       (screen_x - pot_w*0.4, pot_top - pot_h + 2, pot_w*0.8, 4))
    
    # Multiple leaves with varying sizes and angles
    leaf_colors = [(50, 120, 50), (60, 140, 60), (40, 100, 40), (70, 160, 70)]
    leaf_positions = [
        (0, -25, 0.8), (-15, -20, 0.6), (15, -22, 0.7),
        (-8, -30, 0.9), (10, -28, 0.75), (0, -35, 1.0),
        (-20, -15, 0.5), (18, -18, 0.55)
    ]
    
    for i, (lx, ly, size) in enumerate(leaf_positions):
        color = leaf_colors[i % len(leaf_colors)]
        leaf_x = screen_x + lx * scale
        leaf_y = pot_top - pot_h + ly * scale
        leaf_w = 12 * size * scale
        leaf_h = 16 * size * scale
        
        # Leaf shape (pointed ellipse)
        pygame.draw.ellipse(surface, color,
                           (leaf_x - leaf_w/2, leaf_y - leaf_h/2, leaf_w, leaf_h))
        # Leaf vein
        pygame.draw.line(surface, tuple(c-20 for c in color),
                        (leaf_x, leaf_y + leaf_h*0.3),
                        (leaf_x, leaf_y - leaf_h*0.4), 1)


def draw_sofa(surface, screen_x, screen_y, camera):
    """Draw an enhanced sofa with cushions and backrest."""
    tw, th = camera.tile_width, camera.tile_height
    scale = camera.zoom
    
    sofa_w, sofa_d = tw * 0.9, th * 0.7
    
    # Sofa base shadow
    pygame.draw.ellipse(surface, (30, 30, 40),
                       (screen_x - sofa_w*0.45, screen_y + th*0.1, sofa_w*0.9, th*0.15))
    
    # Sofa backrest (raised)
    back_h = 15 * scale
    back_rect = pygame.Rect(screen_x - sofa_w*0.4, 
                           screen_y - th*0.5 - back_h,
                           sofa_w*0.8, back_h)
    pygame.draw.rect(surface, COLORS["sofa"], back_rect)
    # Backrest cushion lines
    for i in range(1, 3):
        x = screen_x - sofa_w*0.4 + (sofa_w*0.8 * i / 3)
        pygame.draw.line(surface, tuple(c-30 for c in COLORS["sofa"]),
                        (x, screen_y - th*0.5 - back_h),
                        (x, screen_y - th*0.5), 1)
    
    # Seat cushions
    seat_rect = pygame.Rect(screen_x - sofa_w*0.45, 
                           screen_y - th*0.25,
                           sofa_w*0.9, th*0.35)
    pygame.draw.rect(surface, (130, 80, 80), seat_rect)
    # Cushion division
    pygame.draw.line(surface, tuple(c-40 for c in COLORS["sofa"]),
                    (screen_x, screen_y - th*0.25),
                    (screen_x, screen_y + th*0.1), 2)
    
    # Armrests
    arm_w = sofa_w * 0.15
    arm_h = th * 0.25
    # Left arm
    pygame.draw.rect(surface, tuple(c-20 for c in COLORS["sofa"]),
                    (screen_x - sofa_w*0.45, screen_y - th*0.35, arm_w, arm_h))
    # Right arm
    pygame.draw.rect(surface, tuple(c-20 for c in COLORS["sofa"]),
                    (screen_x + sofa_w*0.3, screen_y - th*0.35, arm_w, arm_h))
    
    # Throw pillow
    pygame.draw.ellipse(surface, (150, 100, 100),
                       (screen_x - sofa_w*0.2, screen_y - th*0.35, tw*0.2, th*0.2))


def draw_counter(surface, screen_x, screen_y, camera):
    """Draw an enhanced counter with cabinets and appliances."""
    tw, th = camera.tile_width, camera.tile_height
    scale = camera.zoom
    
    counter_w, counter_d = tw * 0.9, th * 0.6
    counter_h = 18 * scale
    
    # Counter shadow
    pygame.draw.ellipse(surface, (30, 30, 40),
                       (screen_x - counter_w*0.45, screen_y + th*0.15, 
                        counter_w*0.9, th*0.1))
    
    # Counter sides (3D)
    hw, hd = counter_w/2, counter_d/2
    base_points = [
        (screen_x - hw, screen_y - hd*0.5),
        (screen_x + hw, screen_y - hd*0.5),
        (screen_x + hw, screen_y + hd*0.5),
        (screen_x - hw, screen_y + hd*0.5),
    ]
    top_points = [(x, y - counter_h) for x, y in base_points]
    
    # Side faces
    pygame.draw.polygon(surface, (160, 140, 120),
                       [base_points[3], base_points[0], top_points[0], top_points[3]])
    pygame.draw.polygon(surface, (140, 120, 100),
                       [base_points[0], base_points[1], top_points[1], top_points[0]])
    pygame.draw.polygon(surface, (180, 160, 140),
                       [base_points[1], base_points[2], top_points[2], top_points[1]])
    
    # Counter top
    pygame.draw.polygon(surface, COLORS["counter"], top_points)
    pygame.draw.polygon(surface, (160, 140, 120), top_points, width=1)
    
    # Cabinet doors on front
    door_w = counter_w * 0.25
    door_h = counter_h * 0.7
    for i in range(3):
        door_x = screen_x - counter_w*0.35 + i * (door_w + 4)
        pygame.draw.rect(surface, (150, 130, 110),
                        (door_x, base_points[0][1] - door_h - 2, door_w, door_h))
        # Door handle
        pygame.draw.circle(surface, (80, 70, 60),
                          (int(door_x + door_w - 4), int(base_points[0][1] - door_h*0.5)), 2)
    
    # Coffee maker on top
    cm_x, cm_y = screen_x - tw*0.2, top_points[0][1] + 3
    pygame.draw.rect(surface, (40, 40, 40),
                    (cm_x, cm_y - 12*scale, 10*scale, 12*scale))
    pygame.draw.rect(surface, (60, 60, 60),
                    (cm_x + 2, cm_y - 10*scale, 6*scale, 4*scale))  # Screen
    # Coffee pot
    pygame.draw.ellipse(surface, (80, 60, 40),
                       (cm_x + 12*scale, cm_y - 8*scale, 8*scale, 8*scale))


# ============================================================================
# LOW-POLY AGENT (Human Shape)
# ============================================================================

class Agent:
    """A low-poly human agent that walks between tiles with wall collision."""
    
    def __init__(self, name: str, job_role: str, start_x: int, start_y: int):
        self.name = name
        self.job_role = job_role
        self.grid_x = start_x
        self.grid_y = start_y
        self.target_x = start_x
        self.target_y = start_y
        
        # Animation state
        self.walk_progress = 0.0  # 0.0 to 1.0
        self.walk_speed = 0.025
        self.walking = False
        
        # Walking animation (bob up/down)
        self.bob_phase = 0.0
        self.bob_amplitude = 2
        
        # Color based on job role
        self.colors = {
            "developer": (60, 120, 200),
            "tester": (60, 200, 100),
            "pm": (200, 100, 60),
            "janitor": (180, 160, 80),
            "designer": (200, 80, 160),
            "sales": (80, 180, 180),
            "hr": (160, 80, 140),
        }
        self.color = self.colors.get(job_role, (150, 150, 150))
        
        # Path for walking (A* pathfinding)
        self.path = []
        self.path_index = 0
        self.current_room = None
        self.target_room = None
    
    def set_target(self, target_x: int, target_y: int):
        """Set a new walking target."""
        self.target_x = target_x
        self.target_y = target_y
        self.walking = True
        self.walk_progress = 0.0
    
    def set_target_with_pathfinding(self, target_x: int, target_y: int):
        """Set target using A* pathfinding to avoid walls."""
        start = (self.grid_x, self.grid_y)
        goal = (target_x, target_y)
        
        self.path = find_path(start, goal)
        self.path_index = 0
        
        if self.path:
            self._advance_path()
        else:
            # No path found - stay in place
            pass
    
    def update(self):
        """Update agent position and animation."""
        if self.walking:
            self.walk_progress += self.walk_speed
            self.bob_phase += 0.3
            
            if self.walk_progress >= 1.0:
                self.walk_progress = 1.0
                self.walking = False
                self.grid_x = self.target_x
                self.grid_y = self.target_y
                self.bob_phase = 0.0
                
                # Continue on path or pick new target
                if len(self.path) > 0 and self.path_index < len(self.path):
                    self._advance_path()
                else:
                    self.path = []
                    self.path_index = 0
                    self._pick_random_target()
        
        # Idle bob
        if not self.walking:
            self.bob_phase += 0.03
    
    def _pick_random_target(self):
        """Pick a random reachable tile using pathfinding."""
        import random
        
        # Try to find a valid target
        for _ in range(20):  # Limit attempts
            # Pick a random position in the office
            new_x = random.randint(1, GRID_WIDTH - 2)
            new_y = random.randint(1, GRID_HEIGHT - 2)
            
            # Check if walkable
            if not WALL_COLLISION_MAP[new_y][new_x]:
                # Use pathfinding to get there
                self.set_target_with_pathfinding(new_x, new_y)
                return
    
    def _advance_path(self):
        """Advance to next point in path."""
        if self.path_index < len(self.path):
            self.set_target(*self.path[self.path_index])
            self.path_index += 1
        else:
            self.path = []
            self.path_index = 0
    
    def get_screen_pos(self, camera: IsometricCamera) -> tuple:
        """Get current screen position (interpolated if walking)."""
        if self.walking:
            # Interpolate between current and target
            x = self.grid_x + (self.target_x - self.grid_x) * self.walk_progress
            y = self.grid_y + (self.target_y - self.grid_y) * self.walk_progress
        else:
            x, y = self.grid_x, self.grid_y
        
        return camera.iso_to_screen(x, y)
    
    def draw(self, surface, camera: IsometricCamera):
        """Draw the low-poly agent (scaled down for larger tiles)."""
        screen_x, screen_y = self.get_screen_pos(camera)
        
        # Bob up/down when walking
        bob = 0
        if self.walking or self.bob_phase > 0:
            bob = math.sin(self.bob_phase) * self.bob_amplitude * camera.zoom
        
        # Scale by zoom - agents are now smaller relative to tiles
        scale = camera.zoom * 0.6  # Scale down to 60%
        
        # Body (ellipse)
        body_w = 10 * scale
        body_h = 14 * scale
        body_y = screen_y - body_h - 4 * scale + bob
        
        pygame.draw.ellipse(surface, self.color,
                           (screen_x - body_w/2, body_y, body_w, body_h))
        
        # Head
        head_r = 4 * scale
        head_y = body_y - head_r - 1 * scale
        pygame.draw.circle(surface, COLORS["agent"],
                          (int(screen_x), int(head_y)), int(head_r))
        
        # Hair (simple arc)
        pygame.draw.arc(surface, (40, 30, 20),
                       (screen_x - head_r, head_y - head_r, head_r*2, head_r*2),
                       3.14, 0, 2)
        
        # Arms
        arm_y = body_y + 2 * scale
        pygame.draw.line(surface, COLORS["agent"],
                        (screen_x - body_w/2, arm_y),
                        (screen_x - body_w/2 - 4*scale, arm_y + 3*scale), 2)
        pygame.draw.line(surface, COLORS["agent"],
                        (screen_x + body_w/2, arm_y),
                        (screen_x + body_w/2 + 4*scale, arm_y + 3*scale), 2)
        
        # Legs (walking animation)
        leg_y = body_y + body_h
        walk_offset = 0
        if self.walking:
            walk_offset = math.sin(self.bob_phase * 1.5) * 2 * scale
        
        pygame.draw.line(surface, (60, 60, 80),
                        (screen_x - 2*scale, leg_y),
                        (screen_x - 2*scale + walk_offset, leg_y + 6*scale), 2)
        pygame.draw.line(surface, (60, 60, 80),
                        (screen_x + 2*scale, leg_y),
                        (screen_x + 2*scale - walk_offset, leg_y + 6*scale), 2)
        
        # Name label (smaller)
        font = pygame.font.SysFont("Arial", int(8 * scale))
        label = font.render(self.name, True, COLORS["text"])
        shadow = font.render(self.name, True, COLORS["text_shadow"])
        surface.blit(shadow, (screen_x - label.get_width()//2 + 1, body_y - 12*scale + 1))
        surface.blit(label, (screen_x - label.get_width()//2, body_y - 12*scale))


# ============================================================================
# MAIN VISUALIZATION CLASS
# ============================================================================

class OfficeVisualization:
    """Main visualization class for the isometric office floor."""
    
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Agent Office — Isometric Floor Plan")
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 14)
        self.font_title = pygame.font.SysFont("Arial", 16, bold=True)
        
        # Camera
        self.camera = IsometricCamera()
        
        # Create agents in valid starting positions (walkable tiles)
        self.agents = [
            Agent("Alice", "developer", 4, 5),
            Agent("Bob", "tester", 10, 11),
            Agent("Carol", "pm", 10, 3),
            Agent("David", "designer", 4, 9),
        ]
        
        # Start all agents walking
        for agent in self.agents:
            agent._pick_random_target()
        
        # Furniture placement for expanded grid (multiple items per department)
        self.furniture = [
            # Coding area desks (6 desks)
            (2, 5, "desk"), (3, 5, "desk"), (4, 5, "desk"),
            (2, 6, "desk"), (3, 6, "desk"), (5, 6, "desk"),
            (2, 7, "desk"), (4, 7, "desk"),
            # Meeting area
            (9, 3, "sofa"), (10, 3, "sofa"), (11, 4, "desk"),
            # HR area
            (9, 6, "desk"), (11, 6, "desk"),
            # Sales area
            (9, 8, "desk"), (10, 8, "desk"), (11, 8, "desk"),
            (9, 9, "desk"), (10, 9, "desk"),
            # Design area
            (3, 9, "desk"), (4, 9, "desk"), (3, 10, "desk"), (4, 10, "desk"),
            # Testing area
            (10, 11, "desk"), (11, 11, "desk"), (12, 11, "desk"),
            (10, 12, "desk"), (11, 12, "desk"),
            # Kitchen
            (4, 2, "counter"), (5, 2, "counter"),
            # Lobby plants
            (6, 1, "plant"), (8, 1, "plant"), (7, 4, "plant"),
            (7, 7, "plant"), (7, 10, "plant"),
        ]
        
        self.running = True
    
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
            
            # Camera controls
            self.camera.handle_event(event)
    
    def update(self):
        """Update simulation state."""
        for agent in self.agents:
            agent.update()
            
            # Occasionally make agent walk to new location
            if not agent.walking and pygame.time.get_ticks() % 3000 < 50:
                agent._pick_random_target()
    
    def draw_grid_background(self):
        """Draw empty tiles."""
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if OFFICE_FLOOR[y][x] is None:
                    color = COLORS["floor"]
                    draw_iso_tile(self.screen, x, y, color, self.camera)
    
    def draw_floor(self):
        """Draw the office floor with department tiles."""
        tiles_to_draw = []
        
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cell = OFFICE_FLOOR[y][x]
                if cell is not None:
                    dept_key, has_height = cell
                    tiles_to_draw.append((x, y, dept_key, has_height))
        
        tiles_to_draw.sort(key=lambda t: t[0] + t[1])
        
        for x, y, dept_key, has_height in tiles_to_draw:
            color = COLORS.get(dept_key, COLORS["floor"])
            if has_height:
                draw_iso_tile_with_height(self.screen, x, y, color, height=8, camera=self.camera)
            else:
                draw_iso_tile(self.screen, x, y, color, self.camera)
    
    def draw_walls(self):
        """Draw partition walls between departments."""
        for x1, y1, x2, y2, height, color_key in DEPARTMENT_WALLS:
            color = COLORS.get(color_key, COLORS["floor"])
            draw_wall(self.screen, x1, y1, x2, y2, height, color, self.camera)
    
    def draw_furniture(self):
        """Draw low-poly furniture on tiles."""
        for grid_x, grid_y, ftype in self.furniture:
            screen_pos = self.camera.iso_to_screen(grid_x + 0.5, grid_y + 0.5)
            
            if ftype == "desk":
                draw_desk(self.screen, screen_pos[0], screen_pos[1], self.camera)
            elif ftype == "plant":
                draw_plant(self.screen, screen_pos[0], screen_pos[1], self.camera)
            elif ftype == "sofa":
                draw_sofa(self.screen, screen_pos[0], screen_pos[1], self.camera)
            elif ftype == "counter":
                draw_counter(self.screen, screen_pos[0], screen_pos[1], self.camera)
    
    def draw_department_labels(self):
        """Draw department names."""
        for grid_x, grid_y, name, color_key in DEPARTMENT_LABELS:
            screen_pos = self.camera.iso_to_screen(grid_x, grid_y)
            label_x = screen_pos[0]
            label_y = screen_pos[1] - 20 * self.camera.zoom
            
            # Scale font by zoom
            scaled_font = pygame.font.SysFont("Arial", int(16 * self.camera.zoom), bold=True)
            shadow = scaled_font.render(name, True, COLORS["text_shadow"])
            text = scaled_font.render(name, True, COLORS["text"])
            
            self.screen.blit(shadow, (label_x - shadow.get_width()//2 + 1, label_y + 1))
            self.screen.blit(text, (label_x - text.get_width()//2, label_y))
    
    def draw_agents(self):
        """Draw all agents."""
        for agent in self.agents:
            agent.draw(self.screen, self.camera)
    
    def draw_ui(self):
        """Draw UI elements."""
        # Title
        title = self.font_title.render("TECHCORP HQ — Isometric Office Floor", True, COLORS["text"])
        self.screen.blit(title, (20, 20))
        
        # Controls
        controls = self.font.render("Drag: Pan  |  Scroll: Zoom  |  R: Reset  |  Q: Quit", True, COLORS["text"])
        self.screen.blit(controls, (20, SCREEN_HEIGHT - 30))
        
        # Zoom indicator
        zoom_text = self.font.render(f"Zoom: {self.camera.zoom:.1f}x", True, COLORS["text"])
        self.screen.blit(zoom_text, (20, 45))
        
        # Legend
        legend_x = SCREEN_WIDTH - 180
        legend_y = 20
        legend_title = self.font_title.render("Departments:", True, COLORS["text"])
        self.screen.blit(legend_title, (legend_x, legend_y))
        
        departments = [
            ("CODING", "coding"),
            ("TESTING", "testing"),
            ("MEETING", "meeting"),
            ("KITCHEN", "kitchen"),
            ("DESIGN", "design"),
            ("SALES", "sales"),
            ("HR", "hr"),
            ("LOBBY", "lobby"),
        ]
        
        for i, (name, key) in enumerate(departments):
            y_pos = legend_y + 25 + i * 20
            pygame.draw.rect(self.screen, COLORS[key], (legend_x, y_pos, 16, 16))
            text = self.font.render(name, True, COLORS["text"])
            self.screen.blit(text, (legend_x + 22, y_pos + 1))
        
        # Agent count
        agent_count = self.font.render(f"Agents: {len(self.agents)}", True, COLORS["text"])
        self.screen.blit(agent_count, (20, 65))
    
    def draw(self):
        """Main draw method."""
        self.screen.fill(COLORS["background"])
        
        # Draw in order (back to front for proper depth)
        self.draw_grid_background()
        self.draw_floor()
        self.draw_walls()  # Walls between departments
        self.draw_furniture()
        self.draw_department_labels()
        self.draw_agents()
        self.draw_ui()
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop."""
        print("Starting Agent Office Isometric Visualization...")
        print("   Controls:")
        print("   - Left-click + drag: Pan view")
        print("   - Scroll wheel: Zoom in/out")
        print("   - R: Reset camera")
        print("   - Q or ESC: Quit")
        print(f"   Office size: {GRID_WIDTH}x{GRID_HEIGHT} tiles")
        print(f"   Agents: {len(self.agents)}")
        
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
    viz = OfficeVisualization()
    viz.run()


if __name__ == "__main__":
    main()
