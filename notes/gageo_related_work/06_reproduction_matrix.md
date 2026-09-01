# 06 — Reproduction Matrix

Machine-readable rows are stored in [`06_reproduction_matrix.csv`](06_reproduction_matrix.csv)。The matrix contains only settings with tracked result JSON；blocked or unrun experiments remain in [`07_reproduction_checkpoint.md`](07_reproduction_checkpoint.md) rather than being represented as fabricated empty result rows。

## Status vocabulary

- **VERIFIED MATCH**：tracked JSON value rounds to the paper-displayed value under the same split/view/prompt/metric。
- **APPROXIMATELY ALIGNED**：same intended protocol and trend, but a non-zero displayed difference or incomplete run provenance remains。
- **NOT DIRECTLY COMPARABLE**：different dataset/split/prompt/protocol prevents a defensible numerical comparison。
- **UNRESOLVED**：necessary protocol or artifact is unavailable。

## Main benchmark summary

| Setting | Rows | Status | Evidence |
| --- | ---: | --- | --- |
| CMA-Loc Seen (`test`) | 6 view×prompt rows | 6 VERIFIED MATCH | 4,220 samples per prompt; JSON task groups 2,184 Drone + 2,036 Ground |
| CMA-Loc Unseen (`unseen_test`) | 6 view×prompt rows | 11/12 total main rows VERIFIED MATCH; Unseen Mask D2S AAE approximately aligned | 4,197 samples per prompt; JSON groups 2,017 Drone + 2,180 Ground |
| CVOGL-Seg Table 4 | 2 view rows | APPROXIMATELY ALIGNED | 973 samples each; differences in headline metrics ≤1.40 percentage points |

The single main-benchmark displayed discrepancy is Unseen D→S Mask AAE：paper 461.2 pixels vs saved evaluator 461.1 pixels。It is too small to affect any research decision。

## Confidence interpretation

Tables 2–3 receive **high numerical confidence** because：

1. saved JSONs contain exact unrounded aggregates；
2. task counts sum to split counts；
3. all prompt/view rows independently match paper values；
4. result artifacts were added in historical commits before this audit。

Their **execution provenance is partial**：the result files do not embed command、config、checkpoint hash、code hash or logs。The reproduction README records a representative command and checkpoint path, so “saved-result verified reproduction” is supported；“fully self-contained rerunnable bundle” is not。

Table 4 receives **medium confidence**：the result files and approximate numerical alignment are real, and an official-code historical CVOGL-Seg adapter can be found at GAGeo commit `28c58f5`；however the exact adapter revision/config/log used for the tracked JSON is not preserved in this repository。

## Research-facing conclusions

- Richer prompts materially improve Drone→Satellite；the effect is small for Seen Ground→Satellite and modest for Unseen Ground→Satellite。
- Unseen Ground→Satellite Point is an appropriate hard setting：mAcc 65.30、model mIoU 72.68，and severe failures concentrate there。
- Aggregate averages alone do not identify mechanism；they motivate the per-sample controlled diagnostic recorded in the checkpoint。
