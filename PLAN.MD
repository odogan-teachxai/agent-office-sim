# 🏢 Agent Office — Evolution Plan

> **Goal:** Transform the existing information-spread simulation into a **living office simulation** where agents have job roles (developers, PMs, testers, janitors, etc.) and work on their jobs *while simultaneously* participating in the information spread network.

---

## 🎯 Vision

Imagine a virtual office:
- **Developers** code features, **Testers** find bugs, **PMs** assign tasks
- Agents gossip, share news, and spread (mis)information during coffee breaks
- The existing info-spread simulation continues to run **unchanged** in the background
- Office work and information spread happen **in parallel**

```
┌─────────────────────────────────────────────────────────────────┐
│                         AGENT OFFICE                            │
│                                                                 │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│   │  DEVELOPER  │   │     PM      │   │   TESTER    │           │
│   │  (writes)   │◄──►│ (coordinates)│◄──►│  (validates)│           │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘           │
│          │                 │                 │                  │
│          └─────────────────┼─────────────────┘                  │
│                            │                                    │
│              ┌─────────────▼─────────────┐                      │
│              │   INFORMATION SPREAD      │                      │
│              │  (existing simulation)    │                      │
│              │  • Posts propagate        │                      │
│              │  • Agents share/verify    │                      │
│              │  • Misinfo detection      │                      │
│              └───────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Current State

| Component | Status | Notes |
|-----------|--------|-------|
| `AgentType` | ✅ Exists | Info-sharing behavior (IMMEDIATE_SHARER, SKEPTIC, etc.) |
| `Agent` traits | ✅ Exists | gullibility, skepticism, influence, etc. |
| `JobRole` | ✅ Done | DEVELOPER, PM, TESTER, JANITOR, DESIGNER, INTERN, SALES_REP, HR_MANAGER |
| `job_role` field | ✅ Done | Optional, orthogonal to `agent_type` |
| `OfficeTask` & `Office` | ✅ Done | Task system with assignment, progress, completion |
| Office work in tick | ✅ Done | Runs alongside info-spread each tick |
| Work → Posts | ✅ Done | Task completions generate posts that spread |
| Products | ✅ Done | Products evolve from Planning → Shipped |
| Continuous Simulation | ✅ Done | `run_continuous_office.py` with pause/resume |
| ML Job Role Features | ✅ Done | 11 new features for misinformation detection |
| Run scripts | ✅ Done | run_continuous_office.py, run_live_office.py, run_integrated.py, run_office.py, run.py |
| Simulation loop | ✅ Exists | Processes info-spread ticks |
| Network | ✅ Exists | Follower/followee graph |
| 3D Visualization | 🔜 Planned | Step 6 - "Sims-like" office view |

---

## ✅ Step 1 — DONE: Structural Foundation

**What was done:**
- Added `JobRole` enum in [agent.py](/testbed/agent-office-sim/agent_office/agent.py):
  ```python
  class JobRole(Enum):
      DEVELOPER = "developer"
      PROJECT_MANAGER = "project_manager"
      TESTER = "tester"
      JANITOR = "janitor"
      DESIGNER = "designer"
      INTERN = "intern"
      SALES_REP = "sales_rep"
      HR_MANAGER = "hr_manager"
  ```
- Added `job_role: Optional[JobRole] = None` to `Agent` dataclass
- Added placeholder office-work fields: `current_task`, `productivity`
- Updated `create_agent_from_type()` to accept optional `job_role`
- Exported `JobRole` in `__init__.py`
- **Backward compatible** — existing code works unchanged

**Example usage now:**
```python
from agent_office import create_agent_from_type, AgentType, JobRole

# Old way (still works):
dev = create_agent_from_type("dev1", "Alice", AgentType.CAUTIOUS_SHARER)

