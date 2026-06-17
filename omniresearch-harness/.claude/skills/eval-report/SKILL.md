---
name: eval-report
description: "Produce an honest eval report: metrics, subgroup slices, baseline delta, ship/no-ship."
---

# eval-report

Produce an evaluation report.

1. Evaluate on the held-out set with objective-aligned metrics (for the autoresearch-mlx loop: `val_bpb`, lower is better).
2. Slice by subgroup and report the worst slice.
3. Compare against the baseline in `results.tsv`; show the delta.
4. End with SHIP or NO-SHIP and the number behind it.
