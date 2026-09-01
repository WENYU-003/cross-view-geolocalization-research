# Scene_16 Counterexample Mechanism Isolation

## Scope

This audit analyzes the fixed 29-query counterexample shortlist using saved aerial/satellite correspondence artifacts only. It does not rerun retrieval, RoMa, DSM, PnP, or training.

Only 6/29 cases have panels in the existing 24-query RGB audit. Missing visual labels remain explicit and are not inferred from metrics.

## Focus comparison

| Metric (median) | High-Agreement catastrophic (n=6) | Low-Agreement success (n=6) |
| --- | ---: | ---: |
| Final error (m) | 87.982 | 1.021 |
| Agreement@3m | 0.577 | 0.276 |
| Agreement@5m | 0.590 | 0.302 |
| Shared pairs | 823.000 | 822.500 |
| Coherent shift (m) | 0.318 | 7.490 |
| Shift-corrected residual (m) | 1.349 | 6.944 |
| Agree3 support count | 477.500 | 233.000 |
| Agree3 UAV occupancy | 0.570 | 0.336 |
| Agree3 satellite occupancy | 0.625 | 0.320 |
| Agree5 UAV hull coverage | 0.534 | 0.335 |
| Agree5 satellite hull coverage | 0.535 | 0.425 |

## Mechanism isolation result

- 5/6 high-Agreement catastrophic cases have coherent shift <1 m and shift-corrected median residual <2 m. Their aerial and satellite 2D endpoint fields are mutually consistent and broadly supported, yet final errors remain catastrophic.
- The high-Agreement catastrophic group has more Agreement<=3/5m pairs and broader pseudo-correct support than the low-Agreement successful group. Therefore neither pseudo-correct count nor pseudo-correct coverage explains their failure.
- Low-Agreement successful cases show that a minority of support can be sufficient, but the current artifacts do not identify which correspondences actually drove PnP. Several also contain a coherent aerial-satellite offset, indicating that cross-reference disagreement can include map-frame/georegistration effects.
- The stable difference is not repeated-structure ambiguity versus context support. It is a diagnostic split: some catastrophic outcomes are not explained at all by 2D cross-reference consistency, while some successful outcomes violate the aerial-pseudo-reference assumption.
- A narrower frontend-associated subgroup is repeatable inside the shortlist: L16_0208 and L16_0210-L16_0214 are all catastrophic with low Agreement, concentrated support, and large local residual. Compared with the six low-Agreement successes, their median UAV occupancy is 0.344 versus 0.656, satellite normalized HHI is 0.0446 versus 0.0103, and spatial entropy is 0.754 versus 0.904. This supports weak spatial diversity/local inconsistency for this subgroup, but not as a universal explanation of every catastrophic case.

## What is supported

1. Global aerial-satellite Agreement is unsuitable as a per-correspondence localization-utility label.
2. Many mutually consistent and spatially broad 2D pairs are not sufficient for correct final localization.
3. Low cross-reference Agreement is not necessary for failure and can coexist with accurate satellite localization.
4. The 29 cases contain at least two mechanism families and should not be optimized with one undifferentiated frontend objective.
5. Low Agreement becomes more failure-informative when it co-occurs with concentrated support and large residual; Agreement alone is insufficient.

## What remains unconfirmed

- Repeated-structure ambiguity and surrounding-context rescue are visually supported only in a small subset, not the full 29.
- The five 2D-consistent catastrophic cases may reflect common visually wrong matches, satellite DSM/georegistration, or downstream pose instability; current 2D artifacts cannot separate them.
- Exact localization utility requires either solver-selected correspondence provenance or a DSM-free manual/planar landmark correctness protocol in the native reference frame.

## Decision

Do not expand immediately to new scenes and do not design a model yet. First export RGB panels for the 23 currently unviewed counterexamples and, if possible, record which sampled correspondences become solver inputs/inliers without changing the solver. External-scene validation is justified only after the 2D-consistent-catastrophic subgroup is separated from genuine frontend ambiguity.

## Provisional external validation plan

This section is a plan, not an executed experiment. Official scene statistics provide query count, altitude, pitch, and map resolution, but they do not map scene IDs to semantic content or repetitive-structure labels.

- Scene_19 is the provisional viewpoint-diversity candidate: 256 queries and a narrow, strongly oblique 18-34 degree pitch range, unlike Scene_16's 29-90 degree range. Its actual visual-content difference must be confirmed with a CPU-only map/query montage before selection.
- Scene_24 is the provisional resolution-gap candidate: 162 queries, aerial resolution 0.067 m and satellite resolution 0.278 m (about 4.15x), versus Scene_16's 0.042 m and 0.132 m (about 3.14x). It is the smallest fast candidate among the scene-level statistics considered here.
- Scene_15 is the stronger but slightly larger resolution-gap alternative: 300 queries, 0.030 m aerial versus 0.285 m satellite (9.5x). Use it only if Scene_24's visual inventory does not provide the intended stress condition.

Before any GPU work, inspect whether matching+localization artifacts already exist for these scenes and generate a small RGB inventory. If new artifacts are necessary, rerun only controlled aerial-GT-reference and satellite-GT-reference RoMa matching+localization with the same matcher, pose prior, PnP method, keypoint budget, and logging schema. Reuse the analysis code, thresholds, plots, and Scene_16 definitions; do not rerun retrieval or train a model.
