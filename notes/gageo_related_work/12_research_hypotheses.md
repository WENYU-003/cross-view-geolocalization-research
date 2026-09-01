# 12 — Research Hypotheses

> **Status：FROZEN for the first minimal intervention。** Phase 3B supports a modified，late-spatial PR-MHA hypothesis；this is not yet an effectiveness claim。

## Candidate interventions

Scores use 1（poor）to 5（strong/easy）；novelty score means current differentiation potential，not a completed novelty claim。

| Candidate | Evidence support | Mechanism fit | Novelty potential | Implementation ease | Training cost | Ablation clarity | Main risk |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A. Higher-resolution / multi-level DINO features | 3 | 2 | 2 | 3 | 2 | 4 | rejected as first intervention：DINO H@8 does not separate the two Ground cohorts |
| B. Stronger prompt encoder / prompt reinjection | 2 | 2 | 2 | 4 | 4 | 4 | rejected as first intervention：no evidence that prompt input is the first failing stage |
| C. Pose-conditioned rectification / attention | 3 | 3 | 3 | 2 | 2 | 3 | rejected as first intervention：noisy dependency and weaker module fit |
| D. **Late-Spatial PR-MHA** | **5** | **5** | **4** | 3 | 4 | **5** | selected with MODIFY：preserve candidates in stage11→final interval |

Training-cost score is higher when cheaper。

## Selected research hypothesis

> **If Ground catastrophic failures arise because π³ late refinement suppresses or replaces viable stage-11 spatial hypotheses without explicit candidate preservation and verification，then retaining top-K stage-11 reference hypotheses through the stage11→final interval and reliability-gating their prompt/context consistency before final spatial decoding should reduce coupled bbox/mask zero-overlap failures while preserving successful baseline behavior。**

This predicts a tail-specific effect：Ground severe rate and lower-tail IoU should improve more than median performance。DINOv2、SAM2、the official prompt definition and evaluation protocol remain unchanged。

The causal chain to test is fixed：

```text
stage-11 query/reference spatial fields + inference-time prompt
→ explicit reference top-K
→ late-stage candidate survival and prompt-return verification
→ gated correction of bbox/mask inputs
→ fewer Ground double-zero failures
```

Support requires both mechanism and task movement：stage11→final GT retention/rank must improve **and** Ground severe rate must fall。Either one alone is insufficient。

## Falsifying outcomes

Reject or revise PR-MHA if any of the following occurs：

1. increasing K above 8 still leaves too few severe GT hypotheses recoverable to affect the tail；
2. candidate verification cannot distinguish GT-overlapping from wrong candidates beyond the forward score；
3. an adapter reduces mean error but does not reduce severe Ground failures；
4. gains disappear after controlling for annotation-valid samples；
5. Drone or Ground-success guardrails regress materially；
6. closest-work review shows equivalent top-K prompt-return verification already exists。

## Expected affected samples

Primary：190 Ground severe failures，especially 114 Ground + Small。

Secondary：53 Ground + Medium、23 Ground + Large and rare repetitive-instance Drone failures。

Not primary：boundary-only segmentation errors，because the existing mask head is preserved。

Only the stage-11-recoverable subset is guaranteed to be directly addressable by a preservation method。At K=8 that subset is `31.6%` of severe samples；larger-K recoverability must be measured before estimating the attainable ceiling。
