# Pre-Registration v2 — M7 confirmation of the CORRECTED-PHYSICS model

**Written before the confirmation run. Supersedes `PREREGISTRATION_M7.md` for the project's
primary model. The v1 pre-registration and its confirmation remain valid for the legacy
(local-column growth) model and are reproducible at their commit.**

- **Date:** 2026-07-11
- **Authors:** Joseph Lewis & Selah, with Claude Code
- **What changed vs v1:** the model now uses **flux-limited pebble accretion**
  (`evolve(flux_limited=True)`; `embryos.pebble_surface_density`) — the physically correct
  drifting-pebble growth that replaced the stationary-column growth (which formed giants in
  ~10⁴ yr in every system). The ten globals were re-fit for this physics on a train split
  (`fit_giant.py`). Same ≤10 global parameters, no per-planet dials.
- **Transparency (same caveat as v1):** the ~22% point estimate below was seen on exploratory
  train/test splits during development. This document freezes the parameters, the held-out
  list, the metric, and the pass threshold so the confirmation is a single hash-verified test.
  It is a *formalization*, not a blind test.

## Hypothesis
- **H1:** the corrected-physics model's global parameters predict held-out exoplanet
  architectures well enough to beat a geometric-regularity null on **more than the 5% chance
  fraction** of systems.
- **H0:** the beat-geometric rate equals the chance baseline, p₀ = 0.05.

## Frozen inputs (sha256, first 16 hex)

| artifact | path | sha256[:16] |
|---|---|---|
| corrected-physics parameters | `runs/fit_giant/fit_giant.json` | `af23af79e5518638` |
| held-out systems (253) | `data/heldout_confirm_v2.json` | `d24deda2aba2b5b6` |

The held-out list is, by construction, the 253 systems **not** in the giant-aware fit's
training split (`fit_giant.split(n_train=60, seed=432)`). No held-out system influenced the
parameters.

## Metric, null, test statistic (frozen)
- **Metric:** per-system anchored RMS of `log10(a_pred/a_obs)` (guide §7; innermost planet is
  the only positional input), evaluated with `flux_limited=True`, seed 432, `n_steps = 500`.
- **Null:** single best-fit geometric ratio per system.
- **Test statistic:** beat-geometric rate = fraction of held-out systems with
  `model_rms ≤ geometric_null_rms`.

## Pre-registered pass criterion
**PASS iff both:** (1) beat-geometric rate **≥ 0.15**, and (2) one-sided binomial p vs
p₀ = 0.05 **< 1e-3**. **Point prediction:** ≈ 0.22 (95% expected 0.17–0.27).

## Analysis plan
One confirmation run over the frozen held-out list with the frozen parameters and the corrected
physics, via `preregister_confirm_v2.py` (hashes verified before scoring). Report rate, 95%
Wilson CI, binomial p, and PASS/FAIL. No input changes after this commit. A failure is reported
with equal prominence.

## Result — **PASS (H1 confirmed)**

`runs/prereg_M7v2/confirmation.json`:

| quantity | value |
|---|---|
| held-out systems | 253 |
| beat geometric-regularity null | **56 / 253 = 22.1%** |
| 95% Wilson CI | [17.5%, 27.6%] |
| one-sided binomial p vs 0.05 | **5.0 × 10⁻²¹** |
| criterion | rate ≥ 15% and p < 1e-3 |
| **decision** | **PASS — H1 confirmed** |

The corrected-physics model confirms at 22.1% (inside the predicted 0.17–0.27 band, far above the
0.15 threshold), statistically indistinguishable from the legacy model's 23.6% — **the spacing
skill is fully preserved under the physically-correct growth.** Giant-planet demographics remain
*not* predicted beyond stellar metallicity (see `EXPLORATORY_giant_refit.md`); this confirmation
covers positions only, which is the model's earned, ceiling-limited leg.
