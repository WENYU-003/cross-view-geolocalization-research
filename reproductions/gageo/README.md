# GAGeo Reproduction

## 1. Paper

**Beyond 2D Matching: A Unified Single-Stage Framework for Geometry-Aware Cross-View Object Geo-Localization**

This directory records my reproduction of **GAGeo** on the **CMA-Loc** benchmark.

### Current Status

- ✅ Environment setup
- ✅ CMA-Loc dataset setup
- ✅ Released checkpoint successfully loaded
- ✅ Seen + Point
- ✅ Seen + BBox
- ✅ Seen + Mask
- ✅ Unseen + Point
- ✅ Unseen + BBox
- ✅ Unseen + Mask
- ✅ Drone-to-Satellite evaluation
- ✅ Ground-to-Satellite evaluation
- ✅ Table 2 main detection results reproduced
- ✅ Table 3 main segmentation results reproduced

> Current milestone: the core CMA-Loc benchmark results in Tables 2 and 3 have been successfully reproduced using the officially released GAGeo checkpoint.

The complete paper reproduction is still in progress.

---

## 2. Task Understanding

GAGeo studies **Cross-View Object Geo-Localization (CVOGL)**.

Given:

```text
Query Image
+
Reference Image
+
Spatial Prompt
```

the goal is to identify the target object specified in the query image and locate the corresponding object in the cross-view reference image.

In the CMA-Loc main benchmark, the query view can be:

```text
Ground
or
Drone
```

while the reference view is:

```text
Satellite
```

Therefore the two main cross-view settings are:

```text
Ground → Satellite (G→S)

Drone → Satellite (D→S)
```

---

## 3. Prompt Types

GAGeo supports three prompt modalities:

```text
Point
BBox
Mask
```

These are three different ways to tell the model:

> Which object in the query image should be localized?

### Point Prompt

Provides a point located inside the target object.

```text
Query Image
      ●
   target
```

It contains relatively sparse spatial information.

### BBox Prompt

Provides the rectangular region of the target.

```text
┌───────────┐
│  target   │
└───────────┘
```

It contains richer spatial information than a point.

### Mask Prompt

Provides the pixel-level region belonging to the target object.

```text
000000000
001111000
001111100
000111000
000000000
```

It contains the most detailed target-region information.

### Important

Point, BBox, and Mask are:

```text
INPUT PROMPT TYPES
```

They are NOT three different GAGeo models.

The same released GAGeo checkpoint supports all three prompt modalities.

---

## 4. Output Tasks

The input prompt type should not be confused with the model output task.

Regardless of whether the input is:

```text
Point
BBox
Mask
```

GAGeo jointly predicts:

```text
Reference-object Bounding Box
Reference-object Segmentation Mask
Camera Position
Camera Rotation
```

The relationship is:

```text
Point ─┐
BBox  ─┼────→ GAGeo ─────┬→ BBox Prediction
Mask  ─┘                  ├→ Mask Prediction
                          ├→ Camera Position
                          └→ Camera Rotation
```

Therefore:

```text
Prompt
= input information

Detection
= bbox output task

Segmentation
= mask output task

Camera Pose
= geometric output task
```

This explains why a Point-prompt experiment can simultaneously generate both detection and segmentation results.

---

## 5. Simplified GAGeo Pipeline

The overall model can be understood as:

```text
Query Image
    ↓
DINOv2
    ↓
Query Visual Tokens
                         ┐
Point / BBox / Mask      │
    ↓                    │
SAM2 Prompt Encoder      │
    ↓                    │
Prompt Representation    │
                         ├────→ π3 Backbone
Reference Image          │
    ↓                    │
DINOv2                   │
    ↓                    │
Reference Visual Tokens  ┘
                              ↓
                   Local Attention
                              ↓
                   Global Attention
                              ↓
                  Cross-view Interaction
                              ↓
                Geometry-aware Representation
                              ↓
             ┌────────────────┼────────────────┐
             ↓                ↓                ↓
         BBox Head        Mask Head       Camera Head
             ↓                ↓                ↓
            Box              Mask        Position/Rotation
```

GAGeo therefore uses a:

```text
single-stage
+
multi-task
+
geometry-aware
```

architecture.

---

## 6. Main Model Components

### DINOv2

DINOv2 extracts visual patch-level representations from both:

```text
Query Image
Reference Image
```

The output is no longer raw RGB pixels, but visual tokens/features that can be processed by the Transformer.

---

### SAM2 Prompt Encoder

The prompt encoder converts:

```text
Point
BBox
Mask
```

