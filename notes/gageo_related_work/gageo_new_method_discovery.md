# GAGeo New Method Discovery

> Status: method-discovery checkpoint after Phase 6B/6B.1. No model implementation or new training is included here.
>
> Evidence convention: **Evidence** means directly supported by preserved artifacts or inspected code; **Interpretation** is the most economical explanation of that evidence; **Hypothesis** is falsifiable but unverified; **Proposed method** is a research intervention, not a result.

## 1. Frozen empirical evidence

### 1.1 Failure population

For CMA-Loc `unseen_test`, Point Prompt, all 4,197 samples:

- Ground severe failure: `190 / 2,180 = 8.72%`;
- Drone severe failure: `6 / 2,017 = 0.30%`;
- Ground/Drone relative risk: approximately `29.3×`;
- severe failure is defined without changing the evaluator: `det_iou == 0` and `mask_iou == 0`;
- size is an amplifier, but size/shape/city-matched comparisons still retain a large Ground gap.

**Evidence:** the failure is strongly conditioned on Ground→Satellite observation, not explained away by the marginal distribution of object size, shape, or city.

### 1.2 Layer-wise trajectory on the fixed 570-sample matched set

| Cohort (N=190 each) | Stage-11 spatial H@8 | Final spatial H@8 | H@8 refinement gain | Mean GT-rank change | Return-margin change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ground severe | 0.3158 | 0.1316 | **-0.1842** | **+150.91** | **-0.1258** |
| Matched Ground success | 0.4421 | 0.9158 | +0.4737 | improvement | positive |
| Matched Drone success | 0.7895 | 0.9684 | +0.1789 | improvement | positive |

Matched/bootstrap comparisons in Phase 3B separate Ground severe from matched Ground success over this same interval. Stage 11 is therefore not merely a weak feature snapshot: late refinement is beneficial for successful samples while being systematically harmful for the severe Ground cohort.

Two boundaries must remain explicit:

1. Only `31.58%` of Ground-severe samples have the GT inside stage-11 spatial top-8. A method that irrevocably truncates to eight candidates has a low ceiling on this cohort.
2. The artifacts localize divergence to **after pair-stage 11 and by the final spatial output**; they do not identify one causal block among stages 12–17.

### 1.3 Observable failure type and annotation boundary

Detection and segmentation fail together (`det_iou = mask_iou = 0`), and their per-sample errors are highly coupled. The 190 rendered panels are compatible with a coherent wrong-instance/spatial-anchor outcome rather than merely imprecise object boundaries.

This is not an independent annotation audit. The runtime taxonomy can support “observable coherent wrong-region behavior,” but it cannot prove that every apparent wrong instance is annotation-valid or that one visual subtype dominates all 190 cases.

### 1.4 Phase 6B and Phase 6B.1

- Zero-gate PR-MHA, 384 Ground training samples and 96 optimizer steps: **NO-GO**.
- Non-zero effective gate near `1e-2`, with the same data, seed, optimizer, schedule, losses, Top-K and insertion point: **NO-GO**.
- The real-batch audit showed finite, non-zero gradients in gate, candidate scorer, return verifier, correction projection and confidence branches.
- The trained non-zero-gate checkpoint was loaded and executed during 570-sample evaluation.
- Baseline and trained mechanism metrics were effectively unchanged; Ground-severe H@8 refinement stayed approximately `-0.1842`, GT-rank degradation stayed approximately `+150.91`, and return-margin movement was negligible.

**Frozen decision:** abandon the current Late-Spatial PR-MHA implementation as the active method. Do not spend the next experiment on gate, LR, epoch, loss-weight or K tuning.

## 2. What PR-MHA taught us

### 2.1 What the implementation actually did

The implemented path is:

```text
stage-11 query spatial features + prompt
    -> one pooled query descriptor
    -> cosine scores over all reference patches
    -> hard Top-K=8 reference patches
    -> prompt-return score for each selected patch
    -> weighted sparse feature correction
    -> F11' = F11 + tanh(gate_parameter) * correction
    -> frozen π³ stages 12–17
```

It did **not**:

- append persistent hypothesis tokens to stages 12–17;
- maintain candidate identity or probability through every late stage;
- prevent later π³ blocks from overwriting the injected signal;
- use an explicit survival, calibration, ranking, cycle-consistency, or intermediate belief loss;
- provide gradient through the discrete Top-K identities;
- represent the `68.42%` of severe samples whose GT is already outside stage-11 top-8.

### 2.2 Supported lesson

**Evidence:** a one-shot, hard-Top-K, sparsely gated residual trained only through existing terminal task losses does not measurably repair the diagnosed trajectory under this MVP.

**Interpretation:** the intervention modified features but did not control the process that destroys or reorders spatial belief during stages 12–17. Its residual was handed back to the same frozen transition dynamics without a persistent state or a direct preservation signal.

**Not supported:** “all multi-hypothesis approaches are ineffective,” “stage 11 is the wrong interval,” or “the result only needs more epochs.” None follows from the two MVPs.

### 2.3 Design constraints learned from the failure

A successor must differ structurally, not cosmetically:

1. keep **dense support** or a recoverable dustbin/re-entry path instead of irrevocable top-8 truncation;
2. expose an explicit hypothesis/belief state across stages 12–17;
3. control the actual late update trajectory, rather than add one feature residual before it;
4. supervise intermediate survival/calibration directly;
5. delay irreversible competition until sufficient cross-view evidence has accumulated;
6. remain inspectable with stage-wise GT mass, rank, entropy and wrong-peak margin.

## 3. Updated problem definition

### 3.1 What is directly supported

> Under severe Ground→Satellite appearance and projection change, the correct reference region retains measurable intermediate spatial recoverability, but the existing late π³ refinement changes that recoverability in the wrong direction, while improving it for matched successful samples.

This is a **trajectory-conditioned failure**, not merely a weak-backbone or universally poor-resolution failure.

### 3.2 Explanations weakened by existing evidence

- **Small-object scale as the dominant cause:** weakened by matched-condition Ground/Drone gaps; scale remains an amplifier.
- **Raw point-prompt insufficiency as the dominant cause:** weakened because richer prompts do not remove the Ground tail.
- **DINOv2 local resolution alone:** weakened because severe Ground DINO H@8 is not lower than matched Ground success, yet their late trajectories diverge.
- **Segmentation-head boundary quality:** weakened by coupled bbox/mask zero-overlap and coherent wrong-region behavior.
- **Zero-gate optimization alone:** rejected as an explanation of the second MVP; non-zero-gate gradients and execution were verified but metrics did not move.
- **A final single-token bottleneck as the established mechanism:** not supported strongly enough and should not remain the primary limitation.

### 3.3 Mechanisms still not distinguished

The current artifacts do not isolate which of the following produces the late degradation:

- cross-view messages overwrite useful local reference evidence;
- attention/query competition prematurely sharpens a wrong spatial mode;
- the model lacks part-level correspondences for facade↔roof or ground↔overhead appearance;
- repeated instances produce an uncalibrated multi-modal posterior that the decoder treats as unimodal;
- terminal bbox/mask/pose losses provide insufficient credit assignment to intermediate spatial states;
- some severe examples contain annotation or crop-generation confounds.

These are alternatives to test, not conclusions to write into the method claim.

### 3.4 New framing: Premature Spatial Hypothesis Collapse

The framing is useful **as an operational phenomenon**:

> **Premature Spatial Hypothesis Collapse (PSHC):** during iterative cross-view refinement, probability mass or recoverability associated with a plausible correct reference region is suppressed before accumulated evidence is sufficient to distinguish it from visually coherent distractors.

The evidence supports the words “spatial,” “late refinement,” and “collapse of GT recoverability.” It does not yet prove that attention becomes over-confident, that a particular token wins a competition, or that collapse is irreversible internally. Therefore PSHC should initially be presented as a measurable trajectory failure, not a fully established causal theory.

### 3.5 Method principle

> Preserve a calibrated distribution over plausible spatial hypotheses until sufficient cross-view evidence has accumulated; make every late update accountable for retaining, transporting, or rejecting probability mass rather than forcing an early winner.

A new method must directly represent and supervise this distribution. Merely increasing feature capacity, adding a post-hoc verifier, or changing a scalar gate is insufficiently aligned.

## 4. Recent method landscape

Search scope: primary project/paper pages from CVPR/ECCV/ICLR 2024 through ICCV/CVPR 2025, plus clearly labelled 2025–2026 preprints/current papers. The purpose is mechanism transfer, not claiming that every paper solves GAGeo's task.

