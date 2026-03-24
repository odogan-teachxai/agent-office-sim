"""
Feature Extractor Module - Extracts ML-ready features from dissemination records.

This module transforms raw simulation data into structured features suitable for
machine learning models. Features are designed to capture patterns that differentiate
misinformation from accurate information.
"""

from dataclasses import dataclass, field
from typing import Optional
import math

from ..agent import JobRole


@dataclass
class PostFeatures:
    """Features derived from post characteristics."""
    # Categorical (one-hot encoded later)
    category_news: int = 0
    category_gossip: int = 0
    category_entertainment: int = 0
    category_politics: int = 0
    category_science: int = 0
    category_health: int = 0
    
    # Numerical
    emotional_intensity: float = 0.0
    credibility_score: float = 0.0
    source_reliability: float = 0.0
    
    # Derived
    emotional_credibility_gap: float = 0.0  # High emotion + low credibility = suspicious
    sensationalism_score: float = 0.0  # High emotion + low source reliability
    
    def to_list(self) -> list[float]:
        """Convert to feature vector."""
        return [
            self.category_news,
            self.category_gossip,
            self.category_entertainment,
            self.category_politics,
            self.category_science,
            self.category_health,
            self.emotional_intensity,
            self.credibility_score,
            self.source_reliability,
            self.emotional_credibility_gap,
            self.sensationalism_score
        ]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "category_news": self.category_news,
            "category_gossip": self.category_gossip,
            "category_entertainment": self.category_entertainment,
            "category_politics": self.category_politics,
            "category_science": self.category_science,
            "category_health": self.category_health,
            "emotional_intensity": self.emotional_intensity,
            "credibility_score": self.credibility_score,
            "source_reliability": self.source_reliability,
            "emotional_credibility_gap": self.emotional_credibility_gap,
            "sensationalism_score": self.sensationalism_score
        }


