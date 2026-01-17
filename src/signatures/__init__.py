"""
DSPy Signatures for Multi-Agent RAG with Recursive Meta-Cognitive Reasoning
"""

from .meta_cognitive import (
    DecomposeSignature,
    SolveSignature,
    VerifySignature,
    SynthesizeSignature,
    ReflectSignature,
    MetaCognitiveOutput
)

from .retrieval import (
    VectorSearchSignature,
    RerankSignature
)

__all__ = [
    'DecomposeSignature',
    'SolveSignature',
    'VerifySignature',
    'SynthesizeSignature',
    'ReflectSignature',
    'MetaCognitiveOutput',
    'VectorSearchSignature',
    'RerankSignature'
]
