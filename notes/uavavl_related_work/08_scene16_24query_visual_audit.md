# Scene_16 24-Query Front-End Visual Audit

## Research question

Which front-end failure mechanisms explain the satellite-specific correspondence degradation observed after retrieval is removed with GT reference selection?

## Hypothesis

Catastrophic satellite localization failures should show weaker aerial–satellite 2D map agreement than successful queries. The audit should also determine whether degradation is dominated by a coherent map-plane shift or by locally inconsistent correspondences.

## Evidence and controlled scope

- Dataset: AnyVisLoc `Scene_16`.
- Selection: 24 deterministic error-quantile cases from the existing shortlist: 8 `success_le_3m`, 8 `mid_3_to_20m`, and 8 `catastrophic_gt_20m`.
- Aerial run: `20260831-1017_1scenes`, GT reference, RoMa, `yp`, 3,000 requested matches.
- Satellite run: `20260831-0905_1scenes`, GT reference, RoMa, `yp`, 3,000 requested matches.
- Pairing: mutual-nearest UAV query coordinates within 5 original-image pixels.
- Diagnostic only: map XY disagreement, median coherent shift, and shift-corrected residual.
- Explicitly excluded: retrieval, DSM Z, PnP inlier labels, model training, and baseline changes.

The downloaded evidence archives contain `result.json`, `matches_and_pnp_inputs.npz`, and PKL summaries, but they do **not** contain UAV/aerial/satellite RGB images or RoMa certainty maps. Therefore the completed artifact is a geometry-only correspondence audit, not yet a complete appearance-level visual taxonomy.

## Command

```bash
PYTHONPATH=reproductions/anyvisloc \
python reproductions/anyvisloc/build_scene16_visual_audit.py \
  --aerial-archive /path/to/aerial_gtref_logging_scene16_20260831-1017.tar.gz \
  --satellite-archive /path/to/satellite_gtref_scene16_20260831-0905.tar.gz \
  --shortlist /path/to/representative_case_shortlist.csv \
  --output-dir /path/to/scene16_24query_geometric_audit_20260831
```

External output layout used for this audit:

```text
$EVIDENCE_DIR/
scene16_24query_geometric_audit_20260831/
```

`$EVIDENCE_DIR` is an external, machine-specific evidence location and is not tracked by Git.

## Geometry-only candidate labels

These labels are deterministic diagnostic candidates, not semantic ground truth:

- `COHERENT_SHIFT_CANDIDATE`: median shift at least 5 m and shift-corrected median residual at most 3 m.
- `INCONSISTENT_CORRESPONDENCE_CANDIDATE`: shift-corrected median residual at least 5 m or Agreement@5m below 30%.
- `MIXED_SHIFT_AND_RESIDUAL_CANDIDATE`: median shift at least 3 m without satisfying the two definitions above.
- `RELATIVELY_CONSISTENT_2D_CANDIDATE`: none of the above.

## Results

| Failure group | Coherent shift | Inconsistent | Mixed | Relatively consistent | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Satellite error <=3 m | 0 | 2 | 0 | 6 | 8 |
| 3 m < error <=20 m | 0 | 5 | 1 | 2 | 8 |
| Satellite error >20 m | 2 | 5 | 0 | 1 | 8 |
| **All** | **2** | **12** | **1** | **9** | **24** |

The 24 panels and prefilled manual review table were generated successfully. Every recomputed Agreement@3m, Agreement@5m, robust-shift norm, and shift-corrected median residual agrees with the shortlist value to an absolute tolerance of `1e-6`.

## Interpretation

### Supported by current raw evidence

- Correspondence inconsistency is enriched in the middle and catastrophic groups: 10/16 versus 2/8 successful cases under the current deterministic rule.
- Catastrophic failure is not a single mechanism. Five cases are inconsistency candidates, two are coherent-shift candidates, and one is relatively consistent in this 2D audit.
- A coherent map-plane displacement is a real candidate mechanism for a subset, not a universal explanation.
- Pair count alone cannot define correctness; all cases can retain many mutual pairs while their map endpoints disagree.

### Important counterexamples

- Two successful cases are classified as geometry-only inconsistency candidates. Low aerial–satellite pseudo-reference agreement is therefore not sufficient for final failure.
- One catastrophic case is relatively consistent in this diagnostic. A good 2D agreement score is therefore not sufficient for accurate final pose.

These counterexamples prevent promoting the current heuristic labels into causal conclusions.

## Remaining uncertainty

The following cannot be labeled from the downloaded artifacts and remain `NEEDS_RGB` or `NEEDS_RGB_OR_LANDMARKS`:

- appearance/domain gap;
- scale/resolution loss;
- repetitive structures;
- visibility or occlusion mismatch;
- temporal change;
- aerial/satellite map georegistration confounder;
- RoMa confidence calibration.

## Next decision

Do not select a network architecture yet. Recover only the 24 original dataset samples or export their UAV, aerial, and satellite crops plus RoMa certainty. Then manually audit the same fixed shortlist, resolve the counterexamples, and choose the first minimal front-end mechanism only after the dominant failure type is known.

## RGB export preparation

The active remote dataset was inspected and the following inputs were confirmed:

