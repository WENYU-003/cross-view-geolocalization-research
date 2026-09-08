# GEO-1 Minimal Falsification Analysis

## Scope and evidence boundary

This directory contains an offline, no-training analysis of the saved
Scene_16 satellite full-pipeline provenance. It does not modify or rerun
AnyVisLoc, CAMP, RoMa, DSM lifting, PnP/RANSAC, or candidate selection.

The native RoMa correspondence confidence and a native
correspondence-only candidate score were not saved. Consequently:

- retrieval Top-1 to selected-candidate identity change is a strict
  downstream reranking increment;
- it is not a PnP-only causal increment;
- coverage, concentration, and affine-coherence measurements are
  analysis-defined proxies only;
- any core interpretation that depends on those proxies must be
  `INCONCLUSIVE`.

`PDE`/`R_i` are GT-derived geographic-distance diagnostics. They are never
used as pre-geometry prediction scores.

## Frozen variable definitions

For each query/candidate, an affine map from saved patch-local reference
coordinates to local geographic XY is recovered from
`ref_pts_patch -> (local_x, local_y)`. Applying this map to the four crop
corners gives the candidate geographic footprint. Candidate distance is the
shortest GT-XY distance to that polygon and is zero inside it.

The primary correctness threshold is `tau=0 m`; sensitivity thresholds are
`tau={0,5,10,20} m`. Multiple overlapping candidates may be correct.

The primary confident-geometry threshold is PnP inlier ratio `>=0.3`;
sensitivity thresholds are `{0.2,0.3,0.4}`. This is an uncalibrated geometry
confidence proxy.

The preregistration used the term `wrong-candidate rejection` without freezing
one unique operational definition. The three plausible definitions are
therefore deliberately separated:

1. **PnP-failure rejection:** a wrong candidate returns no successful PnP
   pose.
2. **Selection-level rejection:** a wrong candidate is not selected. This is
   descriptive and mechanically high when only one of five candidates wins.
3. **Productive rejection:** retrieval Top-1 is wrong, a correct candidate is
   available in Top-5, and final selection changes to a correct candidate.
   This is query-level and equals the operational rescue event.

## Frozen decision rule

Primary analysis uses `tau=0` and inlier-ratio threshold `0.3`. Definitions
and thresholds must not be selected after viewing results.

**GO support** requires all of:

- candidate identity increment `<= +5 pp`;
- geometry rescue `<=10%` and Wilson 95% CI upper `<20%`;
- wrong-candidate rejection `<=25%` (operational definition unresolved);
- confident-but-wrong `>=20%`.

**NO-GO** requires either:

- candidate identity improvement `>=+10 pp`, rescue `>=25%`, and at least
  `80%` of rescued cases have final localization error `<=3 m`; or
- wrong-candidate rejection `>=50%` (operational definition unresolved).

Every other outcome is `INCONCLUSIVE`. Because the preregistration did not
choose among PnP-failure, selection-level, and productive rejection, the
`wrong-candidate rejection <=25%` GO clause and the `>=50%` NO-GO clause are
both marked **UNADJUDICATED**. None of the observed definitions may be chosen
post hoc to trigger or avoid a verdict. The independent NO-GO conjunction
(identity improvement, rescue rate, and rescued localization quality) remains
adjudicable.

## Candidate-pool evidence retained from this audit

These observations are retained as evidence for future candidate-pool review,
not as a reformulated GEO-1 method claim:

- rescue: `69/100`;
- correct retrieval Top-1 to wrong selected candidate: `54/154`;
- net candidate identity increment: `+5.08 pp`;
- wrong-candidate PnP failure: `0/850`;
- confident-but-wrong at inlier-ratio threshold `0.3`: `27.80%`.

## Reproduction command

```bash
python reproductions/anyvisloc/geo1_analysis/analyze_geo1_minimal_falsification.py \
  --input-root /absolute/path/to/geo1_scene16_candidate_provenance \
  --output-dir reproductions/anyvisloc/geo1_analysis \
  --bootstrap-repetitions 10000 \
  --bootstrap-seed 20260908
```

All five candidates from a query remain together during bootstrap resampling.
Wilson intervals are also reported for binomial proportions. Raw provenance
and large experiment artifacts remain outside Git.
