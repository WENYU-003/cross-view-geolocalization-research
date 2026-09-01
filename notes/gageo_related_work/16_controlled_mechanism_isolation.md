# 16 — Controlled Mechanism Isolation

## Status

**Phase 3B：PARTIAL。** Matched-control preparation is complete from tracked artifacts。Failure taxonomy、layer-wise correspondence and prompt-return validation are blocked locally by missing CMA-Loc images/annotations and released checkpoint；no causal module or PR-MHA decision is frozen。

This phase does not rerun the 4,197-sample benchmark。It uses the existing Point-Prompt CSV to form controls，then runs frozen-checkpoint inference only on selected cohorts when the required NSCC artifacts are available。

## 1. Matched-control result

Fixed by construction：`unseen_test`、Point Prompt、Los Angeles。Controlled jointly：size and shape。

| Size | Shape | Ground severe | Drone severe | Ground/Drone RR |
| --- | --- | ---: | ---: | ---: |
| Small | Regular | 114/701 = 16.26% | 4/587 = 0.68% | 23.87× |
| Small | Irregular | 0/26 | 0/85 | not identifiable |
| Medium | Regular | 48/675 = 7.11% | 0/583 | Ground-only observed tail |
| Medium | Irregular | 5/51 = 9.80% | 1/90 = 1.11% | 8.82× |
| Large | Regular | 23/630 = 3.65% | 1/515 = 0.19% | 18.80× |
| Large | Irregular | 0/97 | 0/157 | not identifiable |

The Ground gap survives every informative size×shape stratum。Therefore size and shape do not explain away the view-conditioned tail。Shape is nevertheless a possible modifier：185/190 Ground severe cases are Regular，but the Irregular strata are much smaller and include only five failures。

A deterministic 1:1:1 cohort has been generated for all 190 Ground severe cases：

- Ground severe；
- Ground strict success，same size/shape/city；
- Drone strict success，same size/shape/city。

Strict success means both `det_iou >= 0.5` and `mask_iou >= 0.5`。All controls are unique within each task/stratum。The tracked CSV has no additional covariate after matching：no continuous target area、pose、image content、annotation quality or intermediate feature。Consequently it cannot answer what separates a matched Ground success from a failure without raw data or inference。

Reproduce with：

```bash
python reproductions/gageo/prepare_phase3b_controls.py
```

Outputs：

- `reproductions/gageo/phase3b/matched_control_summary.json`；
- `reproductions/gageo/phase3b/matched_control_manifest.csv`（570 rows）；
- `reproductions/gageo/phase3b/ground_severe_taxonomy_audit.csv`（190 rows）。

## 2. Failure-taxonomy audit protocol

No prevalence is assigned from the seven stored Ground panels。All 190 Ground severe cases must be reviewed using three synchronized views：query with Point Prompt、reference with GT bbox/mask、reference with predicted bbox/mask。

Use exactly one primary label：

- **A — wrong-instance anchoring**：prediction coherently covers another complete plausible object/region，clearly separated from GT；
- **B — near-GT spatial offset**：prediction corresponds to the GT object/footprint but a translation/alignment error makes overlap zero；
- **C — no meaningful correspondence**：prediction has no coherent object-level or near-GT relationship；
- **D — annotation / GT suspicious**：pairing、GT mask/bbox、crop or visibility appears invalid/ambiguous；
- **E — other**：none of A–D；a note is mandatory。

Record confidence and annotation validity separately。The layer-wise runner below exports all 190 panels and a fillable runtime audit CSV on NSCC。

Current taxonomy result：**UNRESOLVED**。The existing seven selected Ground panels are compatible with A but cannot estimate its prevalence。

## 3. Actual layer checkpoints and measurement

Official code revision inspected：`f6585cb`。

`Pi3Backbone` has 36 decoder blocks for the released Large configuration。One pair-stage is one local block plus one global block，so there are 18 pair-stages indexed 0–17。The configured deep-supervision checkpoints are not guessed block numbers；they are read at runtime from `model.backbone.supervision_layers`，currently `[4, 11, 17]`：

