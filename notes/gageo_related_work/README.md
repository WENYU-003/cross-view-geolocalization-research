# GAGeo Research Line

本目录保存 GAGeo / CMA-Loc 从论文理解、复现核验到 failure-mechanism research 的证据链。单篇论文阅读稿位于 [`papers/gageo.md`](../../papers/gageo.md)，原始复现结果位于 [`reproductions/gageo/`](../../reproductions/gageo/)；本目录不复制 raw results，而是记录它们支持什么科研结论、还缺少什么证据。

## Current checkpoint

**Phase 1（paper understanding）：COMPLETE。**

**Phase 2（paper ↔ code ↔ reproduction alignment）：COMPLETE，带明确 provenance 限制。**

**Phase 3（systematic failure analysis）：COMPLETE at observable-mechanism level。**

**Phase 4（limitation）：COMPLETE。**

**Phase 5（research hypothesis / method design）：COMPLETE as a selected, falsifiable working method；implementation remains gated by the first feature diagnostic and a full novelty review。**

当前可防守的主结论是：

- 保存的六个 CMA-Loc JSON 与论文 Tables 2–3 在论文报告精度上对齐；
- `test` 的 4,220 个样本对应论文数值中的 Seen，`unseen_test` 的 4,197 个样本对应 Unseen；论文正文给出的两个样本数顺序与发布文件相反，不能在没有作者确认时称为已证实 typo；
- point / bbox / mask 是 query prompt modality，不是 detection / segmentation task；每次 evaluation 都同时输出 bbox、model mask 和 camera geometry；
- `--skip_sam` 只关闭可选的外部 SAM 后处理，不关闭 GAGeo 内部的 SAM2 prompt encoder，也不关闭原生 mask head；
- `unseen_test + point` 的 196/4,197 severe failures 可从保存 CSV 确定性重算；Ground 与 Drone 的差距是可靠统计现象，但尚不是因果解释；
- Table 4 数值约对齐，但其运行日志、不可变 config snapshot 和适配脚本没有保存在本 research repository 中；Table 5 缺少公开 triplet pairing；Table 6/结构 ablation 需要重训，当前不是进入 limitation research 的必要条件。

## File index

- [`00_research_scope.md`](00_research_scope.md)：研究范围、证据协议与阶段路线。
- [`01_anchor_paper.md`](01_anchor_paper.md)：anchor paper 的精炼研究摘要。
- [`02_task_and_problem_definition.md`](02_task_and_problem_definition.md)：任务、视角、prompt 与输出定义。
- [`03_architecture_walkthrough.md`](03_architecture_walkthrough.md)：基于发布代码的数据流与 tensor 角色。
- [`04_prompt_and_pi3_mechanism.md`](04_prompt_and_pi3_mechanism.md)：prompt 注入、attention 隔离与 π³ 机制；区分 FACT 和 INTERPRETATION。
- [`05_paper_code_mapping.md`](05_paper_code_mapping.md)：paper component → file → class/function → data flow。
- [`06_reproduction_matrix.md`](06_reproduction_matrix.md) / [`06_reproduction_matrix.csv`](06_reproduction_matrix.csv)：保存结果与论文表格的逐 setting 对齐。
- [`07_reproduction_checkpoint.md`](07_reproduction_checkpoint.md)：DONE / PARTIAL / BLOCKED / LOW PRIORITY 决策。
- [`08_metric_and_split_audit.md`](08_metric_and_split_audit.md)：split、prompt、view、SAM 与指标的代码定义。
- [`09_failure_analysis_checkpoint.md`](09_failure_analysis_checkpoint.md)：只保存已核验 failure evidence 和 provenance 边界。
- [`10_failure_mechanism_diagnosis.md`](10_failure_mechanism_diagnosis.md)：控制 size/shape 后的 catastrophic-tail 与 shared-head mechanism 诊断。
- [`11_limitation.md`](11_limitation.md)：从 failure mechanism 推导的可干预 limitation。
- [`12_research_hypotheses.md`](12_research_hypotheses.md)：四个 intervention 的证据与风险比较。
- [`13_idea_decision.md`](13_idea_decision.md)：主 idea 选择与 closest-method collision check。
- [`14_proposed_method.md`](14_proposed_method.md)：PR-MHA 的数据流、模块和 falsifiable prediction。
- [`15_implementation_and_experiment_plan.md`](15_implementation_and_experiment_plan.md)：代码插入点、训练与 minimum viable experiment。

## Evidence labels

- **[Paper]**：论文原文直接支持。
- **[Official code]**：发布代码直接支持；本次核对基于 GAGeo repository `f6585cb`。
- **[RESULT_VERIFIED]**：从 Git 中保存的 JSON/CSV 重新解析得到。
- **[Git history]**：由本 research repository 的历史 commit 支持。
- **[Interpretation]**：与证据一致但不是直接测量。
- **[Hypothesis]**：可证伪、尚未验证。
- **[Uncertainty]**：缺失或冲突的 provenance / annotation / protocol。

不要把 subgroup correlation 写成 failure cause，也不要把保存的 summary JSON 描述成包含完整 per-sample provenance。
