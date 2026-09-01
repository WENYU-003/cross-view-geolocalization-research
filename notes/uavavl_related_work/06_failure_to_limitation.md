# 06 — AnyVisLoc Failure Evidence to Literature Limitation Mapping

## 1. Phase 4 objective and evidence boundary

This file connects the Phase 3 literature limitations to the AnyVisLoc Scene_16 reproduction record:

```text
observed aggregate evidence
→ affected pipeline stage
→ possible bottleneck
→ literature limitation
→ remaining uncertainty
→ required diagnostic
```

It does **not** select a proposed method. No experiment was rerun for Phase 4.

Evidence labels used here:

- **[RAW_VERIFIED]**: recomputed from the recovered raw result bundle and checked against query-level artifacts;
- **[Local result]**: backed by a raw result/log/per-sample artifact stored in this repository;
- **[Research summary]**: recorded in a repository note, but the raw result is absent;
- **[Paper]**: supported by a primary paper as recorded in Phase 1–3;
- **[Inference]**: interpretation consistent with available evidence but not directly measured;
- **[Hypothesis]**: falsifiable causal explanation requiring a diagnostic;
- **[Missing]**: required evidence is absent from the repository.

Important boundary after Phase 4.6: the raw bundle `anyvisloc_scene16_evidence_20260830.tar.gz` was recovered outside Git and verified with SHA-256 `d0edc35ed7cdd8f6005e03d916114d3b269a47093f7c8b2a5727ede1781c8593`. It contains 1,007 JSON/CSV artifacts, including 295-query Scene_16 results. The lightweight derived table [`06_anyvisloc_scene16_query_audit.csv`](06_anyvisloc_scene16_query_audit.csv) is stored in the repository; the raw bundle remains external and must not be treated as a tracked dataset.

Two additional GT-reference logging bundles were recovered outside Git for the DSM-free cross-reference diagnostic:

- satellite GT-reference `20260831-0905_1scenes`, SHA-256 `63954d09d9c5d3051df8aa4f15bc33aa00806dc1dcecf731ec84ff46500c16fe`;
- aerial GT-reference replay `20260831-1017_1scenes`, SHA-256 `9925de87703aa20c52d28ce476757f4dc5bd5b456c486a4372b3f9b76882f1c7`.

Each contains 295 per-query JSON, NPZ, and PKL artifacts. Exact commands, config snapshots, code revision, candidate lists/scores, RoMa certainty, logs, and image-level failure visualizations remain unavailable.

## 2. Repository artifact audit

### Present

- `reproductions/anyvisloc/anyvisloc-reproduction-record.md` — tracked narrative record containing settings and aggregate metrics;
- `papers/anyvisloc.md` — tracked paper-reading note;
- `notes/uavavl_related_work/01_anchor_paper.md` — Phase 1 anchor decomposition and evidence boundary;
- `notes/uavavl_related_work/04_comparison_matrix.*` and `05_common_limitations.md` — Phase 3 literature comparison.
- recovered external raw bundle with Scene_16 summary, retrieval-only, GT-reference matching/localization, full aerial, satellite, pose-prior, and matcher-comparison JSON/CSV files;
- `notes/uavavl_related_work/06_anyvisloc_scene16_query_audit.csv` — 295-row canonical query-level audit table derived without modifying raw artifacts.
- external aerial/satellite GT-reference logging bundles with 295 saved correspondence arrays each;
- `reproductions/anyvisloc/analyze_cross_reference_2d.py` — DSM-free aerial/satellite correspondence-agreement audit.

### Absent

- tracked raw `Result/AnyVisLoc/<run>/.../Scene_16/` directory inside this repository;
- ranked candidate identities and raw similarity scores;
- per-candidate matching outputs;
- exact command for each reported run;
- preserved YAML/config snapshot and code revision for each run;
- logs, runtime profiles, environment export, or checkpoint hashes;
- Scene_16 failure-case images and candidate-level visualizations.
- RoMa confidence/certainty values and manual 2D correspondence ground truth.

Therefore, the five principal Scene_16 numeric checkpoints are now **RAW_VERIFIED from an external immutable bundle**, and the canonical query-level table is independently re-auditable in this repository. This does not upgrade missing command/config/code provenance or candidate-level attribution.

## 3. Checkpoint verification table