# New way (with job role):
pm = create_agent_from_type("pm1", "Bob", AgentType.INFLUENCER, job_role=JobRole.PROJECT_MANAGER)
# pm.agent_type == INFLUENCER (info behavior)
# pm.job_role == PROJECT_MANAGER (office role)
```

---

## 📋 Follow-Up Steps (Do NOT implement all at once)

### Step 2 — DONE: Define Office Tasks

**Status:** ✅ COMPLETED

**Goal:** Create a simple task system agents can "work on."

**Files to touch:** `agent_office/office.py` (new file)

**What to do:**
1. Create `OfficeTask` dataclass:
   ```python
   @dataclass
   class OfficeTask:
       id: str
       title: str
       assigned_to: Optional[str]  # agent_id
       status: str  # "pending", "in_progress", "done"
       difficulty: float  # 0.1 - 1.0
   ```
2. Create `Office` class (minimal):
   ```python
   class Office:
       def __init__(self):
           self.tasks: list[OfficeTask] = []
           self.agents: list[Agent] = []
       
       def assign_task(self, task: OfficeTask, agent: Agent):
           task.assigned_to = agent.id
           agent.current_task = task.title
       
       def complete_task(self, task: OfficeTask, agent: Agent):
           task.status = "done"
           agent.current_task = None
           # Maybe boost productivity or morale?
   ```
3. Add 3-4 sample tasks (e.g., "Fix login bug", "Write tests", "Clean kitchen")
4. **Do NOT** hook into simulation yet — just standalone

**Success criteria:** Can create tasks, assign to agents, mark complete.

---

### Step 3 — DONE: Job Role Behaviors

**Status:** ✅ COMPLETED

**Goal:** Different job roles do different work.

**Files to touch:** `agent_office/office.py`

**What to do:**
1. Add a simple `work()` method or dispatch per job role:
   ```python
   def agent_do_work(agent: Agent, office: Office):
       if agent.job_role == JobRole.DEVELOPER:
           # Look for coding tasks
           pass
       elif agent.job_role == JobRole.TESTER:
           # Look for testing tasks
           pass
       elif agent.job_role == JobRole.PROJECT_MANAGER:
           # Assign tasks to others
           pass
       elif agent.job_role == JobRole.JANITOR:
           # "Clean" (maybe reduces some "mess" counter)
           pass
   ```
2. Each role has a preferred task type (optional mapping)
3. **Keep it simple** — just print/log what they do, no complex logic

**Success criteria:** Different roles "prefer" different work conceptually.

---

### Step 4 — DONE: Integrate Office into Simulation Tick

**Status:** ✅ COMPLETED

**What was done:**
- Added optional `office: Office = None` and `on_office_event` callback to `Simulation.__init__()`
- Added office work phase in `tick()` that runs AFTER info-spread processing:
  ```python
  def tick(self):
      # === PHASE 1: INFO-SPREAD (unchanged) ===
      events = self._process_pending_shares_batch()
      
      # === PHASE 2: OFFICE WORK (optional) ===
      if self.office:
          completed_tasks = self.office.tick()
          # Track office events separately
      
      return events
  ```
- Added `office_events` list to track office activity
- Updated `get_simulation_report()` to include office stats when available
- Created `run_integrated.py` demo showing both systems coexisting
- **Info-spread logic is completely unchanged** — verified with original `run.py`

**Verification:**
```bash
# Run integrated simulation (both systems)
python3 run_integrated.py --ticks 25

# Original simulation still works unchanged
python3 run.py --agents 5 --posts 2
```

**Output shows both systems:**
```
[TICK 003]
  ✅ Carol | project_manager → COMPLETED: Organize team meeting
  📢 Bob | developer → SHARE IMMEDIATELY: Scientists Discover...
```

---

### Step 5 — DONE: Connect Info Spread to Office (Soft Coupling)

**Status:** ✅ COMPLETED

**What was done:**
- Added `TASK_COMPLETION_POSTS` templates in [office.py](/testbed/agent-office-sim/agent_office/office.py) with realistic post messages for each task type
- Created `create_task_completion_post()` function that generates posts when tasks complete
- Added `on_post_create` callback to Office class for post injection
- Updated Simulation to auto-connect office via `_connect_office()` method
- When tasks complete:
  1. Post is created with personalized message (e.g., "Alice: Just fixed a tricky bug!")
  2. Post is injected into simulation via `add_post()`
  3. Post spreads through network naturally
  4. Other agents react based on traits (share/verify/ignore/flag)
- Created `run_live_office.py` demo showing the full flow with detailed logging
- Work posts marked with 💼 indicator in logs
- Agents add commentary like "Great work!" or "Wait, did they actually finish that?"

**Example output:**
```
[TICK 002]
  ✅ TASKS COMPLETED (1):
    ✓ Frank (janitor) finished: Clean kitchen

  📝 WORK POSTS CREATED:
    🎉 Frank posted: "Frank: Office cleanup done..."

  📢 INFO-SPREAD:
    💼 Carol (project_manager) → VERIFY THEN SHARE | "Frank: Office cleanup..."
        └─ 💬 "Great work! Everyone should see this!"
    💼 Eve (designer) → IGNORE | "Frank: Office cleanup..."