| Work | Venue/year | Mechanism relevant here | Transferable lesson / collision |
| --- | --- | --- | --- |
| [RoMa: Robust Dense Feature Matching](https://openaccess.thecvf.com/content/CVPR2024/papers/Edstedt_RoMa_Robust_Dense_Feature_Matching_CVPR_2024_paper.pdf) | CVPR 2024 | dense warp and match-certainty prediction; coarse classification followed by robust refinement | Preserve dense correspondence and uncertainty instead of a tiny discrete candidate set. A generic dense matcher alone would be derivative. |
| [OmniGlue](https://openaccess.thecvf.com/content/CVPR2024/html/Jiang_OmniGlue_Generalizable_Feature_Matching_with_Foundation_Model_Guidance_CVPR_2024_paper.html) | CVPR 2024 | foundation-model guidance with position-guided cross-image attention | Semantic guidance and geometric/correspondence reasoning should remain separable; generic DINO guidance is already occupied. |
| [Efficient LoFTR](https://openaccess.thecvf.com/content/CVPR2024/html/Wang_Efficient_LoFTR_Semi-Dense_Local_Feature_Matching_with_Sparse-Like_Speed_CVPR_2024_paper.html) | CVPR 2024 | adaptive token selection, coarse matching and subpixel refinement | Coarse-to-fine re-anchoring is feasible, but copying a matching pyramid is not a PSHC contribution. |
| [GIM](https://proceedings.iclr.cc/paper_files/paper/2024/hash/38830ee2c33d56682385a00c8e7e9b85-Abstract-Conference.html) | ICLR 2024 | self-training dense matchers from large internet video with filtering/propagation | Data scale improves generalization, but it would not isolate our late-stage mechanism and violates the minimal-test priority. |
| [DUSt3R](https://openaccess.thecvf.com/content/CVPR2024/html/Wang_DUSt3R_Geometric_3D_Vision_Made_Easy_CVPR_2024_paper.html) / [MASt3R](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/09080.pdf) | CVPR/ECCV 2024 | dense pointmaps; matching head and coarse-to-fine reciprocal correspondences | Explicit correspondence fields are more inspectable than a pooled object token, but 3D pointmaps are not justified by current evidence. |
| [SEA-RAFT](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/01065.pdf) | ECCV 2024 | iterative updates with a mixture distribution and uncertainty-aware loss | Iteration should preserve multi-modality and calibrated uncertainty rather than deterministically overwrite state. |
| [Cutie](https://openaccess.thecvf.com/content/CVPR2024/papers/Cheng_Putting_the_Object_Back_into_Video_Object_Segmentation_CVPR_2024_paper.pdf) | CVPR 2024 | persistent object memory/query interaction and distractor-aware reading | Persistence must be an actual state carried through refinement; a one-time adapter is not memory. |
| [SAM 2](https://openreview.net/pdf/7c41968163abe4e3700e3e3a15174a9d679fcd52.pdf) | ICLR 2025 | streaming memory attention for identity through time | Memory can stabilize identity, but temporal memory cannot simply be renamed cross-view memory. |
| [EASE-DETR](https://openaccess.thecvf.com/content/CVPR2024/html/Gao_EASE-DETR_Easing_the_Competition_among_Object_Queries_CVPR_2024_paper.html) | CVPR 2024 | explicitly analyzes query competition and protects/amplifies a leading query | Query competition is a recognized decoder issue. EASE promotes earlier winner dominance, whereas PSHC calls for delaying dominance under ambiguity; this contrast must be made explicit. |
| [Vision Transformers Need Registers](https://openreview.net/pdf?id=2dnO3LLiJ1) | ICLR 2024 | dedicated register tokens prevent patch-token repurposing and dense-map artifacts | Persistent workspace is valuable, but “add registers” alone is too generic and does not define spatial belief. |
| [Image-matching Uncertainty in VPR](https://openaccess.thecvf.com/content/CVPR2024/papers/Zaffar_On_the_Estimation_of_Image-matching_Uncertainty_in_Visual_Place_Recognition_CVPR_2024_paper.pdf) | CVPR 2024 | estimates match uncertainty under perceptual aliasing | Uncertainty should drive refinement, not only reject predictions after inference. |
| [MATCHA](https://openaccess.thecvf.com/content/CVPR2025/html/Xue_MATCHA_Towards_Matching_Anything_CVPR_2025_paper.html) | CVPR 2025 | dynamically combines semantic foundation features with geometric diffusion features under correspondence supervision | DINO semantics alone can confuse repeated instances; a PSHC method needs localized correspondence evidence, not only stronger semantics. |
| [MINIMA](https://openaccess.thecvf.com/content/CVPR2025/html/Ren_MINIMA_Modality_Invariant_Image_Matching_CVPR_2025_paper.html) | CVPR 2025 | synthetic data scaling for modality-invariant matching | A strong collision for broad “domain gap” claims; our novelty must be the refinement state/trajectory, not simply multimodal training. |
| [Self-Supervised Spatial Correspondence Across Modalities](https://openaccess.thecvf.com/content/CVPR2025/html/Shrivastava_Self-Supervised_Spatial_Correspondence_Across_Modalities_CVPR_2025_paper.html) | CVPR 2025 | cross-/intra-modal contrastive random walks and cycle consistency over all-pairs matches | Bidirectional cycle evidence is a principled verifier and motivates transport-based candidate B. |
| [CoMatch](https://openaccess.thecvf.com/content/ICCV2025/html/Li_CoMatch_Dynamic_Covisibility-Aware_Transformer_for_Bilateral_Subpixel-Level_Semi-Dense_Image_Matching_ICCV_2025_paper.html) | ICCV 2025 | covisibility-aware token condensation suppresses messages from non-covisible regions; bilateral refinement | Confidence-aware message routing is relevant, but a generic covisibility module would collide strongly. |
| [ArgMatch](https://openaccess.thecvf.com/content/ICCV2025/papers/Deng_ArgMatch_Adaptive_Refinement_Gathering_for_Efficient_Dense_Matching_ICCV_2025_paper.pdf) | ICCV 2025 | adaptive refinement windows, confidence-aware aggregation, gradient routing for ambiguous/large-error matches | Supports adaptive, uncertainty-dependent refinement rather than a fixed K/window. |
| [Mind the Gap](https://www.openaccess.thecvf.com/content/ICCV2025/papers/Liu_Mind_the_Gap_Aligning_Vision_Foundation_Models_to_Image_Feature_ICCV_2025_paper.pdf) | ICCV 2025 | aligns foundation features to cross-image matching via instance-detail features and bidirectional prompting | Cross-image reasoning is not guaranteed by single-image foundation features; simply adding DINO features is not novel. |
| [GeoDistill](https://openaccess.thecvf.com/content/ICCV2025/html/Tong_GeoDistill_Geometry-Guided_Self-Distillation_for_Weakly_Supervised_Cross-View_Localization_ICCV_2025_paper.html) | ICCV 2025 | geometry-guided teacher/student feature focusing under weak supervision | Intermediate distillation is occupied nearby; preservation loss alone is likely incremental unless tied to a new belief dynamics formulation. |
| [TROGeo](https://openaccess.thecvf.com/content/ICCV2025/papers/Zhang_Breaking_Rectangular_Shackles_Cross-View_Object_Segmentation_for_Fine-Grained_Object_Geo-Localization_ICCV_2025_paper.pdf) | ICCV 2025 | object/context perception and cross-view object segmentation with SAM-style prompting | Segmentation refinement is already a neighboring direction and does not explain the coupled wrong-region trajectory by itself. |
| [SMGeo](https://arxiv.org/abs/2511.14093) | 2025 preprint | grid-level sparse mixture-of-experts for cross-view encoding | Makes a generic spatial MoE especially collision-prone; no current evidence identifies expert specialization as the bottleneck. |
| [GAGeo](https://cipual.github.io/GAGeo-project-page/) | ECCV 2026 project/paper | geometry-aware promptable object geo-localization with π³, DINOv2 and SAM2 | The new claim must target a measured failure of its iterative spatial trajectory, not repackage its prompt or geometry components. |

Landscape conclusion: dense distributions, uncertainty, bilateral/cycle evidence, persistent memory and adaptive refinement are individually established. A defensible contribution must combine them around a new, measurable object: **the survival and controlled evolution of a cross-view spatial belief through iterative refinement**.

## 5. Candidate methods

### Candidate 1 — Dense Belief-Transport Refinement (DBTR)

**Core idea.** Replace hidden, implicit spatial commitment with an explicit normalized dense belief `p_t` over all reference patches. Every late π³ stage proposes a feature update and new cross-view evidence; a learned conservative filter transports the previous belief, fuses new evidence, and decides where the baseline feature update is trustworthy.

**Why it targets the failure.** It acts on the measured trajectory itself: GT probability mass, rank, entropy and wrong-peak margin remain observable at every stage. No hard Top-K eliminates the GT. Ambiguous cases can retain multiple modes; confident cases can still sharpen.

**Changed GAGeo interval.** Wrap pair-stages 12–17. DINOv2, SAM2, stages 0–11 and original heads remain usable and initially frozen.

**Tensor flow.** For reference tokens `F_t in R^(B×N×C)`, query/prompt summary `q_t`, and belief `p_t in R^(B×N)`:

```text
baseline late pair-stage: F_t, Q_t -> F~_(t+1), Q~_(t+1)
local transport:          p_t -> pbar_(t+1) = T_t(p_t)
cross-view evidence:      h_t(F_t, F~_(t+1), Q~_(t+1), prompt) -> e_(t+1)
Bayesian/log-space fuse:  p_(t+1) = softmax(log(pbar+eps) + tau_t * e_(t+1))
update trust:             a_t = sigmoid(g_t(p_t, p_(t+1), entropy, feature delta))
controlled state update:  F_(t+1) = F_t + a_t * (F~_(t+1) - F_t)
```

The state is dense and can be multi-modal. `T_t` is a local stochastic transport kernel, so mass may move to neighboring patches rather than being frozen at stage 11.

**Training signal.** Existing task losses plus: downsampled GT-region belief NLL; stage-wise GT-mass survival hinge; hard-wrong peak ranking; calibration/entropy loss; and an update-quality target that teaches `a_t` to accept a proposal when it improves GT margin and attenuate it when it harms GT margin.

**Inference.** No GPS/PnP or test-time labels. Belief is initialized at stage 11, transported and updated through late stages, and used to control the same late visual feature path before original heads.

**Difference from baseline.** Baseline updates a latent field unconditionally. DBTR makes the spatial posterior explicit and controls the baseline transition.

**Difference from failed PR-MHA.** Dense rather than hard top-8; persistent rather than one-shot; controls baseline update rather than adding a new sparse correction; stage-wise direct supervision rather than only terminal losses.

**Overhead.** Approximately `O(BNC)` evidence heads plus local transport; avoids full `N²` assignment. Late-stage activation memory rises moderately.

**Difficulty.** Medium-high: pair-stage wrapping and careful checkpoint-compatible logging are required, but the entire backbone need not be rewritten.

**Expected failure mode.** It may preserve an already wrong multi-modal belief, or learn to freeze refinement and harm Ground/Drone successes. Guardrails and proposal-acceptance calibration are essential.

### Candidate 2 — Query-Part Unbalanced Transport (QPUT)

**Core idea.** Represent the prompted query as multiple foreground/context part tokens and solve a soft, unbalanced bipartite transport from query parts to all reference patches plus a dustbin. Refine the transport at several late stages and verify it through a reference→query cycle.

**Why it targets the failure.** Facade/ground evidence may correspond only partially to roofs/overhead context. A one-vector query and one-to-one commitment are brittle; unbalanced transport allows missing parts, repeated structures and multiple plausible regions.

**Changed GAGeo interval.** Part-token extraction at stage 11; transport/refinement at stages 11, 14 and 17; transport marginal conditions the final spatial field and original heads.

**Tensor flow.** Query parts `U in R^(B×M×C)`, reference tokens `V in R^(B×N×C)`, assignment `P_t in R^(B×M×(N+1))`; Sinkhorn/unbalanced updates produce a reference marginal `p_t = sum_m P_t[m,:N]`. A reverse assignment provides cycle evidence.

**Training signal.** GT-region transport mass, dustbin supervision for non-corresponding parts, bidirectional cycle consistency, hard-negative region ranking, marginal calibration and existing task losses.

**Inference.** Iterative soft assignment remains dense until the final marginal; no external geometry solver.

**Difference from baseline.** Adds explicit part-to-region assignment and missing-part handling.

**Difference from failed PR-MHA.** Multi-part rather than pooled query; differentiable soft assignment rather than hard Top-K; bidirectional cycle verification rather than a scalar prompt-return score.

**Overhead.** `O(BMN)` affinities per refinement and Sinkhorn iterations; manageable for small `M`, but higher than DBTR.

**Difficulty.** High: part construction, dustbin/marginals and numerical stability all require ablation.

**Expected failure mode.** Cross-view appearances may have no stable part correspondence, causing diffuse or semantically spurious transport; novelty overlaps with modern OT/dense matching.

### Candidate 3 — Persistent Anchored Hypothesis Tokens (PAHT)

**Core idea.** Instantiate multiple spatially anchored hypothesis tokens at stage 11, carry their identity and position through stages 12–17, prohibit early mutual suppression, and perform explicit final competition only after accumulated cross-view evidence.

**Why it targets the failure.** A candidate cannot silently disappear: survival, position drift, evidence and confidence are logged per token.

**Changed GAGeo interval.** Add hypothesis tokens and attention masks to late π³ pair-stages; decode a set into final spatial features.

**Tensor flow.** `H_11 in R^(B×K×C)` with anchor coordinates and a dustbin; each late block updates tokens through reference/query cross-attention while diversity and anchor state persist. A final set aggregator produces the task representation.

**Training signal.** Set assignment to GT/distractors, anchor retention, diversity, delayed-ranking and final task losses.

**Inference.** Maintain K candidates until stage 17, then aggregate/select.

**Difference from baseline.** Explicit candidate identities and delayed competition.

**Difference from failed PR-MHA.** This actually persists tokens through late stages; the failed implementation only injected a sparse residual once.

**Overhead.** Attention involving `K` extra tokens; modest for small K.

**Difficulty.** Medium.

**Expected failure mode.** Fixed K still inherits a recall ceiling, and reviewers may view it as a DETR/Cutie-style query bank inserted into GAGeo unless the anti-collapse dynamics are mathematically distinctive.

### Candidate 4 — Coarse-to-Fine Re-anchoring Pyramid (CFRP)

**Core idea.** Preserve a broad stage-11 coarse distribution, then open adaptive local windows around all sufficiently plausible modes. Later stages perform bilateral query/reference refinement and can re-anchor a mode when new evidence contradicts its earlier center.

**Why it targets the failure.** It avoids both a single global winner and a fixed top-K point set; evidence can migrate from approximate semantic regions toward geometrically consistent fine regions.

**Changed GAGeo interval.** Multi-scale reference features and adaptive late-stage windowed matching at stages 11/14/17.

**Tensor flow.** Coarse belief `B×Hc×Wc`; threshold/uncertainty-dependent windows; fine correlations per window; scatter/merge into a final dense field with bilateral consistency.

**Training signal.** Coarse GT-region classification, fine offset/correlation loss, forward/backward consistency, confidence calibration and existing task losses.

**Inference.** Coarse global search followed by adaptive local refinement and re-entry when confidence drops.

**Difference from baseline.** Explicit scale-space search and re-anchoring.

**Difference from failed PR-MHA.** Candidate regions remain expandable and movable; verification is dense/bilateral rather than a one-shot scalar.

**Overhead.** Depends on active windows; potentially efficient but implementation-heavy.

**Difficulty.** High.

**Expected failure mode.** If the correct region is absent from the coarse support, local refinement cannot recover it. The method may look like a direct transplantation of LoFTR/MASt3R/CoMatch.

### Candidate 5 — Intermediate Survival Distillation (ISD)

**Core idea.** Add auxiliary losses that force final spatial logits/features to retain GT-region mass available at stage 11 and penalize harmful rank reversals.

**Why it targets the failure.** It directly improves credit assignment to the diagnosed interval.

**Changed GAGeo interval.** Readout heads at stage 11 and final; no major new inference module.

**Tensor flow.** Stage-wise dense logits share a projector; final logits are supervised by GT and conditionally distilled from intermediate distributions.

**Training signal.** GT NLL, rank-survival and conditional KL.

**Inference.** Baseline path only.

**Difference from baseline/PR-MHA.** Changes the learning objective rather than features/candidates.

**Overhead.** Low at inference; moderate only during training.

**Difficulty.** Low.

**Expected failure mode.** It can preserve wrong intermediate beliefs or merely regularize without changing the transition mechanism. Strong risk of being judged “one more auxiliary loss.” Best used as an ablation/component, not the core method.

### Candidate 6 — Uncertainty-Routed Spatial Experts (URSE)

**Core idea.** Route reference patches through specialist late refiners based on ambiguity, view discrepancy and local confidence, mixing expert outputs with a calibrated router.

**Why it might target the failure.** Ground severe and Drone success plausibly need different update dynamics.

**Changed GAGeo interval.** Replace/wrap late π³ MLP/attention updates with sparse experts.

**Tensor flow.** Per-patch router weights over E experts; top-r routing; merge into spatial field.

**Training signal.** Existing task loss, load balancing, router calibration and optional failure-aware sampling.

**Inference.** Sparse expert execution.

**Difference from PR-MHA.** Learns conditional transition operators rather than correcting selected hypotheses.

**Overhead.** Parameter-heavy; sparse compute.

**Difficulty.** High.

**Expected failure mode.** Router learns task/view shortcuts, experts collapse, and no explicit hypothesis survives. Current evidence does not identify insufficient expert capacity; recent cross-view spatial MoE work creates high novelty collision. Do not prioritize.

### Candidate 7 — Diffusion-Style Spatial Posterior Refinement (DSPR)

**Core idea.** Treat the spatial posterior as a stochastic variable and iteratively denoise multiple belief samples conditioned on query/reference features.

**Why it might target the failure.** Sampling can represent multiple modes without deterministic early collapse.

**Changed GAGeo interval.** Separate iterative belief decoder after stage 11.

**Tensor flow.** Noisy heatmap samples `B×S×H×W` undergo conditional denoising; samples aggregate into calibrated posterior and task features.

**Training signal.** Denoising score loss plus task/ranking/calibration losses.

**Inference.** Multiple denoising steps/samples.

**Difference from PR-MHA.** Represents a distribution through stochastic trajectories rather than eight deterministic candidates.

**Overhead.** High latency/memory.

**Difficulty.** Very high.

**Expected failure mode.** Complexity and stochasticity may not improve correspondence; current evidence does not justify a generative model. Reject as first implementation.

## 6. Reviewer-style comparison matrix

Scores are `1` (weak/low) to `5` (strong/high). For the last two columns, **higher is worse**.

| Candidate | Mechanism alignment | Novelty potential | Technical depth | Evidence support | Feasibility | Ablation clarity | Generalization | Incremental risk ↑ | Collision risk ↑ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Dense Belief-Transport Refinement | **5** | 4 | **5** | **5** | 3 | **5** | **5** | 2 | 3 |
| Query-Part Unbalanced Transport | 4 | 4 | **5** | 3 | 2 | 4 | 4 | 2 | 4 |
| Persistent Anchored Hypothesis Tokens | **5** | 3 | 4 | 4 | 4 | **5** | 4 | 4 | 4 |
| Coarse-to-Fine Re-anchoring Pyramid | 4 | 3 | 4 | 3 | 3 | 4 | 4 | 4 | **5** |
| Intermediate Survival Distillation | 4 | 2 | 2 | 4 | **5** | **5** | 3 | **5** | 4 |
| Uncertainty-Routed Spatial Experts | 3 | 2 | 4 | 2 | 3 | 4 | 3 | **5** | **5** |
| Diffusion-Style Posterior Refinement | 2 | 3 | **5** | 1 | 1 | 3 | 3 | 3 | 4 |

### Strict reviewer objections

**DBTR:** “This is a learned temporal/filtering gate around transformer blocks.” It rises above a patch only if the paper defines a normalized belief-state transition, makes belief survival/calibration measurable, and shows the same principle across failure severities or another iterative correspondence setting. A scalar confidence gate without dense posterior dynamics would collapse back to incremental engineering.

**QPUT:** “This is SuperGlue/Sinkhorn or modern dense matching adapted to cross-view grounding.” It needs a genuinely cross-view partial-part formulation, unbalanced/dustbin semantics, and evidence that cycle transport repairs the measured late collapse rather than merely improving matching.

**PAHT:** “This is DETR queries or video-memory tokens inside GAGeo.” It needs a formal delayed-competition mechanism, candidate birth/re-entry, and trajectory metrics. Fixed tokens plus diversity loss are not enough.

**CFRP:** “This is LoFTR/MASt3R coarse-to-fine matching.” It needs a PSHC-specific re-anchoring rule and direct survival evidence, not just a feature pyramid.

**ISD:** “This is auxiliary deep supervision.” It is suitable as an ablation or a DBTR loss, not as the paper's sole contribution.

**URSE:** “This is a generic MoE.” There is no direct evidence that expert specialization is the missing mechanism, and cross-view sparse-MoE collision is already high.

**DSPR:** “Diffusion is unnecessary complexity.” Without evidence that calibrated stochastic samples outperform a dense deterministic posterior, the cost is unjustified.

### How to elevate the work from patch to principle

The method section should be organized around a general refinement problem:

1. define spatial hypotheses as a probability distribution, not hidden feature similarity;
2. define premature collapse through stage-wise GT mass/rank/calibration;
3. separate **transport**, **new evidence**, and **update trust** mathematically;
4. allow multi-modality and spatial migration;
5. train the transition with stage-wise accountability;
6. show that the mechanism helps severe ambiguous cases without freezing beneficial refinement on successful cases;
7. include PR-MHA as a negative ablation demonstrating that one-shot candidate injection is insufficient.

## 7. Top-2 methods

### Method A — Dense Belief-Transport Refinement (DBTR)

#### Mathematical intuition

Late refinement should approximate sequential Bayesian evidence accumulation, not repeated unconstrained feature overwrite. Let `p_t(n)` be belief that reference patch `n` belongs to the prompted target. A local stochastic operator permits position migration:

```text
pbar_(t+1) = T_t p_t
p_(t+1) = softmax(log(pbar_(t+1) + eps) + tau_t e_(t+1))
```

where `e_(t+1)` is new bidirectional cross-view evidence and `tau_t` is uncertainty-dependent. The baseline pair-stage proposes `F~_(t+1)`; a learned trust map accepts or rejects its update:

```text
a_t = sigmoid(g_t(p_t, p_(t+1), H(p_t), H(p_(t+1)), F~_(t+1)-F_t))
F_(t+1) = F_t + a_t * (F~_(t+1)-F_t)
```

This preserves useful state when evidence is ambiguous but allows large refinement when evidence is consistent.

#### Architecture and insertion

- Initialize dense `p_11` from prompt-conditioned all-reference correlation after pair-stage 11.
- Wrap pair-stages 12–17; the released block still proposes the next feature state.
- Add lightweight local transport, evidence, calibration and update-trust heads.
- Feed controlled final spatial features into unchanged bbox/mask/pose heads.
- Log `p_t` after each late pair-stage.

#### Losses

- `L_belief`: GT-region NLL at each late stage;
- `L_survival`: penalize harmful decreases in GT mass/rank when the earlier state retained the GT;
- `L_wrong_rank`: margin against the strongest wrong region;
- `L_cal`: Brier/NLL or entropy calibration;
- `L_update`: supervise trust from whether the proposed baseline update improves or harms GT margin;
- unchanged GAGeo task losses.

#### Why it may work when PR-MHA did not

It does not bet on eight discrete indices or a single injected correction. The posterior persists, can move, is directly supervised, and controls each actual late update. The intervention therefore has a measurable causal route to the diagnosed stage11→final degradation.

#### Minimal implementation plan

1. Add a config-disabled late-stage wrapper and dense belief initializer.
2. Export per-stage belief mass/rank/entropy without changing evaluation cohorts.
3. Freeze released GAGeo for the first mechanism MVP; train only transport/evidence/trust heads on the same 384 Ground subset.
4. Evaluate the fixed 570 matched samples before any full benchmark.

#### Smallest falsifiable MVP

Use the existing 384 Ground, seed-42, 96-step protocol and fixed 570 mechanism set. The MVP should implement dense state plus controlled updates across stages 12–17; it must not reduce to a read-only probe or a final post-processor.

**Positive signal:** at least two of the pre-existing main conditions improve—Ground-severe H@8 refinement by `>= +0.05`, GT-rank degradation reduced by `>=20%`, return-margin refinement by `>= +0.03`—with Ground-success and Drone-success guardrails intact. In addition, stage-wise GT mass should cease its systematic late decline on the severe cohort.

**NO-GO:** no material mechanism movement despite verified belief losses/gradients and non-trivial update trust; or improvement comes only from freezing late refinement and damages success cohorts. Then the belief-control hypothesis is unsupported at MVP scale.

### Method B — Query-Part Unbalanced Transport (QPUT)

#### Mathematical intuition

Let `U={u_m}` be prompted query foreground/context parts and `V={v_n}` reference patches. Compute costs `C_mn`; solve an entropy-regularized unbalanced transport with a dustbin:

```text
P_t = argmin_P <P,C_t> + eps * H(P) + lambda_q D(P1 || a) + lambda_r D(P^T1 || b)
```

The reference marginal `p_t(n)=sum_m P_t(m,n)` is a spatial belief. A reverse map and cycle loss test whether a reference hypothesis returns to compatible query parts.

#### Architecture and insertion

- Build M query part/context tokens from the Point-prompt region at stage 11.
- Compute soft transport to all reference patches plus dustbin.
- Recompute/refine at stages 14 and 17 with bidirectional evidence.
- Use the final marginal to condition the existing final spatial representation and heads.

#### Losses

- GT-region transport-mass NLL;
- query→reference→query cycle consistency;
- dustbin/missing-part regularization;
- hard-wrong region ranking;
- marginal calibration;
- original task losses.

#### Why it may work when PR-MHA did not

It avoids one pooled descriptor, hard indices and scalar return verification. Partial matching and dustbins explicitly model missing cross-view parts, while differentiable soft assignments retain alternatives.

#### Minimal implementation plan

1. Start with `M=4–8` prompt-conditioned part/context tokens and one unbalanced transport at stage 11 plus one at final.
2. Freeze baseline; train only part/transport heads.
3. Log GT transport mass, cycle score and marginal rank on the fixed 570 set.
4. Add the stage-14 update only if the two-level MVP shows signal.

#### Smallest falsifiable MVP

Same 384/96 training budget, with stage-11 and final soft transport only. Compare against both baseline and hard-Top-K PR-MHA.

**Positive signal:** Ground-severe GT transport mass and final H@8/rank improve under unchanged guardrails, and cycle score separates GT-containing from strongest-wrong regions.

**NO-GO:** transport stays diffuse/un-calibrated, cycle evidence cannot distinguish GT from repeated wrong structures, or task gains occur without reducing stage11→final collapse.

## 8. Recommended method

### Recommendation: implement DBTR first

DBTR is the best first research bet because:

1. **Closest to the evidence.** The measured object is a harmful refinement trajectory; DBTR changes and supervises that trajectory directly.
2. **Avoids the demonstrated top-K ceiling.** It retains all 1,369 reference patches as dense probability support.
3. **Produces a decisive mechanism readout.** Per-stage GT mass, rank, entropy, proposal quality and trust expose whether the claimed mechanism changed.
4. **Not another post-hoc adapter.** It factorizes late refinement into transport, evidence accumulation and controlled state transition.
5. **Bounded implementation.** It wraps stages 12–17 and reuses the released proposal blocks and task heads; it does not replace DINOv2, SAM2 or the full π³ backbone.
6. **Generalizable research claim.** Hypothesis-preserving belief dynamics can apply to iterative cross-view grounding and correspondence systems beyond GAGeo.

QPUT is the second choice because it offers stronger part-level/cycle reasoning, but current evidence has not established that missing partial correspondence is the dominant bottleneck. It also has greater implementation cost and closer novelty collision with OT/dense matching.

### Status of PR-MHA

The **current implementation is formally abandoned** as the main method. Its code/results should remain as a preserved negative experiment. Its broad intuition—avoid premature commitment—survives only after being reformulated as dense, persistent, supervised belief dynamics. It should not be renamed or incrementally tuned into DBTR.

## 9. Minimal falsification experiment

### Research question

Does explicitly transporting a dense spatial belief and using it to control each late π³ update prevent Ground-severe GT recoverability from degrading, without blocking the beneficial refinement seen on successful Ground/Drone samples?

### Fixed baseline and changed variable

- Baseline: released GAGeo checkpoint and existing 570-sample Phase-3B mechanism evaluation.
- Training: official train split only; reuse the exact 384 Ground samples, seed 42, effective batch 4 and 96 optimizer steps from Phase 6B/6B.1.
- Frozen: DINOv2, SAM2, original π³ parameters, original bbox/mask/pose heads.
- Trainable: only DBTR belief initializer, transport/evidence heads and update-trust heads.
- Sole conceptual change: one-shot sparse PR-MHA is replaced by dense persistent belief-controlled stage updates.

### Required logging before training

- checkpoint provenance and exact trainable tensor list;
- gate/trust/evidence/transport gradient norms on one real batch;
- normalized belief sums and all-finite checks;
- effective feature-update ratio per late stage;
- identity check with DBTR disabled.

### Primary mechanism evaluation

On the same fixed cohorts:

- Ground severe: spatial H@1/4/8, GT rank, GT-vs-wrong margin, return margin and per-stage GT belief mass;
- Ground success and Drone success: identical guardrails;
- stage-wise entropy, strongest-wrong mass and accepted/rejected baseline-update quality;
- prediction drift recorded without redefining manifest cohorts.

### Pre-registered decision

**GO** only if at least two hold on Ground severe:

1. H@8 refinement gain improves by `>= +0.05` relative to `-0.1842`;
2. GT-rank degradation is reduced by at least `20%`, to `<= 120.7`;
3. return-margin refinement improves by `>= +0.03` relative to `-0.1258`;

and Ground-success/Drone-success guardrails do not materially fail. A mechanism-specific additional requirement is that GT belief mass is retained through late stages rather than gains appearing only in a terminal head.

**NO-GO** if gradients/execution are verified but the mechanism metrics remain invariant, if the module merely suppresses all refinement, or if severe gains are purchased through clear success-cohort degradation. Do not respond to NO-GO by first increasing epochs.

## 10. Novelty risks / papers that must be checked

Before treating DBTR as a paper-level method, run a line-by-line novelty audit against:

1. uncertainty-aware iterative matching: RoMa, SEA-RAFT, ArgMatch and CoMatch;
2. query competition/delayed suppression: EASE-DETR and later DETR query-dynamics work;
3. persistent object/memory tokens: Cutie, SAM 2 and current video object segmentation memory models;
4. dense belief propagation, differentiable filtering and neural Bayesian update papers from 2024–2026;
5. optimal-transport/cycle correspondence: SuperGlue descendants and 2025 cross-modal spatial correspondence;
6. intermediate self-distillation/preservation: GeoDistill and transformer deep-supervision work;
7. cross-view visual grounding/localization: GAGeo, TROGeo, OCGNet, SMGeo and any 2026 CVPR/ECCV/NeurIPS successors;
8. foundation-feature matching: MATCHA, Mind the Gap, MINIMA, MASt3R and later multimodal matchers.

Precise search queries:

- `"belief propagation" transformer dense correspondence iterative refinement 2024 2025 2026`
- `"hypothesis collapse" visual matching transformer query competition`
- `uncertainty gated feature update dense matching transformer`
- `persistent spatial belief cross-view localization`
- `multi-modal correspondence posterior iterative image matching`
- `Bayesian filtering transformer feature refinement vision`
- `intermediate hypothesis preservation loss correspondence`
- `delayed competition object queries spatial grounding`

Primary novelty risk: reviewers may reduce DBTR to “confidence gating plus auxiliary heatmap losses.” The design must therefore preserve the full factorization—normalized dense belief, spatial transport, evidence fusion, and proposal-dependent state update—and evaluate its stage-wise dynamics. If implementation removes those elements, the claimed principle is no longer present.

Secondary risk: the PSHC cohort may be a symptom of missing cross-view part correspondence rather than destructive update dynamics. QPUT is the planned alternative only if DBTR fails despite demonstrably learning calibrated belief transitions, or if a targeted probe shows that reference belief cannot be updated from existing late features.

No publication claim is frozen. The frozen research decision is narrower: stop tuning PR-MHA and test whether explicit dense belief dynamics can change the already measured failure trajectory under the smallest controlled experiment.

## 11. Problem Scale Audit

> **Status: COMPLETE. Decision: STRONG.** The audit uses the released GAGeo baseline on all 2,180 CMA-Loc `unseen_test` Ground samples with Point Prompt, PR-MHA disabled, and read-only π³ hooks at pair-stages `[4, 11, 17]` plus final spatial output. No training or method intervention is involved.

### 11.1 Provenance

| Item | Verified value |
| --- | --- |
| Unique Ground samples | 2,180 |
| Layer records | 17,440 (`2,180 × 8`) |
| Selection | `all_samples`, `ground_to_satellite` |
| Prompt | `point` |
| PR-MHA | `false` |
| Pair-stage hooks | `[4, 11, 17]` |
| Released checkpoint SHA-256 | `c83a5c5a9611ccf1f523e479dcc195dd5b7d5e7ed939d03a72bab26def3900d1` |
| Dataset JSON SHA-256 | `dac9c58087942e459486c4da875c3f90fb8dcebade4e0d1a52d997c74ba20a53` |
| `layerwise_per_sample.csv` SHA-256 | `3a703685fdf4929be1b3821d9576103225131efaf5277fabb2be1de11e9457aa` |
| `layerwise_summary.json` SHA-256 | `8b39653879db8eac59afbbbeff4f92ab91002b31139a6e6be3d678a0a3365d79` |

Every index has exactly the expected eight records. The following audit uses only `pi3_stage_11_spatial` and `pi3_final_spatial`; object-token Hit@K is not interpreted as a spatial map.

### 11.2 Important global boundary

Late refinement is strongly beneficial on average:

- spatial H@8 rises from `55.50%` to `81.65%` (`+26.15 pp`);
- H@1 rises from `35.41%` to `77.89%`;
- H@4 rises from `48.21%` to `80.14%`;
- mean GT-rank change is nearly neutral (`-0.17`, bootstrap 95% CI `[-6.31, +6.16]`) because large improvements and large degradations coexist;
- mean GT-vs-wrong margin improves by `+0.0961` (95% CI `[+0.0924,+0.0999]`);
- mean return margin improves by `+0.1853` (95% CI `[+0.1733,+0.1977]`).

Therefore the problem is **not** “late π³ refinement is generally harmful.” It is a conditional failure of update selectivity: the same interval helps most Ground samples but destructively changes a meaningful minority.

## 12. Coverage

### 12.1 Full-Ground rank coverage

`delta_rank = final_rank - stage11_rank`; positive means degradation.

| Rank trajectory | Count | Ground proportion |
| --- | ---: | ---: |
| Improved | 1,126 | 51.65% |
| Tied | 719 | 32.98% |
| Worsened | 335 | **15.37%** |

Among all 2,180 Ground samples, degradation magnitude is:

| Positive rank degradation | Count | Ground proportion | Share of worsened set |
| --- | ---: | ---: | ---: |
| 1–20 ranks | 69 | 3.17% | 20.60% |
| 21–100 ranks | 94 | 4.31% | 28.06% |
| >100 ranks | 172 | **7.89%** | **51.34%** |

The median rank change is `-1` with IQR `[-21,0]`, but the worsened tail is heavy: more than half of worsened samples lose over 100 rank positions.

### 12.2 Explicit H@8 loss

The pre-registered destructive set is:

```text
D8 = {stage11 spatial H@8 = 1 and final spatial H@8 = 0}
```

- `|D8| = 116`;
- `116 / 2,180 = 5.32%` of all Ground samples;
- stage 11 contains 1,210 H@8-positive samples, so `116 / 1,210 = 9.59%` of initially recoverable H@8 cases lose that status;
- the reverse transition is much more common: 686 samples (`31.47%`) gain H@8.

Thus destructive H@8 refinement is a minority path embedded inside a generally successful refiner, but it is not confined to the 190 severe examples.

### 12.3 Hit@K and margin coverage

| Metric | Stage 11 | Final | Change |
| --- | ---: | ---: | ---: |
| Spatial H@1 | 35.41% | 77.89% | +42.48 pp |
| Spatial H@4 | 48.21% | 80.14% | +31.93 pp |
| Spatial H@8 | 55.50% | 81.65% | +26.15 pp |

Despite positive aggregate changes:

- GT-vs-wrong margin worsens for 309/2,180 (`14.17%`), while improving for `85.83%`;
- return margin worsens for 535/2,180 (`24.54%`), while improving for `75.46%`.

This confirms that mean metrics alone hide a destructive minority trajectory.

### 12.4 Continuum by final performance

Performance strata are fixed from final runtime outputs using the original definitions:

- severe: `det_iou=0 and mask_iou=0`, `N=190`;
- moderate: neither severe nor success, `N=265`;
- success: `det_iou>=0.5 and mask_iou>=0.5`, `N=1,725`.

| Cohort | Rank worsened | >100-rank degradation | H@8 lost | GT-margin worsened | Return-margin worsened |
| --- | ---: | ---: | ---: | ---: | ---: |
| Severe | **72.63%** | **42.11%** | **24.74%** | 51.05% | **64.21%** |
| Moderate | **38.87%** | **15.85%** | **15.85%** | 24.91% | **40.75%** |
| Success | 5.45% | 2.90% | 1.57% | 8.46% | 17.68% |

The rank and H@8 trajectories reinforce this ordering:

| Cohort | Stage11 H@8 | Final H@8 | H@8 change | Mean rank change | Mean return-margin change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Severe | 31.58% | 13.16% | **-18.42 pp** | **+150.91** | **-0.1258** |
| Moderate | 49.06% | 55.85% | +6.79 pp | **+28.67** | +0.0531 |
| Success | 59.13% | 93.16% | +34.03 pp | -21.25 | +0.2399 |

The phenomenon forms a clear performance continuum. Moderate cases remain mixed: their aggregate H@8 improves, yet 38.87% lose GT rank, 15.85% lose H@8, and mean rank worsens by 28.67 (95% CI `[+10.09,+47.72]`). Severe cases show the strongest destructive trajectory; success cases overwhelmingly benefit, but a small residual destructive subset still exists.

**Conclusion:** destructive refinement is concentrated toward poor final performance but is not only a severe-tail artifact.

## 13. Oracle Impact Ceiling

### 13.1 Strict task-oracle boundary

The stage-11 diagnostic is an oracle-mask-pooled spatial correspondence measurement, not a stage-11 bbox/mask prediction. The released heads are trained for final features. A strict stage-11 task oracle therefore cannot be computed without inventing an out-of-distribution decoder path, and none is reported.

### 13.2 Pre-registered D8 restricted optimistic ceiling

The proxy changes only samples in the pre-registered `D8` set. Each D8 sample is granted perfect detection/mask recovery (`IoU=1`); every other final prediction is unchanged:

```text
oracle_det_iou_i = 1.0       if i in D8
                   det_iou_i otherwise
```

D8 composition:

- severe: 47;
- moderate: 42;
- success: 27;
- total: 116.

| Metric | Current | D8 restricted optimistic ceiling | Absolute ceiling |
| --- | ---: | ---: | ---: |
| Ground detection mIoU | 73.590% | 77.457% | **+3.867 pp** |
| Ground Acc@0.50 | 81.284% | 85.183% | **+3.899 pp** |
| Ground Acc@0.75 | 72.752% | 77.110% | **+4.358 pp** |
| Ground severe failure rate | 8.716% | 6.560% | **-2.156 pp** |

The severe ceiling corresponds to removing 47/190 severe failures, a maximum relative reduction of `24.74%` within this restricted recoverable set.

This is a **ceiling, not an expected method gain**. It is conservative about eligibility because it ignores rank degradation that does not cross H@8, but optimistic about payoff because every eligible sample is made perfect. It establishes that the clearest measured collapse subset has non-trivial benchmark headroom; it does not establish that DBTR/QPUT can realize it.

## 14. Continue / Abandon Decision

### 14.1 Final grade: STRONG

Both pre-registered gates are satisfied:

1. **Coverage:** 335/2,180 (`15.37%`) lose GT rank, 172 (`7.89%`) lose over 100 positions, and 116 (`5.32%`) undergo explicit H@8 loss. Severe→moderate→success degradation rates show a strong monotonic continuum rather than a severe-only anomaly.
2. **Impact ceiling:** even the restricted D8 set carries ceilings of approximately `+3.87 mIoU`, `+3.90 Acc@0.50`, `+4.36 Acc@0.75`, and `-2.16 pp` severe failure rate.

### 14.2 Research decision

> **Continue Premature Spatial Hypothesis Collapse as the GAGeo CVPR-level limitation.**

The claim must remain conditional: π³ late refinement is beneficial overall, but it lacks update selectivity under ambiguous Ground→Satellite conditions and catastrophically suppresses a meaningful subset of otherwise recoverable spatial hypotheses. A valid method must selectively protect this subset without reducing the large gains enjoyed by successful samples.

This STRONG label approves continued mechanism-driven method research; it does not approve DBTR or QPUT specifically, and it is not evidence that either candidate will work.

## Method re-ranking checkpoint after full-Ground audit

> Sections 15–18 supersede the pre-audit recommendation and MVP in Sections 8–9. DBTR and QPUT remain preserved as candidate-history records; neither is authorized for implementation in its earlier form.

### 15.1 Updated name and definition

The full-Ground audit requires a narrower and more accurate formulation than unconditional hypothesis preservation:

> **Conditional Destructive Late Refinement (CDLR):** π³ late refinement substantially improves spatial localization for most Ground→Satellite samples, but for a condition-dependent minority it assigns negative refinement utility—suppressing or reordering already plausible spatial hypotheses and producing a heavy rank-degradation tail.

Premature Spatial Hypothesis Collapse remains the observable failure event inside CDLR; it is no longer the complete method framing. The central research question becomes:

> Can a model estimate the expected utility and uncertainty of each late spatial update, accept aggressive refinement when it is reliable, and conservatively retain/transport prior belief only when the proposed update is likely destructive?

### 15.2 Evidence, interpretation and missing gate

**Evidence:** late refinement improves GT rank for 51.65% of all Ground samples, ties for 32.98%, and worsens it for 15.37%. It increases overall H@8 by 26.15 points, yet 116 samples lose stage-11 H@8 support. Worsening rates form a severe→moderate→success gradient of 72.63%→38.87%→5.45%.

**Interpretation:** one shared late transition behaves differently across input conditions; a uniformly conservative intervention would discard substantial useful capacity.

**Hypothesis, not yet evidence:** destructive updates are predictable from inference-time observables such as spatial entropy, competing-mode margin, cross-view cycle/return agreement, update magnitude and cross-stage disagreement. The existing CSV contains outcome labels and oracle diagnostic scores, but it does not prove label-free risk predictability.

This is now the mandatory pre-implementation gate. A reliability-aware method is not justified merely because destructive cases exist; it must have a usable, calibrated risk signal before the harmful update is committed.

### 15.3 Updated method requirements

A valid method must:

1. preserve the released π³ proposal path and allow near-baseline/aggressive updates on predicted-positive-utility samples;
2. estimate update utility, not treat generic low confidence as synonymous with failure;
3. act per stage and per spatial hypothesis/region, not through one global sample gate;
4. keep dense or re-enterable support for uncertain modes rather than fixed Top-K truncation;
5. supervise both acceptance of beneficial proposals and rejection/attenuation of destructive proposals;
6. report calibration, selective risk and success-cohort regret in addition to average localization metrics;
7. be config-disableable and checkpoint-compatible with the released baseline.

### Method re-ranking

### 16.1 Status of original DBTR

**DBTR v1: MODIFY, not implement unchanged.** Its dense persistent belief and proposal-aware trust map remain useful, but its earlier narrative emphasized survival/preservation. If `L_survival` is applied uniformly, DBTR can over-protect the 51.65% of Ground samples whose rank improves and inhibit the 26.15-point overall H@8 gain.

DBTR is retained only as a substrate for an asymmetric objective:

- accept and closely reproduce the π³ proposal when its utility is positive;
- attenuate, transport around, or preserve prior belief when predicted utility is negative or uncertain;
- penalize both destructive acceptance **and** beneficial-update rejection.

### 16.2 Candidate 1 — Reliability-Conditioned Belief Refinement (RCBR)

**Core idea.** Maintain a dense spatial belief, let every released late π³ block produce its normal proposal, and learn a calibrated, spatially varying predictor of the proposal's expected utility. The controller blends prior and proposed states per hypothesis rather than globally preserving or globally refining.

**Destructive-risk estimate.** At stage `t`, predict continuous utility `u_hat_t(n)` and epistemic/aleatoric uncertainty `sigma_hat_t(n)` from inference-visible signals: current/proposed spatial logits, entropy and multi-modality, top-mode gaps, prompt-return/cycle agreement, query/reference evidence agreement, and feature-update magnitude. GT masks/ranks are used only to construct training targets.

**Normal-sample behavior.** When predicted utility is positive and uncertainty is low, acceptance `alpha_t(n)` approaches one, so the original π³ proposal passes through with minimal regret.

**High-risk behavior.** Where utility is negative or uncertain, acceptance decreases only around affected hypotheses; prior belief is locally transported rather than frozen, retaining re-entry and allowing later evidence to reverse the decision.

**Uncertainty/confidence.** Explicit and calibrated. Confidence is not a free scalar score: it predicts the sign/magnitude of counterfactual refinement utility.

**Intermediate supervision.** Required. For training GT region `Y`, define proposal utility from the change in GT log-mass/rank surrogate between current and proposed states. Supervise utility regression/classification, calibration, beneficial-proposal acceptance and harmful-proposal rejection at each late stage.

**Persistent hypotheses.** Yes, as a normalized dense belief over reference patches; no irreversible fixed Top-K.

**Why it is not merely a GAGeo patch.** The object is a general iterative-inference transition: estimate proposal utility under uncertainty, then selectively accept the update. The same formulation applies to iterative matching, grounding and correspondence models.

**Difference from PR-MHA.** PR-MHA made one hard-Top-K sparse correction before frozen late dynamics and had no utility targets. RCBR evaluates each actual baseline update, retains dense state, and is directly supervised to accept good updates as well as reject bad ones.

**Relation to DBTR.** A strict upgrade: DBTR supplies belief transport; RCBR changes the core from preservation to calibrated selective update utility.

**Smallest method MVP.** After the risk-predictability probe passes, wrap stages 12–17 with a shared lightweight utility/trust head, freeze the released model, train only belief/utility/control parameters, and evaluate the fixed 2,180 Ground trajectories plus the 570 matched guardrails.

**NO-GO.** Risk is predictable but controlled updates do not reduce D8/rank degradation; or they improve the tail by materially reducing success H@8/return margin; or the controller simply learns `alpha≈0`/`alpha≈1` everywhere.

### 16.3 Candidate 2 — Dual-Trajectory Risk-Selective Refinement (DTR)

**Core idea.** Preserve the exact aggressive π³ trajectory as the default and instantiate a second conservative, dense-belief trajectory only for uncertain samples/regions. A calibrated verifier later selects or fuses the trajectories.

**Destructive-risk estimate.** A lightweight router uses stage-11 ambiguity and early late-stage disagreement. The most informative signal is divergence between aggressive and conservative trajectories combined with bidirectional prompt/reference consistency.

**Normal-sample behavior.** Low-risk samples execute or select the unchanged aggressive path; this offers the strongest architectural guardrail for the 51.65% improved population.

**High-risk behavior.** High-risk regions retain a conservative branch with transported multi-modal belief; final verification can roll back from a destructive aggressive state.

**Uncertainty/confidence.** Explicit in the router and final selector; branch disagreement provides a model-based uncertainty estimate.

**Intermediate supervision.** Required for router/selector utility and branch regret. The aggressive branch itself remains frozen.

**Persistent hypotheses.** Only in the conservative branch; the baseline branch remains unchanged.

**Why it is not merely GAGeo-specific.** It is a conditional-computation/anytime-refinement formulation applicable when iterative models have positive average utility but heavy negative-regret tails.

**Difference from PR-MHA.** It never overwrites the only state with a one-shot correction. The successful baseline trajectory remains available, and an alternative state survives until evidence resolves the choice.

**Relation to DBTR.** DBTR can serve as the conservative branch, but DTR's main contribution is dual-trajectory routing and regret-aware selection rather than belief filtering itself.

**Smallest falsifiable MVP.** Compute an unchanged aggressive final state and one lightweight conservative trajectory from stage 11; train only a selector on official train Ground samples. Test whether the selector approaches an oracle choice without harming baseline-success cases.

**NO-GO.** Branch disagreement does not predict which path is better; selected outputs do not beat the aggressive baseline; or conditional compute approaches two full late passes without enough tail gain.

### 16.4 Candidate 3 — Cycle-Consistent Selective Transport (CCST)

**Core idea.** Replace learned generic risk with correspondence-derived reliability. Maintain a soft, unbalanced query-part→reference transport; use reverse transport/cycle consistency to decide whether evidence is reliable enough to sharpen the spatial marginal.

**Destructive-risk estimate.** High forward entropy, low transported mass, poor reference→query cycle return, disagreement across query parts and unstable marginals across stages indicate destructive-refinement risk.

**Normal-sample behavior.** Strong bilateral cycle agreement lowers temperature and permits aggressive concentration/refinement.

**High-risk behavior.** Weak or contradictory cycles retain a broad marginal, allocate unmatched parts to a dustbin, and prevent a visually plausible single distractor from dominating.

**Uncertainty/confidence.** Explicit, derived from transport entropy, unmatched mass and cycle residual rather than only an MLP confidence score.

**Intermediate supervision.** GT-region transport mass and task losses are required; cycle consistency can also supply a label-free training signal.

**Persistent hypotheses.** Yes, as a soft transport marginal over all reference patches.

**Why it is not merely GAGeo-specific.** The method is a general partial-correspondence reliability mechanism for severe appearance/viewpoint change.

**Difference from PR-MHA.** Differentiable dense assignment, multiple query parts, dustbin support and bilateral verification replace pooled-query hard Top-K and scalar return scoring.

**Relation to DBTR.** Alternative rather than extension: CCST defines reliability from assignment/cycle structure; DBTR/RCBR learns update utility over π³ proposals.

**Smallest falsifiable MVP.** Add stage-11 and final soft transports only, freeze GAGeo, and test whether label-free cycle reliability predicts D8 and whether transport marginal retains GT mass. Do not yet alter every late block.

**NO-GO.** Cycle signals cannot separate D8 from beneficial cases, transport remains diffuse, or apparent correspondence improvements fail to move final spatial/task metrics.

### 16.5 Reviewer-style ranking

Scores are `1` (weak) to `5` (strong); for risk columns, higher is worse.

| Candidate | Evidence alignment | Explains conditionality | Success protection | Novelty potential | Technical depth | Feasibility | Falsifiability | Incremental risk ↑ | Collision risk ↑ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **RCBR** | **5** | **5** | 4 | 4 | **5** | 3 | **5** | 2 | 3 |
| **DTR** | **5** | **5** | **5** | 4 | 4 | 3 | 4 | 3 | 4 |
| **CCST** | 4 | 4 | 4 | 4 | **5** | 2 | 4 | 2 | **5** |

Reviewer objections:

- **RCBR:** “This is just confidence gating.” It becomes principled only if confidence predicts counterfactual update utility, acts per spatial hypothesis across iterative stages, is calibrated, and is evaluated with selective risk/regret—not merely with average accuracy.
- **DTR:** “This is an ensemble or mixture-of-experts.” It needs conditional execution, an explicit refinement-regret objective, and evidence that branch disagreement predicts harmful updates; otherwise it is expensive redundancy.
- **CCST:** “This is an OT matcher transplanted into GAGeo.” It needs to show that cycle-derived reliability specifically controls harmful refinement while preserving positive π³ utility, not simply improve generic correspondence.

### Recommended method v2

### 17.1 Recommendation

> **Recommend RCBR, conditional on first passing the risk-predictability probe.**

Do not implement original DBTR unchanged. Retain dense belief transport, but make the core contribution **reliability-conditioned selective refinement**.

### 17.2 Core formulation

Let the frozen late π³ stage propose:

```text
F_tilde_(t+1) = Phi_t(F_t, Q_t)
```

Let `p_t` be the persistent dense spatial belief and `p_tilde_(t+1)` the belief implied by the proposal. Predict proposal utility and uncertainty from label-free observables `z_t(n)`:

```text
(u_hat_t(n), sigma_hat_t(n)) = R_theta(z_t(n))
alpha_t(n) = sigmoid((u_hat_t(n) - kappa * sigma_hat_t(n)) / T)
p_(t+1) = Normalize(alpha_t * p_tilde_(t+1) + (1-alpha_t) * Transport_t(p_t))
F_(t+1) = F_t + alpha_t * (F_tilde_(t+1) - F_t)
```

`alpha_t` is spatial/hypothesis-conditioned, not one global gate. Normal samples can retain `alpha≈1`; only uncertain negative-utility regions receive conservative updates.

Training constructs a counterfactual utility target using GT only as supervision:

```text
u*_t = Quality(p_tilde_(t+1), Y) - Quality(p_t, Y)
```

where `Quality` combines differentiable GT log-mass and hard-wrong margin. Losses must be asymmetric:

- utility regression/sign classification and calibration;
- accept beneficial proposals (`u*_t > delta`);
- reject/attenuate destructive proposals (`u*_t < -delta`);
- preserve dense belief only in destructive/uncertain regions;
- baseline-consistency/regret loss on positive-utility cases;
- unchanged task losses.

### 17.3 Why RCBR ranks first

1. It directly models the newly observed asymmetry: positive mean utility with a heavy negative-utility tail.
2. It gives success cases an explicit acceptance target instead of treating preservation as universally desirable.
3. It retains DBTR's dense support and avoids PR-MHA's top-8 ceiling.
4. It tests a general scientific claim—whether update utility is predictable and controllable—rather than a GAGeo-specific adapter choice.
5. Every claim has an observable diagnostic: utility AUROC/AUPRC, calibration, acceptance by true utility, D8 retention and success regret.

Main risk: the destructive subset may be identifiable only with GT-dependent signals and not from inference-time observables. That risk is why no controller implementation should begin before the probe below.

### Previous minimal falsification proposal

### 18.1 First experiment: frozen refinement-utility predictability probe

This is the next experiment before RCBR implementation. It does not change GAGeo outputs and does not train a localization model.

**Research question:** can label-free stage-11/late-transition observables predict whether released π³ refinement will be destructive?

**Data:**

- extract risk descriptors from a deterministic official-train Ground subset; GT is used only to label refinement utility;
- fit a linear/logistic probe first, with a very small MLP only as a capacity ablation;
- evaluate once on all 2,180 `unseen_test` Ground samples;
- never train on `unseen_test` and never use oracle GT rank/margin as probe inputs.

**Pre-registered observable inputs:**

- normalized spatial entropy and number/effective mass of competing modes;
- top-1/top-2 and top-1/top-K score gaps;
- prompt→reference→prompt return/cycle consistency;
- agreement between prompt-token, query-spatial and object-token evidence;
- proposal update norm and spatial distribution shift/KL between adjacent late stages;
- spatial concentration/dispersion and cross-stage rank-free peak stability.

**Targets:**

- binary D8 label;
- binary sign of GT-rank or GT-mass utility;
- continuous GT log-mass/hard-wrong-margin change.

**Positive signal / GO to RCBR implementation:**

- D8 AUROC `>=0.70`;
- D8 AUPRC at least `2×` its 5.32% test prevalence;
- highest-risk 20% captures at least 50% of D8 samples;
- calibration ECE `<=0.10` after train-only calibration;
- risk score also orders severe→moderate→success without using those labels as input.

**NO-GO:** AUROC `<0.60`, AUPRC enrichment `<2×`, or high-risk selection cannot capture D8 without flagging most successful samples. In that case, do not implement RCBR; prefer CCST only if cycle-derived reliability shows a stronger label-free signal, otherwise revisit the limitation mechanism.

### 18.2 Why this is the smallest decisive experiment

RCBR, DTR and CCST all assume that harmful updates can be recognized before or while they occur. The probe tests that shared assumption without confounding it with a new refinement architecture. A PASS justifies implementing one controller; a FAIL prevents another costly adapter cycle.

## 15. RCBR Premise Validation

**Status: PRE-REGISTERED; frozen feature extraction and probe fitting have not started.**

The premise being tested is deliberately narrower than the RCBR method:

> Can D8 destructive late refinement be predicted from information already available at or before pair-stage 11, before stages 12--17 and the final prediction are observed?

The binary target is fixed as:

```text
label_d8 = 1[stage11_spatial_H@8 = 1 and final_spatial_H@8 = 0]
```

The released GAGeo checkpoint remains frozen. D8 may use the oracle GT region to construct the supervision label, but no GT-derived, post-stage-11, or final-output quantity may enter the predictor. This experiment trains only an offline linear risk probe; it does not train or implement RCBR and does not alter GAGeo inference.

## 16. Data Leakage Audit

### 16.1 Frozen split protocol

| Role | Official metadata | Ground count | D8 count / prevalence | Allowed use |
| --- | --- | ---: | ---: | --- |
| Probe training | `train_all.json` | **95,681 verified** | **pending frozen export** | Fit scaler and linear-probe weights only |
| Selection/calibration | `val_all.json` | **12,166 verified** | **pending frozen export** | Select feature family, `C`, class weighting, calibration, and decision threshold |
| Frozen final evaluation | `unseen_test.json` | **2,180 verified** | **116 / 2,180 = 5.32% verified** | One final report after all choices are frozen |

The NSCC split audit passed against official metadata: train `191,423` total / `95,681` Ground, validation `23,927` total / `12,166` Ground, and unseen-test `4,197` total / `2,180` Ground. Train/validation D8 prevalences still require frozen export and cannot be stated yet. No unseen-test statistic may be used to choose features, hyperparameters, calibration, or threshold; its known prevalence is used only to state the already frozen PASS criterion.

The official train loader samples a random satellite crop, whereas validation and unseen-test use fixed pre-cropped satellite images. For a reproducible train export, crop randomness must be frozen per stable sample identifier (fixed base seed plus original metadata index), and the seed/crop offset must be recorded. This is an extraction-control change, not a forward change.

To prevent validation reuse from contaminating calibration, official validation Ground will be divided deterministically into `val_select` and `val_calibrate` after export with a fixed seed and stratification by D8 label. `val_select` chooses the small model grid; `val_calibrate` fits probability calibration and selects the reporting threshold. Both remain entirely separate from unseen-test.

### 16.2 Predictor provenance and leakage table

| Feature / field | Source | Available when inference reaches stage 11? | Label-derived? | Leakage decision |
| --- | --- | --- | --- | --- |
| Point-conditioned stage-11 score-map statistics | Point prompt + stage-11 query/reference spatial patches | Yes | No | **ALLOW** |
| Stage-11 task-token/reference score-map statistics | Stage-11 learnable task token + reference spatial patches | Yes | No | **ALLOW** |
| Stage-4 to stage-11 score-map stability | Pair-stages 4 and 11 | Yes | No | **ALLOW** |
| Agreement between the two stage-11 evidence maps | Stage 11 | Yes | No | **ALLOW** |
| Prompt-local query feature contrast | Point prompt + stage-4/11 query spatial patches | Yes | No | **ALLOW** |
| Query/reference global similarity summaries at stage 11 | Stage-11 query/reference patches | Yes | No | **ALLOW** |
| GT rank, GT Hit@K, GT-vs-wrong margin at stage 11 | Stage 11 + GT region | No, requires GT | Yes | **LABEL/ANALYSIS ONLY** |
| Stage-12--17 features or transition statistics | After stage 11 | No | No | **FORBID** |
| Final spatial feature or any final score statistic | Final | No | No | **FORBID** |
| Final bbox/mask/position/rotation or derived confidence/error | Final heads | No | Possibly | **FORBID** |
| Final GT rank / Hit@K and `label_d8` | Stage 11 + final + GT | No | Yes | **SUPERVISION ONLY** |
| Severe/moderate/success cohort or final IoU | Final prediction + GT | No | Yes | **EVALUATION ONLY** |

Every predictor column must have the prefix `feature_`. Supervision/evaluation columns must have `label_` or `audit_`. The probe loader must consume an explicit feature whitelist and fail if any final-, GT-, label-, IoU-, cohort-, or stage-12--17-derived column appears in the design matrix.

## 17. Risk Feature Definition

The first probe uses a small, fixed, GT-independent feature family. It does not search over dozens of post-hoc statistics.

### 17.1 Inference-time score maps

Construct two normalized reference-patch score maps without GT:

1. `P_point_11`: pool the stage-11 query/front patches around the provided Point Prompt with a fixed local kernel, then cosine-match this prompt-conditioned query descriptor to all stage-11 reference/satellite patches;
2. `P_task_11`: cosine-match the inference-available stage-11 learnable task token to all stage-11 reference patches.

Build the corresponding prompt-conditioned map `P_point_4` at pair-stage 4. The Point Prompt is an input available at inference; the GT query mask currently used by the Phase 3B diagnostic must not be used for these maps.

### 17.2 Pre-registered scalar feature whitelist

For `P_point_11`:

- `feature_point11_entropy_norm`;
- `feature_point11_top1_top2_gap`;
- `feature_point11_top1_top8_gap`;
- `feature_point11_top8_mass`;
- `feature_point11_peak_zscore`;
- `feature_point11_top8_spatial_dispersion`.

Cross-evidence agreement at stage 11:

- `feature_point_task11_js_divergence`;
- `feature_point_task11_top8_overlap`;
- `feature_point_task11_peak_distance_norm`.

Stage-4 to stage-11 stability:

- `feature_point4_11_js_divergence`;
- `feature_point4_11_top8_overlap`;
- `feature_point4_11_peak_distance_norm`.

Prompt/query evidence quality:

- `feature_prompt_local_global_cosine_11`;
- `feature_prompt_local_feature_norm_11`;
- `feature_reference_feature_norm_mean_11`.

This is a fixed 15-dimensional input. Entropy and mass use a fixed temperature selected on `val_select`; all spatial distances are normalized by the reference feature-grid diagonal. Feature definitions, tensor shapes, temperature, and crop provenance must be written into the export metadata before unseen-test probe evaluation.

## 18. Linear Probe Protocol

1. Run the released GAGeo baseline in evaluation mode and export the fixed 15-dimensional features plus separately namespaced labels for official train, validation, and unseen-test Ground samples with Point Prompt.
2. Fit missing-value handling and standardization on official train Ground only. Any non-finite feature is a hard error rather than silently imputed from test statistics.
3. Fit L2 logistic regression. Use a pre-registered small grid `C in {0.01, 0.1, 1, 10}` and compare unweighted versus train-derived balanced class weights on `val_select` only.
4. Choose the model by validation AUPRC, with AUROC as the deterministic tie-breaker. No nonlinear probe is part of the premise gate.
5. Fit Platt calibration on `val_calibrate` only. Choose the confusion-matrix threshold on `val_calibrate` by maximum F1; the top-risk-20% statistic remains threshold-free.
6. Freeze the feature schema, preprocessing, model, calibrator, and threshold; then evaluate once on all 2,180 unseen-test Ground samples.
7. Report AUROC, AUPRC, D8 prevalence, AUPRC/prevalence, top-risk-20% D8 coverage, ECE, the confusion matrix at the frozen validation threshold, and D8/non-D8 risk median, IQR, and quantiles.

The existing `run_phase3b_layerwise.py` cannot execute this protocol unchanged: it is hard-coded to official `unseen_test`, asserts 4,197 total records / 2,180 selected Ground records, and its current query descriptor uses GT-mask pooling. The companion `export_rcbr_frozen_features.py` therefore reuses released-checkpoint loading and read-only stage hooks, supports official `train`/`val`/`unseen_test`, performs deterministic train cropping, and writes strictly separated `feature_*`, `label_*`, and `audit_*` columns. It does not alter the Phase 3B runner, model forward, or metric definitions.

## 19. PASS / FAIL Criteria

After every choice is frozen on train/validation, the RCBR premise passes only if the single unseen-test evaluation satisfies **all** of:

- `AUROC >= 0.70`;
- `AUPRC >= 2 * unseen_test_D8_prevalence` (with current verified prevalence `0.0532`, threshold approximately `0.1064`);
- the highest-risk 20% of all 2,180 Ground samples cover at least 50% of D8 samples;
- `ECE <= 0.10`.

The confusion matrix and D8/non-D8 distributions are mandatory reports but do not replace any gate. If any criterion fails, `RCBR premise = NO-GO` and RCBR architecture implementation must not proceed. If all pass, `RCBR premise = GO`; this authorizes only the pre-registered RCBR MVP, not a full benchmark.

Current decision: **NOT YET EVALUATED.** No probe result or RCBR premise conclusion exists at this checkpoint.
