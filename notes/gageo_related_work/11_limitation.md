# 11 — Limitation

## Defensible limitation statement

> **GAGeo 在 Ground→Satellite、尤其 Small-target 条件下，由于当前 `query prompt → query patches → π³ global interaction → single object-task token` 路径缺少显式的多假设 reference anchoring 与错误候选验证机制，会在少数强视角歧义样本中提前压缩到一个语义合理但错误的 reference instance/region，导致 bbox 与 mask 一致性的 catastrophic zero-overlap failure。**

## Code correspondence

1. `GeometryPromptEncoder` encodes query prompt；
2. `Pi3Backbone.decode_with_extra_tokens` lets prompt affect query features and performs global interaction；
3. default model uses one bbox/mask object query；its position is not tied to a concrete reference patch；
4. `CrossViewLocalizer.forward` sends that shared object query to both `BBoxHead` and `SAMMaskHead`；
5. evaluator selects one final query/hypothesis and has no candidate-verification or abstention path。

π³ global attention can represent many correspondences internally，but the released task interface does not explicitly preserve、supervise and verify multiple spatial alternatives before decoding。

## Why this limitation is intervention-ready

- It explains a tail failure rather than only a mean gap；
- It predicts coupled bbox/mask failures because both read the same selected task representation；
- It predicts stronger impact for Small/repetitive targets where alternative instances are harder to separate；
- It suggests a localized intervention：preserve top-K spatial hypotheses、verify them against the original prompt/context、then fuse the verified context into the object token；
- it keeps original bbox/mask heads and evaluation definitions unchanged，making ablation clear。

## Scope boundary

This limitation does **not** claim：

- DINOv2 resolution is proven sufficient；
- a particular π³ attention layer is causally responsible；
- all Ground failures are model errors rather than annotation errors；
- additional generic learnable queries solve the problem。The paper's generic query-count ablation is not equivalent to spatially anchored and independently verified hypotheses。

The limitation is supported as a model-interface behavior。Exact layer attribution remains a Phase-3.1 diagnostic before implementation。
