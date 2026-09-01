# 11 — Limitation

> **Status：FROZEN after Phase 3B full-sample diagnosis。** Evidence：released-checkpoint inference on the fixed 570-sample Point-Prompt matched cohort，including all 190 Ground severe cases。

## Defensible limitation statement

> **GAGeo 在 Ground→Satellite、尤其目标较小且 reference 中存在重复建筑实例时，π³ stage 11 之后的 late spatial refinement 不能稳定保留和验证仍然可行的 GT 空间假设，反而会把空间证据重排到一个语义合理但错误的 reference instance；最终共享 spatial representation 因而同时驱动 bbox 与 mask 落到错误区域，造成 zero-overlap catastrophic failure。**

## Frozen definition

1. **Failure condition**：Ground→Satellite Point-Prompt tail，especially small/repetitive urban targets；
2. **Module interval**：after π³ pair-stage 11 and before `pi3_final_spatial`；
3. **Observed mechanism**：GT spatial recoverability、rank and prompt-return evidence degrade while a coherent wrong instance becomes the final anchor；
4. **Why baseline cannot handle it**：the released late-refinement path jointly updates one spatial field but has no explicit top-K spatial candidate identity、survival objective or candidate-level verification before bbox/mask decoding；
5. **Supporting evidence**：570 released-checkpoint samples，matched-stratified Ground comparison，and all 190 severe panels；
6. **Remaining uncertainty**：the exact block in stages 12–17，larger-K recoverability，and independent annotation certification。None blocks a stage-11 MVP。

Small-object scale is an amplifier，not the complete mechanism：the Ground gap survives informative size×shape strata。The limitation is specifically a **late spatial hypothesis preservation/verification failure**，not generic domain gap and not proven DINOv2-resolution failure。

## Code correspondence

1. `GeometryPromptEncoder` encodes query prompt；
2. `Pi3Backbone.decode_with_extra_tokens` lets prompt affect query features and performs global interaction；
3. the diagnosed divergence occurs after pair-stage 11 and before `pi3_final_spatial`；
4. default model has no explicit mechanism that preserves multiple spatial candidates through that interval；
5. `CrossViewLocalizer.forward` sends the selected shared representation to `BBoxHead` and `SAMMaskHead`，with no candidate-verification or abstention path。

π³ global attention can represent many correspondences internally，but the released task interface does not explicitly preserve、supervise and verify multiple spatial alternatives before decoding。The released diagnostic does not expose stage-17 spatial patches，so it cannot identify the exact first pair-stage among 12–17。

## Why this limitation is intervention-ready

- It explains a tail failure rather than only a mean gap；
- It predicts coupled bbox/mask failures because both read the same selected task representation；
- It predicts stronger impact for Small/repetitive targets where alternative instances are harder to separate；
- It suggests a localized intervention：preserve top-K spatial hypotheses、verify them against the original prompt/context、then apply a gated correction to the existing bbox/mask inputs；
- it keeps original bbox/mask heads and evaluation definitions unchanged，making ablation clear。

Full-sample evidence：Ground severe spatial H@8 changes from `0.3158` at stage 11 to `0.1316` at final，while matched Ground success changes `0.4421→0.9158` and Drone success `0.7895→0.9684`。Ground severe GT rank worsens by `+150.91` on average and return margin drops by `-0.1258`（95% bootstrap CI `[-0.1681,-0.0849]`）。All 190 severe panels are visually compatible with a coherent wrong-instance/spatial anchoring outcome rather than boundary-only segmentation error。

## Scope boundary

This limitation does **not** claim：

- DINOv2 resolution is proven sufficient；
- a particular pair-stage between 12–17 is causally responsible；
- late refinement is the sole cause of all 190 failures（68.4% already have GT outside stage-11 top-8）；
- all Ground failures are independently certified model errors rather than annotation errors；
- additional generic learnable queries solve the problem。The paper's generic query-count ablation is not equivalent to spatially anchored and independently verified hypotheses。

The limitation is supported at module-interval resolution and is intervention-ready。Exact stage 12–17 attribution remains unresolved and should be treated as an ablation variable，not silently inferred。
