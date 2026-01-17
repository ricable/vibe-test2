# System Architecture: Multi-Agent RAG with Meta-Cognitive Reasoning

## Executive Summary

This document provides a comprehensive architectural overview of the Multi-Agent Retrieval-Augmented Generation (RAG) system built on the DSPy framework, implementing recursive meta-cognitive reasoning and GEPA (Genetic-Pareto) optimization.

## Core Principles

### 1. Declarative Abstraction
- **Traditional Approach**: Imperative prompting with manual string manipulation
- **Our Approach**: DSPy signatures define input/output contracts declaratively
- **Benefit**: Separation of logic from implementation, enabling algorithmic optimization

### 2. Modular Composition
- **Signature**: Defines the "what" (I/O specification)
- **Module**: Defines the "how" (execution strategy like CoT, ReAct)
- **Optimizer**: Refines both automatically based on metrics

### 3. Multi-Agent Specialization
- **Lead Agent**: High-level orchestration and synthesis
- **Domain Subagents**: Specialized expertise with dedicated knowledge bases
- **Tool Integration**: Vector search, APIs, external systems

### 4. Meta-Cognitive Self-Awareness
- **Monitoring**: System observes its own reasoning process
- **Evaluation**: Assesses quality and identifies weaknesses
- **Adaptation**: Retries with refinements when confidence is low

## Architecture Layers

```
┌──────────────────────────────────────────────────────────────────┐
│                    Layer 7: Application                           │
│  - Medical RAG example                                           │
│  - Custom domain applications                                    │
│  - API endpoints                                                 │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                    Layer 6: Orchestration                         │
│  - MetaCognitiveReasoningAgent                                   │
│    ├─ Decompose (break down questions)                          │
│    ├─ Solve (route to subagents)                                │
│    ├─ Verify (validate solutions)                               │
│    ├─ Synthesize (combine results)                              │
│    └─ Reflect (self-assess & retry)                             │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                    Layer 5: Agent Execution                       │
│  - DomainSubagent (ReAct strategy)                              │
│    ├─ Thought: Reasoning about next action                      │
│    ├─ Action: Search, answer, or clarify                        │
│    └─ Observation: Tool results                                 │
│  - LeadAgent (multi-agent coordination)                         │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                    Layer 4: DSPy Signatures                       │
│  - DecomposeSignature                                           │
│  - SolveSignature                                               │
│  - VerifySignature                                              │
│  - SynthesizeSignature                                          │
│  - ReflectSignature                                             │
│  - VectorSearchSignature                                        │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                    Layer 3: Tools & Utilities                     │
│  - VectorSearchTool                                             │
│  - Custom domain tools                                          │
│  - MLflow integration                                           │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                    Layer 2: Knowledge Base                        │
│  - VectorStore (FAISS)                                          │
│    ├─ SentenceTransformer embeddings                           │
│    ├─ HNSW indexing                                            │
│    └─ Domain-specific collections                              │
│  - DocumentChunk (context preservation)                         │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                    Layer 1: Foundation                            │
│  - LLM Providers (OpenAI, Anthropic)                            │
│  - Embedding Models (Sentence Transformers)                     │
│  - Storage (File system, PostgreSQL/RuVector)                   │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Inference Pipeline

```
User Question
     │
     ↓
┌─────────────────────────────────────────┐
│  MetaCognitiveReasoningAgent            │
│                                         │
│  ┌────────────────┐                     │
│  │ 1. Decompose   │                     │
│  │ Input: Question                      │
│  │ Output: [SubProblem1, SubProblem2]  │
│  └────────┬───────┘                     │
│           ↓                             │
│  ┌────────────────┐                     │
│  │ 2. Solve       │                     │
│  │ For each SubProblem:                │
│  │   - Route to DomainSubagent         │
│  │   - Execute ReAct loop              │
│  │   - Generate sub-answer             │
│  └────────┬───────┘                     │
│           ↓                             │
│  ┌────────────────┐                     │
│  │ 3. Verify      │                     │
│  │ - Logic check                       │
│  │ - Fact check                        │
│  │ - Bias check                        │
│  └────────┬───────┘                     │
│           ↓                             │
│  ┌────────────────┐                     │
│  │ 4. Synthesize  │                     │
│  │ - Weight by confidence              │
│  │ - Combine sub-answers               │
│  │ - Generate final answer             │
│  └────────┬───────┘                     │
│           ↓                             │
│  ┌────────────────┐                     │
│  │ 5. Reflect     │                     │
│  │ - Assess quality                    │
│  │ - Check confidence                  │
│  │ - Retry if needed                   │
│  └────────────────┘                     │
└─────────────────────────────────────────┘
     │
     ↓
Final Answer + Metadata
```

### 2. SubAgent ReAct Loop

```
SubProblem
     │
     ↓
