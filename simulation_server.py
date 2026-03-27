"""
simulation_server.py — Minimal HTTP server exposing simulation state as JSON.

This proves the Python-simulation-as-source-of-truth + JSON-over-HTTP integration path.

Usage:
    python simulation_server.py

Endpoints:
    GET  /         -> simple info text
    GET  /state    -> full snapshot: agents (with x,y,z), posts, edges, tick, state
    POST /tick     -> advance one tick; returns events that occurred

No auth, no database, no fancy frontend. Just JSON from Python simulation.
"""

import json
import math
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from agent_office.demo_setup import build_demo_simulation
from agent_office.simulation import SimulationEvent
import random
from agent_office.office import OfficeTask, Product, TaskType, SAMPLE_TASKS
from agent_office.post import create_sample_posts

# Static files directory (web/ next to this script)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


# -----------------------------------------------------------------------------
# Simulation Setup (happens once at startup)
# -----------------------------------------------------------------------------

print("Building demo simulation (with office)...")
team, office, network, sim = build_demo_simulation(
    num_initial_tasks=5,
    num_initial_posts=15,
    connect_office=True,
    verbose=False,
)

# Add initial products for the office (since demo_setup doesn't add them)
from agent_office.office import SAMPLE_PRODUCTS
for product in SAMPLE_PRODUCTS[:3]:
    office.add_product(product)
print(f"Added {min(3, len(SAMPLE_PRODUCTS))} initial products to office")

# Assign simple circular positions to agents (server-side, since core has none)
AGENT_POSITIONS: dict[str, tuple[float, float, float]] = {}
agents = network.get_all_agents()
n = max(1, len(agents))
for i, agent in enumerate(agents):
    angle = 2 * math.pi * i / n
    radius = 5.0
    x = round(radius * math.cos(angle), 2)
    z = round(radius * math.sin(angle), 2)
    AGENT_POSITIONS[agent.id] = (x, 0.0, z)

print(f"Simulation ready: {len(agents)} agents, tick={sim.current_tick}")


# -----------------------------------------------------------------------------
# Helpers: serialize simulation objects to JSON-safe dicts
# -----------------------------------------------------------------------------

def serialize_event(event: SimulationEvent) -> dict:
    """Convert a SimulationEvent to a JSON-serializable dict."""
    return {
        "timestamp": event.timestamp.isoformat(),
        "tick": event.tick,
        "event_type": event.event_type,
        "agent_id": event.agent_id,
        "agent_name": event.agent_name,
        "post_id": event.post_id,
        "post_subject": event.post_subject,
        "behavior": event.behavior,
        "details": event.details,
    }


def get_state_snapshot() -> dict:
    """Build the full /state response from current simulation."""
    # Agents with positions
    agent_list = []
    for agent in sim.network.get_all_agents():
        stats = agent.get_stats()
        x, y, z = AGENT_POSITIONS.get(agent.id, (0.0, 0.0, 0.0))
        stats["x"] = x
        stats["y"] = y
        stats["z"] = z
        agent_list.append(stats)

    # Posts
    post_list = [post.get_stats() for post in sim.posts.values()]

    # Edges (connections)
    edge_list = []
    for follower_id, conns in sim.network.connections.items():
        for conn in conns:
            edge_list.append({
                "from": follower_id,
                "to": conn.followee_id,
                "strength": conn.strength,
                "trust": conn.trust_level,
            })

    # Recent events (last 50 for UI display)
    event_list = []
    for ev in list(sim.events)[-50:]:
        event_list.append({
            "timestamp": ev.timestamp.isoformat(),
            "tick": ev.tick,
            "event_type": ev.event_type,
            "agent_id": ev.agent_id,
            "agent_name": ev.agent_name,
            "post_id": ev.post_id,
            "post_subject": ev.post_subject,
            "behavior": ev.behavior,
            "details": ev.details,
        })

    # Office data (products, tasks, stats) if office is connected
    office_data = None
    if sim.office:
        office_data = {
            "stats": sim.office.get_stats(),
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "status": p.status.value,
                    "progress": round(p.get_progress() * 100, 1),
                    "contributors": list(p.contributors),
                }
                for p in sim.office.products[:8]  # limit to 8
            ],
            "active_products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "status": p.status.value,
                    "progress": round(p.get_progress() * 100, 1),
                    "contributors": list(p.contributors),
                }
                for p in sim.office.get_active_products()[:5]
            ],
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "progress": round(t.progress * 100, 1),
                    "assigned_to": t.assigned_to,
                    "type": t.task_type.value,
                }
                for t in sim.office.tasks[:20]
            ],
            "in_progress_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "progress": round(t.progress * 100, 1),
                    "assigned_to": t.assigned_to,
                    "type": t.task_type.value,
                }
                for t in sim.office.get_in_progress_tasks()[:10]
            ],
        }

    return {
        "tick": sim.current_tick,
        "state": sim.state.value,
        "agents": agent_list,
        "posts": post_list,
        "edges": edge_list,
        "events": event_list,
        "office": office_data,
    }


