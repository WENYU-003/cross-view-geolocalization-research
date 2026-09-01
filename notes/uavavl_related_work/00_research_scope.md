# 00 — Research Scope

## 1. Objective

本专题围绕 AnyVisLoc 暴露的前端问题建立 CVPR 2027 method-design knowledge base。目标不是收集最多的论文，而是回答：

1. AnyVisLoc 的成功与失败分别发生在 retrieval、matching、geometry 还是 pose-prior interface？
2. 现有方法用什么机制处理 extreme cross-view gap，而不仅是使用什么 backbone？
3. 哪些 limitation 同时得到 primary literature 和我们实验的支持？
4. 哪些候选改动具有可证伪的机制假设，并能用最小实验验证？
5. 哪些 idea 已被最近工作覆盖，哪些差异只是假组合创新？

## 2. In scope

- UAV / aerial absolute visual localization
- cross-view geo-localization and global retrieval
- sparse, semi-dense, and dense feature matching
- retrieval-to-matching feature reuse or unified representations
- cross-view alignment, multi-scale features, and small-overlap/small-target representation
- ViT and visual foundation features, especially DINOv2
- CLIP or multimodal priors when they address a demonstrated ambiguity
- geometry-aware correspondence, candidate verification, and front-end confidence
- coarse-to-fine or selective refinement that reduces matching cost
- the effect of reference modality and pose priors on front-end robustness

## 3. Out of scope for the main contribution

- replacing P3P/PnP without evidence that the solver is the active bottleneck;
- UAV trajectory smoothing or post-processing as the primary novelty;
- large architecture rewrites before failure attribution;
- model stacking without a mechanism-level hypothesis;
- broad literature lists whose papers cannot be connected to an AnyVisLoc stage or observed failure.

Geometry remains part of evaluation and diagnosis. It is out of scope only as the default location of the proposed-method contribution.

## 4. Anchor questions by stage

| Stage | Research question | Required evidence |
| --- | --- | --- |
| Retrieval | Does a geographically useful candidate enter Top-K, and is rank correlated with downstream localizability? | R@K/PDM@K, candidate distance/overlap, per-sample downstream result |
| Matching | Given a useful reference, are correspondences numerous, well distributed, cross-view stable, and geometrically valid? | oracle-reference runs, match count/confidence/coverage, PnP inliers, reprojection error |
| Geometry | Do good 2D–2D matches become valid 2D–3D points under map/DSM assumptions? | DSM validity, coordinate conversion, inlier ratio, pose residuals |
| Pose prior | Is performance due to the visual representation or to rotation/scale/view-center alignment supplied by sensors? | controlled prior/noise ablation with unchanged visual modules |
| Efficiency | Which features are recomputed, and how does cost scale with Top-K, image size, and dense refinement area? | wall time, memory, feature-cache behavior, per-stage profiling |

## 5. Evidence protocol

For every future limitation or idea, record:

```text
Claim
→ Evidence label
→ Source / artifact
→ Stage affected
→ Alternative explanation
→ Missing measurement
→ Decision enabled
```

Use the following minimum standard:

- paper claims require the primary paper;
- implementation claims require official code/config inspection;
- our results require a command/config/result path and sample count;
- causal claims require a controlled experiment or remain hypotheses;
- version-dependent facts must name the paper/repository version and date checked.

## 6. Phase 1 boundaries

Phase 1 produces an anchor decomposition, taxonomy, and search plan. It does **not** claim that a final related-paper shortlist, common limitation set, candidate method, or novelty conclusion is complete.

The next phase should begin only after this scope and anchor decomposition are reviewed.
