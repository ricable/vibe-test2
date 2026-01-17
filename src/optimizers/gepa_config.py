"""
GEPA (Genetic-Pareto) Optimizer Configuration

Implements configuration for the two-model optimization architecture:
- Student model: Fast, cost-efficient execution
- Reflection model: High-intelligence failure analysis
"""

import dspy
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class GEPAConfig:
    """
    Configuration for GEPA optimizer.

    Attributes:
        student_model: Fast model for execution (e.g., 'gpt-4o-mini')
        reflection_model: Smart model for reflection (e.g., 'gpt-4o')
        num_iterations: Number of optimization iterations
        population_size: Size of candidate population
        pareto_frontier_size: Number of candidates in Pareto frontier
        enable_tool_optimization: Whether to optimize tool descriptions
        metrics: List of metric names to optimize
    """
    student_model: str = "gpt-4o-mini"
    reflection_model: str = "gpt-4o"
    num_iterations: int = 10
    population_size: int = 20
    pareto_frontier_size: int = 5
    enable_tool_optimization: bool = True
    metrics: List[str] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = ['accuracy', 'groundedness', 'completeness']


def create_gepa_optimizer(
    config: GEPAConfig,
    trainset: List[dspy.Example],
    metric: Callable,
    valset: Optional[List[dspy.Example]] = None
) -> dspy.teleprompt.MIPRO:  # Or the actual GEPA class when available
    """
    Create and configure a GEPA optimizer.

    Note: As of DSPy 2.5, GEPA is typically accessed through MIPRO or
    custom implementations. This function provides a template for
    GEPA-style optimization.

    Args:
        config: GEPA configuration
        trainset: Training examples
        metric: Evaluation metric function
        valset: Optional validation set

    Returns:
        Configured optimizer instance
    """
    # Configure student LM
    student_lm = dspy.OpenAI(
        model=config.student_model,
        max_tokens=2000,
        temperature=0.7
    )

    # Configure reflection LM (for failure analysis)
    reflection_lm = dspy.OpenAI(
        model=config.reflection_model,
        max_tokens=4000,
        temperature=0.8
    )

    # For now, use MIPRO as the base optimizer
    # MIPRO implements Pareto frontier optimization similar to GEPA
    optimizer = dspy.teleprompt.MIPRO(
        metric=metric,
        num_candidates=config.population_size,
        init_temperature=1.0,
        verbose=True
    )

    return optimizer


