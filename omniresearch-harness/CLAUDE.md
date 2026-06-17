# omniresearch-harness

Autonomous research orchestrator — runs multi-agent coding swarms (omnigent) through fixed-budget, eval-gated ML research loops (autoresearch-mlx).

> Agentics + AI harness · domains: `agentics/orchestration`, `ai/ml-lifecycle`. Generated with [create-agent-harness](https://github.com/ruvnet/agent-harness-generator).

## Behavioral rules

- Use the harness's MCP tools (`mcp__omniresearch-harness__*`) for orchestration
- Memory and routing are handled by the kernel — you don't need to learn them
- Each research iteration is bounded by a fixed compute budget; change one variable at a time
- A proposal is committed only if it strictly improves the eval metric (`val_bpb`); otherwise revert
- Defer destructive operations to the user

## Agents

| Agent | Tier | Role | Lineage |
|---|---|---|---|
| `orchestrator` | opus | Routes work and owns the goal state. | omnigent |
| `planner` | opus | Builds the dependency-aware plan. | omnigent |
| `worker` | sonnet | Executes one task and reports. | omnigent |
| `critic` | opus | Reviews outputs before they land. | omnigent |
| `data-curator` | sonnet | Builds and documents the dataset. | autoresearch-mlx |
| `trainer` | sonnet | Runs reproducible, fixed-budget training jobs. | autoresearch-mlx |
| `evaluator` | opus | The honest eval gate (`val_bpb`). | autoresearch-mlx |
| `deployer` | sonnet | Commits the winner / reverts the regression. | autoresearch-mlx |

## Skills

- `/run-swarm` — Decompose a goal and run the orchestrator→planner→worker→critic loop to completion.
- `/memory-inspect` — Search and inspect the harness memory namespace (HNSW + emergent-time decay).
- `/eval-report` — Produce an honest eval report: metrics, subgroup slices, baseline delta, ship/no-ship.
- `/research-loop` — Run one fixed-budget autonomous research iteration: propose → train → evaluate → commit-or-revert.

## Commands

- `doctor` — Health-check the harness: kernel load, MCP wiring, memory backend, host adapter.

## Architecture

This harness uses [@metaharness/kernel](https://www.npmjs.com/package/@metaharness/kernel) — a Rust-compiled WASM module with a NAPI-RS native fallback — so the same code runs identically on every platform.

It blends two upstream archetypes the meta-harness recognises:

- **omnigent** (`vertical:agentics`) — multi-agent orchestration across swappable coding-agent harnesses.
- **autoresearch-mlx** (`vertical:ai`) — a fixed-time autonomous research loop that edits `train.py`, runs a bounded experiment, evaluates `val_bpb`, and commits or reverts via git.

See [`SOURCES.md`](./SOURCES.md) for full lineage.
