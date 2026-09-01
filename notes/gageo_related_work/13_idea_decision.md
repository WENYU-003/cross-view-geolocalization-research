# 13 — Idea Decision

> **Status：FROZEN for MVP design；no model implementation or training has started。**

## Decision

**PR-MHA：MODIFY。** Keep multi-hypothesis preservation and verification，but move the intervention from a final-token post-module to the **π³ stage11→final spatial refinement interval**。

Frozen method name：**Late-Spatial PR-MHA**。No competing method remains active for the first MVP。

The full 570-sample evidence rejects a final-token-only interpretation。Ground severe retains more spatial GT recoverability at stage 11 than at final，whereas matched Ground success and Drone success gain sharply over exactly the same interval。The method must protect spatial alternatives before late refinement discards or replaces them。

## Why not the alternatives

- **Multi-scale features only**：likely helps Small targets，but Ground Large retains a 21× severe RR and high average accuracy；resolution alone does not explain the discrete wrong-region mode。
- **More prompt information**：Mask vs Point adds only +1.74 pp Ground mAcc and +1.39 pp mIoU，far smaller than Drone gains；the problem is not simply insufficient input prompt detail。
- **Pose-guided warping first**：Ground rotation prediction is much worse，so using it as a hard guide risks reinforcing the same failed representation。
- **Only hard-negative contrastive loss**：may improve instance discrimination，but existing GAGeo already uses object-level contrastive learning；a loss alone does not guarantee that alternative spatial hypotheses survive late refinement。
- **Final-token-only re-ranking**：acts after final spatial H@8 and GT rank have already degraded，so it is too late for the observed mechanism。

## Closest-method collision check

Targeted primary-source check on 2026-09-01：

- [OCGNet](https://arxiv.org/abs/2505.17911) preserves click location via Gaussian Kernel Transfer、Location Enhancement and multi-head cross attention；therefore “reinject prompt location” is not a defensible standalone novelty。
- [SMGeo](https://arxiv.org/abs/2511.14093) uses query-guided fusion、grid-level experts and heatmap-supervised anchor-free localization；therefore “add a reference heatmap” alone is also weak novelty。
- [TROGeo](https://openaccess.thecvf.com/content/ICCV2025/papers/Zhang_Breaking_Rectangular_Shackles_Cross-View_Object_Segmentation_for_Fine-Grained_Object_Geo-Localization_ICCV_2025_paper.pdf) uses object/context perception and a two-stage SAM prompt stage；segmentation refinement alone is already covered and does not target our shared wrong-region tail。

Modified PR-MHA's current differentiation is the combination of：

```text
stage-11 top-K reference spatial hypotheses
→ preserve candidate identity through late π³ refinement
→ candidate-specific return attention to the original query prompt region
→ reliability-gated fusion before final spatial/task collapse
```

This is a **working novelty position**, not a paper-ready novelty conclusion。A broader related-work matrix remains mandatory before method implementation beyond the MVP。

## Risk decision

The highest technical risk is that the correct reference instance is already absent from stage-11 top-K for most severe samples：at K=8，`68.4%` are outside top-K。The first MVP must measure larger-K recoverability and test whether verification adds discrimination。Prompt-return is retained as a joint signal，not treated as sufficient alone，because its cohort-level divergence is strong but its per-sample distributions overlap。

The exact insertion block within pair-stages 12–17 is unresolved because stage-17 spatial patches were not exported。The frozen intervention point is therefore an interval：**after pair-stage 11，before final spatial output**。

Implementation decision：inject K spatially anchored candidate tokens immediately after the stage-11 global block，propagate them through the existing frozen late π³ blocks，then use their verified final representations to form a zero-initialized residual correction for the unchanged bbox/mask inputs。When disabled，the original token layout、forward outputs and checkpoint behavior must remain unchanged。
