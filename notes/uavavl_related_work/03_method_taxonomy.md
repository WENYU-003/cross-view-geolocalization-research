# 03 — Method Taxonomy

## 1. Why a mechanism taxonomy

Chronological lists show when papers appeared but not which AnyVisLoc failure they can explain. This taxonomy uses three coordinates:

```text
task/reference setting
× pipeline role
× representation/matching mechanism
```

A paper may occupy multiple cells. The goal is to compare mechanisms under comparable tasks rather than declare one universal ranking.

## 2. Task and reference taxonomy

### 2.1 Required A–L literature coverage

| ID | Literature category | Primary mechanism question | AnyVisLoc connection |
| --- | --- | --- | --- |
| A | UAV / Aerial Visual Localization | How is a UAV metrically localized against aerial, orthophoto, or satellite maps? | Direct task, priors, reference geometry, and localization metrics |
| B | Cross-View Geo-Localization | How are ground/drone/aerial/satellite views mapped into a common location space? | View/domain robustness for coarse candidate search |
| C | Global Image Retrieval | Which global or regional representation places a useful tile in Top-K? | CAMP stage, Recall@K/PDM@K, and candidate quality |
| D | Local Feature Matching | Which detected/described points remain repeatable and geometrically precise? | Sparse matcher alternatives and oracle-reference diagnosis |
| E | Dense / Semi-Dense Matching | How can correspondences survive weak texture, large viewpoint change, and small overlap? | RoMa robustness versus cost; selective refinement motivation |
| F | Geometry-Aware Localization | How are map/depth/camera constraints used to validate matches and estimate metric pose? | DSM lifting, PnP, inliers, and candidate verification |
| G | Cross-View Feature Alignment | How are rotation, perspective, and view-specific structures aligned in feature space? | Oblique UAV versus ortho/satellite gap and pose-prior dependence |
| H | Vision Foundation Models | Which transferable features preserve semantics, structure, or regions across domains? | DINOv2/CLIP/SAM-related feasibility, with task-specific evidence required |
| I | Coarse-to-Fine Matching | How is broad search narrowed without making unrecoverable early decisions? | retrieval → Top-K → matching and possible ROI refinement |
| J | Feature Reuse / Unified Representation | Can global and local tasks share computation or information without losing specialization? | separate CAMP/RoMa encoders and repeated extraction |
| K | Multi-scale / Small-Target Representation | How are fine structures retained while preserving scene context? | small overlap, oblique façades, and low-resolution satellite evidence |
| L | Retrieval + Matching Unified Framework | Can retrieval ranking and correspondence/localization evidence be optimized or reasoned about jointly? | hard stage interface, Top-N rescue, and geometry-aware ranking |

All twelve categories enter discovery, but final paper quotas are determined by evidence and mechanism coverage rather than equal counts.

### 2.2 Task-setting priority

| Category | Core question | Why it matters to AnyVisLoc | Phase 2 priority |
| --- | --- | --- | --- |
| A. UAV / aerial visual localization | Can a UAV camera be metrically localized against a geo-referenced map? | Direct task match; captures priors, map construction, and localization metrics | Highest |
| B. Cross-view geo-localization | Can images from ground/drone/aerial/satellite views share a location representation? | Supplies view-gap representations and retrieval protocols, though often only place ID/ranking | Highest |
| H. Vision foundation models | Which transferable features survive domain/view changes without task-specific retraining? | DINOv2/CLIP/SAM-related features may help, but must be tied to a verified stage | Medium–high |
| K. Multi-scale / small-target representation | Does the useful overlapping structure occupy too few tokens or only one scale? | Relevant to oblique views, small overlap, and satellite-resolution loss | Medium–high |

Task similarity and mechanism similarity are separate. A generic matcher may be Tier 2 even if it never evaluates UAV localization; a UAV paper may be low relevance if it solves only trajectory smoothing.

## 3. Pipeline-role taxonomy

### 3.1 Pipeline-based versus unified

```text
Pipeline-based:
retrieval encoder → Top-K → matcher encoder → geometry

Unified/shared:
shared representation → retrieval + correspondence/verification heads → geometry
```

