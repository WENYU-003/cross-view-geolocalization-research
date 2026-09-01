# 14 — Provisional Candidate Method: PR-MHA

> **Status：PROVISIONAL，do not implement yet。** The architecture and insertion point must follow the Phase 3B layer-wise result rather than the Phase 3A interpretation。

## Goal

PR-MHA adds a lightweight，config-disableable verification path to GAGeo。It does not replace DINOv2、SAM2、π³、bbox head or mask head。

## Baseline vs proposed flow

```text
Baseline
prompt-conditioned query/reference interaction
→ one unanchored object task token
→ bbox + mask

PR-MHA
prompt-conditioned query/reference features
→ dense reference anchor scores
→ retain top-K spatial candidate tokens
→ each candidate attends back to query grid
→ score mass returning to prompt/context region
→ reliability-gated verified context
→ existing object task token
→ unchanged bbox + mask heads
```

## Module 1: Query target/context representation

Build a 37×37 prompt weight map：

- point：Gaussian neighborhood around the prompt patch；
- bbox：soft interior + narrow context ring；
- mask：downsampled binary/soft mask + context ring。

Pool final or intermediate query features into：

```text
target descriptor
context-ring descriptor
```

The context descriptor matters because facade appearance alone may be ambiguous；roads、neighbors and relative layout can help distinguish reference candidates。

## Module 2: Forward reference hypotheses

Project query target/context and reference patch features into a shared adapter space，then generate a dense anchor logit map。Use non-maximum suppression/top-K peaks to create spatial candidate tokens：

```text
candidate_k = reference feature at peak_k
            + 2D peak position embedding
            + query target/context conditioning
```

Unlike generic extra learnable queries，each candidate is tied to a concrete reference location and receives explicit positive/negative supervision。

## Module 3: Prompt-return verification

For every reference candidate，compute candidate→query attention。A correct candidate should return attention mass to the query prompt region and compatible context ring。Define：

```text
return score = attention mass inside target prompt
             + weighted context consistency
```

Combine forward anchor score and return score to rank candidates。This verification is intended to reject semantically similar but spatially/contextually inconsistent buildings。

## Module 4: Reliability-gated fusion

Compute a confidence margin between the top candidates。Fuse the verified reference context into the existing object token with a zero-initialized residual gate：

```text
object_token' = object_token + gate(confidence) · verified_context
```

If verification is uncertain，the gate remains near zero and preserves baseline behavior。This is important because most Ground samples already have high median IoU。

## Training losses

Keep all original GAGeo losses and add：

1. `L_anchor`：reference GT center/mask heatmap focal or BCE loss；
2. `L_rank`：GT-overlapping candidate outranks mined wrong candidates；
3. `L_return`：positive candidate returns mass to query prompt，negative candidates do not；
4. optional entropy/margin calibration for the reliability gate。

All labels already exist in CMA-Loc。Evaluation metrics and severe-failure definition remain unchanged。

## Falsifiable prediction

PR-MHA should primarily lift the lower tail：Ground q05/q10 and severe-failure rate should improve more than the median。If only mean/median changes while 190 severe cases remain，the intervention does not address the claimed mechanism。
