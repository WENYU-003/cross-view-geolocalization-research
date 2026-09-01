# 04 — Cross-Paper Comparison Matrix

## 1. Scope and evidence rules

This readable matrix compares the 12 Phase 3 representative methods. The machine-readable source is `04_comparison_matrix.csv`, which contains 47 fields including all localizability axes.

- **[P]**: explicitly supported by the primary paper.
- **[O]**: observed in official code or our retained reproduction record.
- **[I]**: our inference or hypothesis.
- **Unknown / Not Verified**: the primary evidence inspected so far is insufficient.

The tables compare mechanisms, not headline accuracy. Dataset, map scope, initialization, sensor inputs, output pose, and hardware differ too much for direct numerical ranking.

## 2. Task and pipeline position

| Method | Task / view setting | Core pipeline | Final output | Relation to AnyVisLoc |
| --- | --- | --- | --- | --- |
| AnyVisLoc | Low-altitude oblique/downward UAV → aerial or satellite 2.5D map | CAMP retrieval → Top-K RoMa → DSM lift → P3P/PnP | Absolute UAV pose/location | Anchor modular pipeline |
| OrthoLoC | UAV → DOP/orthophoto + DSM | Paired benchmark → AdHoP → plug-in matcher → 6-DoF localization/calibration | 6-DoF pose/calibration | Closest diagnostic benchmark for orthographic geodata |
| PiLoT v2 | Free-view UAV video → TDOM + DSM crop | State crop → learned pixel-to-map registration → sensor-constrained optimization | UAV pose | Direct alternative to RoMa→DSM→PnP |
| 3D Geometric Perception | Multi-view UAV sequence → satellite gallery | VGGT 3D → virtual BEV → retrieval → candidate alignment → pose | Absolute 3-DoF pose | Explicitly unifies AnyVisLoc's separated stages |
| PiLoT | UAV video → rendered geo-referenced 3D mesh | Render references → multi-level registration → JNGO | 6-DoF ego pose + target geolocation | Continuous local registration, not global lost-in-space search |
| Bearing-UAV | Unaligned UAV view → satellite map/context | Global/local structure → relative spatial interaction → pose regression | Position + heading | Moves beyond fixed tile retrieval and explicit PnP |
| AirLock+ | Oblique UAV video → satellite image | DINOv2/RoMa registration → homography → temporal filtering | Target geodetic position | Direct satellite registration, but planar/temporal |
| Coarse-to-Fine UAV | Oblique UAV → satellite + elevation | Global retrieval → GSD adaptation → local matching → pose | UAV location/pose | Closest modular predecessor |
| CAMP | Drone ↔ satellite | Shared ConvNeXt + partition descriptors → retrieval | Ranked place/image | AnyVisLoc retrieval component only |
| RoMa | General difficult image pair | DINOv2 coarse + fine CNN → dense warp/refinement | Dense matches/confidence | AnyVisLoc matcher only |
| R²Former | Mainly street-level VPR | One ViT → global retrieval → token-correlation reranking | Ranked place/image | Feature-reuse and Top-K reranking precedent |
| SelaVPR | Mainly street-level VPR | Frozen DINOv2 + adapters → global retrieval → dense MNN reranking | Ranked place/image | DINOv2 shared global/local precedent |

## 3. Representation, matching, and alignment