class GEPAFeedbackMetric:
    """
    Rich feedback metric for GEPA optimization.

    Instead of just returning a score, this metric provides textual
    feedback that the reflection LM can use to propose instruction improvements.
    """

    def __init__(
        self,
        name: str,
        weight: float = 1.0,
        feedback_template: Optional[str] = None
    ):
        """
        Initialize GEPAFeedbackMetric.

        Args:
            name: Metric name (e.g., 'groundedness', 'completeness')
            weight: Weight in multi-objective optimization
            feedback_template: Template for generating feedback
        """
        self.name = name
        self.weight = weight
        self.feedback_template = feedback_template or self._default_template()

    def _default_template(self) -> str:
        """Default feedback template"""
        return (
            f"Evaluating {self.name}:\n"
            "Score: {score}\n"
            "Feedback: {feedback}\n"
            "Suggested improvements: {suggestions}"
        )

    def evaluate(
        self,
        example: dspy.Example,
        prediction: dspy.Prediction,
        trace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate and provide rich feedback.

        Args:
            example: Ground truth example
            prediction: Model prediction
            trace: Optional execution trace

        Returns:
            Dictionary with score and feedback
        """
        raise NotImplementedError("Subclasses must implement evaluate()")


class GroundednessMetric(GEPAFeedbackMetric):
    """
    Metric for evaluating whether answers are grounded in retrieved context.
    """

    def __init__(self, weight: float = 1.0):
        super().__init__(name="groundedness", weight=weight)

    def evaluate(
        self,
        example: dspy.Example,
        prediction: dspy.Prediction,
        trace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate groundedness of the answer.

        Args:
            example: Ground truth example
            prediction: Model prediction
            trace: Execution trace

        Returns:
            Score and feedback
        """
        # Simple heuristic: check if answer references sources
        answer = prediction.get('answer', '')
        sources = prediction.get('sources', '')

        # Basic checks
        has_sources = len(sources) > 0
        reasonable_length = 50 < len(answer) < 2000

        # Calculate score
        score = 0.0
        feedback_items = []

        if has_sources:
            score += 0.5
        else:
            feedback_items.append("No sources cited")

        if reasonable_length:
            score += 0.3
        else:
            feedback_items.append(f"Answer length {len(answer)} is unusual")

        # Check for hedging language (indicates uncertainty)
        hedging_phrases = ['might', 'could', 'possibly', 'perhaps', 'unclear']
        hedging_count = sum(1 for phrase in hedging_phrases if phrase in answer.lower())

        if hedging_count <= 2:
            score += 0.2
        else:
            feedback_items.append(f"Excessive hedging ({hedging_count} instances)")

        feedback = "; ".join(feedback_items) if feedback_items else "Well-grounded answer"

        return {
            'score': score,
            'feedback': feedback,
            'metric_name': self.name,
            'weight': self.weight
        }


class CompletenessMetric(GEPAFeedbackMetric):
    """
    Metric for evaluating whether all sub-problems were addressed.
    """

    def __init__(self, weight: float = 1.0):
        super().__init__(name="completeness", weight=weight)

    def evaluate(
        self,
        example: dspy.Example,
        prediction: dspy.Prediction,
        trace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate completeness of the answer.

        Args:
            example: Ground truth example
            prediction: Model prediction
            trace: Execution trace

        Returns:
            Score and feedback
        """
        answer = prediction.get('answer', '')
        sub_solutions = prediction.get('sub_solutions', [])

        score = 0.0
        feedback_items = []

        # Check if we have sub-solutions
        if len(sub_solutions) > 0:
            score += 0.4

            # Check confidence of sub-solutions
            confidences = [s.get('confidence', 0.0) for s in sub_solutions]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            if avg_confidence > 0.7:
                score += 0.3
            else:
                feedback_items.append(f"Low average sub-solution confidence: {avg_confidence:.2f}")

            # Check if all sub-solutions have answers
            answered = sum(1 for s in sub_solutions if len(s.get('answer', '')) > 10)
            if answered == len(sub_solutions):
                score += 0.3
            else:
                feedback_items.append(f"Only {answered}/{len(sub_solutions)} sub-problems answered")
        else:
            feedback_items.append("No decomposition into sub-problems")
            score = 0.2  # Can still be complete without explicit decomposition

        feedback = "; ".join(feedback_items) if feedback_items else "Complete answer"

        return {
            'score': score,
            'feedback': feedback,
            'metric_name': self.name,
            'weight': self.weight
        }


class ConfidenceAccuracyMetric(GEPAFeedbackMetric):
    """
    Metric for correlating confidence scores with factual accuracy.
    """

    def __init__(self, weight: float = 0.8):
        super().__init__(name="confidence_accuracy", weight=weight)

    def evaluate(
        self,
        example: dspy.Example,
        prediction: dspy.Prediction,
        trace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate confidence calibration.

        Args:
            example: Ground truth example
            prediction: Model prediction
            trace: Execution trace

        Returns:
            Score and feedback
        """
        confidence = prediction.get('confidence', 0.5)
        answer = prediction.get('answer', '')

        # Check if ground truth is available
        if hasattr(example, 'answer'):
            ground_truth = example.answer

            # Simple string similarity
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, answer.lower(), ground_truth.lower()).ratio()

            # Confidence should match accuracy
            calibration_error = abs(confidence - similarity)

            score = max(0.0, 1.0 - calibration_error)
            feedback = f"Confidence {confidence:.2f} vs. similarity {similarity:.2f}"

            if calibration_error > 0.3:
                feedback += " - poorly calibrated"
        else:
            # No ground truth - just check if confidence is reasonable
            if 0.3 <= confidence <= 0.95:
                score = 0.7
                feedback = "Confidence in reasonable range"
            else:
                score = 0.4
                feedback = f"Confidence {confidence:.2f} may be too extreme"

        return {
            'score': score,
            'feedback': feedback,
            'metric_name': self.name,
            'weight': self.weight
        }


def create_composite_metric(metrics: List[GEPAFeedbackMetric]) -> Callable:
    """
    Create a composite metric from multiple feedback metrics.

    Args:
        metrics: List of GEPAFeedbackMetric instances

    Returns:
        Callable metric function for DSPy
    """
    def composite_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
        """
        Composite metric that combines multiple feedback metrics.

        Args:
            example: Ground truth example
            prediction: Model prediction
            trace: Optional execution trace

        Returns:
            Weighted average score
        """
        total_weight = sum(m.weight for m in metrics)
        weighted_score = 0.0

        feedback_parts = []

        for metric in metrics:
            result = metric.evaluate(example, prediction, trace)
            score = result['score']
            feedback = result['feedback']

            weighted_score += score * metric.weight
            feedback_parts.append(f"[{metric.name}] {feedback}")

        # Print feedback for GEPA reflection
        print("\n=== GEPA Feedback ===")
        for fb in feedback_parts:
            print(fb)
        print(f"Composite Score: {weighted_score / total_weight:.3f}\n")

        return weighted_score / total_weight

    return composite_metric