- each `Scene_16/<sample_id>.npz` contains `image` with shape `(750, 1000, 3)` and dtype `uint8`;
- `Scene_16/aerial_map.png` is RGB with size `8704 x 10360`;
- `Scene_16/satellite_map.png` is RGB with size `2768 x 3294`.

`export_scene16_rgb_audit.py` therefore performs a CPU-only export from the existing artifacts. It does not rerun retrieval, RoMa, DSM lookup, or PnP. For each fixed query it shows the UAV RGB and equal-metric north-up aerial/satellite map windows with mutual-pair endpoints colored by 2D map agreement.

The map panels are deliberately labeled as `north_up_equal_metric_geographic_window_not_exact_matcher_input`: they support appearance, scale, repetition, visibility, temporal-change, and georegistration diagnosis, but they must not be described as the pose-prior-rotated tensors directly consumed by RoMa.

## RGB evidence audit (2026-08-31)

### Restored artifact

The RGB audit archive was restored and validated locally:

```text
$EVIDENCE_DIR/
Scene16_RGB_Audit_20260831.tar.gz
```

- SHA-256: `a86aa34456419a73e613d744546a7791acee5afd7c2d00aa0008feb7f8a0d0a4`
- 24/24 expected PNG panels are present.
- The fixed shortlist remains balanced: 8 `success_le_3m`, 8 `mid_3_to_20m`, and 8 `catastrophic_gt_20m`.
- The exporter manifest confirms that no GPU, retrieval rerun, matcher rerun, DSM label, or PnP label was used.
- The panels are north-up equal-metric geographic windows, not the exact pose-prior-rotated tensors passed to RoMa.

The original prefilled table was preserved. Conservative manual labels were written to:

```text
$EVIDENCE_DIR/
Scene16_RGB_Audit_20260831/rgb_manual_review_codex_20260831.csv
```

### Quantitative group contrast

| Failure group | n | Mean Agreement@5m | Median Agreement@5m | Mean final error (m) | Median final error (m) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Satellite error <=3 m | 8 | 56.72% | 59.32% | 1.664 | 1.688 |
| 3 m < error <=20 m | 8 | 38.65% | 34.33% | 8.846 | 7.379 |
| Satellite error >20 m | 8 | 30.03% | 26.12% | 102.220 | 38.084 |

This ordered decrease supports an association between weaker aerial–satellite map-endpoint agreement and worse satellite localization on the fixed 24-query shortlist. It does not by itself establish that feature disagreement caused every pose error.

### Qualitative observations

The strongest recurring visual pattern is **structure-dependent correspondence ambiguity**:

- repeated pyramidal roof units in the rectangular complex and radial ribs in the circular building are frequently disagreement-heavy;
- roads, plazas, parking areas, and other surrounding context more often provide agreeing endpoints;
- successful controls can retain extensive roof disagreement when enough agreeing context is spatially distributed outside the repetitive structure;
- near-nadir cases such as `L16_0248` and `L16_0253` still show strong disagreement on the radial roof, so oblique viewpoint is a contributor but is not a sufficient explanation;
- satellite blur/resolution, shadow, illumination, and visible seasonal appearance differences are present, but these challenges also occur in successful controls and are not sufficient failure predictors by themselves.

Primary qualitative label counts across the 24 panels are:

| Primary review label | Count |
| --- | ---: |
| Robust context support control | 6 |
| Repetitive/symmetric structure ambiguity | 5 |
| Mixed cross-view appearance and repetition | 5 |
| Structure-dependent ambiguity with context support | 3 |
| Front-end disagreement but pose success | 2 |
| Repetitive structure and domain gap | 1 |
| Severe front-end correspondence inconsistency | 1 |
| Downstream or spatial-degeneracy counterexample | 1 |

These are reviewer labels for hypothesis generation, not ground-truth causal classes.

### Counterexamples and evidence boundary

- `L16_0098` has Agreement@5m of 58.59% but 91.84 m final error. It is a direct counterexample to the claim that all catastrophic errors are explained by weak 2D correspondence agreement. Spatial degeneracy, DSM/georegistration, or another downstream effect remains possible.
- `L16_0076` and `L16_0077` have only 32.46% and 29.68% Agreement@5m, respectively, yet final errors of 0.29 m and 0.80 m. A low global agreement percentage is therefore not sufficient for localization failure.
- The visible RGB panels cannot verify acquisition-time structural change or landmark-level aerial/satellite georegistration. Both fields remain `UNCERTAIN` for all 24 cases.
- Green/red marks encode agreement with the aerial pseudo-reference under the current diagnostic. They are not independently annotated correspondence ground truth.

### Updated decision

The evidence supports continuing a **front-end** research question, but the question should be narrower than generic satellite feature alignment:

> Do cross-view matchers assign too much support to repetitive/symmetric structures and too little reliable, spatially distributed support to stable surrounding context under satellite appearance and resolution changes?

Before method design, the minimum next diagnostic is to quantify correspondence correctness and spatial support by semantic/structural region on a larger deterministic sample, using exact matcher-input coordinates where recoverable. Candidate quantities include roof-versus-context Agreement@5m, coverage/grid occupancy, match-confidence calibration, and concentration/entropy. PnP and DSM remain downstream evaluation only, not the proposed contribution.
