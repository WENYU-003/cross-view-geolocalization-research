# 00 — GAGeo Research Scope

## Objective

GAGeo research line 的目标不是获得“完整复现率”，而是形成一条能够被实验反驳或支持的研究链：

```text
paper understanding
→ reproduction verification
→ reproducible failure evidence
→ mechanism diagnosis
→ defensible limitation
→ falsifiable hypothesis
→ minimal method experiment
```

当前关注前端视觉表示、prompt-conditioned cross-view alignment、small-target signal 与 geometry-aware interaction。只有当证据显示 camera/solver 部分是主动 bottleneck 时，才把主要创新移到后处理或几何求解器。

## In scope

- CMA-Loc Ground→Satellite 与 Drone→Satellite object localization；
- point / bbox / mask prompt 如何改变 query target representation；
- DINOv2 patch feature、SAM2 prompt embedding 与 π³ local/global interaction；
- bbox、mask、camera position 与 rotation 的共享表示和任务接口；
- Seen/Unseen、view、size、shape 的 per-sample failure distribution；
- target signal 在 DINOv2 和 π³ 中间层的保留、传播与混淆；
- 用最小 diagnostic 区分 representation failure、cross-view interaction failure 与 head-selection failure。

## Out of scope at this checkpoint

- 继续 UAV-AVL / AnyVisLoc proposed-method exploration；
- 为追求表格完整而重训 Table 6 或 Figure 4 全套 ablation；
- 在缺少公开 pairing 时自定义协议替代 Table 5；
- 在 failure cause 未隔离前实现大规模 architecture change；
- 把 `Ground + Small` 的相关性直接写成“尺度导致失败”。

## Evidence protocol

每个 research claim 至少记录：

```text
Claim
→ Evidence level
→ Source artifact / code revision
→ Population and sample count
→ Alternative explanation
→ Missing measurement
→ Decision enabled
```

本阶段使用以下边界：

1. 论文任务与报告数字以本地论文稿和原论文表格为准。
2. 实现行为以发布 GAGeo code `f6585cb` 的实际 control/data flow 为准，不依据变量名猜测。
3. 我们的数值结论必须能从 tracked JSON/CSV 重算。
4. README 中的命令、环境和 checkpoint 路径是 provenance 记录，但不等价于保存的运行日志、checkpoint hash 或 immutable config snapshot。
5. qualitative labels 在没有明确 annotation rubric 和完整样本集前仅作为初步观察。

## Phase boundary

Phase 2 只回答“现有 paper、code、result artifacts 能支持什么”。它不启动新的 GPU evaluation，也不选择最终 proposed method。进入 Phase 3 后只先执行一个最高信息增益 diagnostic，结果再决定后续假设。
