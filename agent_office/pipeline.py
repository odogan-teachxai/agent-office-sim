#!/usr/bin/env python3
"""
Data Generation Pipeline for Agent Office

This module runs multiple simulations to generate a dataset suitable for
machine learning. It collects early dissemination patterns and creates
ML-ready data files.
"""

import argparse
import random
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from .agent import Agent, AgentType, JobRole, create_agent_from_type
from .post import Post, create_sample_posts
from .network import SocialNetwork
from .simulation import Simulation
from .logger import SimulationLogger
from .ml.data_collector import EarlyDisseminationTracker
from .ml.feature_extractor import FeatureExtractor
from .ml.dataset_builder import DatasetBuilder
from .ml.ml_pipeline import MLPipeline, TrainingConfig


class DataGenerationPipeline:
    """
    Pipeline for generating ML-ready datasets from multiple simulations.
    
    This class:
    1. Runs multiple simulations with different random seeds
    2. Collects early dissemination data for each post
    3. Extracts features and builds a dataset
    4. Trains and compares ML models
    """
    
    def __init__(
        self,
        output_dir: str = "output",
        early_window_ticks: int = 10,
        random_seed: int = 42
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.early_window_ticks = early_window_ticks
        self.random_seed = random_seed
        
        self.feature_extractor = FeatureExtractor(early_window_ticks)
        self.dataset_builder = DatasetBuilder(
            feature_extractor=self.feature_extractor,
            random_seed=random_seed
        )
        self.ml_pipeline: Optional[MLPipeline] = None
    
    def create_agents(self, num_agents: int = 13) -> list[Agent]:
        """Create a diverse set of agents with job roles."""
        agents = []
        agent_types = list(AgentType)
        agent_names = [
            "Alice", "Bob", "Charlie", "Diana", "Eve",
            "Frank", "Grace", "Henry", "Ivy", "Jack",
            "Kate", "Leo", "Mia", "Noah", "Olivia"
        ]
        # Job roles for office simulation (cycle through them)
        job_roles = list(JobRole)
        
        for i in range(num_agents):
            agent_type = agent_types[i % len(agent_types)]
            job_role = job_roles[i % len(job_roles)]
            name = agent_names[i] if i < len(agent_names) else f"Agent_{i}"
            agent = create_agent_from_type(f"agent_{i}", name, agent_type, job_role=job_role)
            agents.append(agent)
        
        return agents
    
    def run_single_simulation(
        self,
        seed: int,
        num_agents: int = 13,
        num_posts: int = 8,
        tick_delay: float = 0.05,
        max_ticks: int = 150,
        verbose: bool = False
    ) -> EarlyDisseminationTracker:
        """Run a single simulation and collect data."""
        random.seed(seed)
        
        network = SocialNetwork()
        agents = self.create_agents(num_agents)
        
        tracker = EarlyDisseminationTracker(self.early_window_ticks)
        
        for agent in agents:
            network.add_agent(agent)
            tracker.register_agent(agent.id, agent.agent_type, agent.job_role)
        
        network.create_preferential_attachment_network(avg_connections=4)
        
        def on_event(event):
            tracker.record_event(
                tick=event.tick,
                post_id=event.post_id,
                agent_id=event.agent_id,
                agent_name=event.agent_name,
                behavior=event.behavior,
                confidence=event.details.get("confidence", 0.5),
                trust_modifier=event.details.get("trust_modifier", 0.5),
                from_agent_id=None
            )
        
        simulation = Simulation(
            network=network,
            tick_delay=tick_delay,
            on_event=on_event
        )
        
        all_posts = create_sample_posts()
        posts_to_use = random.sample(all_posts, min(num_posts, len(all_posts)))
        
        for post in posts_to_use:
            tracker.register_post(post)
            influencers = [a for a in agents if a.agent_type == AgentType.INFLUENCER]
            if influencers and random.random() < 0.5:
                initial_agent = random.choice(influencers)
            else:
                initial_agent = random.choice(agents)
            simulation.add_post(post, initial_agent)
        
        simulation.run(max_ticks=max_ticks, stop_when_idle=True, idle_threshold=8)
        
        if verbose:
            print(f"  Simulation {seed}: {len(tracker.records)} posts tracked, "
                  f"{sum(len(r.interactions) for r in tracker.records.values())} interactions")
        
        return tracker
    
    def run_multiple_simulations(
        self,
        num_simulations: int = 10,
        num_agents: int = 13,
        num_posts: int = 8,
        verbose: bool = True
    ) -> None:
        """Run multiple simulations and aggregate data."""
        if verbose:
            print(f"\n🔄 Running {num_simulations} simulations...")
            print("=" * 60)
        
        for i in range(num_simulations):
            seed = self.random_seed + i
            tracker = self.run_single_simulation(
                seed=seed,
                num_agents=num_agents,
                num_posts=num_posts,
                verbose=verbose
            )
            self.dataset_builder.add_records_from_tracker(tracker)
        
        if verbose:
            print("=" * 60)
            dist = self.dataset_builder.get_class_distribution()
            print(f"\n📊 Dataset Statistics:")
            print(f"   Total records: {dist['total']}")
            print(f"   Misinformation: {dist['misinformation']} ({dist['misinformation_ratio']:.1%})")
            print(f"   Accurate: {dist['accurate']} ({dist['accurate_ratio']:.1%})")
    
    def build_dataset(self, verbose: bool = True) -> dict:
        """Build and save the dataset."""
        if verbose:
            print(f"\n📁 Building dataset...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"misinfo_dataset_{timestamp}"
        
        paths = self.dataset_builder.save_splits(
            str(self.output_dir),
            test_ratio=0.2,
            prefix=prefix
        )
        
        if verbose:
            print(f"   Train set: {paths['train_size']} samples")
            print(f"   Test set: {paths['test_size']} samples")
            print(f"   Files saved to: {self.output_dir}")
            for name, path in paths.items():
                if name.endswith('_csv') or name.endswith('_jsonl') or name.endswith('_json'):
                    print(f"     • {name}: {Path(path).name}")
        
        return paths
    
    def train_models(
        self,
        num_epochs: int = 20,
        verbose: bool = True
    ) -> dict:
        """
        Train and compare Logistic Regression and SVM models.
        """
        if verbose:
            print(f"\n🤖 Training ML models...")
        
        config = TrainingConfig(
            learning_rate=0.01,
            num_epochs=num_epochs,
            regularization=0.01,
            random_seed=self.random_seed,
            batch_size=32,
            validation_split=0.15
        )
        
        self.ml_pipeline = MLPipeline(config, self.feature_extractor)
        results = self.ml_pipeline.train_and_compare(
            self.dataset_builder,
            verbose=verbose
        )
        
        return results
    
    def run_full_pipeline(
        self,
        num_simulations: int = 70,  # ~560 posts (70 * 8)
        num_agents: int = 13,
        num_posts: int = 8,
        num_epochs: int = 20,
        min_samples: int = 500,
        verbose: bool = True
    ) -> dict:
        """
        Run the complete data generation and ML pipeline.
        
        Args:
            num_simulations: Number of simulations to run
            num_agents: Agents per simulation
            num_posts: Posts per simulation
            num_epochs: Number of training epochs
            min_samples: Minimum required samples
            verbose: Print progress
        """
        if verbose:
            print("\n" + "=" * 70)
            print("   🏢 AGENT OFFICE - ML Training Pipeline")
            print("=" * 70)
            print(f"\n⚙️  Configuration:")
            print(f"   Target minimum samples: {min_samples}")
            print(f"   Simulations: {num_simulations}")
            print(f"   Agents per simulation: {num_agents}")
            print(f"   Posts per simulation: {num_posts}")
            print(f"   Training epochs: {num_epochs}")
            print(f"   Early window: {self.early_window_ticks} ticks")
        
        # Run simulations
        self.run_multiple_simulations(
            num_simulations=num_simulations,
            num_agents=num_agents,
            num_posts=num_posts,
            verbose=verbose
        )
        
        # Check if we have enough samples
        total_samples = len(self.dataset_builder)
        if total_samples < min_samples:
            additional_sims = (min_samples - total_samples) // num_posts + 1
            if verbose:
                print(f"\n⚠️  Need more samples. Running {additional_sims} additional simulations...")
            self.run_multiple_simulations(
                num_simulations=additional_sims,
                num_agents=num_agents,
                num_posts=num_posts,
                verbose=verbose
            )
        
        # Build dataset
        dataset_paths = self.build_dataset(verbose=verbose)
        
        # Save combined training CSV
        self._save_training_csv(verbose)
        
        # Train models
        ml_results = self.train_models(num_epochs=num_epochs, verbose=verbose)
        
        # Save final results
        result_paths = self.ml_pipeline.save_results(str(self.output_dir))
        
        if verbose:
            print("\n" + "=" * 70)
            print("   ✅ Pipeline Complete!")
            print("=" * 70)
            print(f"\n💾 Output Files:")
            print(f"   • Training CSV: {self.output_dir}/training_data.csv")
            print(f"   • Model Comparison: {Path(result_paths['comparison_report']).name}")
        
        return {
            "dataset_paths": dataset_paths,
            "ml_results": ml_results,
            "statistics": self.dataset_builder.get_statistics(),
            "total_samples": len(self.dataset_builder)
        }
    
    def _save_training_csv(self, verbose: bool = True) -> None:
        """Save the complete training dataset to a single CSV file."""
        csv_path = self.output_dir / "training_data.csv"
        self.dataset_builder.save_to_csv(str(csv_path))
        
        if verbose:
            print(f"\n📄 Saved training data to: {csv_path}")
            print(f"   Total rows: {len(self.dataset_builder)}")


def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(
        description="Agent Office - ML Training Pipeline"
    )
    parser.add_argument(
        "--simulations", "-s",
        type=int,
        default=70,
        help="Number of simulations to run (default: 70)"
    )
    parser.add_argument(
        "--agents", "-a",
        type=int,
        default=13,
        help="Number of agents per simulation (default: 13)"
    )
    parser.add_argument(
        "--posts", "-p",
        type=int,
        default=8,
        help="Number of posts per simulation (default: 8)"
    )
    parser.add_argument(
        "--epochs", "-e",
        type=int,
        default=20,
        help="Number of training epochs (default: 20)"
    )
    parser.add_argument(
        "--min-samples", "-m",
        type=int,
        default=500,
        help="Minimum training samples required (default: 500)"
    )
    parser.add_argument(
        "--early-window", "-w",
        type=int,
        default=10,
        help="Early dissemination window in ticks (default: 10)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="Output directory (default: output)"
    )
    
    args = parser.parse_args()
    
    pipeline = DataGenerationPipeline(
        output_dir=args.output,
        early_window_ticks=args.early_window
    )
    
    results = pipeline.run_full_pipeline(
        num_simulations=args.simulations,
        num_agents=args.agents,
        num_posts=args.posts,
        num_epochs=args.epochs,
        min_samples=args.min_samples,
        verbose=True
    )
    
    return results


if __name__ == "__main__":
    main()