into representations that can be used by the network.

Sparse prompts such as Point and BBox generate sparse prompt tokens.

Mask prompts produce dense representations.

The prompt therefore tells the model:

> Which part of the query image corresponds to the target object?

---

### π3 Backbone

π3 is the main geometry-aware 3D foundation model backbone.

It alternates:

```text
Local Attention
and
Global Attention
```

Local attention processes information within individual views.

Global attention enables interaction between:

```text
Query
and
Reference
```

This is where cross-view geometric reasoning occurs.

---

### Task Heads

After cross-view interaction, the shared representation is used by several task-specific heads.

```text
BBox Head
→ predicts target bounding box

Mask Head
→ predicts target segmentation mask

Camera Head
→ predicts camera pose

Position Head
→ predicts observer/camera position
```

These heads operate in parallel rather than sequentially.

---

## 7. Why Segmentation Exists in a Geo-Localization Model

GAGeo does not only want to know:

```text
Where is the target approximately?
```

It also wants to understand:

```text
What exact pixels belong to the target?
```

BBox prediction provides coarse spatial localization.

Segmentation provides pixel-level object geometry.

Therefore:

```text
BBox
= coarse object localization

Mask
= fine-grained object geometry
```

Segmentation acts as an additional spatial/geometric learning objective rather than an unrelated classification task.

---

## 8. Experimental Environment

Experiments were performed on NSCC.

```text
Conda environment:
gageo

GPU:
NVIDIA A100-SXM4-40GB
```

Interactive GPU allocation:

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

Checkpoint loading output:

```text
Loaded state_dict keys: 2164
Missing: 0
Unexpected: 0
```

This confirms that the released checkpoint matches the current model architecture.

The model contains approximately:

```text
937M parameters
```

During evaluation:

```text
trainable = 0
```

because inference does not update model parameters.

---

## 9. CMA-Loc Dataset Setup

The CMA-Loc dataset is stored separately under NSCC scratch storage:

```text
/home/users/ntu/wenyu003/scratch/datasets/CMA-Loc/
```

Large datasets and checkpoints are not stored inside the Git repository.

Two symbolic links are used.

### Image Link

```text
paper2_GAGeo/data/urban
    ->
/home/users/ntu/wenyu003/scratch/datasets/CMA-Loc/urban
```

This contains the actual query/reference images.

### Metadata Link

```text
paper2_GAGeo/data/json
    ->
/home/users/ntu/wenyu003/scratch/datasets/CMA-Loc/metadata
```

This contains information such as:

```text
query/reference pairing
city
task type
Point annotation
BBox annotation
Mask annotation
camera pose
dataset split
```

Therefore:

```text
data/urban
= image data

data/json
= annotation and pairing information
```

---

## 10. CMA-Loc Cities

The dataset contains eight cities:

```text
Berlin
Chicago
London
Los Angeles
Moscow
New York
Paris
Tokyo
```

The main CMA-Loc benchmark contains both:

```text
Ground → Satellite
Drone → Satellite
```

samples.

---

## 11. Evaluation Command

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

### Important Arguments

```text
--config
    model/evaluation configuration

--checkpoint
    released trained GAGeo weights

--image_root
    CMA-Loc image root

--splits
    test or unseen_test

--prompt_types
    point / bbox / mask

--batch_size
    number of samples processed in one GPU batch

--num_workers
    CPU workers used for loading data

--skip_sam
    skip additional SAM post-processing

--save_json
    save the final evaluation metrics into a JSON file
```

---

## 12. Meaning of Batch Size

For example:

```text
batch_size = 4
```

does NOT mean that only four samples are evaluated.

It means:

```text
Batch 1:
samples 1–4

Batch 2:
samples 5–8

Batch 3:
samples 9–12

...
```

until the entire split has been evaluated.

For the 4220-sample split:

```text
4220 / 4
=
1055 batches
```

which matches the evaluation progress output.

---

## 13. One Evaluation Automatically Contains D→S and G→S

With the default:

```text
view_subset = all
```

one evaluation run automatically evaluates both cross-view setups.

The terminal reports:

```text
task/drone
```

which means:

```text
Drone → Satellite
```

and:

```text
task/ground
```

which means:

```text
Ground → Satellite
```

Therefore we do NOT need to separately execute:

```text
Point + D→S
Point + G→S
```

One Point evaluation already contains both.

---

## 14. Six Main Benchmark Evaluations

The main CMA-Loc reproduction consists of six runs:

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

Each run automatically contains:

```text
D→S
+
G→S
```

and simultaneously outputs:

```text
Detection
+
Segmentation
+
Camera Pose
```

Raw results:

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

## 15. Detection Metrics

Paper Table 2 uses:

```text
mAcc ↑
Acc@75 ↑
Acc@50 ↑
```

### Acc@50

A prediction is considered successful when:

```text
BBox IoU >= 0.50
```

Acc@50 is the percentage of samples satisfying this condition.

Higher is better.

### Acc@75

A stricter criterion:

```text
BBox IoU >= 0.75
```

Higher is better.

### mAcc

Detection accuracy is calculated at:

```text
IoU = 0.50
0.55
0.60
0.65
0.70
0.75
0.80
0.85
0.90
0.95
```

and then averaged.

Therefore:

```text
Acc@50
= relatively loose detection criterion

Acc@75
= stricter criterion

mAcc
= comprehensive multi-threshold detection quality
```

---

## 16. Segmentation Metrics

Paper Table 3 uses:

```text
mIoU ↑
mDice ↑
AAE ↓
ME ↓
```

Higher is better:

```text
mIoU
mDice
```

Lower is better:

```text
AAE
ME
```

The evaluator additionally reports:

```text
rotation_error_deg
pos_err_px
latency_ms
```

These will be useful for later geometric and efficiency analysis.

---

# 17. Table 2 — Detection Reproduction

## Seen

| Prompt | View | Paper mAcc | Ours mAcc | Paper Acc@75 | Ours Acc@75 | Paper Acc@50 | Ours Acc@50 |
|---|---|---:|---:|---:|---:|---:|---:|
| Point | D→S | 68.48 | 68.48 | 77.01 | 77.01 | 92.86 | 92.86 |
| BBox | D→S | 74.47 | 74.47 | 85.90 | 85.90 | 97.21 | 97.21 |
| Mask | D→S | 76.00 | 76.00 | 88.32 | 88.32 | 97.71 | 97.71 |
| Point | G→S | 71.50 | 71.50 | 80.70 | 80.70 | 89.69 | 89.69 |
| BBox | G→S | 71.50 | 71.50 | 80.94 | 80.94 | 89.78 | 89.78 |
| Mask | G→S | 71.41 | 71.41 | 81.04 | 81.04 | 89.39 | 89.39 |

## Unseen

| Prompt | View | Paper mAcc | Ours mAcc | Paper Acc@75 | Ours Acc@75 | Paper Acc@50 | Ours Acc@50 |
|---|---|---:|---:|---:|---:|---:|---:|
| Point | D→S | 71.74 | 71.74 | 82.80 | 82.80 | 93.95 | 93.95 |
| BBox | D→S | 77.03 | 77.03 | 89.19 | 89.19 | 97.62 | 97.62 |
| Mask | D→S | 79.16 | 79.16 | 91.77 | 91.77 | 98.26 | 98.26 |
| Point | G→S | 65.30 | 65.30 | 72.75 | 72.75 | 81.28 | 81.28 |
| BBox | G→S | 66.70 | 66.70 | 74.72 | 74.72 | 82.48 | 82.48 |
| Mask | G→S | 67.04 | 67.04 | 74.72 | 74.72 | 82.94 | 82.94 |

### Result

```text
Table 2 GAGeo detection results
successfully reproduced.
```

---

# 18. Table 3 — Segmentation Reproduction

## Seen

| Prompt | View | Paper mIoU | Ours mIoU | Paper mDice | Ours mDice | Paper AAE | Ours AAE | Paper ME | Ours ME |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Point | D→S | 79.39 | 79.39 | 87.50 | 87.50 | 793.2 | 793.2 | 6.16 | 6.16 |
| BBox | D→S | 82.28 | 82.28 | 89.69 | 89.69 | 530.7 | 530.7 | 4.35 | 4.35 |
| Mask | D→S | 83.19 | 83.19 | 90.35 | 90.35 | 488.2 | 488.2 | 4.05 | 4.05 |
| Point | G→S | 77.37 | 77.37 | 84.01 | 84.01 | 1758.1 | 1758.1 | 19.18 | 19.18 |
| BBox | G→S | 77.36 | 77.36 | 83.99 | 83.99 | 1734.2 | 1734.2 | 19.57 | 19.57 |
| Mask | G→S | 77.21 | 77.21 | 83.82 | 83.82 | 1770.9 | 1770.9 | 19.74 | 19.74 |

## Unseen