- **Pipeline-based strength:** modularity, replaceable components, independently pretrained experts.
- **Pipeline-based risk:** objective mismatch, repeated feature extraction, and hard Top-K error propagation.
- **Unified strength:** possible feature reuse and joint consistency.
- **Unified risk:** global invariance and local distinctiveness may compete; training/data cost can rise.

**AnyVisLoc relation:** the anchor is modular/pipeline-based. A unified alternative is not automatically better and needs accuracy–compute ablation.

### 3.2 Global retrieval versus local matching

| Axis | Global retrieval | Local matching |
| --- | --- | --- |
| Typical output | one vector or regional descriptors per image | coordinate-level correspondences/confidences |
| Desired invariance | viewpoint/domain/appearance tolerance | local distinctiveness plus geometric precision |
| Search role | reduce map-scale candidates | establish fine spatial evidence |
| Common failure | correct place below Top-K | wrong/clustered matches despite a useful reference |

**AnyVisLoc relation:** CAMP Recall@1 versus Recall@5 and oracle-reference matching results make this interface a high-priority analysis axis.

### 3.3 Retrieval + matching unified framework

This category includes methods that share features, train the stages jointly, let local evidence affect retrieval, or perform differentiable/learned candidate verification.

Important distinctions:

- shared backbone only;
- shared backbone plus separate heads;
- local descriptors aggregated into a global descriptor;
- retrieval-conditioned local refinement;
- joint training with geometric or localization loss.

Do not treat all as the same “unified” idea.

## 4. Matching-density taxonomy

### 4.1 Sparse

```text
image → keypoint detector + descriptors → limited matches → geometric filtering
```

Efficient when repeatable keypoints exist, but may miss cross-view correspondences under weak texture, severe perspective, or small overlap.

### 4.2 Dense

```text
two feature grids → all/large-region correlation → dense warp/confidence → sampled matches
```

Often more robust to difficult appearance/view changes, but memory and runtime can be high.

### 4.3 Semi-dense / selective dense

```text
coarse/global evidence → reliable tokens or ROI → dense refinement only there
```

This is a mechanism class, not yet our proposed method. It is important because it could preserve difficult-match robustness while limiting Top-K matching cost.

**AnyVisLoc relation:** the retained RoMa versus sparse-matcher trend motivates this axis, but exact per-sample and runtime evidence still needs recovery.

## 5. Scale and search taxonomy

### 5.1 Single-scale versus multi-scale

- **Single-scale:** simpler and cheaper, but one token/grid resolution may erase small structures or lack context.
- **Multi-scale:** combines semantic context with spatial detail, but fusion and memory cost matter.

Required Phase 2 distinction: image pyramids, CNN feature pyramids, intermediate ViT layers, and token resampling are different mechanisms.

### 5.2 Coarse-to-fine matching

```text
coarse map/image retrieval
→ coarse correspondence or candidate verification
→ local ROI / higher-resolution features
→ precise matches
→ geometry
```

Important questions are what defines “coarse,” how uncertainty is propagated, and whether the fine stage can recover a coarse error.

**AnyVisLoc relation:** Top-N retrieval followed by RoMa is already coarse-to-fine at the pipeline level. A novel method must improve the interface or refinement mechanism, not merely rename the existing pipeline.

## 6. Backbone taxonomy

### 6.1 CNN

Locality and feature pyramids are natural; strong cross-view retrieval methods often use CNN/ConvNeXt backbones. Examine receptive field, resolution, and training strategy rather than treating all CNNs alike.

### 6.2 ViT / Transformer

Patch tokens and global self-attention can model long-range structure, but patch size and layer choice affect spatial precision. Inspect whether methods use CLS/global pooling, patch tokens, intermediate layers, or cross-attention.

### 6.3 Foundation model

- **DINOv2-like:** self-supervised visual structure and patch features; potentially useful for local correspondence and transferable geometry.
- **CLIP-like:** image–text aligned semantic embedding; potentially robust to appearance categories but not guaranteed to preserve pixel geometry.
- **SAM-related:** segmentation-oriented region features/masks; potentially useful for stable-region selection, not automatically a localization descriptor.

**Rule:** “uses a foundation model” is not a mechanism or novelty claim. Record feature layer, tensor resolution, frozen/trainable state, adaptation, and downstream objective.