- π³ early：pair-stage 4；
- π³ middle：pair-stage 11；
- π³ late：pair-stage 17；
- final：concatenated outputs of the last two decoder blocks plus `final_proj` object token。

The frozen diagnostic measures，per sample and layer：Hit@1/4/8、GT rank、best-GT minus best-wrong score margin。The target representation is oracle-pooled from the query GT mask solely for representation diagnosis；the actual model input remains Point Prompt。It additionally measures candidate→query prompt-region return mass、true/wrong margin、AUROC and AUPRC wherever paired query/reference spatial features are exposed。

Run inside the released GAGeo environment：

```bash
python /path/to/cross-view-geolocalization-research/reproductions/gageo/run_phase3b_layerwise.py \
  --gageo-root /path/to/GAGeo \
  --config /path/to/exact_eval_config.yaml \
  --checkpoint /path/to/mp_rank_00_model_states.pt \
  --json /path/to/unseen_test.json \
  --image-root /path/to/CMA-Loc/urban \
  --manifest /path/to/cross-view-geolocalization-research/reproductions/gageo/phase3b/matched_control_manifest.csv \
  --output-dir /path/to/phase3b_layerwise
```

Start with `--max-per-cohort 8` as a smoke test；then run the fixed 570-sample cohort，not the full benchmark。The script refuses checkpoints with missing or unexpected keys。

## 4. Competing-hypothesis checkpoint

| Hypothesis | Current decision | Decision-changing evidence |
| --- | --- | --- |
| H1 Small-object / scale | **PARTIALLY SUPPORTED** | strong amplifier；controlled gap remains across informative size×shape strata |
| H2 viewpoint / projection discrepancy | **PARTIALLY SUPPORTED** | view gap survives controls；still confounded with Ground/Drone acquisition and generation |
| H3 prompt information weakness | **NOT SUPPORTED as dominant** | richer prompt gains remain small for Ground；transmission failure remains possible |
| H4 DINOv2 local representation / resolution loss | **UNRESOLVED** | requires DINO Hit@K and patch-area audit |
| H5 π³ interaction degradation | **UNRESOLVED** | requires stage 4→11→17 cohort comparison |
| H6 final single-token / single-hypothesis compression | **UNRESOLVED** | requires spatial-vs-object-token recoverability comparison |
| H7 annotation / data-generation confound | **UNRESOLVED, material** | requires 190-case annotation-validity audit |

## 5. Decision gate

`FAILURE FIRST APPEARS AT`：**UNRESOLVED**。

`DOMINANT FAILURE TYPE`：**UNRESOLVED**。

The only currently defensible mechanism statement is weaker than the Phase 3A proposal：

> **A Ground-conditioned catastrophic localization mode occurs upstream of, or in the shared input to, bbox and mask decoding；size amplifies it，but existing aggregate artifacts cannot locate its first failing module。**

Previous limitation：**REVISE / downgrade to provisional**。Its observed shared-path portion remains，but “premature single-token collapse” is not established。

PR-MHA：**decision pending；GO / MODIFY / NO-GO cannot yet be assigned**。

Decision rules：

- **GO** only if the GT region survives in spatial top-K before token collapse and prompt-return distinguishes true from wrong candidates；
- **MODIFY** if multi-hypothesis recoverability exists but the loss occurs earlier or return verification is weak；
- **NO-GO** if the GT region is already absent at DINO/early π³，or taxonomy shows wrong-instance anchoring is not dominant。

## Required external artifacts

The smallest unblocker is not a new benchmark result。Provide either direct files or an NSCC path/manifest for：

1. `unseen_test.json`；
2. exact released checkpoint and evaluation config；
3. CMA-Loc `urban/Losangeles/mono` and `urban/Losangeles/crop_sate` images referenced by the 570-row manifest。

The segmentations and bboxes are read from `unseen_test.json`；separate mask files are not required if its COCO annotations are complete。