@dataclass
class SpreadFeatures:
    """Features derived from early dissemination patterns."""
    # Early reach metrics
    early_reach: int = 0
    early_shares: int = 0
    early_flags: int = 0
    early_ignores: int = 0
    early_verifications: int = 0
    
    # Rates
    early_share_rate: float = 0.0
    early_flag_rate: float = 0.0
    early_ignore_rate: float = 0.0
    early_verification_rate: float = 0.0
    
    # Velocity and acceleration
    early_velocity: float = 0.0  # shares per tick
    share_acceleration: float = 0.0  # change in velocity
    
    # Confidence metrics
    avg_early_confidence: float = 0.0
    confidence_variance: float = 0.0
    
    # Agent type involvement (early sharers)
    early_immediate_sharers: int = 0
    early_cautious_sharers: int = 0
    early_skeptics: int = 0
    early_influencers: int = 0
    early_lurkers: int = 0
    
    # Agent type ratios in early spread
    skeptic_share_ratio: float = 0.0  # skeptics sharing / total shares
    immediate_sharer_ratio: float = 0.0
    
    # Job role involvement in early spread (NEW for office simulation)
    early_developer_shares: int = 0
    early_tester_shares: int = 0
    early_pm_shares: int = 0
    early_janitor_shares: int = 0
    early_designer_shares: int = 0
    early_intern_shares: int = 0
    early_sales_shares: int = 0
    early_hr_shares: int = 0
    
    # Job role ratios (NEW)
    developer_share_ratio: float = 0.0
    tester_flag_ratio: float = 0.0  # Testers are good at spotting issues
    pm_share_ratio: float = 0.0  # PMs amplify information
    
    # Timing
    first_share_tick: Optional[int] = None
    first_flag_tick: Optional[int] = None
    time_to_first_flag: Optional[int] = None  # ticks from first share to first flag
    
    # Behavioral patterns
    immediate_share_ratio: float = 0.0  # share_immediately / total shares
    verified_share_ratio: float = 0.0  # verify_then_share / total shares
    
    # Network effects
    avg_trust_modifier: float = 0.0
    high_trust_shares: int = 0  # shares from high trust connections
    
    def to_list(self) -> list[float]:
        """Convert to feature vector."""
        return [
            self.early_reach,
            self.early_shares,
            self.early_flags,
            self.early_ignores,
            self.early_verifications,
            self.early_share_rate,
            self.early_flag_rate,
            self.early_ignore_rate,
            self.early_verification_rate,
            self.early_velocity,
            self.share_acceleration,
            self.avg_early_confidence,
            self.confidence_variance,
            self.early_immediate_sharers,
            self.early_cautious_sharers,
            self.early_skeptics,
            self.early_influencers,
            self.early_lurkers,
            self.skeptic_share_ratio,
            self.immediate_sharer_ratio,
            # Job role features (NEW)
            self.early_developer_shares,
            self.early_tester_shares,
            self.early_pm_shares,
            self.early_janitor_shares,
            self.early_designer_shares,
            self.early_intern_shares,
            self.early_sales_shares,
            self.early_hr_shares,
            self.developer_share_ratio,
            self.tester_flag_ratio,
            self.pm_share_ratio,
            # Timing
            self.first_share_tick if self.first_share_tick is not None else -1,
            self.first_flag_tick if self.first_flag_tick is not None else -1,
            self.time_to_first_flag if self.time_to_first_flag is not None else -1,
            self.immediate_share_ratio,
            self.verified_share_ratio,
            self.avg_trust_modifier,
            self.high_trust_shares
        ]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "early_reach": self.early_reach,
            "early_shares": self.early_shares,
            "early_flags": self.early_flags,
            "early_ignores": self.early_ignores,
            "early_verifications": self.early_verifications,
            "early_share_rate": self.early_share_rate,
            "early_flag_rate": self.early_flag_rate,
            "early_ignore_rate": self.early_ignore_rate,
            "early_verification_rate": self.early_verification_rate,
            "early_velocity": self.early_velocity,
            "share_acceleration": self.share_acceleration,
            "avg_early_confidence": self.avg_early_confidence,
            "confidence_variance": self.confidence_variance,
            "early_immediate_sharers": self.early_immediate_sharers,
            "early_cautious_sharers": self.early_cautious_sharers,
            "early_skeptics": self.early_skeptics,
            "early_influencers": self.early_influencers,
            "early_lurkers": self.early_lurkers,
            "skeptic_share_ratio": self.skeptic_share_ratio,
            "immediate_sharer_ratio": self.immediate_sharer_ratio,
            # Job role features (NEW)
            "early_developer_shares": self.early_developer_shares,
            "early_tester_shares": self.early_tester_shares,
            "early_pm_shares": self.early_pm_shares,
            "early_janitor_shares": self.early_janitor_shares,
            "early_designer_shares": self.early_designer_shares,
            "early_intern_shares": self.early_intern_shares,
            "early_sales_shares": self.early_sales_shares,
            "early_hr_shares": self.early_hr_shares,
            "developer_share_ratio": self.developer_share_ratio,
            "tester_flag_ratio": self.tester_flag_ratio,
            "pm_share_ratio": self.pm_share_ratio,
            # Timing
            "first_share_tick": self.first_share_tick,
            "first_flag_tick": self.first_flag_tick,
            "time_to_first_flag": self.time_to_first_flag,
            "immediate_share_ratio": self.immediate_share_ratio,
            "verified_share_ratio": self.verified_share_ratio,
            "avg_trust_modifier": self.avg_trust_modifier,
            "high_trust_shares": self.high_trust_shares
        }


