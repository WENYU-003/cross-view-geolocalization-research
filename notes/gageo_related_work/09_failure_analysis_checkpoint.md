# 09 — Failure Analysis Checkpoint

## Population and criterion

**[RESULT_VERIFIED]** Source：[`reproductions/gageo/results/failure_cmaloc_unseen_point.csv`](../../reproductions/gageo/results/failure_cmaloc_unseen_point.csv)。

```text
split: unseen_test (operationally Unseen)
prompt: Point
views: Drone→Satellite + Ground→Satellite
rows: 4197
severe failure: det_iou == 0 AND mask_iou == 0
```

This severe criterion is a reproduction-analysis definition, not an official paper metric。

## Deterministically reverified counts

| Group | Total | Severe | Rate |
| --- | ---: | ---: | ---: |
| Overall | 4,197 | 196 | 4.67% |
| Drone | 2,017 | 6 | 0.30% |
| Ground | 2,180 | 190 | 8.72% |
| Large | 1,399 | 24 | 1.72% |
| Medium | 1,399 | 54 | 3.86% |
| Small | 1,399 | 118 | 8.43% |
| Regular | 3,691 | 190 | 5.15% |
| Irregular | 506 | 6 | 1.19% |

### Task × size

| Task | Size | Total | Severe | Rate |
| --- | --- | ---: | ---: | ---: |
| Drone | Large | 672 | 1 | 0.15% |
| Drone | Medium | 673 | 1 | 0.15% |
| Drone | Small | 672 | 4 | 0.60% |
| Ground | Large | 727 | 23 | 3.16% |
| Ground | Medium | 726 | 53 | 7.30% |
| Ground | Small | 727 | 114 | 15.68% |

### Task × shape

| Task | Shape | Total | Severe | Rate |
| --- | --- | ---: | ---: | ---: |
| Drone | Irregular | 332 | 1 | 0.30% |
| Drone | Regular | 1,685 | 5 | 0.30% |
| Ground | Irregular | 174 | 5 | 2.87% |
| Ground | Regular | 2,006 | 185 | 9.22% |

## What the evidence supports

1. Under this exact split/prompt/criterion, Ground severe failures are much more frequent than Drone。
2. Severe-failure rate is monotonic across saved size categories：Large < Medium < Small。
3. Ground + Small is the strongest observed subgroup：114/727 = 15.68%。
4. The Ground/Drone gap remains within each size category，so the aggregate gap is not explained only by different size-category counts。
5. Shape and task are confounded；the lower Irregular rate cannot be interpreted as irregular geometry being easier。

## What the evidence does not support

- It does not prove viewpoint gap causes the Ground failures。
- It does not prove small pixel/patch size causes failure；`size_category` is a dataset label, while actual target area in 14×14 patch units is not stored。
- It does not locate failure at DINOv2、prompt encoding、π³ interaction or task heads。
- It does not establish the prevalence of qualitative categories from ten selected panels。
- `det_iou == 0` and `mask_iou == 0` do not distinguish a far-away prediction from an adjacent non-overlapping building。

## Provenance boundary

CSV contains：stable row index、task/size/shape、city、query/reference filenames、bbox IoU、mask IoU、Dice。It does not contain：

- input prompt coordinates/mask；
- GT/predicted bbox coordinates；
- predicted mask artifact path；
- camera position/rotation predictions；
- intermediate features/attention；
- exact command/config/checkpoint hash；
- the script that generated the CSV。

Therefore subgroup counts are independently auditable from the tracked artifact，but regenerating the CSV from the raw checkpoint/dataset is not yet repository-complete。

## Research-use decision

The Ground vs Drone severe-failure gap is strong enough to define a Phase 3 mechanism-analysis population。The first analysis must use matched Ground + Small successes as controls；otherwise any feature difference could simply reflect size、city、shape or annotation distribution rather than failure mechanism。
