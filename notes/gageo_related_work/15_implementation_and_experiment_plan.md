# 15 — Implementation and Experiment Plan

> **Status：FROZEN MVP BLUEPRINT。** Phase 3B is complete。This document fixes tomorrow's implementation entry points；it does not authorize a large training run。

## Research purpose

Test one falsifiable intervention：explicitly preserve and verify stage-11 spatial alternatives before the diagnosed late-refinement degradation，then determine whether this improves both representation retention and the Ground catastrophic tail。

## MVP code modification points in official GAGeo

| File | Exact MVP change | Insertion point |
| --- | --- | --- |
| **new** `models/heads/late_spatial_pr_mha.py` | prompt-map builder；stage-11 anchor scorer；NMS/top-K；candidate initializer；return verifier；confidence gate；final residual builder | self-contained new method |
| `models/heads/__init__.py` | export `LateSpatialPRMHA` | import surface only |
| `models/backbone/pi3_backbone.py` | accept optional module/prompt map；after pair-stage 11 global block append K candidates and coordinates；rebuild masks；collect candidate states from final two blocks；slice original task queries separately | `decode_with_extra_tokens`，immediately after decoder block `2*11+1 = 23` |
| `models/cross_view_localizer.py` | parse config args；build prompt map from the actual point/bbox/mask；call backbone branch；fuse corrected bbox query/reference features only for bbox/mask heads；return `pr_mha_aux` | before backbone call and immediately before `BBoxHead`/`SAMMaskHead` |
| `utils/losses.py` | add weighted `L_anchor/L_preserve/L_rank/L_return/L_gate` when `pr_mha_aux` exists | `DETRCriterion.forward` before final weighted sum |
| `utils/misc.py` | recognize `late_spatial_pr_mha.*` as its own/new-module optimizer group | `get_param_groups` |
| `configs/default.yaml` | add disabled model defaults and zero loss weights；baseline stays unchanged | `model.pr_mha` and `training` sections |
| `train.py` | pass config/criterion weights；apply module-only freeze policy；log PR-MHA metrics；whitelist only new-module missing keys when initializing from released checkpoint | model/criterion/optimizer construction and `train_one_epoch` logging |
| `train_ddp.py` | mirror `train.py` construction、freeze、checkpoint and logging behavior | DDP equivalents |
| `evaluate_cmaloc.py` | pass config；checkpoint whitelist；optional per-sample candidate/gate diagnostics，without metric changes | model construction/loading and per-sample export |
| **new** `tests/test_late_spatial_pr_mha.py` | shape、top-K uniqueness、finite gradients、zero-gate identity、disabled-path identity and checkpoint-key whitelist tests | CPU synthetic tests |

Do not modify `BBoxHead`、`SAMMaskHead`、dataset preprocessing or metric definitions。

## Tensor flow and expected shapes（Large，518×518）

```text
front/satellite RGB                         [B,3,518,518]
stage-11 front/reference patches           [B,1369,1024]
prompt weight / optional context ring       [B,1369]
prompt-pooled query descriptor              [B,1024]
projected query/reference                   [B,256], [B,1369,256]
anchor logits                               [B,1369]
top-K indices / xy                          [B,8], [B,8,2]
candidate tokens appended after stage 11    [B,8,1024]
candidate final-two-block concat            [B,8,2048]
candidate→query return attention            [B,8,1369]
verification logits / weights / gate        [B,8], [B,8], [B,1]
verified context / sparse spatial residual  [B,2048], [B,1369,2048]
corrected bbox query                        [B,Q_bbox,2048]
corrected bbox/mask reference features      [B,1369,2048]
```

The original heatmap、camera and contrastive branches receive unmodified final features in MVP。

## Config contract

```yaml
model:
  use_late_spatial_pr_mha: false   # default: exact released path
  pr_mha:
    insertion_stage: 11
    top_k: 8
    proj_dim: 256
    nms_radius: 1
    point_sigma_patches: 1.5
    anchor_temperature: 0.07
    return_temperature: 0.07
    use_context_ring: true
    gate_init: 0.0

training:
  pr_mha_module_only: true
  lr_pr_mha: 1.0e-4
  weight_pr_anchor: 1.0
  weight_pr_preserve: 1.0
  weight_pr_rank: 0.5
  weight_pr_return: 0.5
  weight_pr_gate: 0.01
```

`use_late_spatial_pr_mha=false` must not instantiate/call the new path or alter output tensors。With it enabled，released checkpoint loading may miss only `late_spatial_pr_mha.*` keys；any other missing/unexpected key remains fatal。New checkpoints save the switch and all new keys normally。

## Training strategy

1. Initialize from the released checkpoint and assert that only new PR-MHA keys are missing。
2. Freeze DINOv2、SAM2 prompt encoder/projections、all π³ blocks、existing task queries、all existing heads and contrastive queue。
3. Train only `late_spatial_pr_mha.*`。Gradients may pass through frozen late π³ blocks into candidate inputs，but their weights do not update。
4. Use official train data with all prompt types；do not train on the 570 diagnosis samples。
5. Mine top-scoring non-GT reference peaks as hard negatives；retain every original GAGeo loss and add the five weighted PR-MHA terms。
6. First run CPU/unit tests，then 2-sample forward/backward，then a 32-sample overfit/smoke test。Do not start a full run until all three pass。

## Minimum viable evaluation

Primary：Unseen Point Ground severe rate and stage11→final spatial H@8/GT-rank retention。

Secondary：all Unseen Ground，Ground Medium/Large。

Guardrails：Unseen Drone by size and full Seen split。

First controlled comparison：

```text
released baseline
vs Late-Spatial PR-MHA K=8
vs K=8 without return verification
```

## MVP success / stop criteria

Continue only if：

1. disabled path matches the released baseline within numerical tolerance；
2. enabled zero-gate initialization also matches baseline before training；
3. Ground severe rate decreases by at least `20%` relative（from `8.72%` to `≤6.98%`）on the full official Point unseen evaluation；
4. Ground-severe stage11→final H@8 gain improves by at least `+0.10` absolute from the diagnosed `-0.1842`；
5. Ground-success and Drone-success mean det/mask IoU each regress by no more than `1.0` percentage point，and overall Ground mAcc/mIoU do not regress materially；
6. removing return verification weakens either retention or severe-tail improvement，supporting the claimed mechanism。

Stop/revise if the method only improves mean IoU，cannot move late-stage retention，or violates guardrails。The exact best insertion block within stages 12–17 is deferred to later ablation and does not block this MVP。

## Logging additions

Log `pr_mha/anchor_recall@1,@4,@8`、GT candidate survival after late refinement、top1-top2 margin、return consistency for GT/wrong candidates、candidate entropy、gate mean/p05/p95、each new loss、and per-cohort severe rate。Evaluation export must include sample index、top-K coordinates/scores、selected candidate、gate and baseline-vs-enabled prediction，without storing feature tensors by default。