| Method | Retrieval representation | Matching / alignment | Resolution / multi-scale | Cross-view mechanism | Feature reuse / unification |
| --- | --- | --- | --- | --- | --- |
| AnyVisLoc | CAMP ConvNeXt global + partitions | RoMa dense coarse-to-fine | Retrieval 384²; RoMa pyramid | Pose-aware rotation/scale/crop + learned features | No cross-stage reuse; modular experts |
| OrthoLoC | Matcher/benchmark dependent | AdHoP preconditioning + plug-in matcher | Resolution and covisibility explicitly analyzed | Adaptive homography | Modular benchmark, not one learned representation |
| PiLoT v2 | No conventional global descriptor | Pixel-to-orthogonal-map registration | Multi-level, exact resolution unverified | Learned free-view ↔ orthomap alignment | Registration/pose coupled; global retrieval absent |
| 3D Geometric Perception | BEV/global patch feature | Candidate-wise alignment in shared 3D space | Patch tokens + BEV; exact scale details unverified | 3D reconstruction and orthorectified BEV | Yes: retrieval, alignment, and pose share geometry |
| PiLoT | No global retrieval | Neural pixel-to-3D feature alignment | Three-level coarse-to-fine | Pose-conditioned rendered references | Unified registration/pose only |
| Bearing-UAV | Global/local structural features | Contextual cross-view interaction / pose regression | Global + local; exact pyramid unverified | Relative spatial encoding | Unified position/heading prediction |
| AirLock+ | DINOv2-based alignment representation | RoMa + RANSAC homography | RoMa pyramid | Synthetic view generation + homography | Multi-component; reuse unverified |
| Coarse-to-Fine UAV | Unknown / Not Verified | Local feature matching after GSD adaptation | Explicit resolution adaptation | Coarse-to-fine cross-view matching | No verified sharing |
| CAMP | ConvNeXt global + position-aware parts | No pixel matching | Regional partitions | Contrastive attribute and partition alignment | Shared query/reference encoder only |
| RoMa | None | Dense warp + confidence + refinement | DINOv2 coarse + fine pyramid | Learned generic two-view correspondence | Unified matcher, not retrieval/localization |
| R²Former | 256-D ViT global feature | Attention-selected token correlation reranker | Top-500 local tokens; no main pyramid | Learned correlation, not UAV-specific | Yes: one ViT for global/local evidence |
| SelaVPR | Adapted frozen DINOv2 global feature | Up-convolved dense local MNN reranking | Dense upsampling, not full pyramid | No explicit UAV alignment | Yes: shared frozen DINOv2 + adapters |

## 4. Geometry, priors, and final localization

| Method | Geometry / 3D | DSM / map substrate | PnP | Pose prior / dependency | Final-localization objective |
| --- | --- | --- | --- | --- | --- |
| AnyVisLoc | Reference 2D pixels lifted to 3D | Aerial or ALOS DSM | Yes, P3P/PnP + RANSAC | Yaw, pitch, altitude; strong Scene_16 sensitivity [O-summary] | Partial: final pose evaluated, components trained separately |
| OrthoLoC | Orthographic geometry and homography refinement | DOP + DSM | Unknown / Not Verified | Unknown / Not Verified | Partial/yes at refinement and evaluation level |
| PiLoT v2 | 2.5D map-aware optimization | TDOM + DSM | No; direct optimization | Gravity + single-point range; structurally dependent | Yes |
| 3D Geometric Perception | VGGT local 3D scene + BEV | Satellite image; no external DSM | No verified PnP | Multi-frame reconstruction instead of yaw/pitch prior | Yes |
| PiLoT | Explicit geo-referenced 3D mesh | 3D mesh | No; JNGO | Sequential state/reference rendering | Yes |
| Bearing-UAV | Relative spatial structure, no verified explicit 3D | Satellite context | No | Predicts heading | Yes |
| AirLock+ | Planar homography | Satellite image; no verified DSM | No | Temporal tracking/filtering | Yes at system level |
| Coarse-to-Fine UAV | Correspondences + elevation | Topographic elevation | Unknown / Not Verified | Unknown / Not Verified | Partial; joint training unverified |
| CAMP | No physical geometry | None | No | None in original retrieval | No |
| RoMa | External geometry only | None | No internal solver | None | No |
| R²Former | Token xy/correlation only | None | No | None | No metric objective |
| SelaVPR | No explicit geometry | None | No | None | No metric objective |

## 5. Localizability matrix

