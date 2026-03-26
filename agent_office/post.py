"""
Post module - Defines post characteristics and content in the social network.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid
import random


class PostCategory(Enum):
    """Categories of posts in the social network."""
    NEWS = "news"
    GOSSIP = "gossip"
    ENTERTAINMENT = "entertainment"
    POLITICS = "politics"
    SCIENCE = "science"
    HEALTH = "health"


class TruthValue(Enum):
    """Truth value of a post's content."""
    TRUE = "true"
    FALSE = "false"
    MIXED = "mixed"          # Partially true, partially false
    UNVERIFIED = "unverified"  # Cannot be determined
    
    def is_true(self) -> bool:
        """Check if the post is definitively true."""
        return self == TruthValue.TRUE
    
    def is_false(self) -> bool:
        """Check if the post is definitively false."""
        return self == TruthValue.FALSE
    
    def is_misleading(self) -> bool:
        """Check if the post is false or mixed (potentially misleading)."""
        return self in [TruthValue.FALSE, TruthValue.MIXED]


@dataclass
class Post:
    """
    Represents a post in the social network.
    
    Attributes:
        id: Unique identifier for the post
        subject: Subject/headline of the post
        content: Full content of the post
        category: Category of the post
        truth_value: Whether the information is true, false, etc.
        emotional_intensity: How emotionally charged the content is (0.0 - 1.0)
        credibility_score: How credible the post appears (0.0 - 1.0)
        source_reliability: How reliable the original source is (0.0 - 1.0)
        created_at: When the post was created
        author_id: ID of the agent who created the post
    """
    id: str = field(default_factory=lambda: ''.join(random.choices('0123456789abcdef', k=8)))
    subject: str = ""
    content: str = ""
    category: PostCategory = PostCategory.NEWS
    truth_value: TruthValue = TruthValue.UNVERIFIED
    emotional_intensity: float = 0.5
    credibility_score: float = 0.5
    source_reliability: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    author_id: Optional[str] = None
    
    # Tracking attributes
    share_count: int = 0
    reach_count: int = 0  # Unique people who have seen it
    flagged_count: int = 0
    spread_path: list = field(default_factory=list)  # List of agent IDs who shared
    
    def __post_init__(self):
        """Validate and clamp values after initialization."""
        self.emotional_intensity = max(0.0, min(1.0, self.emotional_intensity))
        self.credibility_score = max(0.0, min(1.0, self.credibility_score))
        self.source_reliability = max(0.0, min(1.0, self.source_reliability))
    
    def record_share(self, agent_id: str):
        """Record that an agent shared this post."""
        self.share_count += 1
        if agent_id not in self.spread_path:
            self.spread_path.append(agent_id)
    
    def record_view(self):
        """Record that someone viewed this post."""
        self.reach_count += 1
    
    def record_flag(self):
        """Record that someone flagged this post as suspicious."""
        self.flagged_count += 1
    
    def get_virality_score(self) -> float:
        """Calculate how viral this post has become."""
        if self.share_count == 0:
            return 0.0
        # Virality = shares per view ratio, weighted by reach
        return min(1.0, (self.share_count / max(1, self.reach_count)) * (1 + self.reach_count / 100))
    
    def get_deception_score(self) -> float:
        """Calculate how deceptive this post is based on flags vs shares."""
        if self.share_count == 0:
            return 0.0
        return self.flagged_count / max(1, self.share_count + self.flagged_count)
    
    def get_stats(self) -> dict:
        """Get statistics about this post's spread."""
        return {
            "id": self.id,
            "subject": self.subject,
            "category": self.category.value,
            "truth_value": self.truth_value.value,
            "emotional_intensity": self.emotional_intensity,
            "share_count": self.share_count,
            "reach_count": self.reach_count,
            "flagged_count": self.flagged_count,
            "virality_score": self.get_virality_score(),
            "deception_score": self.get_deception_score(),
            "spread_depth": len(self.spread_path)
        }
    
    def __repr__(self) -> str:
        return f"Post({self.subject[:30]}..., truth={self.truth_value.value}, shares={self.share_count})"


