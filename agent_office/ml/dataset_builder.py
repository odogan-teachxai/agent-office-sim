"""
Dataset Builder Module - Creates ML-ready datasets from simulation data.

This module transforms collected dissemination records into clean, organized
datasets suitable for machine learning. It supports multiple output formats
and handles train/test splitting.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from datetime import datetime
import json
import csv
import random

from .data_collector import DisseminationRecord, EarlyDisseminationTracker
from .feature_extractor import FeatureExtractor


@dataclass
class DatasetRecord:
    """A single record in the ML dataset."""
    # Identifier
    post_id: str
    
    # Label (what we're trying to predict)
    is_misinformation: int  # 1 if false/mixed, 0 if true
    truth_value: str  # original truth value for reference
    
    # Features
    features: dict
    
    # Metadata
    total_reach: int
    total_shares: int
    total_flags: int


class DatasetBuilder:
    """
    Builds ML-ready datasets from dissemination records.
    
    This class handles:
    - Feature extraction
    - Label creation
    - Train/test splitting
    - Multiple output formats (CSV, JSONL, JSON)
    """
    
    def __init__(
        self,
        feature_extractor: Optional[FeatureExtractor] = None,
        label_column: str = "is_misinformation",
        random_seed: int = 42
    ):
        """
        Initialize the dataset builder.
        
        Args:
            feature_extractor: FeatureExtractor instance (creates default if None)
            label_column: Name of the label column
            random_seed: Random seed for reproducibility
        """
        self.feature_extractor = feature_extractor or FeatureExtractor()
        self.label_column = label_column
        self.random_seed = random_seed
        self.records: list[DatasetRecord] = []
    
    def add_record(self, dissemination_record: DisseminationRecord) -> DatasetRecord:
        """
        Add a dissemination record to the dataset.
        
        Args:
            dissemination_record: Record from EarlyDisseminationTracker
            
        Returns:
            The created DatasetRecord
        """
        # Extract features
        features = self.feature_extractor.get_feature_dict(dissemination_record)
        
        # Create label
        # is_misinformation = 1 if post is false or mixed, 0 if true
        is_misinformation = 1 if dissemination_record.truth_value in ["false", "mixed"] else 0
        
        # Create dataset record
        dataset_record = DatasetRecord(
            post_id=dissemination_record.post_id,
            is_misinformation=is_misinformation,
            truth_value=dissemination_record.truth_value,
            features=features,
            total_reach=dissemination_record.total_reach,
            total_shares=dissemination_record.total_shares,
            total_flags=dissemination_record.total_flags
        )
        
        self.records.append(dataset_record)
        return dataset_record
    
    def add_records_from_tracker(self, tracker: EarlyDisseminationTracker) -> int:
        """
        Add all records from a tracker.
        
        Args:
            tracker: EarlyDisseminationTracker instance
            
        Returns:
            Number of records added
        """
        count = 0
        for record in tracker.get_all_records():
            self.add_record(record)
            count += 1
        return count
    
    def get_feature_matrix(self) -> list[list[float]]:
        """Get the feature matrix (X) for ML models."""
        feature_names = self.feature_extractor.get_feature_names()
        matrix = []
        for record in self.records:
            row = []
            for name in feature_names:
                value = record.features.get(name, 0.0)
                # Handle None values
                if value is None:
                    value = 0.0
                row.append(float(value))
            matrix.append(row)
        return matrix
    
    def get_labels(self) -> list[int]:
        """Get the label vector (y) for ML models."""
        return [record.is_misinformation for record in self.records]
    
    def train_test_split(
        self,
        test_ratio: float = 0.2,
        stratify: bool = True
    ) -> tuple[list[DatasetRecord], list[DatasetRecord]]:
        """
        Split the dataset into training and test sets.
        
        Args:
            test_ratio: Fraction of data to use for testing
            stratify: Whether to maintain class distribution in splits
            
        Returns:
            Tuple of (train_records, test_records)
        """
        random.seed(self.random_seed)
        
        if stratify:
            # Separate by class
            misinfo_records = [r for r in self.records if r.is_misinformation == 1]
            accurate_records = [r for r in self.records if r.is_misinformation == 0]
            
            # Shuffle each class
            random.shuffle(misinfo_records)
            random.shuffle(accurate_records)
            
            # Split each class
            misinfo_test_size = int(len(misinfo_records) * test_ratio)
            accurate_test_size = int(len(accurate_records) * test_ratio)
            
            test_records = (
                misinfo_records[:misinfo_test_size] + 
                accurate_records[:accurate_test_size]
            )
            train_records = (
                misinfo_records[misinfo_test_size:] + 
                accurate_records[accurate_test_size:]
            )
        else:
            # Simple random split
            shuffled = self.records.copy()
            random.shuffle(shuffled)
            test_size = int(len(shuffled) * test_ratio)
            test_records = shuffled[:test_size]
            train_records = shuffled[test_size:]
        
        # Shuffle the final splits
        random.shuffle(train_records)
        random.shuffle(test_records)
        
        return train_records, test_records
    
    def get_class_distribution(self) -> dict:
        """Get the distribution of classes in the dataset."""
        misinfo_count = sum(1 for r in self.records if r.is_misinformation == 1)
        accurate_count = sum(1 for r in self.records if r.is_misinformation == 0)
        
        return {
            "total": len(self.records),
            "misinformation": misinfo_count,
            "accurate": accurate_count,
            "misinformation_ratio": misinfo_count / max(1, len(self.records)),
            "accurate_ratio": accurate_count / max(1, len(self.records))
        }
    
    def get_statistics(self) -> dict:
        """Get dataset statistics."""
        feature_names = self.feature_extractor.get_feature_names()
        
        # Calculate feature statistics
        feature_stats = {}
        for name in feature_names:
            values = []
            for r in self.records:
                val = r.features.get(name, 0.0)
                if val is None:
                    val = 0.0
                values.append(float(val))
            
            if values:
                mean = sum(values) / len(values)
                variance = sum((v - mean) ** 2 for v in values) / len(values)
                feature_stats[name] = {
                    "mean": mean,
                    "std": variance ** 0.5,
                    "min": min(values),
                    "max": max(values)
                }
        
        return {
            "total_records": len(self.records),
            "num_features": len(feature_names),
            "feature_names": feature_names,
            "class_distribution": self.get_class_distribution(),
            "feature_statistics": feature_stats
        }
    
    def to_dict_list(self) -> list[dict]:
        """Convert all records to a list of dictionaries."""
        feature_names = self.feature_extractor.get_feature_names()
        
        records = []
        for record in self.records:
            row = {
                "post_id": record.post_id,
                self.label_column: record.is_misinformation,
                "truth_value": record.truth_value,
                "total_reach": record.total_reach,
                "total_shares": record.total_shares,
                "total_flags": record.total_flags
            }
            # Add features
            for name in feature_names:
                row[name] = record.features.get(name, 0.0)
            records.append(row)
        
        return records
    
    def save_to_csv(self, filepath: str) -> None:
        """Save dataset to CSV file."""
        feature_names = self.feature_extractor.get_feature_names()
        
        # Column order
        columns = ["post_id", self.label_column, "truth_value", 
                   "total_reach", "total_shares", "total_flags"] + feature_names
        
        records = self.to_dict_list()
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(records)
    
    def save_to_jsonl(self, filepath: str) -> None:
        """Save dataset to JSONL (one JSON object per line)."""
        records = self.to_dict_list()
        
        with open(filepath, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
    
    def save_to_json(self, filepath: str) -> None:
        """Save dataset to JSON file with metadata."""
        data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_records": len(self.records),
                "num_features": len(self.feature_extractor.get_feature_names()),
                "class_distribution": self.get_class_distribution()
            },
            "feature_names": self.feature_extractor.get_feature_names(),
            "records": self.to_dict_list()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def save_splits(
        self,
        output_dir: str,
        test_ratio: float = 0.2,
        prefix: str = "dataset"
    ) -> dict:
        """
        Save train/test splits to files.
        
        Args:
            output_dir: Directory to save files
            test_ratio: Test set ratio
            prefix: File prefix
            
        Returns:
            Dictionary with file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        train_records, test_records = self.train_test_split(test_ratio)
        
        # Create temporary builders for each split
        train_builder = DatasetBuilder(
            feature_extractor=self.feature_extractor,
            label_column=self.label_column,
            random_seed=self.random_seed
        )
        train_builder.records = train_records
        
        test_builder = DatasetBuilder(
            feature_extractor=self.feature_extractor,
            label_column=self.label_column,
            random_seed=self.random_seed
        )
        test_builder.records = test_records
        
        # Save files
        paths = {
            "train_csv": str(output_path / f"{prefix}_train.csv"),
            "test_csv": str(output_path / f"{prefix}_test.csv"),
            "train_jsonl": str(output_path / f"{prefix}_train.jsonl"),
            "test_jsonl": str(output_path / f"{prefix}_test.jsonl"),
            "full_json": str(output_path / f"{prefix}_full.json")
        }
        
        train_builder.save_to_csv(paths["train_csv"])
        test_builder.save_to_csv(paths["test_csv"])
        train_builder.save_to_jsonl(paths["train_jsonl"])
        test_builder.save_to_jsonl(paths["test_jsonl"])
        self.save_to_json(paths["full_json"])
        
        return {
            **paths,
            "train_size": len(train_records),
            "test_size": len(test_records),
            "class_distribution": self.get_class_distribution()
        }
    
    def __len__(self) -> int:
        return len(self.records)
    
    def __repr__(self) -> str:
        dist = self.get_class_distribution()
        return (
            f"DatasetBuilder(records={len(self.records)}, "
            f"features={dist['total']}, "
            f"misinfo_ratio={dist['misinformation_ratio']:.2f})"
        )
