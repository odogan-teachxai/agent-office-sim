"""
Agent module - Defines user characteristics and behaviors in the social network.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import random


# =============================================================================
# Module-Level Constants
# =============================================================================

# --- Scoring Weights (used in _calculate_share_score) ---
BASE_SKEPTICISM_WEIGHT = 0.3
EMOTIONAL_MULTIPLIER_BASE = 1.0
EMOTIONAL_MULTIPLIER_GULLIBILITY_FACTOR = 0.5
EMOTIONAL_IMPACT_COEFFICIENT = 0.3
CREDIBILITY_NEUTRAL_POINT = 0.5
CREDIBILITY_BONUS_SCALE = 0.2
SOURCE_RELIABILITY_NEUTRAL_POINT = 0.5
SOURCE_RELIABILITY_BONUS_SCALE = 0.1
SCORE_NOISE_RANGE = (-0.1, 0.1)

# --- Suspicion Weights (used in _calculate_suspicion_score) ---
SUSPICION_EMOTION_CRED_GAP_WEIGHT = 0.4
SUSPICION_SOURCE_UNRELIABILITY_WEIGHT = 0.3
SUSPICION_SKEPTICISM_BASE = 0.5
SUSPICION_SKEPTICISM_SCALE = 0.5

# --- Category Suspicion Adjustments ---
CATEGORY_SUSPICION = {
    "gossip": 0.15,
    "politics": 0.05,
    "health": 0.0,
    "news": -0.05,
    "science": -0.1,
    "entertainment": 0.0,
}

# --- Evaluation Thresholds (used in evaluate_post) ---
SUSPICION_THRESHOLD_VERIFY_BOOST = 0.5
VERIFY_PROBABILITY_BOOST = 0.2
SUSPICION_THRESHOLD_INTUITIVE_REJECTION = 0.7
SKEPTICISM_THRESHOLD_INTUITIVE_REJECTION = 0.5
INTUITIVE_REJECTION_SKEPTICISM_FACTOR = 0.5

# --- Verification Parameters (used in _verify_post) ---
TRUE_POST_PASS_BASE_PROB = 0.75
TRUE_POST_SKEPTICISM_BONUS = 0.2
TRUE_POST_CONFIDENCE_BASE = 0.7
FALSE_POST_BASE_DETECTION = 0.6
FALSE_POST_CREDIBILITY_ADJUSTMENT = 0.2
FALSE_POST_EMOTION_MASK_FACTOR = 0.3
FALSE_POST_DETECTION_MIN = 0.1
FALSE_POST_DETECTION_MAX = 0.9
FALSE_POST_CONFIDENCE_DETECTED = 0.3
FALSE_POST_CONFIDENCE_UNDETECTED = 0.2
UNCERTAIN_REJECT_BASE_PROB = 0.3
UNCERTAIN_REJECT_SKEPTICISM_FACTOR = 0.4
UNCERTAIN_CONFIDENCE_BASE = 0.4

# =============================================================================
# Helper Functions
# =============================================================================

def _category_name(post: 'Post') -> str:
    """
    Extract the category name string from a post's category field.
    
    Handles both PostCategory enum and plain string values gracefully.
    """
    if hasattr(post.category, 'value'):
        return post.category.value
    return str(post.category)


# =============================================================================
# Enums
# =============================================================================

class AgentType(Enum):
    """Types of agents based on their sharing behavior."""
    IMMEDIATE_SHARER = "immediate_sharer"      # Shares without thinking
    CAUTIOUS_SHARER = "cautious_sharer"        # Verifies before sharing
    SKEPTIC = "skeptic"                         # Rarely shares, high verification
    INFLUENCER = "influencer"                   # High influence, moderate sharing
    LURKER = "lurker"                           # Reads but rarely shares


class JobRole(Enum):
    """Office job roles for agents (orthogonal to AgentType sharing behavior)."""
    DEVELOPER = "developer"           # Writes code, fixes bugs
    PROJECT_MANAGER = "project_manager"  # Plans, coordinates, assigns work
    TESTER = "tester"                 # Tests code, reports issues
    JANITOR = "janitor"               # Maintains office, cleans up
    DESIGNER = "designer"             # Designs UI/UX, creates assets
    INTERN = "intern"                 # Learning, assisting others
    SALES_REP = "sales_rep"           # Sells products, talks to clients
    HR_MANAGER = "hr_manager"         # Handles hiring, culture, conflicts


class AgentBehavior(Enum):
    """Possible behaviors an agent can exhibit when encountering a post."""
    SHARE_IMMEDIATELY = "share_immediately"
    VERIFY_THEN_SHARE = "verify_then_share"
    VERIFY_THEN_IGNORE = "verify_then_ignore"
    IGNORE = "ignore"
    FLAG_AS_SUSPICIOUS = "flag_as_suspicious"


# --- Category Preferences by Agent Type ---
CATEGORY_PREFERENCES = {
    AgentType.IMMEDIATE_SHARER: {
        "news": 0.1, "gossip": 0.2, "entertainment": 0.15,
        "politics": 0.1, "science": 0.0, "health": 0.05
    },
    AgentType.CAUTIOUS_SHARER: {
        "news": 0.1, "gossip": -0.1, "entertainment": 0.05,
        "politics": 0.0, "science": 0.2, "health": 0.15
    },
    AgentType.SKEPTIC: {
        "news": 0.05, "gossip": -0.2, "entertainment": 0.0,
        "politics": -0.1, "science": 0.15, "health": 0.1
    },
    AgentType.INFLUENCER: {
        "news": 0.15, "gossip": 0.1, "entertainment": 0.2,
        "politics": 0.1, "science": 0.1, "health": 0.1
    },
    AgentType.LURKER: {
        "news": 0.0, "gossip": 0.0, "entertainment": 0.0,
        "politics": 0.0, "science": 0.0, "health": 0.0
    },
}

# --- Agent Type Parameter Ranges ---
AGENT_TYPE_RANGES = {
    AgentType.IMMEDIATE_SHARER: {
        "gullibility": (0.7, 0.95),
        "skepticism": (0.1, 0.3),
        "share_threshold": (0.2, 0.4),
        "verify_probability": (0.1, 0.3),
        "emotional_susceptibility": (0.7, 0.95),
        "influence": (0.3, 0.6),
    },
    AgentType.CAUTIOUS_SHARER: {
        "gullibility": (0.3, 0.5),
        "skepticism": (0.5, 0.7),
        "share_threshold": (0.5, 0.7),
        "verify_probability": (0.6, 0.85),
        "emotional_susceptibility": (0.3, 0.5),
        "influence": (0.4, 0.7),
    },
    AgentType.SKEPTIC: {
        "gullibility": (0.1, 0.3),
        "skepticism": (0.8, 0.95),
        "share_threshold": (0.7, 0.9),
        "verify_probability": (0.8, 0.95),
        "emotional_susceptibility": (0.1, 0.3),
        "influence": (0.2, 0.5),
    },
    AgentType.INFLUENCER: {
        "gullibility": (0.4, 0.6),
        "skepticism": (0.3, 0.5),
        "share_threshold": (0.4, 0.6),
        "verify_probability": (0.4, 0.6),
        "emotional_susceptibility": (0.5, 0.7),
        "influence": (0.8, 0.98),
    },
    AgentType.LURKER: {
        "gullibility": (0.3, 0.6),
        "skepticism": (0.4, 0.6),
        "share_threshold": (0.85, 0.95),
        "verify_probability": (0.5, 0.7),
        "emotional_susceptibility": (0.2, 0.4),
        "influence": (0.1, 0.3),
    },
}


@dataclass
class Agent:
    """
    Represents a user in the social network.
    
    Attributes:
        id: Unique identifier for the agent
        name: Display name of the agent
        agent_type: Behavioral type of the agent (info-sharing behavior)
        job_role: Office job role (developer, PM, tester, etc.) - orthogonal to agent_type
        gullibility: How easily they believe information (0.0 - 1.0)
        skepticism: How likely they are to question information (0.0 - 1.0)
        influence: How much influence they have in the network (0.0 - 1.0)
        share_threshold: Minimum score needed for them to share (0.0 - 1.0)
        verify_probability: Probability they will verify before sharing (0.0 - 1.0)
        emotional_susceptibility: How much emotional content affects them (0.0 - 1.0)
        
        # Office work attributes (for future office simulation)
        current_task: Optional[str] = None  # What they're currently working on
        productivity: float = 0.5  # How efficiently they work (0.0 - 1.0)
    """
    id: str
    name: str
    agent_type: AgentType
    job_role: Optional[JobRole] = None  # Orthogonal to agent_type!
    gullibility: float = 0.5
    skepticism: float = 0.5
    influence: float = 0.5
    share_threshold: float = 0.5
    verify_probability: float = 0.5
    emotional_susceptibility: float = 0.5
    
    # Tracking attributes (info spread)
    posts_seen: list = field(default_factory=list)
    posts_shared: list = field(default_factory=list)
    posts_flagged: list = field(default_factory=list)
    total_shares_received: int = 0
    
    # Office work attributes (placeholder for future)
    current_task: Optional[str] = None
    productivity: float = 0.5
    
    def __post_init__(self):
        """Validate and clamp values after initialization."""
        self.gullibility = max(0.0, min(1.0, self.gullibility))
        self.skepticism = max(0.0, min(1.0, self.skepticism))
        self.influence = max(0.0, min(1.0, self.influence))
        self.share_threshold = max(0.0, min(1.0, self.share_threshold))
        self.verify_probability = max(0.0, min(1.0, self.verify_probability))
        self.emotional_susceptibility = max(0.0, min(1.0, self.emotional_susceptibility))
    
    def evaluate_post(self, post: 'Post') -> tuple[AgentBehavior, float]:
        """
        Evaluate a post and decide what behavior to exhibit.
        
        This method implements nuanced behavior differences between how agents
        react to misinformation vs accurate information:
        
        MISINFORMATION PATTERNS:
        - Higher emotional intensity triggers more immediate shares from gullible agents
        - Skeptics are more likely to flag posts with low credibility scores
        - Cautious sharers verify more often when credibility is low
        - Trust in source affects sharing decisions
        
        ACCURATE INFORMATION PATTERNS:
        - Lower emotional intensity leads to more thoughtful sharing
        - Higher credibility leads to faster verification approval
        - Skeptics still verify but are less likely to flag
        
        Returns:
            Tuple of (behavior, confidence_score)
        """
        share_score = self._calculate_share_score(post)
        suspicion_score = self._calculate_suspicion_score(post)
        
        # Suspicious content triggers more verification for cautious/skeptic types
        verify_prob = self.verify_probability
        if suspicion_score > SUSPICION_THRESHOLD_VERIFY_BOOST and self.agent_type in [AgentType.CAUTIOUS_SHARER, AgentType.SKEPTIC]:
            verify_prob = min(1.0, verify_prob + VERIFY_PROBABILITY_BOOST)
        
        if random.random() < verify_prob:
            # Verification path
            verification_result = self._verify_post(post)
            
            if verification_result["passed"]:
                behavior = AgentBehavior.VERIFY_THEN_SHARE if share_score >= self.share_threshold else AgentBehavior.VERIFY_THEN_IGNORE
                return behavior, share_score
            else:
                # Failed verification: maybe flag based on suspicion + skepticism
                flag_probability = self.skepticism * (0.5 + suspicion_score * 0.5)
                if random.random() < flag_probability:
                    return AgentBehavior.FLAG_AS_SUSPICIOUS, suspicion_score
                return AgentBehavior.VERIFY_THEN_IGNORE, suspicion_score
        else:
            # Immediate decision (no verification)
            # High suspicion + skepticism can trigger intuitive rejection
            if suspicion_score > SUSPICION_THRESHOLD_INTUITIVE_REJECTION and self.skepticism > SKEPTICISM_THRESHOLD_INTUITIVE_REJECTION:
                if random.random() < self.skepticism * INTUITIVE_REJECTION_SKEPTICISM_FACTOR:
                    return AgentBehavior.IGNORE, share_score
            
            behavior = AgentBehavior.SHARE_IMMEDIATELY if share_score >= self.share_threshold else AgentBehavior.IGNORE
            return behavior, share_score
    
    def _calculate_share_score(self, post: 'Post') -> float:
        """
        Calculate the likelihood of sharing a post.
        
        This is influenced by:
        - Agent's gullibility vs skepticism balance
        - Emotional intensity of the post
        - Source credibility (for cautious types)
        - Category preferences
        """
        # Base score from gullibility vs skepticism
        base_score = self.gullibility - (self.skepticism * BASE_SKEPTICISM_WEIGHT)
        
        # Emotional content impact - stronger for gullible agents
        emotional_multiplier = EMOTIONAL_MULTIPLIER_BASE + (self.gullibility * EMOTIONAL_MULTIPLIER_GULLIBILITY_FACTOR)
        emotional_impact = post.emotional_intensity * self.emotional_susceptibility * EMOTIONAL_IMPACT_COEFFICIENT * emotional_multiplier
        
        # Credibility consideration (cautious types are more sensitive to this)
        credibility_bonus = 0.0
        if self.agent_type in [AgentType.CAUTIOUS_SHARER, AgentType.SKEPTIC]:
            credibility_bonus = (post.credibility_score - CREDIBILITY_NEUTRAL_POINT) * CREDIBILITY_BONUS_SCALE
        
        # Source reliability consideration
        source_bonus = (post.source_reliability - SOURCE_RELIABILITY_NEUTRAL_POINT) * SOURCE_RELIABILITY_BONUS_SCALE
        
        # Category alignment (some agents prefer certain categories)
        category_bonus = self._get_category_bonus(post)
        
        # Combine scores
        final_score = base_score + emotional_impact + credibility_bonus + source_bonus + category_bonus
        
        # Add some randomness (human unpredictability)
        noise = random.uniform(*SCORE_NOISE_RANGE)
        final_score += noise
        
        return max(0.0, min(1.0, final_score))
    
    def _calculate_suspicion_score(self, post: 'Post') -> float:
        """
        Calculate how suspicious a post appears to this agent.
        
        Higher scores indicate more red flags for misinformation:
        - High emotional intensity + low credibility = suspicious
        - Low source reliability = suspicious
        - Category-specific suspicion (e.g., gossip often less credible)
        """
        suspicion = 0.0
        
        # Emotional intensity vs credibility mismatch
        # High emotion with low credibility is a classic misinformation signal
        emotion_credibility_gap = post.emotional_intensity * (1 - post.credibility_score)
        suspicion += emotion_credibility_gap * SUSPICION_EMOTION_CRED_GAP_WEIGHT
        
        # Low source reliability contributes to suspicion
        suspicion += (1 - post.source_reliability) * SUSPICION_SOURCE_UNRELIABILITY_WEIGHT
        
        # Category-based suspicion adjustment (using module-level constant)
        category_name = _category_name(post)
        suspicion += CATEGORY_SUSPICION.get(category_name, 0.0)
        
        # Agent's skepticism amplifies their suspicion detection
        suspicion *= (SUSPICION_SKEPTICISM_BASE + self.skepticism * SUSPICION_SKEPTICISM_SCALE)
        
        return max(0.0, min(1.0, suspicion))
    
    def _get_category_bonus(self, post: 'Post') -> float:
        """Get bonus score based on post category and agent type (using module-level constant)."""
        category_name = _category_name(post)
        preferences = CATEGORY_PREFERENCES.get(self.agent_type, {})
        return preferences.get(category_name, 0.0)
    
    def _verify_post(self, post: 'Post') -> dict:
        """
        Attempt to verify the truthfulness of a post.
        
        Returns a dictionary with:
        - passed: Whether the post passed verification
        - detected_false: Whether the agent detected the post as false
        - confidence_in_verification: How confident the agent is in their verification
        
        Higher skepticism = better at detecting false information.
        Higher gullibility = more likely to accept false information as true.
        """
        result = {
            "passed": False,
            "detected_false": False,
            "confidence_in_verification": 0.5
        }
        
        if post.truth_value.is_true():
            # True posts are more likely to pass verification
            # Even skeptics will generally approve true content
            pass_probability = TRUE_POST_PASS_BASE_PROB + self.skepticism * TRUE_POST_SKEPTICISM_BONUS
            result["passed"] = random.random() < pass_probability
            result["confidence_in_verification"] = TRUE_POST_CONFIDENCE_BASE + random.uniform(0, 0.2)
            result["detected_false"] = False
            
        elif post.truth_value.is_false():
            # False posts - skepticism helps detect them
            # Detection chance is based on skepticism and post's credibility appearance
            base_detection = self.skepticism * FALSE_POST_BASE_DETECTION
            
            # Low credibility posts are easier to detect as false
            credibility_adjustment = (1 - post.credibility_score) * FALSE_POST_CREDIBILITY_ADJUSTMENT
            
            # High emotion can mask falsehoods for gullible agents
            emotion_mask = post.emotional_intensity * self.gullibility * FALSE_POST_EMOTION_MASK_FACTOR
            
            detection_chance = base_detection + credibility_adjustment - emotion_mask
            detection_chance = max(FALSE_POST_DETECTION_MIN, min(FALSE_POST_DETECTION_MAX, detection_chance))
            
            detected = random.random() < detection_chance
            result["detected_false"] = detected
            result["passed"] = not detected  # Pass if NOT detected as false
            
            # Confidence: higher if detected, lower if missed
            if detected:
                result["confidence_in_verification"] = FALSE_POST_CONFIDENCE_DETECTED + detection_chance * 0.3
            else:
                result["confidence_in_verification"] = FALSE_POST_CONFIDENCE_UNDETECTED
            
        else:
            # Mixed or unverified posts - uncertain outcome
            # Skeptics tend to reject uncertain content
            reject_probability = UNCERTAIN_REJECT_BASE_PROB + self.skepticism * UNCERTAIN_REJECT_SKEPTICISM_FACTOR
            result["passed"] = random.random() > reject_probability
            result["detected_false"] = False
            result["confidence_in_verification"] = UNCERTAIN_CONFIDENCE_BASE + random.uniform(0, 0.2)
        
        return result
    
    def record_post_seen(self, post_id: str):
        """Record that the agent has seen a post."""
        if post_id not in self.posts_seen:
            self.posts_seen.append(post_id)
    
    def record_post_shared(self, post_id: str):
        """Record that the agent shared a post."""
        if post_id not in self.posts_shared:
            self.posts_shared.append(post_id)
    
    def record_post_flagged(self, post_id: str):
        """Record that the agent flagged a post as suspicious."""
        if post_id not in self.posts_flagged:
            self.posts_flagged.append(post_id)
    
    def has_seen_post(self, post_id: str) -> bool:
        """Check if agent has already seen a post."""
        return post_id in self.posts_seen
    
    def get_stats(self) -> dict:
        """Get statistics about this agent's activity."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type.value,
            "job_role": self.job_role.value if self.job_role else None,
            "influence": self.influence,
            "posts_seen": len(self.posts_seen),
            "posts_shared": len(self.posts_shared),
            "posts_flagged": len(self.posts_flagged),
            "share_rate": len(self.posts_shared) / max(1, len(self.posts_seen)),
            "total_shares_received": self.total_shares_received,
            "current_task": self.current_task
        }
    
    def __repr__(self) -> str:
        job_info = f", job={self.job_role.value}" if self.job_role else ""
        return f"Agent({self.name}, type={self.agent_type.value}{job_info}, influence={self.influence:.2f})"


def create_agent_from_type(
    agent_id: str,
    name: str,
    agent_type: AgentType,
    job_role: Optional[JobRole] = None
) -> Agent:
    """
    Factory function to create agents with type-appropriate characteristics.
    
    Args:
        agent_id: Unique identifier
        name: Display name
        agent_type: Info-sharing behavior type (IMMEDIATE_SHARER, SKEPTIC, etc.)
        job_role: Office job role (DEVELOPER, PROJECT_MANAGER, etc.) - optional
    
    Returns:
        Configured Agent instance
    """
    # Sample parameters from type-specific ranges (using module-level constant)
    ranges = AGENT_TYPE_RANGES.get(agent_type, AGENT_TYPE_RANGES[AgentType.CAUTIOUS_SHARER])
    config = {param: random.uniform(low, high) for param, (low, high) in ranges.items()}
    
    return Agent(
        id=agent_id,
        name=name,
        agent_type=agent_type,
        job_role=job_role,  # Can be None
        **config
    )
