# 05 — Paper ↔ Code Mapping

## Version boundary

- Paper source used for alignment: local paper extraction and [`papers/gageo.md`](../../papers/gageo.md).
- Official implementation inspected: `/Users/oscarsmac/Documents/Research/CVPR/code/GAGeo`, Git revision `f6585cb`.
- Research-result repository: current repository, results introduced by commits `1fa99e9`, `471a7dc`, `3117fda`, and `c5ada95`.

Official-code working tree currently contains unrelated local NSCC setup changes; this audit only read it and did not modify it.

## Model mapping

| Paper component | Code file | Class / function | Confirmed data flow |
| --- | --- | --- | --- |
| Unified GAGeo model | `models/cross_view_localizer.py` | `CrossViewLocalizer.forward` | encodes prompt → calls backbone → splits task tokens → invokes four heads |
| DINOv2 image encoder | `models/backbone/pi3_backbone.py` | `Pi3Backbone.encoder`, `Pi3Backbone.forward` | stacks Satellite and front/query, extracts normalized patch tokens |
| SAM2 prompt encoder | `models/encoder/prompt_encoder.py` | `GeometryPromptEncoder.forward` | point/bbox → sparse; mask → dense; optional 256→decoder projection |
| π³ local/global backbone | `models/backbone/pi3_backbone.py` | `decode_with_extra_tokens` | even blocks local per-stream; odd blocks global concatenated interaction |
| Sparse-prompt isolation | same | `_build_global_attn_mask` | blocks prompt↔Satellite, prompt↔task, prompt↔prompt except self |
| Dense mask injection | same | `decode_with_extra_tokens` | default `global_kv`: add dense embedding only to query-patch keys |
| Object / position task tokens | same | `learnable_queries`; split in `CrossViewLocalizer.forward` | object queries feed bbox/mask; heatmap queries feed position |
| Detection head | `models/heads/bbox_head.py` | `BBoxHead.forward` | task token → normalized `cxcywh`, confidence/logit |
| Segmentation head | `models/heads/mask_head.py` | `SAMMaskHead.forward` | task token → dynamic kernel; reference features → upsampled model mask |
| Camera position | `models/heads/heatmap_head.py` | `HeatmapHead.forward` | position query dot reference grid → heatmap → soft-argmax `(x,y)` |
| Camera rotation | `models/heads/pi3_camera_head.py` | `Pi3CameraHead.forward` | query + reference patch features → relative rotation matrix |
| Contrastive learning | `models/heads/contrastive_head.py` | `CrossViewContrastiveHead.forward` | mask-pooled paired features → MoCo/InfoNCE objective |
| Joint losses | `utils/losses.py` | `DETRCriterion.forward` | bbox L1/GIoU, focal class, mask BCE/Dice, heatmap, rotation, contrastive, deep supervision |

## Dataset and evaluation mapping

| Paper/evaluation concept | Code location | Confirmed behavior |
| --- | --- | --- |
| Train dataset | `datasets/cmaloc.py::CrossViewDataset` | loads query/Satellite pair, transforms prompts/masks/bbox/pose, optionally crops training Satellite image |
| Released evaluator dataset | `evaluate_cmaloc.py::EvalDataset` | loads pre-cropped `crop_sate`, resizes both views and all annotations to configured size |
| Split files | `evaluate_cmaloc.py::main` | `test → test_all.json`; `unseen_test → unseen_test.json` |
| Ground/Drone grouping | `_is_drone_item`, `filter_eval_subset`, `GroupedEvaluator.summarize` | prefers annotation `task_type`; evaluator default `view_subset=all` keeps both |
| Prompt switch | `evaluate_split` | point sets `points`; bbox sets pixel-space xywh `boxes`; mask sets query `masks` |
| Detection metrics | `GroupedEvaluator._agg` | bbox IoU per sample; threshold accuracy at 0.50:0.05:0.95, 0.50, 0.75 |
| Model segmentation | `SegMetrics`, `evaluate_split` | threshold native `mask_pred > 0.5`; compute IoU, Dice, area error, centroid error |
| Optional external SAM | `evaluate_split`, `--skip_sam` | predicted bbox + center point prompt an external SAM on reference; independent of native GAGeo mask |
| Pose metrics | `geodesic_rotation_error_deg_np`, `evaluate_split` | valid-sample mean SO(3) angle and normalized-position L2×image size |
| Saved grouped JSON | `save_results_json` | aggregate/group summaries only; no per-sample records or config metadata |

## Paper experiment → existing artifact

| Paper experiment | Code/protocol record | Tracked artifact | Evidence status |
| --- | --- | --- | --- |
| Tables 2–3 CMA-Loc | `evaluate_cmaloc.py`; command in reproduction README | six `test/unseen_test × point/bbox/mask` JSON files | **VERIFIED MATCH** at reported precision; execution provenance partial |
| Table 4 CVOGL-Seg OOD | historical official-code adapter existed at commit `28c58f5`; README records setup | two 973-sample JSON files | **APPROXIMATELY ALIGNED**; adapter/config/log not tracked here |
| Table 5 Ground→Drone | historical official code has an evaluator, but public 1,245-pair annotation is unavailable in current release | none | **UNRESOLVED / BLOCKED** |
| Table 6 loss ablation | requires separately trained variants | none | **NOT DIRECTLY COMPARABLE / LOW PRIORITY** |
| Figure 4 token/backbone ablation | requires alternative trained models | none | **NOT DIRECTLY COMPARABLE / LOW PRIORITY** |
| Severe-failure analysis | generation script not tracked; deterministic CSV audit available | `failure_cmaloc_unseen_point.csv` | counts **RESULT_VERIFIED**; generation provenance partial |

## Code-reading cautions

1. `front_view` means query/mono view, not always Ground；it may be Drone。
2. `sate_features` is reference/Satellite feature；spelling is historical。
3. 注释中曾出现 token-side wording drift；以 `decode_with_extra_tokens` 的实际 concatenation/splitting 为准。
4. `model_miou` 是 native GAGeo mask；`sam_miou` 才是外部 SAM post-processing。
5. `det_miou` 不是论文 Table 2 的 mAcc；Table 2 对应 `det_avg_acc`。
