# 07 — Related Work Tutorial and Previous-Idea Re-evaluation

## 0. 阅读说明与证据边界

这是一份学习用教程，不是论文的 Related Work 初稿，也不选择最终 proposed method。目标是把 Phase 1–3 的索引、taxonomy 和 comparison matrix 转换成可以用于方法设计的技术理解。

本文使用以下标签：

- **[Paper]**：来自论文原文；
- **[RAW_VERIFIED]**：来自已恢复的 AnyVisLoc Scene_16 raw artifacts，并在 `06_failure_to_limitation.md` 中完成复核；
- **[Inference]**：由论文结构或现有结果推导出的解释，不是作者原话；
- **[Hypothesis]**：仍需 controlled experiment 验证的研究假设；
- **[Uncertainty]**：现有原文、代码或实验记录不足以确认。

特别注意：论文中的 “unified”“end-to-end” 和 “training-free” 不是同义词。一个方法可以在 inference 时共用表示，但没有联合训练；也可以端到端回归，却不显式建立可解释的几何对应。

---

# Part 1 — AnyVisLoc baseline recap

## 1.1 它解决的任务

AnyVisLoc/UAV-AVL 研究低空、多视角、GNSS-denied UAV visual localization。给定 UAV RGB query、相机内参、近似 altitude/pitch/yaw，以及带地理坐标的 aerial/satellite image 和 DSM，它希望输出 UAV 的绝对位置/姿态。

它的核心不是一个单一网络，而是一个模块化 benchmark：

```text
UAV RGB query Iq ∈ R^(3×Hq×Wq)
  + intrinsics K
  + approximate altitude / pitch / yaw
        ↓ pose-aware rotation, scale and crop preparation
reference map tiles {Ir_j}
        ↓ retrieval encoder (canonical baseline: CAMP)
global descriptors gq, {gr_j}
        ↓ similarity ranking
Top-K candidate tiles
        ↓ local/dense matcher (canonical baseline: RoMa)
2D–2D matches {(uq_i, ur_i, confidence_i)}
        ↓ reference geotransform + DSM lookup
2D query points uq_i ↔ 3D world points Pw_i=(X_i,Y_i,Z_i)
        ↓ P3P/PnP inside RANSAC
candidate poses + inliers
        ↓ Top-N decision
absolute UAV pose and metric localization error
```

四个概念必须分开：

```text
retrieval similarity
    ≠ visual correspondence correctness
    ≠ 2D–3D geometric solvability
    ≠ geographic correctness of the returned pose
```

## 1.2 五个模块分别在做什么

| 模块 | 输入 → 输出 | 它真正解决的问题 | 主要风险 |
| --- | --- | --- | --- |
| Retrieval | query/map image → global descriptor → Top-K | 从大地图中缩小搜索区域 | 相似的 tile 未必适合精确定位；正确/可用 tile 可能不在 rank 1 |
| Feature extraction | pixels → global/local feature tensors | 把跨视角外观变成可比较表示 | query/reference domain、scale、resolution 和 objective 不一致 |
| Matching | query feature ↔ candidate feature → 2D–2D pairs | 找局部对应 | 重复纹理、低 overlap、façade-to-roof、错误表面对应 |
| Geometry/localization | 2D–2D + DSM → 2D–3D → pose | 把像素对应变成地理坐标 | DSM 缺失/粗糙/错位；PnP 可解但地理位置错误 |
| Pose prior | yaw/pitch/altitude → rotate/scale/crop | 降低视角和搜索难度 | 视觉方法依赖传感器归一化；prior error 会跨阶段传播 |

## 1.3 当前最重要的本地证据

Scene_16 canonical full run 是 `20260820-2000_1scenes/aerial/aerial-CAMP-Roma-yp`，共 295 queries：mean error 0.4738 m、median 0.3146 m、SR@1m 89.83%、SR@3m 99.66%。

- Retrieval-only：R@1 68.47%、R@3 92.20%、R@5 95.25%。79 个 query 的 GT rank 在 2–5，其中 67 个在 full Top-N pipeline 中达到 1 m，79 个全部达到 3 m。[RAW_VERIFIED]
- GT rank 与 final error 几乎无单调关系：Spearman `rho=0.0079`, permutation `p=0.894`。[RAW_VERIFIED]
- 295 个 canonical samples 全部 `pnp_success=true`，但 30 个 error >1 m，1 个 >3 m；PnP inlier count 与 error 的 Spearman `rho=0.0291`, `p=0.617`。[RAW_VERIFIED]
- Satellite reference 同样 295/295 PnP success，但 median error 7.425 m、mean 94.683 m。[RAW_VERIFIED]
- `yp` 改成 `p` 后 median 2.141 m、mean 114.194 m，说明 yaw-alignment pathway 是强依赖，但尚不能定位影响首先发生在哪一层。[RAW_VERIFIED]

这些证据支持研究 retrieval-to-localization interface、cross-view representation 和 geometry confidence；但由于缺少 candidate IDs/scores、per-candidate matches/poses、exact config/seed，它们还不能证明某个具体机制就是答案。

---

# Part 2 — 8 Tier-1 papers detailed explanation

## 2.1 PiLoT v2 — Pixel-to-Orthogonal Map Alignment

**一句话。** 用轻量 TDOM+DSM 取代 3D mesh rendering，在 sequential pose prior 附近直接做 learned pixel-to-map registration，并把 gravity 和 single-point range 写进 LM 优化。

### 1–4. 问题、输入、pipeline 与模块

它想解决：如何用比 textured 3D mesh 更轻的地图，在 free-view/oblique UAV video 中实时估计 6-DoF pose。

输入是 monocular UAV frame、intrinsics、上一时刻 pose、TDOM、DSM、gravity direction 和单点 laser range。上一姿态不是可选装饰，它用于从大地图截取 local reference。

```text
Iq + previous pose + K
  → crop TDOM/DSM around predicted state
  → shared multi-level feature/uncertainty extractor
  → reference DSM pixels lifted to geo-referenced 3D anchors
  → evaluate many x/y/yaw hypotheses
  → coarse-to-fine LM on SE(3)
     [feature residual + gravity residual + range residual]
  → 6-DoF pose
```

核心模块：local map crop 降低搜索空间；shared encoder-decoder 产生跨视角多层特征和 uncertainty；multi-hypothesis initialization 扩大局部收敛域；LM 将视觉与物理传感器约束共同优化。

### 5–11. Backbone、retrieval、alignment、geometry、prior、training、loss

- **Backbone/feature：** 沿用 PiLoT 式轻量 shared encoder-decoder，产生三层 feature pyramid 和 uncertainty map；论文实验涉及 MobileOne 系列。[Paper]
- **Retrieval：** 没有 conventional global retrieval。它由 previous pose 决定 local crop，再在 crop 内做 hypothesis search。
- **Matching/alignment：** 不是先输出离散 keypoint matches；对参考 DSM 像素对应的 3D anchors，在当前 pose hypothesis 下投影进 query feature map，最小化 query/reference feature residual：

  `r_(j,l)=f_q^l(π(K_l,T^-1 P_j))-f_r^l(p_j^r)`。

- **Geometry/localization：** 在 `SE(3)` 上 coarse-to-fine Levenberg–Marquardt；参考侧 DSM 提供 3D。
- **Pose prior：** 强依赖 sequential state 来 crop；另使用 gravity 和 single-point range。它不是 global lost-in-space solution。
- **是否训练：** 是。跨视角 feature registration network 用 AirSim–Cesium–Unreal 合成的精确几何数据训练，并强调 zero-shot real-world transfer。
- **Loss/supervision：** 以已知 geometry/pose 形成 reprojection/registration supervision；通过 differentiable optimizer 和 robust Barron-type residual 学 feature 与 uncertainty。推理目标可概括为 `E=E_feature+λ_g E_gravity+λ_r E_range`。

### 12–16. 贡献、最强点、局限、与 AnyVisLoc 区别、研究启示