┌─────────────────────────────────────────┐
│  DomainSubagent                         │
│                                         │
│  Iteration 1:                           │
│  ┌────────────┐                         │
│  │ Thought    │ "Need diabetes info"    │
│  └──────┬─────┘                         │
│         ↓                               │
│  ┌────────────┐                         │
│  │ Action     │ "search"                │
│  └──────┬─────┘                         │
│         ↓                               │
│  ┌────────────┐                         │
│  │ Input      │ "metformin dosing"      │
│  └──────┬─────┘                         │
│         ↓                               │
│  VectorSearchTool                       │
│  └──────┬─────┘                         │
│         ↓                               │
│  Retrieved Context                      │
│                                         │
│  Iteration 2:                           │
│  ┌────────────┐                         │
│  │ Thought    │ "Have sufficient info"  │
│  └──────┬─────┘                         │
│         ↓                               │
│  ┌────────────┐                         │
│  │ Action     │ "answer"                │
│  └──────┬─────┘                         │
│         ↓                               │
│  Generate Answer                        │
└─────────────────────────────────────────┘
     │
     ↓
SubSolution + Confidence
```

### 3. GEPA Optimization Pipeline

```
Training Set
     │
     ↓
┌──────────────────────────────────────────────┐
│  GEPA Optimizer                              │
│                                              │
│  Iteration 1:                                │
│  ┌────────────────────────────┐              │
│  │ Current Prompts            │              │
│  │ (Population)               │              │
│  └──────┬─────────────────────┘              │
│         ↓                                    │
│  ┌────────────────────────────┐              │
│  │ Evaluate with Student LM   │              │
│  │ (GPT-4o-mini)              │              │
│  └──────┬─────────────────────┘              │
│         ↓                                    │
│  ┌────────────────────────────┐              │
│  │ Compute Metrics            │              │
│  │ - Groundedness             │              │
│  │ - Completeness             │              │
│  │ - Confidence Accuracy      │              │
│  └──────┬─────────────────────┘              │
│         ↓                                    │
│  ┌────────────────────────────┐              │
│  │ Reflection LM Analysis     │              │
│  │ (GPT-4o)                   │              │
│  │ - Identify failures        │              │
│  │ - Propose improvements     │              │
│  └──────┬─────────────────────┘              │
│         ↓                                    │
│  ┌────────────────────────────┐              │
│  │ Mutate Prompts             │              │
│  │ (Genetic algorithm)        │              │
│  └──────┬─────────────────────┘              │
│         ↓                                    │
│  ┌────────────────────────────┐              │
│  │ Update Pareto Frontier     │              │
│  │ (Multi-objective selection)│              │
│  └──────┬─────────────────────┘              │
│         ↓                                    │
│  Repeat for N iterations                     │
└──────────────────────────────────────────────┘
     │
     ↓
Optimized Agent
```

## Component Specifications

### MetaCognitiveReasoningAgent

**Responsibilities:**
- Execute 5-stage reasoning pipeline
- Manage retry logic based on confidence
- Coordinate multiple subagents
- Track execution traces

**Key Methods:**
```python
def forward(question: str, context: str = "") -> dspy.Prediction:
    """Execute meta-cognitive reasoning"""
    for retry in range(max_retries):
        decompose_result = self.decompose(question, context)
        sub_solutions = self.solve_via_subagents(decompose_result)
        verification = self.verify(sub_solutions)
        synthesis = self.synthesize(sub_solutions, verification)
        reflection = self.reflect(synthesis, verification)

        if reflection.final_confidence >= threshold:
            return synthesis

        # Retry with refinements
        context = update_context_with_weaknesses(reflection)

    return synthesis  # Max retries reached
```

**Configuration:**
- `confidence_threshold`: 0.8 (default)
- `max_retry_attempts`: 3 (default)
- `subagents`: Dict[domain_name, DomainSubagent]

### DomainSubagent

**Responsibilities:**
- Execute ReAct loop for domain-specific questions
- Use vector search tools for retrieval
- Generate answers with confidence scores

**ReAct Cycle:**
1. **Thought**: Reason about what to do next
2. **Action**: Choose search/answer/clarify
3. **Observation**: Process tool results
4. Repeat until answer ready or max iterations

**Configuration:**
- `domain`: str (e.g., "diabetes", "copd")
- `vector_search_tool`: VectorSearchTool
- `max_iterations`: 3 (default)

### VectorStore

**Responsibilities:**
- Store document embeddings with FAISS
- Perform semantic similarity search
- Maintain metadata for source tracking

**Features:**
- Context-preserving chunking with overlap
- HNSW indexing for fast search
- Domain filtering for targeted retrieval

**Key Methods:**
```python
def add_documents(documents, domain, chunk_size, chunk_overlap):
    """Add documents with chunking and embedding"""

def search(query, k, domain=None, min_score=0.0):
    """Semantic search with optional domain filter"""

def save(path):
    """Persist index and metadata"""

def load(path):
    """Load from disk"""
