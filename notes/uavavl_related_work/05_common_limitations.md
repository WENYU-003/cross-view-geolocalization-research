# 05 — Common Limitations and Research-Opportunity Filtering

## 1. Scope and interpretation

This analysis uses the 12-method Phase 3 comparison set. “Addressed” means a method explicitly contains a mechanism or evaluation for the limitation; it does **not** mean the problem is solved. Frequency is used to find persistent gaps, not to vote for an idea.

Evidence labels:

- **[P]** primary paper explicitly supports the statement;
- **[O]** our retained AnyVisLoc reproduction record supports it; raw artifacts are still missing;
- **[I]** inference or hypothesis requiring validation.

Frequency status:

- **A** — explicitly/directly addresses;
- **P** — partially addresses or uses a proxy;
- **I** — ignores / does not represent;
- **U** — cannot verify or task structure makes comparison uncertain.

## 2. Cross-paper frequency summary

| ID | Common limitation | A | P | I | U | Phase 3 interpretation |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| L1 | Cross-view representation, scale, and local-structure inconsistency | 9 | 2 | 1 | 0 | Widely recognized; improved but not solved across map modalities |
| L2 | Retrieval similarity is not final localizability | 2 | 3 | 3 | 4 | Clear gap in global-search pipelines; some direct-pose methods avoid rather than solve it |
| L3 | Match confidence/count is not spatially useful geometry | 4 | 5 | 3 | 0 | Many methods produce better matches, few calibrate them for final pose robustness |
| L4 | Retrieval, matching, and pose objectives/interfaces are misaligned | 5 | 3 | 2 | 2 | Latest unified methods address architectural separation, not necessarily calibrated localizability |
| L5 | Map/DSM validity and PnP solvability/conditioning are weakly represented | 1 | 5 | 2 | 4 | Strong gap in 2.5D-map pipelines; direct-pose methods often bypass PnP |
| L6 | Sensitivity to noisy/missing orientation, scale, or state priors | 3 | 3 | 4 | 2 | Recognized, but protocols and priors differ substantially |
| L7 | Pipeline error propagation and attribution remain incomplete | 4 | 4 | 2 | 2 | Unified methods align objectives but can reduce diagnostic transparency |
| L8 | Repeated extraction and Top-K pairwise computation | 3 | 4 | 3 | 2 | Shared features are established prior art; efficiency alone has high novelty risk |
| L9 | Generalization across unseen scenes and reference modalities | 4 | 5 | 1 | 2 | Actively studied, but aerial↔satellite/orthomap transfer remains benchmark-dependent |

Counts sum to 12 per row. The method-level assignments and evidence are in `04_comparison_matrix.csv`; borderline cases are marked Partial or Unknown rather than forced into a conclusion.

### Frequency assignment ledger

Abbreviations: `AVL` AnyVisLoc, `Ort` OrthoLoC, `Pv2` PiLoT v2, `3DG` 3D Geometric Perception, `PiL` PiLoT, `Bear` Bearing-UAV, `Air` AirLock+, `C2F` Coarse-to-Fine UAV, `CAMP`, `RoMa`, `R2F` R²Former, `Sela` SelaVPR.

| ID | A — explicitly addresses | P — partial/proxy | I — ignores | U — unverified/non-comparable |
| --- | --- | --- | --- | --- |
| L1 | Ort, Pv2, 3DG, PiL, Bear, Air, C2F, CAMP, RoMa | AVL, Sela | R2F | — |
| L2 | 3DG, Bear | AVL, Air, C2F | CAMP, R2F, Sela | Ort, Pv2, PiL, RoMa |
| L3 | Ort, Pv2, PiL, Air | AVL, 3DG, Bear, C2F, RoMa | CAMP, R2F, Sela | — |
| L4 | Pv2, 3DG, PiL, Bear, R2F | AVL, Air, Sela | CAMP, RoMa | Ort, C2F |
| L5 | Ort | AVL, Pv2, PiL, Air, C2F | CAMP, RoMa | 3DG, Bear, R2F, Sela |
| L6 | AVL, Pv2, Bear | PiL, Air, C2F | CAMP, RoMa, R2F, Sela | Ort, 3DG |
| L7 | AVL, Ort, Pv2, 3DG | PiL, Bear, R2F, Sela | CAMP, RoMa | Air, C2F |
| L8 | Pv2, R2F, Sela | AVL, 3DG, PiL, Bear | Air, CAMP, RoMa | Ort, C2F |
| L9 | AVL, Ort, Air, CAMP | Pv2, 3DG, Bear, RoMa, Sela | R2F | PiL, C2F |

