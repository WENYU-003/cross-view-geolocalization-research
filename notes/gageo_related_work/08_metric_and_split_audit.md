# 08 — Metric and Split Audit

## Seen / Unseen and sample counts

| Released evaluator name | JSON annotation | Saved count | Metric identity | Operational semantic |
| --- | --- | ---: | --- | --- |
| `test` | `test_all.json` | 4,220 | matches paper Seen rows | **Seen** |
| `unseen_test` | `unseen_test.json` | 4,197 | matches paper Unseen rows | **Unseen** |

The paper text states 4,197 Seen and 4,220 Unseen, while released files/results show the reverse counts. The metric rows provide stronger operational identification than the prose count sentence. Without author confirmation, record this as a paper/release count-order inconsistency, not a confirmed typo.

Task composition：

```text
test:        Drone 2184 + Ground 2036 = 4220
unseen_test: Drone 2017 + Ground 2180 = 4197
```

The evaluator default `--view_subset all` keeps both. D→S and G→S table rows are grouped summaries from the same prompt/split run, not necessarily separate runs.

## Prompt vs task

- `--prompt_types point` supplies query point coordinates/positive label。
- `bbox` supplies query bbox in pixel-space `(x,y,w,h)`。
- `mask` supplies query binary mask。
- Every prompt path calls the same model and produces `pred_boxes`, `mask_pred`, `position`, and `rotation_matrix`。

Therefore point/bbox do not “belong to detection”，and mask does not “belong to segmentation”。All three are input prompts; detection and segmentation are simultaneous output tasks。

## `--skip_sam`

Actual behavior in `evaluate_cmaloc.py`：

```text
--skip_sam
→ do not load external segment_anything SamPredictor
→ do not generate the optional bbox+center-point post-processed SAM mask
→ still run GAGeo's internal SAM2-derived GeometryPromptEncoder
→ still run GAGeo's native SAM-style MaskHead
→ still report model_miou/model_mdice/model_aae/model_me
```

Thus `skip_sam` does not make the run detection-only and does not remove mask-prompt support。

## Detection metrics

For each sample the evaluator converts predicted normalized `cxcywh` to absolute reference-image `xyxy`，then computes bbox IoU (u_i)。

| JSON field | Exact code definition | Paper relation |
| --- | --- | --- |
| `det_miou` | mean of (u_i) | diagnostic mean bbox IoU；not Table 2 mAcc |
| `det_avg_acc` | mean over samples and thresholds (t=0.50,0.55,...,0.95) of `1[u_i ≥ t]` | paper mAcc / A@0.5:0.95 |
| `det_acc50` | fraction with bbox IoU ≥ 0.50 | paper Acc@50 |
| `det_acc75` | fraction with bbox IoU ≥ 0.75 | paper Acc@75 |

Because every sample has one target and one selected prediction，`det_avg_acc` is thresholded localization accuracy, not COCO precision–recall AP。

## Native model-mask metrics

The evaluator thresholds `mask_pred > 0.5` and computes each sample metric before averaging：

| JSON field | Exact definition |
| --- | --- |
| `model_miou` | mean binary mask intersection / union |
| `model_mdice` | mean (2|P∩G|/(|P|+|G|)) |
| `model_aae` | mean absolute area error `abs(predicted foreground pixels - GT foreground pixels)`，unit = resized pixels |
| `model_me` | Euclidean distance between predicted and GT foreground centroids，unit = pixels；if either mask is empty, uses image diagonal |

These are native GAGeo mask metrics。Optional external-SAM equivalents use the `sam_` prefix and are absent when `--skip_sam` is used。

## Pose and runtime metrics

| JSON field | Exact definition | Caveat |
| --- | --- | --- |
| `rotation_error_deg` | mean SO(3) geodesic angle from `pred_R.T @ gt_R` over valid-pose samples | evaluator reconstructs GT from relative yaw/pitch/roll or legacy fallback |
| `pos_err_px` | mean L2 distance between normalized predicted/GT camera positions × `img_size` | resized 518×518 reference pixels, not meters |
| `latency_ms` | synchronized model forward wall time divided by batch size | excludes dataloading, metric calculation and external SAM；hardware/batch dependent |

## Output JSON limitation

`save_results_json` saves only grouped aggregate dictionaries。It does not save command、config、checkpoint hash、per-sample predictions or exclusions。Therefore the six JSONs are strong numerical result artifacts but not self-contained reproducibility bundles。
