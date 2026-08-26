# Research Directions

These are ongoing research explorations motivated by paper reading and reproduction. They are **not claimed as finalized contributions**.

## 1. Sparse-Guided Coarse-to-Fine Matching
Use inexpensive sparse/global correspondence cues to identify reliable regions, followed by selective dense matching.

```text
Global / Sparse Matching
        ↓
Reliable Region Selection
        ↓
Selective Dense Matching
        ↓
Geometric Verification
```

### Motivation
Dense matching everywhere may be computationally expensive and may introduce ambiguous correspondences in repetitive or irrelevant regions.

### Questions
- How should reliable regions be selected?
- Can geometric consistency guide region selection?
- What is the accuracy/speed trade-off?

## 2. Feature Reuse Across Retrieval and Matching
Typical pipelines extract representations independently at multiple stages:

```text
Retrieval → Matching → Alignment → Localization
```

A possible direction is to reuse or adapt intermediate retrieval features for subsequent matching.

### Questions
- Which feature levels are transferable between retrieval and matching?
- Does reuse reduce computation without hurting local correspondence quality?
- Should a shared backbone use task-specific lightweight heads?

## 3. Cross-View Feature Alignment
Explore representations robust to:
- viewpoint changes,
- scale changes,
- ground/UAV/satellite domain gaps,
- repetitive structures,
- weak texture.

Potential tools include Transformer-based interaction, cross-attention, region alignment, and geometry-aware constraints.

## 4. Geometry-Aware Front-End
Instead of treating geometry only as a final PnP step, investigate whether geometric cues can improve earlier stages such as:
- candidate re-ranking,
- correspondence filtering,
- region selection,
- cross-view feature alignment.

## Evaluation Principle
Any proposed improvement should be evaluated against:
- retrieval quality,
- matching quality,
- localization accuracy,
- computational cost,
- robustness/failure cases.