`U` includes methods whose task removes the exact interface, such as direct-pose systems without PnP. It must not be interpreted as a negative result.

## 3. Representation-level limitations

### L1. Cross-view representation remains inconsistent across geometry, scale, and modality

**Evidence.** AnyVisLoc and the 2024 coarse-to-fine work explicitly treat oblique-to-orthographic scale/view changes; RoMa combines DINOv2 coarse features with fine CNN features because coarse foundation tokens alone lack pixel precision [P]. OrthoLoC analyzes domain, resolution, and covisibility shifts [P]. AnyVisLoc Scene_16 satellite references degrade severely relative to aerial references [O-summary].

**Affected methods.** All methods relying on direct appearance features; strongest exposure occurs in CAMP, RoMa, R²Former, and SelaVPR because none internally models georeferenced 3D map validity.

**Latest-method status.** PiLoT, PiLoT v2, and 3D Geometric Perception address the gap through rendering, orthomap registration, or BEV geometry [P]. Bearing-UAV uses relative structural context [P]. These solutions change map/input assumptions and therefore do not establish that the generic low-altitude cross-view representation problem is solved.

**Uncertainty.** [I] Our current evidence does not separate viewpoint, resolution, temporal change, DSM error, and map registration as causes of the Scene_16 satellite failure.

### Within L1: semantic invariance and metric correspondence precision remain competing objectives

**Evidence.** CAMP/R²Former/SelaVPR favor place-level invariance, while RoMa requires a dedicated fine branch for pixel accuracy [P]. DELG/SelaVPR show global/local reuse is feasible, but do not prove the same representation supports UAV-to-DSM PnP.

**Affected methods.** CAMP, R²Former, SelaVPR, AnyVisLoc's separate CAMP/RoMa stack, and any proposed shared feature pipeline.

**Latest-method status.** Shared representations are established. The unresolved question is not whether features can be shared, but whether a shared representation can preserve both cross-view retrieval invariance and geographically accurate local constraints [I].

## 4. Retrieval-level limitations

### L2. Retrieval similarity is not equivalent to candidate localizability

**Evidence.** AnyVisLoc Scene_16 has R@1 68.47% versus R@5 95.25%, while GT-reference RoMa→P3P is highly accurate [O-summary]. This supports candidate ranking as an important interface, but does not prove every retrieval miss is recoverable. CAMP optimizes cross-view place similarity without DSM/PnP evidence [P/I].

**Affected methods.** AnyVisLoc/CAMP, the 2024 coarse-to-fine pipeline, R²Former, SelaVPR, and other Top-K retrieval systems.

**Latest-method status.** R²Former and SelaVPR rerank using local evidence; CAME uses candidate context; 3D Geometric Perception and Bearing-UAV align retrieval more closely with pose [P]. However, VPR pair scores and candidate-context scores remain different from a calibrated probability of successful metric localization [I].

**Final-localization link.** Direct: a visually correct or nearby tile may still lack overlap, usable 3D surfaces, or well-conditioned correspondences.

### Within L2: correct candidates beyond rank 1 can be lost at a hard stage boundary

**Evidence.** AnyVisLoc's Scene_16 R@1/R@3/R@5 gap and Top-N pipeline motivate retaining multiple hypotheses [O-summary].

**Affected methods.** Any hard Top-K retrieval→matching pipeline, including AnyVisLoc and the coarse-to-fine predecessor.

**Latest-method status.** Candidate-context reranking and candidate-wise attention reduce this risk [P], but the failure can persist when all upstream candidates are visually plausible yet geometrically weak [I].

## 5. Matching-level limitations