- **主要贡献：** lightweight TDOM/DSM direct registration；cross-view learned feature；sensor-constrained LM；real-time benchmark。
- **最强点：** 它不是只提高 matcher score，而是直接让 feature 服务于 pose optimization；同时用 2.5D map 避免 PiLoT 的 mesh/rendering 成本。
- **Limitation：** local sequential crop、gravity/range 和可靠 TDOM/DSM 是结构性依赖；LM 仍有 initialization/capture-range 问题；synthetic-to-real 与 map invalidity 未被完全消除。
- **与 AnyVisLoc：** AnyVisLoc 是 global retrieval → explicit matcher → PnP；PiLoT v2 是 prior-localized crop → dense feature residual → LM，无显式 Top-K retrieval/PnP。
- **最值得关注：** geometry-aware feature residual 和 uncertainty 如何进入 optimizer；但“TDOM/DSM direct alignment”本身已被占据，不能作为宽泛 novelty。

Primary source: [PiLoT v2](https://arxiv.org/html/2606.31098)

## 2.2 Unifying UAV Cross-View Geo-Localization via 3D Geometric Perception

**一句话。** 先用 VGGT 把 multi-view UAV sequence 重建为局部 3D，再渲染 satellite-aligned BEV，使 retrieval、candidate alignment 和 3-DoF pose 共享一个 geometry-aware substrate。

### 1–4. 问题、输入、pipeline 与模块

它直接针对 decoupled pipeline 的 objective fragmentation：global descriptor 需要 scene discrimination，而 pose 需要 spatial geometry，两个阶段分别优化会发生 error propagation。

输入是连续多帧 UAV images 和 satellite gallery；输出 absolute position + heading（3-DoF）。

```text
{Iq_n}_(n=1..N)
  → DINOv2 patch tokens t ∈ R^(L×D)
  → VGGT frame-wise/global attention
  → cameras + dense local point cloud
  → ground-plane fitting + virtual orthographic camera
  → satellite-aligned BEV
  → GeM global descriptor → Top-K satellite retrieval
  → Satellite-wise Attention, one candidate at a time
  → geometric/feature validation + relative pose
  → scale from satellite GSD + geo-registration
  → latitude/longitude + heading
```

VGGT 提供 3D reconstruction；BEV 把 oblique perspective 变到接近 satellite projection 的 canonical space；Satellite-wise Attention 防止不同候选相互污染，并把复杂度对 candidate 数量变为线性；geometric validation 结合 visual coverage 与 spatial proximity 选候选。

### 5–11. Backbone、retrieval、alignment、geometry、prior、training、loss

- **Backbone/feature：** pretrained DINOv2 patch tokens；VGGT 将其变成 camera/point-cloud-aware features；GeM 聚合 BEV/satellite global descriptor。
- **Retrieval：** BEV descriptor 对 satellite descriptors 做 Top-K（论文 K=10），而不是直接拿 oblique query 做检索；并提出 overlap-aware `RIoU@K`。
- **Matching/alignment：** satellite tokens 作为 query，UAV scene tokens 作为 shared key/value，按 candidate 隔离 cross-attention；之后估计 satellite camera pose 并做 geometric validation。
- **Geometry/localization：** VGGT local 3D + fitted ground plane → BEV；利用 satellite GSD 恢复 metric scale，把 UAV–satellite relative pose 转到 UTM/GPS 和 heading。
- **Pose prior：** 不需要 AnyVisLoc 式 yaw/pitch/altitude retrieval prior；但需要 multi-view sequence、satellite georeference/GSD，并依赖 local reconstruction quality。
- **是否训练：** 使用 pretrained DINOv2/VGGT 并有 task pipeline；当前论文正文未充分交代哪些组件被 fine-tune、是否真正 joint training。[Uncertainty]
- **Loss/supervision：** 原文清楚定义 inference 与 evaluation metrics，但当前可核对正文没有给出完整 joint loss。不能把“single inference pipeline/shared representation”升级成“所有 stage end-to-end jointly supervised”。[Uncertainty]

### 12–16. 贡献、最强点、局限、与 AnyVisLoc 区别、研究启示

- **主要贡献：** geometry-centric shared representation；BEV retrieval；candidate-isolated attention；University-Pose 3-DoF recalibration 与 overlap-aware evaluation。
- **最强点：** 真正改变了 retrieval 的输入空间：不是强迫 oblique/satellite features 直接 invariance，而是先显式 orthorectify；也让候选按 downstream geometry 验证。
- **Limitation：** multi-view sequence 与 sufficient parallax；VGGT compute/memory；reconstruction/ground-plane failure；satellite GSD/geo-alignment；训练细节和真实低空场景 generalization 仍需核实。
- **与 AnyVisLoc：** AnyVisLoc 分别用 CAMP/RoMa/PnP；该方法以 DINOv2+VGGT 3D/BEV 表示贯通 coarse-to-fine，并绕开 classic PnP。
- **最值得关注：** retrieval label 从 exact tile ID 转为 overlapping/geometrically usable tile；以及 shared representation 是否真的改善 final localization，而不是只增加模型规模。

Primary source: [3D Geometric Perception paper](https://arxiv.org/pdf/2604.01747)

## 2.3 PiLoT — Neural Pixel-to-3D Registration

**一句话。** 用 state-conditioned 3D mesh rendering 生成一个 geo-referenced reference，再以共享多尺度 feature 和 JNGO 直接优化 6-DoF pose，同时支持 target pixel-to-geo projection。

### 1–4. 问题、输入、pipeline 与模块

它想解决 sequential UAV ego localization 与 target geolocation 的实时统一，并避免“为每个 pose hypothesis 都渲染一张图”的开销。

输入：monocular video、known intrinsics、geo-referenced textured 3D mesh、第一帧 pose prior；输出每帧 6-DoF ego pose 和任意 target pixel 的 3D geolocation。

```text
previous estimate
  → constant-velocity KF predicts reference pose
  → render one RGB+depth reference from 3D mesh
  → depth-valid reference pixels back-project to world anchors Pj

query + rendered reference
  → shared MobileOne-S0/U-Net features at 1/4, 1/2, 1 resolution
  → uncertainty maps
  → rotation-aware pose swarm
  → JNGO coarse-to-fine LM feature alignment
  → 6-DoF camera pose
  → query target ray intersects 3D map
  → target lon/lat/alt
```

Dual-thread 把 rendering 与 localization 并行；one-reference-to-many-hypotheses 复用 reference；JNGO 负责 global exploration + local optimization。

### 5–11. Backbone、retrieval、alignment、geometry、prior、training、loss

- **Backbone/feature：** shared MobileOne-S0 前三 stages + U-Net decoder；三层、32-channel feature pyramid 与 uncertainty maps。
- **Retrieval：** 无 global gallery retrieval；由 sequential state 在 3D map 中生成局部 rendered reference。
- **Matching/alignment：** 连续 feature residual，不先导出独立 sparse matches。
- **Geometry/localization：** rendered depth 将 reference pixels 变成 geo-anchors；JNGO 在 SE(3) 上优化 pose；target 用最终 pose 做 ray casting。
- **Pose prior：** 第一帧 single pose prior，随后依赖 KF/上一估计；不使用 GNSS/IMU，但依赖状态连续性。
- **是否训练：** 是，使用大规模 AirSim–Cesium–Unreal synthetic geometry data，强调 zero-shot real-world。
- **Loss/supervision：** ground-truth pose/depth 提供 differentiable reprojection/registration supervision；robust direct geometric loss 并学习 uncertainty。

### 12–16. 贡献、最强点、局限、与 AnyVisLoc 区别、研究启示

- **主要贡献：** render/localize dual threads；single-reference multi-hypothesis registration；JNGO；ego + target geolocation 一体化。
- **最强点：** feature 的最终消费者就是 pose optimizer，training objective 与 localization 比 modular retrieval/matching 更接近。
- **Limitation：** textured 3D mesh 获取、存储和 online rendering 昂贵；局部 sequential prior 限制 global recovery；synthetic-to-real 风险。
- **与 AnyVisLoc：** AnyVisLoc 可全地图检索、使用轻量 image+DSM；PiLoT 用更重 3D map 和 local state，直接 registration 而非 retrieval→matcher→PnP。
- **最值得关注：** shared feature/uncertainty + differentiable pose optimization；但不能把它的 local tracking setting 与 AnyVisLoc global localization 直接等价比较。

Primary source: [PiLoT](https://arxiv.org/html/2603.20778)

## 2.4 AirLock+

**一句话。** 用 predictive target tracking、learned coarse cross-view alignment、RoMa dense matching 和 RANSAC homography，把 UAV video 中的 target pixel 持续映射到 satellite geodetic coordinates。

### 1–4. 问题、输入、pipeline 与模块

它关注的是 target geolocalization 与 geospatial AR，而不是只估 UAV ego pose。输入包括 UAV video、初始化 target bounding box、相应 geo-referenced satellite map；输出 target trajectory 的 latitude/longitude。

```text
UAV frame It + initial target box
  → YOLO-based predictive tracker → target pixel pA_t

UAV frame + satellite map
  → learned DINOv2 ViT-B/14 coarse alignment/orientation
  → RoMa dense correspondences
  → RANSAC homography H_t
  → temporal plausibility filtering/interpolation

pA_t → H_t pA_t = pB_t
  → satellite pixel-to-geodetic transform π
  → target (lat, lon) trajectory
```

Tracker 保持 target observation；alignment network 处理 rotation/scale 与跨域粗对齐；RoMa 提供 dense correspondences；homography 把两幅图建立 planar pixel mapping；temporal filter 排除不合理速度并补 missing estimates。

### 5–11. Backbone、retrieval、alignment、geometry、prior、training、loss

- **Backbone/feature：** coarse alignment 使用 DINOv2 ViT-B/14、768-D patch embeddings；fine matcher 是 RoMa，其 coarse semantic branch 也使用 DINOv2。
- **Retrieval：** 不是大规模 gallery retrieval；输入 satellite region 已给定/由系统范围确定，重点是 registration。
- **Matching/alignment：** learned coarse alignment 后 swap-in RoMa dense matching；RANSAC 过滤错误 correspondences。
- **Geometry/localization：** 估计 2D homography `p_sat ~ H p_uav`，再用 satellite geotransform 得经纬度；没有 DSM/PnP/6-DoF 3D pose。
- **Pose prior：** 不以精确 UAV pose 为输入，但 learned alignment 处理 heading/scale，temporal dynamics 是一种系统先验。
- **是否训练：** coarse alignment network 训练；RoMa 使用 pretrained model。训练集由 UAV-VisLoc 的 3,394 scenes 各生成十个 physically plausible synthetic views。
- **Loss/supervision：** synthetic aligned pairs 与 orientation labels 监督 alignment network；论文当前可核对片段未完整暴露逐项 loss 公式，故不猜测具体组合。[Uncertainty]

### 12–16. 贡献、最强点、局限、与 AnyVisLoc 区别、研究启示

- **主要贡献：** 可扩展 real-video UAV-to-satellite registration system；target geolocation + AR；真实长轨迹 benchmark。
- **最强点：** 把 DINOv2/RoMa 放进真实 temporal system，并测试 outdated satellite/unseen environments；证明“DINOv2+RoMa 做 satellite registration”不是空白方向。
- **Limitation：** planar homography 难表示显著 relief/façade/parallax；依赖已知 satellite region 和 target tracking；temporal filtering 会掩盖单帧 matcher failure；reported target error 不等同于 6-DoF UAV pose error。
- **与 AnyVisLoc：** AnyVisLoc 先全局检索再 DSM+PnP 估 UAV pose；AirLock+ 直接对给定 satellite region 做 homography，并定位 target。
- **最值得关注：** coarse alignment 对 RoMa 的前置作用，以及 temporal robustness；我们必须避免把其 system-level result 当成纯 matcher result。

Primary source: [AirLock+](https://openaccess.thecvf.com/content/WACV2026/html/Deng_AirLock_Scaling_UAV-to-Satellite_Image_Registration_for_Target_Geolocalization_and_Geospatial_WACV_2026_paper.html)

## 2.5 Scale-Aware U2S-CVGL

**一句话。** 从单帧 UAV image 中检测 small vehicles，把它们当 metric semantic anchors 恢复 GSD，再据此裁剪正确尺度的 satellite image 后运行任意 retrieval model。

### 1–4. 问题、输入、pipeline 与模块

它针对 benchmark 常被隐藏的假设：UAV query 与 satellite gallery 已经具有近似 physical scale/FOV。现实中 altitude/relative ground height 不可靠，resize 到同样像素尺寸并不会消除 GSD mismatch。

输入是 UAV RGB、camera intrinsics、pitch（roll 假设被 gimbal 稳定）、continuous satellite imagery/GSD；输出 global image scale 和 scale-aligned satellite crops，之后再由 plug-in CVGL retrieval 输出位置。

```text
UAV image + K + pitch
  → oriented bounding-box detector
  → small-vehicle boxes {center, length_px, width_px, angle, score}
  → radial/tangential Decoupled Stereoscopic Projection
  → per-instance scales s_len, s_wid → s_i
  → confidence/min-count filtering + IQR aggregation
  → global GSD ŝ
  → metric FOV and satellite crop size
  → standard CVGL retrieval network
  → geo-localized tile/location
```

### 5–11. Backbone、retrieval、alignment、geometry、prior、training、loss

- **Backbone/feature：** scale module 的主要视觉输出是 small-vehicle OBB，而不是 DINO/CLIP feature；后端 retrieval backbone 是 plug-and-play，可接已有 CVGL models。
- **Retrieval：** 先按估计 GSD 自适应 crop，之后仍用 standard image retrieval；它修正 retrieval 的 input construction，而非重写 descriptor objective。
- **Matching/alignment：** 没有 local feature matcher；alignment 指 physical scale/FOV alignment。
- **Geometry/localization：** 使用车辆统计尺寸、camera ray、pitch、车辆 radial/tangential orientation 建模 perspective inflation；`s_i=(s_len+s_wid)/2`，再以 IQR 去异常值。
- **Pose prior：** 不需要 GNSS/altitude/range，但需要 calibrated intrinsics 与 nominal/known pitch，并假设 roll≈0、车辆在 ground plane。
- **是否训练：** 几何 scale recovery 本身无需 end-to-end training；需要已有 OBB detector 与 pretrained CVGL model。是否为特定实验重新训练 detector/model 取决于 implementation，不能笼统写成整个系统 training-free。[Uncertainty]
- **Loss/supervision：** 核心 scale module 是解析几何，无 learned loss；评估使用 scale error 和 downstream retrieval metrics。

### 12–16. 贡献、最强点、局限、与 AnyVisLoc 区别、研究启示

- **主要贡献：** 揭示 scale consistency hidden assumption；semantic metric anchors；stereoscopic projection + robust aggregation；augmented continuous-map/scale annotations。
- **最强点：** 问题定义清晰且物理可解释，能直接改变 downstream crop/FOV，而非期待 encoder 自己吸收任意 scale gap。
- **Limitation：** 需要足够多、检测可靠的小车辆；乡村/森林/高空或严重遮挡时不可用；依赖车辆尺寸分布、intrinsics/pitch 和 continuous satellite map。
- **与 AnyVisLoc：** AnyVisLoc 用 altitude/pitch 做 scale/crop prior；该论文尝试从 image semantics 恢复 scale，再调用 retrieval，不处理 RoMa/DSM/PnP。
- **最值得关注：** 我们的 scale/pose-prior idea 必须先证明 AnyVisLoc failures 的确由 scale mismatch 驱动；否则只是借用一个已有模块。

Primary source: [Scale-Aware U2S-CVGL](https://arxiv.org/html/2603.07535)

## 2.6 Coarse-to-Fine GNSS-Denied UAV Localization

**一句话。** 这是 AnyVisLoc 之前很接近的 modular predecessor：SDS bilateral retrieval → multi-scale improved SuperPoint matching → DSM-supported constrained space resection。

### 1–4. 问题、输入、pipeline 与模块

它解决大 oblique angle 下三个连续问题：tile center 不能代表 UAV camera location、cross-view retrieval/matching 困难、传统 space resection 容易因初始化差而不收敛。

输入是 oblique UAV image、geo-tagged orthographic reference imagery，以及 DOM/DSM 提供的 reference pixel 3D coordinates；输出 UAV fine position/pose。

```text
oblique UAV image + orthographic map
  → SDS line-segment direction pattern
  → bilateral image retrieval
  → candidate reference
  → improved SuperPoint with DGPM
  → candidate correspondences
  → TMRRM two-stage refinement
  → reference pixels lifted by DOM/DSM
  → triangular-pyramid constrained space resection
     + angle-similarity constraint
  → UAV position/pose
```

### 5–11. Backbone、retrieval、alignment、geometry、prior、training、loss

- **Backbone/feature：** matching 基于 improved SuperPoint；DGPM 显式建立 discrete Gaussian multi-scale pyramid。
- **Retrieval：** hand-crafted/geometric SDS 描述 line segment directions，并进行 bilateral retrieval。
- **Matching/alignment：** DGPM 提高 scale/view variation 下的 keypoints/descriptors；TMRRM 两阶段去除错误 matches。
- **Geometry/localization：** DOM/DSM 把 reference 2D 点转成 3D ground coordinates；triangular-pyramid constrained resection 和 angle similarity 改善大斜视初值与收敛。
- **Pose prior：** 原文摘要与当前可访问正文没有清楚证明需要何种 onboard pose prior；不能自行假设。[Uncertainty]
- **是否训练：** improved SuperPoint 使用 multi-view image training strategy。[Paper]
- **Loss/supervision：** 当前可访问 primary page 未给出完整 loss 公式和 training protocol，标记未确认。[Uncertainty]

### 12–16. 贡献、最强点、局限、与 AnyVisLoc 区别、研究启示

- **主要贡献：** 同时改 retrieval、matcher 和 resection；显式处理 oblique scale；解决 tile-center localization 不足。
- **最强点：** 它表明“coarse-to-fine + multi-scale local matching + elevation geometry”在 2024 年已是完整系统，宽泛 pipeline claim 不再 novel。
- **Limitation：** components 多、贡献归因困难；SDS 的语义/跨域 generalization 有限；匹配与最终 geometry 仍 stage-wise；公开 code、完整训练细节和跨域验证不足。
- **与 AnyVisLoc：** 两者都属于 retrieval→matching→2D–3D pose pipeline；AnyVisLoc 更像统一 benchmark、覆盖更多 retrieval/matcher/reference/prior combinations，并采用 CAMP/RoMa/PnP。
- **最值得关注：** 任何 Coarse-to-Fine Matching idea 必须具体到新的 feedback、supervision 或 geometry-conditioned mechanism，不能只说“先粗后细”。

Primary source: [ISPRS JPRS paper](https://doi.org/10.1016/j.isprsjprs.2024.05.006)

## 2.7 OrthoLoC

**一句话。** 构建 paired UAV–DOP/DSM 6-DoF benchmark，把 retrieval error 隔离掉，并用 training-free AdHoP 先估 homography warp DOP、再二次 matching 和 PnP。

### 1–4. 问题、输入、pipeline 与模块

它问的是：在正确 local orthographic geodata 已给定时，现有 matcher 到底能不能跨 perspective/orthographic gap 输出可用于 6-DoF localization/calibration 的对应。

输入是 UAV perspective image、paired DOP、DSM、known intrinsics（localization setting；calibration setting 可估 intrinsics）；输出 6-DoF pose，可选 camera calibration。

```text
UAV image I + paired DOP
  → plug-in matcher → initial 2D–2D correspondences
  → confidence/valid-DSM/FOV filtering
  → DSM lift → 2D query ↔ 3D world
  → RANSAC-EPnP → initial pose

initial 2D–2D matches
  → normalized-DLT + RANSAC homography H
  → warp DOP toward UAV perspective
  → second matching pass
  → map matches back with H^-1
  → DSM lift → refined EPnP/LM
  → accept only if reprojection error decreases
  → 6-DoF pose / calibration
```

### 5–11. Backbone、retrieval、alignment、geometry、prior、training、loss

- **Backbone/feature：** method-agnostic；benchmark 测试 SP+SG、SP+LightGlue、LoFTR、DKM、GIM+DKM、RoMa、MASt3R 等。
- **Retrieval：** paired reference，因此 intentionally decoupled/removed。它不能直接证明 large-gallery retrieval 性能。
- **Matching/alignment：** AdHoP 利用 quasi-planar aerial structures 估 homography，warp 后再次运行同一 matcher；新 matches 变回原 DOP 坐标。
- **Geometry/localization：** DSM lifting；confidence <0.5、invalid 3D、outside-FOV matches 被过滤；5-pixel RANSAC-EPnP，calibration 再用 LM joint refinement。
- **Pose prior：** paired DOP 本身是很强的 location prior；pure localization 假设 intrinsics known，但不要求 AnyVisLoc 式 yaw/altitude crop prior。
- **是否训练：** AdHoP 无训练；plug-in matchers 使用各自 pretrained weights。
- **Loss/supervision：** AdHoP 是解析 homography/RANSAC + reprojection acceptance，没有 learned loss。

### 12–16. 贡献、最强点、局限、与 AnyVisLoc 区别、研究启示

- **主要贡献：** 16.4K paired multimodal 6-DoF dataset；controlled matcher benchmark；AdHoP；domain/resolution/covisibility/calibration analysis。
- **最强点：** 对我们的 failure analysis 最有价值：它把 retrieval 排除，使 matcher、orthographic gap、DSM 和 pose 可单独测；AdHoP 还是低复杂度、可解释 baseline。
- **Limitation：** paired crop 避开 global search；homography 的 quasi-planar assumption 对高度起伏/立面有限；二次 feature extraction 增加成本；AdHoP 依赖 initial matches 足以估 H。
- **与 AnyVisLoc：** 几何后端很接近，但 OrthoLoC 先给正确 local map并做 homography refinement；AnyVisLoc 必须先 retrieval、并承担 Top-K/candidate selection error。
- **最值得关注：** 应优先用它帮助定义 controlled oracle-reference diagnostic，而不是直接把 AdHoP 当 proposed method。

Primary source: [OrthoLoC](https://arxiv.org/html/2509.18350)

## 2.8 Bearing-UAV

**一句话。** 把四个相邻 satellite tiles 组成有坐标结构的 block，用 global-local features、relative coordinate encoding 和 cross-attention 直接回归 block 内位置与 heading，绕过 matcher/PnP。

### 1–4. 问题、输入、pipeline 与模块

它反对把 retrieved tile center 当最终位置：定位精度会被 tile size/density 限制，而且 localization 与 heading 常分两步，error 会继续传播。

输入是 UAV-view patch、包含四个相邻 remote-sensing tiles 的 RSB，以及四个 tile 的 relative coordinates；输出 continuous 2D position 和 heading vector。

```text
UVP + 4 neighboring RSTs
  → shared VGG-16 feature maps F ∈ R^(H×W×D)
  → Non-local block + learnable clustering
  → GLUF vectors (global context + ordered local segments)

tile relative coordinates
  → RCE coordinate embeddings

UVP GLUF ↔ 4 RST GLUFs
  → PSG cosine weights → coordinate prior q ∈ R^2
  → Cross-Attention → overlap-aware feature f
  → concat φ=[u,f,q]
  → two MLP heads
  → relative position p ∈ R^2 and heading (cosθ,sinθ)
  → absolute position from known RSB index
```

### 5–11. Backbone、retrieval、alignment、geometry、prior、training、loss

- **Backbone/feature：** ImageNet-pretrained VGG-16；Non-local block；SGMNet-like clustering，K=4，base D=256，形成 GLUF。
- **Retrieval：** operation 时依据当前 nominal position/index 查找一个 RSB；在 block 内 PSG 用 query-to-four-tile cosine weights 形成 spatial guidance。它不是对无限大 gallery 的 blind global retrieval。
- **Matching/alignment：** 没有 explicit keypoint matches；cross-attention 在 query GLUF 与四个 tile features 间学习 overlap-aware association。
- **Geometry/localization：** 不用 DSM/PnP；relative coordinate embedding 与 known block coordinates 提供隐式 map geometry，MLP 直接回归连续位置和 heading。
- **Pose prior：** 单次模型不需 yaw/pitch/altitude；navigation mode 需要已知起点/当前 nominal RSB index 才能查四邻域，并会随 sequential prediction 更新。
- **是否训练：** 是，在 Bearing-UAV-90K 上 supervised training；默认 VGG-16 backbone。
- **Loss/supervision：** Smooth L1 multi-task loss：`L_sum=0.8 L_position+0.2 L_heading`；heading 用 `(cosθ,sinθ)` 避免角度周期不连续。

### 12–16. 贡献、最强点、局限、与 AnyVisLoc 区别、研究启示

- **主要贡献：** beyond matching-to-tile paradigm；position+heading joint regression；RSB relative structure；90K dataset 与 vision-only navigation。
- **最强点：** objective 直接对齐最终 continuous location/heading，并显式利用 neighboring-tile topology，不受 tile center resolution 的硬上限。
- **Limitation：** 需要正确/邻近 RSB index，global recovery 能力有限；直接 regression 难以做 correspondence-level attribution；依赖较大 supervised dataset，跨 unseen city/general map density 仍有风险；不输出 full 6-DoF。
- **与 AnyVisLoc：** AnyVisLoc 是显式 global retrieval/matching/DSM/PnP；Bearing-UAV 是 local block feature fusion + coordinate regression，无显式 matches 和 PnP。
- **最值得关注：** “retrieval + matching integration”已出现，但它用 direct regression 解题；我们若保留 modular explainability，需要说明与这种 paradigm 的取舍。

Primary source: [Bearing-UAV](https://arxiv.org/html/2603.22153)

---

# Part 3 — Method evolution map

## 3.1 不是单线替代，而是四条演进支路

```text
                                  ┌─ Scale-Aware
                                  │  semantic metric anchor
                                  │  → correct crop/GSD
                                  │  → conventional retrieval
                                  │
AnyVisLoc / C2F modular line ─────┼─ OrthoLoC
retrieval → matcher → DSM → PnP   │  paired DOP/DSM
                                  │  → homography pre-warp
                                  │  → matcher → PnP
                                  │
                                  └─ AirLock+
                                     coarse alignment → RoMa
                                     → planar homography → target geo

Local direct-registration line:
PiLoT: previous state → 3D mesh render → neural feature residual → JNGO/LM
   ↓ reduce map/render cost
PiLoT v2: previous state → TDOM/DSM crop → feature residual + gravity/range → LM

Unified geometry line:
multi-view UAV → DINOv2/VGGT 3D → BEV retrieval
              → candidate-isolated alignment → absolute 3-DoF

Direct regression line:
Bearing-UAV: local 4-tile block + GLUF/RCE/attention
             → position + heading, no explicit matcher/PnP
```

## 3.2 横向分类

| 论文 | Pipeline-based? | Unified 到什么程度 | 是否绕过 retrieval→matcher→PnP | 主要强调 |
| --- | --- | --- | --- | --- |
| AnyVisLoc | 是，最模块化 | 否 | 否 | benchmark、可替换组件、诊断性 |
| C2F | 是 | 否 | 否 | oblique coarse-to-fine、multi-scale、resection |
| Scale-Aware | 是，作为前置插件 | 否 | 否 | physical scale/FOV robustness |
| OrthoLoC | 是 | alignment+geometry 更紧，但 matcher 可替换 | 去掉 retrieval，保留 matcher+PnP | controlled diagnosis、orthographic geometry |
| AirLock+ | 是，system pipeline | registration system-level integration | 无 global retrieval/PnP，使用 homography | real video、target、temporal robustness |
| PiLoT | local direct pipeline | feature+pose optimizer unified | 是 | 3D render、direct registration、real time |
| PiLoT v2 | local direct pipeline | feature+sensor+pose optimizer unified | 是 | lightweight 2.5D map、sensor robustness |
| 3D Geometric | inference 上最接近 unified | 3D/BEV shared across retrieval/alignment/pose | 绕过 classic matcher/PnP，但仍保留 Top-K | 3D geometry、shared representation |
| Bearing-UAV | local block end-to-end regression | representation+position+heading | 是 | objective alignment、relative map structure |

## 3.3 按研究主题理解演进

- **Retrieval：** exact tile classification → overlap-aware/topological candidate → scale-corrected crops → BEV-space retrieval。
- **Matching：** sparse descriptors → dense foundation matching → pre-warped matching → feature residual/direct alignment → no explicit matching。
- **Unified representation：** separate CAMP/RoMa → shared global-local feature heads → VGGT 3D substrate；但“shared”不自动代表两个任务都最优。
- **Geometry：** DSM lifting + PnP → homography preconditioning → constrained resection → direct SE(3) optimization → reconstruction-grounded pose。
- **Pose estimation：** tile center → PnP/resection → learned direct optimizer → coordinate/heading regression。
- **Cross-view alignment：** learn invariance in descriptors → physically align scale/view → render/BEV canonicalization → cross-attention。
- **Robustness：** Top-K rescue、RANSAC、uncertainty、sensor constraints、temporal filtering、多候选隔离分别处理不同 failure source，不能当作同一种 robustness。

---

# Part 4 — Common technical themes

## 4.1 Retrieval similarity vs localization usefulness

**为什么是问题。** Retrieval loss 通常奖励 place identity/descriptor proximity；最终定位需要足够 overlap、可靠 DSM、可观测的 3D distribution 和正确物理 surface。视觉最像的 tile 可能只是重复屋顶，而邻近但非 exact-ID tile 反而有足够 overlap。

**发生层级。** Retrieval output 与 matcher/geometry input 的接口。

**受影响论文。** AnyVisLoc、C2F 最直接；Scale-Aware 只改善 crop；3D Geometric 用 overlap-aware `RIoU@K` 和 geometric validation；Bearing-UAV 用四邻域和直接 position loss；OrthoLoC 通过 paired design 暂时移除该问题。

**为什么没解决。** 现有 proxy 各不相同：tile ID、IoU、feature score、inlier ratio、direct regression。它们仍不是跨 matcher/map/solver 可迁移的 calibrated probability of localization success。

**AnyVisLoc 对应证据。** rank/error `rho≈0.008`，rank 2–5 cohort 广泛可定位。[RAW_VERIFIED] 但缺 candidate-level score/outcome，不能说 CAMP score 已被证明与 localizability 不一致。

## 4.2 Repeated feature extraction

**为什么是问题。** Modular pipeline 中 query 先经 retrieval encoder，之后又被 matcher encoder 编码；Top-K 每个 reference 还可能重复走 dense matcher。大致成本是：

`C_query ≈ C_retrieval + K·C_match-query`，`C_ref ≈ cached_retrieval + K·C_match-ref`。

**发生层级。** Feature extraction / systems efficiency。

**受影响论文。** AnyVisLoc 最明显；OrthoLoC 的 AdHoP 甚至做两轮 matching；AirLock+ coarse alignment + RoMa；C2F 多阶段。PiLoT/PiLoT v2 共享两侧 feature extractor，3D Geometric 尝试共享 DINO/VGGT substrate，Bearing-UAV 可预存 tile GLUF。

**为什么没解决。** Retrieval 需要 invariant/global feature，matching 需要 equivariant/local precise feature；简单共享可能省 compute 却损失 accuracy。Feature reuse 是 optimization goal，不是天然 research contribution。

**AnyVisLoc 证据。** 代码结构支持存在重复路径，但本地没有 per-stage runtime/profile，因此只有 implementation-supported inference，没有 accuracy/latency causal evidence。

## 4.3 Retrieval/matching objective misalignment

**为什么是问题。** Retrieval 常用 contrastive/triplet/classification；matching 学 correspondence/confidence；pose 最终最小化 metric/reprojection error。三个 loss 的 optimum 不必一致：

`argmin L_ret ≠ argmin L_match ≠ argmin E_pose`。

**层级与论文。** AnyVisLoc/C2F 是 hard stage boundaries；PiLoT/PiLoT v2 让 features 直接进入 pose optimizer；3D Geometric 用 shared 3D 表示和 candidate validation；Bearing-UAV 直接监督 position/heading。

**为什么仍未完全解决。** Direct optimization/regression 往往牺牲 global search、诊断性或数据效率；shared inference 不代表 verified joint loss；pose supervision 也可能 overfit map/dataset。

**AnyVisLoc 证据。** GT-reference 与 full run 的 paired difference、rank/error 弱关系提供 interface-level support；尚无 gradient/objective-level proof。[RAW_VERIFIED + Hypothesis]

## 4.4 Cross-view feature inconsistency

**为什么是问题。** Oblique query 看见 façade、透视缩短和遮挡；orthophoto/satellite 更接近 roof/ground orthographic projection。对应 location 不代表对应 pixels 或对应 appearance。

**层级与论文。** Feature extraction/matching。RoMa/DINOv2 提升 semantic tolerance；OrthoLoC 用 homography 预变换；PiLoT 用 view-conditioned rendering；PiLoT v2 学 free-view↔orthomap features；3D Geometric 先重建再 BEV；Bearing-UAV 用 relative context/cross-attention。

**为什么未解决。** Homography 不能表达一般 3D parallax；render/BEV 依赖 geometry；learned invariance 可能损失 precise equivariance；satellite 还有时间与传感器 domain gap。

**AnyVisLoc 证据。** aerial→satellite 的系统级 collapse 很强，但仍混合了 retrieval、imagery、registration、DSM resolution 和 temporal change，不能单独归因 feature。[RAW_VERIFIED]

## 4.5 Scale / resolution gap

**为什么是问题。** 相同 tensor size 不等于相同 meters-per-pixel。若 query FOV 与 candidate FOV 差异大，global context 和 local patch frequency 都会变化。

**层级与论文。** Input preparation、retrieval、matching。Scale-Aware 直接估 GSD；C2F/DGPM 做 multi-scale；PiLoT/PiLoT v2/3D Geometric 通过 geometry/render/BEV 统一尺度；OrthoLoC 明确测 map resolution。

**为什么未解决。** Scale-Aware 需要 semantic anchors；multi-scale 搜索成本高；geometry 方法需要 map/reconstruction；learned multi-scale feature 不能保证 metric scale 可识别。

**AnyVisLoc 证据。** `yp`/`p` 和 reference mode 表明 pose-aware preparation 与 map resolution 很重要，但没有独立 scale-only ablation，因此 scale causality 仍是假设。

## 4.6 Pose prior dependency

**为什么是问题。** Prior 能显著缩小 rotation/scale/search space，却使“视觉鲁棒性”与“传感器归一化质量”混在一起。部署时 yaw drift 或 altitude-to-ground error 会导致系统性错 crop/错方向。

**层级与论文。** Input preparation 和 candidate generation。AnyVisLoc 用 yaw/pitch/altitude；PiLoT/PiLoT v2 用 sequential state，v2 另加 gravity/range；Scale-Aware 用 intrinsics/pitch；AirLock+ 用 temporal continuity；Bearing-UAV 回归 heading，但 navigation 仍需当前 RSB。

**为什么未解决。** 完全 prior-free global localization 搜索空间巨大；强 prior 系统更准但 recovery 更弱。关键不是“要不要 prior”，而是 sensitivity、fallback 与 uncertainty 是否可量化。

**AnyVisLoc 证据。** `yp`→`p` 的 paired aggregate degradation 已 raw verified；受影响的第一个 stage 仍未知。

## 4.7 Geometry / DSM dependency

**为什么是问题。** Reference pixel `(u,v)` 的视觉 match 正确，也可能因 DSM no-data、低 resolution、map misregistration、roof/ground surface ambiguity 得到错误 `P_w=(X,Y,Z)`。

**层级与论文。** 2D–3D lifting 和 pose。AnyVisLoc、C2F、OrthoLoC、PiLoT v2 都依赖 2.5D；PiLoT 依赖更重 3D mesh；3D Geometric 依赖 reconstructed local 3D 和 satellite scale。

**为什么未解决。** 大多数方法把 map 当 deterministic truth；matcher confidence 不等于 elevation validity；更强 3D map 又提高 storage/acquisition cost。

**AnyVisLoc 证据。** Satellite collapse 与 all-PnP-success wrong poses 相符，但缺 DSM validity、surface label、georegistration residual，仍不能确认 DSM 是主因。

## 4.8 PnP solvability vs geographic correctness

**为什么是问题。** RANSAC/PnP 只问“是否存在一组 correspondences 符合某个 camera model 和 threshold”，并不验证 candidate 的地理 identity。重复结构或系统性错 3D 点也能产生一致解。

**层级与论文。** Geometry solver 与 final decision。AnyVisLoc/OrthoLoC/C2F 受影响；PiLoT 系列用 direct optimizer，Bearing-UAV 用 regression，AirLock+ 用 homography，所以是绕过而不是解决同一校准问题。

**为什么未解决。** Inlier count 忽略 spatial coverage、3D conditioning、residual distribution、map validity 和 candidate correctness。

**AnyVisLoc 证据。** canonical 与 satellite 都 295/295 PnP success；canonical inliers/error 几乎不相关；四个 high-inlier samples 仍 >1 m。[RAW_VERIFIED]

## 4.9 Pipeline error propagation

**为什么是问题。** 错 crop 会导致错 retrieval；错 candidate 导致 matcher 只能寻找伪对应；伪对应经 DSM 变成一致但错误的 3D；PnP success 又可能被当最终 confidence。后级无法访问前级 uncertainty 时，错误只会被硬传递。

**层级与论文。** 全 pipeline。AnyVisLoc 最容易观察；AirLock+ 用 temporal filtering；3D Geometric 用 shared representation/candidate validation；PiLoT 系列把 feature residual 和 pose 联合；Bearing-UAV 直接回归但降低可解释 attribution。

**为什么未解决。** Modular 设计易诊断但 interfaces 硬；unified 模型可联合纠错但内部 failure attribution 更难。需要区分“减少错误传播”和“隐藏错误来源”。

**AnyVisLoc 证据。** canonical/long-tail 相同 query/rank metadata 却出现 run-specific catastrophic failures，说明 downstream instability 可独立产生；但 seed、cache、matches、solver residual 缺失，机制仍 uncertain。[RAW_VERIFIED]

---

# Part 5 — Our previous ideas re-evaluation

## 5.1 状态总表

| Direction | Closest papers | 已被做到的部分 | 我们的 evidence | Novelty risk | Difficulty | Status |
| --- | --- | --- | --- | --- | --- | --- |
| A Coarse-to-Fine Matching | C2F, RoMa, OrthoLoC, PiLoT/v2 | pyramid/refinement/pre-warp/direct coarse-to-fine 已成熟 | oblique/satellite gap；无 scale-level failure trace | High（宽泛 idea） | Medium | **REVISE** |
| B Feature Reuse | DELG, Patch-NetVLAD, R²Former, SelaVPR, 3DG | shared global/local features、reference cache 已存在 | 代码结构支持重复；无 profile/accuracy evidence | High | Medium–High | **NEED MORE EVIDENCE** |
| C Shared/Unified Encoder | R²Former, SelaVPR, 3DG, Bearing-UAV | shared encoder/global-local heads/shared 3D substrate | objective mismatch 仅 interface-level support | High | High | **REVISE** |
| D DINOv2 Multi-scale | RoMa, AirLock+, 3DG, AnyLoc | DINO coarse semantics + pyramids 已广泛使用 | RoMa canonical strong；satellite collapse 非 DINO 因果证据 | High | Medium | **REVISE** |
| E CLIP Semantic Prior | multimodal geo-retrieval, CLIP-VPR family | semantic retrieval/context prior 已非空白 | 当前无 CLIP/semantic failure evidence | Medium–High | Medium | **NEED MORE EVIDENCE** |
| F Geometry-Aware Matching | DKM, MASt3R, OrthoLoC, PiLoT/v2, 3DG | geometry-aware confidence、3D grounding、prewarp/direct optimization | PnP success/inliers 不等于 accuracy，support 最强 | Medium–High | High | **KEEP**（需窄化） |
| G Retrieval + Matching Integration | R²Former, SelaVPR, CAME, 3DG, Bearing-UAV | local reranking/shared features/candidate attention/direct pose 已覆盖 | rank/error weak relation + rank2–5 cohort | High | High | **REVISE** |
| H Cross-view Feature Alignment | RoMa, AirLock+, OrthoLoC, PiLoT/v2, 3DG | dense learned matching、homography、render/BEV canonicalization | satellite/prior degradation提供系统级支持 | High（宽泛） | High | **KEEP**（问题保留、机制重定义） |

## 5.2 A — Coarse-to-Fine Matching

- **Original idea：** coarse DINO/global evidence 找区域，再以高分辨率 local features 精配，减少 dense full-resolution cost。
- **Closest papers：** 2024 C2F、RoMa、OrthoLoC AdHoP、PiLoT/PiLoT v2。
- **做到什么程度：** multi-scale pyramid、coarse-to-fine refinement、先 warp 再 match、coarse-to-fine pose optimization 都已存在。
- **不够 novel：** “加一个 coarse stage”“DINO coarse + CNN fine”“多尺度匹配”本身。
- **仍可能空间：** 由 downstream geographic/DSM uncertainty 决定在哪里 refine；candidate/region-specific adaptive resolution；以 final localization utility 而非 correspondence loss 决策是否进入 fine stage。
- **Evidence：** satellite/oblique failures 支持问题重要，但没有证明 scale level selection 是因果。
- **结论：REVISE。** 从 architecture slogan 改成可证伪的 adaptive decision hypothesis。

## 5.3 B — Feature Reuse

- **Original idea：** CAMP/DINO/RoMa 避免重复 encode query/reference，复用 tokens 给 retrieval 和 matching。
- **Closest papers：** DELG、Patch-NetVLAD、R²Former、SelaVPR、3D Geometric；Bearing-UAV 还可缓存 satellite GLUF。
- **做到什么程度：** shared global/local backbone、local feature reranking、shared 3D representation 都已有。
- **不够 novel：** 单纯 cache、共享 encoder、减少 FLOPs。
- **仍可能空间：** feature reuse 作为 enabling constraint，与 stage-specific adapters/uncertainty 保持 retrieval invariance 和 matching equivariance；研究 accuracy–latency–memory Pareto，而不是只报 speed。
- **Evidence：** 当前仅从代码结构推断重复计算；没有 profiler，也没有 shared-feature ablation。
- **结论：NEED MORE EVIDENCE。** 先 profile，再决定是 engineering optimization 还是 research question。

## 5.4 C — Shared / Unified Encoder

- **Original idea：** 一个 encoder 同时产生 retrieval global descriptor 与 matching local tokens。
- **Closest papers：** R²Former、SelaVPR、DELG、3D Geometric、Bearing-UAV。
- **做到什么程度：** global/local heads 和 shared backbone 已成熟；3D Geometric 更进一步共享 geometry substrate。
- **不够 novel：** “single ViT + two heads”“reuse intermediate tokens”。
- **仍可能空间：** 显式区分 invariant retrieval subspace 与 equivariant matching subspace；用 task conflict/gradient conflict 作为研究对象；geometry-conditioned adapters 而不是完全硬共享。
- **Evidence：** AnyVisLoc rank/error 弱关联与 separate models 支持研究 interface，但没有证明 shared encoder 会改善。
- **结论：REVISE。** 重点从 sharing 变为如何管理 two-objective conflict。

## 5.5 D — DINOv2 Multi-scale Representation

- **Original idea：** 抽取 DINOv2 多层 tokens，融合 semantic coarse layer 与 spatial fine layer 来跨视角匹配。
- **Closest papers：** RoMa、AirLock+、3D Geometric、AnyLoc；一般 multi-scale matchers 也很多。
- **做到什么程度：** DINOv2 coarse semantics + fine pyramid 在 RoMa/AirLock+ 已接近；3D Geometric 用 DINO tokens 服务 retrieval/3D。
- **不够 novel：** 仅 concatenate 多层 DINO、FPN、feature pyramid 或把 RoMa backbone 替换为 DINO。
- **仍可能空间：** 按 viewpoint/scale/DSM reliability 动态选择 layers；把 DINO token 的 semantic invariance 与 metric correspondence uncertainty 校准；分析哪些层对 façade/roof 与 satellite temporal shift 有效。
- **Evidence：** RoMa canonical baseline 强，说明 DINO/RoMa 是必须超过的 baseline；satellite collapse 说明它尚未解决系统问题，但不能说明 backbone 是原因。
- **结论：REVISE。** 必须是具体 selection/calibration mechanism + controlled layer ablation。

## 5.6 E — CLIP Semantic Prior

- **Original idea：** 用 CLIP semantics 识别 road/building/water/vegetation，辅助 retrieval、mask distractors 或引导 matching。
- **Closest papers：** multimodal geo-localization、CLIP-based VPR、semantic-guided retrieval；3D Geometric related work 已讨论 text/multimodal geo reasoning。
- **做到什么程度：** semantic/global prior 和 text-augmented retrieval 已存在；“把 CLIP 加到 retrieval”风险高。
- **不够 novel：** zero-shot CLIP score 融合、prompt ensemble、通用 semantic mask。
- **仍可能空间：** 明确针对 localization usability 的 negative evidence，例如水体/动态区域/DSM-invalid surface gating；语义只提供 uncertainty prior，不替代 metric correspondence。
- **Evidence：** 当前没有 semantic category 与 failure 的 per-sample labels，也没有 CLIP baseline。
- **结论：NEED MORE EVIDENCE。** 先建立 failure taxonomy/semantic correlation，避免 solution-first。

## 5.7 F — Geometry-Aware Matching

- **Original idea：** matcher 不只预测 visual confidence，还考虑 correspondence coverage、DSM validity、3D distribution 与 PnP conditioning。
- **Closest papers：** DKM、MASt3R、OrthoLoC、PiLoT/PiLoT v2、3D Geometric。
- **做到什么程度：** geometry-aware sampling/confidence、3D-grounded matching、homography preconditioning 和 direct pose optimization 已存在。
- **不够 novel：** 加 epipolar/homography consistency、按 inlier count rerank、泛称 geometry loss。
- **仍可能空间：** georeferenced 2.5D-specific validity；对 DSM no-data/roof-ground ambiguity/3D degeneracy 建模；学习 calibrated `P(localization success | matches, map, solver)`，并保持 matcher-agnostic diagnostic value。
- **Evidence：** all-PnP-success wrong poses、inlier/error 无关、high-inlier >1m cases，是八个方向中最直接的 raw support。
- **结论：KEEP（需窄化）。** 保留 research question，不预设网络形式。

## 5.8 G — Retrieval + Matching Integration

- **Original idea：** Top-K retrieval 后用 local evidence rerank，甚至 joint encode/joint train，使候选排序更贴近最终 localization。
- **Closest papers：** R²Former、SelaVPR、CAME、3D Geometric、Bearing-UAV。
- **做到什么程度：** local reranking、candidate-context modeling、candidate-isolated attention、direct pose regression 都已存在。
- **不够 novel：** global+local score linear fusion、Top-K reranking、共享 encoder 后直接拼接。
- **仍可能空间：** final metric localization supervision/calibration；candidate-specific map/DSM/solver evidence；允许 overlapping non-GT tiles 成为 positives；明确 compare Top1-only vs TopK causal rescue。
- **Evidence：** R@1→R@5 gap、79 个 rank2–5 cohort、rank/error weak relation；但缺 candidate outcomes，因此最关键 causal link 未闭合。
- **结论：REVISE。** 从 generic integration 改为 localization-utility-aware candidate decision。

## 5.9 H — Cross-view Feature Alignment

- **Original idea：** 显式对齐 UAV oblique features 与 aerial/satellite orthographic features，再进入 matcher/pose。
- **Closest papers：** RoMa、AirLock+、OrthoLoC、PiLoT/PiLoT v2、3D Geometric、Scale-Aware。
- **做到什么程度：** learned invariant feature、homography warp、view rendering、BEV、physical scale alignment 几条路线均已存在。
- **不够 novel：** generic domain adaptation、单个 homography、普通 cross-attention、简单 BEV transform。
- **仍可能空间：** 研究 partial 3D/non-planar alignment、uncertainty-aware canonicalization、只在 failure-prone regions 使用 alignment、区分 aerial 与 historical satellite 的不同 gap。
- **Evidence：** reference-mode collapse 与 yaw-alignment dependency 强烈说明 alignment problem 重要；尚无 stage-isolated evidence 指定应该使用哪种 mechanism。
- **结论：KEEP（问题保留、机制重定义）。** 先做 satellite GT-reference/oracle matching controls。

## 5.10 哪些方向“基本撞车”，哪些只是太宽泛

基本撞车的是具体宽泛实现，不是整个科学问题：

- `DINOv2 + fine pyramid dense matching`：RoMa/AirLock+ 已覆盖；
- `shared encoder + global/local heads`：DELG/R²Former/SelaVPR 等已覆盖；
- `generic Top-K local reranking`：R²Former/SelaVPR/CAME 已覆盖；
- `plain coarse-to-fine matching`：C2F/RoMa/OrthoLoC/PiLoT 系列已覆盖；
- `TDOM/DSM direct registration`：PiLoT v2 已覆盖；
- `DINO/VGGT shared 3D/BEV retrieval and pose`：3D Geometric 已覆盖；
- `direct position+heading regression from neighboring tiles`：Bearing-UAV 已覆盖。

仍然开放的是更具体的机制与证据问题：retrieval candidate 的 localization utility；georeferenced DSM/PnP-aware confidence；satellite-specific error decomposition；prior uncertainty 如何进入前端；以及如何在不牺牲 modular diagnostics 的情况下减少 objective mismatch。

---

# Part 6 — What I should understand before designing a new method

## 6.1 先能回答这六个问题

1. **任务边界是什么？** global lost-in-space、known local crop、还是 sequential tracking？三者不能用同一 headline accuracy 直接比较。
2. **输出是什么？** tile ID、2D position、3-DoF、6-DoF、还是 target coordinates？“更准”必须指同一 output/metric。
3. **地图假设是什么？** satellite RGB、DOP+DSM、TDOM+DSM、textured mesh、还是 online multi-view reconstruction？地图成本是方法的一部分。
4. **跨视角 gap 是靠 feature invariance 还是 geometric canonicalization 解决？** 前者可能失去 pixel precision，后者依赖 geometry/prior。
5. **confidence 对谁校准？** retrieval correctness、match correctness、solver success 与 metric pose success 是四种标签。
6. **统一方法付出的代价是什么？** compute、training data、prior、global recovery、diagnostic visibility 或 portability。

## 6.2 设计 hypothesis 前需要的最小证据

```text
候选级：candidate ID / similarity / overlap
      + matches / confidence / coverage
      + DSM validity / 3D spread
      + PnP residual / conditioning / pose
      + final metric error
```

没有这条链，就只能证明 query-level association，不能说明“哪一个 candidate 被哪个 downstream signal rescue/reject”。

对于 satellite failure，还至少需要两项 controlled evidence：

1. satellite GT-reference → matcher → geometry，隔离 global retrieval；
2. aerial/satellite paired reference 的 map resolution、DSM validity、temporal/georegistration diagnostics。

对于 feature reuse/shared encoder，先做 profiler 与 frozen-feature probe；对于 CLIP semantic prior，先建立 failure semantic labels；对于 scale idea，先做 scale-only controlled perturbation。这样才能保持 research question first。

## 6.3 当前最值得继续精读的三篇

1. **OrthoLoC**：最适合学习如何隔离 retrieval、matching、DSM 与 pose，并建立我们自己的 controlled diagnostic。
2. **3D Geometric Perception**：最直接挑战 modular pipeline，必须弄清 shared geometry、overlap-aware retrieval 与 candidate validation 到底解决了多少 objective mismatch。
3. **PiLoT v2**：最接近“2.5D map + geometry-aware feature + pose optimizer”的强竞争方向，能帮助区分我们的前端问题与 local direct-registration setting。

AirLock+ 应作为 DINOv2/RoMa satellite registration 的 novelty blocker 精读；Bearing-UAV 应作为 direct regression paradigm 对照精读，但优先级略低于上述三篇对当前 AnyVisLoc evidence 的直接解释能力。

## 6.4 当前最值得继续研究的三个问题

### Q1. Candidate 的 visual relevance 怎样转化为 localization utility？

**Evidence：** R@1/R@5 gap、rank-error weak association、rank2–5 cohort 可定位。[RAW_VERIFIED]

**仍缺：** per-candidate score、overlap、selected candidate、matches 与 pose。完成 candidate-level audit 后，才可判断需要 reranking、calibration 还是新的 retrieval supervision。

### Q2. 为什么 PnP/inlier evidence 无法可靠表示 geographic correctness？

**Evidence：** canonical/satellite 全部 PnP success；inlier count 几乎不关联 error；存在 high-inlier high-error cases。[RAW_VERIFIED]

**仍缺：** spatial match coverage、3D point conditioning、DSM validity、reprojection distribution、wrong-candidate identity。这个问题最有直接 experiment support。

### Q3. Satellite 与 pose-prior failure 首先发生在哪个前端环节？

**Evidence：** satellite 与 `p` 的 median/mean/SR 均显著退化。[RAW_VERIFIED]

**仍缺：** satellite retrieval-only、satellite GT-reference matching/localization、paired preprocessing/match diagnostics 和 yaw/scale controlled perturbation。只有先定位 stage，才能选择 feature alignment、scale correction、semantic prior 或 geometry model。

---

## Primary sources used for this tutorial

- [AnyVisLoc / UAV-AVL](https://arxiv.org/abs/2503.10692)
- [PiLoT v2](https://arxiv.org/html/2606.31098)
- [Unifying UAV Cross-View Geo-Localization via 3D Geometric Perception](https://arxiv.org/pdf/2604.01747)
- [PiLoT](https://arxiv.org/html/2603.20778)
- [AirLock+](https://openaccess.thecvf.com/content/WACV2026/html/Deng_AirLock_Scaling_UAV-to-Satellite_Image_Registration_for_Target_Geolocalization_and_Geospatial_WACV_2026_paper.html)
- [Scale-Aware U2S-CVGL](https://arxiv.org/html/2603.07535)
- [Coarse-to-Fine GNSS-Denied UAV Localization](https://doi.org/10.1016/j.isprsjprs.2024.05.006)
- [OrthoLoC](https://arxiv.org/html/2509.18350)
- [Bearing-UAV](https://arxiv.org/html/2603.22153)