| Checkpoint | Recorded setting and value | Repository source | Verification status | Raw evidence status | What can be claimed now |
| --- | --- | --- | --- | --- | --- |
| CAMP retrieval-only | Scene_16, 295 queries, aerial, `yp`; R@1 68.47%, R@3 92.20%, R@5 95.25%; PDM@1/3/5 0.9624/0.9446/0.9166 | raw run `20260820-1835_1scenes`; reproduction record §6 | **RAW_VERIFIED** | Per-query ranks/PDM present; candidate IDs/scores and command/config missing | Exact aggregate retrieval metrics and 295 query IDs are verified |
| GT reference → RoMa → P3P | mean 0.4102 m; median 0.3190 m; SR@1m 94.92%; SR@3/5m 100% | raw run `20260820-1945_1scenes`; reproduction record §7 | **RAW_VERIFIED** | Per-query error, inliers, pose and PnP status present; exact command/config missing | Oracle-reference matching+geometry is verified as strong on Scene_16 |
| Full aerial pipeline | CAMP→RoMa→Top-N→P3P, aerial, `yp`; 295/295 attempts; mean 0.4738 m; median 0.3146 m; SR@1m 89.83%; SR@3m 99.66% | raw run `20260820-2000_1scenes`; query audit CSV; reproduction record §8 | **RAW_VERIFIED** | Query ranks/PDM/inliers/status/error present; candidate selection and exact command/config missing | Canonical query-level baseline and failure IDs are verified |
| Satellite reference | CAMP→RoMa, satellite, `yp`; 295 PnP successes; mean 94.6830 m; median 7.4245 m; SR@1/3/5m 5.42/20.68/36.95% | raw run `20260821-1517_1scenes`; reproduction record §11 | **RAW_VERIFIED** | Per-query final records and a later satellite GT-reference control are present; satellite retrieval-only and RoMa certainty remain missing | System-level satellite collapse and wrong-but-solvable poses are verified; retrieval is not the only cause |
| Satellite GT reference → RoMa | `20260831-0905`, 295 queries; mean 16.5790 m; median 6.2004 m; SR@1/3/5m 5.08/23.39/41.36%; mean/median inliers 929.8/961 | external logging bundle; paired DSM-free audit | **RAW_VERIFIED** | Per-query matches, map XY, DSM lift and PnP outputs present; exact command/code revision and RoMa certainty missing | Retrieval is not necessary for satellite degradation; matching/geometry attribution still requires care |
| Aerial GT logging replay → RoMa | `20260831-1017`, 295 queries; mean 0.4267 m; median 0.3453 m; SR@1/3m 93.90/100%; mean/median inliers 2313.7/2406 | external logging bundle; paired DSM-free audit | **RAW_VERIFIED** | Per-query matches and map XY present; exact command/code revision and RoMa certainty missing | Stable replay suitable as aerial pseudo-reference for cross-reference agreement |
| Pose-prior ablation | aerial, CAMP→RoMa, `p`; 295 processed; mean 114.1942 m; median 2.1407 m; SR@1m 42.71%; SR@3m 51.86% | raw run `20260821-1548_1scenes`; reproduction record §12 | **RAW_VERIFIED** | Paired final records present; exact transforms, noise levels, command/config missing | Aggregate dependence on yaw-alignment pathway is verified; stage/cause remains unresolved |
| RoMa vs SP_LG_GIM | SP_LG_GIM run `20260821-1306` has 291 finite/PnP-success rows, mean 3.1323 m, median 1.5000 m, SR@1m 28.81%, SR@3m 82.03% | raw run `20260821-1306_1scenes`; reproduction record §9 | **RAW_VERIFIED for recorded run outcome** | Exact matched preprocessing/config and correspondence diagnostics missing; `20260821-1402` is anomalous | RoMa is stronger on the retained runs, but a causal matcher claim still requires provenance-controlled comparison |
| Top1 vs Top5 behavior | 79 queries have GT rank 2–5; 67/79 localize within 1 m and 79/79 within 3 m in the canonical Top-N run | raw canonical query join; reproduction record §10 | **RAW_VERIFIED association; causal rescue unverified** | **Missing** Top1-only localization, selected candidate, and candidate-specific outcomes | Below-rank-1 cohort success is verified; incremental Top-5 rescue frequency is not |
| Failure cases Type A–D | retrieval, matching, satellite-domain, and prior-dependence taxonomy | reproduction record §14 | **Conceptual note only** | **Missing** case IDs, artifacts, deterministic labels, visual examples | Useful provisional taxonomy, not a per-sample failure dataset |

### Pose-prior terminology correction

The available record supports `yp` versus `p`, not “full yaw/pitch prior” versus “no yaw/pitch prior.” Phase 1 code inspection recorded that `p` retains pitch/altitude-based view-center/scale preparation but omits yaw alignment. Consequently:

- **supported statement:** removing the yaw-alignment pathway strongly degrades aggregate localization [RAW_VERIFIED];
- **unsupported statement:** the experiment removes all pose priors;
- **unsupported causal claim:** degradation is caused specifically by PnP initialization.

## 4. Aggregate and query-level comparisons verified from raw artifacts

Phase 4.6 recomputed the values below from the recovered raw artifacts. Query-level claims use the canonical full run `20260820-2000_1scenes/aerial-CAMP-Roma-yp` unless another run is named explicitly.

### 4.1 Recall@1 versus Recall@5

For 295 queries, the raw rank counts are:

- R@1: 202 queries;
- R@3: 272 queries;
- R@5: 281 queries.

Thus exactly 79 queries satisfy the retrieval evaluation criterion within Top-5 but not at rank 1, and 14 have `GT_rank > 5` under the stored rank field. This supports:

```text
useful retrieval evidence often exists below rank 1
```

It does **not** establish:

