---
name: research-loop
description: "Run one fixed-budget autonomous research iteration (autoresearch-mlx): propose → train → evaluate → commit-or-revert."
---

# research-loop

Run a single iteration of the autoresearch-mlx fixed-time research loop, driven
by the harness swarm. Each iteration is bounded by a fixed compute budget
(the upstream convention is one ~5-minute MLX training run per proposal).

1. **Propose** — the `planner` reads `program.md` and `results.tsv`, then the
   `worker`/`trainer` edits `train.py` to make ONE attributable change.
2. **Train** — the `trainer` runs the fixed-time experiment (MLX on Apple
   Silicon; no PyTorch/CUDA) and records the training/val curves.
3. **Evaluate** — the `evaluator` computes `val_bpb` on the held-out set and
   compares it against the current best baseline in `results.tsv`.
4. **Gate** — the `critic` accepts or rejects the proposal against the
   success criterion (strictly lower `val_bpb`).
5. **Commit or revert** — the `deployer` commits the change to git and appends
   the new baseline to `results.tsv` on a win, or runs `git revert` on a loss.
6. Append the trajectory to harness memory so the next iteration starts warm
   (`/memory-inspect`).

Stop when the iteration budget is exhausted or no proposal improves the metric.
