# Scene_16 Solver Correspondence Provenance Audit

## Scope

This CPU-only audit recovers the saved raw RoMa rows, valid 2D-3D solver inputs, PnP/RANSAC inlier indices, final pose, and final error for nine fixed focus samples. It does not rerun retrieval, RoMa, DSM sampling, PnP, or training.

The official runner applies `valid` and passes `uav_pts_original[valid]` with `local_x/local_y/dsm_z[valid]` to PnP. Saved `inlier_indices` index this filtered solver-input array. All nine artifacts satisfy the recorded count/index invariants.

## Artifact availability

- Saved: raw match coordinates and row order; per-row world XYZ; valid mask; solver-input count; inlier indices; final pose; final error.
- Missing: RoMa confidence/certainty, per-inlier reprojection residual, PnP method encoded in the artifact, RANSAC seed, and manual correspondence ground truth.

## Focus-group comparison (median)

| Metric | 2D-consistent catastrophic | Low-Agreement successful |
| --- | ---: | ---: |
| Final error (m) | 88.204 | 1.351 |
| Solver input | 3000.0 | 3000.0 |
| PnP inliers | 1355.0 | 618.0 |
| PnP inlier ratio | 0.452 | 0.206 |
| Solver Agreement@5m | 0.593 | 0.308 |
| Cross-reference-paired inlier fraction | 0.264 | 0.268 |
| Paired-inlier Agreement@5m | 1.000 | 1.000 |
| Paired-inlier aerial/satellite |Z| gap (m) | 10.342 | 9.199 |
| Inlier UAV occupancy | 0.531 | 0.352 |
| Inlier world-XY occupancy | 0.531 | 0.320 |
| Inlier world-XY minor/major | 0.331 | 0.170 |
| Inlier DSM-Z std (m) | 1.073 | 1.374 |
| Predicted Z error (m) | -30.051 | -8.514 |

## Main findings

1. All 3,000 raw matches are valid 2D-3D solver inputs in every focus sample. There is no hidden validity-filter collapse before PnP.
2. Catastrophic cases have more, not fewer, PnP inliers than successful controls. Raw inlier count and ratio therefore do not explain accuracy.
3. 5/5 catastrophic samples retain Agreement@5m >= 0.5 among the PnP inliers that can be cross-reference paired. Only about one quarter of all inliers have a mutual aerial query match, so this does not certify every inlier; within the recoverable paired subset, however, RANSAC did not select correspondences that look worse under the aerial pseudo-reference.
4. Solver/inlier spatial metrics and XY collinearity proxies do not show a common severe collapse unique to all catastrophic samples. Any sample-specific concentration remains a secondary diagnostic, not a group-level explanation.
5. The satellite DSM is coarse and produces quantized Z support. The paired-inlier aerial/satellite Z gap is also large in successful controls, so Z disagreement alone is not sufficient to explain the split. Four neighboring catastrophic samples (L16_0096-L16_0101) nevertheless share a roughly -30 m predicted-Z error together with 88-92 m horizontal error, which is compatible with a wrong/ambiguous pose branch; the saved artifacts lack reprojection residuals and solver configuration needed to prove that mechanism.

## Conclusion and GO / NO-GO

The saved solver provenance does not provide a single stable explanation for the full 2D-consistent catastrophic group. Globally consistent correspondences remain consistent in the recoverable paired-inlier subset after validity filtering and RANSAC selection, while PnP reports many inliers. The evidence therefore does not support the hypothesis that a small low-quality or geometrically collapsed solver subset is the common cause. It does isolate a four-query wrong-pose branch with large coupled XY/Z error, but L16_0012 does not follow it.

`NO-GO` for continuing to deepen this Scene_16 mechanism as a clean frontend-model target. Remaining explanations require manual/native-frame correspondence correctness, local satellite georegistration/orthorectification evidence, or solver reprojection diagnostics that were not saved. Under the agreed decision rule, stop further Scene_16 expansion and reconsider the research direction rather than designing a model from this subgroup.

## Evidence boundary

Aerial-satellite geographic disagreement is a pseudo-reference diagnostic, not manual correspondence truth. PnP inliers mean consistency with the estimated pose under a reprojection threshold; they do not certify geographic identity. The artifact does not save per-point reprojection residuals, so residual-distribution and numerical-conditioning claims remain unavailable.