### L3. Match count or confidence does not guarantee useful spatial coverage

**Evidence.** DKM explicitly argues geometry needs reliable and spatially distributed matches [P]. RoMa outputs dense confidence but does not use AnyVisLoc DSM validity or PnP conditioning [P/I]. AirLock+ uses RANSAC inlier-ratio gating [P], which is stronger than raw count but still tied to a planar model.

**Affected methods.** AnyVisLoc/RoMa, AirLock+, OrthoLoC plug-in matchers, and the coarse-to-fine UAV pipeline.

**Latest-method status.** AdHoP, dense confidence, coarse-to-fine registration, and 3D-grounded alignment all improve correspondence quality. None of the 12 methods is verified to calibrate feature confidence jointly against DSM validity, 3D spatial distribution, and PnP conditioning.

**Final-localization link.** Direct: clustered or nearly coplanar 3D constraints can yield unstable poses even with many inliers [I].

### Within L3: cross-view deformation is handled, but failure calibration is weak

**Evidence.** RoMa, PiLoT, PiLoT v2, OrthoLoC, and AirLock+ each introduce stronger alignment mechanisms [P]. Most report aggregate matching or localization performance, not calibrated per-pair failure probabilities that transfer across maps.

**Affected methods.** Nearly all pairwise registration methods.

**Latest-method status.** Mechanism coverage is mature; a generic “better cross-view matcher” has high novelty risk. The remaining question is whether failure evidence can be tied to the final map-based solver [I].

## 6. Retrieval–matching interface limitations

### L4. Stage objectives and feature spaces are often inconsistent

**Evidence.** AnyVisLoc uses CAMP for retrieval and RoMa for matching, with independently trained representations [P/O]. R²Former, SelaVPR, DELG, and Patch-NetVLAD already demonstrate multiple forms of shared global/local representation [P].

**Affected methods.** AnyVisLoc and other modular pipelines; less so direct-registration systems.

**Latest-method status.** Architectural feature sharing is substantially addressed. What is not verified is joint alignment to **metric localizability**, especially with georeferenced DSM and noisy priors.

**Novelty consequence.** “Share a backbone,” “reuse DINOv2 tokens,” or “add a local reranker” is insufficient as a standalone contribution.

### Within L4: upstream retrieval receives little feedback from downstream failure

**Evidence.** CAMP has no access to RoMa coverage, DSM validity, RANSAC/PnP residuals, or final localization error [P/O]. AnyVisLoc Top-N uses downstream evidence after retrieval, but the retrieval score itself remains independent [P/I].

**Latest-method status.** 3D Geometric Perception couples retrieval and pose in shared geometry; Bearing-UAV directly predicts pose; R²Former/SelaVPR couple retrieval and local similarity [P]. These do not yet establish a general DSM/PnP-aware candidate score.

## 7. Geometry/localization-level limitations

### L5. Map and DSM validity are assumed more often than modeled

**Evidence.** AnyVisLoc uses reference pixels and DSM to create 3D points [P/O]. Scene_16 satellite performance collapses relative to aerial reference [O-summary]. OrthoLoC explicitly studies orthographic geodata resolution/domain/covisibility [P].

**Affected methods.** AnyVisLoc, OrthoLoC, PiLoT v2, PiLoT, and the coarse-to-fine UAV pipeline; analogous map-quality assumptions exist in satellite-only methods.

**Latest-method status.** PiLoT v2 uses TDOM/DSM directly and PiLoT uses a richer mesh [P], but verified evidence does not show an upstream uncertainty model for no-data pixels, map misregistration, wrong surfaces, or local height reliability.

**Final-localization link.** Direct: an apparently correct 2D match can be lifted to a wrong or noisy 3D point.

### Within L5: PnP solvability and conditioning are almost absent from upstream representations

**Evidence.** AnyVisLoc executes RANSAC P3P/PnP but no explicit conditioning-aware score is verified [O/I]. CAMP, RoMa, R²Former, and SelaVPR do not model PnP. PiLoT/PiLoT v2/Bearing-UAV/3D Geometric Perception bypass PnP with direct optimization/regression rather than solve candidate-aware PnP scoring [P].