class FeatureExtractor:
    """
    Extracts ML-ready features from dissemination records.
    
    This class transforms raw simulation data into structured features that
    capture patterns differentiating misinformation from accurate information.
    """
    
    # Feature names for ML interpretability
    POST_FEATURE_NAMES = [
        "category_news", "category_gossip", "category_entertainment",
        "category_politics", "category_science", "category_health",
        "emotional_intensity", "credibility_score", "source_reliability",
        "emotional_credibility_gap", "sensationalism_score"
    ]
    
    SPREAD_FEATURE_NAMES = [
        "early_reach", "early_shares", "early_flags", "early_ignores",
        "early_verifications", "early_share_rate", "early_flag_rate",
        "early_ignore_rate", "early_verification_rate", "early_velocity",
        "share_acceleration", "avg_early_confidence", "confidence_variance",
        "early_immediate_sharers", "early_cautious_sharers", "early_skeptics",
        "early_influencers", "early_lurkers", "skeptic_share_ratio",
        "immediate_sharer_ratio",
        # Job role features (NEW)
        "early_developer_shares", "early_tester_shares", "early_pm_shares",
        "early_janitor_shares", "early_designer_shares", "early_intern_shares",
        "early_sales_shares", "early_hr_shares",
        "developer_share_ratio", "tester_flag_ratio", "pm_share_ratio",
        # Timing
        "first_share_tick", "first_flag_tick",
        "time_to_first_flag", "immediate_share_ratio", "verified_share_ratio",
        "avg_trust_modifier", "high_trust_shares"
    ]
    
    ALL_FEATURE_NAMES = POST_FEATURE_NAMES + SPREAD_FEATURE_NAMES
    
    def __init__(self, early_window_ticks: int = 10):
        """
        Initialize the feature extractor.
        
        Args:
            early_window_ticks: Number of ticks for early dissemination window
        """
        self.early_window_ticks = early_window_ticks
    
    def extract_post_features(self, record) -> PostFeatures:
        """Extract features from post characteristics."""
        features = PostFeatures()
        
        # One-hot encode category
        category_map = {
            "news": "category_news",
            "gossip": "category_gossip",
            "entertainment": "category_entertainment",
            "politics": "category_politics",
            "science": "category_science",
            "health": "category_health"
        }
        category_attr = category_map.get(record.post_category, "category_news")
        setattr(features, category_attr, 1)
        
        # Numerical features
        features.emotional_intensity = record.emotional_intensity
        features.credibility_score = record.credibility_score
        features.source_reliability = record.source_reliability
        
        # Derived features - these capture misinformation signals
        # High emotional intensity + low credibility = suspicious
        features.emotional_credibility_gap = (
            record.emotional_intensity * (1 - record.credibility_score)
        )
        
        # Sensationalism score: high emotion + unreliable source
        features.sensationalism_score = (
            record.emotional_intensity * (1 - record.source_reliability) * 
            (1 - record.credibility_score)
        )
        
        return features
    
    def extract_spread_features(self, record) -> SpreadFeatures:
        """Extract features from dissemination patterns."""
        features = SpreadFeatures()
        
        # Get early interactions
        early_interactions = [
            i for i in record.interactions 
            if i.tick < self.early_window_ticks
        ]
        
        # Early counts
        features.early_reach = len(early_interactions)
        
        # Helper to get behavior value
        def get_behavior_value(behavior):
            return behavior.value if hasattr(behavior, 'value') else str(behavior)
        
        # Helper to get agent type value
        def get_agent_type_value(agent_type):
            return agent_type.value if hasattr(agent_type, 'value') else str(agent_type)
        
        shares = [i for i in early_interactions 
                 if get_behavior_value(i.behavior) in ["share_immediately", "verify_then_share"]]
        flags = [i for i in early_interactions 
                if get_behavior_value(i.behavior) == "flag_as_suspicious"]
        ignores = [i for i in early_interactions 
                 if get_behavior_value(i.behavior) == "ignore"]
        verifications = [i for i in early_interactions 
                        if get_behavior_value(i.behavior) in ["verify_then_share", "verify_then_ignore"]]
        immediate_shares = [i for i in early_interactions 
                          if get_behavior_value(i.behavior) == "share_immediately"]
        
        features.early_shares = len(shares)
        features.early_flags = len(flags)
        features.early_ignores = len(ignores)
        features.early_verifications = len(verifications)
        
        # Rates
        if features.early_reach > 0:
            features.early_share_rate = features.early_shares / features.early_reach
            features.early_flag_rate = features.early_flags / features.early_reach
            features.early_ignore_rate = features.early_ignores / features.early_reach
            features.early_verification_rate = features.early_verifications / features.early_reach
        
        # Velocity
        features.early_velocity = features.early_shares / max(1, self.early_window_ticks)
        
        # Share acceleration (compare first half to second half of early window)
        half_window = self.early_window_ticks // 2
        first_half_shares = len([i for i in shares if i.tick < half_window])
        second_half_shares = len([i for i in shares if i.tick >= half_window])
        features.share_acceleration = second_half_shares - first_half_shares
        
        # Confidence metrics
        if shares:
            confidences = [i.confidence for i in shares]
            features.avg_early_confidence = sum(confidences) / len(confidences)
            if len(confidences) > 1:
                mean = features.avg_early_confidence
                features.confidence_variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)
        
        # Agent type involvement in early shares
        for share in shares:
            agent_type = get_agent_type_value(share.agent_type)
            if agent_type == "immediate_sharer":
                features.early_immediate_sharers += 1
            elif agent_type == "cautious_sharer":
                features.early_cautious_sharers += 1
            elif agent_type == "skeptic":
                features.early_skeptics += 1
            elif agent_type == "influencer":
                features.early_influencers += 1
            elif agent_type == "lurker":
                features.early_lurkers += 1
            
            # Job role tracking (NEW)
            if share.job_role:
                job_role = share.job_role.value
                if job_role == "developer":
                    features.early_developer_shares += 1
                elif job_role == "tester":
                    features.early_tester_shares += 1
                elif job_role == "project_manager":
                    features.early_pm_shares += 1
                elif job_role == "janitor":
                    features.early_janitor_shares += 1
                elif job_role == "designer":
                    features.early_designer_shares += 1
                elif job_role == "intern":
                    features.early_intern_shares += 1
                elif job_role == "sales_rep":
                    features.early_sales_shares += 1
                elif job_role == "hr_manager":
                    features.early_hr_shares += 1
        
        # Agent type ratios
        if features.early_shares > 0:
            features.skeptic_share_ratio = features.early_skeptics / features.early_shares
            features.immediate_sharer_ratio = features.early_immediate_sharers / features.early_shares
            # Job role ratios (NEW)
            features.developer_share_ratio = features.early_developer_shares / features.early_shares
            features.pm_share_ratio = features.early_pm_shares / features.early_shares
        
        # Tester flag ratio (testers are good at spotting issues)
        tester_flags = sum(1 for f in flags if f.job_role and f.job_role.value == "tester")
        if features.early_flags > 0:
            features.tester_flag_ratio = tester_flags / features.early_flags
        
        # Timing
        if shares:
            features.first_share_tick = min(i.tick for i in shares)
        if flags:
            features.first_flag_tick = min(i.tick for i in flags)
        
        # Time to first flag (key misinformation signal)
        if features.first_share_tick is not None and features.first_flag_tick is not None:
            features.time_to_first_flag = features.first_flag_tick - features.first_share_tick
        
        # Behavioral pattern ratios
        if features.early_shares > 0:
            features.immediate_share_ratio = len(immediate_shares) / features.early_shares
            verified_shares = [i for i in shares if get_behavior_value(i.behavior) == "verify_then_share"]
            features.verified_share_ratio = len(verified_shares) / features.early_shares
        
        # Trust metrics
        trust_modifiers = [i.trust_modifier for i in shares]
        if trust_modifiers:
            features.avg_trust_modifier = sum(trust_modifiers) / len(trust_modifiers)
            features.high_trust_shares = len([t for t in trust_modifiers if t > 0.6])
        
        return features
    
    def extract_all_features(self, record) -> tuple[PostFeatures, SpreadFeatures]:
        """Extract all features from a dissemination record."""
        post_features = self.extract_post_features(record)
        spread_features = self.extract_spread_features(record)
        return post_features, spread_features
    
    def get_feature_vector(self, record) -> list[float]:
        """Get a combined feature vector for ML models."""
        post_features, spread_features = self.extract_all_features(record)
        return post_features.to_list() + spread_features.to_list()
    
    def get_feature_dict(self, record) -> dict:
        """Get a combined feature dictionary."""
        post_features, spread_features = self.extract_all_features(record)
        return {**post_features.to_dict(), **spread_features.to_dict()}
    
    def get_feature_names(self) -> list[str]:
        """Get all feature names."""
        return self.ALL_FEATURE_NAMES.copy()
