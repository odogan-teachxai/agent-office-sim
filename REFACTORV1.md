# REFACTORV1.md — Agent Office Simulation Refactor Summary

> **Scope:** All changes made during the conversation to improve architecture, reduce duplication, enhance readability, and add reproducibility.

---

## 1. Architecture & Runner Cleanup

### 1.1 Duplicated Demo Team Extraction
- **Problem:** Four runner scripts (`run_office.py`, `run_integrated.py`, `run_live_office.py`, `run_continuous_office.py`) each defined an identical 9-agent roster locally.
- **Solution:** Created `agent_office/demo_team.py` with `create_demo_team()` returning the canonical roster.
- **Updated:** All four runners now import and delegate to `create_demo_team()`.
- **Files:** `agent_office/demo_team.py` (new), `run_*.py` (modified).

### 1.2 Export Demo Team from Package
- **Change:** Added `from .demo_team import create_demo_team` and `"create_demo_team"` to `agent_office/__init__.py` `__all__`.
- **File:** `agent_office/__init__.py`.

### 1.3 Shared Simulation Setup Extraction
- **Problem:** Runner scripts duplicated ~40–55 lines of setup (team → Office → tasks → network → Simulation → posts).
- **Solution:** Created `agent_office/demo_setup.py` with `build_demo_simulation()` that constructs the full scaffold.
- **Updated:** `run_office.py`, `run_integrated.py`, `run_live_office.py` now use `build_demo_simulation()`.
- **Files:** `agent_office/demo_setup.py` (new), `run_*.py` (modified).

### 1.4 Orphaned Pygame Apps Removed
- **Deleted:** `run_viz.py` and `run_3d_office.py` — these were standalone pygame front-ends not using `Simulation.tick()`.
- **Rationale:** Not Simulation runners; user gave permission to delete unnecessary files.

### 1.5 Generated File Cleanup
- **Deleted:** `output/` directory (~4.4 MB of JSON/CSV/JSONL logs and datasets).
- **Deleted:** All `__pycache__/` directories and `*.pyc` files.
- **Updated:** `.gitignore` — added `output/` ignore rule under "Project generated outputs" section.

---

## 2. Internal Agent Scoring Refactor (Readability & Constants)

### 2.1 Module-Level Constants in `agent.py`
Added ~40 named constants (no behavior change):

| Category | Constants |
|----------|-----------|
| Scoring Weights | `BASE_SKEPTICISM_WEIGHT`, `EMOTIONAL_MULTIPLIER_BASE/GULLIBILITY_FACTOR`, `EMOTIONAL_IMPACT_COEFFICIENT`, `CREDIBILITY_NEUTRAL_POINT/BONUS_SCALE`, `SOURCE_RELIABILITY_NEUTRAL_POINT/BONUS_SCALE`, `SCORE_NOISE_RANGE` |
| Suspicion Weights | `SUSPICION_EMOTION_CRED_GAP_WEIGHT`, `SUSPICION_SOURCE_UNRELIABILITY_WEIGHT`, `SUSPICION_SKEPTICISM_BASE/SCALE` |
| Category Dicts | `CATEGORY_SUSPICION` (gossip +0.15, science −0.1, etc.), `CATEGORY_PREFERENCES` (per-AgentType bonuses) |
| Eval Thresholds | `SUSPICION_THRESHOLD_VERIFY_BOOST`, `VERIFY_PROBABILITY_BOOST`, `SUSPICION_THRESHOLD_INTUITIVE_REJECTION`, etc. |
| Verification Params | `TRUE_POST_PASS_BASE_PROB`, `FALSE_POST_BASE_DETECTION`, `FALSE_POST_DETECTION_MIN/MAX`, etc. |
| Agent Type Ranges | `AGENT_TYPE_RANGES` — single source of truth for `create_agent_from_type()` |

### 2.2 Helper Function Extracted
- **`_category_name(post)`** — replaces repeated `post.category.value if hasattr(...) else str(...)` pattern (was 2× inline).

### 2.3 Refactored Scoring Methods
- **`_calculate_share_score()`** — all magic floats → named constants; `random.uniform(*SCORE_NOISE_RANGE)`.
- **`_calculate_suspicion_score()`** — uses `CATEGORY_SUSPICION` and `_category_name()`.
- **`_get_category_bonus()`** — reduced from ~30 lines to 5 lines (uses `CATEGORY_PREFERENCES`).
- **`evaluate_post()`** — uses threshold constants; slightly flattened via ternary returns.
- **`_verify_post()`** — all params named; confidence logic clarified.
- **`create_agent_from_type()`** — reduced from ~45 lines to 8 lines using `AGENT_TYPE_RANGES` dict comprehension.