- that every lower-ranked candidate is more localizable than Top-1;
- that the candidate selected by downstream geometry is correct;
- how many Top-5 candidates yield a stable PnP solution;
- that CAMP similarity is negatively correlated with final localization.

### 4.2 GT-reference versus full aerial pipeline

| Metric | GT reference | Full aerial | Aggregate difference |
| --- | ---: | ---: | ---: |
| Mean error | ≈0.410 m | ≈0.4738 m | +0.0638 m, about +15.6% |
| Median error | ≈0.319 m | ≈0.3146 m | −0.0044 m; effectively similar at recorded precision |
| SR@1m | ≈94.92% | ≈89.83% | −5.09 percentage points |
| SR@3m | 100% | ≈99.66% | −0.34 percentage points |

Exact threshold counts are 280 versus 265 successes within 1 m and 295 versus 294 within 3 m. The 295 sample IDs are paired: 27 queries change from oracle success to full failure at 1 m, while 12 change from oracle failure to full success. This proves that the two runs differ on a concentrated subset, but it does **not** identify retrieval as the unique cause because matcher stochasticity, preprocessing, candidate overlap, and missing run provenance remain confounded [RAW_VERIFIED/Inference].

### 4.3 Aerial versus satellite reference

| Metric | Aerial `yp` | Satellite `yp` | Aggregate change |
| --- | ---: | ---: | ---: |
| Mean error | ≈0.4738 m | ≈94.683 m | roughly 200× larger |
| Median error | ≈0.3146 m | ≈7.425 m | roughly 23.6× larger |
| SR@1m | ≈89.83% | ≈5.42% | −84.41 percentage points |
| SR@3m | ≈99.66% | ≈20.68% | −78.98 percentage points |

Both runs contain 295 `pnp_success=true` samples. Therefore, solver success is demonstrably not equivalent to accurate geographic localization [RAW_VERIFIED]. The satellite run has 279 errors above 1 m, 234 above 3 m, and a maximum error of 11,168.42 m; the very large mean relative to median is a verified catastrophic-error tail.

This comparison does not isolate domain gap from resolution, temporal change, reference coverage, georegistration, DSM quality, retrieval failure, or wrong-surface correspondence.

### 4.4 `yp` versus `p`

| Metric | Aerial `yp` | Aerial `p` | Aggregate change |
| --- | ---: | ---: | ---: |
| Mean error | ≈0.4738 m | ≈114.194 m | roughly 241× larger |
| Median error | ≈0.3146 m | ≈2.141 m | roughly 6.8× larger |
| SR@1m | ≈89.83% | ≈42.71% | −47.12 percentage points |
| SR@3m | ≈99.66% | ≈51.86% | −47.80 percentage points |

The paired raw evidence strongly supports dependence on the yaw-alignment pathway [RAW_VERIFIED]. It does not show whether the degradation first occurs in retrieval, crop overlap, matcher correlation, candidate selection, or final geometry.

### 4.5 Phase 4.6 query-level rank audit

`PDM` in the audit table is the stored `pdm_at_k` for `retrieval_k=5`, i.e. per-query PDM@5. `PnP_inliers` is the stored `best_inliers` from the canonical full run.

| GT-rank group | N | Mean error (m) | Median error (m) | SR@1m | SR@3m | PnP failure | Inliers mean / median | Inliers min–max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 202 | 0.4524 | 0.3213 | 92.57% | 99.50% | 0/202 | 2499.9 / 2528.5 | 1436–2963 |
| 2–3 | 70 | 0.5188 | 0.3398 | 85.71% | 100% | 0/70 | 2448.4 / 2515.5 | 1588–2860 |
| 4–5 | 9 | 0.5143 | 0.3392 | 77.78% | 100% | 0/9 | 2570.4 / 2607 | 2271–2824 |
| >5 / miss | 14 | 0.5323 | 0.2313 | 78.57% | 100% | 0/14 | 2128.0 / 2107 | 1657–2641 |

The relationship is not monotonic: GT rank versus final error has Pearson `r=0.0507` and Spearman `rho=0.0079` (two-sided permutation `p=0.894`, 100,000 permutations, seed 20260830). The stored per-query PDM@5 versus final error is also weak (Pearson `r=-0.0273`; Spearman `rho=0.1498`). These values support **weak query-level alignment between retrieval diagnostics and final metric error**, not a candidate-level similarity/localizability claim.

The 79-query rank-2-to-5 cohort contains 67 successes within 1 m and all 79 within 3 m. Therefore, the R@1→R@5 cohort is broad and generally localizable in the full Top-N pipeline; it is not merely a few catastrophic cases. However, this is an association, not a measured incremental gain: a Top1-only localization run and per-candidate outputs are absent, so the number of queries causally “rescued” by Top-5 cannot be computed.

### 4.6 Phase 4.6 PnP/inlier audit

All 295 canonical rows have `pnp_success=true`, yet only 265 are within 1 m and 294 are within 3 m. Among solver-success rows, the error rate is therefore 10.17% above 1 m and 0.34% above 3 m. PnP success is a solver-completion flag, not an accuracy guarantee.