```

**Verification:**
```bash
python3 run_live_office.py --ticks 50
# Shows work → posts → spread → reactions

---

### Step 6 — 3D Visualization (Sims-like Office)

**Status:** 🔜 READY TO START

**Goal:** Visualize the office like a **Sims game** — watch agents live their work lives.

**Files to touch:** New file `run_visualization.py` or `agent_office/viz_3d/` (TBD)

---

#### 🎯 Why Visualize? (Current State Analysis)

The simulation is now **richly alive**:

| System | What Happens |
|--------|--------------|
| **Office Work** | Agents pick tasks by job role, work on them, complete them |
| **Products** | Tasks contribute to products (Mobile App, AI Chatbot...). Products advance: Planning → Development → Testing → Ready → Shipped |
| **Info-Spread** | Task completions generate posts. Posts spread through the network |
| **Reactions** | Other agents react based on traits (share/verify/ignore/flag). Skeptics flag suspicious posts; Influencers amplify |
| **Continuous Mode** | `run_continuous_office.py` runs forever with pause/resume. You can watch it for hours |

**The problem:** All of this is hidden in terminal text. You can't *see*:
- Why Alice's post spread to Bob, Carol, David...
- Where Frank (janitor) is vs Alice (developer)
- How Mobile App v2.0 went from 0% → shipped

**Visualization makes the simulation observable.**

---

#### 🏠 "Sims-like" Concept

```
┌─────────────────────────────────────────────────────────────┐
│                    🏢 TECHCORP HQ (Floor Plan)              │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CODING DESK  │  │  TEST LAB    │  │  MEETING RM  │      │
│  │  Alice 💻    │  │  David 🧪    │  │  Carol 👔    │      │
│  │  Bob 💻      │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   KITCHEN    │  │   LOBBY      │  │  DESIGN BAY  │      │
│  │   Frank 🧹   │  │  (coffee ☕)  │  │   Eve 🎨     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  💬 "Auth bug fixed!" — Alice → Bob → Carol → (shared!)    │
│  📦 Mobile App v2.0: ████████████░░░░ 67% (In Development) │
│  🚀 AI Chatbot SHIPPED! 🎉                                  │
└─────────────────────────────────────────────────────────────┘
```

**Key Visual Elements:**

| Element | Visual |
|---------|--------|
| **Agents** | Simple sprites/avatars walking or sitting |
| **Stations** | Desks, labs, kitchen — agents go to their "place" |
| **Tasks** | Progress bar above agent's head, or "working" animation |
| **Posts** | Speech bubbles above agent when they post/comment |
| **Shares** | Lines/arrows between agents when post spreads |
| **Products** | A "project board" showing active products' progress |
| **Shipped** | Celebration animation (confetti, product icon) |

---

#### 📐 Proposed Architecture

```
run_visualization.py (or viz_3d/)
├── FloorPlanRenderer   # Draw office layout (2D isometric or 3D)
├── AgentRenderer       # Draw agents, animate walk/sit/talk
├── ProductRenderer     # Show product progress board
├── PostBubbleRenderer  # Speech bubbles for posts
├── NetworkLineRenderer # Lines showing post spread
└── SimulationBridge    # Read state from Simulation/Office each frame
```

**Rendering Options (in order of complexity):**

1. **Pygame (2D Isometric)** — Classic "top-down office" view
   - Fast to build
   - Grid-based floor plan
   - Simple sprites for agents (walk cycles)
   
2. **Pygame (Top-down 2D)** — Simpler, less fancy
   - Agents as colored circles/icons
   - Floor as a simple layout
   - Good for proof-of-concept

3. **Godot/Unity (Full 3D)** — Maximum polish
   - Real 3D office, animated characters
   - But heavy for a Python project

**Recommendation:** Start with **Pygame isometric** — gives the "Sims" feel without heavy dependencies.

---

#### 🔗 Data Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Simulation     │───▶│  Viz Bridge     │───▶│  Renderer       │
│  (tick loop)    │    │  (reads state)  │    │  (draws frame)  │
│                 │    │                 │    │                 │
│ • agents pos    │    │ • agent coords  │    │ • draw agents   │
│ • tasks         │    │ • task progress │    │ • draw tasks    │
│ • posts         │    │ • post bubbles  │    │ • draw bubbles  │
│ • products      │    │ • product state │    │ • draw products │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

