# 14 — Proposed Method: Late-Spatial PR-MHA

> **Status：DESIGN FROZEN for MVP；no training or model-code modification has started。**

## Goal

Late-Spatial PR-MHA adds a lightweight，config-disableable preservation and verification path **after π³ pair-stage 11 and before the remaining late pair-stages/final spatial representation**。It does not replace DINOv2、SAM2、π³、bbox head or mask head。

## Baseline vs proposed flow

```text
Baseline
π³ stage-11 query/reference spatial fields
→ late π³ refinement
→ final reference field + bbox/mask query
→ bbox + mask

Late-Spatial PR-MHA
π³ stage-11 spatial field
→ dense reference anchor scores + top-K spatial candidates
→ preserve candidate identity/context through late π³ refinement
→ each refined candidate attends back to query grid
→ forward score + prompt/context-return verification
→ reliability-gated fusion before final spatial/task collapse
→ unchanged bbox + mask heads
```

## Module 1: Stage-11 query target/context representation

MVP inputs for the released Large model：

- internal stage-11 query patches `Fq11 ∈ R[B,1369,1024]`；
- internal stage-11 reference patches `Fr11 ∈ R[B,1369,1024]`；
- the actual inference prompt（point/bbox/mask），converted to `Wp ∈ [0,1]^{B×1369}`；
- the existing bbox/mask task query，unchanged until final fusion。

Build a 37×37 prompt weight map：

- point：Gaussian neighborhood around the prompt patch；
- bbox：soft interior + narrow context ring；
- mask：downsampled binary/soft mask + context ring。

Pool stage-11 query features into：

```text
target descriptor
context-ring descriptor
```

The context descriptor matters because facade appearance alone may be ambiguous；roads、neighbors and relative layout can help distinguish reference candidates。

## Module 2: Stage-11 forward reference hypotheses

Project query target/context and reference patch features into a 256-D adapter space。Cosine similarity produces `S_anchor ∈ R[B,1369]`。Apply 3×3 local-maximum suppression and select `K=8` peaks，yielding indices `[B,8]`、coordinates `[B,8,2]` and candidate tokens `[B,8,1024]`：

```text
candidate_k = reference feature at peak_k
            + 2D peak position embedding
            + query target/context conditioning
```

Unlike generic extra learnable queries，each candidate is tied to a concrete reference location and receives explicit positive/negative supervision。

## Module 3: Preserve hypotheses through late refinement

Immediately after the stage-11 global block（decoder block 23 for the Large model），append the eight candidates to the satellite-side learnable-token segment with their reference-grid RoPE coordinates。Propagate them through the existing stage12→17 local/global blocks，which are frozen in MVP。Keep the original number of task queries separately so candidate tokens are never mistaken for heatmap/bbox queries。Concatenate the candidate states from the final two decoder blocks to obtain `Cfinal ∈ R[B,8,2048]`。

## Module 4: Prompt-return verification

For every refined candidate，project `Cfinal` and `Fq11` to 256-D，then compute candidate→query attention `Areturn ∈ R[B,8,1369]`。Inference uses the prompt-derived map，never an oracle GT query mask。For candidate `k`：

```text
m_k = Σ_n Areturn[k,n] · Wp[n]
return_consistency_k = logit(clamp(m_k)) - logit(clamp(mean(Wp)))
verification_k = anchor_score_k
               + α · return_consistency_k
               + β · context_consistency_k
```

The uniform-area correction prevents a large prompt region from receiving a high score merely because of its area。For Point Prompt，`Wp` is a Gaussian centered at the exact official point；bbox uses a soft interior，and mask uses adaptive pooling。Context consistency is a narrow outer ring and can be disabled independently。Prompt-return remains complementary rather than sufficient alone：the full run shows strong cohort-level divergence but overlapping per-sample distributions。

## Module 5: Reliability-gated fusion

Let `pk = softmax(verification)`。Build verified context `V = Σ_k pk·Cfinal_k ∈ R[B,2048]` and a sparse verified spatial residual `R ∈ R[B,1369,2048]` scattered at the selected peaks（MVP uses fixed 3×3 Gaussian spreading）。Gate confidence uses top-1/top-2 margin、normalized entropy and top return consistency：

```text
g = tanh(γ) · sigmoid(MLP([margin, 1-normalized_entropy, top_return]))
bbox_query' = bbox_query + g · Wobj(V)
sat_features' = sat_features + g · R
```

`γ` is initialized to zero，so the enabled MVP begins as the released predictor。Only `bbox_query'` and `sat_features'` are passed to the existing `BBoxHead` and `SAMMaskHead`；camera、heatmap and contrastive branches keep the original features。The bbox/mask heads and their signatures do not change。

With `use_late_spatial_pr_mha: false`，the module is not called，no tokens are appended，and the original inference path is unchanged。The switch is required for every baseline comparison。

## New MVP parameters

- query/reference/return projections：`1024↔256`；
- candidate initializer and 2D coordinate MLP；
- verification coefficients/MLP；
- object residual projection `2048→2048`；
- confidence MLP and zero-initialized scalar `γ`。

Top-K、NMS and fixed Gaussian scatter have no trainable parameters。All new parameters live under `late_spatial_pr_mha.*` for checkpoint filtering and ablation。

## Training losses

Keep all original GAGeo losses and add：

1. `L_anchor`：stage-11 dense anchor focal loss against the downsampled reference GT mask；
2. `L_preserve`：negative log probability mass assigned to GT-overlapping reference patches before hard top-K；
3. `L_rank`：best GT-overlapping candidate outranks the hardest non-GT candidate by a margin；
4. `L_return`：GT candidate return consistency outranks wrong candidates；
5. `L_gate`：small residual/gate regularizer that protects the released prediction when confidence is low。

All labels already exist in CMA-Loc。Evaluation metrics and severe-failure definition remain unchanged。

## Falsifiable prediction

PR-MHA should primarily lift the lower tail：Ground q05/q10 and severe-failure rate should improve more than the median。If only mean/median changes while 190 severe cases remain，the intervention does not address the claimed mechanism。

## Minimum viable experiment

- Use the official train split for optimization；the 570 diagnosis samples remain evaluation-only。
- Freeze DINOv2、SAM2 prompt encoder/projections、all π³ blocks、existing task queries and all existing heads；train only `late_spatial_pr_mha.*`。
- Use `K=8` in the first run；K=4 is a later ablation，not an initial grid。
- Primary metric：Ground severe-failure rate (`det_iou == 0 && mask_iou == 0`)。
- Diagnostics：stage11→final H@8 retention，GT rank gain，GT-vs-wrong margin and return margin。
- Guardrails：Ground-success and Drone-success det/mask IoU plus overall official evaluation。
- Support：severe tail and late-stage GT retention improve without material success-cohort regression。
- Falsify：only mean IoU improves，candidate retention does not，or success cohorts regress。

Exact placement inside pair-stages 12–17 remains an ablation variable because the current artifact does not expose stage-17 spatial patches。