PnP inlier count versus final error is nearly uncorrelated in the canonical run: Pearson `r=0.0107`, Spearman `rho=0.0291` (two-sided permutation `p=0.617`, 100,000 permutations, seed 20260830).

| Inlier group | Definition | N | Mean error (m) | Median error (m) | Failure >1m | Failure >3m |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Low | `inliers <= 2392` (bottom-quartile cutoff, ties retained) | 76 | 0.3947 | 0.2983 | 5.26% | 0% |
| Middle | `2392 < inliers < 2649` | 143 | 0.5511 | 0.3604 | 15.38% | 0.70% |
| High | `inliers >= 2649` (top-quartile cutoff, ties retained) | 76 | 0.4076 | 0.2720 | 5.26% | 0% |

Four high-inlier queries still exceed 1 m: `L16_0017` (2.340 m, 2818 inliers), `L16_0039` (2.028 m, 2719), `L16_0177` (1.327 m, 2649), and `L16_0286` (1.135 m, 2928). No high-inlier query exceeds 3 m in the canonical run. Raw count alone is therefore not a calibrated geometry-quality measure; coverage, residuals, 3D distribution, candidate correctness, and map validity remain missing.

### 4.7 Canonical versus `20260821-1402` long tail

| Run | N | Mean (m) | Median (m) | Max (m) | Error >3m | Error >10m | PnP failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `20260820-2000` canonical | 295 | 0.4738 | 0.3146 | 5.3045 | 1 | 0 | 0 |
| `20260821-1402` RoMa | 295 | 6.6812 | 0.3391 | 981.8200 | 5 | 5 | 0 |

The two runs contain the same 295 sample IDs, GT coordinates, retrieval ranks, PDM values, reference mode, retrieval method, matcher label, pose-prior label, and candidate count. Their per-query errors all differ and only one inlier count is identical. The five `20260821-1402` errors above 3 m are:

- `L16_0116`: 981.820 m (`20260820-2000`: 0.052 m);
- `L16_0115`: 598.269 m (`20260820-2000`: 1.557 m);
- `L16_0118`: 205.217 m (`20260820-2000`: 2.519 m);
- `L16_0120`: 31.371 m (`20260820-2000`: 0.139 m);
- `L16_0119`: 31.072 m (`20260820-2000`: 0.231 m).

The canonical run's only error above 3 m is `L16_0155` at 5.304 m, which is not in the anomalous run's >3 m set. The long tail is therefore **run-specific rather than a stable set of intrinsically hard queries** [RAW_VERIFIED]. Because seeds, command, config snapshot, code revision, matcher state, and detailed PnP residuals are absent, the mechanism remains uncertain; the evidence localizes the instability downstream of identical stored retrieval outputs, but cannot distinguish matching, preprocessing/cache state, correspondence lifting, or solver randomness.

### 4.8 Canonical Scene_16 run recommendation

Use `20260820-2000_1scenes/aerial/aerial-CAMP-Roma-yp` as the canonical Scene_16 full-pipeline baseline because it:

- covers all 295 queries with no exception or PnP failures;
- matches the retained reproduction checkpoint exactly;
- has query-level ranks, PDM, inliers, solver status, pose, and final error;
- has a controlled aerial/CAMP/RoMa/`yp`, `retrieval_k=5` identity;
- is consistent with the strong GT-reference control and lacks the unexplained >10 m tail.

The exact command, config snapshot, code revision, model/checkpoint identity, and seed are still missing, so “canonical” means **best current evidence reference**, not fully reproducible experiment provenance. Retain `20260821-1402` as an anomalous stability diagnostic; retain satellite, `p`, SP_LG_GIM, retrieval-only, and GT-reference runs as secondary controlled evidence. Do not delete or average these runs together.

### 4.9 DSM-free aerial/satellite 2D correspondence audit

The paired runs `20260831-1017` (aerial) and `20260831-0905` (satellite) contain the same 295 Scene_16 query IDs, RoMa matcher label, `yp` pose-prior label, 3,000 requested matches, resize ratio, and UAV input/matching dimensions. The saved result schema does not record the PnP method, so that field remains command-level rather than artifact-level evidence.

The reproducible diagnostic in `reproductions/anyvisloc/analyze_cross_reference_2d.py` deliberately does not read `dsm_z` or `inlier_indices`. For each query it:

1. pairs aerial and satellite correspondences by mutual-nearest UAV pixels within 5 original-image pixels;
2. compares the reference endpoints after their existing 2D geotransforms place them in the common Scene_16 metric XY frame;
3. measures raw XY disagreement and agreement within 1/3/5/10 m;
4. estimates the per-query robust median XY shift and reports residual disagreement after removing that coherent shift;
5. uses final satellite error only for post-hoc grouping and correlation, not to define 2D correctness.

The aerial run is a high-accuracy **pseudo-reference**, not manually annotated correspondence ground truth. Nevertheless, the audit supplies a DSM-free front-end diagnostic that was previously missing.

