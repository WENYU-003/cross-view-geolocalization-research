# GEO-1 Minimal Falsification Report

## Evidence status

Result-file-confirmed offline analysis of 295 Scene_16 satellite queries and 1,475 saved candidate records. No model, matcher, DSM, PnP, or training run was executed.

## Primary result (`tau=0 m`, inlier ratio `>=0.3`)

- Retrieval Top-1 identity accuracy: 52.20% (154/295).
- Selected identity accuracy: 57.29% (169/295).
- Downstream candidate identity increment: +5.08 pp.
- Geometry-mediated rescue: 69.00% (69/100), Wilson 95% CI [59.37%, 77.22%].
- Rescued cases with final error <=3 m: 20.29% (14/69).
- Correct retrieval Top-1 changed to a wrong selected candidate: 35.06% (54/154).
- PnP-failure wrong-candidate rejection: 0.00% (0/850).
- Selection-level wrong-candidate rejection: 85.18% (724/850).
- Productive rejection/rescue: 69.00% (69/100).
- Confident-but-wrong: 27.80% (82/295).
- Native RoMa confidence/ranking: UNAVAILABLE.
- Per-candidate PnP reprojection error: UNAVAILABLE.

## Preregistered verdict adjudication

**INCONCLUSIVE**

The preregistration did not uniquely define wrong-candidate rejection. Its <=25% GO clause and >=50% NO-GO clause are therefore UNADJUDICATED: PnP-failure, selection-level, and productive rejection are all retained, and none is selected post hoc for the verdict.

GO support is not established: identity increment is +5.08 pp (required <=+5 pp), rescue is 69.00% with Wilson upper 77.22% (required <=10% and upper <20%), and the rejection clause is unadjudicable. The independent NO-GO conjunction fails because identity improvement is below +10 pp and rescued <=3 m rate is 20.29% rather than >=80%; the alternative rejection branch is unadjudicable.

## Strongest counterevidence and strongest premise-consistent evidence

The strongest counterevidence to the premise is the 69.00% productive rescue rate among queries with a wrong retrieval Top-1 and a correct Top-5 alternative. Geometry-mediated selection therefore does not merely preserve the retrieval Top-1 candidate identity in this run.

The strongest premise-consistent evidence is that PnP hard-rejected 0.00% of wrong candidates while 27.80% of all queries ended in a selected wrong candidate with inlier ratio >=0.3. In addition, only 20.29% of identity rescues produced <=3 m final localization, so most footprint-identity rescues were not high-accuracy geographic rescues.

## Future candidate-pool evidence

- Rescue: 69/100.
- Correct retrieval Top-1 to wrong selected candidate: 54/154.
- Net candidate identity increment: +5.08 pp.
- Wrong-candidate PnP failure: 0/850.
- Confident-but-wrong at inlier ratio 0.3: 27.80%.

## Sensitivity

| tau (m) | inlier ratio | identity increment (pp) | rescue | rescued <=3 m | deterioration | PnP-failure rejection | selection rejection | confident-wrong |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.2 | +5.08 | 69.00% | 20.29% | 35.06% | 0.00% | 85.18% | 41.69% |
| 0 | 0.3 | +5.08 | 69.00% | 20.29% | 35.06% | 0.00% | 85.18% | 27.80% |
| 0 | 0.4 | +5.08 | 69.00% | 20.29% | 35.06% | 0.00% | 85.18% | 12.88% |
| 5 | 0.2 | +5.08 | 69.07% | 20.90% | 31.90% | 0.00% | 85.50% | 38.64% |
| 5 | 0.3 | +5.08 | 69.07% | 20.90% | 31.90% | 0.00% | 85.50% | 25.76% |
| 5 | 0.4 | +5.08 | 69.07% | 20.90% | 31.90% | 0.00% | 85.50% | 11.53% |
| 10 | 0.2 | +4.41 | 65.96% | 22.58% | 28.32% | 0.00% | 85.62% | 36.27% |
| 10 | 0.3 | +4.41 | 65.96% | 22.58% | 28.32% | 0.00% | 85.62% | 24.07% |
| 10 | 0.4 | +4.41 | 65.96% | 22.58% | 28.32% | 0.00% | 85.62% | 10.51% |
| 20 | 0.2 | +5.08 | 67.82% | 23.73% | 23.16% | 0.00% | 86.88% | 30.17% |
| 20 | 0.3 | +5.08 | 67.82% | 23.73% | 23.16% | 0.00% | 86.88% | 18.98% |
| 20 | 0.4 | +5.08 | 67.82% | 23.73% | 23.16% | 0.00% | 86.88% | 6.10% |

## Interpretation boundary

The strict increment compares CAMP retrieval Top-1 identity with the final max-inlier selected identity. It measures the joint downstream reranking behavior of learned matches, DSM lifting, PnP/RANSAC, and selection; it is not a PnP-only causal effect. Coverage and affine-coherence fields in the candidate table are analysis-defined proxies and are not used by the frozen verdict.

The full provenance comes from one nondeterministic pipeline run. The earlier L16_0001 smoke demonstrated run-to-run changes in PnP inliers, selected index, and final error despite invariant retrieval Top-5. Bootstrap intervals quantify query sampling uncertainty, not algorithmic rerun variance.

## Decision

The final verdict is INCONCLUSIVE. Its primary basis is that native RoMa correspondence-only ranking cannot be recovered, so the PnP-only independent causal increment is not identifiable, while observed downstream reranking both rescues many wrong Top-1 cases and corrupts many correct Top-1 cases. The ambiguous preregistered rejection clause is not used to decide the verdict. GEO-1 should STOP in its current formulation as a method-development candidate. This is not a claim that geometry is useless.
