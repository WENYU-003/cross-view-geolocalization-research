# 01 — Anchor Paper: UAV-AVL / AnyVisLoc

## 1. Identity and evidence boundary

**Title:** *Exploring the Best Way for UAV Visual Localization under Low-altitude Multi-view Observation Condition: A Benchmark*

- **[Paper]** Current arXiv record: [arXiv:2503.10692 v2](https://arxiv.org/abs/2503.10692), updated 13 April 2026 and marked accepted by CVPR Findings 2026.
- **[Official code]** Repository: [UAV-AVL/Benchmark](https://github.com/UAV-AVL/Benchmark).
- **[Official code]** The official repository currently cites the accepted work as CVPR Findings 2026, pages 1731–1741.
- **[Uncertainty]** Author lists changed between early arXiv metadata and the current accepted-version citation. Future bibliography must use the final CVF proceedings record rather than silently mixing versions.

This document separates three evidence sources:

1. claims made by the paper;
2. behavior documented by the current official code;
3. findings recorded from our Scene_16 reproduction.

## 2. Research problem

**[Paper]** Input is a low-altitude UAV query image whose field of view lies somewhere inside a geo-referenced aerial or satellite reference map. The output is the UAV camera's absolute position/pose in a GNSS-denied setting.

The hard regime is defined by:

- altitude approximately 30–300 m;
- pitch approximately 20°–90°;
- oblique views containing façades and non-planar structures;
- a large reference-map search space;
- aerial or historical satellite reference modalities.

The central difficulty is therefore not ordinary same-view retrieval. It is coarse-to-fine localization under simultaneous viewpoint, scale, appearance, temporal, and geometric differences.

## 3. Complete pipeline

```text
UAV RGB query Iq
  + intrinsics K
  + approximate altitude / pitch / yaw
        ↓
pose-aware rotation, scale, and search/crop preparation
        ↓
global image retrieval over reference-map tiles
        ↓
Top-K candidate tiles
        ↓
pixel-level query ↔ reference matching for each candidate
        ↓
reference pixels (u, v)
        ↓ georeferenced map XY + DSM elevation Z
world points (X, Y, Z)
        ↓ paired with query pixels
2D query ↔ 3D world correspondences
        ↓ P3P/PnP + RANSAC
candidate camera poses and inlier evidence
        ↓ Top1 or Top-N candidate selection
final UAV pose / position
        ↓
localization error and threshold accuracy
```

The four conclusions must remain separate:

```text
retrieval quality ≠ matching quality ≠ geometric solvability ≠ final localization accuracy
```

## 4. Retrieval stage

**Purpose.** Reduce a map-scale search problem to a small set of image tiles that can afford pixel-level matching.

**[Paper]** Retrieval methods are evaluated with Recall@K and the proposed Pixel Distance Metric PDM@K. The benchmark selects CAMP as the retrieval component of its best combined baseline.

**[Paper]** Deep retrieval weights are evaluated at 384×384 and were trained on University-1652. The paper reports that ConvNeXt-based approaches and training/sampling strategies perform strongly in this benchmark.

**[Official code]** The current demo supports cached reference/gallery retrieval features and exposes `retrieval_k`, `RETRIEVAL_TOPN`, and feature normalization through arguments/config.

**Interpretation.** Retrieval answers “where should expensive matching be attempted?” It does not by itself prove the selected tile can yield geometrically useful correspondences.

## 5. Feature / representation

AnyVisLoc is a benchmark and modular framework rather than a single shared feature encoder.

- **[Paper]** Retrieval and matching methods retain their own pretrained representations.
- **[Official code]** The default retrieval component is CAMP.
- **[Official code]** RoMa uses its outdoor checkpoint and a DINOv2 ViT-L/14 checkpoint in the current demo.
- **[Official code]** Selectable sparse alternatives include SuperPoint/LightGlue-family configurations and other detector/descriptor combinations.

**[Inference]** In the standard pipeline, retrieval features and matcher features have different objectives and are generally extracted by different networks. This creates a plausible feature-recomputation and information-interface issue, but the benchmark does not establish that sharing features would improve accuracy.

## 6. Matching stage

For candidate reference tile `Ir`, the matcher produces:

```text
Iq: [3, Hq, Wq], Ir: [3, Hr, Wr]
        ↓ matcher-specific encoders/correlation
Mq = {(xq_i, yq_i) ↔ (xr_i, yr_i), confidence_i}
```

- **[Paper]** The benchmark compares traditional, sparse learned, and dense learned matchers under the same downstream localization framework.
- **[Paper]** Its best combined baseline uses RoMa and Top-N re-ranking.
- **[Paper]** Matching must handle low overlap, oblique façades versus ortho imagery, repetitive structures, and scale/viewpoint changes.
- **[Official code]** The current runner can cap sparse keypoints, set minimum matches, and configure PnP/RANSAC thresholds.

The relevant output is not simply a high match count. Useful matches must be correct, spatially distributed, and convertible into accurate reference-world points.

## 7. Geometry / localization stage

The matcher initially supplies 2D–2D pairs. The reference side is lifted to 3D:

```text
reference pixel (u, v)
  → geo-reference transform → metric X, Y
  → DSM lookup → elevation Z
  → world point Pw = [X, Y, Z]

query pixel pq ↔ Pw
  → P3P/PnP inside RANSAC
  → camera rotation R and translation t
```

- **[Paper]** The framework uses pixel matching followed by PnP localization.
- **[Official code]** Reference JSON metadata stores map/DSM paths, spatial resolutions, and local coordinate origins; current runners expose P3P/PnP and RANSAC settings.
- **[Inference]** Even visually correct 2D matches can become poor 2D–3D constraints when DSM resolution, map registration, or the selected physical surface is wrong.

PnP is the back-end consumer of front-end evidence. A returned pose is not proof of geographic correctness.

## 8. Pose prior

- **[Paper]** UAV altitude and pitch/yaw are used to estimate image scale and rotation, narrowing the retrieval and matching search space.
- **[Paper]** Gaussian-noise experiments show increasing yaw noise causes substantial degradation; pitch noise is milder over the tested range.
- **[Official code]** `pose_priori=yp` uses pitch, yaw, and altitude for pose-aware view-center estimation and yaw-aligns the map. `pose_priori=p` keeps pose-aware view-center estimation but omits yaw alignment.

This means the evaluated visual front-end is not purely pose-prior-free. Any future claim of viewpoint invariance must control the prior pathway explicitly.

## 9. Dataset and evaluation protocol

- **[Paper]** 18,000 UAV images from 25 regions in 15 Chinese cities.
- **[Paper]** Seven DJI drone types, varied weather, season, illumination, scene, altitude, and pitch.
- **[Paper]** Two 2.5D reference types: aerial orthophoto + aerial DSM, and historical satellite map + ALOS 30 m DSM.
- **[Paper]** Initial component comparisons use 10% of UAV images with aerial maps; the selected combined baseline is then evaluated on the full dataset.
- **[Official code]** Current released data are organized per scene as sample NPZ files plus reference JSON, image maps, and DSM arrays.

**Architectural evaluation caution:** our Scene_16 controlled study is not numerically interchangeable with paper-wide tables.

## 10. Metrics

### Retrieval

- **Recall@K:** whether a useful/overlapping reference occurs in the first K results under the benchmark criterion.
- **PDM@K:** a rank-weighted metric based on normalized spatial distance `Ri = di / (wi × r)`, intended to reflect overlap/localizability across maps with different image widths and spatial resolutions.

### Final localization

- threshold accuracy such as A@5 m, A@10 m, and A@20 m in the paper;
- mean/median localization error and success rates at 1/3/5 m in our retained Scene_16 records;
- processing failures and sample counts must be reported separately from successful-pose accuracy.

**[Uncertainty]** The arXiv abstract reports 74.1% accuracy within 5 m for the best baseline, while the zero-noise reference in the current Table 7 rendering shows 74.6%. Treat this as version/table-context dependent until checked against the final proceedings PDF.

## 11. Main contribution

The paper's contribution is primarily:

1. a large low-altitude, multi-view UAV AVL dataset with aerial and satellite 2.5D references;
2. a unified retrieval → matching → PnP benchmark framework;
3. systematic comparison of component combinations and localization strategies;
4. the PDM@K retrieval metric;
5. analysis of reference type, viewing angle, and prior noise.

It should not be described as proposing a single end-to-end shared representation.

## 12. Architectural assumptions

| Assumption | Evidence | Consequence if violated |
| --- | --- | --- |
| Query FOV lies within the reference map | [Paper] | retrieval has no valid answer |
| Geo-referenced ortho/satellite imagery and DSM are available | [Paper/Official code] | 2D reference pixels cannot be lifted reliably to world points |
| Camera intrinsics and approximate sensor priors are available | [Paper/Official code] | crop, scale, rotation, and PnP may degrade |
| Top-K contains sufficient visual/geographic overlap | [Paper/Inference] | matcher sees unrelated content |
| Matcher outputs correspondences on physically consistent surfaces | [Inference] | RANSAC/PnP may fail or return a wrong pose |
| Map registration and DSM resolution are adequate | [Paper] | systematic 3D point error, especially for satellite reference |
| Candidate inlier/pose evidence correlates with true location | [Inference] | Top-N re-ranking may select a convincing but wrong structure |

## 13. Computational structure

```text
Reference preparation (amortized)
  tile map → retrieval encoding → optional feature cache

Per query
  retrieval encoding + database similarity search
  + K × matcher encoding/correlation
  + K × DSM lookup/PnP verification
```

- **[Official code]** Reference retrieval features can be cached.
- **[Inference]** The dominant online cost is likely matcher-dependent and grows with Top-K, input resolution, and dense correlation/refinement.
- **[Inference]** Separate retrieval and matching backbones generally repeat query/reference encoding, but a shared encoder may trade specialization for efficiency.
- **[Uncertainty]** No local per-stage profile is stored in this repository; efficiency claims require measurement rather than parameter-count intuition.

## 14. Known strengths

- **[Paper]** Makes low-altitude multi-view difficulty measurable across retrieval, matching, localization strategy, reference type, and prior noise.
- **[Paper]** Includes both practically accurate aerial references and more widely available but harder satellite references.
- **[Paper]** PDM@K tries to connect retrieval quality with downstream overlap/localizability.
- **[Official code]** Provides separable full, retrieval-only, and oracle matching/localization modes.
- **[Research summary]** The modular modes enabled our controlled Scene_16 attribution experiments.

## 15. Known limitations and evidence level

| Limitation | Level | Current evidence |
| --- | --- | --- |
| Low-pitch/oblique views reduce global and local similarity | [Paper] | pitch-stratified benchmark analysis |
| Satellite reference is much harder due to resolution, DSM, temporal, and modality gaps | [Paper] + [Research summary] | paper factor analysis; large Scene_16 degradation |
| Performance depends on yaw/pitch/altitude priors | [Paper] + [Research summary] | noise curves; `yp` versus `p` sanity check |
| Rank-1 retrieval misses candidates recoverable within Top-K | [Research summary] | Scene_16 R@1 versus R@3/R@5 and Top-N behavior |
| Dense matching can be expensive | [Paper] + [Inference] | benchmark runtime comparison; no local profile retained |
| Retrieval and matching representations are separately optimized and commonly recomputed | [Official code] + [Inference] | modular model stack; benefit of sharing is unverified |
| Top-N errors can propagate into convincing but wrong PnP solutions | [Paper] + [Research summary] | challenging cases and satellite run; per-sample attribution still missing |
| Generalization from the chosen benchmark/model training data remains uncertain | [Uncertainty] | requires cross-dataset or unseen-domain tests |

## 16. Our reproduced findings — Scene_16

All figures below are **[Research summary]**, not currently backed by raw result files inside this repository.

| Controlled experiment | Recorded result | What it supports | What it does not prove |
| --- | --- | --- | --- |
| CAMP retrieval-only, aerial, `yp`, 295 queries | R@1 68.47%; R@3 92.20%; R@5 95.25%; PDM@1/3/5 0.9624/0.9446/0.9166 | useful candidates often exist beyond rank 1 | that retrieval is the only full-pipeline bottleneck |
| GT reference → RoMa → P3P | mean ≈0.410 m; median ≈0.319 m; SR@1m≈94.92%; SR@3/5m=100% | matching + geometry can be highly accurate with oracle coarse localization | robustness across all scenes/reference types |
| CAMP → RoMa → Top-N → P3P, aerial, `yp` | mean ≈0.474 m; median ≈0.315 m; SR@1m≈89.83%; SR@3m≈99.66% | the complete aerial pipeline works well on Scene_16 | paper-wide reproduction |
| Satellite reference, otherwise similar | mean ≈94.683 m; median ≈7.425 m; SR@1m≈5.42%; SR@3m≈20.68% | reference modality/geometry is a severe system-level factor | which of retrieval, matching, DSM, or registration is causal |
| Aerial `p` instead of `yp` | mean ≈114.194 m; median ≈2.141 m; SR@1m≈42.71%; SR@3m≈51.86% | yaw alignment/prior pathway strongly affects results | a full pose-noise curve or pure visual rotation invariance |

The most important current gap is per-sample alignment across retrieval rank, matcher statistics, DSM validity, PnP inliers, and final error.

## 17. Phase 1 conclusions

Evidence currently supports three research bottleneck families:

1. **candidate quality and retrieval-to-matching interface**;
2. **cross-view correspondence under oblique/satellite gaps**;
3. **dependence on pose-aware rotation/scale preparation**.

It does **not** yet select a proposed method. Feature reuse, DINOv2 multi-scale features, CLIP priors, selective dense matching, and geometry-aware ranking remain candidate mechanisms to be checked against related work and per-sample evidence.
