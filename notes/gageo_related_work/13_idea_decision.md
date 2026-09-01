# 13 — Idea Decision

## Decision

**Selected working idea：Prompt-Return Multi-Hypothesis Anchoring（PR-MHA）。**

The method is selected because it intervenes on the observed catastrophic-tail mechanism：the model should not compress an ambiguous reference field into one object representation before verifying alternatives。

## Why not the alternatives

- **Multi-scale features only**：likely helps Small targets，but Ground Large retains a 21× severe RR and high average accuracy；resolution alone does not explain the discrete wrong-region mode。
- **More prompt information**：Mask vs Point adds only +1.74 pp Ground mAcc and +1.39 pp mIoU，far smaller than Drone gains；the problem is not simply insufficient input prompt detail。
- **Pose-guided warping first**：Ground rotation prediction is much worse，so using it as a hard guide risks reinforcing the same failed representation。
- **Only hard-negative contrastive loss**：may improve instance discrimination，but existing GAGeo already uses object-level contrastive learning；a loss alone does not guarantee that alternative spatial hypotheses survive the single-token bottleneck。

## Closest-method collision check

Targeted primary-source check on 2026-09-01：

- [OCGNet](https://arxiv.org/abs/2505.17911) preserves click location via Gaussian Kernel Transfer、Location Enhancement and multi-head cross attention；therefore “reinject prompt location” is not a defensible standalone novelty。
- [SMGeo](https://arxiv.org/abs/2511.14093) uses query-guided fusion、grid-level experts and heatmap-supervised anchor-free localization；therefore “add a reference heatmap” alone is also weak novelty。
- [TROGeo](https://openaccess.thecvf.com/content/ICCV2025/papers/Zhang_Breaking_Rectangular_Shackles_Cross-View_Object_Segmentation_for_Fine-Grained_Object_Geo-Localization_ICCV_2025_paper.pdf) uses object/context perception and a two-stage SAM prompt stage；segmentation refinement alone is already covered and does not target our shared wrong-region tail。

PR-MHA's current differentiation is the combination of：

```text
explicit top-K reference spatial hypotheses
→ candidate-specific return attention to the original query prompt region
→ reliability-gated fusion into GAGeo's object task token
```

This is a **working novelty position**, not a paper-ready novelty conclusion。A broader related-work matrix remains mandatory before method implementation beyond the MVP。

## Risk decision

The highest technical risk is that the correct reference instance has already vanished from all top-K π³ features。That risk is cheap to test with the proposed frozen-feature diagnostic，so PR-MHA has a favorable information-gain profile despite medium implementation complexity。
