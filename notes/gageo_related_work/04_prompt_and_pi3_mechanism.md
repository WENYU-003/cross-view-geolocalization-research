# 04 — Prompt and π³ Mechanism

## Point and BBox prompts

**FACT [Paper + Official code]**

- point/bbox 定义在 query image；
- point/bbox 经 `GeometryPromptEncoder` 形成 sparse embeddings；
- bbox 输入格式是 query pixel-space `(x,y,w,h)`，编码为两个角点；
- sparse tokens 加到 query/front local stream；
- sparse prompt 与 reference/task tokens 直接隔离；
- prompt coordinates 同时用于 RoPE spatial position。

**INTERPRETATION**

Sparse prompt 的作用不是直接提供“卫星图上的位置”，而是先让 query features 形成 target-conditioned representation。随后普通 query image tokens 参与 global attention，把目标相关信息带到 reference 与 task tokens。隔离 mask 防止模型把 query prompt coordinate 错当成 reference coordinate。

## Mask prompt

**FACT [Paper + Official code]**

- binary query mask 经 CNN 变为与 37×37 patch grid 对齐的 dense embedding；
- 默认 `mask_inject_mode=global_kv`；
- dense embedding 仅在 global attention 中加到 query patch keys；
- Q 与 V 仍来自未直接加 mask 的 global token sequence；
- code 还保留 `global_qkv` 和 `pre_backbone` 可配置模式，但 published default 是 `global_kv`。

**INTERPRETATION**

Key-only modulation 主要改变“reference/task token 应关注哪些 query patches”的分配，而不是永久覆写 query visual feature。它试图在保留 π³ input symmetry / feature distribution 的同时引入 dense target prior。

## What π³ actually does

**FACT [Paper + Official code]**

- DINOv2 先独立编码两张图；
- π³ decoder 交替 local attention 与 global attention；
- local block 建模 each-view context；
- global block 允许 reference、query 与 task tokens 交换信息；
- GAGeo 去除/避免依赖 first-frame anchor 的 order-dependent components，并使用 π³ permutation-equivariant design；
- task-specific predictions 从更新后的 task tokens 与 reference spatial features解码。

**INTERPRETATION**

“Geometry-aware”不等于网络显式执行 epipolar matching、triangulation 或 PnP。这里的 geometry 主要来自：

1. π³ pretrained representation 的多视图/3D prior；
2. query-reference joint attention；
3. camera position / rotation supervision；
4. object-level mask/box spatial supervision。

因此不能仅由 backbone 名称断言某个 sample 的预测使用了正确 3D correspondence；这需要额外 diagnostic。

## Task-token asymmetry vs permutation equivariance

**FACT**

视觉 backbone 设计减少 view-order bias，但 GAGeo task interface 仍有角色不对称：prompt 属于 query，prediction task tokens 属于 reference。Permutation equivariance 指交换输入 view 时 representation 不应被固定“第一帧坐标”绑死，不表示 query/reference 的任务语义完全相同。

## Current unanswered mechanism question

现有 aggregate results 和 failure CSV 只能说明 Ground + Small 更常出现 bbox/mask 双零。它们没有说明：

- frozen DINOv2 中 target patches 是否已缺少可分辨信息；
- prompt 是否成功提高 query target-region feature salience；
- π³ global attention 是否把正确 instance 信息传播到 reference；
- task head 是否在已有正确 feature 的情况下选错 neighboring building。

这些仍是 Phase 3 要区分的竞争解释，当前不应写成 conclusion。