| Prompt | View | Paper mIoU | Ours mIoU | Paper mDice | Ours mDice | Paper AAE | Ours AAE | Paper ME | Ours ME |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Point | D→S | 81.47 | 81.47 | 88.83 | 88.83 | 810.8 | 810.8 | 5.57 | 5.57 |
| BBox | D→S | 84.12 | 84.12 | 90.86 | 90.86 | 570.1 | 570.1 | 4.02 | 4.02 |
| Mask | D→S | 85.11 | 85.11 | 91.58 | 91.58 | 461.2 | 461.1 | 3.61 | 3.61 |
| Point | G→S | 72.68 | 72.68 | 78.63 | 78.63 | 2691.4 | 2691.4 | 31.04 | 31.04 |
| BBox | G→S | 73.82 | 73.82 | 79.76 | 79.76 | 2528.7 | 2528.7 | 29.40 | 29.40 |
| Mask | G→S | 74.07 | 74.07 | 80.03 | 80.03 | 2533.4 | 2533.4 | 28.85 | 28.85 |

The small AAE difference for Unseen D→S Mask:

```text
Paper:
461.2

Released evaluator:
approximately 461.1
```

is only a rounding-level difference.

### Result

```text
Table 3 GAGeo segmentation results
successfully reproduced.
```

---

## 19. Observation — Richer Prompts Strongly Help D→S

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

The trend is clear:

```text
Point
  ↓
BBox
  ↓
Mask

More detailed target-region information
→ Better Drone-to-Satellite performance
```

This indicates that D→S localization benefits substantially from richer geometric prompt information.

---

## 20. Observation — Rich Prompts Barely Improve Seen G→S

Seen G→S detection:

```text
Point = 71.50
BBox  = 71.50
Mask  = 71.41
```

Unlike D→S, increasing prompt precision produces almost no improvement.

This suggests that the main G→S bottleneck may not simply be inaccurate target-region specification.

Potential explanations to investigate later include:

```text
Extreme viewpoint difference

Ground/satellite appearance inconsistency

Occlusion

Limited visible façade information

Cross-view geometric ambiguity

Information loss in ground observations
```

This is an important direction for later failure analysis.

---

## 21. Observation — Unseen G→S Is More Difficult

Point prompt:

```text
Seen G→S mAcc
= 71.50

Unseen G→S mAcc
= 65.30
```

Segmentation:

```text
Seen G→S mIoU
= 77.37

Unseen G→S mIoU
= 72.68
```

A noticeable degradation occurs when G→S localization is evaluated in unseen environments.

D→S does not show the same level of degradation.

Therefore:

```text
Ground → Satellite
```

appears to remain a more difficult generalization problem.

---

## 22. Seen vs Unseen

Seen and Unseen should not be confused with different prompt types or different models.

### Seen

The evaluation remains within environments/distributions represented during training.

```text
Training distribution
        ↓
Seen test samples
```

The exact test images are not training samples, but the environment/domain is familiar.

### Unseen

The model is evaluated on new environments/scenes not represented in training.

```text
Training distribution
        ↓
New environment
        ↓
Unseen evaluation
```

This measures scene-level generalization.

---

## 23. Seen / Unseen Split Inconsistency

An important issue was identified during reproduction.

The paper Sec. 5.1 states:

```text
4,197 Seen pairs
4,220 Unseen pairs
```

However, the released evaluator produces:

```text
test
= 4220 samples

unseen_test
= 4197 samples
```

The numerical evidence is stronger than the sample-count description.

The released:

```text
test
```

results exactly match the **Seen** columns of Tables 2 and 3.

The released:

```text
unseen_test
```

results exactly match the **Unseen** columns.

Therefore the mapping used in this reproduction is:

```text
test
→ Seen
→ 4220 samples

unseen_test
→ Unseen
→ 4197 samples
```

The current evidence strongly suggests that the two sample counts in Sec. 5.1 may have been accidentally swapped.

This should still be confirmed with the authors before describing it as a definitive typo.

---

# 24. Current Reproduction Progress

Completed:

```text
Environment Setup                 ✅
CMA-Loc Dataset Setup             ✅
Dataset Symbolic Links            ✅
Released Checkpoint Loading       ✅

Seen + Point                      ✅
Seen + BBox                       ✅
Seen + Mask                       ✅

Unseen + Point                    ✅
Unseen + BBox                     ✅
Unseen + Mask                     ✅

Drone → Satellite                 ✅
Ground → Satellite                ✅

Table 2 Detection                 ✅
Table 3 Segmentation              ✅
```

Current conclusion:

> The officially released GAGeo checkpoint successfully reproduces the core CMA-Loc benchmark results reported in Tables 2 and 3.