The visualization **reads** from the existing Simulation/Office classes — no changes needed to core code!

---

#### 📋 Implementation Plan (Step 6)

1. **Phase 1: Static Floor Plan**
   - Draw office layout (desks, rooms)
   - Place agents at "home" positions

2. **Phase 2: Agent Movement**
   - Agents walk to task stations based on job role
   - Simple walk animation (frame flip or tiny bobbing)

3. **Phase 3: Task Visualization**
   - Progress bar above working agents
   - Color by task type (coding=blue, testing=green, etc.)

4. **Phase 4: Post Spread**
   - Speech bubble when agent posts
   - Lines/arrows when post spreads to followers

5. **Phase 5: Products**
   - Project board in corner showing active products
   - "Shipped!" celebration animation

6. **Phase 6: Polish**
   - Time-of-day (lighting changes)
   - Sound effects (optional)
   - Speed controls

---

#### 🎬 Example User Experience

> You start `run_visualization.py`. A window opens showing a top-down office.
> 
> - Frank (janitor) walks to the kitchen, cleans it. ✅ Task complete → Post: "Kitchen spotless!"
> - Alice (developer) is at her desk, working on "Fix login bug". Progress: 67%
> - Bob sees Alice's post → 💬 Bubble: "Great work!" → Shares it
> - Line appears: Alice → Bob (post spread)
> - Carol (PM) sees it → 💬 Bubble: "Finally!" → Shares it
> - Line appears: Bob → Carol
> - "Mobile App v2.0" progress bar advances to 45%
> - 10 ticks later: Mobile App v2.0 SHIPS! 🎉 Confetti animation

---

#### ⏸️ Status

**ON HOLD** until user says "go" — but the simulation is ready for it.

*No code changes made. This is a design document for future work.*

---

### Step 7 — DONE: ML Pipeline Awareness

**Status:** ✅ COMPLETED

**What was done:**
- Updated `AgentInteraction` in [data_collector.py](/testbed/agent-office-sim/agent_office/ml/data_collector.py) to include `job_role` field
- Added job role tracking to `DisseminationRecord`:
  - `job_roles_seen`: counts of each job role that viewed the post
  - `job_roles_shared`: counts of each job role that shared the post
  - `job_roles_flagged`: counts of each job role that flagged the post
- Updated `EarlyDisseminationTracker`:
  - `job_role_registry`: maps agent_id to JobRole
  - `register_agent()` now accepts optional `job_role` parameter
  - `record_event()` includes job role in interactions
- Added job role features to `SpreadFeatures` in [feature_extractor.py](/testbed/agent-office-sim/agent_office/ml/feature_extractor.py):
  - Individual counts: `early_developer_shares`, `early_tester_shares`, etc.
  - Ratios: `developer_share_ratio`, `pm_share_ratio`
  - Special metric: `tester_flag_ratio` (testers are good at spotting issues!)
- Updated `extract_spread_features()` to calculate job role features from early interactions
- Updated [pipeline.py](/testbed/agent-office-sim/agent_office/pipeline.py):
  - `create_agents()` now assigns job roles to agents
  - `register_agent()` calls include job roles

**New ML Features (11 additional features):**
```python
# Job role involvement in early spread
early_developer_shares, early_tester_shares, early_pm_shares,
early_janitor_shares, early_designer_shares, early_intern_shares,
early_sales_shares, early_hr_shares,

# Job role ratios
developer_share_ratio,  # Are developers early adopters?
tester_flag_ratio,      # Do testers spot misinformation?
pm_share_ratio          # Do PMs amplify information?
```

**Hypothesis:** Different job roles may have different patterns:
- **Testers** might be better at spotting misinformation (higher flag rates)
- **PMs** might amplify information more (higher share rates)
- **Developers** might be early adopters of technical content

**Verification:**
```bash
python3 run_pipeline.py --simulations 10 --epochs 5
# Dataset will now include job role features for ML training
```

---

## 🎮 Continuous Office Simulation (BONUS)

**File:** `run_continuous_office.py`

A persistent, living office simulation that runs indefinitely until you stop it.

