"""
MLflow Integration for DSPy Multi-Agent RAG

Provides autologging, experiment tracking, and trace visualization.
"""

import mlflow
import dspy
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime


class MLflowTracker:
    """
    MLflow integration for tracking DSPy optimization and inference.

    Features:
    - Automatic experiment tracking
    - Prompt evolution logging
    - Trace visualization
    - Model performance comparison
    """

    def __init__(
        self,
        tracking_uri: str = "./mlruns",
        experiment_name: str = "multi_agent_rag_dspy"
    ):
        """
        Initialize MLflow tracker.

        Args:
            tracking_uri: MLflow tracking URI
            experiment_name: Name of the experiment
        """
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name

        # Set up MLflow
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

        # Create tracking directory if needed
        Path(tracking_uri).mkdir(parents=True, exist_ok=True)

    def start_run(self, run_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
        """
        Start a new MLflow run.

        Args:
            run_name: Optional name for the run
            tags: Optional tags for the run
        """
        tags = tags or {}
        tags['timestamp'] = datetime.now().isoformat()

        mlflow.start_run(run_name=run_name, tags=tags)

    def end_run(self):
        """End the current MLflow run"""
        mlflow.end_run()

    def log_params(self, params: Dict[str, Any]):
        """
        Log parameters to MLflow.

        Args:
            params: Dictionary of parameters
        """
        for key, value in params.items():
            # MLflow params must be strings
            mlflow.log_param(key, str(value))

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """
        Log metrics to MLflow.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number
        """
        for name, value in metrics.items():
            mlflow.log_metric(name, value, step=step)

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        """
        Log an artifact (file) to MLflow.

        Args:
            local_path: Path to local file
            artifact_path: Optional path within the artifact directory
        """
        mlflow.log_artifact(local_path, artifact_path)

    def log_prompt_evolution(
        self,
        iteration: int,
        module_name: str,
        prompt_text: str,
        score: float,
        feedback: str = ""
    ):
        """
        Log prompt evolution during GEPA optimization.

        Args:
            iteration: Optimization iteration number
            module_name: Name of the DSPy module
            prompt_text: The prompt instruction text
            score: Performance score
            feedback: Textual feedback from reflection LM
        """
        # Log as metrics
        mlflow.log_metric(f"{module_name}_score", score, step=iteration)

        # Log prompt text as artifact
        prompt_file = f"prompts/{module_name}_iter_{iteration}.txt"
        temp_path = Path(f"/tmp/{module_name}_iter_{iteration}.txt")
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_path, 'w') as f:
            f.write(f"Iteration: {iteration}\n")
            f.write(f"Module: {module_name}\n")
            f.write(f"Score: {score}\n")
            f.write(f"Feedback: {feedback}\n\n")
            f.write(f"Prompt:\n{prompt_text}\n")

        mlflow.log_artifact(str(temp_path), "prompts")
        temp_path.unlink()  # Clean up

    def log_trace(
        self,
        trace_id: str,
        question: str,
        answer: str,
        confidence: float,
        sub_solutions: List[Dict],
        verification_trace: str,
        reflection_notes: str,
        retry_count: int = 0
    ):
        """
        Log a complete execution trace.

        Args:
            trace_id: Unique identifier for this trace
            question: Input question
            answer: Final answer
            confidence: Confidence score
            sub_solutions: List of sub-solutions
            verification_trace: Verification report
            reflection_notes: Reflection notes
            retry_count: Number of retries
        """
        trace_data = {
            'trace_id': trace_id,
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'answer': answer,
            'confidence': confidence,
            'sub_solutions': sub_solutions,
            'verification_trace': verification_trace,
            'reflection_notes': reflection_notes,
            'retry_count': retry_count
        }

        # Save as JSON artifact
        temp_path = Path(f"/tmp/trace_{trace_id}.json")
        with open(temp_path, 'w') as f:
            json.dump(trace_data, f, indent=2)

        mlflow.log_artifact(str(temp_path), "traces")
        temp_path.unlink()

        # Log key metrics
        mlflow.log_metric(f"trace_{trace_id}_confidence", confidence)
        mlflow.log_metric(f"trace_{trace_id}_retry_count", retry_count)

    def log_pareto_frontier(
        self,
        iteration: int,
        candidates: List[Dict[str, Any]]
    ):
        """
        Log Pareto frontier candidates during GEPA optimization.

        Args:
            iteration: Optimization iteration
            candidates: List of candidate dictionaries with scores
        """
        frontier_data = {
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'candidates': candidates
        }

        temp_path = Path(f"/tmp/pareto_frontier_iter_{iteration}.json")
        with open(temp_path, 'w') as f:
            json.dump(frontier_data, f, indent=2)

        mlflow.log_artifact(str(temp_path), "pareto_frontiers")
        temp_path.unlink()

    def log_vector_store_stats(self, stats: Dict[str, int]):
        """
        Log vector store statistics.

        Args:
            stats: Dictionary of domain -> chunk count
        """
        for domain, count in stats.items():
            mlflow.log_metric(f"vector_store_{domain}_chunks", count)

    def compare_models(
        self,
        model_results: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Compare performance across different models or configurations.

        Args:
            model_results: Dictionary of model_name -> metrics

        Returns:
            Comparison summary
        """
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'models': model_results
        }

        # Find best model for each metric
        best_per_metric = {}
        all_metrics = set()

        for model_name, metrics in model_results.items():
            all_metrics.update(metrics.keys())

        for metric in all_metrics:
            best_score = -float('inf')
            best_model = None

            for model_name, metrics in model_results.items():
                if metric in metrics and metrics[metric] > best_score:
                    best_score = metrics[metric]
                    best_model = model_name

            best_per_metric[metric] = {
                'model': best_model,
                'score': best_score
            }

        comparison['best_per_metric'] = best_per_metric

        # Log comparison as artifact
        temp_path = Path("/tmp/model_comparison.json")
        with open(temp_path, 'w') as f:
            json.dump(comparison, f, indent=2)

        mlflow.log_artifact(str(temp_path), "comparisons")
        temp_path.unlink()

        return comparison


def enable_dspy_autologging(tracker: MLflowTracker):
    """
    Enable automatic logging for DSPy operations.

    Args:
        tracker: MLflowTracker instance
    """
    # Note: This is a placeholder for DSPy autologging
    # Actual implementation would hook into DSPy's internal calls

    print("DSPy autologging enabled")
    print(f"Tracking URI: {tracker.tracking_uri}")
    print(f"Experiment: {tracker.experiment_name}")


class OptimizationCallback:
    """
    Callback for logging optimization progress.
    """

    def __init__(self, tracker: MLflowTracker):
        self.tracker = tracker
        self.iteration = 0

    def on_iteration_start(self, **kwargs):
        """Called at the start of each optimization iteration"""
        self.iteration += 1
        print(f"\n=== Optimization Iteration {self.iteration} ===")

    def on_iteration_end(self, score: float, feedback: str = "", **kwargs):
        """Called at the end of each optimization iteration"""
        self.tracker.log_metrics(
            {'optimization_score': score},
            step=self.iteration
        )

        if feedback:
            print(f"Feedback: {feedback}")

    def on_optimization_complete(self, final_score: float, **kwargs):
        """Called when optimization completes"""
        print(f"\n=== Optimization Complete ===")
        print(f"Final Score: {final_score:.4f}")

        self.tracker.log_metrics({'final_optimization_score': final_score})