Legend: **Yes** = directly represented; **Partial** = proxy/downstream use only; **No** = absent; **U/N/A** = unverified or structurally not applicable.

| Method | Candidate overlap | Match spatial coverage | Map / DSM validity | Correspondence geometry | PnP solvability | PnP conditioning | Retrieval ↔ localization consistency | Localizability-aware ranking |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AnyVisLoc | Partial: PDM evaluates overlap | Partial: dense matches/RANSAC | Partial: DSM used downstream | Yes, downstream | Partial: solver executed | No explicit metric | Partial: PDM/Top-N bridge only | Partial: geometry after CAMP ranking |
| OrthoLoC | Yes: covisibility analysis | Partial | Partial: modalities/resolution studied | Yes | Partial/unknown solver | Unknown | Cannot verify; retrieval decoupled | U/N/A in paired benchmark |
| PiLoT v2 | Partial: local crop constrains overlap | Partial | Partial: DSM used, invalidity handling unknown | Yes | N/A, direct optimizer | N/A; optimizer conditioning unknown | N/A to global retrieval | No global ranking verified |
| 3D Geometric Perception | Partial: BEV/overlap-aware data | Partial: shared 3D alignment | No explicit map-validity model | Yes | N/A | N/A | Yes structurally | Partial/yes; exact ranking loss unverified |
| PiLoT | Partial: rendered local bundle | Partial: dense alignment | Partial: mesh assumed valid | Yes | N/A | N/A | N/A to global retrieval | N/A |
| Bearing-UAV | Partial/yes for unaligned context | Partial: local structure, no explicit matches | No | Partial: relative spatial structure | N/A | N/A | Yes structurally | Partial; no explicit localizability score verified |
| AirLock+ | Partial: registration/inliers | Partial: RANSAC inlier ratio | Partial: outdated map tested | Yes, homography | N/A | N/A | Partial | Partial/unknown candidate policy |
| Coarse-to-Fine UAV | Partial | Unknown | Partial: elevation used | Yes downstream | Unknown | Unknown | Partial/unknown | Unknown |
| CAMP | No explicit overlap objective | No | No | No | No | No | No | No |
| RoMa | Partial pair matchability | Partial dense coverage | No | Partial; external solver only | No | No | N/A | No |
| R²Former | No physical overlap objective | No explicit coverage | No | Partial xy/correlation | No | No | Partial for VPR only | No metric localizability |
| SelaVPR | No physical overlap objective | Partial dense MNN | No | No explicit geometry | No | No | Partial for VPR only | No metric localizability |

## 6. Compute, training, and reproducibility

| Method | Training requirement | Online computation | Official code status | Comparison caution |
| --- | --- | --- | --- | --- |
| AnyVisLoc | Separately pretrained CAMP and RoMa | Retrieval + K dense matches + K pose checks | Available | No retained normalized per-stage profile |
| OrthoLoC | Matcher dependent; AdHoP details need extraction | Matcher + refinement + localization | Available | Paired benchmark is not full global search |
| PiLoT v2 | Dedicated geometric cross-view training | CPU crop + registration + optimization | Not verified | Recent preprint; hardware/code unverified |
| 3D Geometric Perception | Learned VGGT/DINO retrieval/alignment/pose | 3D reconstruction + BEV + Top-K attention | Not verified | Multi-frame input changes compute/task assumptions |
| PiLoT | Million-scale synthetic training | Render thread + multi-level optimization | Available | Uses local state and heavy 3D map |
| Bearing-UAV | Bearing-UAV-90k supervised training | Unified cross-view pose inference | Available | Exact compute/tensor details need extraction |
| AirLock+ | Synthetic cross-view training | DINOv2/RoMa + RANSAC + temporal filter | Project page; code unverified | Tracker/filter contributions are confounded |
| Coarse-to-Fine UAV | Unknown / Not Verified | Retrieval + local matching + pose | Not verified | Full implementation fields incomplete |
| CAMP | Paired CVGL training | One encoder pass/image + descriptor search | Available | Retrieval-only method |
| RoMa | Geometric correspondence training | Dense pairwise matching per candidate | Available | Top-K cost depends on resolution and K |
| R²Former | Retrieval + pair-reranking training | One ViT + Top-K token correlation | Available | Mainly street-level VPR |
| SelaVPR | Frozen DINOv2; train adapters | Global extraction + dense local Top-K rerank | Available | Local-feature storage remains |

