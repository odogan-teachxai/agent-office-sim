"""
ML Pipeline Module - Machine learning for misinformation detection.

This module provides:
- Logistic Regression model
- Support Vector Machine (SVM) model
- Epoch-based training with metrics tracking
- Comprehensive evaluation and comparison reporting
"""

from dataclasses import dataclass, field
from typing import Optional, Union, Callable
from pathlib import Path
from datetime import datetime
import json
import math
import random

from .dataset_builder import DatasetBuilder, DatasetRecord
from .feature_extractor import FeatureExtractor


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    learning_rate: float = 0.01
    num_epochs: int = 20
    regularization: float = 0.01
    random_seed: int = 42
    batch_size: int = 32  # For mini-batch gradient descent
    validation_split: float = 0.15


@dataclass
class EpochMetrics:
    """Metrics for a single training epoch."""
    epoch: int
    train_loss: float
    train_accuracy: float
    val_loss: Optional[float] = None
    val_accuracy: Optional[float] = None


@dataclass
class EvaluationMetrics:
    """Evaluation metrics for model performance."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    auc_roc: float = 0.0
    
    # Confusion matrix
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    
    def to_dict(self) -> dict:
        return {
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "auc_roc": round(self.auc_roc, 4),
            "confusion_matrix": {
                "true_positives": self.true_positives,
                "true_negatives": self.true_negatives,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives
            }
        }


class LogisticRegressionModel:
    """
    Logistic Regression implementation with epoch-based training.
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.weights: list[float] = []
        self.bias: float = 0.0
        self.feature_names: list[str] = []
        self.is_trained: bool = False
        self.training_history: list[EpochMetrics] = []
    
    def _sigmoid(self, z: float) -> float:
        """Sigmoid activation function."""
        if z >= 0:
            return 1 / (1 + math.exp(-z))
        else:
            exp_z = math.exp(z)
            return exp_z / (1 + exp_z)
    
    def _predict_proba_single(self, features: list[float]) -> float:
        """Predict probability for a single sample."""
        z = sum(w * f for w, f in zip(self.weights, features)) + self.bias
        return self._sigmoid(z)
    
    def predict_proba(self, X: list[list[float]]) -> list[float]:
        """Predict probabilities for multiple samples."""
        return [self._predict_proba_single(x) for x in X]
    
    def predict(self, X: list[list[float]], threshold: float = 0.5) -> list[int]:
        """Predict class labels."""
        probas = self.predict_proba(X)
        return [1 if p >= threshold else 0 for p in probas]
    
    def _compute_loss(self, X: list[list[float]], y: list[int]) -> float:
        """Compute binary cross-entropy loss."""
        m = len(X)
        total_loss = 0.0
        
        for features, label in zip(X, y):
            prob = self._predict_proba_single(features)
            prob = max(1e-15, min(1 - 1e-15, prob))
            
            if label == 1:
                total_loss -= math.log(prob)
            else:
                total_loss -= math.log(1 - prob)
        
        # L2 regularization
        reg_term = sum(w ** 2 for w in self.weights) * self.config.regularization / (2 * m)
        
        return (total_loss / m) + reg_term
    
    def _compute_accuracy(self, X: list[list[float]], y: list[int]) -> float:
        """Compute accuracy."""
        predictions = self.predict(X)
        correct = sum(1 for p, t in zip(predictions, y) if p == t)
        return correct / len(y)
    
    def fit(
        self,
        X_train: list[list[float]],
        y_train: list[int],
        X_val: Optional[list[list[float]]] = None,
        y_val: Optional[list[int]] = None,
        feature_names: Optional[list[str]] = None
    ) -> list[EpochMetrics]:
        """
        Train the model using mini-batch gradient descent with epochs.
        """
        random.seed(self.config.random_seed)
        
        n_features = len(X_train[0]) if X_train else 0
        self.weights = [random.gauss(0, 0.01) for _ in range(n_features)]
        self.bias = 0.0
        self.feature_names = feature_names or [f"feature_{i}" for i in range(n_features)]
        
        m = len(X_train)
        batch_size = min(self.config.batch_size, m)
        
        for epoch in range(self.config.num_epochs):
            # Shuffle training data
            indices = list(range(m))
            random.shuffle(indices)
            X_shuffled = [X_train[i] for i in indices]
            y_shuffled = [y_train[i] for i in indices]
            
            # Mini-batch gradient descent
            for start_idx in range(0, m, batch_size):
                end_idx = min(start_idx + batch_size, m)
                X_batch = X_shuffled[start_idx:end_idx]
                y_batch = y_shuffled[start_idx:end_idx]
                batch_m = len(X_batch)
                
                # Compute gradients
                dw = [0.0] * n_features
                db = 0.0
                
                for features, label in zip(X_batch, y_batch):
                    prob = self._predict_proba_single(features)
                    error = prob - label
                    
                    for j in range(n_features):
                        dw[j] += error * features[j]
                    db += error
                
                # Average and add regularization
                dw = [d / batch_m + self.config.regularization * self.weights[j] / batch_m 
                      for j, d in enumerate(dw)]
                db /= batch_m
                
                # Update weights
                self.weights = [w - self.config.learning_rate * dw[j] 
                              for j, w in enumerate(self.weights)]
                self.bias -= self.config.learning_rate * db
            
            # Compute metrics for this epoch
            train_loss = self._compute_loss(X_train, y_train)
            train_acc = self._compute_accuracy(X_train, y_train)
            
            val_loss = None
            val_acc = None
            if X_val and y_val:
                val_loss = self._compute_loss(X_val, y_val)
                val_acc = self._compute_accuracy(X_val, y_val)
            
            epoch_metrics = EpochMetrics(
                epoch=epoch + 1,
                train_loss=train_loss,
                train_accuracy=train_acc,
                val_loss=val_loss,
                val_accuracy=val_acc
            )
            self.training_history.append(epoch_metrics)
        
        self.is_trained = True
        return self.training_history
    
    def get_feature_importance(self) -> list[dict]:
        """Get feature importance based on weight magnitudes."""
        if not self.is_trained:
            return []
        
        importance = [
            {"feature": name, "weight": weight, "importance": abs(weight)}
            for name, weight in zip(self.feature_names, self.weights)
        ]
        importance.sort(key=lambda x: x["importance"], reverse=True)
        return importance