**Affected methods.** Most directly AnyVisLoc and the coarse-to-fine UAV pipeline.

**Latest-method status.** Not solved in the specific sense of predicting whether a retrieved candidate and its matches will yield a stable DSM-based PnP solution. This is a clear gap, but its practical frequency in AnyVisLoc remains unknown.

**Uncertainty.** [I] We do not yet have per-sample Jacobian/condition measures, 3D point spread, or pose covariance to show that numerical degeneracy is a dominant error source.

## 8. Pose-prior dependency

### L6. Orientation/scale priors improve alignment but can create brittle failure modes

**Evidence.** AnyVisLoc explicitly uses yaw, pitch, and altitude; Scene_16 `yp` versus `p` changes median and tail performance substantially [P/O-summary]. PiLoT v2 explicitly uses gravity and range; PiLoT uses sequential state; AirLock+ uses temporal filtering [P]. Bearing-UAV instead predicts heading [P].

**Affected methods.** AnyVisLoc, PiLoT v2, PiLoT, AirLock+, and possibly the coarse-to-fine pipeline; exact OrthoLoC/3D-Geometric-Perception prior sensitivity is unverified.

**Latest-method status.** The field has several alternative priors, not a standardized robustness solution. Comparisons often change both sensor inputs and task regime.

**Uncertainty.** [I] A complete AnyVisLoc yaw/pitch/altitude noise curve and per-sample interaction with retrieval/matching are missing.

## 9. Pipeline and efficiency limitations

### L7. Error propagation remains hard to attribute in multi-stage systems

**Evidence.** AnyVisLoc is explicitly modular and therefore exposes stages, but the retained repository lacks aligned per-sample outputs [O]. AirLock+ mixes matcher, homography, tracker, and filter. Direct-pose systems improve coupling but make internal error attribution less transparent [I].

**Latest-method status.** No single architecture simultaneously maximizes modular diagnosis, unified optimization, and final-pose calibration.

### L8. Repeated feature extraction and Top-K dense matching are real costs, but crowded novelty territory

**Evidence.** AnyVisLoc normally runs separate CAMP and RoMa encoders and repeats pairwise matching across candidates [O/I]. R²Former, SelaVPR, DELG, and Patch-NetVLAD already address shared global/local computation [P]. LightGlue addresses adaptive sparse compute; PiLoT/PiLoT v2 redesign the registration regime [P].

**Research implication.** Efficiency is valuable as an ablation/engineering objective. It is not currently a strong standalone novelty direction unless tied to a verified UAV-localization failure or a new accuracy–localizability–compute trade-off.

## 10. Generalization limitations

### L9. “Cross-view generalization” is not one transferable property

**Evidence.** OrthoLoC studies country/domain/resolution/covisibility; AirLock+ studies outdated satellite imagery and unseen environments; CAMP evaluates cross-dataset retrieval; RoMa and SelaVPR study broader visual generalization [P]. Their output tasks differ.

**Persistent gap.** A method can generalize in retrieval Recall yet fail in map registration, DSM lifting, or final metric pose. Generalization must be reported per stage and per reference modality.

## 11. Where AnyVisLoc stands in 2026

### 11.1 What was strong in its design

- **[P]** It established a large low-altitude, multi-view UAV benchmark with aerial and satellite 2.5D references.
- **[P]** It placed retrieval, matching, DSM lifting, and pose estimation under one replaceable framework.
- **[P]** PDM@K went beyond pure tile identity by incorporating spatial distance/overlap information.
- **[O]** Separate retrieval-only, oracle-reference, and full-pipeline modes enabled our Scene_16 controlled attribution.
- **[P/O]** It made reference modality and pose-prior sensitivity measurable.

### 11.2 What is now behind newer methods

- Independent CAMP and RoMa objectives/features do not exploit shared geometric context.
- Cross-view alignment is largely delegated to pose-aware preprocessing and a generic matcher.
- Retrieval ranking is not trained against final metric-pose success.
- It does not learn a shared 3D/BEV representation as 3D Geometric Perception does.
- It does not perform direct map registration/pose optimization as PiLoT/PiLoT v2 do.
- It does not directly predict heading/location as Bearing-UAV does.
- No verified upstream representation of DSM uncertainty, PnP solvability, or PnP conditioning exists.

