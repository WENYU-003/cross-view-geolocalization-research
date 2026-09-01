# 16 — Controlled Mechanism Isolation

## Status

**Phase 3B：COMPLETE at module-interval resolution。** The released checkpoint was evaluated on the fixed 570-sample Point-Prompt cohort：190 Ground severe，190 size/shape/city-matched Ground strict successes and 190 matched Drone strict successes。No training or baseline change was performed。

The result locates the dominant identified divergence to the **π³ stage11→final spatial refinement interval**。It does not identify an exact pair-stage among 12–17 because the released hook output contains stage-17 object token but not stage-17 spatial patches。

This phase does not rerun the 4,197-sample benchmark。It uses the existing Point-Prompt CSV to form controls and frozen-checkpoint inference only on the selected 570 samples。

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

Current taxonomy result：all 190 runtime panels were accessible and manually reviewed。**190/190 are visually compatible with A — coherent wrong-instance/spatial anchoring**：the predicted bbox/mask lies on a plausible，spatially separate building/footprint rather than being a boundary-only error around GT。The audit CSV's `label`、`confidence`、`annotation_valid` and `notes` fields are blank，so this is a panel-level observation rather than an independent annotation-validity certification。No panel gives affirmative evidence that annotation corruption alone explains the cohort，but a three-panel overlay cannot eliminate a hidden cross-view identity/data-generation error。

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
  --image-root /path/to/CMA-Loc/urban \
  --manifest /path/to/cross-view-geolocalization-research/reproductions/gageo/phase3b/matched_control_manifest.csv \
  --output-dir /path/to/phase3b_layerwise
```

The script follows official `evaluate_cmaloc.py` split resolution：it loads `$JSON_ROOT/unseen_test.json`，or `<gageo-root>/data/json/unseen_test.json` when `JSON_ROOT` is unset。Use `--dataset-json /path/to/unseen_test.json` only for an explicit override。Aggregate results such as `outputs/unseen_test_point.json` are rejected because they contain grouped metrics，not dataset samples。

For every manifest row，the `index` column maps to `official_dataset[index]`。Both `mono_filename` and `sat_filename` must match the official dataset record before tensors are loaded；any mismatch aborts the run。

Start with `--max-per-cohort 8` as a smoke test；then run the fixed 570-sample cohort，not the full benchmark。The script refuses checkpoints with missing or unexpected keys。

## 4. Competing-hypothesis checkpoint

| Hypothesis | Current decision | Decision-changing evidence |
| --- | --- | --- |
| H1 Small-object / scale | **PARTIALLY SUPPORTED** | strong amplifier；controlled gap remains across informative size×shape strata |
| H2 viewpoint / projection discrepancy | **PARTIALLY SUPPORTED** | view gap survives controls；still confounded with Ground/Drone acquisition and generation |
| H3 prompt information weakness | **NOT SUPPORTED as dominant** | richer prompt gains remain small for Ground；transmission failure remains possible |
| H4 DINOv2 local representation / resolution loss | **NOT SUPPORTED as dominant** | Ground severe and matched Ground success DINO H@8 are similar (`0.1158` vs `0.1000`) |
| H5 π³ interaction degradation | **SUPPORTED at late spatial interval** | severe degrades stage11→final while both success cohorts improve |
| H6 final single-token / single-hypothesis compression | **REVISED** | damage is already present by final spatial output；a final-token-only module is too late |
| H7 annotation / data-generation confound | **NOT SUPPORTED as sufficient；not eliminated** | 190/190 panels show coherent wrong-instance outcomes；runtime labels remain blank |

## 5. Decision gate

`FAILURE FIRST APPEARS AT`：**after π³ stage 11 and by final spatial output；exact stage 12–17 unresolved**。

`DOMINANT FAILURE TYPE`：**coherent wrong-instance/spatial anchoring with Ground-conditioned late spatial refinement degradation**。

The full-sample mechanism statement is：

> **π³ late spatial refinement suppresses/reorders viable GT hypotheses under Ground ambiguity and anchors the shared final representation to a coherent wrong reference instance；size amplifies this mode but does not explain it away。**

Previous limitation：**REVISE**。Keep the multi-hypothesis/verification deficiency，but locate it in stage11→final spatial refinement rather than a final single-token bottleneck。

PR-MHA：**MODIFY** — preserve and verify spatial hypotheses inside stage11→final refinement，not after the final object token。

Applied decision rules：

- **GO** required broad GT survival in spatial top-K and strong prompt-return discrimination；the full result does not meet that bar；
- **MODIFY** applies because recoverability exists for a meaningful subset，the loss is in late spatial refinement，and return verification is informative but incomplete；
- **NO-GO** if the GT region is already absent at DINO/early π³，or taxonomy shows wrong-instance anchoring is not dominant。

## External artifacts — RECEIVED

The full NSCC output archive was received on 2026-09-01 and verified locally。The original requirements were：

1. `unseen_test.json`；
2. exact released checkpoint and evaluation config；
3. CMA-Loc `urban/Losangeles/mono` and `urban/Losangeles/crop_sate` images referenced by the 570-row manifest。

The segmentations and bboxes are read from `unseen_test.json`；separate mask files are not required if its COCO annotations are complete。

## 6. Full-output provenance

Verified full output：4,560 per-layer rows (`570 × 8`)，570 unique samples，190 per cohort，and 190 accessible taxonomy panels。

| Artifact | SHA-256 |
| --- | --- |
| `layerwise_per_sample.csv` | `017725efa01d07b0e51f505eeb25a64d904418719a636b2f7f41d2bd02b164a4` |
| `layerwise_summary.json` | `bf45611797eb94c0d27676cc0002ecb79ace06da8eaed8c13f6bd20843555ebf` |
| `taxonomy_runtime_audit.csv` | `8e3bbe5f75cb0364788f3593185b808a52269e7d69bc9421a493625451c302c4` |

Runtime-vs-saved IoU deviations are numerical only：maximum detection difference `5.79e-6`，maximum mask difference `7.88e-4`；the severe/success cohort gate is unchanged。

Reproduce the statistics with：

```bash
python reproductions/gageo/analyze_phase3b_refinement.py \
  --input /path/to/layerwise_per_sample.csv \
  --output /path/to/phase3b_refinement_stats.json \
  --bootstrap-iterations 10000
