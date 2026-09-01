# GAGeo Reproduction

## 1. Overview

This directory records a paper-level reproduction and analysis of:

**Beyond 2D Matching: A Unified Single-Stage Framework for Geometry-Aware Cross-View Object Geo-Localization**

Model: **GAGeo**

Main benchmark: **CMA-Loc**

Additional zero-shot / OOD benchmark: **CVOGL / CVOGL-Seg**

The goal of this reproduction is not only to verify the reported benchmark results, but also to investigate:

- prompt sensitivity,
- cross-view generalization,
- Ground-to-Satellite vs Drone-to-Satellite difficulty,
- out-of-distribution transfer,
- failure modes,
- reproducibility limitations of the public release,
- possible directions for model improvement.

---

## 2. Reproduction Status

| Component | Status |
|---|---|
| Environment setup | ✅ |
| CMA-Loc dataset setup | ✅ |
| Released checkpoint loading | ✅ |
| Seen + Point | ✅ |
| Seen + BBox | ✅ |
| Seen + Mask | ✅ |
| Unseen + Point | ✅ |
| Unseen + BBox | ✅ |
| Unseen + Mask | ✅ |
| Table 2 Detection | ✅ Reproduced |
| Table 3 Segmentation | ✅ Reproduced |
| Table 4 CVOGL Drone → Satellite | ✅ Reproduced |
| Table 4 CVOGL Ground → Satellite | ✅ Reproduced |
| CMA-Loc quantitative failure analysis | ✅ |
| CMA-Loc qualitative failure analysis | ✅ |
| Table 5 Ground → Drone | ⚠️ Public pairing unavailable |
| Table 6 loss ablation | ⏸ Not reproduced |
| Figure 4 structural/backbone ablation | ⏸ Not reproduced |

### Current conclusion

The released GAGeo checkpoint successfully reproduces the core CMA-Loc results reported in Tables 2 and 3.

Cross-dataset zero-shot evaluation on CVOGL/CVOGL-Seg in Table 4 was also reproduced with results close to the paper.

Failure analysis further shows that Ground → Satellite and small-target localization remain major weaknesses.

### Phase 2 evidence audit

The tracked JSON/CSV artifacts were re-audited without rerunning GPU inference. Tables 2–3 match the paper-displayed values except for the documented 0.1-pixel Unseen D→S Mask AAE rounding difference; Table 4 is approximately aligned. The 196/4,197 severe-failure count and all task/size/shape contingency counts are deterministically reproducible from the tracked CSV.

Run the lightweight audit with:

```bash
python reproductions/gageo/verify_gageo_artifacts.py
```

The saved result JSONs contain grouped aggregates rather than command/config/checkpoint metadata, and the severe-failure CSV generator is not tracked. Therefore numerical verification is stronger than execution-provenance completeness. Detailed boundaries and the research decision are recorded in [`notes/gageo_related_work/`](../../notes/gageo_related_work/).

---

## 3. Task and Model Summary

GAGeo studies **Cross-View Object Geo-Localization (CVOGL)**.

Given:

```text
Query Image
+
Spatial Prompt
+
Cross-View Reference Image
```

the model identifies the prompted target in the query image and localizes the corresponding object in the reference image.

The two main CMA-Loc view settings are:

```text
Ground → Satellite
Drone  → Satellite
```

The model supports three prompt types:

```text
Point
BBox
Mask
```

These are different ways to specify the target object in the query image.

They are **not different models**.

The same released GAGeo checkpoint supports all three prompt modalities.

### Outputs

GAGeo jointly predicts:

```text
Target Bounding Box
Target Segmentation Mask
Camera / Geometric Outputs
```

Therefore a single Point/BBox/Mask evaluation contributes simultaneously to:

```text
Detection metrics
Segmentation metrics
Geometric metrics
```

### Simplified architecture

```text
Query Image
    ↓
DINOv2
    ↓
Query Features
                       ┐
Point / BBox / Mask    │
    ↓                  │
SAM2 Prompt Encoder    │
    ↓                  │
Prompt Features        │
                       ├──→ π3 Geometry-Aware Backbone
Reference Image        │
    ↓                  │
DINOv2                 │
    ↓                  │
Reference Features     ┘
                            ↓
                 Cross-View Interaction
                            ↓
               Shared Geometric Representation
                            ↓
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
          BBox Head      Mask Head    Geometry Heads
```