### 11.3 What remains valuable

Its main 2026 value is **not that CAMP→RoMa→PnP is the final SOTA architecture**. Its strongest role is:

1. **Diagnostic platform** — best fit;
2. **Modular research testbed** — equally important for controlled component substitution;
3. **Final-method baseline** — useful as a transparent baseline, but not the expected end-state architecture.

AnyVisLoc's modularity is therefore a research asset: it permits a new front-end mechanism to be tested without conflating retrieval, matching, map geometry, and solver changes.

## 12. Ideas with little standalone novelty remaining

The following broad ideas are already substantially occupied:

- DINOv2 plus a fine pyramid for robust dense matching — RoMa.
- DINOv2 guidance for sparse matching — OmniGlue.
- A shared encoder/global-local heads — DELG, R²Former, SelaVPR, Patch-NetVLAD.
- Top-K learned local reranking — R²Former, SelaVPR; candidate context is further covered by CAME.
- SAM+DINO region-level retrieval — Revisit Anything.
- Direct TDOM/DSM pixel-to-map alignment — PiLoT v2.
- Shared 3D/BEV retrieval, alignment, and pose — 3D Geometric Perception.
- DINOv2/RoMa UAV-to-satellite registration — AirLock+.
- Semantic-object-based scale estimation and satellite cropping — Scale-Aware U2S-CVGL.
- Generic matcher pseudo-training/domain generalization — GIM.

These mechanisms can remain components, but their presence alone cannot support novelty.

## 13. Filtered research opportunities — not proposed methods

### Opportunity 1 — Candidate localizability at the retrieval–matching interface

**Observed common limitation.** Retrieval score and local reranking generally target place identity/similarity, not the probability that a candidate yields a correct, stable metric pose.

**Papers affected.** AnyVisLoc/CAMP, coarse-to-fine UAV localization, R²Former, SelaVPR; partially addressed by 3D Geometric Perception, Bearing-UAV, AirLock+, and CAME.

**Whether latest methods solve it.** No general solution is established for global UAV search with DSM-assisted 2D–3D localization. Newer methods either use direct pose models, local state, candidate context, or non-metric VPR proxies.

**Our evidence.** [O-summary] Scene_16 R@1 is far below R@5, while oracle-reference matching/localization is strong. This supports studying the interface, not a particular scoring design.

**Remaining uncertainty.** We lack per-candidate overlap, match coverage, DSM validity, PnP diagnostics, and final error. It is unknown which signal adds information beyond CAMP score and RANSAC inliers.

**Potential research value.** High if a measurable localizability target predicts final success and changes candidate selection under controlled evaluation.

**Novelty risk.** High: CAME, R²Former, SelaVPR, Bearing-UAV, and 3D Geometric Perception already cover neighboring forms of reranking/unification. A claim must be specific to metric UAV/DSM localization.

### Opportunity 2 — Geometry usefulness of correspondences under imperfect 2.5D maps

**Observed common limitation.** Matcher confidence does not encode whether matches lift to valid, spatially distributed, well-conditioned 3D constraints.

**Papers affected.** AnyVisLoc/RoMa, OrthoLoC, PiLoT v2, coarse-to-fine UAV localization; related generic evidence comes from DKM and MASt3R.

**Whether latest methods solve it.** PiLoT/PiLoT v2 and 3D Geometric Perception integrate geometry more tightly, but no verified representative explicitly models georeferenced DSM validity together with PnP solvability/conditioning.

**Our evidence.** [O-summary] Aerial GT-reference localization is strong, while satellite reference fails badly. This establishes a system-level map/modality bottleneck, not yet a correspondence-geometry cause.

**Remaining uncertainty.** Retrieval failure, appearance shift, DSM resolution, map registration, wrong-surface matches, and PnP degeneracy are still confounded.

**Potential research value.** High if per-sample analysis shows final errors concentrate in low-validity, low-spread, or ill-conditioned correspondence sets.