```

## 7. Per-sample stage11→final spatial gain

Gain is `final_spatial - stage11_spatial`。For GT rank，negative is improvement；for all other metrics，positive is improvement。Intervals are percentile-bootstrap 95% CIs of the mean（10,000 draws，seed `20270901`）。

| Cohort | Metric | Mean gain [95% CI] | Median；IQR | Improved / degraded |
| --- | --- | --- | --- | --- |
| Ground severe | H@1 | `-0.0842 [-0.1421,-0.0316]` | `0；0` | `3.7% / 12.1%` |
|  | H@4 | `-0.1211 [-0.1895,-0.0526]` | `0；0` | `5.8% / 17.9%` |
|  | H@8 | `-0.1842 [-0.2580,-0.1105]` | `0；0` | `6.3% / 24.7%` |
|  | GT rank | `+150.91 [112.79,190.29]` | `+56；279` | `23.7% / 72.6%` |
|  | GT-vs-wrong margin | `-0.0013 [-0.0147,0.0119]` | `-0.0005；0.1110` | `48.9% / 51.1%` |
|  | Return margin | `-0.1258 [-0.1681,-0.0849]` | `-0.0905；0.3594` | `35.8% / 64.2%` |
| Ground success | H@1 | `+0.6632 [0.5947,0.7316]` | `1；1` | `66.3% / 0.0%` |
|  | H@4 | `+0.5211 [0.4526,0.5895]` | `1；1` | `52.1% / 0.0%` |
|  | H@8 | `+0.4737 [0.4053,0.5474]` | `0；1` | `47.9% / 0.5%` |
|  | GT rank | `-42.38 [-61.56,-24.13]` | `-8；58.5` | `72.6% / 5.8%` |
|  | GT-vs-wrong margin | `+0.1376 [0.1256,0.1495]` | `+0.1386；0.1106` | `96.3% / 3.7%` |
|  | Return margin | `+0.2704 [0.2343,0.3068]` | `+0.2583；0.3409` | `85.8% / 14.2%` |
| Drone success | H@1 | `+0.3316 [0.2579,0.4053]` | `0；1` | `36.3% / 3.2%` |
|  | H@4 | `+0.2158 [0.1526,0.2842]` | `0；0` | `23.2% / 1.6%` |
|  | H@8 | `+0.1789 [0.1211,0.2368]` | `0；0` | `18.9% / 1.1%` |
|  | GT rank | `-22.60 [-38.12,-6.82]` | `0；3` | `42.1% / 4.7%` |
|  | GT-vs-wrong margin | `+0.0468 [0.0345,0.0596]` | `+0.0410；0.0997` | `68.4% / 31.6%` |
|  | Return margin | `+0.0564 [0.0149,0.0973]` | `+0.0563；0.2543` | `58.4% / 41.6%` |

Binary Hit@K gains naturally have many ties，so median zero does not contradict a nonzero cohort mean or the continuous-rank distribution。

## 8. Matched Ground statistical comparison

`control_id` creates deterministic categorical matches，not same-scene/same-target pairs。Ground severe and Ground success are exact-matched on size、shape and city，but arbitrary filename-level one-to-one pairing does not justify a paired signed-rank test。The primary comparison therefore uses independent resampling **within matched size×shape strata**。

Ground-success minus Ground-severe refinement gain：

| Metric | Mean difference [stratified-bootstrap 95% CI] |
| --- | --- |
| H@1 | `+0.7474 [0.6632,0.8316]` |
| H@4 | `+0.6421 [0.5474,0.7421]` |
| H@8 | `+0.6579 [0.5579,0.7579]` |
| GT rank | `-193.29 [-236.24,-150.26]` |
| GT-vs-wrong margin | `+0.1389 [0.1213,0.1564]` |
| Return margin | `+0.3961 [0.3429,0.4502]` |

Every interval excludes zero。The divergence is therefore not explained by the matched categorical size/shape distribution。

## 9. Evidence boundary

### Directly supported

1. Ground severe spatial recoverability is higher at stage 11 than final；both success cohorts show the opposite trajectory。
2. Severe GT rank and return margin degrade，while matched Ground success improves strongly。
3. The Ground severe-vs-success difference remains after size×shape matching。
4. Final bbox/mask failures visibly correspond to coherent alternative reference instances。

### Interpretation

Late π³ refinement commits to or amplifies an incorrect spatial hypothesis under Ground ambiguity because it lacks an explicit mechanism to preserve and verify multiple spatial candidates。

### Still unresolved

- exact first failing pair-stage within 12–17；
- the mechanism for severe samples whose GT is already outside stage-11 top-8（68.4%）；
- larger-K recoverability and learned-verifier discrimination；
- independent annotation-validity certification；
- causal improvement，which requires the next controlled intervention experiment。