The reproduction focuses on whether this shared representation generalizes across prompt types, view combinations, seen/unseen environments, and external datasets.

---

## 4. Experimental Environment

Experiments were performed on NSCC.

```text
Conda environment:
gageo

GPU:
NVIDIA A100-SXM4-40GB
```

Typical interactive GPU allocation:

```bash
qsub -I -l select=1:ngpus=1 -l walltime=03:00:00
```

Environment activation:

```bash
module load miniforge3
conda activate gageo
cd ~/CVPR2027/paper2_GAGeo
```

Released checkpoint:

```text
GAGeo_ckpt/gageo/mp_rank_00_model_states.pt
```

Checkpoint verification:

```text
Missing: 0
Unexpected: 0
```

The model contains approximately:

```text
937M parameters
```

Evaluation is inference-only and does not update model parameters.

---

## 5. Dataset Setup

### 5.1 CMA-Loc

Dataset location:

```text
/home/users/ntu/wenyu003/scratch/datasets/CMA-Loc/
```

Large datasets are stored under NSCC scratch rather than inside the Git repository.

Symbolic links used by GAGeo:

```text
paper2_GAGeo/data/urban
    ->
/home/users/ntu/wenyu003/scratch/datasets/CMA-Loc/urban
```

```text
paper2_GAGeo/data/json
    ->
/home/users/ntu/wenyu003/scratch/datasets/CMA-Loc/metadata
```

The metadata contains information including:

```text
query/reference pairing
city
task type
Point / BBox / Mask annotations
camera information
dataset split
```

### 5.2 Seen / Unseen mapping

An inconsistency was identified between the sample counts described in the paper and the released evaluation files.

Released evaluator:

```text
test        = 4220 samples
unseen_test = 4197 samples
```

Numerically:

```text
test        → matches the paper Seen results
unseen_test → matches the paper Unseen results
```

Therefore this reproduction uses:

```text
test        → Seen
unseen_test → Unseen
```

The current evidence suggests that the two sample counts described in the paper may have been swapped. This should not be described as a confirmed typo without author confirmation.

---

## 6. CMA-Loc Evaluation Protocol

The main CMA-Loc reproduction consists of six evaluation runs:

```text
Seen
├── Point
├── BBox
└── Mask

Unseen
├── Point
├── BBox
└── Mask
```

Each evaluation with the default full view subset automatically contains:

```text
Drone  → Satellite
Ground → Satellite
```

Therefore D→S and G→S do not require separate runs.

Example:

```bash
python evaluate_cmaloc.py \
  --config configs/default.yaml \
  --checkpoint GAGeo_ckpt/gageo/mp_rank_00_model_states.pt \
  --image_root data/urban \
  --splits test \
  --prompt_types point \
  --batch_size 4 \
  --num_workers 4 \
  --skip_sam \
  --save_json outputs/test_point.json
```

Main detection metrics:

```text
mAcc
Acc@0.50
Acc@0.75
```

Main segmentation metrics:

```text
mIoU
mDice
AAE
ME
```

Raw CMA-Loc reproduction results:

```text
results/
├── test_point.json
├── test_bbox.json
├── test_mask.json
├── unseen_test_point.json
├── unseen_test_bbox.json
└── unseen_test_mask.json
```

---

## 7. Table 2 — Detection Reproduction

### Seen

| Prompt | View | Paper mAcc | Ours mAcc | Paper Acc@75 | Ours Acc@75 | Paper Acc@50 | Ours Acc@50 |
|---|---|---:|---:|---:|---:|---:|---:|
| Point | D→S | 68.48 | 68.48 | 77.01 | 77.01 | 92.86 | 92.86 |
| BBox | D→S | 74.47 | 74.47 | 85.90 | 85.90 | 97.21 | 97.21 |
| Mask | D→S | 76.00 | 76.00 | 88.32 | 88.32 | 97.71 | 97.71 |
| Point | G→S | 71.50 | 71.50 | 80.70 | 80.70 | 89.69 | 89.69 |
| BBox | G→S | 71.50 | 71.50 | 80.94 | 80.94 | 89.78 | 89.78 |
| Mask | G→S | 71.41 | 71.41 | 81.04 | 81.04 | 89.39 | 89.39 |

### Unseen