## 7. Representation-objective taxonomy

### 7.1 Semantic versus geometric representation

- **Semantic representation:** groups visually/linguistically related content, useful for domain tolerance and place context.
- **Geometric representation:** preserves coordinate-level structure and repeatable local evidence.

The objectives can conflict: a feature invariant to local changes may be good for retrieval but insufficiently precise for matching.

### 7.2 Independent features versus feature reuse

```text
Independent:
Fg = Eg(I) for retrieval
Fl = El(I) for matching

Reuse:
Fshared = E(I)
global head(Fshared) → retrieval
local head/layers(Fshared) → matching
```

Key comparison dimensions:

- shared computation versus shared supervision;
- reuse of query features, reference features, or both;
- frozen foundation features versus trained task features;
- loss of retrieval invariance or local precision;
- cacheability and memory footprint.

**AnyVisLoc relation:** separate CAMP and RoMa encoders make reuse attractive for efficiency, but current evidence does not show that a shared feature can preserve both tasks.

## 8. Alignment taxonomy

### 8.1 No explicit alignment

Learn viewpoint invariance entirely through training/data augmentation and similarity learning.

### 8.2 Pose-prior alignment

Use altitude/yaw/pitch to rotate, scale, or crop before retrieval/matching. This reduces search difficulty but transfers robustness requirements to sensors.

### 8.3 Learned cross-view alignment

Use spatial transformers, polar transforms, cross-attention, deformable sampling, feature warping, or view-conditioned tokens.

### 8.4 Geometry-aware alignment

Use epipolar, depth, DSM, camera, 3D, or reprojection constraints to restrict or score correspondence.

**AnyVisLoc relation:** the anchor combines pose-prior preprocessing with downstream DSM/PnP, but retrieval similarity itself is not equivalent to geometry-aware localizability.

## 9. Similarity and geometry taxonomy

### 9.1 2D similarity

Image/vector similarity or 2D correspondence confidence without explicit world geometry. Efficient for retrieval and matching, but repeated patterns can appear convincing.

### 9.2 Geometry-aware matching / ranking

Use geometric consistency before final pose selection:

- correspondence spatial coverage;
- robust model inliers/residuals;
- DSM-valid points;
- reprojection consistency;
- multi-candidate pose agreement;
- uncertainty calibrated to final localization.

**AnyVisLoc relation:** Top-N re-ranking already uses downstream evidence. Future novelty must specify what new geometric signal is introduced and why it detects failures missed by inlier count/PnP.

## 10. Pose-prior dependence taxonomy

| Class | Definition | Evaluation requirement |
| --- | --- | --- |
| Prior-dependent | alignment/search assumes reasonably accurate yaw/pitch/altitude | report sensor/noise settings and degradation curve |
| Prior-assisted | can run without prior but improves with it | compare identical visual model with/without prior |
| Prior-independent | no orientation/scale prior in the visual pipeline | test rotations, oblique pitch, and search-area scaling explicitly |

**AnyVisLoc relation:** `yp` versus `p` is not a complete prior-independent comparison because both retain pose-aware center/scale information in the current code.

## 11. Phase 2 coverage matrix

The shortlist should collectively cover:

| Cell | Minimum strong representatives |
| --- | ---: |
| Direct UAV AVL with aerial/satellite reference | 4 |
| Cross-view retrieval/alignment | 3 |
| Sparse and dense matching under extreme view change | 3 |
| Geometry-aware localization/candidate verification | 2 |
| Coarse-to-fine or selective refinement | 2 |
| Feature reuse/unified representation | 2 |
| Foundation/multi-scale representation tied to localization | 3 |

One paper may cover multiple cells. These are coverage goals, not a requirement to inflate the final paper count.

## 12. Taxonomy-driven novelty rule

A candidate is not novel merely because it occupies several taxonomy cells. Novelty must instead be argued as one of:

- a new problem formulation;
- a new mechanism that changes information flow;
- a new, evidence-backed insight about the bottleneck;
- an integration whose interaction is necessary and experimentally isolated.

Every future idea must identify its closest cell neighbors, difference, novelty risk, and falsifying experiment.
