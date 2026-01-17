"""
Meta-Cognitive Reasoning Agent

Implements the complete five-stage recursive meta-cognitive framework:
1. Decompose
2. Solve (via subagents)
3. Verify
4. Synthesize
5. Reflect (with retry logic)
"""

import dspy
import json
from typing import List, Dict, Optional, Any
from ..signatures.meta_cognitive import (
    DecomposeSignature,
    SolveSignature,
    VerifySignature,
    SynthesizeSignature,
    ReflectSignature,
    MetaCognitiveOutput
)


class MetaCognitiveReasoningAgent(dspy.Module):
    """
    Complete meta-cognitive reasoning agent with recursive self-correction.

    This agent implements the full five-stage reasoning cycle and uses
    dspy.Suggest for confidence-based retry logic.
    """

    def __init__(
        self,
        subagents: Dict[str, Any],
        confidence_threshold: float = 0.8,
        max_retry_attempts: int = 3
    ):
        """
        Initialize MetaCognitiveReasoningAgent.

        Args:
            subagents: Dictionary mapping domain names to DomainSubagent instances
            confidence_threshold: Minimum confidence for accepting synthesis
            max_retry_attempts: Maximum number of retry attempts
        """
        super().__init__()

        self.subagents = subagents
        self.confidence_threshold = confidence_threshold
        self.max_retry_attempts = max_retry_attempts

        # Initialize DSPy modules for each stage
        self.decompose = dspy.ChainOfThought(DecomposeSignature)
        self.solve = dspy.ChainOfThought(SolveSignature)
        self.verify = dspy.ChainOfThought(VerifySignature)
        self.synthesize = dspy.ChainOfThought(SynthesizeSignature)
        self.reflect = dspy.ChainOfThought(ReflectSignature)

    def _route_subproblem(self, sub_problem: str) -> Optional[str]:
        """
        Determine which subagent should handle a sub-problem.

        Args:
            sub_problem: The sub-problem text

        Returns:
            Domain name or None
        """
        sub_problem_lower = sub_problem.lower()

        for domain in self.subagents.keys():
            if domain.lower() in sub_problem_lower:
                return domain

        # Default to first available
        return list(self.subagents.keys())[0] if self.subagents else None

    def forward(
        self,
        question: str,
        context: str = ""
    ) -> dspy.Prediction:
        """
        Execute the full meta-cognitive reasoning cycle.

        Args:
            question: Complex question requiring meta-cognitive reasoning
            context: Optional background context

        Returns:
            dspy.Prediction with MetaCognitiveOutput structure
        """
        retry_count = 0
        previous_synthesis = None
        previous_issues = []

        while retry_count <= self.max_retry_attempts:
            # ===== Stage 1: Decompose =====
            decompose_context = context
            if previous_issues:
                decompose_context += (
                    f"\n\nPrevious attempt failed. Issues to address: "
                    f"{', '.join(previous_issues)}"
                )

            decompose_result = self.decompose(
                question=question,
                context=decompose_context
            )

            sub_problems = decompose_result.sub_problems
            decompose_reasoning = decompose_result.reasoning

            # ===== Stage 2: Solve (via subagents) =====
            sub_solutions = []
            all_contexts = []

            for i, sub_problem in enumerate(sub_problems):
                domain = self._route_subproblem(sub_problem)

                if domain and domain in self.subagents:
                    subagent = self.subagents[domain]
                    solution = subagent(sub_problem)

                    sub_solution = {
                        'sub_problem_id': f'sp_{i}',
                        'sub_problem': sub_problem,
                        'domain': domain,
                        'answer': solution.answer,
                        'confidence': solution.confidence,
                        'sources': solution.sources,
                        'reasoning': solution.reasoning_trace
                    }
                    sub_solutions.append(sub_solution)

                    # Accumulate context for verification
                    all_contexts.append(solution.reasoning_trace)
                else:
                    # No appropriate subagent
                    sub_solution = {
                        'sub_problem_id': f'sp_{i}',
                        'sub_problem': sub_problem,
                        'domain': 'unknown',
                        'answer': 'No specialist available',
                        'confidence': 0.1,
                        'sources': '',
                        'reasoning': 'No subagent for this domain'
                    }
                    sub_solutions.append(sub_solution)

            # ===== Stage 3: Verify =====
            sub_solutions_json = json.dumps(sub_solutions, indent=2)
            all_context_str = "\n\n".join(all_contexts)

            verify_result = self.verify(
                question=question,
                sub_solutions=sub_solutions_json,
                context=all_context_str
            )

            logic_check = verify_result.logic_check
            fact_check = verify_result.fact_check
            bias_check = verify_result.bias_check
            issues_found = verify_result.issues_found
            is_valid = verify_result.is_valid

            verification_trace = (
                f"=== Verification Report ===\n"
                f"Logic Check: {logic_check}\n"
                f"Fact Check: {fact_check}\n"
                f"Bias Check: {bias_check}\n"
                f"Issues Found: {', '.join(issues_found) if issues_found else 'None'}\n"
                f"Valid: {is_valid}"
            )

            # ===== Stage 4: Synthesize =====
            synthesis = self.synthesize(
                question=question,
                verified_solutions=sub_solutions_json,
                verification_result=verification_trace
            )

            clear_answer = synthesis.clear_answer
            confidence_level = synthesis.confidence_level
            key_caveats = synthesis.key_caveats

            # ===== Stage 5: Reflect =====
            reflection = self.reflect(
                question=question,
                synthesis=clear_answer,
                confidence=confidence_level,
                verification_trace=verification_trace
            )

            quality_assessment = reflection.quality_assessment
            weaknesses_identified = reflection.weaknesses_identified
            should_retry = reflection.should_retry
            retry_instructions = reflection.retry_instructions
            final_confidence = reflection.final_confidence

            reflection_notes = (
                f"=== Reflection ===\n"
                f"Quality Assessment: {quality_assessment}\n"
                f"Weaknesses: {', '.join(weaknesses_identified) if weaknesses_identified else 'None'}\n"
                f"Final Confidence: {final_confidence:.3f}"
            )

            # ===== Recursive Self-Correction Logic =====
            # Use dspy.Suggest for backtracking if confidence is below threshold
            dspy.Suggest(
                final_confidence >= self.confidence_threshold,
                f"Confidence {final_confidence:.3f} is below threshold {self.confidence_threshold}. "
                f"Retry instructions: {retry_instructions}"
            )

            # If we reach here without backtracking, return the result
            return dspy.Prediction(
                answer=clear_answer,
                confidence=final_confidence,
                caveats=key_caveats,
                sub_solutions=sub_solutions,
                verification_trace=verification_trace,
                reflection_notes=reflection_notes,
                decompose_reasoning=decompose_reasoning,
                retry_count=retry_count
            )

            # Note: The code below is for manual retry logic if dspy.Suggest doesn't trigger
            # (in case backtracking is disabled)
            if should_retry and retry_count < self.max_retry_attempts:
                retry_count += 1
                previous_synthesis = clear_answer
                previous_issues = weaknesses_identified
                # Loop continues
            else:
                # Max retries reached or no retry needed
                break

        # Return final result (if max retries exceeded)
        return dspy.Prediction(
            answer=clear_answer,
            confidence=final_confidence,
            caveats=key_caveats + ["Max retry attempts reached"],
            sub_solutions=sub_solutions,
            verification_trace=verification_trace,
            reflection_notes=reflection_notes,
            decompose_reasoning=decompose_reasoning,
            retry_count=retry_count
        )

    def __call__(self, question: str, context: str = "") -> dspy.Prediction:
        """Callable interface"""
        return self.forward(question, context)
