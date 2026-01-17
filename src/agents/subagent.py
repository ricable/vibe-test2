"""
Domain-Specialized Subagent with ReAct Strategy

Implements a ReAct (Reasoning + Acting) agent that:
- Uses chain-of-thought reasoning
- Has access to domain-specific vector search tools
- Can be optimized with GEPA for both prompts and tool descriptions
"""

import dspy
from typing import List, Optional, Dict, Any
from ..tools.vector_search_tool import VectorSearchTool


class ReActSignature(dspy.Signature):
    """
    ReAct reasoning signature for subagents.

    Combines reasoning (thought) with action (tool use).
    """

    question: str = dspy.InputField(
        desc="Question to answer"
    )
    context: str = dspy.InputField(
        desc="Previously retrieved context or conversation history",
        default=""
    )
    tools_available: str = dspy.InputField(
        desc="Description of available tools",
        default=""
    )

    thought: str = dspy.OutputField(
        desc="Reasoning about what to do next"
    )
    action: str = dspy.OutputField(
        desc="Action to take: 'search', 'answer', or 'clarify'"
    )
    action_input: str = dspy.OutputField(
        desc="Input for the action (e.g., search query or final answer)"
    )


class AnswerSignature(dspy.Signature):
    """
    Generate final answer from accumulated context.
    """

    question: str = dspy.InputField(
        desc="Original question"
    )
    context: str = dspy.InputField(
        desc="All retrieved and processed context"
    )
    reasoning_trace: str = dspy.InputField(
        desc="Reasoning steps taken so far"
    )

    answer: str = dspy.OutputField(
        desc="Clear, concise answer to the question"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence in the answer (0.0 to 1.0)"
    )
    sources: str = dspy.OutputField(
        desc="Comma-separated list of sources used"
    )


class DomainSubagent(dspy.Module):
    """
    Domain-specialized subagent using ReAct strategy.

    This agent specializes in a specific domain (e.g., diabetes, COPD)
    and uses vector search to retrieve relevant information before
    generating answers.
    """

    def __init__(
        self,
        domain: str,
        vector_search_tool: VectorSearchTool,
        max_iterations: int = 3,
        model: Optional[str] = None
    ):
        """
        Initialize DomainSubagent.

        Args:
            domain: Domain specialization (e.g., 'diabetes', 'copd')
            vector_search_tool: Vector search tool for this domain
            max_iterations: Maximum ReAct iterations
            model: Optional specific model to use
        """
        super().__init__()

        self.domain = domain
        self.vector_search_tool = vector_search_tool
        self.max_iterations = max_iterations

        # DSPy modules
        self.react = dspy.ChainOfThought(ReActSignature)
        self.answer = dspy.ChainOfThought(AnswerSignature)

        # Track optimization history
        self.optimization_history = []

    def forward(self, question: str) -> dspy.Prediction:
        """
        Execute ReAct loop to answer a domain-specific question.

        Args:
            question: Question to answer

        Returns:
            dspy.Prediction with answer, confidence, sources, and reasoning_trace
        """
        context_accumulated = []
        reasoning_trace = []
        iterations = 0

        # Get tool description
        tools_desc = self.vector_search_tool.description

        while iterations < self.max_iterations:
            iterations += 1

            # ReAct step
            context_str = "\n\n".join(context_accumulated) if context_accumulated else ""
            react_result = self.react(
                question=question,
                context=context_str,
                tools_available=tools_desc
            )

            thought = react_result.thought
            action = react_result.action.lower().strip()
            action_input = react_result.action_input

            # Track reasoning
            reasoning_trace.append(
                f"[Iteration {iterations}]\n"
                f"Thought: {thought}\n"
                f"Action: {action}\n"
                f"Input: {action_input}"
            )

            # Execute action
            if action == 'search':
                # Use vector search tool
                search_results = self.vector_search_tool(action_input)
                context_accumulated.append(
                    f"[Search Results for '{action_input}']\n{search_results}"
                )
                reasoning_trace.append(f"Retrieved: {len(search_results)} chars of context")

            elif action == 'answer':
                # Ready to answer - break ReAct loop
                break

            elif action == 'clarify':
                # Need clarification - return immediately
                reasoning_trace.append("Agent requires clarification")
                return dspy.Prediction(
                    answer=action_input,
                    confidence=0.3,
                    sources="",
                    reasoning_trace="\n\n".join(reasoning_trace)
                )

            else:
                # Unknown action - default to search
                search_results = self.vector_search_tool(question)
                context_accumulated.append(
                    f"[Default Search Results]\n{search_results}"
                )
                reasoning_trace.append("Unknown action, performed default search")
                break

        # Generate final answer
        final_context = "\n\n".join(context_accumulated)
        reasoning_summary = "\n\n".join(reasoning_trace)

        answer_result = self.answer(
            question=question,
            context=final_context,
            reasoning_trace=reasoning_summary
        )

        return dspy.Prediction(
            answer=answer_result.answer,
            confidence=answer_result.confidence,
            sources=answer_result.sources,
            reasoning_trace=reasoning_summary,
            domain=self.domain
        )

    def __call__(self, question: str) -> dspy.Prediction:
        """Callable interface"""
        return self.forward(question)

    def get_tool_description(self) -> str:
        """Get current tool description (for GEPA optimization)"""
        return self.vector_search_tool.description

    def update_tool_description(self, new_description: str):
        """Update tool description (called by GEPA)"""
        self.vector_search_tool.update_description(new_description)
        self.optimization_history.append({
            'type': 'tool_description_update',
            'new_description': new_description
        })
