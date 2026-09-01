# 10 — Failure Mechanism Diagnosis

## Scope and reproducibility

This diagnosis uses only tracked Phase-2 artifacts：

- `unseen_test + Point` 4,197-row per-sample CSV；
- six grouped CMA-Loc JSON files；
- ten saved severe-failure panels；
- released GAGeo code structure。

Recompute the quantitative analysis with：

```bash
python reproductions/gageo/analyze_failure_mechanisms.py
```

All 4,197 samples are from Los Angeles，so city is held constant。No model inference or new baseline run was performed。

## 1. Size does not explain the Ground/Drone gap

| Stratum | Ground severe | Drone severe | Risk ratio Ground/Drone | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Overall | 8.72% | 0.30% | 29.30× | 13.03–65.89× |
| Small | 15.68% | 0.60% | 26.34× | 9.77–71.00× |
| Medium | 7.30% | 0.15% | 49.13× | 6.81–354.29× |
| Large | 3.16% | 0.15% | 21.26× | 2.88–157.00× |

Equal-weight size standardization gives Ground 8.715% vs Drone 0.298%，almost identical to the unadjusted rates。Therefore different Small/Medium/Large proportions do not create the view gap。

Small size is nevertheless a strong **effect modifier**：within Ground，severe failure rises from 3.16% Large to 15.68% Small。It amplifies the mechanism but is not sufficient：Drone Small remains only 0.60%，and Ground Large still has a >21× relative severe rate。

## 2. Ground failure is a catastrophic tail, not uniform degradation

| Task | BBox IoU mean | BBox median | BBox q10 | Mask IoU mean | Mask median | Mask q10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Drone | 0.825 | 0.877 | 0.630 | 0.815 | 0.859 | 0.619 |
| Ground | 0.736 | 0.889 | **0.000** | 0.727 | 0.875 | **0.000** |

Ground median performance is not worse than Drone，but the bottom 10% collapses to zero。For Ground Large，mean mAcc is even comparable to Drone Large，yet severe failures remain 23/727 vs 1/672。The failure mechanism is therefore an unstable wrong-hypothesis mode affecting a subset，not simply globally weak Ground features。

## 3. Detection and segmentation fail together

| Task | `corr(det_iou, mask_iou)` | det IoU=0 | mask IoU=0 | both=0 | P(mask=0 ∣ det=0) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ground | 0.965 | 222 | 222 | 190 | 85.6% |
| Drone | 0.906 | 6 | 6 | 6 | 100% |

BBox and mask heads share the object task token and reference features。Their strong coupling，plus panels where both heads coherently select the same wrong building/region，supports an upstream/shared reference-instance selection failure rather than two independent head failures or only a mask-boundary problem。

The panels are selected examples，not prevalence estimates：all seven stored Ground examples show a plausible but non-overlapping reference object/region；the three Drone examples are rarer and mostly select nearby/repetitive instances。

## 4. Richer prompts do not remove the Ground tail condition

On Unseen data，Mask minus Point aggregate changes are：

| Task | Detection mAcc | Model mIoU | Rotation error |
| --- | ---: | ---: | ---: |
| Drone | +7.42 pp | +3.64 pp | −0.38° |
| Ground | +1.74 pp | +1.39 pp | +0.16° |

Within Ground Small，Mask improves mAcc only +1.38 pp and mIoU +0.98 pp。A richer prompt provides much less benefit exactly where the dominant tail occurs。This argues against “Point prompt contains too little target information” as the primary explanation。It remains possible that the model fails to transmit rich prompt information across the Ground→Satellite interface；that becomes part of the shared interaction limitation，not a raw prompt-annotation limitation。

## 5. Geometry output shows the same view-conditioned stress

For Point prompt：

| Size | Ground−Drone rotation error | Ground−Drone position error |
| --- | ---: | ---: |
| Small | +14.59° | +15.43 px |
| Medium | +9.16° | −0.01 px |
| Large | +6.10° | −3.42 px |

Rotation error is consistently worse for Ground at every size，while position error is not consistently worse。This is compatible with difficulty resolving Ground facade orientation against aerial geometry。It is not proof that rotation error causes localization failure because pose errors are only available as subgroup means，not joined per sample。

## Competing-hypothesis decisions

| Hypothesis | Decision | Reason |
| --- | --- | --- |
| H1 Small-object / scale | **Amplifier, not dominant cause** | strong Ground size gradient；view gap persists 21–49× within size |
| H2 viewpoint / projection discrepancy | **Strongly supported condition-level explanation** | matched-size gap、facade↔roof qualitative mismatch、rotation-error gap；confounded with real/synthetic data source |
| H3 Point prompt insufficient | **Rejected as dominant** | BBox/Mask add little for Ground while helping Drone substantially |
| H4 DINOv2 resolution insufficient | **Unresolved amplifier** | Small effect is real，but no patch-area/intermediate-feature artifact and Drone Small performs well |
| H5 π³ geometry interaction insufficient | **Supported at shared-interface level, exact layer unresolved** | coupled heads、wrong-region commitment、rotation stress；no per-layer/per-sample feature evidence |
| H6 dataset/annotation pipeline difference | **Material alternative explanation** | Ground pairs use real imagery and heuristic cross-view alignment；Drone pairs are synthetic/deterministic；raw annotation audit is unavailable locally |

## Dominant mechanism

> **目前证据最支持的机制是：在 Ground→Satellite 强 facade-to-roof 变化下，GAGeo 的 prompt-conditioned shared cross-view pathway 对少数样本形成不稳定的 reference spatial anchoring，单一 object-task representation 过早锁定到一个语义合理但错误的建筑/区域，随后 bbox 与 mask heads 一致地产生 catastrophic zero-overlap prediction；Small targets 放大该模式，但不产生该模式。**

### Evidence

- size-standardized Ground/Drone severe RR = 29.29×；
- Ground median high but q10=0，证明是 tail collapse；
- bbox/mask correlation 0.965 and 85.6% zero coupling；
- richer Ground prompts improve little；
- Ground rotation error remains higher within all size strata；
- stored panels show coherent wrong-instance/region selection across Small/Medium/Large。

### Counterevidence / alternative

- Ground Large average performance is strong，so the pathway is not universally incapable；
- no per-sample pose join or intermediate features isolate DINOv2 vs π³；
- Ground and Drone differ in acquisition and annotation pipelines，so some tail may be annotation noise。

### Remaining uncertainty

The next raw-data diagnostic must determine whether the correct reference region remains in the feature top-K before the single object token commits。That result decides whether multi-hypothesis verification is viable or whether earlier representation learning is required。