class SVMModel:
    """
    Support Vector Machine implementation using Pegasos (Primal Estimated sub-GrAdient SOlver for SVM).
    
    This is a simplified linear SVM trained with stochastic gradient descent.
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.weights: list[float] = []
        self.bias: float = 0.0
        self.feature_names: list[str] = []
        self.is_trained: bool = False
        self.training_history: list[EpochMetrics] = []
        # SVM-specific parameter (lambda for regularization)
        self.lambda_param: float = config.regularization if config else 0.01
    
    def _decision_function(self, features: list[float]) -> float:
        """Compute the decision function value."""
        return sum(w * f for w, f in zip(self.weights, features)) + self.bias
    
    def predict_proba(self, X: list[list[float]]) -> list[float]:
        """Predict probabilities (using Platt scaling approximation)."""
        decisions = [self._decision_function(x) for x in X]
        # Simple sigmoid approximation for probability
        return [1 / (1 + math.exp(-d)) for d in decisions]
    
    def predict(self, X: list[list[float]]) -> list[int]:
        """Predict class labels."""
        return [1 if self._decision_function(x) >= 0 else 0 for x in X]
    
    def _compute_hinge_loss(self, X: list[list[float]], y: list[int]) -> float:
        """Compute hinge loss with L2 regularization."""
        m = len(X)
        total_loss = 0.0
        
        for features, label in zip(X, y):
            # Convert 0/1 labels to -1/1 for SVM
            y_svm = 2 * label - 1
            decision = self._decision_function(features)
            hinge = max(0, 1 - y_svm * decision)
            total_loss += hinge
        
        # L2 regularization
        reg_term = 0.5 * self.lambda_param * sum(w ** 2 for w in self.weights)
        
        return (total_loss / m) + reg_term
    
    def _compute_accuracy(self, X: list[list[float]], y: list[int]) -> float:
        """Compute accuracy."""
        predictions = self.predict(X)
        correct = sum(1 for p, t in zip(predictions, y) if p == t)
        return correct / len(y)
    
    def fit(
        self,
        X_train: list[list[float]],
        y_train: list[int],
        X_val: Optional[list[list[float]]] = None,
        y_val: Optional[list[int]] = None,
        feature_names: Optional[list[str]] = None
    ) -> list[EpochMetrics]:
        """
        Train the SVM using Pegasos algorithm with epochs.
        """
        random.seed(self.config.random_seed)
        
        n_features = len(X_train[0]) if X_train else 0
        m = len(X_train)
        
        # Initialize weights
        self.weights = [0.0] * n_features
        self.bias = 0.0
        self.feature_names = feature_names or [f"feature_{i}" for i in range(n_features)]
        
        # Learning rate schedule
        t = 0
        
        for epoch in range(self.config.num_epochs):
            # Shuffle training data
            indices = list(range(m))
            random.shuffle(indices)
            
            for i in indices:
                t += 1
                eta = 1.0 / (self.lambda_param * t)  # Learning rate
                
                features = X_train[i]
                label = y_train[i]
                y_svm = 2 * label - 1  # Convert 0/1 to -1/1
                
                decision = self._decision_function(features)
                
                # Update rule (Pegasos)
                if y_svm * decision < 1:
                    # Misclassified or within margin
                    for j in range(n_features):
                        self.weights[j] = (1 - eta * self.lambda_param) * self.weights[j] + eta * y_svm * features[j]
                    self.bias += eta * y_svm
                else:
                    # Correctly classified outside margin
                    for j in range(n_features):
                        self.weights[j] = (1 - eta * self.lambda_param) * self.weights[j]
            
            # Compute metrics
            train_loss = self._compute_hinge_loss(X_train, y_train)
            train_acc = self._compute_accuracy(X_train, y_train)
            
            val_loss = None
            val_acc = None
            if X_val and y_val:
                val_loss = self._compute_hinge_loss(X_val, y_val)
                val_acc = self._compute_accuracy(X_val, y_val)
            
            epoch_metrics = EpochMetrics(
                epoch=epoch + 1,
                train_loss=train_loss,
                train_accuracy=train_acc,
                val_loss=val_loss,
                val_accuracy=val_acc
            )
            self.training_history.append(epoch_metrics)
        
        self.is_trained = True
        return self.training_history
    
    def get_feature_importance(self) -> list[dict]:
        """Get feature importance based on weight magnitudes."""
        if not self.is_trained:
            return []
        
        importance = [
            {"feature": name, "weight": weight, "importance": abs(weight)}
            for name, weight in zip(self.feature_names, self.weights)
        ]
        importance.sort(key=lambda x: x["importance"], reverse=True)
        return importance


class ModelTrainer:
    """
    Handles training, evaluation, and comparison of multiple models.
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.models: dict[str, Union[LogisticRegressionModel, SVMModel]] = {}
        self.training_results: dict[str, dict] = {}
        self.evaluation_results: dict[str, EvaluationMetrics] = {}
    
    def add_model(self, name: str, model: Union[LogisticRegressionModel, SVMModel]) -> None:
        """Add a model for training."""
        self.models[name] = model
    
    def train_all(
        self,
        X_train: list[list[float]],
        y_train: list[int],
        X_val: Optional[list[list[float]]] = None,
        y_val: Optional[list[int]] = None,
        feature_names: Optional[list[str]] = None
    ) -> dict:
        """Train all models and return results."""
        results = {}
        
        for name, model in self.models.items():
            history = model.fit(
                X_train, y_train,
                X_val, y_val,
                feature_names
            )
            
            results[name] = {
                "training_history": [
                    {
                        "epoch": m.epoch,
                        "train_loss": round(m.train_loss, 4),
                        "train_accuracy": round(m.train_accuracy, 4),
                        "val_loss": round(m.val_loss, 4) if m.val_loss else None,
                        "val_accuracy": round(m.val_accuracy, 4) if m.val_accuracy else None
                    }
                    for m in history
                ],
                "final_train_loss": round(history[-1].train_loss, 4),
                "final_train_accuracy": round(history[-1].train_accuracy, 4),
                "final_val_loss": round(history[-1].val_loss, 4) if history[-1].val_loss else None,
                "final_val_accuracy": round(history[-1].val_accuracy, 4) if history[-1].val_accuracy else None
            }
            
            self.training_results[name] = results[name]
        
        return results
    
    def evaluate_all(
        self,
        X_test: list[list[float]],
        y_test: list[int]
    ) -> dict[str, EvaluationMetrics]:
        """Evaluate all models on test data."""
        for name, model in self.models.items():
            metrics = self._evaluate_model(model, X_test, y_test)
            self.evaluation_results[name] = metrics
        
        return self.evaluation_results
    
    def _evaluate_model(
        self,
        model: Union[LogisticRegressionModel, SVMModel],
        X: list[list[float]],
        y: list[int]
    ) -> EvaluationMetrics:
        """Evaluate a single model."""
        predictions = model.predict(X)
        probas = model.predict_proba(X)
        
        # Confusion matrix
        tp = sum(1 for p, t in zip(predictions, y) if p == 1 and t == 1)
        tn = sum(1 for p, t in zip(predictions, y) if p == 0 and t == 0)
        fp = sum(1 for p, t in zip(predictions, y) if p == 1 and t == 0)
        fn = sum(1 for p, t in zip(predictions, y) if p == 0 and t == 1)
        
        # Metrics
        total = tp + tn + fp + fn
        accuracy = (tp + tn) / max(1, total)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(1e-10, precision + recall)
        
        # AUC-ROC
        auc = self._compute_auc(probas, y)
        
        return EvaluationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            auc_roc=auc,
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn
        )
    
    def _compute_auc(self, probas: list[float], y: list[int]) -> float:
        """Compute AUC-ROC score."""
        pairs = list(zip(probas, y))
        pairs.sort(key=lambda x: x[0], reverse=True)
        
        n_pos = sum(y)
        n_neg = len(y) - n_pos
        
        if n_pos == 0 or n_neg == 0:
            return 0.5
        
        auc = 0.0
        tp_count = 0
        
        for prob, label in pairs:
            if label == 1:
                tp_count += 1
            else:
                auc += tp_count
        
        return auc / (n_pos * n_neg)
    
    def get_comparison_report(self) -> dict:
        """Generate a comprehensive comparison report."""
        report = {
            "models": {},
            "comparison": {},
            "best_model": None,
            "summary": ""
        }
        
        best_accuracy = 0
        best_model_name = None
        
        for name in self.models.keys():
            train_result = self.training_results.get(name, {})
            eval_metrics = self.evaluation_results.get(name)
            
            report["models"][name] = {
                "training": {
                    "final_train_accuracy": train_result.get("final_train_accuracy"),
                    "final_val_accuracy": train_result.get("final_val_accuracy"),
                    "epochs_trained": len(train_result.get("training_history", []))
                },
                "test_evaluation": eval_metrics.to_dict() if eval_metrics else None,
                "feature_importance": self.models[name].get_feature_importance()[:10]
            }
            
            if eval_metrics and eval_metrics.accuracy > best_accuracy:
                best_accuracy = eval_metrics.accuracy
                best_model_name = name
        
        report["best_model"] = best_model_name
        
        # Generate comparison analysis
        if len(self.models) >= 2:
            model_names = list(self.models.keys())
            m1, m2 = model_names[0], model_names[1]
            
            m1_train = self.training_results.get(m1, {}).get("final_train_accuracy", 0)
            m2_train = self.training_results.get(m2, {}).get("final_train_accuracy", 0)
            m1_test = self.evaluation_results.get(m1, EvaluationMetrics()).accuracy
            m2_test = self.evaluation_results.get(m2, EvaluationMetrics()).accuracy
            
            # Calculate generalization gap
            m1_gap = m1_train - m1_test
            m2_gap = m2_train - m2_test
            
            report["comparison"] = {
                "accuracy_difference": round(m1_test - m2_test, 4),
                "generalization_gap": {
                    m1: round(m1_gap, 4),
                    m2: round(m2_gap, 4)
                },
                "better_generalizer": m1 if m1_gap < m2_gap else m2,
                "higher_test_accuracy": m1 if m1_test > m2_test else m2
            }
            
            # Generate summary text
            summary_lines = [
                f"Model Comparison Summary:",
                f"",
                f"1. {m1} (Logistic Regression):",
                f"   - Training Accuracy: {m1_train:.1%}",
                f"   - Test Accuracy: {m1_test:.1%}",
                f"   - Generalization Gap: {m1_gap:.1%}",
                f"",
                f"2. {m2} (SVM):",
                f"   - Training Accuracy: {m2_train:.1%}",
                f"   - Test Accuracy: {m2_test:.1%}",
                f"   - Generalization Gap: {m2_gap:.1%}",
                f"",
                f"Analysis:",
                f"- Best Test Performance: {report['best_model']} ({max(m1_test, m2_test):.1%})",
                f"- Better Generalization: {report['comparison']['better_generalizer']} (smaller gap)",
            ]
            
            if m1_test > m2_test:
                summary_lines.append(f"- {m1} outperforms {m2} on test data by {abs(m1_test - m2_test):.1%}")
            else:
                summary_lines.append(f"- {m2} outperforms {m1} on test data by {abs(m1_test - m2_test):.1%}")
            
            report["summary"] = "\n".join(summary_lines)
        
        return report
    
    def print_training_progress(self) -> None:
        """Print training progress for all models."""
        print("\n" + "=" * 70)
        print("TRAINING PROGRESS")
        print("=" * 70)
        
        for name, result in self.training_results.items():
            print(f"\n{name}:")
            print("-" * 50)
            print(f"{'Epoch':<8} {'Train Loss':<12} {'Train Acc':<12} {'Val Loss':<12} {'Val Acc':<12}")
            print("-" * 50)
            
            for epoch_data in result["training_history"]:
                val_loss = epoch_data.get("val_loss")
                val_acc = epoch_data.get("val_accuracy")
                
                val_loss_str = f"{val_loss:.4f}" if val_loss is not None else "N/A"
                val_acc_str = f"{val_acc:.4f}" if val_acc is not None else "N/A"
                
                print(f"{epoch_data['epoch']:<8} {epoch_data['train_loss']:<12.4f} "
                      f"{epoch_data['train_accuracy']:<12.4f} {val_loss_str:<12} {val_acc_str:<12}")


