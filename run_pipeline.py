#!/usr/bin/env python3
"""
Run the Agent Office ML Training Pipeline.

This script:
1. Generates 500+ rows of training data from simulations
2. Saves the dataset to CSV
3. Trains Logistic Regression and SVM models
4. Compares and reports results
"""

from agent_office import DataGenerationPipeline

if __name__ == "__main__":
    pipeline = DataGenerationPipeline(
        output_dir="output",
        early_window_ticks=10,
        random_seed=42
    )
    
    results = pipeline.run_full_pipeline(
        num_simulations=70,     # ~560 posts
        num_agents=13,          # 13 agents per simulation
        num_posts=8,            # 8 posts per simulation
        num_epochs=20,          # 20 training epochs
        min_samples=500,        # Ensure at least 500 samples
        verbose=True
    )
    
    print("\n" + "=" * 70)
    print("🎉 Training complete! Check the output directory for results.")
    print("=" * 70)
