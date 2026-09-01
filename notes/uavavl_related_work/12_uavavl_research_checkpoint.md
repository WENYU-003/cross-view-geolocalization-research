# UAV-AVL / AnyVisLoc Research Checkpoint

## Checkpoint purpose

This document freezes the current UAV-AVL research line after baseline reproduction, related-work synthesis, Scene_16 failure analysis, satellite correspondence diagnostics, and solver-provenance recovery. It records what is supported, what remains uncertain, and why the current proposed-method direction is stopped.

## Final status

1. **Reproduction completed.** The main AnyVisLoc Scene_16 retrieval-only, GT-reference matching/localization, full aerial pipeline, aerial/satellite reference, matcher, Top-K, and pose-prior checkpoints have been recovered and audited at the evidence levels recorded in [`06_failure_to_limitation.md`](06_failure_to_limitation.md).
2. **Aerial vs satellite performance gap confirmed.** Both full-pipeline and GT-reference evidence show substantial satellite degradation relative to aerial reference performance.
3. **Retrieval is not sufficient to explain the gap.** Satellite GT-reference evaluation removes retrieval but retains a material localization gap.
4. **Cross-reference correspondence degradation exists.** The 295-query DSM-free aerial/satellite endpoint audit shows systematic degradation associated with satellite error, while preserving georegistration and pseudo-reference uncertainty.
5. **Agreement, match count, and simple coverage are not sufficient localization-utility indicators.** Counterexamples include high Agreement with catastrophic error, low Agreement with successful localization, and high/broad match support without accurate final pose.
6. **Solver provenance does not recover a clean frontend subset-degradation mechanism for the high-Agreement catastrophic group.** All 3,000 saved raw matches enter the solver in the nine focus samples; catastrophic controls have many inliers and no shared severe spatial-collapse signature. The cross-reference-pairable inliers remain highly consistent, subject to incomplete pairing and pseudo-reference limitations.
7. **The satellite correspondence-consistency proposed-method direction is NO-GO / frozen.** Current evidence does not support turning Agreement, simple coverage, or solver-subset filtering into a defensible frontend model contribution. Remaining explanations increasingly involve map alignment, DSM lifting, pose ambiguity, or missing manual correspondence truth.
8. **UAV-AVL remains useful as an external validation / secondary benchmark.** A future method selected from an independently supported frontend research question may return to UAV-AVL for controlled aerial/satellite evaluation, robustness analysis, and secondary benchmarking.

## Decision boundary

The NO-GO decision is specific to the current hypothesis:

> satellite localization failure can be converted into a clean proposed frontend method by optimizing cross-reference Agreement, match quantity, simple spatial support, or a solver-selected correspondence subset.

It is not a claim that satellite feature alignment is solved, that UAV-AVL is no longer valuable, or that future methods cannot improve it. It means the recovered Scene_16 evidence does not isolate a sufficiently stable and frontend-specific mechanism for method design.

## Evidence retained in Git

- related-work taxonomy, paper index, comparison matrix, and tutorial;
- lightweight query-level derived CSV;
- failure-to-limitation and Scene_16 diagnostic notes;
- reusable CPU analysis and visualization scripts;
- final decision and explicit uncertainty.

## Evidence intentionally retained outside Git

- raw result bundles and per-query JSON/NPZ/PKL artifacts;
- UAV, aerial, and satellite RGB data;
- generated RGB audit panels and PNG/SVG output directories;
- datasets, checkpoints, model weights, caches, and server-local run directories.

External artifacts must be referenced by run ID, filename, checksum where available, and schema—not uploaded into this repository.

## Handoff

This checkpoint closes active UAV-AVL proposed-method exploration. The next primary research task restarts from GAGeo/CMA-Loc evidence and its own failure question. Do not transfer the frozen UAV-AVL mechanism into GAGeo without independent evidence.
