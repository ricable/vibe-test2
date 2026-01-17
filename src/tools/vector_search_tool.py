"""
Vector Search Tool for DSPy Agents

Provides a callable tool interface for vector retrieval
that can be optimized by GEPA.
"""

import dspy
from typing import List, Dict, Optional
from ..utils.vector_store import VectorStore


class VectorSearchTool:
    """
    Vector search tool for retrieving relevant context.

    This tool can be used by subagents and optimized by GEPA
    with enable_tool_optimization=True.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        domain: str,
        top_k: int = 5,
        description: Optional[str] = None
    ):
        """
        Initialize VectorSearchTool.

        Args:
            vector_store: VectorStore instance
            domain: Domain this tool specializes in
            top_k: Number of results to return
            description: Tool description for GEPA optimization
        """
        self.vector_store = vector_store
        self.domain = domain
        self.top_k = top_k

        # Default description (can be optimized by GEPA)
        if description is None:
            self.description = (
                f"Search {domain} knowledge base for relevant information. "
                f"Returns top {top_k} most relevant document chunks."
            )
        else:
            self.description = description

    def __call__(self, query: str) -> str:
        """
        Execute vector search.

        Args:
            query: Search query

        Returns:
            Formatted string with retrieved context
        """
        results = self.vector_store.search(
            query=query,
            k=self.top_k,
            domain=self.domain
        )

        if not results:
            return f"No relevant {self.domain} information found for: {query}"

        # Format results
        context_parts = []
        for i, (chunk, score) in enumerate(results, 1):
            context_parts.append(
                f"[{i}] Source: {chunk.source} (Score: {score:.3f})\n"
                f"{chunk.text}\n"
            )

        return "\n".join(context_parts)

    def get_tool_spec(self) -> Dict:
        """
        Get tool specification for DSPy.

        Returns:
            Tool specification dictionary
        """
        return {
            "name": f"search_{self.domain}",
            "description": self.description,
            "callable": self,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for finding relevant information"
                    }
                },
                "required": ["query"]
            }
        }

    def update_description(self, new_description: str):
        """
        Update tool description (used by GEPA during optimization).

        Args:
            new_description: New description text
        """
        self.description = new_description
