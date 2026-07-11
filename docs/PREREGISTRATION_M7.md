# Pre-Registration — M7 confirmation of population-fit skill

> **SUPERSEDED by `PREREGISTRATION_M7v2.md`** (corrected flux-limited-growth model, confirmed
> at 22.1%). This v1 pre-registration and its PASS remain valid for the legacy local-column
> growth model and are reproducible via `preregister_confirm.py` (default `flux_limited=False`).


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

## Result — **PASS (H1 confirmed)**

Run once with the frozen inputs (sha256 verified) via `preregister_confirm.py`
(`runs/prereg_M7/confirmation.json`):

| quantity | value |
|---|---|
| held-out systems | 263 |
| beat geometric-regularity null | **62 / 263 = 23.6%** |
| 95% Wilson CI | [18.8%, 29.1%] |
| one-sided binomial p vs p₀ = 0.05 | **1.2 × 10⁻²⁴** |
| pre-registered criterion | rate ≥ 15% **and** p < 1e-3 |
| **decision** | **PASS — H1 confirmed** |

The confirmed rate (23.6%) falls inside the pre-registered prediction band (0.22–0.32) and far
above the 0.15 threshold; p is ~24 orders of magnitude below the 1e-3 bar. **The population-fit
disk-boundary model beats a geometric-regularity null on held-out exoplanet systems far more than
chance — a pre-registered, confirmed, out-of-sample result.**

Honest scope (unchanged from the exploratory finding): 23.6% confirms *partial* skill — most
systems (76%) are still described at least as well by a single geometric ratio. This is a real,
falsifiable planetary leg for the boundary principle, not a claim that boundaries dominate
exoplanet architecture.