---

# 25. What Has NOT Yet Been Reproduced

The complete paper reproduction is not finished.

The following major experiments remain.

---

## Table 4 — OOD / Zero-Shot Dataset Transfer

Training dataset:

```text
CMA-Loc
```

Evaluation dataset:

```text
CVOGL / CVOGL-Seg
```

without dataset-specific fine-tuning.

This evaluates:

```text
Out-of-Distribution (OOD)
generalization
```

The distinction is:

```text
Unseen
= same CMA-Loc benchmark
  but unseen scenes/environments

OOD
= different dataset/domain
```

---

## Table 5 — Ground → Drone Zero-Shot

Training cross-view relationships:

```text
Ground → Satellite

Drone → Satellite
```

New evaluation relationship:

```text
Ground → Drone
```

The model was not directly trained on this matching relationship.

Therefore this evaluates:

```text
Novel cross-view
zero-shot generalization
```

This experiment is particularly important for testing the paper's satellite-anchor contrastive-learning strategy.

---

## Table 6 — Loss Ablation

The paper evaluates:

```text
Base

+ Deep Supervision

+ Contrastive Learning

+ Camera Pose Loss
```

The purpose is to determine:

```text
Which training components
actually contribute to performance?
```

These experiments may require separate checkpoints or retraining.

---

## Figure 4 — Structural Ablation

The paper studies the number of learnable task tokens:

```text
1
2
4
```

and compares different 3D foundation backbones:

```text
VGGT
WorldMirror
π3
```

These experiments may require separately trained models and have higher computational cost.

---

# 26. Zero-Shot vs Unseen vs OOD

These concepts all involve data that the model has not directly seen, but at different levels.

### Unseen

```text
Same benchmark
+
Same task relationship
+
New environment
```

Example:

```text
CMA-Loc
G→S
new scene
```

---

### OOD

```text
Different dataset/domain
```

Example:

```text
Train:
CMA-Loc

Test:
CVOGL-Seg
```

The image style, collection process, annotation distribution, and target distribution may all change.

---

### Novel Cross-View Zero-Shot

The view relationship itself changes.

Training:

```text
G→S
D→S
```

Testing:

```text
G→D
```

Therefore the model must generalize to a cross-view pairing that was not directly trained.

---

# 27. Next Reproduction Plan

The next phase should follow:

```text
1. Inspect available evaluation scripts

2. Inspect released checkpoints

3. Determine which Table 4 / Table 5 / Table 6
   experiments can be reproduced directly

4. Reproduce Ground→Drone zero-shot

5. Reproduce OOD transfer

6. Select high-value ablation experiments

7. Perform failure analysis

8. Identify limitations

9. Develop model-level innovation
```

Priority:

```text
CMA-Loc Main Benchmark
✅ Completed

Ground→Drone Zero-shot
→ High Priority

OOD Dataset Transfer
→ High Priority

Loss Ablation
→ Medium / depends on released checkpoints

Backbone Ablation
→ Medium / potentially expensive

Failure Analysis
→ Required

Innovation Analysis
→ Required
```

---

# 28. Research-Oriented Reproduction Logic

The overall research workflow is:

```text
Paper Understanding
        ↓
Environment / Dataset Preparation
        ↓
Official Baseline Reproduction
        ↓
Paper vs Ours Verification
        ↓
Generalization Evaluation
        ↓
Ablation Study
        ↓
Failure Analysis
        ↓
Limitation Identification
        ↓
Model Innovation
```

The purpose is not only to reproduce identical numbers.

The important research questions are:

```text
When does GAGeo work?

When does GAGeo fail?

Why does rich prompt information
strongly improve D→S
but barely improve Seen G→S?

Why does unseen G→S generalization degrade?

How much does the π3 geometric prior contribute?

How important is contrastive learning
for G→D zero-shot transfer?

Can prompt utilization be improved?

Can cross-view token interaction be improved?

Can the heavy 3D foundation backbone
be made more efficient?

Which front-end modification could provide
a meaningful and experimentally testable
research contribution?
```

---

# 29. Current Milestone

```text
GAGeo Main Benchmark Reproduction
=================================

CMA-Loc
    ↓

Seen / Unseen
    ↓

Point / BBox / Mask
    ↓

D→S / G→S
    ↓

Detection + Segmentation
    ↓

Paper vs Ours
    ↓

Table 2 + Table 3
Successfully Reproduced
```

Next milestone:

```text
Generalization Reproduction
===========================

Ground → Drone Zero-Shot
+
OOD Dataset Transfer
```