## 7. Twelve-method horizontal conclusions

1. **AnyVisLoc is the most modular and diagnosable pipeline**, but not the most unified representation.
2. **OrthoLoC is the strongest diagnostic neighbor**, especially for domain shift, resolution, covisibility, and matcher-to-pose analysis.
3. **PiLoT/PiLoT v2 shift from retrieval-plus-matching to direct registration**, but assume local state and richer map/sensor substrates.
4. **3D Geometric Perception is the strongest unified geometric competitor**, sharing 3D/BEV evidence across retrieval and pose.
5. **Bearing-UAV replaces tile identity with direct location/heading prediction**, improving task alignment but reducing explicit correspondence diagnostics.
6. **AirLock+ proves DINOv2/RoMa satellite registration is already occupied**, while planar/temporal assumptions distinguish it from DSM/PnP localization.
7. **The 2024 coarse-to-fine method shows AnyVisLoc's high-level pipeline is not itself novel**; AnyVisLoc's value lies in scale, benchmark breadth, and analysis.
8. **CAMP optimizes retrieval identity, not final geometric solvability**.
9. **RoMa optimizes difficult correspondence, not map validity or PnP conditioning**.
10. **R²Former already unifies Transformer retrieval and learned reranking**, blocking a broad shared-ViT claim.
11. **SelaVPR already reuses frozen DINOv2 for global and dense local VPR**, blocking a broad foundation-feature-reuse claim.
12. Across all 12 methods, **explicit PnP conditioning and a calibrated candidate-localizability score remain uncommon**, although several newer methods bypass PnP through direct pose optimization.

## 8. Primary sources

- AnyVisLoc: https://arxiv.org/abs/2503.10692
- OrthoLoC: https://papers.neurips.cc/paper_files/paper/2025/hash/2f6a83edafb6b37a80487ce0a6a47e96-Abstract-Datasets_and_Benchmarks_Track.html
- PiLoT v2: https://arxiv.org/abs/2606.31098
- 3D Geometric Perception: https://arxiv.org/abs/2604.01747
- PiLoT: https://openaccess.thecvf.com/content/CVPR2026/html/Cheng_PiLoT_Neural_Pixel-to-3D_Registration_for_UAV-based_Ego_and_Target_Geo-localization_CVPR_2026_paper.html
- Bearing-UAV: https://openaccess.thecvf.com/content/CVPR2026/html/Liu_Beyond_Matching_to_Tiles_Bridging_Unaligned_Aerial_and_Satellite_Views_CVPR_2026_paper.html
- AirLock+: https://openaccess.thecvf.com/content/WACV2026/html/Deng_AirLock_Scaling_UAV-to-Satellite_Image_Registration_for_Target_Geolocalization_and_Geospatial_WACV_2026_paper.html
- Coarse-to-Fine UAV: https://doi.org/10.1016/j.isprsjprs.2024.05.006
- CAMP: https://www.skyearth.org/publication/papers/2024_acvglmucampap.pdf
- RoMa: https://openaccess.thecvf.com/content/CVPR2024/html/Edstedt_RoMa_Robust_Dense_Feature_Matching_CVPR_2024_paper.html
- R²Former: https://openaccess.thecvf.com/content/CVPR2023/html/Zhu_R2Former_Unified_Retrieval_and_Reranking_Transformer_for_Place_Recognition_CVPR_2023_paper.html
- SelaVPR: https://openreview.net/pdf?id=TVg6hlfsKa