| Prompt | View | Paper mAcc | Ours mAcc | Paper Acc@75 | Ours Acc@75 | Paper Acc@50 | Ours Acc@50 |
|---|---|---:|---:|---:|---:|---:|---:|
| Point | D→S | 71.74 | 71.74 | 82.80 | 82.80 | 93.95 | 93.95 |
| BBox | D→S | 77.03 | 77.03 | 89.19 | 89.19 | 97.62 | 97.62 |
| Mask | D→S | 79.16 | 79.16 | 91.77 | 91.77 | 98.26 | 98.26 |
| Point | G→S | 65.30 | 65.30 | 72.75 | 72.75 | 81.28 | 81.28 |
| BBox | G→S | 66.70 | 66.70 | 74.72 | 74.72 | 82.48 | 82.48 |
| Mask | G→S | 67.04 | 67.04 | 74.72 | 74.72 | 82.94 | 82.94 |

### Conclusion

Table 2 was reproduced exactly with the released checkpoint and evaluator.

---

## 8. Table 3 — Segmentation Reproduction

### Seen

| Prompt | View | Paper mIoU | Ours mIoU | Paper mDice | Ours mDice | Paper AAE | Ours AAE | Paper ME | Ours ME |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Point | D→S | 79.39 | 79.39 | 87.50 | 87.50 | 793.2 | 793.2 | 6.16 | 6.16 |
| BBox | D→S | 82.28 | 82.28 | 89.69 | 89.69 | 530.7 | 530.7 | 4.35 | 4.35 |
| Mask | D→S | 83.19 | 83.19 | 90.35 | 90.35 | 488.2 | 488.2 | 4.05 | 4.05 |
| Point | G→S | 77.37 | 77.37 | 84.01 | 84.01 | 1758.1 | 1758.1 | 19.18 | 19.18 |
| BBox | G→S | 77.36 | 77.36 | 83.99 | 83.99 | 1734.2 | 1734.2 | 19.57 | 19.57 |
| Mask | G→S | 77.21 | 77.21 | 83.82 | 83.82 | 1770.9 | 1770.9 | 19.74 | 19.74 |

### Unseen

| Prompt | View | Paper mIoU | Ours mIoU | Paper mDice | Ours mDice | Paper AAE | Ours AAE | Paper ME | Ours ME |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Point | D→S | 81.47 | 81.47 | 88.83 | 88.83 | 810.8 | 810.8 | 5.57 | 5.57 |
| BBox | D→S | 84.12 | 84.12 | 90.86 | 90.86 | 570.1 | 570.1 | 4.02 | 4.02 |
| Mask | D→S | 85.11 | 85.11 | 91.58 | 91.58 | 461.2 | 461.1 | 3.61 | 3.61 |
| Point | G→S | 72.68 | 72.68 | 78.63 | 78.63 | 2691.4 | 2691.4 | 31.04 | 31.04 |
| BBox | G→S | 73.82 | 73.82 | 79.76 | 79.76 | 2528.7 | 2528.7 | 29.40 | 29.40 |
| Mask | G→S | 74.07 | 74.07 | 80.03 | 80.03 | 2533.4 | 2533.4 | 28.85 | 28.85 |

The only visible discrepancy is a rounding-level difference for Unseen D→S Mask AAE:

```text
Paper ≈ 461.2
Released evaluator ≈ 461.1
```

### Conclusion

Table 3 was successfully reproduced.

---

## 9. Table 4 — Cross-Dataset Zero-Shot / OOD Evaluation

### 9.1 Setup

The released CMA-Loc-trained GAGeo checkpoint was directly evaluated on:

```text
CVOGL
+
CVOGL-Seg
```

No retraining or dataset-specific fine-tuning was used.

Two tasks were evaluated:

```text
CVOGL_DroneAerial
→ Drone → Satellite

CVOGL_SVI
→ Ground → Satellite
```

Each test set contains:

```text
973 samples
```

Point Prompt was used.

The original CVOGL images and CVOGL-Seg masks were stored separately. The segmentation mask directories were linked into the corresponding CVOGL task directories so that the evaluator could access query images, satellite images, pair annotations, and segmentation masks through a unified dataset interface.

A CVOGL evaluation adapter was implemented to reuse the released GAGeo checkpoint without modifying model parameters.

### 9.2 Paper vs Reproduction

