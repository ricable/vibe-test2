# Lineage & source attribution

`omniresearch-harness` was minted with the [ruvnet meta-harness-generator](https://github.com/ruvnet/agent-harness-generator)
(`metaharness@0.1.15`) by blending the two archetypes the generator's
`analyze-repo` step recognises for the source repositories below.

## Source repositories

| Repo | What it is | Generator archetype | Contributes |
|---|---|---|---|
| [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) | AI agent orchestration framework — orchestrate Claude Code, Codex, Cursor, Pi, and custom agents; swap harnesses without rewriting. | `ai-agent-framework-harness` → `vertical:agentics` | `orchestrator`, `planner`, `worker`, `critic` agents; `run-swarm` + `memory-inspect` skills; swarm-bus MCP. |
| [trevin-creator/autoresearch-mlx](https://github.com/trevin-creator/autoresearch-mlx) | Apple-Silicon (MLX) port of a fixed-time autonomous research loop: edit `train.py`, run a bounded experiment, evaluate `val_bpb`, commit or revert via git. | `data-pipeline-harness` → `vertical:ai` | `data-curator`, `trainer`, `evaluator`, `deployer` agents; `eval-report` skill; the `research-loop` skill. |

## How the blend was derived

The generator's `analyze-repo` scores a repo's high-signal files (README,
manifests) against an archetype library and recommends a `vertical:*` template:

- **omnigent** — multi-agent / orchestration / MCP signals → `vertical:agentics`
  (agents: orchestrator, planner, worker, critic).
- **autoresearch-mlx** — ML / training / model / dataset signals → `vertical:ai`
  (agents: data-curator, trainer, evaluator, deployer).

This harness unions both agent rosters and skill sets, then adds a bespoke
`research-loop` skill that wires the orchestration swarm onto autoresearch-mlx's
propose → train → evaluate → commit-or-revert cycle, with the eval gate keyed on
`val_bpb` (validation bits-per-byte).

## Faithfulness note

Files were rendered from the generator's own templates
(`templates/vertical_agentics/*` and `templates/vertical_ai/*`) using its
Mustache-style `{{name}}` / `{{description}}` / `{{host}}` substitution
(`name=omniresearch-harness`, `host=claude-code`). The `.harness/manifest.json`
fingerprints and `.harness/provenance.json` witness stub mirror the generator's
`manifest.js` / witness-client output shapes. Because `npx metaharness` runs
arbitrary external code, the scaffold was reproduced from the inspected
templates rather than executed in this sandbox.
