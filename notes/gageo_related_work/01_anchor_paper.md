# 01 — Anchor Paper

## Paper

**Beyond 2D Matching: A Unified Single-Stage Framework for Geometry-Aware Cross-View Object Geo-Localization**

Anchor reading note: [`papers/gageo.md`](../../papers/gageo.md).

## Motivation

传统 cross-view 方法多依赖整体 2D appearance similarity，但 Ground 主要看到 facade，Satellite 主要看到 roof/footprint；相同建筑在两视角中可能缺少直接可见表面重叠。论文因此把 CVOGL 从纯 2D matching 扩展为 prompt-conditioned、geometry-aware 的 object localization。

## Task

给定 query image (I_q)、reference image (I_r) 和定义在 query 上的 spatial prompt (p)，模型在 reference 坐标系中定位同一目标：

\[
F(I_q, I_r, p) \rightarrow y_r.
\]

主任务输出是 reference 上的 target bbox 和 target mask。模型还联合预测 query camera 在 reference 中的位置与相对旋转。

## Core contributions

1. **CMA-Loc dataset**：Ground–Satellite、Drone–Satellite、point/bbox/mask、object masks 与 camera pose supervision。
2. **Unified single-stage GAGeo**：把 visual tokens、prompt representations 和 learnable task tokens 直接放进 π³ 的交替 local/global attention 中。
3. **Geometry-aware multi-task learning**：联合 bbox、mask、camera position、rotation 与 deep supervision，使共享表示不能只依赖外观相似度。
4. **Satellite-anchored contrastive learning**：对 mask-pooled object features 做对比学习，用 Satellite 作为 Ground 与 Drone 的共同桥梁，支持 zero-shot Ground→Drone。

## Component roles

- frozen DINOv2：两张图的 patch-level visual encoder；
- pretrained/frozen SAM2 prompt encoder：point/bbox sparse tokens 与 mask dense embedding；
- π³：继承 3D prior、交替执行 within-view 与 cross-view attention；
- object / position task tokens：在 reference stream 聚合任务信息；
- lightweight heads：输出 bbox、mask、camera-position heatmap 和 rotation matrix。

## What is not the novelty

单独使用 DINOv2、SAM2 或 transformer 不是论文的核心新意。创新主张在于：将 prompt、task token、π³ geometry prior、特殊 attention isolation 和多任务输出组织进统一 CVOGL forward path，并用 Satellite bridge 学习跨 view-family 表示。

## Research relevance

对本研究最重要的问题不是“能否再堆一个 foundation model”，而是：在 Ground + Small 等失败组中，target signal 是在 frozen DINOv2 阶段已经不足、在 π³ cross-view interaction 中被稀释，还是一直保留到最终却被 task head 选错。该问题尚未被现有 aggregate benchmark 回答。