| Task | Metric | Paper | Ours | Difference |
|---|---|---:|---:|---:|
| Drone → Satellite | mAcc / A@0.5:0.95 | 29.43 | 29.72 | +0.29 |
| Drone → Satellite | Acc@0.5 | 50.27 | 50.15 | -0.12 |
| Drone → Satellite | Acc@0.75 | 30.55 | 31.04 | +0.49 |
| Drone → Satellite | mIoU | 46.79 | 45.75 | -1.04 |
| Drone → Satellite | mDice | 53.38 | 52.22 | -1.16 |
| Ground → Satellite | mAcc / A@0.5:0.95 | 19.37 | 19.21 | -0.16 |
| Ground → Satellite | Acc@0.5 | 35.21 | 33.81 | -1.40 |
| Ground → Satellite | Acc@0.75 | 19.28 | 19.42 | +0.14 |
| Ground → Satellite | mIoU | 33.02 | 32.27 | -0.75 |
| Ground → Satellite | mDice | 38.36 | 37.48 | -0.88 |

### Conclusion

Table 4 was successfully reproduced at paper-level accuracy.

Detection metrics are very close to the reported values. Segmentation metrics differ by approximately one percentage point while preserving the same overall trend.

A strong view-dependent performance gap is observed:

```text
Drone → Satellite
>
Ground → Satellite
```

Saved results:

```text
results/table4_cvogl_droneaerial.json
results/table4_cvogl_svi.json
```

---

## 10. Main Experimental Findings

### 10.1 Richer prompts strongly improve Drone → Satellite

Seen D→S detection mAcc:

```text
Point = 68.48
BBox  = 74.47
Mask  = 76.00
```

Unseen D→S:

```text
Point = 71.74
BBox  = 77.03
Mask  = 79.16
```

Drone-to-Satellite localization benefits strongly from richer prompt geometry.

### 10.2 Rich prompts provide little benefit for Seen Ground → Satellite

Seen G→S detection mAcc:

```text
Point = 71.50
BBox  = 71.50
Mask  = 71.41
```

Increasing prompt precision produces almost no improvement.

This suggests that the main G→S bottleneck is not simply inaccurate target-region specification. The remaining difficulty is more likely related to cross-view representation and alignment.

### 10.3 Unseen Ground → Satellite generalization degrades

Point Prompt:

```text
Seen G→S mAcc   = 71.50
Unseen G→S mAcc = 65.30
```

Segmentation:

```text
Seen G→S mIoU   = 77.37
Unseen G→S mIoU = 72.68
```

Ground → Satellite therefore remains the more difficult generalization setting.

---

## 11. Failure Analysis — CMA-Loc Unseen + Point

A dedicated per-sample evaluator was implemented for:

```text
CMA-Loc unseen_test
+
Point Prompt
```

Instead of storing only average benchmark metrics, each sample records:

```text
task type
target size
target shape
detection IoU
segmentation IoU
segmentation Dice
query filename
satellite filename
```

For analysis purposes, a **severe failure** is defined as:

```text
Detection IoU = 0
AND
Segmentation IoU = 0
```

This is an analysis criterion introduced for this reproduction and is not an official paper metric.

Saved per-sample results:

```text
results/failure_cmaloc_unseen_point.csv
```

### 11.1 Overall Severe Failure Rate

| Metric | Value |
|---|---:|
| Total samples | 4197 |
| Severe failures | 196 |
| Severe failure rate | 4.67% |

### 11.2 Failure Rate by View

| Task | Total | Severe Failures | Failure Rate |
|---|---:|---:|---:|
| Drone → Satellite | 2017 | 6 | 0.30% |
| Ground → Satellite | 2180 | 190 | 8.72% |

The severe-failure rate for Ground → Satellite is dramatically higher than for Drone → Satellite.

### 11.3 Failure Rate by Target Size

| Size | Total | Severe Failures | Failure Rate |
|---|---:|---:|---:|
| Large | 1399 | 24 | 1.72% |
| Medium | 1399 | 54 | 3.86% |
| Small | 1399 | 118 | 8.43% |

The severe-failure rate increases clearly as target size decreases.

### 11.4 Task × Size

| Task | Size | Total | Severe Failures | Failure Rate |
|---|---|---:|---:|---:|
| Drone | Large | 672 | 1 | 0.15% |
| Drone | Medium | 673 | 1 | 0.15% |
| Drone | Small | 672 | 4 | 0.60% |
| Ground | Large | 727 | 23 | 3.16% |
| Ground | Medium | 726 | 53 | 7.30% |
| Ground | Small | 727 | 114 | 15.68% |

