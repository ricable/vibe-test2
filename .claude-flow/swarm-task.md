# ERKRS Implementation Task

## Objective
Implement the Ericsson RAN Knowledge Retrieval System (ERKRS) as specified in the Product Requirements Document.

## System Overview
Build a three-tier AI-agent-compatible knowledge retrieval system:
- **Tier 1**: Skill Layer (always-loaded, ~50KB)
- **Tier 2**: Structured Store (SQLite with FTS5)
- **Tier 3**: Vector Store (ChromaDB with semantic search)

## Key Requirements

### Phase 1: Foundation (Priority 1)
1. **Project Structure Setup**
   - Create Python project structure as specified in PRD section 8.2
   - Setup pyproject.toml with dependencies
   - Configure pytest, linting, and CI/CD

2. **Markdown Parser**
   - Parse markdown files preserving structure, tables, code blocks
   - Extract YAML front matter
   - Handle nested lists and nested headers

3. **Entity Extractor**
   - Extract CXC codes (pattern: CXC[0-9]{7})
   - Extract FAJ codes (pattern: FAJ[0-9]{6})
   - Extract MO.attribute pairs (pattern: [A-Z][a-z]+[A-Z][a-z]+\.[a-z]+)
   - Extract PM counter names (pattern: pm[A-Z]\w+)

4. **SQLite Schema & DAL**
   - Implement schema from PRD section 4.2.2
   - Create Data Access Layer with async support
   - Add FTS5 full-text search indexes

### Phase 2: Vector Store (Priority 2)
1. **Semantic Chunker**
   - Implement intelligent chunking respecting markdown boundaries
   - Keep tables and code blocks atomic
   - Add configurable overlap between chunks
   - Extract metadata for each chunk

2. **Embedding Pipeline**
   - Integrate sentence-transformers (bge-base-en-v1.5)
   - Batch processing for efficiency
   - Store embeddings with chunk IDs

3. **ChromaDB Integration**
   - Setup ChromaDB collections
   - Implement metadata filtering
   - Support hybrid search (vector + keyword)

### Phase 3: Query Router (Priority 3)
1. **Query Classifier**
   - Implement pattern-based routing (see PRD section 4.3)
   - Support CXC lookup, parameter lookup, counter lookup
   - Route to appropriate tier based on query type

2. **Hybrid Retrieval**
   - Combine structured (Tier 2) and semantic (Tier 3) retrieval
   - Deduplicate and merge results
   - Rank by relevance

3. **Context Enhancement**
   - Auto-include prerequisite features
   - Add related parameters for feature queries
   - Include relevant counters

### Phase 4: API & Integration (Priority 4)
1. **FastAPI Service**
   - Implement REST API with /query endpoint
   - Support batch queries
   - Add proper error handling and validation
   - Include OpenAPI documentation

2. **MCP Server**
   - Implement MCP-compatible tool interface
   - Expose search, lookup, and browse tools
   - Support streaming responses

3. **Skill File Generator**
   - Generate SKILL.md from knowledge base
   - Include feature index, parameter quick-ref
   - Add troubleshooting decision trees
   - Stay within 80KB budget

## Technical Stack
- **Language**: Python 3.11+
- **Storage**: SQLite 3.40+, ChromaDB 0.4+
- **Embedding**: sentence-transformers/bge-base-en-v1.5
- **API**: FastAPI 0.100+
- **MCP**: anthropic-mcp-sdk

## Success Criteria
- Query accuracy ≥ 90%
- Query latency p50 < 200ms
- Token efficiency ≥ 75%
- 100% documentation coverage
- All tests passing with ≥ 80% coverage

## Coordination Strategy
1. **Architect Agent**: Design system architecture, define interfaces
2. **Backend Dev Agent**: Implement core ingestion and retrieval logic
3. **Data Engineer Agent**: Build storage layers (SQLite, ChromaDB)
4. **DevOps Agent**: Setup project structure, CI/CD, Docker

## Deliverables
1. Working Python package `erkrs`
2. Populated SQLite database and vector store
3. FastAPI service with OpenAPI docs
4. MCP server implementation
5. Generated SKILL.md file
6. Comprehensive test suite
7. README and documentation
