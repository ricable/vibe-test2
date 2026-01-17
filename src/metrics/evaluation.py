"""
Evaluation metrics for multi-agent RAG systems
"""

import dspy
from typing import List, Dict, Any, Callable
from difflib import SequenceMatcher


class AccuracyMetric:
    """
    Basic accuracy metric for evaluating predictions.
    """

    @staticmethod
    def exact_match(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
        """Exact match accuracy"""
        if not hasattr(example, 'answer'):
            return 0.0

        pred_answer = prediction.get('answer', '').strip().lower()
        true_answer = example.answer.strip().lower()

        return 1.0 if pred_answer == true_answer else 0.0

    @staticmethod
    def fuzzy_match(example: dspy.Example, prediction: dspy.Prediction, trace=None, threshold: float = 0.8) -> float:
        """Fuzzy string matching accuracy"""
        if not hasattr(example, 'answer'):
            return 0.0

        pred_answer = prediction.get('answer', '').strip().lower()
        true_answer = example.answer.strip().lower()

        similarity = SequenceMatcher(None, pred_answer, true_answer).ratio()

        return 1.0 if similarity >= threshold else 0.0

    @staticmethod
    def contains_answer(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
        """Check if answer contains the key information"""
        if not hasattr(example, 'answer'):
            return 0.0

        pred_answer = prediction.get('answer', '').strip().lower()
        true_answer = example.answer.strip().lower()

        # Check if prediction contains the ground truth
        return 1.0 if true_answer in pred_answer else 0.0


class ConfidenceMetric:
    """
    Metrics related to confidence calibration.
    """

    @staticmethod
    def confidence_threshold(example: dspy.Example, prediction: dspy.Prediction, trace=None, threshold: float = 0.8) -> float:
        """Check if confidence meets threshold"""
        confidence = prediction.get('confidence', 0.0)
        return 1.0 if confidence >= threshold else 0.0

    @staticmethod
    def confidence_calibration(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
        """
        Evaluate how well confidence matches actual accuracy.

        Returns 1.0 - calibration_error
        """
        if not hasattr(example, 'answer'):
            return 0.5

        confidence = prediction.get('confidence', 0.5)
        pred_answer = prediction.get('answer', '').strip().lower()
        true_answer = example.answer.strip().lower()

        # Compute actual accuracy (similarity)
        similarity = SequenceMatcher(None, pred_answer, true_answer).ratio()

        # Calibration error
        calibration_error = abs(confidence - similarity)

        return max(0.0, 1.0 - calibration_error)


class MetaCognitiveMetric:
    """
    Metrics specific to meta-cognitive reasoning.
    """

    @staticmethod
    def decomposition_quality(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
        """
        Evaluate quality of decomposition into sub-problems.

        Checks:
        - Are there sub-problems?
        - Are they specific and actionable?
        - Are they comprehensive?
        """
        decompose_reasoning = prediction.get('decompose_reasoning', '')
        sub_solutions = prediction.get('sub_solutions', [])

        score = 0.0

        # Check if decomposition occurred
        if len(sub_solutions) > 0:
            score += 0.3

            # Check diversity of domains
            domains = set(s.get('domain', 'unknown') for s in sub_solutions)
            if len(domains) > 1:
                score += 0.2

            # Check if sub-problems are well-formed
            well_formed = sum(
                1 for s in sub_solutions
                if len(s.get('sub_problem', '')) > 10
            )

            if well_formed == len(sub_solutions):
                score += 0.3

            # Check average confidence
            confidences = [s.get('confidence', 0.0) for s in sub_solutions]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            if avg_conf > 0.6:
                score += 0.2
        else:
            # No decomposition - check if it was needed
            question = example.get('question', '')
            if len(question.split()) < 15:  # Simple question
                score = 0.5  # OK to not decompose
            else:
                score = 0.1  # Should have decomposed

        return score

    @staticmethod
    def reflection_quality(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
        """
        Evaluate quality of reflection and self-correction.

        Checks:
        - Is there reflection content?
        - Did the system identify weaknesses?
        - Is confidence calibrated?
        """
        reflection_notes = prediction.get('reflection_notes', '')
        retry_count = prediction.get('retry_count', 0)
        confidence = prediction.get('confidence', 0.0)

        score = 0.0

        # Check if reflection occurred
        if len(reflection_notes) > 20:
            score += 0.3

            # Check if weaknesses were identified
            if 'weakness' in reflection_notes.lower() or 'issue' in reflection_notes.lower():
                score += 0.2

            # Check if retry logic was used appropriately
            if retry_count > 0 and confidence > 0.7:
                score += 0.3  # Successfully improved through retry
            elif retry_count == 0 and confidence > 0.8:
                score += 0.2  # No retry needed, high confidence

        return score


def create_evaluation_suite(
    include_accuracy: bool = True,
    include_confidence: bool = True,
    include_metacognitive: bool = True,
    custom_metrics: List[Callable] = None
) -> Dict[str, Callable]:
    """
    Create a suite of evaluation metrics.

    Args:
        include_accuracy: Include accuracy-based metrics
        include_confidence: Include confidence-based metrics
        include_metacognitive: Include meta-cognitive metrics
        custom_metrics: Additional custom metrics

    Returns:
        Dictionary of metric name -> metric function
    """
    metrics = {}

    if include_accuracy:
        metrics['exact_match'] = AccuracyMetric.exact_match
        metrics['fuzzy_match'] = AccuracyMetric.fuzzy_match
        metrics['contains_answer'] = AccuracyMetric.contains_answer

    if include_confidence:
        metrics['confidence_threshold'] = ConfidenceMetric.confidence_threshold
        metrics['confidence_calibration'] = ConfidenceMetric.confidence_calibration

    if include_metacognitive:
        metrics['decomposition_quality'] = MetaCognitiveMetric.decomposition_quality
        metrics['reflection_quality'] = MetaCognitiveMetric.reflection_quality

    if custom_metrics:
        for i, metric in enumerate(custom_metrics):
            metrics[f'custom_{i}'] = metric

    return metrics


def evaluate_predictions(
    predictions: List[dspy.Prediction],
    examples: List[dspy.Example],
    metrics: Dict[str, Callable]
) -> Dict[str, float]:
    """
    Evaluate a set of predictions against examples using multiple metrics.

    Args:
        predictions: List of predictions
        examples: List of ground truth examples
        metrics: Dictionary of metrics to compute

    Returns:
        Dictionary of metric name -> average score
    """
    if len(predictions) != len(examples):
        raise ValueError("Number of predictions must match number of examples")

    results = {name: [] for name in metrics.keys()}

    for pred, example in zip(predictions, examples):
        for name, metric_fn in metrics.items():
            score = metric_fn(example, pred)
            results[name].append(score)

    # Compute averages
    avg_results = {
        name: sum(scores) / len(scores) if scores else 0.0
        for name, scores in results.items()
    }

    return avg_results