The most failure-prone subgroup is:

```text
Ground + Small
= 15.68% severe failure rate
```

### 11.5 Shape Analysis

| Shape | Total | Severe Failures | Failure Rate |
|---|---:|---:|---:|
| Regular | 3691 | 190 | 5.15% |
| Irregular | 506 | 6 | 1.19% |

Task × Shape:

| Task | Shape | Total | Severe Failures | Failure Rate |
|---|---|---:|---:|---:|
| Drone | Irregular | 332 | 1 | 0.30% |
| Drone | Regular | 1685 | 5 | 0.30% |
| Ground | Irregular | 174 | 5 | 2.87% |
| Ground | Regular | 2006 | 185 | 9.22% |

This result should be interpreted cautiously because task and shape distributions are not independent.

The apparent shape effect may partly reflect the much larger number of severe Ground failures.

---

## 12. Qualitative Failure Analysis

Representative severe-failure samples were visualized with:

```text
Query + Point Prompt
Satellite + GT / Pred BBox
GT Mask
Predicted Mask
```

Representative cases were selected from:

```text
Ground + Small
Ground + Medium
Ground + Large
Drone + Large
Drone + Small
```

The inspected examples reveal several recurring patterns.

### F1. Similar-Instance Confusion

The model frequently predicts a semantically similar neighboring building rather than the correct instance.

This is particularly visible in repetitive residential and industrial environments.

Interpretation:

```text
semantic-level recognition
        ↓
often approximately correct

exact instance correspondence
        ↓
still unstable
```

### F2. Large Ground-to-Satellite Viewpoint Gap

Ground images mainly expose:

```text
building facades
street-level appearance
vehicles
trees
occlusion
```

Satellite images mainly expose:

```text
rooftops
building footprints
top-down geometry
neighborhood structure
```

The shared visual evidence between the two views can therefore be weak.

This is consistent with the large severe-failure gap:

```text
Ground → Satellite = 8.72%
Drone  → Satellite = 0.30%
```

### F3. Small-Target Sensitivity

Small satellite targets contain fewer discriminative pixels and are more easily confused with neighboring structures.

Quantitatively:

```text
Large  = 1.72%
Medium = 3.86%
Small  = 8.43%
```

The combination:

```text
Ground + Small
```

is especially difficult:

```text
15.68%
```

### F4. Region-Level Mislocalization

Failure is not limited to small targets.

Several Ground + Medium and Ground + Large examples show predictions jumping to an entirely different building region.

Therefore small target size is an important factor, but not the only source of failure.

Cross-view semantic and geometric misalignment remains a major problem.

### F5. Drone Failures Are Usually More Localized

Drone failures are much rarer.

When they occur, predictions often remain close to the correct region but select a neighboring building or nearby instance.

This suggests:

```text
Drone → Satellite
coarse localization
is relatively strong

remaining difficulty
→ fine-grained instance discrimination
```

Representative visualizations are stored under:

```text
failure_cases/
```

---

## 13. Limitations Identified

Based on benchmark reproduction and failure analysis, the following limitations are supported by the current evidence.

### 13.1 Ground → Satellite alignment remains fragile

Extreme viewpoint and appearance differences remain difficult even when the target prompt becomes more informative.

### 13.2 Fine-grained instance discrimination is insufficient

The model can identify semantically relevant regions but may confuse neighboring objects with similar appearance.

### 13.3 Small targets remain highly vulnerable

Low target resolution significantly increases localization ambiguity.

### 13.4 Scale alone does not explain Ground failures

Medium and large Ground targets can still suffer region-level mislocalization.

### 13.5 Current single-stage prediction may benefit from explicit refinement

Drone failure cases suggest that coarse localization can already be close to correct while final instance selection remains inaccurate.

---

## 14. Potential Research Directions

The following ideas are motivated by the reproduced results and failure analysis. They are research hypotheses rather than validated contributions.

### 14.1 Coarse-to-Fine Cross-View Localization

```text
Query / Reference
      ↓
Coarse candidate localization
      ↓
Local crop / zoom-in
      ↓
Fine-grained cross-view matching
      ↓
Refined BBox / Mask
```

Potential motivation:

```text
reduce nearby-instance confusion
improve small-target localization
refine already-correct coarse predictions
```

