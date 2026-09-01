# 15 — Implementation and Experiment Plan

## Research purpose before code changes

Test whether GAGeo catastrophic Ground failures retain the correct reference location among several latent feature hypotheses but lose it when collapsing to one object token。No architecture implementation starts until the frozen-feature diagnostic answers this。

## Required diagnostic bundle

The local machine currently lacks CMA-Loc images/metadata and the released GAGeo checkpoint。The smallest useful upload is：

1. `unseen_test.json`；
2. the released GAGeo checkpoint and exact evaluation config；
3. query、`crop_sate`、query/satellite masks for：
   - all 114 Ground + Small severe failures；
   - 114 shape/actual-area-matched Ground + Small successes；
   - 114 matched Drone + Small successes as a view control；
4. if possible，raw GT/pred bbox and camera pose fields for these samples。

An NSCC-accessible manifest is also sufficient；large datasets/checkpoints should not be committed to the research repository。

## First experiment: frozen top-K recoverability probe

No training，one released checkpoint：

1. export DINOv2 output and π³ stages 4、11、17 for the diagnostic bundle；
2. build query prompt-weighted target/context descriptors；
3. compute reference anchor maps and GT-mask Hit@1/Hit@4/Hit@8；
4. compare severe Ground + Small vs matched successful Ground + Small and Drone controls；
5. for top-K candidates，compute prompt-return score and AUROC/margin for GT vs wrong candidates；
6. manually audit annotation validity for all 114 severe cases before treating model-vs-GT disagreement as model failure。

### GO criterion

- failures have materially higher GT Hit@4/8 than Hit@1，showing recoverable alternatives；and
- prompt-return/context score separates GT from wrong candidates（initial target AUROC ≥0.65 or a clear paired margin）；and
- effect is not driven only by invalid annotations。

### NO-GO / revise criterion

- GT is absent from top-K at every layer；or
- correct/wrong candidates are indistinguishable；or
- a large fraction of severe Ground labels are invalid/ambiguous。

If GT is absent early，prioritize multi-scale/cross-view representation learning。If GT exists but return verification fails，investigate context/geometry descriptors。If labels are invalid，repair/evaluate the dataset before method design。

## MVP code modification points

Only after GO：

| File | Change | Why |
| --- | --- | --- |
| `models/heads/prompt_return_anchor_head.py` | new PR-MHA scorer、top-K candidate builder、return verifier、gate | isolate new method from baseline |
| `models/cross_view_localizer.py` | construct prompt weight map；call PR-MHA after backbone；fuse residual before bbox/mask heads；export diagnostics | smallest reversible insertion point |
| `utils/losses.py` | add anchor/rank/return losses behind config flags | controlled training and clean ablation |
| `configs/default.yaml` or new method config | `use_pr_mha`、K、loss weights、freeze policy | preserve baseline compatibility |
| `evaluate_cmaloc.py` | optional per-sample anchor Hit@K、selected candidate、confidence export | test mechanism，not only headline metrics |
| `reproductions/gageo/` | command/config snapshot、per-sample manifest and result summary | scientific provenance |

MVP operates on final π³ features。Only if successful should a second version insert candidate tokens after π³ stage 4 inside `Pi3Backbone.decode_with_extra_tokens`，allowing later global blocks to refine verified hypotheses。

## Training strategy

1. Initialize from released checkpoint。
2. Freeze DINOv2、SAM2 prompt encoder and π³；train only PR-MHA projections/gate and，if necessary，the existing object heads。
3. Use both Ground and Drone training samples with Ground/Small-aware balanced sampling；retain Drone as a guardrail。
4. Mine top-scoring non-GT reference peaks as hard negatives；do not change original bbox/mask/pose losses。
5. Run a smoke subset first，then one controlled training run。Unfreeze only the last π³ global stages if the frozen adapter has anchor recall but insufficient final localization gain。

## Minimum viable evaluation

Primary：Unseen Point Ground + Small，severe rate、bbox/mask q05/q10、mAcc、mIoU。

Secondary：all Unseen Ground，Ground Medium/Large。

Guardrails：Unseen Drone by size and full Seen split。

Compare：

```text
released baseline
vs PR-MHA K=4
vs forward-anchor only (no return verification)
```

The single essential ablation is “no return verification”；it tests the claimed mechanism against a generic anchor-map improvement。Stop if severe Ground + Small does not improve or if Drone/overall median materially regresses。
