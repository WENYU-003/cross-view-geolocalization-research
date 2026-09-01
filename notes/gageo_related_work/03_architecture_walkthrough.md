# 03 — Architecture Walkthrough

本文件以发布 GAGeo code revision `f6585cb` 为实现依据。核心入口是 `CrossViewLocalizer.forward`。

## End-to-end data flow

```text
front/query RGB [B,3,518,518] ─┐
                               ├─ frozen DINOv2 ViT-L/14 ─→ query/reference patch tokens
sat/reference RGB [B,3,518,518]┘                                  │
                                                                 │
query point/bbox/mask ─→ GeometryPromptEncoder (SAM2-adapted) ────┤
                                                                 │
reference-side learnable object/position tokens ─────────────────┤
                                                                 ↓
                                                 Pi3Backbone decoder
                                      18 × (local block + global block)
                                                                 ↓
                    reference features / query features / learnable task-token outputs
                              ├─ BBoxHead → boxes + confidence
                              ├─ SAMMaskHead → model mask + predicted IoU
                              ├─ HeatmapHead → camera-position heatmap + soft-argmax position
                              └─ Pi3CameraHead → rotation matrix + yaw/pitch/roll
```

## 1. Image encoding

`Pi3Backbone.forward` stacks Satellite first and front/query second, normalizes them, flattens to `B×2`, then calls `dinov2_vitl14_reg`。默认：

```text
image size = 518
patch size = 14
patch grid = 37 × 37
patch tokens per view = 1369
encoder / decoder token dim = 1024 for large
final exported feature dim = 2048 (last two decoder blocks concatenated)
```

DINOv2 encoder 提供单图视觉 patch tokens；跨视角 interaction 发生在后续 π³ decoder，不发生在 DINOv2 内。

## 2. Prompt encoding

`GeometryPromptEncoder.forward`：

- point → positional encoding + point-type embedding；在没有 box 时按 SAM convention 加一个 padding/not-a-point token；
- bbox `(x,y,w,h)` → top-left / bottom-right 两个角点 token；
- mask → resize 到 148×148，再经 CNN downscaling 到 `[B,C,37,37]`；
- SAM-native 256-D 表示经 trainable projection 对齐 π³ decoder dimension。

只有真实 mask prompt 时 dense embedding 才传给 backbone；无 mask 的 `no_mask_embed` 不被作为 dense injection 使用。

## 3. π³ token layout and interaction

Local stage 分别处理：

```text
Satellite/reference stream: register + satellite patches + learnable task tokens
Front/query stream:         register + query patches + sparse prompt tokens
```

Global stage 拼接：

```text
[satellite, front/query, learnable task tokens, sparse prompt tokens]
```

Point/bbox token 只能直接吸收 query context；attention mask 阻止它与 satellite 和 task tokens 直接交互。跨视角影响通过“prompt → query features → global interaction → reference/task features”间接传播。

Mask prompt 默认 `global_kv`：dense embedding 只加到 global attention 中 query patch 的 K，不加到 Q/V。它改变其他 token 对 query 区域的 attention weight，而不直接把 dense mask 残差写进所有输出 feature。

## 4. Task tokens and heads

`learnable_out` 被拆成：

- `bbox_queries`：供 bbox 和 mask 两个 object heads 共用；
- `heatmap_queries`：聚合后供 camera-position head 使用。

具体输出：

- `BBoxHead`：3-layer MLP 输出 normalized `cxcywh`，linear classifier 输出 confidence；
- `SAMMaskHead`：将 reference 37×37 features 上采样到 148×148，由 object token 生成 dynamic kernel，点积后插值到 518×518；这里的 “SAM-style” 是 head 设计，不是推理时外接 SAM；
- `HeatmapHead`：position token 与 reference spatial features 点积，生成 heatmap，经 soft-argmax 得到 normalized `(x,y)`；
- `Pi3CameraHead`：使用 query 与 reference patch features 估计相对 rotation matrix。

## 5. Training state

论文和发布配置说明：

- DINOv2 encoder frozen；
- SAM prompt encoder 的 pretrained native layers frozen，projection trainable；
- π³ backbone 与 camera head 由 pretrained weights 初始化并训练；
- task tokens、prompt projections、bbox/mask/position heads 从任务训练中学习；
- contrastive head 只在提供 query/reference GT masks 时计算 mask-pooled object alignment loss；evaluation 中传入 `mono_mask=None, sat_mask=None`，不会更新 queue 或产生训练 loss。

## 6. Deep supervision

默认 supervision stages 为 4、11、17（每个 stage 是一对 local+global blocks）。中间 object/reference features 送入独立 bbox/mask heads；早期/中期 stage 还可计算 position 和 rotation supervision。这是训练稳定性策略，不代表 inference 需要三个串行 detector。