### 14.2 Fine-Grained Instance-Level Alignment

Improve discrimination between visually similar neighboring buildings instead of relying primarily on semantic-level correspondence.

### 14.3 Context-Aware Cross-View Matching

Use contextual information including:

```text
road structure
neighboring buildings
local spatial layout
surrounding geometry
```

to distinguish ambiguous instances.

### 14.4 Geometry-Aware Refinement

Use cross-view geometric consistency or local structural constraints to reduce region-level mismatches.

### 14.5 Feature Reuse

Reuse extracted representations across:

```text
coarse localization
fine refinement
detection
segmentation
```

to reduce repeated computation and preserve useful cross-view correspondence information.

---

## 15. Table 5 — Ground → Drone Reproducibility Limitation

The paper reports a Ground → Drone zero-shot experiment using:

```text
1245 Ground–Drone–Satellite triplets
```

However, the current public release does not provide an explicit:

```text
CMA-Triplet annotation
Ground ↔ Drone pairing file
Table 5 evaluation script
```

The standard CMA-Loc metadata contains Ground and Drone samples, but the exact 1245 pair relationships used in the paper cannot be recovered from the released `sat_filename` values.

A direct shared-satellite matching attempt produced:

```text
Ground / Drone pairs sharing the same sat_filename = 0
```

Therefore Table 5 cannot currently be strictly reproduced under the paper protocol without the original triplet pairing.

This is recorded as a **public-release reproducibility limitation** rather than replaced with a self-defined evaluation protocol.

---

## 16. Table 6 and Structural Ablations

The paper also reports training-time ablations involving components such as:

```text
Base
+ Deep Supervision
+ Contrastive Learning
+ Camera Pose Loss
```

and structural/backbone experiments including different task-token settings and geometry backbones.

These experiments were not reproduced in the current stage because they may require:

```text
separately trained checkpoints
or
full retraining
```

Their computational cost is substantially higher than released-checkpoint evaluation.

They are therefore treated as optional extended reproduction rather than part of the completed core reproduction.

---

## 17. Saved Reproduction Artifacts

The research repository stores the important outputs required for later verification and reporting.

```text
reproductions/gageo/
├── README.md
│
├── results/
│   ├── test_point.json
│   ├── test_bbox.json
│   ├── test_mask.json
│   ├── unseen_test_point.json
│   ├── unseen_test_bbox.json
│   ├── unseen_test_mask.json
│   ├── table4_cvogl_droneaerial.json
│   ├── table4_cvogl_svi.json
│   └── failure_cmaloc_unseen_point.csv
│
└── failure_cases/
    ├── representative Ground + Small failures
    ├── representative Ground + Medium failures
    ├── representative Ground + Large failures
    └── representative Drone failures
```

Large datasets, checkpoints, and full experimental environments are intentionally not stored in Git.

---

## 18. Final Reproduction Summary

The current GAGeo reproduction achieved the following:

```text
CMA-Loc main benchmark
        ↓
Seen / Unseen
        ↓
Point / BBox / Mask
        ↓
Drone→Satellite / Ground→Satellite
        ↓
Detection + Segmentation
        ↓
Tables 2 and 3 reproduced
```

Cross-dataset evaluation was extended to:

```text
CMA-Loc-trained GAGeo
        ↓
CVOGL / CVOGL-Seg
        ↓
Drone→Satellite
Ground→Satellite
        ↓
Table 4 reproduced
```

Failure analysis further identified:

```text
Ground → Satellite
as the dominant severe-failure setting

Small targets
as substantially more vulnerable

Ground + Small
as the most difficult observed subgroup

Similar-instance confusion
and region-level mislocalization
as recurring qualitative failure modes
```

The current reproduction therefore moves beyond benchmark verification and provides evidence for model-level limitations that may motivate future cross-view localization research.

---

## 19. Current Research Checkpoint

```text
GAGeo Core Reproduction
=======================

Environment / Dataset
        ✅

Tables 2–3
        ✅

Table 4 OOD
        ✅

Table 5
        ⚠️ blocked by missing public pairing

Failure Analysis
        ✅

Initial Limitations
        ✅

Initial Research Directions
        ✅
```

At this stage, the core GAGeo reproduction is considered complete.

The next research step is to compare these findings with other reproduced cross-view localization systems and identify a focused, experimentally testable improvement direction.