def create_sample_posts() -> list[Post]:
    """Create a variety of sample posts for simulation."""
    posts = [
        # True posts
        Post(
            subject="New Study Shows Benefits of Regular Exercise",
            content="A comprehensive study from Harvard Medical School confirms that 30 minutes of daily exercise significantly improves cardiovascular health.",
            category=PostCategory.HEALTH,
            truth_value=TruthValue.TRUE,
            emotional_intensity=0.3,
            credibility_score=0.9,
            source_reliability=0.95
        ),
        Post(
            subject="Local Library Announces Summer Reading Program",
            content="The city library will host a free summer reading program for children ages 5-12 starting next month.",
            category=PostCategory.NEWS,
            truth_value=TruthValue.TRUE,
            emotional_intensity=0.2,
            credibility_score=0.85,
            source_reliability=0.9
        ),
        Post(
            subject="Scientists Discover New Species in Deep Ocean",
            content="Marine biologists have identified three previously unknown species during a deep-sea expedition.",
            category=PostCategory.SCIENCE,
            truth_value=TruthValue.TRUE,
            emotional_intensity=0.5,
            credibility_score=0.85,
            source_reliability=0.9
        ),
        
        # False posts
        Post(
            subject="SHOCKING: Celebrities Secretly Running Government",
            content="Insiders reveal that famous actors have been secretly controlling government decisions for years!",
            category=PostCategory.GOSSIP,
            truth_value=TruthValue.FALSE,
            emotional_intensity=0.9,
            credibility_score=0.2,
            source_reliability=0.1
        ),
        Post(
            subject="Miracle Cure Found - Doctors Don't Want You to Know",
            content="A simple household ingredient can cure all diseases! Medical industry hiding the truth!",
            category=PostCategory.HEALTH,
            truth_value=TruthValue.FALSE,
            emotional_intensity=0.95,
            credibility_score=0.1,
            source_reliability=0.05
        ),
        Post(
            subject="Breaking: Alien Contact Confirmed by Government",
            content="Government officials finally admit they've been in contact with extraterrestrial beings since 1950.",
            category=PostCategory.NEWS,
            truth_value=TruthValue.FALSE,
            emotional_intensity=0.85,
            credibility_score=0.15,
            source_reliability=0.1
        ),
        
        # Mixed truth posts
        Post(
            subject="Climate Change: What They're Not Telling You",
            content="While climate change is real, some activists exaggerate the timeline for dramatic effect.",
            category=PostCategory.POLITICS,
            truth_value=TruthValue.MIXED,
            emotional_intensity=0.7,
            credibility_score=0.5,
            source_reliability=0.4
        ),
        Post(
            subject="New Technology Promises to Change Everything",
            content="AI advancement will transform industries, but claims of human replacement are overstated.",
            category=PostCategory.SCIENCE,
            truth_value=TruthValue.MIXED,
            emotional_intensity=0.6,
            credibility_score=0.6,
            source_reliability=0.5
        ),
        
        # Entertainment posts (truth less relevant)
        Post(
            subject="10 Movies That Will Make You Cry",
            content="A curated list of emotionally powerful films that have touched audiences worldwide.",
            category=PostCategory.ENTERTAINMENT,
            truth_value=TruthValue.TRUE,
            emotional_intensity=0.5,
            credibility_score=0.7,
            source_reliability=0.6
        ),
        Post(
            subject="Celebrity Couple Spotted at Local Restaurant",
            content="Rumors spread about famous actors seen dining together, sparking relationship speculation.",
            category=PostCategory.GOSSIP,
            truth_value=TruthValue.UNVERIFIED,
            emotional_intensity=0.6,
            credibility_score=0.3,
            source_reliability=0.2
        ),
    ]
    
    return posts
