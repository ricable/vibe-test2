"""
Lead Agent: Multi-Agent Orchestrator

Coordinates specialized subagents and implements the high-level
decomposition and synthesis logic.
"""

import dspy
import json
from typing import List, Dict, Optional, Any
from ..signatures.meta_cognitive import (
    DecomposeSignature,
    SynthesizeSignature
)


class LeadAgent(dspy.Module):
    """
    Lead Agent for multi-agent orchestration.

    Responsibilities:
    1. Decompose complex questions into sub-problems
    2. Route sub-problems to appropriate subagents
    3. Synthesize sub-answers into coherent final answer
    """

    def __init__(
        self,
        subagents: Dict[str, Any],
        confidence_threshold: float = 0.8
    ):
        """
        Initialize LeadAgent.

        Args:
            subagents: Dictionary mapping domain names to DomainSubagent instances
            confidence_threshold: Minimum confidence for accepting synthesis
        """
        super().__init__()

        self.subagents = subagents
        self.confidence_threshold = confidence_threshold

        # DSPy modules
        self.decompose = dspy.ChainOfThought(DecomposeSignature)
        self.synthesize = dspy.ChainOfThought(SynthesizeSignature)

    def _route_subproblem(self, sub_problem: str) -> Optional[str]:
        """
        Determine which subagent should handle a sub-problem.

        Args:
            sub_problem: The sub-problem text

        Returns:
            Domain name or None if no specific domain
        """
        # Simple keyword-based routing (can be replaced with ML-based routing)
        sub_problem_lower = sub_problem.lower()

        for domain in self.subagents.keys():
            if domain.lower() in sub_problem_lower:
                return domain

        # Default: return first available domain or None
        return list(self.subagents.keys())[0] if self.subagents else None

    def forward(
        self,
        question: str,
        context: str = ""
    ) -> dspy.Prediction:
        """
        Execute multi-agent reasoning pipeline.

        Args:
            question: Complex question to answer
            context: Optional background context

        Returns:
            dspy.Prediction with final answer and metadata
        """
        # Step 1: Decompose question into sub-problems
        decompose_result = self.decompose(
            question=question,
            context=context
        )

        sub_problems = decompose_result.sub_problems
        decompose_reasoning = decompose_result.reasoning

        # Step 2: Route and solve sub-problems
        sub_solutions = []

        for i, sub_problem in enumerate(sub_problems):
            # Route to appropriate subagent
            domain = self._route_subproblem(sub_problem)

            if domain and domain in self.subagents:
                subagent = self.subagents[domain]
                solution = subagent(sub_problem)

                sub_solutions.append({
                    'sub_problem_id': f'sp_{i}',
                    'sub_problem': sub_problem,
                    'domain': domain,
                    'answer': solution.answer,
                    'confidence': solution.confidence,
                    'sources': solution.sources,
                    'reasoning': solution.reasoning_trace
                })
            else:
                # No appropriate subagent - record as unsolved
                sub_solutions.append({
                    'sub_problem_id': f'sp_{i}',
                    'sub_problem': sub_problem,
                    'domain': 'unknown',
                    'answer': 'Unable to find appropriate specialist for this question.',
                    'confidence': 0.1,
                    'sources': '',
                    'reasoning': 'No subagent available for this domain'
                })

        # Step 3: Synthesize sub-solutions
        verified_solutions_json = json.dumps(sub_solutions, indent=2)

        # For now, use a simple verification placeholder
        # (Full verification will be added in meta_cognitive_agent.py)
        verification_result = "Basic validation: All subagents returned responses."

        synthesis = self.synthesize(
            question=question,
            verified_solutions=verified_solutions_json,
            verification_result=verification_result
        )

        # Extract synthesis results
        clear_answer = synthesis.clear_answer
        confidence_level = synthesis.confidence_level
        key_caveats = synthesis.key_caveats

        return dspy.Prediction(
            answer=clear_answer,
            confidence=confidence_level,
            caveats=key_caveats,
            sub_solutions=sub_solutions,
            decompose_reasoning=decompose_reasoning,
            synthesis_confidence=confidence_level
        )

    def __call__(self, question: str, context: str = "") -> dspy.Prediction:
        """Callable interface"""
        return self.forward(question, context)
