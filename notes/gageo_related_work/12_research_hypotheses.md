# 12 — Research Hypotheses

> **Status：PROVISIONAL candidate pool。** PR-MHA is the leading hypothesis，not a selected/frozen method，until Phase 3B tests top-K recoverability and prompt-return discrimination。

## Candidate interventions

Scores use 1（poor）to 5（strong/easy）；novelty score means current differentiation potential，not a completed novelty claim。

| Candidate | Evidence support | Mechanism fit | Novelty potential | Implementation ease | Training cost | Ablation clarity | Main risk |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A. Higher-resolution / multi-level DINO features | 3 | 2 | 2 | 3 | 2 | 4 | targets Small amplifier but not Ground Large catastrophic tail |
| B. Stronger prompt encoder / prompt reinjection | 2 | 2 | 2 | 4 | 4 | 4 | richer prompts already give little Ground gain；collides with OCGNet-style location preservation |
| C. Pose-conditioned rectification / attention | 3 | 3 | 3 | 2 | 2 | 3 | predicted rotation is itself unreliable；circular error amplification |
| D. Prompt-Return Multi-Hypothesis Anchoring（PR-MHA） | **5** | **5** | **4** | 3 | 4 | **5** | correct region may be absent from feature top-K；requires diagnostic gate |

Training-cost score is higher when cheaper。

## Leading research hypothesis（not frozen）

> **If Ground catastrophic failures are caused by premature collapse from ambiguous cross-view evidence into one unanchored object token，then retaining top-K reference spatial hypotheses and verifying each candidate by whether it can attend back to the original query prompt/context will reduce coupled bbox/mask zero-overlap failures，especially for Ground + Small，without degrading the high-performing median population。**

## Falsifying outcomes

Reject or revise PR-MHA if any of the following occurs：

1. the GT reference region is not present in top-K feature hypotheses for failures at DINOv2 or π³ stages；
2. prompt-return consistency cannot distinguish GT from the selected wrong candidate better than chance；
3. an adapter reduces mean error but does not reduce severe Ground failures；
4. gains disappear after controlling for annotation-valid samples；
5. Drone or Ground-success guardrails regress materially；
6. closest-work review shows equivalent top-K prompt-return verification already exists。

## Expected affected samples

Primary：190 Ground severe failures，especially 114 Ground + Small。

Secondary：53 Ground + Medium、23 Ground + Large and rare repetitive-instance Drone failures。

Not primary：boundary-only segmentation errors，because the existing mask head is preserved。
