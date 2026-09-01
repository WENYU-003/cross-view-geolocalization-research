# UAV-AVL / AnyVisLoc Research Line

本目录保存 UAV-AVL / AnyVisLoc 专题研究的跨论文综合、Scene_16 raw-evidence audit、研究假设筛选和最终决策。单篇论文笔记仍放在 [`papers/`](../../papers/)，baseline reproduction 记录和分析脚本放在 [`reproductions/anyvisloc/`](../../reproductions/anyvisloc/)。

## Checkpoint status

**Status: frozen after completed reproduction and failure attribution.**

截至本 checkpoint，当前能够防守的结论是：

- AnyVisLoc / UAV-AVL reproduction completed；
- aerial vs satellite performance gap confirmed；
- retrieval is not sufficient to explain the gap；
- cross-reference correspondence degradation exists；
- Agreement、match count 和 simple coverage 都不是充分的 localization-utility indicator；
- solver provenance 表明 high-Agreement catastrophic cases 不能被干净解释为 frontend solver-subset degradation；
- 当前 satellite correspondence-consistency proposed-method direction 为 **NO-GO / frozen**；
- UAV-AVL 保留为未来方法的 external validation / secondary benchmark，不作为当前主线继续深挖。

上述“confirmed”仅限各文件明确记录的 evidence boundary。Raw bundles 保存在 Git 外；仓库只跟踪轻量 derived tables、分析代码、研究笔记和决策。

## Research progression

| Stage | Deliverable | Status |
| --- | --- | --- |
| Anchor onboarding | Pipeline、模块、baseline 与证据协议 | Completed |
| Related-work collection | 25-paper shortlist 与 structured extraction | Completed |
| Cross-paper comparison | Taxonomy、comparison matrix、common limitations | Completed |
| Failure evidence mapping | Scene_16 query-level raw audit | Completed |
| Teaching and idea re-evaluation | Tier-1 tutorial、idea collision/risk analysis | Completed |
| Satellite GT-reference diagnostic | Aerial/satellite 2D correspondence audit | Completed |
| Spatial-support mechanism isolation | 295-query diagnostic 与 29-query counterexamples | Completed |
| Solver provenance | Raw → valid 2D-3D → PnP inlier → pose audit | Completed |
| Research decision | Satellite correspondence-consistency method direction | **NO-GO / frozen** |

## File index

- [`00_research_scope.md`](00_research_scope.md): scope、research questions、evidence protocol 和 stop conditions。
- [`01_anchor_paper.md`](01_anchor_paper.md): AnyVisLoc pipeline 与 anchor-paper technical decomposition。
- [`02_related_papers_index.md`](02_related_papers_index.md): 25-paper shortlist、tiering 与 structured extraction。
- [`03_method_taxonomy.md`](03_method_taxonomy.md): mechanism-oriented literature taxonomy。
- [`04_comparison_matrix.md`](04_comparison_matrix.md) / [`04_comparison_matrix.csv`](04_comparison_matrix.csv): cross-paper comparison。
- [`05_common_limitations.md`](05_common_limitations.md): common limitation teaching and evidence boundaries。
- [`06_failure_to_limitation.md`](06_failure_to_limitation.md): literature limitation → Scene_16 raw evidence mapping。
- [`06_anyvisloc_scene16_query_audit.csv`](06_anyvisloc_scene16_query_audit.csv): lightweight 295-query derived audit table；不含 raw images、matches 或 model outputs。
- [`07_related_work_tutorial.md`](07_related_work_tutorial.md): Tier-1 technical tutorial 和 previous-ideas re-evaluation。
- [`08_scene16_24query_visual_audit.md`](08_scene16_24query_visual_audit.md): 24-query RGB/geometric audit protocol and findings。
- [`09_scene16_spatial_support_diagnostic.md`](09_scene16_spatial_support_diagnostic.md): 295-query spatial-support diagnostic。
- [`10_scene16_counterexample_mechanism_isolation.md`](10_scene16_counterexample_mechanism_isolation.md): 29-query counterexample mechanism isolation。
- [`11_scene16_solver_provenance_audit.md`](11_scene16_solver_provenance_audit.md): solver correspondence provenance and NO-GO evidence。
- [`12_uavavl_research_checkpoint.md`](12_uavavl_research_checkpoint.md): final research-line checkpoint and handoff decision。

## Evidence labels

- **[Paper]**: primary paper support。
- **[Official code]**: official repository/config/implementation support。
- **[RAW_VERIFIED]**: recomputed from recovered external raw artifacts。
- **[Derived]**: deterministic lightweight table/statistic derived from recorded evidence。
- **[Inference]**: evidence-bounded interpretation。
- **[Hypothesis]**: falsifiable but not verified。
- **[Uncertainty]**: missing, conflicting, or version-dependent information。

Do not promote an inference or hypothesis to a paper finding. Do not describe an external raw bundle as tracked repository data.

## Anchor sources

- Primary paper: [arXiv:2503.10692](https://arxiv.org/abs/2503.10692)
- Official implementation: [UAV-AVL/Benchmark](https://github.com/UAV-AVL/Benchmark)
- Reading note: [`papers/anyvisloc.md`](../../papers/anyvisloc.md)
- Reproduction workspace: [`reproductions/anyvisloc/`](../../reproductions/anyvisloc/)
