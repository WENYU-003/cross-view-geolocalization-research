# 02 — Phase 2 Related-Paper Index

## 1. Scope, evidence labels, and stop condition

This file records the Phase 2 selected corpus around UAV-AVL / AnyVisLoc. It is an evidence base for later comparison; it does **not** select a proposed method.

- **[P]**: stated by the primary paper.
- **[O]**: verified from the authors' official project/code page.
- **[I]**: our method-level inference; not a paper-reported conclusion.
- **Unknown / Not Verified**: not confirmed from a primary source.

Selection stopped at **25 related papers** because every A–L taxonomy cell has multiple useful representatives and additional candidates were not changing the present mechanism map. The AnyVisLoc anchor is kept as the comparison reference and is not counted as a related paper.

## 2. Anchor reference

| Title | Year / venue | Role | Primary paper | Official code |
| --- | --- | --- | --- | --- |
| Exploring the Best Way for UAV Visual Localization under Low-altitude Multi-view Observation Condition: A Benchmark (AnyVisLoc / UAV-AVL) | 2026, CVPR Findings | Anchor: `retrieval → Top-K pairwise matching → DSM lifting → P3P/PnP` | [arXiv](https://arxiv.org/abs/2503.10692) | [UAV-AVL/Benchmark](https://github.com/UAV-AVL/Benchmark) |

## 3. Selected corpus

| # | Paper | Tier | Taxonomy | Main reason retained |
| ---: | --- | --- | --- | --- |
| 1 | PiLoT v2 | 1 | A, F, G, I, J | Direct TDOM/DSM pixel-to-map registration with sensor priors |
| 2 | Unifying UAV CVGL via 3D Geometric Perception | 1 | A, B, F, G, J, L | Shared 3D/BEV representation for retrieval, alignment, and pose |
| 3 | PiLoT | 1 | A, F, G, I, K | Direct neural pixel-to-3D UAV registration |
| 4 | AirLock+ | 1 | A, B, E, F, G, H | DINOv2/RoMa UAV-to-satellite registration in real trajectories |
| 5 | Scale-Aware U2S-CVGL | 1 | A, B, G, K | Physically interpretable scale estimation and map cropping |
| 6 | Coarse-to-Fine GNSS-Denied UAV Localization | 1 | A, B, D, F, G, I | Closest pre-AnyVisLoc modular coarse-to-fine pipeline |
| 7 | OrthoLoC | 1 | A, D, E, F, G | Orthographic geodata benchmark with controlled retrieval/matching isolation |
| 8 | Bearing-UAV | 1 | A, B, C, G, L | Vision-only absolute location and heading beyond fixed map tiles |
| 9 | UniGeoRS / CAME | 2 | B, C, G, L | Top-ranked candidate context and cross-attention reranking |
| 10 | MMGeo | 2 | A, B, C, H | UAV multimodal compositional retrieval |
| 11 | Beyond Paired Data / CAEVL | 2 | A, B, C, H | Satellite-only self-supervised UAV retrieval training |
| 12 | Sample4Geo | 2 | B, C, J | Strong shared-encoder cross-view retrieval baseline |
| 13 | CAMP | 2 | B, C, G, K | Current AnyVisLoc retrieval component |
| 14 | RoMa | 2 | E, G, H, I, K | Current dense matcher; DINOv2 coarse plus precise fine features |
| 15 | OmniGlue | 2 | D, G, H | Foundation-guided sparse matching, including aerial evaluation |
| 16 | MASt3R | 2 | E, F, H, J | Dense matching grounded in learned 3D pointmaps |
| 17 | DKM | 2 | E, F, I, K | Confidence and spatially balanced sampling for geometry |
| 18 | R²Former | 2 | C, D, J, L | One Transformer for retrieval and learned reranking |
| 19 | SelaVPR | 2 | C, D, H, J, L | Frozen DINOv2 reused for global and local VPR features |
| 20 | GIM | 3 | D, E, H | Cross-domain matcher self-training and generalization |
| 21 | DINOv2 | 3 | H, J | Foundation feature source used by several closest methods |
| 22 | DELG | 3 | C, D, J, L | Foundational shared local/global feature extraction |
| 23 | Patch-NetVLAD | 3 | C, D, I, J, K, L | Shared feature map for retrieval and multi-scale patch verification |
| 24 | LightGlue | 3 | D, I | Adaptive sparse matching efficiency baseline |
| 25 | Revisit Anything | 3 | C, H, J, K | SAM+DINO segment-level retrieval under partial overlap |

**Tier counts:** Tier 1 = 8; Tier 2 = 11; Tier 3 = 6.

## 4. Research-question coverage

| Research question | Taxonomy cells | Representative papers |
| --- | --- | --- |
| How should an oblique UAV frame be localized metrically against orthographic/satellite data? | A, F, G | PiLoT v2, PiLoT, OrthoLoC, coarse-to-fine UAV localization, AirLock+ |
| Can the system avoid treating perspective deformation as appearance noise? | F, G, H | 3D Geometric Perception, PiLoT, PiLoT v2, MASt3R, OrthoLoC |
| How can a useful map candidate reach Top-K under scale, domain, and partial-overlap shifts? | B, C, G, K | CAMP, Sample4Geo, Scale-Aware U2S-CVGL, UniGeoRS/CAME, CAEVL |
| Can Top-K context or local evidence improve ranking? | C, D, L | CAME, R²Former, SelaVPR, Patch-NetVLAD |
| Which matcher survives large viewpoint/domain shift while retaining pixel precision? | D, E, G, H, I | RoMa, OmniGlue, DKM, GIM, MASt3R, LightGlue |
| Can retrieval and matching reuse features without losing task specialization? | J, L | R²Former, SelaVPR, DELG, Patch-NetVLAD, Sample4Geo |
| Can multimodal or region-level evidence handle semantic/partial-overlap ambiguity? | H, K | MMGeo, Revisit Anything, DINOv2 |

All A–L cells from `03_method_taxonomy.md` are covered. No new mechanism class was required, so Phase 2 does not modify the taxonomy file.

## 5. Tier 1 — direct anchor neighbors

### 5.1 PiLoT v2: Pixel-to-Orthogonal Map Alignment for Free-view UAV Geo-localization

- **Identity:** 2026; arXiv preprint; Tier 1; A/F/G/I/J; [paper](https://arxiv.org/abs/2606.31098); official code: **Unknown / Not Verified**.
- **Research problem / task / view:** free-view UAV video localization against TDOM+DSM; oblique perspective query versus orthogonal 2.5D map.
- **Input / backbone / feature:** UAV frame, TDOM, DSM, gravity direction, single-point laser range; dedicated cross-view registration network; multi-level learned features; exact backbone **Unknown / Not Verified**.
- **Retrieval / matching / alignment:** state-conditioned map cropping rather than lost-in-space gallery retrieval; pixel-to-map feature registration; learned cross-view alignment.
- **Multi-scale / multimodal / geometry / pose prior:** multi-level coarse-to-fine; RGB plus 2.5D map and range; DSM-aware pose optimization; gravity and laser range are explicit priors.
- **Supervision / training:** [P] trained using a new large-scale geometrically annotated cross-view dataset; training details beyond the paper record are **Unknown / Not Verified**.
- **Dataset / metrics:** author dataset; pose/localization accuracy and compute/storage comparisons; exact complete benchmark list **Unknown / Not Verified**.
- **Contribution / strength:** [P] replaces PiLoT's 3D mesh rendering with CPU-friendly TDOM/DSM crops while retaining direct registration.
- **Limitation:** [I] depends on TDOM, DSM, gravity, range, and a local map-cropping state; it is not equivalent to global lost-in-space retrieval.
- **Relation / relevance / confidence / notes:** closest direct neighbor for orthomap/DSM alignment; extremely high relevance; high confidence for paper claims, code status unverified.
- **Technical flow:** `UAV frame + gravity/range → map crop → cross-view multi-level features → pixel-to-map registration → constrained pose optimization → UAV pose`.
- **Difference from UAV-AVL:** it learns direct orthomap registration and integrates sensor priors into optimization; AnyVisLoc separately retrieves tiles, runs RoMa, lifts matches with DSM, then uses PnP.

### 5.2 Unifying UAV Cross-View Geo-Localization via 3D Geometric Perception

- **Identity:** 2026; arXiv preprint; Tier 1; A/B/F/G/J/L; [paper](https://arxiv.org/abs/2604.01747); official code: **Unknown / Not Verified**.
- **Research problem / task / view:** multi-frame oblique UAV sequence to satellite gallery and absolute 3-DoF pose.
- **Input / backbone / feature:** UAV sequence plus satellite gallery; VGGT and visual patch features; reconstructed local 3D scene and virtual BEV.
- **Retrieval / matching / alignment:** BEV descriptor retrieves Top-K; Satellite-wise Attention processes candidates; view alignment in a shared geometric space estimates pose.
- **Multi-scale / multimodal / geometry / pose prior:** explicit 3D/BEV geometry; RGB only; multi-scale and external pose prior **Unknown / Not Verified**.
- **Supervision / training:** learned retrieval/alignment/pose framework; exact loss schedule **Unknown / Not Verified**.
- **Dataset / metrics:** recalibrated University-1652 and SUES-200; retrieval recall and meter-level localization.
- **Contribution / strength:** [P] unifies retrieval, view alignment, and pose estimation around a shared explicit 3D representation.
- **Limitation:** [I] requires multiple UAV frames and VGGT reconstruction; runtime and reconstruction failure need independent profiling.
- **Relation / relevance / confidence / notes:** directly challenges AnyVisLoc's decoupled interface; extremely high relevance; high confidence for primary-paper mechanism, reproducibility unverified.
- **Technical flow:** `UAV sequence → VGGT 3D scene → satellite-aligned BEV → satellite retrieval → candidate-wise alignment → absolute 3-DoF pose`.
- **Difference from UAV-AVL:** it makes 3D/BEV the shared representation for all stages; AnyVisLoc uses independent retrieval and matching representations followed by conventional DSM/PnP.

### 5.3 PiLoT: Neural Pixel-to-3D Registration for UAV-based Ego and Target Geo-localization

- **Identity:** 2026; CVPR; Tier 1; A/F/G/I/K; [paper](https://openaccess.thecvf.com/content/CVPR2026/html/Cheng_PiLoT_Neural_Pixel-to-3D_Registration_for_UAV-based_Ego_and_Target_Geo-localization_CVPR_2026_paper.html); [official code](https://github.com/Choyaa/PiLoT).
- **Research problem / task / view:** real-time 6-DoF UAV ego and target localization against a geo-referenced 3D mesh.
- **Input / backbone / feature:** live UAV video and rendered 3D reference views; lightweight three-level UAV-specific feature extractor with predicted uncertainty.
- **Retrieval / matching / alignment:** no conventional global gallery retrieval; rendered reference bundle; direct feature alignment through stochastic pose hypotheses and gradient optimization.
- **Multi-scale / multimodal / geometry / pose prior:** explicit coarse-to-fine multi-level alignment and 3D mesh geometry; RGB plus rendered geometry; initialization/state is used by rendering.
- **Supervision / training:** [P] million-scale synthetic dataset with metric depth, pose, weather, and illumination variation.
- **Dataset / metrics:** public and author benchmarks; ego/target error, pose accuracy, and FPS.
- **Contribution / strength:** direct neural pixel-to-3D registration with reported on-device real-time operation.
- **Limitation:** [P, via PiLoT v2] heavy mesh storage/acquisition and rendering cost.
- **Relation / relevance / confidence / notes:** alternative continuous-registration paradigm; extremely high relevance; very high confidence.
- **Technical flow:** `UAV frame + current state → render 3D references → multi-level features/uncertainty → JNGO coarse-to-fine alignment → 6-DoF ego pose + target geolocation`.
- **Difference from UAV-AVL:** replaces global retrieval, generic pairwise matching, and PnP with state-conditioned rendering and differentiable feature-to-3D registration.

### 5.4 AirLock+: Scaling UAV-to-Satellite Image Registration for Target Geolocalization and Geospatial AR

- **Identity:** 2026; WACV; Tier 1; A/B/E/F/G/H; [paper](https://openaccess.thecvf.com/content/WACV2026/html/Deng_AirLock_Scaling_UAV-to-Satellite_Image_Registration_for_Target_Geolocalization_and_Geospatial_WACV_2026_paper.html); [project](https://airlock-wacv2026.github.io/); official code: **Unknown / Not Verified**.
- **Research problem / task / view:** geolocate targets observed in high-altitude oblique UAV video using satellite imagery.
- **Input / backbone / feature:** UAV video, satellite reference, tracked target pixels; DINOv2 ViT-B/14-based alignment representation and RoMa matching.
- **Retrieval / matching / alignment:** candidate/reference registration with RoMa; RANSAC homography; temporal filtering and homography interpolation.
- **Multi-scale / multimodal / geometry / pose prior:** no confirmed feature pyramid; RGB; planar homography; temporal motion/plausibility priors.
- **Supervision / training:** [P] synthetic physically plausible UAV views from UAV-VisLoc scenes; learned alignment component.
- **Dataset / metrics:** seven real UAV sequences; target geolocation error and trajectory length; paper reports 20.23 m mean error over 7.8 km target trajectories.
- **Contribution / strength:** real-trajectory system under oblique view, outdated satellite imagery, and unseen environments.
- **Limitation:** [I] homography assumes approximate planarity, and tracker/filter contributions confound pure front-end attribution.
- **Relation / relevance / confidence / notes:** direct evidence that DINOv2+RoMa UAV/satellite registration already exists; very high relevance and confidence.
- **Technical flow:** `UAV video → target tracking + cross-view features → RoMa correspondences → RANSAC homography → temporal filtering → geodetic target position`.
- **Difference from UAV-AVL:** estimates 2D map homographies and uses temporal tracking; AnyVisLoc lifts map matches with DSM and solves per-candidate camera pose using PnP.

### 5.5 Scale-Aware UAV-to-Satellite Cross-View Geo-Localization: A Semantic Geometric Approach

- **Identity:** 2026; arXiv preprint; Tier 1; A/B/G/K; [paper](https://arxiv.org/abs/2603.07535); [official code](https://github.com/UAV-AVL/U2S-CVGL).
- **Research problem / task / view:** unknown-scale UAV query to scale-adaptive satellite retrieval.
- **Input / backbone / feature:** UAV RGB, camera intrinsics and pitch; detected small vehicles act as semantic metric anchors; detector backbone **Unknown / Not Verified**.
- **Retrieval / matching / alignment:** estimates physical scale before retrieval and controls the satellite crop/FOV; no pixel-level matching stage confirmed.
- **Multi-scale / multimodal / geometry / pose prior:** explicit scale alignment; semantic objects plus RGB; stereoscopic projection geometry; intrinsics and pitch priors, no altitude/range requirement.
- **Supervision / training:** object detection plus geometric estimator; exact supervision **Unknown / Not Verified**.
- **Dataset / metrics:** DenseUAV+ and UAV-VisLoc+; scale MAPE and localization success.
- **Contribution / strength:** converts scale mismatch into an interpretable physical estimate instead of relying only on feature invariance.
- **Limitation:** [P] usable anchors occur in only 33.7% and 50.5% of images in the two reported settings.
- **Relation / relevance / confidence / notes:** closest prior for scale-aware map crop and pose-prior reduction; very high relevance; high confidence.
- **Technical flow:** `UAV image → vehicle anchors → physical-scale estimate → scale-conditioned satellite crop → cross-view retrieval → location`.
- **Difference from UAV-AVL:** estimates scale from scene semantics; AnyVisLoc primarily derives rotation/scale/search preparation from yaw, pitch, and altitude priors.

### 5.6 A Coarse-to-Fine Visual Geo-Localization Method for GNSS-Denied UAV with Oblique-View Imagery

- **Identity:** 2024; ISPRS Journal of Photogrammetry and Remote Sensing; Tier 1; A/B/D/F/G/I; [paper/DOI](https://doi.org/10.1016/j.isprsjprs.2024.05.006); official code: **Unknown / Not Verified**.
- **Research problem / task / view:** oblique UAV image to satellite-map metric localization under GNSS denial.
- **Input / backbone / feature:** UAV and geo-referenced satellite imagery plus topographic elevation; exact backbone/features **Unknown / Not Verified**.
- **Retrieval / matching / alignment:** global coarse retrieval followed by local feature matching and spatial-resolution adaptation.
- **Multi-scale / multimodal / geometry / pose prior:** scale/GSD adaptation; RGB plus elevation; local correspondences and terrain elevation support pose; exact priors **Unknown / Not Verified**.
- **Supervision / training:** **Unknown / Not Verified**.
- **Dataset / metrics:** two non-overlapping real regions with top-down and front-down imagery; retrieval/localization metrics, exact full protocol **Unknown / Not Verified**.
- **Contribution / strength:** direct modular treatment of oblique view, resolution mismatch, retrieval, fine matching, and terrain-supported pose.
- **Limitation:** [I] decoupled errors from retrieval, adaptation, matching, and elevation require per-stage attribution.
- **Relation / relevance / confidence / notes:** closest architectural predecessor to AnyVisLoc; very high relevance; high confidence for overall pipeline, medium for unverified implementation fields.
- **Technical flow:** `oblique UAV query → global retrieval → GSD adaptation → local matching → map coordinates/elevation → camera pose`.
- **Difference from UAV-AVL:** conceptually similar; AnyVisLoc benchmarks many replaceable components and explicitly evaluates Top-N, aerial/satellite maps, DSM lifting, and pose-prior variants.

### 5.7 OrthoLoC: UAV 6-DoF Localization and Calibration Using Orthographic Geodata

- **Identity:** 2025; NeurIPS Datasets and Benchmarks Track; Tier 1; A/D/E/F/G; [paper](https://papers.neurips.cc/paper_files/paper/2025/hash/2f6a83edafb6b37a80487ce0a6a47e96-Abstract-Datasets_and_Benchmarks_Track.html); [project/code](https://deepscenario.github.io/OrthoLoC/).
- **Research problem / task / view:** UAV 6-DoF localization and calibration using lightweight orthographic geodata under domain/resolution/covisibility shifts.
- **Input / backbone / feature:** 16,425 UAV images from Germany/US paired with DOP/DSM modalities; evaluates multiple existing matchers; no single backbone.
- **Retrieval / matching / alignment:** paired design decouples retrieval from matching; AdHoP adaptively preconditions geometry before a plug-in matcher.
- **Multi-scale / multimodal / geometry / pose prior:** studies resolution; RGB+DOP+DSM; explicit homography preconditioning and 6-DoF geometry; pose-prior details **Unknown / Not Verified**.
- **Supervision / training:** benchmark plus plug-in refinement; exact AdHoP training status **Unknown / Not Verified**.
- **Dataset / metrics:** OrthoLoC; match/localization/calibration metrics, translation error, and controlled shift analyses.
- **Contribution / strength:** direct controlled benchmark and an alignment refinement reported to improve matching and translation error.
- **Limitation:** [I] paired benchmark design partially removes the global search problem; cross-region generalization still requires direct inspection.
- **Relation / relevance / confidence / notes:** closest evaluation neighbor for AnyVisLoc matching-versus-localization attribution; extremely high relevance and confidence.
- **Technical flow:** `paired UAV + orthographic geodata → adaptive homography preconditioning → plug-in matcher → 2D–3D geometry → 6-DoF pose/calibration`.
- **Difference from UAV-AVL:** emphasizes controlled paired matching/calibration and homography preconditioning; AnyVisLoc starts from map-scale retrieval and uses pose-aware preprocessing plus DSM/PnP.

### 5.8 Beyond Matching to Tiles: Bridging Unaligned Aerial and Satellite Views for Vision-Only UAV Navigation (Bearing-UAV)

- **Identity:** 2026; CVPR; Tier 1; A/B/C/G/L; [paper](https://openaccess.thecvf.com/content/CVPR2026/html/Liu_Beyond_Matching_to_Tiles_Bridging_Unaligned_Aerial_and_Satellite_Views_CVPR_2026_paper.html); [official code](https://github.com/liukejia121/bearinguav).
- **Research problem / task / view:** absolute UAV location and heading from unaligned aerial/satellite views without assuming a fixed matching tile.
- **Input / backbone / feature:** UAV RGB and satellite map; global and local structural features with relative spatial encoding; exact backbone **Unknown / Not Verified**.
- **Retrieval / matching / alignment:** predicts pose from neighboring/map features rather than only tile identity; explicit relational structure handles misalignment and sparse regions.
- **Multi-scale / multimodal / geometry / pose prior:** global+local granularity; RGB only; predicts location and heading; external pose prior not reported in verified abstract.
- **Supervision / training:** supervised on Bearing-UAV-90k; full losses **Unknown / Not Verified**.
- **Dataset / metrics:** Bearing-UAV-90k, multi-city; localization error and heading/navigation metrics.
- **Contribution / strength:** avoids the fixed tile accuracy–storage trade-off and treats heading as an output.
- **Limitation:** [I] pose regression may not expose correspondence/DSM failure evidence; transfer outside the new benchmark must be verified.
- **Relation / relevance / confidence / notes:** major 2026 novelty boundary for “beyond tile retrieval” and joint location-heading prediction; extremely high relevance; high confidence.
- **Technical flow:** `UAV image + satellite context → global/local structural features → relative spatial modeling → absolute position + heading → navigation`.
- **Difference from UAV-AVL:** directly predicts location/heading from unaligned map context; AnyVisLoc chooses tiles, produces explicit correspondences, and solves pose geometrically.

## 6. Tier 2 — module-critical papers

### 6.1 UniGeoRS: A Unified Benchmark for Tri-view Geo-Localization / CAME

- **Identity:** 2026; CVPR; Tier 2; B/C/G/L; [paper](https://openaccess.thecvf.com/content/CVPR2026/html/Liang_UniGeoRS_A_Unified_Benchmark_for_Tri-view_Geo-Localization_CVPR_2026_paper.html); official code: **Unknown / Not Verified**.
- **Problem / task / view:** six-direction satellite/UAV/ground retrieval and candidate-context refinement.
- **Input / backbone / feature:** RGB query/gallery; plug-in to several CVGL backbones; global/striped features.
- **Retrieval / matching / alignment:** initial ranking; Rank Distance uses query–gallery and gallery–gallery affinity; bidirectional query–candidate cross-attention reranks Top-K; no pixel correspondence.
- **Multi-scale / multimodal / geometry / pose prior:** no explicit multi-scale; RGB; candidate-neighborhood structure but no physical geometry or pose prior.
- **Supervision / training:** rank plus classification losses; CAME trained as a second-stage module.
- **Dataset / metrics:** UniGeoRS (real+synthetic tri-view); Recall@K and AP.
- **Contribution / strength / limitation:** [P] general candidate-context reranker; directly relevant to R@1 versus R@5; [I] retrieval identity/AP does not prove metric localizability.
- **Relation / relevance / confidence / notes:** maps to CAMP Top-K refinement, not RoMa/PnP; very high relevance; high confidence for mechanism, code unverified.

### 6.2 MMGeo: Multimodal Compositional Geo-Localization for UAVs

- **Identity:** 2025; ICCV; Tier 2; A/B/C/H; [paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Ji_MMGeo_Multimodal_Compositional_Geo-Localization_for_UAVs_ICCV_2025_paper.pdf); [official code/data](https://github.com/YuxiangJi/MMGeo).
- **Problem / task / view:** compose available UAV-side image, point cloud/depth/text information to retrieve a satellite reference without requiring a fully multimodal gallery.
- **Input / backbone / feature:** UAV RGB plus optional point cloud, depth, text; satellite RGB; exact encoders **Unknown / Not Verified**.
- **Retrieval / matching / alignment:** unified multimodal composition projected toward the satellite representation; global retrieval; no verified pixel matching.
- **Multi-scale / multimodal / geometry / pose prior:** multimodal by design; depth/point cloud supplies geometric context; explicit pose prior **Unknown / Not Verified**.
- **Supervision / training:** learned multimodal composition; exact loss **Unknown / Not Verified**.
- **Dataset / metrics:** multimodal extensions of GTA-UAV and UAV-VisLoc; retrieval metrics.
- **Contribution / strength / limitation:** first UAV compositional setting in the paper's claim; robust when modalities are available; [I] sensor availability and global retrieval output limit direct comparison to metric AnyVisLoc.
- **Relation / relevance / confidence / notes:** blocks broad “add CLIP/text/depth multimodality” claims; high relevance; high confidence for paper-level claims.

### 6.3 Beyond Paired Data: Self-Supervised UAV Geo-Localization from Reference Imagery Alone (CAEVL)

- **Identity:** 2026; WACV; Tier 2; A/B/C/H; [paper](https://openaccess.thecvf.com/content/WACV2026/papers/Amadei_Beyond_Paired_Data_Self-Supervised_UAV_Geo-Localization_from_Reference_Imagery_Alone_WACV_2026_paper.pdf); [official code](https://github.com/Tristan-Amadei/caevl).
- **Problem / task / view:** UAV-to-satellite retrieval without paired UAV–satellite training images.
- **Input / backbone / feature:** satellite reference images for training and UAV/satellite RGB at inference; edge-based representation and lightweight autoencoder-derived embedding; exact architecture is config-dependent.
- **Retrieval / matching / alignment:** nearest-neighbor global embedding retrieval; augmentation simulates cross-view/domain shifts; no local correspondence or geometry.
- **Multi-scale / multimodal / geometry / pose prior:** no verified multi-scale; edge+RGB representations; no physical geometry or pose prior.
- **Supervision / training:** self-supervised, non-contrastive, satellite-only training in two stages.
- **Dataset / metrics:** ViLD; Recall@1 within geographic thresholds and GFLOPs.
- **Contribution / strength / limitation:** removes paired-query training requirement with low compute; [I] simulated shift may not cover oblique perspective/DSM errors and output remains coarse retrieval.
- **Relation / relevance / confidence / notes:** important data/generalization baseline for AnyVisLoc retrieval adaptation; high relevance and confidence.

### 6.4 Sample4Geo: Hard Negative Sampling for Cross-View Geo-Localisation

- **Identity:** 2023; ICCV; Tier 2; B/C/J; [paper](https://openaccess.thecvf.com/content/ICCV2023/html/Deuser_Sample4Geo_Hard_Negative_Sampling_For_Cross-View_Geo-Localisation_ICCV_2023_paper.html); [official code](https://github.com/Skyy93/Sample4Geo).
- **Problem / task / view:** ground/satellite and UAV/satellite retrieval with strong hard negatives and a simple architecture.
- **Input / backbone / feature:** paired RGB; weight-shared ConvNeXt-B; mean-pooled global feature.
- **Retrieval / matching / alignment:** cosine/global embedding search; no local matching; implicit shared-space alignment through symmetric InfoNCE.
- **Multi-scale / multimodal / geometry / pose prior:** none explicit.
- **Supervision / training:** paired symmetric contrastive learning; GPS and dynamic visual-similarity hard-negative sampling.
- **Dataset / metrics:** CVUSA, CVACT, University-1652, VIGOR; Recall@K/AP depending on benchmark.
- **Contribution / strength / limitation:** strong simple shared encoder; [I] global descriptor lacks metric correspondence and hard-negative mining requires gallery refresh.
- **Relation / relevance / confidence / notes:** alternative to CAMP retrieval and a novelty blocker for weight sharing; very high relevance and confidence.

### 6.5 CAMP: Contrastive Attributes Mining and Position-Aware Partitioning

- **Identity:** 2024; IEEE TGRS; Tier 2; B/C/G/K; [paper](https://www.skyearth.org/publication/papers/2024_acvglmucampap.pdf); [official code](https://github.com/Mabel0403/CAMP).
- **Problem / task / view:** drone/satellite cross-view retrieval under local misalignment and hard-negative confusion.
- **Input / backbone / feature:** UAV/satellite RGB; shared ConvNeXt-B; global plus position-aware partition features.
- **Retrieval / matching / alignment:** descriptor retrieval; no pixel correspondence; Position-aware Partition Branch plus Contrastive Attributes Mining align/discriminate regional attributes.
- **Multi-scale / multimodal / geometry / pose prior:** regional/multi-part, not a verified feature pyramid; RGB only; no explicit geometry or pose prior.
- **Supervision / training:** paired cross-view classification/metric learning with contrastive attribute mining.
- **Dataset / metrics:** University-1652 and SUES-200; Recall@K and AP.
- **Contribution / strength / limitation:** current AnyVisLoc retrieval baseline with strong cross-dataset results; [I] place-level descriptors do not encode downstream DSM/PnP solvability.
- **Relation / relevance / confidence / notes:** direct baseline; indispensable for controlled retrieval comparison; very high relevance and confidence.

### 6.6 RoMa: Robust Dense Feature Matching

- **Identity:** 2024; CVPR; Tier 2; E/G/H/I/K; [paper](https://openaccess.thecvf.com/content/CVPR2024/html/Edstedt_RoMa_Robust_Dense_Feature_Matching_CVPR_2024_paper.html); [official code](https://github.com/Parskatt/RoMa).
- **Problem / task / view:** dense two-view correspondence under large viewpoint, illumination, texture, and scale changes.
- **Input / backbone / feature:** image pair; frozen DINOv2 coarse features plus dedicated ConvNet fine feature pyramid.
- **Retrieval / matching / alignment:** no retrieval; Transformer match decoder predicts dense warp/probability; coarse-to-fine refinement and confidence sampling.
- **Multi-scale / multimodal / geometry / pose prior:** explicit pyramid; RGB; supplies correspondences to external geometry; no pose prior.
- **Supervision / training:** geometric correspondence supervision; DINOv2 frozen, decoder/refinement learned.
- **Dataset / metrics:** MegaDepth, ScanNet, WxBS; relative-pose AUC/mAA and matching robustness.
- **Contribution / strength / limitation:** combines transferable coarse semantics with pixel-precise fine features; [P] DINOv2 alone is too coarse; [I] Top-K dense execution cost and DSM-localizability remain unmodeled.
- **Relation / relevance / confidence / notes:** current AnyVisLoc matcher; every matching proposal must show incremental value over it; extremely high relevance and confidence.

### 6.7 OmniGlue: Generalizable Feature Matching with Foundation Model Guidance

- **Identity:** 2024; CVPR; Tier 2; D/G/H; [paper](https://openaccess.thecvf.com/content/CVPR2024/html/Jiang_OmniGlue_Generalizable_Feature_Matching_with_Foundation_Model_Guidance_CVPR_2024_paper.html); [official code](https://github.com/google-research/omniglue).
- **Problem / task / view:** sparse feature matching that generalizes to unseen domains, including aerial imagery.
- **Input / backbone / feature:** image pair; SuperPoint local features plus DINOv2 context features.
- **Retrieval / matching / alignment:** no retrieval; position-guided attention injects foundation context into sparse matching and separates appearance/position cues.
- **Multi-scale / multimodal / geometry / pose prior:** no verified pyramid; RGB; correspondences feed external pose estimation; no pose prior.
- **Supervision / training:** learned correspondence matcher with frozen/pretrained foundation guidance.
- **Dataset / metrics:** six diverse domains; matching/relative-pose metrics.
- **Contribution / strength / limitation:** strong zero-shot domain generalization; [I] still limited by detector/keypoint coverage and does not use DSM geometry.
- **Relation / relevance / confidence / notes:** primary blocker for DINOv2-guided SuperPoint/LightGlue ideas; very high relevance and confidence.

### 6.8 Grounding Image Matching in 3D with MASt3R

- **Identity:** 2024; ECCV; Tier 2; E/F/H/J; [paper](https://arxiv.org/abs/2406.09756); [official code](https://github.com/naver/mast3r).
- **Problem / task / view:** accurate dense matching grounded in learned pairwise 3D reconstruction.
- **Input / backbone / feature:** image pair; DUSt3R-derived asymmetric ViT encoder-decoder; pointmaps plus dense local descriptors.
- **Retrieval / matching / alignment:** no global retrieval; reciprocal nearest-neighbor dense descriptor matching jointly with 3D point prediction.
- **Multi-scale / multimodal / geometry / pose prior:** no primary multi-scale claim verified; RGB; explicit learned 3D; calibration/pose not required for pairwise prediction.
- **Supervision / training:** large multi-dataset 3D and correspondence supervision.
- **Dataset / metrics:** matching, relative pose, 3D reconstruction, and localization benchmarks; task-specific metrics.
- **Contribution / strength / limitation:** unifies descriptors with pointmaps; [I] heavy pairwise compute and perspective-image priors may not transfer to orthomaps/DSM.
- **Relation / relevance / confidence / notes:** strongest general prior for geometry-grounded foundation matching; very high relevance and confidence.

### 6.9 DKM: Dense Kernelized Feature Matching for Geometry Estimation

- **Identity:** 2023; CVPR; Tier 2; E/F/I/K; [paper](https://openaccess.thecvf.com/content/CVPR2023/html/Edstedt_DKM_Dense_Kernelized_Feature_Matching_for_Geometry_Estimation_CVPR_2023_paper.html); [official code](https://github.com/Parskatt/DKM).
- **Problem / task / view:** dense correspondence optimized for robust two-view geometry.
- **Input / backbone / feature:** image pair; multi-level CNN features.
- **Retrieval / matching / alignment:** no retrieval; kernel-regression global matcher, embedding decoder, stacked dense warp refinement, confidence-aware balanced sampling.
- **Multi-scale / multimodal / geometry / pose prior:** multi-level; RGB; explicitly considers reliability and spatial distribution for geometry; no pose prior.
- **Supervision / training:** MegaDepth/ScanNet depth/correspondence supervision.
- **Dataset / metrics:** MegaDepth-1500, ScanNet; relative-pose AUC.
- **Contribution / strength / limitation:** links dense confidence and sampling to downstream geometry; [P] unmatchable regions and planar degeneracy remain; [I] does not know DSM validity/PnP conditioning.
- **Relation / relevance / confidence / notes:** evidence that match confidence is not identical to geometry usefulness; high relevance and confidence.

### 6.10 R²Former: Unified Retrieval and Reranking Transformer for Place Recognition

- **Identity:** 2023; CVPR; Tier 2; C/D/J/L; [paper](https://openaccess.thecvf.com/content/CVPR2023/html/Zhu_R2Former_Unified_Retrieval_and_Reranking_Transformer_for_Place_Recognition_CVPR_2023_paper.html); [official code](https://github.com/Jeff-Zilence/R2Former).
- **Problem / task / view:** avoid duplicate global/local models and expensive handcrafted verification in VPR.
- **Input / backbone / feature:** RGB pair; ViT-S/B; one Transformer provides 256-D global feature and attention-selected local tokens with coordinates.
- **Retrieval / matching / alignment:** global nearest-neighbor retrieval; learned reranker consumes local correlations, attention, and xy; outputs pair score rather than pixel matches.
- **Multi-scale / multimodal / geometry / pose prior:** no major multi-scale; RGB; xy is used but no RANSAC/PnP; no prior.
- **Supervision / training:** retrieval ranking/triplet and pairwise reranking objectives; end-to-end/alternating variants.
- **Dataset / metrics:** MSLS, Pitts30k and standard VPR tests; Recall@K, runtime, memory.
- **Contribution / strength / limitation:** explicit shared retrieval/reranking with efficiency analysis; [I] street-level pair scoring does not establish cross-view metric correspondence.
- **Relation / relevance / confidence / notes:** closest precedent for shared ViT tokens and learned Top-K verification; very high relevance and confidence.

### 6.11 SelaVPR: Towards Seamless Adaptation of Pre-trained Models for Visual Place Recognition

- **Identity:** 2024; ICLR; Tier 2; C/D/H/J/L; [paper](https://openreview.net/pdf?id=TVg6hlfsKa); [official code](https://github.com/Lu-Feng/SelaVPR).
- **Problem / task / view:** adapt foundation features to global retrieval and local reranking without separate heavy models.
- **Input / backbone / feature:** RGB; frozen DINOv2 ViT-L/14 plus lightweight adapters; global descriptor and up-convolved dense local features.
- **Retrieval / matching / alignment:** global VPR search; mutual nearest-neighbor dense local matching reranks Top-K without RANSAC.
- **Multi-scale / multimodal / geometry / pose prior:** local upsampling, not a full pyramid; RGB; no explicit geometry or prior.
- **Supervision / training:** train adapters with global triplet and mutual-nearest-neighbor local losses; backbone frozen.
- **Dataset / metrics:** MSLS, Pitts30k, Tokyo24/7 and VPR tests; Recall@K, runtime/storage.
- **Contribution / strength / limitation:** parameter-efficient shared DINOv2 global/local adaptation; [I] learned local score does not guarantee physical geometry and dense feature storage remains.
- **Relation / relevance / confidence / notes:** key novelty prior for reusing DINOv2 across AnyVisLoc stages; very high relevance and confidence.

## 7. Tier 3 — enabling mechanisms

### 7.1 GIM: Learning Generalizable Image Matcher From Internet Videos

- **Identity:** 2024; ICLR Spotlight; Tier 3; D/E/H; [paper](https://openreview.net/forum?id=FU_MJLD8LeY); [official code](https://github.com/xuelunshen/gim).
- **Problem / task / view:** improve zero-shot domain generalization across matcher architectures.
- **Input / backbone / feature:** Internet video frames; supports DKM, RoMa, LoFTR, and LightGlue architectures/features.
- **Retrieval / matching / alignment:** no retrieval; complementary matchers generate pseudo-labels, robust fitting cleans them, and temporal propagation expands supervision.
- **Multi-scale / multimodal / geometry / pose prior:** architecture-dependent; RGB; robust geometry filters pseudo-labels; no pose prior.
- **Supervision / training:** self-training with pseudo-correspondences and strong augmentation.
- **Dataset / metrics:** ZEB and multiple downstream domains; matching/pose metrics.
- **Contribution / strength / limitation:** separates data/generalization strategy from matcher architecture; [I] Internet-video pairs remain mismatched to UAV–orthomap geometry and training is costly.
- **Relation / relevance / confidence / notes:** precedent for “adapt RoMa using pseudo-data”; high relevance and confidence.

### 7.2 DINOv2: Learning Robust Visual Features without Supervision

- **Identity:** 2024; TMLR; Tier 3; H/J; [paper](https://openreview.net/forum?id=a68SUt6zFt); [official code](https://github.com/facebookresearch/dinov2).
- **Problem / task / view:** general-purpose transferable visual representation, not a localization method.
- **Input / backbone / feature:** RGB; ViT-S/B/L/g; CLS and patch tokens.
- **Retrieval / matching / alignment:** none built in; downstream methods define pooling, correspondence, or cross-attention.
- **Multi-scale / multimodal / geometry / pose prior:** fixed native tokenization; no multimodal input, explicit geometry, or pose prior.
- **Supervision / training:** LVD-142M self-supervision with self-distillation and masked modeling; downstream can remain frozen.
- **Dataset / metrics:** broad image- and pixel-level transfer tasks.
- **Contribution / strength / limitation:** strong transferable semantics/structure; [P via RoMa] native features are too coarse for pixel-accurate matching without a fine branch.
- **Relation / relevance / confidence / notes:** already inside RoMa, OmniGlue, SelaVPR, and related methods; “add DINOv2” is not novelty; high confidence.

### 7.3 DELG: Unifying Deep Local and Global Features for Image Search

- **Identity:** 2020; ECCV; Tier 3; C/D/J/L; [paper](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123650715.pdf); [official code](https://github.com/tensorflow/models/tree/master/research/delf).
- **Problem / task / view:** unify global landmark retrieval and local spatial verification.
- **Input / backbone / feature:** RGB; ResNet-50/101; high-level GeM global descriptor plus attentive local features from earlier layers.
- **Retrieval / matching / alignment:** global shortlist, local matching, geometric verification; attention selects local regions.
- **Multi-scale / multimodal / geometry / pose prior:** optional multi-scale inference; RGB; 2D geometric verification; no pose prior.
- **Supervision / training:** image-level labels; joint global/local learning with gradient-flow balancing.
- **Dataset / metrics:** Google Landmarks v2, Revisited Oxford/Paris; mAP and recognition metrics.
- **Contribution / strength / limitation:** classic one-forward global/local feature reuse; [I] landmark retrieval differs sharply from oblique UAV–orthomap matching.
- **Relation / relevance / confidence / notes:** blocks broad “single backbone, two heads” claims; high relevance and confidence.

### 7.4 Patch-NetVLAD: Multi-Scale Fusion of Locally-Global Descriptors for Place Recognition

- **Identity:** 2021; CVPR; Tier 3; C/D/I/J/K/L; [paper](https://openaccess.thecvf.com/content/CVPR2021/papers/Hausler_Patch-NetVLAD_Multi-Scale_Fusion_of_Locally-Global_Descriptors_for_Place_Recognition_CVPR_2021_paper.pdf); [official code](https://github.com/QVPR/Patch-NetVLAD).
- **Problem / task / view:** add locally discriminative verification to robust global VPR while reusing one feature map.
- **Input / backbone / feature:** RGB; VGG16-NetVLAD; full-image descriptor and dense multi-scale patch VLAD descriptors from conv5.
- **Retrieval / matching / alignment:** NetVLAD Top-100; mutual patch matching; homography RANSAC or displacement-consistency score.
- **Multi-scale / multimodal / geometry / pose prior:** explicit patch-size fusion; RGB; 2D spatial consistency; no prior.
- **Supervision / training:** weakly supervised NetVLAD triplet training; patch features reuse the trained feature map.
- **Dataset / metrics:** MSLS and standard VPR/localization datasets; Recall@N.
- **Contribution / strength / limitation:** clear shared retrieval→matching data flow; [I] coarse patch descriptors and street-level geometry may fail under extreme cross-view deformation.
- **Relation / relevance / confidence / notes:** direct feature-reuse precedent; high relevance and confidence.

### 7.5 LightGlue: Local Feature Matching at Light Speed

- **Identity:** 2023; ICCV; Tier 3; D/I; [paper](https://openaccess.thecvf.com/content/ICCV2023/html/Lindenberger_LightGlue_Local_Feature_Matching_at_Light_Speed_ICCV_2023_paper.html); [official code](https://github.com/cvg/LightGlue).
- **Problem / task / view:** accurate sparse local matching with input-adaptive compute.
- **Input / backbone / feature:** keypoints/descriptors from SuperPoint, DISK, ALIKED, SIFT, etc.; matcher has no image backbone.
- **Retrieval / matching / alignment:** no retrieval; self/cross-attention matcher with confidence-driven layer exit and point pruning.
- **Multi-scale / multimodal / geometry / pose prior:** extractor-dependent; RGB; external RANSAC/pose consumes matches; no prior.
- **Supervision / training:** learned correspondence supervision through Glue Factory.
- **Dataset / metrics:** MegaDepth, ScanNet, HPatches and localization tests; pose accuracy and speed.
- **Contribution / strength / limitation:** strong accuracy–latency sparse baseline; [I] cannot recover correspondences absent from the detector and worst-case compute is pair-dependent.
- **Relation / relevance / confidence / notes:** controlled alternative to dense RoMa and blocker for generic adaptive-pruning claims; high relevance and confidence.

### 7.6 Revisit Anything: Visual Place Recognition via Image Segment Retrieval

- **Identity:** 2024; ECCV; Tier 3; C/H/J/K; [paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/08592.pdf); [project](https://revisit-anything.github.io/); [official code](https://github.com/AnyLoc/Revisit-Anything).
- **Problem / task / view:** place recognition under viewpoint change and partial overlap using object/region-level retrieval.
- **Input / backbone / feature:** RGB; SAM segments plus DINOv2 patch features; segment-level VLAD/SuperSegment representation.
- **Retrieval / matching / alignment:** segment-aware image retrieval and partial image matching; no pixel-accurate local matcher.
- **Multi-scale / multimodal / geometry / pose prior:** multiple segments/regions; RGB foundation models; no explicit 3D geometry or pose prior.
- **Supervision / training:** largely frozen foundation components and unsupervised aggregation; exact variants should be checked before reproduction.
- **Dataset / metrics:** diverse VPR benchmarks including viewpoint-shift settings; Recall@K.
- **Contribution / strength / limitation:** [P] segment-level representation improves partial-overlap VPR where global aggregation struggles; [I] segmentation errors and coarse regions do not directly support DSM/PnP.
- **Relation / relevance / confidence / notes:** closest novelty prior for SAM+DINO region selection/retrieval; high relevance and confidence.

## 8. Current closest-method and novelty-risk flags

These are Phase 2 overlap warnings, not a final novelty matrix or proposed method.

| Broad claim that is already occupied | Closest methods | Remaining question, not a novelty claim |
| --- | --- | --- |
| DINOv2 plus a fine feature pyramid for robust dense matching | RoMa | Can a UAV/DSM-specific signal improve final localizability beyond generic match confidence? |
| DINOv2-guided sparse matching | OmniGlue | Does sparse coverage survive the actual low-pitch/satellite failure subset? |
| Shared encoder/features for retrieval and local verification | DELG, Patch-NetVLAD, R²Former, SelaVPR | Can sharing preserve both cross-view invariance and pixel-level PnP precision? |
| Top-K candidate context and learned reranking | UniGeoRS/CAME, R²Former | Can ranking predict downstream geometric solvability rather than place identity only? |
| Geometry-grounded learned matching | MASt3R, PiLoT, 3D Geometric Perception | What advantage remains when georeferenced DSM is already available? |
| TDOM/DSM pixel-to-map alignment | PiLoT v2, OrthoLoC | Which failure is unsolved under global search, imperfect maps, and noisy priors? |
| Scale-aware satellite cropping from semantics | Scale-Aware U2S-CVGL | Is scale error actually causal in AnyVisLoc per-sample failures? |
| SAM+DINO region-level retrieval | Revisit Anything | Do stable regions improve UAV cross-view overlap without erasing metric detail? |
| Cross-domain matcher self-training | GIM | Can pseudo-labels be made valid across oblique UAV and orthographic map modalities? |

## 9. Evidence gaps before Phase 3

- PiLoT v2 and 3D Geometric Perception are recent preprints; official code and full reproducibility are not verified.
- Bearing-UAV, UniGeoRS/CAME, and several 2026 papers require full-PDF inspection for exact loss definitions, tensor resolutions, compute, and ablations.
- The coarse-to-fine 2024 ISPRS paper requires full extraction of backbone, training data, pose-prior settings, and numerical protocol.
- MMGeo requires a modality-by-modality ablation extraction before any CLIP/multimodal conclusion.
- OrthoLoC requires exact AdHoP formulation and its interaction with each tested matcher.
- AnyVisLoc still lacks aligned per-sample retrieval rank, match coverage/confidence, DSM validity, PnP inliers/conditioning, and final error in this repository.
- Compute comparisons are not normalized across hardware, input resolution, Top-K, cached gallery features, or sequential versus global-search settings.
- Paper-reported limitations must remain separate from our `[I]` critiques in the Phase 3 matrix.

## 10. Phase 3 priority set and extraction plan

Phase 3 should begin with these **12 papers**, because together they define the closest task and mechanism boundaries:

1. AnyVisLoc / UAV-AVL (anchor)
2. OrthoLoC
3. PiLoT v2
4. Unifying UAV Cross-View Geo-Localization via 3D Geometric Perception
5. PiLoT
6. Bearing-UAV
7. AirLock+
8. Coarse-to-Fine GNSS-Denied UAV Localization
9. CAMP
10. RoMa
11. R²Former
12. SelaVPR

Planned Phase 3 sequence:

```text
verify final bibliographic/code status
→ extract exact input/output tensors and computation
→ normalize retrieval/matching/geometry/pose-prior fields
→ separate paper-reported evidence from our critique
→ build comparison matrix
→ identify common limitations only where multiple primary sources support them
→ map each limitation to missing AnyVisLoc per-sample evidence
```

Do not turn the “remaining questions” above into a proposed method until the comparison matrix and AnyVisLoc error attribution are available.