| Satellite outcome group | N | Mutual pairs/query (median) | XY disagreement median (m) | Agreement@3m (mean) | Agreement@5m (mean) | Robust shift median (m) | Shift-corrected residual median (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `error <= 3m` | 69 | 848 | 2.685 | 49.73% | 55.36% | 1.136 | 2.468 |
| `3m < error <= 20m` | 181 | 820 | 7.700 | 39.62% | 43.83% | 4.996 | 2.689 |
| `error > 20m` | 45 | 779 | 8.468 | 24.31% | 29.33% | 7.619 | 5.290 |

Across all 295 queries, median XY disagreement is 6.853 m and mean Agreement@5m is 44.32%. Agreement@5m versus final satellite error has Spearman `rho=-0.4997`; Agreement@3m has `rho=-0.4866`; the number of mutual query pairs has `rho=-0.3615`. The robust coherent-shift magnitude has `rho=0.4472` with final error. These are descriptive paired associations, not causal estimates or calibrated significance tests.

This evidence supports the following narrower statement [RAW_VERIFIED]:

```text
With retrieval removed, satellite correspondences show substantially less
agreement with the high-accuracy aerial pseudo-reference, and lower 2D
agreement is associated with worse satellite localization.
```

It does not prove that learned feature representation is the only cause. Raw XY disagreement also contains aerial/satellite georegistration differences, temporal map change, visibility differences, and any coherent wrong-match offset. Removing a per-query robust translation reduces some disagreement, but the catastrophic group retains a larger residual than the success group. The current evidence therefore supports a front-end correspondence/alignment bottleneck while preserving map-registration uncertainty.

The next minimal validation is not a new PnP/DSM method. It is a 24-query, error-quantile-stratified image audit (8 success, 8 middle, 8 catastrophic) using the script-generated shortlist, followed if necessary by a small set of manually labeled cross-view landmarks. This will distinguish appearance/scale/semantic ambiguity and coherent wrong matches from global map offset without making 3D processing the contribution.

## 5. Failure-to-limitation evidence table

| Evidence | Stage | Literature limitation | Support | Confidence | Missing evidence | Research value |
| --- | --- | --- | --- | --- | --- | --- |
| R@1 68.47% versus R@5 95.25%; rank/error Spearman `rho=0.0079` | Retrieval / candidate interface | L2 retrieval similarity ≠ localizability; L4 hard retrieval–matching interface | Rank gap and weak query-level rank/error relation [RAW_VERIFIED] | **High** for ranking gap; **medium** for query-level mismatch; **low** for candidate-level claim | candidate scores, overlap, selected candidate, per-candidate pose/error | High: tests whether ranking should reflect downstream evidence |
| GT-reference SR@1=94.92% versus full SR@1=89.83%, with 27 oracle-success/full-failure and 12 reverse transitions | Retrieval/candidate selection versus matcher+geometry | L2 candidate localizability; L7 stage error propagation | Paired query transitions show concentrated run differences [RAW_VERIFIED] | **High** for paired difference; **medium-low** for retrieval causality | candidate selection, identical matcher state and exact run provenance | High: can isolate which queries require better candidate selection |
| Aerial GT-reference is sub-meter; satellite GT-reference median=6.200 m, mean=16.579 m; DSM-free Agreement@5m is lower in high-error queries | Feature alignment / matching, with map-registration uncertainty | L1 cross-view representation; L3 useful correspondence; L5 map validity; L9 generalization | Retrieval-independent degradation plus 295-query 2D cross-reference association [RAW_VERIFIED] | **High** for satellite 2D-agreement degradation; **medium** for a front-end bottleneck; **low** for a feature-only cause | RoMa certainty, manual landmarks, image visualizations, map-offset control | Very high: direct front-end failure regime with explicit confounders |
| `yp` substantially outperforms `p` on paired 295-query outputs | Pose-aware preprocessing / retrieval / matching alignment | L6 pose-prior dependency; L1 cross-view alignment | Yaw-alignment pathway matters [RAW_VERIFIED] | **High** for aggregate dependency; **medium-low** for stage mechanism | exact transforms, paired ranks/matches, controlled yaw-noise curve | High: tests visual robustness versus sensor-assisted normalization |
| RoMa retained run is stronger than SP_LG_GIM retained run | Matching / geometry | L3 confidence/count ≠ useful geometry; L5 PnP solvability | Exact run outcomes and per-sample errors/PnP status recovered [RAW_VERIFIED] | **Medium** because exact controlled provenance is incomplete | match coverage, raw correspondences, exact config/seed and stable rerun | Medium-high if correspondence geometry predicts final success |
| 295/295 canonical and satellite samples have `pnp_success=true` despite inaccurate poses | Geometry / final decision | L5 solver success ≠ geographic correctness; L7 insufficient failure calibration | Solver-success rows include 30 canonical errors >1 m and 279 satellite errors >1 m [RAW_VERIFIED] | **High** | residuals, selected candidate, conditioning and calibrated confidence | High: motivates calibrated rejection/localizability diagnostics |
| Rank-2-to-5 cohort has 67/79 SR@1 and 79/79 SR@3 in the Top-N run | Retrieval–matching interface | L2/L4 downstream evidence can exploit non-rank-1 retrieval | Broad localization success below rank 1 [RAW_VERIFIED] | **Medium** for association; **low** for causal rescue count | Top1-only localization and per-candidate selection evidence | High if causal rescue is confirmed |
| Type A–D failure taxonomy exists without instances | Pipeline diagnosis | L7 error propagation/attribution | Failure families are recorded [Research summary] | **Low** as empirical taxonomy | deterministic criteria, labels, counts, examples | Essential prerequisite for failure-driven method selection |

## 6. Five most important failure / limitation mappings

### Mapping 1 — Rank gap → candidate-selection bottleneck

```text
Observed: R@1 << R@5
→ Retrieval stage
→ useful reference criterion often exists below rank 1
→ L2 retrieval similarity/localizability + L4 stage interface
→ CAMP, CAME, R²Former, SelaVPR, 3D Geometric Perception, Bearing-UAV
```

**Confidence:** high for the ranking gap; medium for weak query-level alignment; low for the stronger candidate-level claim that CAMP similarity is miscalibrated to localizability.

**Remaining uncertainty:** Query ID, GT rank, PDM@5, inliers, PnP status, and final error are joined, but candidate identity/score, true overlap, selected candidate, and per-candidate pose are not.

**Required diagnostic:** candidate-level table for every Top-K result, followed by oracle best-candidate and score-versus-success analysis.

### Mapping 2 — Oracle/full gap → concentrated interface failures

```text
Observed: oracle and full medians are nearly equal,
          but full SR@1 is 5.09 pp lower
→ retrieval/candidate selection before matching+geometry
→ likely concentrated failures rather than uniform degradation [Inference]
→ L2 candidate localizability + L7 pipeline attribution
```

**Confidence:** high for paired run differences; medium-low for assigning them uniquely to retrieval.

**Remaining uncertainty:** Samples are paired, but a lower-ranked/overlapping candidate, matcher stochasticity, or changed preprocessing could explain individual differences.

**Required diagnostic:** retain the recovered transition labels, then restore candidate selection, exact config/seed, and identical-state matcher evidence for the 12 oracle-success/full-failure cases.

### Mapping 3 — Satellite collapse → reference representation and map-geometry bottleneck

```text
Observed: satellite median ≈23.6× aerial;
          295 samples processed but SR@1≈5.42%
→ retrieval + matching + map/DSM + final geometry
→ domain/resolution/temporal/georegistration/DSM causes remain confounded
→ L1 representation + L5 map validity + L9 generalization
→ OrthoLoC, PiLoT v2, AirLock+, RoMa, MASt3R
```

**Confidence:** high for the system-level modality effect and retrieval-independent GT-reference gap; medium for a front-end correspondence/alignment bottleneck because DSM-free 2D agreement tracks failure; low for a feature-only causal claim.

**Required diagnostic:** the matched-query aerial/satellite GT-reference control and DSM-free XY audit are complete. Next inspect the deterministic 24-query visual shortlist and, if ambiguity remains, add a small manual landmark set plus RoMa certainty. Keep map/georegistration offsets as a measured confounder rather than turning DSM/PnP into the contribution.

### Mapping 4 — `yp`/`p` gap → pose-alignment dependency

```text
Observed: removing yaw alignment drops SR@1 by 47.12 pp
→ pose-aware crop/rotation, then retrieval and matching
→ orientation ambiguity or lost overlap may propagate downstream [Hypothesis]
→ L6 prior dependency + L1 cross-view alignment
→ Bearing-UAV, PiLoT v2, PiLoT, AirLock+, Scale-Aware U2S-CVGL
```

**Confidence:** high for aggregate yaw-path dependence; medium-low for whether retrieval or matching is dominant.

**Required diagnostic:** identical-query `yp`/`p` ranks, crop footprints, overlaps, matches, and PnP evidence; then bounded yaw perturbations.

### Mapping 5 — Matcher trend → geometry usefulness of correspondences

```text
Observed: RoMa described as more stable than SP_LG_GIM;
          many matches ≠ geometrically useful matches
→ matching and PnP input
→ coverage, correctness, and 3D distribution may matter more than count [Hypothesis]
→ L3 matching geometry + L5 PnP solvability
→ RoMa, DKM, OrthoLoC, MASt3R, AirLock+
```

**Confidence:** medium for the retained run outcome because exact metrics and sample-level rows are recovered; low for a causal matcher conclusion because controlled provenance is incomplete and `20260821-1402` is unstable.

**Required diagnostic:** per-method match count/confidence, 2D coverage, valid 3D count/spread, inliers, residuals, and final error on identical candidates.

## 7. Can current evidence support “retrieval similarity ≠ localizability”?

### Short answer

**Query-level support: yes. Candidate-level conclusion: no.**

What is supported:

- a useful retrieval criterion often occurs below rank 1 [RAW_VERIFIED];
- GT rank and PDM@5 have weak relationships with final metric error at query level [RAW_VERIFIED];
- 67/79 rank-2-to-5 queries localize within 1 m and 79/79 within 3 m in the canonical Top-N run [RAW_VERIFIED];
- oracle-reference performance is stronger than the full pipeline at the 1 m threshold, with paired transitions in both directions [RAW_VERIFIED];
- PnP completion can coexist with large canonical and satellite localization errors [RAW_VERIFIED].

What is not supported:

- direct correlation between raw CAMP similarity score and final error;
- proof that the Top1 candidate is less localizable than a lower-ranked candidate;
- proof that match coverage/inliers predict success better than retrieval score;
- a calibrated definition of candidate localizability.

The defensible Phase 4.6 statement is:

> Scene_16 query-level raw evidence shows weak alignment between stored GT rank/PDM@5 and final localization error, while many queries with GT rank 2–5 still localize accurately in the Top-N pipeline. Candidate-level similarity-versus-localizability remains untested because candidate scores, identities, selections, and candidate-specific poses are missing.

## 8. Localizability questions Q1–Q5

| Question | Current answer | Why | Required evidence |
| --- | --- | --- | --- |
| Q1. Is Top-1 always the most localizable candidate? | **Cannot answer** | no per-candidate localization result | run/restore matching+geometry for every Top-K candidate and compare final pose/error |
| Q2. Do high retrieval-score candidates fail matching/DSM/PnP? | **Cannot answer** | scores and downstream diagnostics are not joined | candidate score, overlap, match status, DSM validity, solver status/error |
| Q3. Can a lower-ranked candidate have better geometry? | **Query-level cohort success is verified; candidate comparison is not** | rank-2-to-5 queries often localize accurately, but selected/candidate-specific geometry is absent | selected rank, candidate-specific inliers/conditioning/error, and Top1-only outcomes |
| Q4. Does high match count imply low error? | **Cannot answer for raw match count; inlier count alone does not** | canonical inlier/error Spearman `rho=0.0291`; four top-quartile-inlier queries exceed 1 m | raw match count/confidence/coverage and geometry distribution joined to error |
| Q5. Do coverage/inliers predict success better than retrieval score? | **Inliers do not predict query error here; full comparison remains unavailable** | rank, PDM@5, and inlier correlations are all weak, but raw score and coverage are absent | candidate-level score, coverage, inlier ratio, residual and calibrated success analysis |

## 9. Per-sample attribution readiness

Current answer: **the repository can perform limited query-level attribution for the canonical run, but not candidate-level or full stage-causal attribution.**

| Required field | Present? | Current evidence |
| --- | --- | --- |
| `sample_id` / query path | Partial | all 295 sample IDs; machine-specific source paths remain only in external raw artifacts |
| GT reference identifier/rank | Partial | per-query GT rank present; candidate/reference identity absent |
| Top-K candidate IDs and retrieval scores | No | absent |
| candidate physical distance/overlap/PDM contribution | Partial | per-query PDM@5 and rank present; candidate-level components absent |
| selected candidate and selection reason | No | absent |
| match count and retained count | No | absent |
| match-confidence distribution | No | absent |
| query/reference spatial coverage | No | absent |
| DSM valid/no-data statistics | No | absent |
| valid 2D–3D correspondence count | No | absent |
| 3D spatial distribution/eigenvalues | No | absent |
| PnP solver status/inliers/residuals | Partial | status and best-inlier count present; residuals/conditioning absent |
| PnP conditioning/covariance proxy | No | absent |
| final pose and localization error | Yes externally; error retained in audit table | final pose in external raw bundle; final error and threshold labels in repository CSV |
| success/failure label and stage code | Partial | deterministic 1 m/3 m labels present; causal stage code absent |
| per-stage runtime/memory | No | absent |

## 10. Filtered research opportunities — maximum three, not methods

### Opportunity 1 — Candidate localizability at the retrieval–matching interface

**Observed Evidence.** R@1→R@5 adds exactly 79 queries under the retrieval criterion; their canonical Top-N localization is 67/79 within 1 m and 79/79 within 3 m. Full SR@1 is 5.09 pp below oracle despite similar medians, with paired transitions in both directions [RAW_VERIFIED].

**Literature Support.** Phase 3 L2/L4; CAMP, CAME, R²Former, SelaVPR, 3D Geometric Perception, and Bearing-UAV.

**Why Existing Methods Are Insufficient.** VPR rerankers optimize place similarity/local evidence; direct-pose systems use different map/state assumptions. No verified method in the comparison set provides a general DSM/PnP localizability probability for global UAV candidates.

**Missing Evidence.** Candidate IDs/scores, overlap, match geometry, map validity, selection decision, and candidate-specific poses for all Top-K candidates. Query-level PnP status/inliers and final error are now present.

**Research Value.** High if a localizability target changes candidate selection and final localization beyond CAMP+Top-N without hiding failure modes.

**Novelty Risk.** High because learned reranking, candidate context, shared features, and unified pose models are occupied. The gap must be defined by metric UAV/2.5D-map localization, not generic reranking.

**Next Diagnostic.** Build a candidate-level dataset; measure rank correlation and success-prediction AUROC/calibration for CAMP score, overlap, match coverage, inlier ratio, and geometry quality.

### Opportunity 2 — Correspondence usefulness under imperfect aerial/satellite 2.5D maps

**Observed Evidence.** Satellite performance collapses while all 295 samples have `pnp_success=true`; aerial GT-reference localization is strong [RAW_VERIFIED].

**Literature Support.** Phase 3 L1/L3/L5/L9; OrthoLoC, PiLoT v2, RoMa, DKM, MASt3R, and AirLock+.

**Why Existing Methods Are Insufficient.** Generic matcher confidence does not know georeferenced map/DSM validity. Direct registration/3D methods change the substrate but do not establish a reusable diagnostic for AnyVisLoc's 2D–3D/PnP chain.

**Missing Evidence.** Satellite retrieval-only and satellite GT-reference controls; DSM validity, georegistration, match coverage, valid 3D points, inliers, residuals, and conditioning.

**Research Value.** Very high if failures correlate with map-aware geometry rather than merely appearance similarity.

**Novelty Risk.** Medium–high due to DKM geometry-oriented sampling, MASt3R 3D grounding, OrthoLoC AdHoP, and PiLoT v2 map registration.

**Next Diagnostic.** Factor satellite failure into `retrieval`, `2D matching`, `2D→3D lifting`, and `pose` using identical sample IDs and oracle references.

### Opportunity 3 — Robustness to uncertain or missing yaw/scale alignment

**Observed Evidence.** `yp`→`p` reduces SR@1 by 47.12 pp and increases median error about 6.8× on paired 295-query outputs [RAW_VERIFIED/derived].

**Literature Support.** Phase 3 L6; Bearing-UAV, PiLoT v2, PiLoT, AirLock+, and Scale-Aware U2S-CVGL.

**Why Existing Methods Are Insufficient.** Current solutions replace one assumption with heading prediction, gravity/range, sequential state, temporal filtering, or semantic scale anchors. They do not provide a standardized prior-uncertainty protocol for AnyVisLoc's modular front end.

**Missing Evidence.** Exact crop/rotation transforms, retrieval and matching changes under identical perturbations, sensor uncertainty, and a bounded noise curve.

**Research Value.** High if the responsible front-end stage is identified and robustness improves without changing PnP or adding a stronger sensor.

**Novelty Risk.** Medium–high; generic rotation invariance, learned alignment, heading prediction, and scale estimation are established.

**Next Diagnostic.** Run or restore controlled yaw-only perturbations while logging crop overlap, ranks, matching coverage, and final pose; first use a small representative subset.

## 11. Phase 5 diagnostics required before proposing an idea

### Priority 0 — finish provenance recovery before new experiments

- **Completed:** recovered and preserved raw JSON/CSV artifacts externally; verified archive checksum; recomputed all five principal checkpoint metrics; created the canonical 295-query audit table.
- **Still missing:** exact commands, YAML/config snapshots, AnyVisLoc code revision, checkpoint identities/hashes, seeds, logs, dataset split/version fingerprint, and environment record.

### Priority 1 — define one joined diagnostic schema

The first table now exists for the canonical run. Complete two linked tables:

1. **Completed, limited schema:** one row per canonical query with rank, PDM@5, final error, PnP inliers/status and threshold labels;
2. **Missing:** one row per query–candidate pair, plus candidate selection and stage-specific diagnostics.

Use stable identifiers and retain every failed/no-pose attempt. The schema must include the fields in §9 plus paths to raw artifacts.

### Priority 2 — recover or minimally generate three controlled decompositions

1. **Candidate decomposition:** Top-K candidate → matching → DSM → PnP → candidate-specific final error.
2. **Reference decomposition:** aerial/satellite × retrieval/GT-reference using identical query IDs.
3. **Prior decomposition:** `yp`/`p` and bounded yaw perturbations with unchanged models and queries.

### Priority 3 — measure predictive relationships

- Spearman correlation of retrieval score/rank, match confidence/count/coverage, DSM-valid ratio, inlier ratio, residual, and condition proxy with final error;
- AUROC/AUPRC and calibration for predicting success at 1/3/5 m;
- oracle candidate upper bounds: best by GT error, best by inliers, best by coverage, and CAMP Top1;
- paired bootstrap/confidence intervals rather than aggregate-only comparisons.

### Priority 4 — create deterministic failure labels and qualitative cases

Define explicit criteria for retrieval failure, no-overlap, matcher failure, DSM invalidity, insufficient 2D–3D geometry, solver failure, wrong-but-solvable pose, and prior-induced crop/alignment failure. Attach representative images and intermediate overlays.

## 12. Phase 4 decision

The evidence is sufficient to enter **Phase 5 diagnostic design and provenance completion**, but insufficient to choose a proposed method.

The current strongest evidence chain is:

```text
rank gap + oracle/full gap
→ candidate interface deserves investigation

satellite collapse
→ reference representation/map geometry deserves investigation

yp/p collapse
→ pose-alignment dependency deserves investigation
```

The next valid research action is the smallest remaining evidence recovery: restore exact run provenance and candidate-level Top-K outputs for a focused subset or the retained 295 queries. Query-level attribution is now available; candidate-level attribution and stage-causal evidence are not. Architecture modification remains premature.
