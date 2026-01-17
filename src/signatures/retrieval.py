"""
Retrieval Signatures for Vector Search and Reranking
"""

import dspy
from typing import List


class VectorSearchSignature(dspy.Signature):
    """
    Generate optimized search queries for vector retrieval.

    The query should be:
    - Semantically rich
    - Domain-specific when applicable
    - Optimized for embedding similarity
    """

    question: str = dspy.InputField(
        desc="User question or information need"
    )
    domain: str = dspy.InputField(
        desc="Specific domain context (e.g., diabetes, COPD)",
        default=""
    )

    search_query: str = dspy.OutputField(
        desc="Optimized query for vector search"
    )
    reasoning: str = dspy.OutputField(
        desc="Why this query formulation was chosen"
    )


class RerankSignature(dspy.Signature):
    """
    Rerank retrieved documents based on relevance to the specific question.

    Considers:
    - Semantic relevance
    - Factual accuracy
    - Recency and authority
    """

    question: str = dspy.InputField(
        desc="Specific question being answered"
    )
    documents: str = dspy.InputField(
        desc="Retrieved documents with metadata (JSON format)"
    )

    ranked_indices: List[int] = dspy.OutputField(
        desc="Indices of documents in order of relevance (0-indexed)"
    )
    relevance_scores: List[float] = dspy.OutputField(
        desc="Relevance scores for each document (0.0 to 1.0)"
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of ranking decisions"
    )
