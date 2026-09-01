# Scene_16 295-Query Spatial-Support Diagnostic

## Research question

Are satellite localization failures systematically associated with weaker cross-reference geographic agreement, poorer spatial coverage, greater correspondence concentration, insufficient surrounding support, or unreliable saved confidence?

## Controlled evidence scope

- 295 paired Scene_16 queries from saved aerial and satellite GT-reference RoMa runs.
- CPU-only archive analysis; no retrieval, RoMa, training, DSM lookup, or PnP rerun.
- Satellite final error is an outcome variable only.
- Aerial map endpoints are a pseudo-reference, not manual correspondence ground truth.
- RoMa certainty/confidence is unavailable in every saved artifact, so confidence calibration is not reported.

## Reproduction command

```bash
python reproductions/anyvisloc/analyze_scene16_spatial_support.py \
  --aerial-archive "$EVIDENCE_DIR/aerial_gtref_logging_scene16_20260831-1017.tar.gz" \
  --satellite-archive "$EVIDENCE_DIR/satellite_gtref_scene16_20260831-0905.tar.gz" \
  --output-dir /path/to/scene16_spatial_support_diagnostic_20260901
```

- Aerial archive SHA-256: `9925de87703aa20c52d28ce476757f4dc5bd5b456c486a4372b3f9b76882f1c7`
- Satellite archive SHA-256: `63954d09d9c5d3051df8aa4f15bc33aa00806dc1dcecf731ec84ff46500c16fe`
- Pairing: mutual nearest UAV coordinates within 5 original-image pixels.
- Spatial grid: 8 x 8 on normalized coordinates.

## Metric interpretation

- `grid_occupancy`: occupied cells / 64.
- `convex_hull_coverage`: normalized convex-hull area in the UAV image or satellite reference patch.
- `normalized_hhi`: global grid concentration, where uniform support approaches 0 and single-cell support approaches 1.
- `top4_cell_mass_proxy`: fraction of correspondences in the four densest cells. This is only a concentration proxy and is not a roof/repetition label.
- `spatial_entropy`: normalized Shannon entropy over the 64 cells.
- `coherent_shift_magnitude_m`: norm of the median aerial-to-satellite XY displacement.
- `shift_corrected_residual_median_m`: median residual after subtracting that coherent shift.

## Group sizes and key metrics

| Group | n | Median error (m) | Median Agreement@5m | Median shared pairs | Median satellite occupancy | Median satellite HHI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Success <=3 m | 69 | 1.622 | 0.559 | 848.0 | 0.766 | 0.010 |
| Middle 3-20 m | 181 | 7.449 | 0.420 | 820.0 | 0.844 | 0.009 |
| Catastrophic >20 m | 45 | 38.550 | 0.282 | 779.0 | 0.797 | 0.010 |

## Strongest descriptive correlations

| Metric | Spearman vs final error | Pearson vs log(1+error) |
| --- | ---: | ---: |
| `agreement_5m` | -0.500 | -0.466 |
| `agreement_3m` | -0.487 | -0.463 |
| `coherent_shift_magnitude_m` | 0.447 | 0.460 |
| `agreement_1m` | -0.444 | -0.389 |
| `geographic_disagreement_median_m` | 0.421 | 0.459 |
| `num_shared_uav_correspondences` | -0.362 | -0.397 |
| `shared_pairing_rate` | -0.362 | -0.397 |
| `geographic_disagreement_mean_m` | 0.277 | 0.400 |
| `shift_corrected_residual_median_m` | 0.220 | 0.300 |
| `agreement_10m` | -0.200 | -0.269 |
| `satellite_ref_convex_hull_coverage` | 0.180 | 0.142 |
| `satellite_ref_top4_cell_mass_proxy` | 0.091 | 0.319 |

## Research-question decisions

| Candidate factor | Current decision | Evidence |
| --- | --- | --- |
| Low cross-reference geographic agreement | Supported as an association | Agreement@5m has Spearman -0.500 with final error and decreases across success, middle, catastrophic groups. |
| Poor global spatial coverage | Not supported as a general monotonic explanation | Satellite grid occupancy Spearman is 0.035; convex-hull coverage is 0.180, and group medians are not ordered as hypothesized. |
| Excessive global concentration | Not supported globally; possible tail subgroup | Satellite HHI Spearman is 0.080. Raw-error sensitivity is larger because a subset of extreme failures is concentrated. |
| Repetitive-structure ambiguity | Still a hypothesis | The concentration proxy has no semantics and cannot identify roof or repeated structure. |
| Insufficient surrounding-context support | Still a hypothesis | No roof/context masks or manual region labels exist for all 295 queries. |
| Confidence/certainty miscalibration | Not testable from current artifacts | RoMa certainty/confidence was not saved in NPZ, JSON, or PKL. |

## Supported by current evidence

- Cross-reference geographic agreement is descriptively associated with final satellite error across all 295 queries.
- Shared UAV pair count has a moderate negative monotonic association with error, even though every run requested 3,000 matches.
- Coherent shift magnitude and shift-corrected residual capture distinct disagreement components; coherent shift has the stronger monotonic association in this audit.
- Global agreement is neither necessary nor sufficient for accurate localization; required counterexamples remain in the shortlist.
- Simple global spatial coverage, concentration, and entropy metrics do not show a strong monotonic relationship with error across all 295 queries. Concentration is elevated in part of the catastrophic tail, but this is not a universal pattern.

## Not confirmed

- Concentration is not a semantic repetitive-roof label. The top-four-cell mass and HHI are spatial proxies only.
- The 24-query observation that stable surrounding context can rescue a pose is not yet quantitatively verified across all 295 because no semantic context mask exists.
- A correlation between coverage/concentration and error does not establish a causal front-end mechanism.
- Aerial/satellite georegistration, temporal change, and downstream geometry can still explain individual cases.
- Confidence calibration cannot be evaluated because RoMa certainty was not saved.

## Required known counterexamples

- `L16_0098`: error=91.835 m, Agreement@5m=0.586, shared pairs=850, satellite occupancy=0.953.
- `L16_0076`: error=0.287 m, Agreement@5m=0.325, shared pairs=761, satellite occupancy=0.797.
- `L16_0077`: error=0.802 m, Agreement@5m=0.297, shared pairs=839, satellite occupancy=0.797.

## Uncertainty and next decision

This audit can select a narrower front-end research problem but cannot yet justify a model architecture. Agreement/cross-reference correctness remains the strongest verified front-end signal. Basic global coverage and concentration should not be promoted as the main hypothesis without subgroup evidence. The next minimal step is to inspect deterministic counterexample subgroups and decide whether a small manual region annotation protocol can test structure-versus-context support. Any later semantic roof/context claim requires that annotation and must remain separate from the current concentration-only proxy.
