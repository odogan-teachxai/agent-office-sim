#!/usr/bin/env python3
"""
Simple Scenario - 3 Agents, 1 Post

This demonstrates the core simulation loop in a minimal, traceable way.
"""

from agent_office.agent import Agent, AgentType, create_agent_from_type
from agent_office.post import Post, PostCategory, TruthValue
from agent_office.network import SocialNetwork
from agent_office.simulation import Simulation

# ============================================================
# SETUP: Create 3 agents with different personalities
# ============================================================

print("=" * 60)
print("SIMPLE SCENARIO: 3 Agents, 1 Post")
print("=" * 60)

# Agent A: Immediate Sharer (high gullibility, low skepticism)
alice = create_agent_from_type("agent_a", "Alice", AgentType.IMMEDIATE_SHARER)

# Agent B: Skeptic (low gullibility, high skepticism)  
bob = create_agent_from_type("agent_b", "Bob", AgentType.SKEPTIC)

# Agent C: Cautious Sharer (balanced)
charlie = create_agent_from_type("agent_c", "Charlie", AgentType.CAUTIOUS_SHARER)

print("\n📊 AGENT PROFILES:")
print("-" * 40)
for agent in [alice, bob, charlie]:
    print(f"{agent.name} ({agent.agent_type.value})")
    print(f"  Gullibility: {agent.gullibility:.2f} | Skepticism: {agent.skepticism:.2f}")
    print(f"  Verify Prob: {agent.verify_probability:.2f} | Share Threshold: {agent.share_threshold:.2f}")
    print(f"  Emotional Susc: {agent.emotional_susceptibility:.2f}")
    print()

# ============================================================
# SETUP: Create network connections
# ============================================================

network = SocialNetwork()
network.add_agent(alice)
network.add_agent(bob)
network.add_agent(charlie)

# Network structure: Alice follows Bob, Bob follows Charlie, Charlie follows Alice
# (Circular following so posts can spread)
network.add_connection("agent_a", "agent_b", strength=0.7, trust_level=0.8)  # Alice follows Bob
network.add_connection("agent_b", "agent_c", strength=0.6, trust_level=0.7)  # Bob follows Charlie
network.add_connection("agent_c", "agent_a", strength=0.5, trust_level=0.6)  # Charlie follows Alice

print("🌐 NETWORK CONNECTIONS:")
print("-" * 40)
print("Alice follows Bob (trust=0.8)")
print("Bob follows Charlie (trust=0.7)")
print("Charlie follows Alice (trust=0.6)")
print()

# ============================================================
# SETUP: Create a post
# ============================================================

post = Post(
    subject="SHOCKING Health Discovery!",
    content="Doctors don't want you to know this simple cure!",
    category=PostCategory.HEALTH,
    truth_value=TruthValue.FALSE,  # It's misinformation!
    emotional_intensity=0.9,       # Very emotional
    credibility_score=0.2,         # Low credibility
    source_reliability=0.1         # Unreliable source
)

print("📰 THE POST:")
print("-" * 40)
print(f"Subject: {post.subject}")
print(f"Truth: {post.truth_value.value} | Emotion: {post.emotional_intensity} | Credibility: {post.credibility_score}")
print()

# ============================================================
# SIMULATION: Run with detailed logging
# ============================================================

print("🎬 STARTING SIMULATION")
print("=" * 60)

def on_event(event):
    """Print each event as it happens."""
    print(f"\n[Tick {event.tick}] {event.agent_name} received post from {event.details['from_agent']}")
    print(f"  Behavior: {event.behavior}")
    print(f"  Confidence: {event.details['confidence']:.3f}")
    print(f"  Trust in sender: {event.details['trust_modifier']:.2f}")
    
    if event.behavior in ["share_immediately", "verify_then_share"]:
        print(f"  ➡️  {event.agent_name} SHARED the post!")
    elif event.behavior == "flag_as_suspicious":
        print(f"  🚫 {event.agent_name} FLAGGED the post!")
    else:
        print(f"  ⏸️  {event.agent_name} ignored the post")

# Create simulation with NO delay (we want to see it run fast)
sim = Simulation(network, tick_delay=0, on_event=on_event)

# Alice creates the initial post
print(f"\n📝 INITIAL: Alice creates the post")
sim.add_post(post, alice)
print(f"   Pending shares queued: {len(sim.pending_shares)}")
print(f"   (Alice's followers will receive it)")

# Run the simulation
print("\n" + "-" * 60)
print("RUNNING SIMULATION...")
print("-" * 60)

stats = sim.run(max_ticks=50, stop_when_idle=True, idle_threshold=2)

# ============================================================
# RESULTS
# ============================================================

print("\n" + "=" * 60)
print("SIMULATION COMPLETE")
print("=" * 60)

print(f"\n📈 STATISTICS:")
print(f"  Total ticks: {stats.total_ticks}")
print(f"  Total shares: {stats.total_shares}")
print(f"  Total flags: {stats.total_flags}")
print(f"  False posts shared: {stats.false_posts_shared}")

print(f"\n📊 POST SPREAD:")
print(f"  Reach (unique viewers): {post.reach_count}")
print(f"  Share count: {post.share_count}")
print(f"  Flagged count: {post.flagged_count}")
print(f"  Spread path: {' -> '.join(post.spread_path)}")

print(f"\n👤 AGENT ACTIVITY:")
for agent in [alice, bob, charlie]:
    print(f"  {agent.name}: seen={len(agent.posts_seen)}, shared={len(agent.posts_shared)}, flagged={len(agent.posts_flagged)}")

# ============================================================
# ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("ANALYSIS: Why did each agent behave this way?")
print("=" * 60)

print("""
ALICE (Immediate Sharer):
  - Created the post (didn't evaluate it, just posted)
  - Her followers (Bob) received it
  
BOB (Skeptic):
  - High skepticism + high emotional intensity + low credibility
  - Calculated high suspicion score (emotion × (1-credibility) = 0.72)
  - High verify_probability (0.8-0.95 range)
  - During verification: detected false (high skepticism helps detect falsehoods)
  - Result: Likely FLAGGED or IGNORED
  
CHARLIE (Cautious Sharer):
  - Depends on if Bob shared or not
  - If Bob shared: moderate skepticism, moderate verification
  - May verify and detect false, or may be fooled by emotion
  - Share threshold (0.5-0.7) is higher than Alice's (0.2-0.4)
  - Less likely to share than Alice, more likely than Bob
""")
