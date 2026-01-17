"""
Meta-Cognitive Reasoning Signatures

Implements the five-stage recursive reasoning framework:
1. Decompose: Break complex queries into sub-problems
2. Solve: Generate sub-answers with confidence scores
3. Verify: Logic, fact, and bias checking
4. Synthesize: Weighted combination of sub-results
5. Reflect: Self-monitoring and retry logic
"""

import dspy
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class SubProblem(BaseModel):
    """Represents a decomposed sub-problem"""
    id: str
    query: str
    domain: Optional[str] = None
    priority: float = 1.0


class SubSolution(BaseModel):
    """Represents a solution to a sub-problem"""
    sub_problem_id: str
    answer: str
    confidence: float
    sources: List[str] = Field(default_factory=list)
    reasoning: str = ""


class VerificationResult(BaseModel):
    """Results from the verification stage"""
    is_valid: bool
    logic_check: str
    fact_check: str
    bias_check: str
    issues_found: List[str] = Field(default_factory=list)
    corrections_needed: List[str] = Field(default_factory=list)


class MetaCognitiveOutput(BaseModel):
    """Final output of the meta-cognitive reasoning system"""
    clear_answer: str
    confidence_level: float
    key_caveats: List[str]
    sub_solutions: List[SubSolution] = Field(default_factory=list)
    verification_trace: str = ""
    reflection_notes: str = ""


# ===== Stage 1: Decompose =====

class DecomposeSignature(dspy.Signature):
    """
    Break down a complex question into manageable sub-problems.

    Each sub-problem should be:
    - Independent or minimally coupled
    - Specific and answerable
    - Mapped to a relevant domain if applicable
    """

    question: str = dspy.InputField(
        desc="Complex question requiring multi-step reasoning"
    )
    context: str = dspy.InputField(
        desc="Available context or background information",
        default=""
    )

    sub_problems: List[str] = dspy.OutputField(
        desc="List of decomposed sub-problems as clear, specific questions"
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of decomposition strategy"
    )


# ===== Stage 2: Solve =====

class SolveSignature(dspy.Signature):
    """
    Generate a solution for a specific sub-problem with confidence assessment.

    The solution should:
    - Directly answer the sub-problem
    - Be grounded in retrieved context
    - Include a calibrated confidence score
    """

    sub_problem: str = dspy.InputField(
        desc="Specific sub-problem to solve"
    )
    context: str = dspy.InputField(
        desc="Retrieved context relevant to this sub-problem"
    )
    previous_solutions: str = dspy.InputField(
        desc="Solutions to other sub-problems for reference",
        default=""
    )

    answer: str = dspy.OutputField(
        desc="Direct answer to the sub-problem"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score from 0.0 to 1.0"
    )
    reasoning: str = dspy.OutputField(
        desc="Step-by-step reasoning process"
    )
    sources: str = dspy.OutputField(
        desc="Comma-separated list of sources used"
    )


# ===== Stage 3: Verify =====

class VerifySignature(dspy.Signature):
    """
    Perform comprehensive verification of sub-solutions.

    Checks include:
    - Logic consistency across solutions
    - Factual grounding in context
    - Bias detection and mitigation
    """

    question: str = dspy.InputField(
        desc="Original complex question"
    )
    sub_solutions: str = dspy.InputField(
        desc="JSON-formatted list of sub-solutions with answers and confidence"
    )
    context: str = dspy.InputField(
        desc="All retrieved context used"
    )

    logic_check: str = dspy.OutputField(
        desc="Assessment of logical consistency and reasoning validity"
    )
    fact_check: str = dspy.OutputField(
        desc="Verification of factual claims against context"
    )
    bias_check: str = dspy.OutputField(
        desc="Identification of potential biases or hidden assumptions"
    )
    issues_found: List[str] = dspy.OutputField(
        desc="List of specific issues or weaknesses identified"
    )
    is_valid: bool = dspy.OutputField(
        desc="Overall validation result: True if solutions are reliable"
    )


# ===== Stage 4: Synthesize =====

class SynthesizeSignature(dspy.Signature):
    """
    Synthesize verified sub-solutions into a coherent final answer.

    The synthesis should:
    - Weight solutions by confidence
    - Resolve contradictions
    - Present a clear, fluid narrative
    """

    question: str = dspy.InputField(
        desc="Original complex question"
    )
    verified_solutions: str = dspy.InputField(
        desc="JSON-formatted verified sub-solutions"
    )
    verification_result: str = dspy.InputField(
        desc="Verification report from the Verify stage"
    )

    clear_answer: str = dspy.OutputField(
        desc="Synthesized final answer in clear, professional prose"
    )
    confidence_level: float = dspy.OutputField(
        desc="Overall confidence in the synthesis (0.0 to 1.0)"
    )
    key_caveats: List[str] = dspy.OutputField(
        desc="Important caveats, limitations, or warnings"
    )


# ===== Stage 5: Reflect =====

class ReflectSignature(dspy.Signature):
    """
    Meta-cognitive reflection on the reasoning process.

    Reflection includes:
    - Self-assessment of reasoning quality
    - Identification of weaknesses
    - Decision on whether to retry
    """

    question: str = dspy.InputField(
        desc="Original question"
    )
    synthesis: str = dspy.InputField(
        desc="The synthesized answer"
    )
    confidence: float = dspy.InputField(
        desc="Confidence score from synthesis"
    )
    verification_trace: str = dspy.InputField(
        desc="Full verification report"
    )

    quality_assessment: str = dspy.OutputField(
        desc="Assessment of reasoning quality and completeness"
    )
    weaknesses_identified: List[str] = dspy.OutputField(
        desc="Specific weaknesses or gaps in the reasoning"
    )
    should_retry: bool = dspy.OutputField(
        desc="Whether the system should retry with refinements"
    )
    retry_instructions: str = dspy.OutputField(
        desc="Specific instructions for retry if needed"
    )
    final_confidence: float = dspy.OutputField(
        desc="Adjusted confidence after reflection"
    )