# -----------------------------------------------------------------------------
# HTTP Handler
# -----------------------------------------------------------------------------

class SimulationHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep logs minimal
        print(f"[server] {args[0]}")

    def _set_json_headers(self, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _serve_static_file(self, filepath):
        """Serve a static file from STATIC_DIR."""
        full = os.path.join(STATIC_DIR, filepath)
        if os.path.isfile(full):
            # Guess content type
            if filepath.endswith(".html"):
                ctype = "text/html"
            elif filepath.endswith(".js"):
                ctype = "application/javascript"
            elif filepath.endswith(".css"):
                ctype = "text/css"
            else:
                ctype = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            with open(full, "rb") as f:
                self.wfile.write(f.read())
            return True
        return False

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Serve the 3D viewer HTML at root and /index.html
        if path == "/" or path == "/index.html":
            if self._serve_static_file("index.html"):
                return
            # Fallback to JSON if file missing
            self._set_json_headers(200)
            self.wfile.write(json.dumps({
                "ok": True,
                "info": "Simulation server running. Use GET /state and POST /tick.",
                "tick": sim.current_tick,
                "state": sim.state.value,
            }).encode("utf-8"))
            return

        if path == "/state":
            self._set_json_headers(200)
            self.wfile.write(json.dumps(get_state_snapshot()).encode("utf-8"))
            return

        # Try static file (for future assets)
        if path.startswith("/"):
            candidate = path.lstrip("/")
            if self._serve_static_file(candidate):
                return

        # Unknown path
        self._set_json_headers(404)
        self.wfile.write(json.dumps({"error": "not found", "path": path}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/tick":
            events = sim.tick()
            # --- Dynamic content generation (like run_continuous_office.py) ---
            # Keep simulation alive forever by generating new work
            if sim.office:
                # Generate new tasks if running low
                pending = sim.office.get_pending_tasks()
                if len(pending) < 3:
                    count = random.randint(2, 4)
                    for _ in range(count):
                        template = random.choice(SAMPLE_TASKS)
                        task = OfficeTask(
                            title=template.title,
                            description=template.description,
                            task_type=template.task_type,
                            difficulty=template.difficulty,
                        )
                        sim.office.add_task(task)
                    # Log as office event
                    sim.office_events.append({
                        "tick": sim.current_tick,
                        "event_type": "tasks_generated",
                        "count": count,
                    })
                
                # Generate new product if all shipped
                active = sim.office.get_active_products()
                if len(active) == 0:
                    from agent_office.office import ProductStatus
                    names = ["Project Alpha", "Project Beta", "Project Gamma", "Project Delta", "Project Omega"]
                    new_product = Product(
                        name=random.choice(names),
                        description="Auto-generated initiative",
                        product_type=random.choice([TaskType.CODING, TaskType.DESIGNING, TaskType.PLANNING]),
                        tasks_required=random.randint(4, 8)
                    )
                    sim.office.add_product(new_product)
                    sim.office_events.append({
                        "tick": sim.current_tick,
                        "event_type": "product_created",
                        "product_name": new_product.name,
                    })
                
                # Occasionally add random info posts (10% chance)
                if random.random() < 0.10:
                    posts = create_sample_posts()
                    post = random.choice(posts)
                    agent = random.choice(list(sim.network.agents.values()))
                    sim.add_post(post, agent)
            
            event_dicts = [serialize_event(e) for e in events]
            self._set_json_headers(200)
            self.wfile.write(json.dumps({
                "tick": sim.current_tick,
                "events": event_dicts,
            }).encode("utf-8"))
            return

        self._set_json_headers(404)
        self.wfile.write(json.dumps({"error": "not found", "path": path}).encode("utf-8"))

    def do_OPTIONS(self):
        # CORS preflight support (simple)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def run(host: str = "0.0.0.0", port: int = 8080):
    server = HTTPServer((host, port), SimulationHandler)
    print(f"\nSimulation server listening on http://{host}:{port}")
    print("Endpoints:")
    print("  GET  /       -> info")
    print("  GET  /state  -> full snapshot (agents+positions, posts, edges, tick, state)")
    print("  POST /tick   -> advance one tick; returns events")
    print("\nPress Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    run()