### 2.4 Simulation Constants
- **`DEFAULT_BATCH_SIZE = 5`** in `simulation.py` — replaces inline `5` in `tick()`.

---

## 3. Reproducibility: Seeded RNG

### 3.1 Simulation.random_seed Parameter
- Added `random_seed: Optional[int] = None` to `Simulation.__init__()`.
- **Seeds global RNG in `__init__`** when seed provided — covers all randomness from Simulation creation onward (agent evaluation, office work, tick loop).
- Removed redundant seed in `run()`.

### 3.2 Runner Entry Points Updated
- **`run_simulation()`** in `main.py` — added `random_seed` param, seeds at very start before any random calls.
- **`build_demo_simulation()`** in `demo_setup.py` — added `random_seed` param, seeds at very start.

### 3.3 Correct Usage Pattern
```python
import random
random.seed(42)  # Seed ONCE before creating anything
agents = create_agents(...)
net = create_network(...)
posts = create_posts(...)
sim = Simulation(network=net, random_seed=42)
sim.run()
```
- When `random_seed=None` (default): no seeding → **behavior unchanged**.

---

## 4. Logging Refactor

### 4.1 Stdlib logging in `logger.py`
- Replaced all `print(...)` calls with `self._logger.info(...)` using stdlib `logging.Logger`.
- Preserved:
  - `Colors` class (ANSI codes)
  - `SimulationLogger` public API unchanged
  - JSON persistence (`_write_to_file()`) unchanged
- Added module-level `logger = logging.getLogger("agent_office")`.

---

## 5. Bug Fixes

### 5.1 `run_office.py` Unpacking Error
- **Error:** `ValueError: too many values to unpack (expected 2)` at `for agent, task in office_completions`.
- **Root Cause:** `Office.tick()` returns 3-tuples `(agent, task, product)` but code expected 2.
- **Fix:** Changed to `for agent, task, _ in office_completions`.
- **File:** `run_office.py:125`.

### 5.2 Post IDs Deterministic
- **Problem:** `Post.id` used `uuid.uuid4()` — not affected by `random.seed()`.
- **Fix:** Changed to `''.join(random.choices('0123456789abcdef', k=8))` — uses seeded random.
- **File:** `agent_office/post.py:60`.

### 5.3 Run.py Dead Variable Removal (earlier)
- Removed unused `report =` assignment in `run.py`.

---

## 6. Files Changed Summary

| File | Changes |
|------|---------|
| `agent_office/agent.py` | ~40 constants, `_category_name()` helper, refactored scoring methods, `AGENT_TYPE_RANGES` |
| `agent_office/simulation.py` | `random_seed` param + seed in `__init__`, `DEFAULT_BATCH_SIZE` |
| `agent_office/logger.py` | stdlib logging internal replacement |
| `agent_office/post.py` | Post ID via seeded random |
| `agent_office/main.py` | `random_seed` in `run_simulation()`, `Optional` import |
| `agent_office/demo_setup.py` | `random_seed` in `build_demo_simulation()` |
| `agent_office/demo_team.py` | (earlier) Created |
| `agent_office/__init__.py` | (earlier) Export `create_demo_team` |
| `run_office.py` | Fixed 3-tuple unpacking |
| `run_integrated.py`, `run_live_office.py` | (earlier) Use `build_demo_simulation()` |
| `run.py` | (earlier) Dead variable removal |
| `.gitignore` | (earlier) `output/` rule |

---

## 7. Backward Compatibility

- All changes are **non-breaking** when using defaults (`random_seed=None`, etc.).
- Public APIs unchanged (method signatures, return types, report structure).
- Existing scripts work identically without seed arguments.

---

## 8. Test Commands

```bash
# Reproducible run
python3 -c "
import random
from agent_office.main import run_simulation
random.seed(42)
r1 = run_simulation(num_agents=7, num_posts=4, max_ticks=50, verbose=False, random_seed=42)
random.seed(42)
r2 = run_simulation(num_agents=7, num_posts=4, max_ticks=50, verbose=False, random_seed=42)
print('Reproducible:', r1['simulation_stats'] == r2['simulation_stats'])
"

# Basic run (unchanged behavior)
python3 run.py --agents 5 --posts 2
python3 run_office.py --ticks 5
python3 run_integrated.py --ticks 10
```

---

*Documented: 2026-03-26*
