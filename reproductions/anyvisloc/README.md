# AnyVisLoc Reproduction

## Status
**Core paper-level reproduction completed.**

The reproduction was conducted on the AnyVisLoc benchmark with a primary focus on `Scene_16`, using the official UAV-AVL codebase and an NSCC GPU environment.

## Reproduced Pipeline
```text
UAV Query
    ↓
CAMP Retrieval
    ↓
Reference Candidates
    ↓
RoMa / SP_LG_GIM Matching
    ↓
Reference XY + DSM Z
    ↓
2D-3D Correspondences
    ↓
PnP / P3P
    ↓
Estimated UAV Position
```

## Experiments Completed

### Retrieval-only
CAMP retrieval was evaluated independently to separate retrieval quality from downstream localization.

For Scene_16 / aerial reference:
- Recall@1 ≈ 68.47%
- Recall@3 ≈ 92.20%
- Recall@5 ≈ 95.25%
- PDM@1 ≈ 0.9624
- PDM@3 ≈ 0.9446
- PDM@5 ≈ 0.9166

### GT Reference → RoMa → P3P
This oracle-style experiment isolates matching and pose estimation by providing the correct reference.

Observed results:
- Mean localization error ≈ 0.410 m
- Median localization error ≈ 0.319 m
- SR/T1 ≈ 94.92%
- T3/T5 = 100%

This shows that downstream matching and geometry can achieve strong accuracy when retrieval is correct.

### Full Pipeline: CAMP → RoMa → P3P
For Scene_16 / aerial / yaw-pitch prior:
- 295 / 295 queries completed
- Mean ≈ 0.474 m
- Median ≈ 0.315 m
- SR@1m ≈ 89.83%
- SR@3m ≈ 99.66%

### Satellite Reference
For Scene_16 / satellite / yaw-pitch prior:
- Mean ≈ 94.683 m
- Median ≈ 7.425 m
- SR@1m ≈ 5.42%
- SR@3m ≈ 20.68%
- SR@5m ≈ 32.88%

This is a major failure setting and highlights the cross-view/domain gap between UAV observations and satellite references.

### Pose-Prior Dependence
For aerial reference without the yaw-pitch prior:
- Mean ≈ 114.194 m
- Median ≈ 2.141 m
- SR@1m ≈ 42.71%
- SR@3m ≈ 51.86%

The large degradation shows that pose priors are important in the reproduced configuration.

## Main Findings
1. Correct reference retrieval is critical.
2. RoMa + P3P can achieve sub-meter localization when the reference is correct.
3. Aerial references are substantially easier than satellite references in the reproduced setting.
4. Pose priors strongly affect robustness.
5. More retrieval candidates do not automatically guarantee better localization; candidate ranking and geometric verification matter.
6. Retrieval and matching remain important front-end bottlenecks.

## Failure Analysis
Important failure sources include:
- Incorrect retrieval candidate
- Large aerial/satellite domain gap
- Repetitive or weakly textured regions
- Matching ambiguity
- Sensitivity to pose prior
- Candidate re-ranking/verification errors

## Research Ideas Motivated by the Reproduction

### Feature Reuse
Investigate whether retrieval features can be reused or adapted for later matching/alignment rather than recomputing independent representations.

### Sparse-Guided Coarse-to-Fine Matching
```text
Sparse / Global Matching
        ↓
Reliable Region Selection
        ↓
Selective Dense Matching
        ↓
Geometric Verification
```

The goal is to concentrate expensive dense matching on regions that are likely to be geometrically useful.

## Notes
This document records my reproduction and analysis rather than claiming new benchmark results. Exact settings and additional experiments should be kept together with the corresponding configuration and result files when available.