```

## GEPA Optimization Strategy

### Two-Model Architecture

**Student Model:**
- **Purpose**: Execute inference at scale
- **Characteristics**: Fast, cheap, good enough
- **Examples**: GPT-4o-mini, Llama-3-8B, Mistral-7B
- **Usage**: 95% of calls during optimization

**Reflection Model:**
- **Purpose**: Analyze failures, propose improvements
- **Characteristics**: High intelligence, analytical depth
- **Examples**: GPT-4o, Claude 3.5 Sonnet, Qwen3-Thinking
- **Usage**: 5% of calls, triggered on errors

### Pareto Frontier

GEPA maintains a set of non-dominated solutions across multiple objectives:

**Objectives:**
1. **Accuracy**: Correctness of answers
2. **Groundedness**: Factual support in context
3. **Completeness**: Coverage of all sub-problems
4. **Brevity**: Conciseness (optional, trade-off with completeness)
5. **Safety**: Bias detection and mitigation

**Selection Strategy:**
- Stochastic sampling from Pareto set
- Preserves diversity in candidate pool
- Prevents premature convergence

### Feedback Loop

```
┌───────────────────────────────────────────┐
│  Current Prompt                           │
└─────────────┬─────────────────────────────┘
              ↓
┌───────────────────────────────────────────┐
│  Execute on Training Examples             │
│  (Student Model)                          │
└─────────────┬─────────────────────────────┘
              ↓
┌───────────────────────────────────────────┐
│  Failures? Low scores?                    │
└─────────────┬─────────────────────────────┘
              ↓ YES
┌───────────────────────────────────────────┐
│  Reflection Model Analysis                │
│  "The Solve stage failed to call the      │
│  diabetes tool for sub-problem 2.         │
│  Suggested improvement: Add explicit      │
│  instruction to invoke domain-specific    │
│  tools for each sub-problem."             │
└─────────────┬─────────────────────────────┘
              ↓
┌───────────────────────────────────────────┐
│  Mutate Prompt                            │
│  "For each sub-problem, identify the      │
│  relevant domain and call the             │
│  corresponding search tool."              │
└─────────────┬─────────────────────────────┘
              ↓
┌───────────────────────────────────────────┐
│  Evaluate Mutated Prompt                  │
└─────────────┬─────────────────────────────┘
              ↓
     Add to Pareto Frontier
```

## Observability & Monitoring

### MLflow Integration

**Tracked Artifacts:**

1. **Prompt Evolution**
   - Iteration number
   - Prompt text
   - Score
   - Feedback from reflection LM

2. **Execution Traces**
   - Question
   - Answer
   - Sub-solutions
   - Verification report
   - Reflection notes
   - Retry count

3. **Pareto Frontiers**
   - Candidates per iteration
   - Multi-objective scores
   - Selection probabilities

4. **Model Comparisons**
   - Baseline vs. optimized
   - Different student models
   - Cost-performance trade-offs

### Key Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **Confidence Calibration** | `|confidence - accuracy|` | < 0.15 |
| **Retry Rate** | `retries / total_queries` | < 15% |
| **Tool Call Accuracy** | `correct_tools / total_tools` | > 90% |
| **Groundedness** | `cited_sources / total_claims` | > 0.8 |
| **Latency (p95)** | 95th percentile response time | < 5s |

## Security & Safety

### Input Validation
- Sanitize queries to prevent prompt injection
- Rate limiting per user
- Max token limits

### Output Filtering
- Bias detection in Verify stage
- Hallucination checks via grounding
- Confidence thresholds for deployment

### Data Privacy
- No logging of sensitive medical information
- Anonymization of traces
- Encrypted storage for vector embeddings

## Scalability Considerations

### Horizontal Scaling
- Stateless agents enable multiple instances
- Shared vector store via Redis/PostgreSQL
- Load balancer for query distribution

### Vertical Scaling
- GPU acceleration for embeddings
- FAISS GPU indices
- Batched LLM inference

### Cost Optimization
- Cache frequent queries
- Use smallest viable models post-optimization
- Precompute embeddings offline

## Future Enhancements

1. **Autonomous Structure Optimization**
   - GEPA suggests adding/removing subagents
   - Automatic tool discovery and integration

2. **Multi-Modal Reasoning**
   - Image understanding for medical scans
   - Table/chart extraction from PDFs

3. **Continual Learning**
   - Update vector stores with new documents
   - Re-optimize prompts as domain evolves

4. **Advanced Routing**
   - ML-based subagent selection
   - Dynamic domain creation

5. **Explainability**
   - Trace visualization in UI
   - Natural language explanations of reasoning steps

## Conclusion

This architecture provides a robust, scalable foundation for multi-agent RAG systems that:

✅ Separate concerns (signatures, modules, optimizers)
✅ Self-correct via meta-cognitive reflection
✅ Optimize automatically with GEPA
✅ Scale to production workloads
✅ Maintain observability through MLflow

The system represents a significant advancement over traditional RAG, offering reliability, adaptability, and transparency essential for high-stakes applications like medical decision support.