class MLPipeline:
    """
    Complete ML pipeline for misinformation detection.
    """
    
    def __init__(
        self,
        config: Optional[TrainingConfig] = None,
        feature_extractor: Optional[FeatureExtractor] = None
    ):
        self.config = config or TrainingConfig()
        self.feature_extractor = feature_extractor or FeatureExtractor()
        self.trainer: Optional[ModelTrainer] = None
        self.comparison_report: Optional[dict] = None
    
    def train_and_compare(
        self,
        dataset_builder: DatasetBuilder,
        verbose: bool = True
    ) -> dict:
        """
        Train both Logistic Regression and SVM, then compare results.
        """
        # Get data
        X = dataset_builder.get_feature_matrix()
        y = dataset_builder.get_labels()
        feature_names = self.feature_extractor.get_feature_names()
        
        # Split data
        random.seed(self.config.random_seed)
        indices = list(range(len(X)))
        random.shuffle(indices)
        
        val_size = int(len(indices) * self.config.validation_split)
        test_size = int(len(indices) * 0.2)  # 20% for test
        
        # Train/Val/Test split
        test_indices = indices[:test_size]
        val_indices = indices[test_size:test_size + val_size]
        train_indices = indices[test_size + val_size:]
        
        X_train = [X[i] for i in train_indices]
        y_train = [y[i] for i in train_indices]
        X_val = [X[i] for i in val_indices]
        y_val = [y[i] for i in val_indices]
        X_test = [X[i] for i in test_indices]
        y_test = [y[i] for i in test_indices]
        
        if verbose:
            print(f"\n📊 Data Split:")
            print(f"   Training samples: {len(X_train)}")
            print(f"   Validation samples: {len(X_val)}")
            print(f"   Test samples: {len(X_test)}")
        
        # Create trainer and add models
        self.trainer = ModelTrainer(self.config)
        
        # Add Logistic Regression
        lr_model = LogisticRegressionModel(self.config)
        self.trainer.add_model("Logistic Regression", lr_model)
        
        # Add SVM
        svm_model = SVMModel(self.config)
        self.trainer.add_model("SVM", svm_model)
        
        # Train all models
        if verbose:
            print(f"\n🔄 Training models for {self.config.num_epochs} epochs...")
        
        training_results = self.trainer.train_all(
            X_train, y_train,
            X_val, y_val,
            feature_names
        )
        
        if verbose:
            self.trainer.print_training_progress()
        
        # Evaluate on test data
        if verbose:
            print(f"\n📈 Evaluating on test data...")
        
        evaluation_results = self.trainer.evaluate_all(X_test, y_test)
        
        # Generate comparison report
        self.comparison_report = self.trainer.get_comparison_report()
        
        if verbose:
            self._print_comparison_results()
        
        return {
            "training_results": training_results,
            "evaluation_results": {k: v.to_dict() for k, v in evaluation_results.items()},
            "comparison_report": self.comparison_report
        }
    
    def _print_comparison_results(self) -> None:
        """Print formatted comparison results."""
        print("\n" + "=" * 70)
        print("MODEL COMPARISON RESULTS")
        print("=" * 70)
        
        for name, model_data in self.comparison_report["models"].items():
            print(f"\n{name}:")
            print("-" * 50)
            
            train_data = model_data["training"]
            test_data = model_data["test_evaluation"]
            
            print(f"  Training Performance:")
            print(f"    - Final Accuracy: {train_data['final_train_accuracy']:.1%}")
            if train_data.get("final_val_accuracy"):
                print(f"    - Validation Accuracy: {train_data['final_val_accuracy']:.1%}")
            
            print(f"\n  Test Performance:")
            print(f"    - Accuracy: {test_data['accuracy']:.1%}")
            print(f"    - Precision: {test_data['precision']:.1%}")
            print(f"    - Recall: {test_data['recall']:.1%}")
            print(f"    - F1 Score: {test_data['f1_score']:.1%}")
            print(f"    - AUC-ROC: {test_data['auc_roc']:.1%}")
            
            cm = test_data["confusion_matrix"]
            print(f"\n  Confusion Matrix:")
            print(f"    TP: {cm['true_positives']}, TN: {cm['true_negatives']}")
            print(f"    FP: {cm['false_positives']}, FN: {cm['false_negatives']}")
            
            # Top features
            print(f"\n  Top 5 Features:")
            for feat in model_data["feature_importance"][:5]:
                direction = "↑" if feat["weight"] > 0 else "↓"
                print(f"    {direction} {feat['feature']}: {abs(feat['weight']):.4f}")
        
        print("\n" + "=" * 70)
        print("ANALYSIS")
        print("=" * 70)
        print(self.comparison_report["summary"])
    
    def save_results(self, output_dir: str) -> dict:
        """Save all results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comparison report
        report_path = output_path / f"model_comparison_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(self.comparison_report, f, indent=2, default=str)
        
        # Save training history
        history_path = output_path / f"training_history_{timestamp}.json"
        with open(history_path, 'w') as f:
            json.dump(self.trainer.training_results, f, indent=2, default=str)
        
        return {
            "comparison_report": str(report_path),
            "training_history": str(history_path)
        }
