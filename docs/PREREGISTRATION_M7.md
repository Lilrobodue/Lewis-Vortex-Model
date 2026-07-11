# Pre-Registration — M7 confirmation of population-fit skill

**Written before the confirmation run. No input below changes after this file is committed;
any change voids the pre-registration (guide §6, §8).**

- **Date:** 2026-07-11
- **Authors:** Joseph Lewis & Selah, via Claude Code
- **Status at write time:** the beat-geometric rate below has been seen only on *exploratory*
  train/test splits (25.9–28.9%). This document freezes the parameters, the held-out list, the
  metric, and the pass threshold so the confirmation run is a single, non-negotiable test.

## Hypothesis

- **H1:** the frozen population-fit global parameters predict held-out exoplanet architectures
  well enough to beat a geometric-regularity null on **more than the 5% chance fraction** of
  systems.
- **H0 (null):** the model's beat-geometric rate equals the chance baseline, p₀ = 0.05.

## Frozen inputs (integrity hashes, sha256 first 16 hex)

| artifact | path | sha256[:16] |
|---|---|---|
| global parameters (10) | `runs/fit_population/population_fit.json` | `66bec6c0802f819b` |
| held-out systems (263) | `data/heldout_confirm.json` | `032295d0a1f63c16` |

The held-out list is, by construction, the 263 systems **not** in the DE training split
(`fit_population.split_systems(n_train=50, seed=432)`). The parameters were fit only on the
complementary 50 training systems. No system in the held-out list influenced the parameters.

## Metric, null, and test statistic (frozen)

- **Metric:** per-system anchored RMS of `log10(a_pred / a_obs)` — guide §7 protocol: the only
  positional input is the innermost observed planet; predictions are anchored to it and scored
  within the observed radial window (`validate.py --protocol anchored`).
- **Null:** single best-fit geometric ratio per system (`validate.geometric_ratio_null`).
- **Test statistic:** *beat-geometric rate* = fraction of held-out systems with
  `model_rms ≤ geometric_null_rms`.
- **Determinism:** forward-model seed 432, `n_steps = 500`. The geometric null is deterministic.
  The random-spacing null is reported for context only and is **not** part of the pass criterion
  (it is count-unstable — see `M7_failure_analysis.md` caveat 2).

## Pre-registered pass criterion

**PASS iff both hold:**
1. beat-geometric rate **≥ 0.15** (three times the chance baseline), and
2. one-sided binomial p-value against H0 (p₀ = 0.05) **< 1e-3**.

**Point prediction:** beat-geometric rate ≈ 0.27 (95% expected 0.22–0.32).

## Analysis plan

One confirmation run over the frozen held-out list with the frozen parameters. Report: the
beat-geometric rate, its 95% Wilson confidence interval, the one-sided binomial p-value, and the
PASS/FAIL decision against the criterion above. No parameter, metric, or threshold changes after
this file is committed. If the result fails, it is reported as a failure with equal prominence.

## Result

*(to be filled by `preregister_confirm.py` after the run — see `runs/prereg_M7/`)*