**Novelty risk.** Medium–high: DKM covers geometry-oriented confidence/sampling; MASt3R covers 3D-grounded matching; OrthoLoC covers geometric preconditioning. The distinction must use georeferenced 2.5D map uncertainty or final metric pose evidence.

### Opportunity 3 — Front-end robustness to uncertain or missing orientation/scale priors

**Observed common limitation.** Pose-aware preprocessing reduces visual difficulty but introduces sensitivity to sensor error and fixed crop/orientation assumptions.

**Papers affected.** AnyVisLoc, PiLoT v2, PiLoT, AirLock+, Scale-Aware U2S-CVGL; Bearing-UAV addresses heading differently.

**Whether latest methods solve it.** No standardized solution. Methods trade yaw/pitch/altitude for gravity/range, temporal state, learned heading, or semantic scale anchors.

**Our evidence.** [O-summary] Scene_16 `yp` substantially outperforms `p`, supporting yaw alignment as important. The exact noise threshold and affected pipeline stage are not known.

**Remaining uncertainty.** Missing full noise curves, raw sensor accuracy, crop transforms, retrieval ranks, and matcher diagnostics under identical perturbations.

**Potential research value.** Medium–high if robustness can be improved in the visual front end without merely adding another sensor or changing the pose solver.

**Novelty risk.** Medium–high: Bearing-UAV predicts heading; PiLoT v2 incorporates gravity/range; Scale-Aware U2S-CVGL estimates scale from objects; learned alignment is broadly studied.

### Why feature reuse is not currently Top 3

Repeated computation is real, but R²Former, SelaVPR, DELG, and Patch-NetVLAD already establish shared retrieval/local features. Our retained experiments also lack timing/memory evidence showing feature recomputation is the primary scientific bottleneck. It should remain an efficiency axis or secondary hypothesis until profiling supports it.

## 14. Phase 4 per-sample evidence required from AnyVisLoc

Before selecting a proposed method, produce one aligned record per query–candidate pair and one record per final query:

### Retrieval and overlap

- stable query/candidate identifiers;
- candidate rank, raw/normalized CAMP score, score margin, and Top-K list;
- GT/reference rank and PDM/physical center distance;
- true pixel/ground overlap or covisibility when derivable;
- reference type, tile footprint, GSD, timestamp/domain metadata.

### Pose-prior preprocessing

- measured yaw, pitch, altitude and their provenance/uncertainty;
- exact rotation, scale, crop center, crop extent, and transforms applied;
- controlled perturbation values and whether the GT footprint remains inside the crop.

### Matching

- attempted/success status and failure code;
- raw match count, retained count, confidence quantiles;
- query/reference coverage: occupied grid cells, convex-hull area, quadrant balance;
- bidirectional consistency and duplicate/reference-collapse statistics;
- match distribution across semantic/texture/map regions when available;
- per-stage runtime and peak memory.

### Map and 2D–3D lifting

- DSM no-data/invalid ratio at matched pixels;
- elevation resolution, local gradient/discontinuity, and registration metadata;
- number of valid lifted 3D points, unique map cells/surfaces, and rejected points;
- 3D spatial extent, covariance/eigenvalues, depth/elevation range;
- image-to-map reprojection consistency before PnP where available.

### PnP and candidate selection

- solver success/failure, iteration count, inlier count/ratio, reprojection residual quantiles;
- spatial distribution of inliers in 2D and 3D;
- Jacobian/Hessian condition proxy, pose covariance or perturbation sensitivity;
- number of competing pose hypotheses and candidate-to-candidate pose agreement;
- candidate selected by CAMP, match confidence, inliers, and final selection rule.

### Final outcome

- translation/position error, orientation error, success thresholds;
- failed/no-pose samples retained in denominators;
- stage-attributed failure code with explicit deterministic criteria;
- comparison across aerial/satellite and `yp`/`p` under identical queries.

The minimum Phase 4 objective is not to train a model. It is to determine whether final failure is most predictable from retrieval rank, visual correspondence quality, map validity, PnP conditioning, or pose-prior error.
