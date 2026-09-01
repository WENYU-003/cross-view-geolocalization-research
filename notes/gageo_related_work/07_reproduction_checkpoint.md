# 07 — Reproduction Checkpoint

## Inventory and status

| Work item | Status | Evidence and decision |
| --- | --- | --- |
| CMA-Loc environment/dataset setup | DONE with provenance limitation | README records A100 environment, data layout and checkpoint load; environment snapshot/checkpoint hash not tracked |
| Seen × Point/BBox/Mask | DONE | three 4,220-sample JSON files; task groups sum exactly to total |
| Unseen × Point/BBox/Mask | DONE | three 4,197-sample JSON files; task groups sum exactly to total |
| Table 2 Detection | DONE | all 12 view/split/prompt rows match paper at two-decimal percentage precision |
| Table 3 Segmentation | DONE | all rows match displayed precision except one 0.1-pixel AAE rounding difference |
| Table 4 CVOGL/CVOGL-Seg | PARTIAL | two 973-sample result JSONs are close to paper; exact run adapter/config/log absent from research repo |
| Table 5 Ground→Drone | BLOCKED | released public metadata does not expose exact 1,245 Ground–Drone pairing |
| Table 6 loss ablation | LOW PRIORITY | no trained variants; full retraining does not currently change the limitation decision |
| Figure 4 architecture/token ablation | LOW PRIORITY | no trained variants; not required before mechanism diagnosis |
| Quantitative severe failures | DONE for saved statistics | 4,197-row CSV deterministically reproduces all reported subgroup counts |
| Reproducible per-sample export | PARTIAL | stable index/filenames/category/IoUs exist; predictions, prompt coordinates, pose, artifact path and generator script are missing |
| Qualitative examples | PARTIAL | ten tracked panels exist; selection protocol and full taxonomy labels are not reproducibly stored |

## Git provenance

- `1fa99e9` added six main result JSON files under the original `reproductions/GAGeo/` path。
- `471a7dc` moved them to `reproductions/gageo/` and added benchmark records。
- `3117fda` added the two Table 4 result JSON files。
- `c5ada95` added the 4,197-row failure CSV, ten example panels, and consolidated README。

These commits establish that the artifacts predate this audit. They do not by themselves prove the exact command/config/checkpoint identity of every run.

## Confidence summary

### High confidence research evidence

- Tables 2–3 numerical alignment from saved JSON；
- operational split mapping `test=Seen`, `unseen_test=Unseen` from metric identities；
- each main evaluation includes both Drone and Ground groups；
- prompt modalities all produce detection and native segmentation；
- severe failure count and all task/size/shape subgroup counts。

### Usable but bounded evidence

- Table 4 trend and approximate paper alignment；
- stored latency/pose summaries, because evaluator definitions are known but paper comparison is not the main published table；
- ten qualitative panels as examples, not prevalence estimates。

### Not yet research evidence

- README causal phrases such as viewpoint gap or small target “causes” failure；
- a complete failure taxonomy；
- claims about which DINOv2/π³ layer loses target information；
- Table 5/6 reproduction。

## Research decision gate

1. **Is reproduction sufficient for research analysis?** Yes for Tables 2–3 and the `unseen_test + point` statistical failure population. No for training-ablation attribution or complete run provenance claims.
2. **Primary research setting:** CMA-Loc `unseen_test`, Point prompt, Ground→Satellite；start with the Ground + Small subgroup and use matched Ground + Small successes as controls.
3. **Evidence usable now:** six grouped JSONs, paper-aligned Tables 2–3 metrics, 4,197-row failure CSV, verified subgroup rates, and the released model/data-flow implementation.
4. **Important unresolved discrepancy:** why the public split sample-count statement is reversed relative to files; record it, but it does not block the chosen setting because metrics identify semantics.
5. **Low-value discrepancies:** reproducing Table 5 without pairing, full Table 6/Figure 4 retraining, and resolving the 0.1-pixel AAE rounding difference。
6. **Ground vs Drone gap:** sufficiently reliable as a statistical phenomenon to enter mechanism analysis；not sufficient to claim viewpoint gap as the cause。

## Single next diagnostic

Run one **matched Ground + Small target-signal retention probe**：compare all 114 severe failures against size/city/shape-matched successful Ground + Small controls, measuring at frozen DINOv2 output and π³ stages 4/11/17：

```text
query target-vs-background separability
reference target-vs-nearest-distractor separability
cross-view target-region cosine similarity / rank
```

Use GT masks only for offline measurement, never as model input beyond the normal Point prompt. This single diagnostic distinguishes three competing mechanisms：early visual-signal absence、π³ interaction degradation、or preserved representation followed by head/instance-selection failure。
