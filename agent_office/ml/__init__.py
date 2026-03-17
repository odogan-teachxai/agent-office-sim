"""
ML Pipeline for Agent Office - Dataset Generation and Machine Learning

This module provides:
- Early dissemination tracking
- Feature extraction for ML
- Dataset building for training
- Simple ML models for misinformation detection
"""

from .data_collector import EarlyDisseminationTracker, DisseminationRecord
from .feature_extractor import FeatureExtractor, PostFeatures, SpreadFeatures
from .dataset_builder import DatasetBuilder, DatasetRecord
from .ml_pipeline import MLPipeline

__all__ = [
    "EarlyDisseminationTracker",
    "DisseminationRecord",
    "FeatureExtractor",
    "PostFeatures",
    "SpreadFeatures",
    "DatasetBuilder",
    "DatasetRecord",
    "MLPipeline",
]
