# Cross-View Geo-Localization Research

Research notes, paper reproductions, experiments, and ongoing exploration in **Cross-View Geo-Localization (CVGL)**, **UAV Visual Localization**, **Feature Matching**, **Vision Transformers**, and **Multimodal Vision**.

This repository documents my research progress from fundamental computer vision and multi-view geometry to paper reproduction, experimental analysis, and the exploration of potential front-end improvements for cross-view geo-localization.

---

## 🔍 Research Interests

My current research interests focus on:

- Cross-View Geo-Localization (CVGL)
- UAV Visual Localization
- Image Retrieval & Feature Matching
- Cross-View Feature Alignment
- Vision Transformers
- Multimodal Representation Learning
- Geometry-Aware Visual Localization
- Coarse-to-Fine Matching
- Feature Reuse across Retrieval and Matching

A major focus of my current work is understanding how **retrieval, feature representation, cross-view matching, and geometric reasoning** interact in practical geo-localization systems.

---

## 📚 Paper Reading

### Cross-View Geo-Localization & UAV Localization

| Paper / Method | Main Topic | Status |
|---|---|---|
| **AnyVisLoc** | UAV visual localization under low-altitude multi-view observation | Reproduced |
| **UniGeoRS / CAME** | Unified tri-view geo-localization and cross-view matching enhancement | Studied |
| **GAGeo** | Geometry-aware cross-view geo-localization | Reproduction in progress |
| **Wrivinder** | SfM + 3DGS based ground-to-satellite geo-localization | Studied |
| **PiLoT** | Neural pixel-to-3D registration for UAV geo-localization | Studied |

### Feature Matching & 3D Vision

Topics and representative methods studied include:

- SIFT
- Lowe Ratio Test
- RANSAC
- Homography
- SuperGlue
- LoFTR
- DUSt3R
- MASt3R
- Sparse and dense feature matching
- Learned local feature correspondence

---

## 🧪 Reproduction Projects

### 1. AnyVisLoc / UAV-AVL

**Status: Core paper-level reproduction completed**

I reproduced and analyzed the main UAV visual localization pipeline:

```text
UAV Query
    ↓
Image Retrieval
    ↓
Reference Candidate Selection
    ↓
2D-2D Feature Matching
    ↓
DSM-assisted 2D-3D Correspondence Construction
    ↓
PnP / P3P
    ↓
UAV Position Estimation
```

The completed UAV-AVL research line includes related-work synthesis, raw-evidence-backed Scene_16 failure attribution, satellite GT-reference diagnostics, spatial-support analysis, counterexample isolation, and solver-provenance recovery.

Current decision:

- reproduction completed;
- aerial/satellite gap confirmed;
- retrieval alone does not explain the gap;
- Agreement, match count, and simple coverage are insufficient localization-utility indicators;
- the current satellite correspondence-consistency proposed-method direction is **NO-GO / frozen**;
- UAV-AVL remains available as a future external validation / secondary benchmark.

Start here:

- [UAV-AVL research checkpoint](notes/uavavl_related_work/12_uavavl_research_checkpoint.md)
- [Related-work and failure-analysis index](notes/uavavl_related_work/README.md)
- [AnyVisLoc reproduction and analysis scripts](reproductions/anyvisloc/README.md)

### 2. GAGeo / CMA-Loc

The next active research line returns to GAGeo/CMA-Loc from its existing reproduction results and per-sample failure evidence. UAV-AVL hypotheses must not be transferred into GAGeo without independent support.

Existing record: [GAGeo reproduction](reproductions/gageo/README.md).

---

## Repository Map

- `papers/`: individual paper-reading notes;
- `notes/`: technical learning notes and cross-paper research synthesis;
- `reproductions/`: baseline reproduction records, lightweight derived results, and analysis code;
- `ideas/`: research directions that remain hypotheses until supported by evidence.

Datasets, model weights, checkpoints, raw result bundles, caches, and large generated outputs are intentionally kept outside Git.
