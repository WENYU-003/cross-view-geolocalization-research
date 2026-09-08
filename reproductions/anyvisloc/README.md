# AnyVisLoc / UAV-AVL Reproduction and Analysis

This directory contains the AnyVisLoc reproduction record and lightweight offline analysis scripts. It does not contain the upstream benchmark implementation, dataset, model weights, raw result bundles, or generated image audits.

## Status

- baseline reproduction: completed;
- Scene_16 query/failure attribution: completed;
- satellite correspondence-consistency method hypothesis: **NO-GO / frozen**;
- future role: external validation / secondary benchmark.

See [`notes/uavavl_related_work/12_uavavl_research_checkpoint.md`](../../notes/uavavl_related_work/12_uavavl_research_checkpoint.md) for the final decision and [`anyvisloc-reproduction-record.md`](anyvisloc-reproduction-record.md) for the baseline record.

## Analysis scripts

| Script | Responsibility | Model/GPU execution |
| --- | --- | --- |
| [`analyze_cross_reference_2d.py`](analyze_cross_reference_2d.py) | Pair aerial/satellite query correspondences and measure DSM-free geographic endpoint agreement | None |
| [`build_scene16_visual_audit.py`](build_scene16_visual_audit.py) | Build the fixed 24-query geometry-first audit and shortlist | None |
| [`export_scene16_rgb_audit.py`](export_scene16_rgb_audit.py) | Export RGB/map panels from an existing dataset and saved correspondence artifacts | None |
| [`analyze_scene16_spatial_support.py`](analyze_scene16_spatial_support.py) | Compute 295-query agreement, shift, residual, coverage, concentration, entropy, correlations, and counterexamples | None |
| [`analyze_scene16_counterexample_mechanisms.py`](analyze_scene16_counterexample_mechanisms.py) | Isolate mechanisms in the fixed 29-query shortlist | None |
| [`analyze_scene16_solver_provenance.py`](analyze_scene16_solver_provenance.py) | Recover raw → valid 2D-3D → PnP inlier → pose provenance for fixed focus samples | None |

The scripts are analysis-only. They must not be interpreted as changes to the AnyVisLoc matcher, DSM construction, PnP solver, or evaluation protocol.

## GEO-1 candidate-provenance logging patch

`patches/geo1_candidate_provenance.patch` adds an opt-in
`--save_candidate_provenance` flag to the external AnyVisLoc full runner. The
flag is disabled by default. When enabled, it records the existing matcher
outputs, DSM validity, exact PnP inputs, RANSAC inlier indices, candidate poses,
and the unchanged max-inlier candidate decision. It does not change retrieval,
matching, DSM sampling, PnP parameters, random state, or candidate selection.

Apply it from the root of the external `paper2_UAV_AVL` source tree:

```bash
patch -p1 < /path/to/cross-view-geolocalization-research/reproductions/anyvisloc/patches/geo1_candidate_provenance.patch
```

Run one control query without the flag and the same query with the flag, then
use `verify_geo1_candidate_provenance_smoke.py` to require identical
`best_index`, `pred_error`, and per-candidate inlier counts plus five complete,
finite candidate records. This is provenance validation only; it is not a
GEO-1 hypothesis test.

## Inputs and outputs

Inputs are supplied through command-line arguments and normally point to external, immutable evidence bundles or server-local dataset locations. Do not hard-code machine paths in these scripts.

Generated CSV/JSON/plots should be written to an external analysis-output directory. Only lightweight, decision-relevant derived tables explicitly selected for long-term audit belong in Git.

Do not commit:

- `anyvisloc_evidence_inbox/`;
- raw `Result/` directories;
- tar archives, per-query NPZ/PKL files, or RGB audit panels;
- datasets, checkpoints, weights, caches, or environment-specific output.

## Evidence boundary

Aerial endpoints are used as a high-accuracy pseudo-reference in the cross-reference diagnostics, not manual correspondence ground truth. Agreement and PnP inlier labels therefore do not certify geographic identity. Each research note records the additional missing fields and uncertainty for its analysis.