### Features:
- **Product Development:** Agents work on tasks that contribute to products (Mobile App v2.0, AI Chatbot, etc.)
- **Product Lifecycle:** Planning → Development → Testing → Ready → Shipped
- **Live Dashboard:** Real-time view of products, team activity, and events
- **Pause/Resume:** Press 'P' to pause all activity, press again to resume
- **Auto-Generation:** New tasks and products are created automatically
- **Celebration Posts:** When products ship, celebration posts spread through the network

### Controls:
- **P** - Pause/Resume simulation
- **Q** or **Ctrl+C** - Quit

### Run:
```bash
python3 run_continuous_office.py --speed 1.0
```

### Dashboard Shows:
1. **📦 Active Products** - Progress bars showing development status
2. **👥 Team Activity** - What each agent is working on
3. **📰 Recent Events** - Task completions, product advances, shares
4. **📊 Statistics** - Tasks, products, info-spread metrics

---

## 🔒 Constraints

1. **NEVER break the existing info-spread simulation.** It must run identically with or without job roles.
2. `AgentType` and `JobRole` are **orthogonal** — a Skeptic can be a Janitor.
3. `job_role` is **optional** (`None` allowed) for backward compat.
4. Do one step at a time. Test before moving on.

---

## 📝 Notes for Future

- Could add "morale", "energy", "meetings" as office dynamics
- Could simulate time-of-day (morning coffee = more chatting = more shares)
- Could add hierarchy (PM assigns to Dev, not vice versa)
- Could persist office state (save/load)

---

## ✅ Checklist

- [x] Step 1: Structural foundation (JobRole enum, job_role field)
- [x] Step 2: Define Office Tasks (OfficeTask, Office classes, sample tasks)
- [x] Step 3: Job Role Behaviors (preferred task types mapping)
- [x] Step 4: Integrate Office into Simulation Tick (both systems coexist)
- [x] Step 5: Connect Info Spread to Office (task completion → posts → spread → reactions)
- [ ] Step 6: 3D Visualization (Sims-like office) — 📝 **DESIGN READY**, awaiting user "go"
- [x] Step 7: ML Pipeline Awareness (job role features — 11 new features added)

---

## 💬 My Analysis: Current State

After all the work, here's where we stand:

### The Simulation is "Alive"

The Agent Office simulation has become something special:

1. **Agents have identities** — Not just "Agent 3" but "Alice (Developer, Cautious Sharer)" who fixes bugs and posts about it.

2. **Work produces culture** — When Frank cleans the kitchen, he posts "Kitchen spotless!" and Bob shares it. Work generates gossip.

3. **Products give purpose** — Agents aren't just doing random tasks. They're building "Mobile App v2.0" together. When it ships, everyone celebrates.

4. **The network is social** — Posts don't just "spread." Alice tells Bob (who trusts her), Bob tells Carol (who's skeptical), Carol flags it. You can *trace the social graph*.

5. **It's watchable** — `run_continuous_office.py` runs forever. You can leave it running and come back to see what's happened.

### Why 3D Visualization Makes Sense Now

The simulation is **already a game without graphics**. The pieces are there:

| Simulation Element | Visual Equivalent |
|--------------------|-------------------|
| Agent with job_role | Avatar at a desk |
| Task in progress | Progress bar / "working" animation |
| Task complete → post | Speech bubble above agent |
| Post spreads to followers | Lines connecting agents |
| Product advancing | Progress bar on project board |
| Product shipped | Celebration animation |

**Without visualization**, you read text logs. **With visualization**, you *watch* the office drama unfold.

### My Recommendation for 3D Visualization

**Start simple, grow organic:**

1. **Phase 1 (MVP):** Pygame, top-down 2D. Agents as colored dots with labels. Floor as colored rectangles. Just to prove the concept.

2. **Phase 2:** Isometric tiles. Agents have tiny sprites (walk, sit). You can see the "office" look.

3. **Phase 3 (Polish):** Add speech bubbles, product board, time-of-day lighting.

**Why not full 3D?** Because the *logic* is the star. The visualization just makes it observable. Pygame gets you 80% of the "wow" for 10% of the effort.

**Key insight:** The simulation already emits all the events we need. The viz just needs to *read* the state each frame. No core changes required.

---

*This analysis and design plan added without modifying any code.*

---

*Last updated: 2026-03-24 (updated: Steps 2-4 marked DONE)*
*Author: Grok Build Agent (per user request)*
