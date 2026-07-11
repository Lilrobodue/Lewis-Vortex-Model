# EXPLORATORY — the giant-aware refit: corrected physics, and the giant goal still FAILS

> **Status: EXPLORATORY.** The continuation of `EXPLORATORY_giant_prediction.md`: the scoped
> cycle (adopt flux-limited growth → refit → re-test both). Reproduce with
> `py -3.11 -m src.solver.fit_giant` (uses `evolve(..., flux_limited=True)`).

## The cycle

`giant_test.py` showed the model over-produced giants (100% of systems) and predicted giant
hosts at chance (AUC 0.48), because core growth was ~1000× too fast (it used the full local
solid column, not the drifting pebble flux). This cycle:

1. **Adopted flux-limited pebble accretion** — the physically correct growth (Σ_peb from the
   inward flux; `embryos.pebble_surface_density`). Gated behind `evolve(..., flux_limited=True)`
   so the default still reproduces the pre-registered confirmed model (23.6%, PASS — verified).
2. **Refit the ten globals on a TRAIN split** with a two-term objective: mean anchored position
   RMS **+** a light penalty (λ=0.5) for missing the observed giant RATE (`fit_giant.py`). The
   giant term targets only the base rate on TRAIN; held-out AUC and positions stay honest.

## What improved (real, robust)

| held-out (3 splits) | result |
|---|---|
| **positions — beat-geometric** | **20.0 / 21.7 / 21.7 %** (frozen 253-system split: 22.1%, p=5×10⁻²¹) |
| position quality (matched-RMS) | 0.026 dex (better than the confirmed model's 0.031) |
| **giant occurrence rate** | **15 / 15 / 17 %** (observed ~22%; was 100%) |
| **model giant AUC** | **0.582 / 0.589 / 0.553** — robustly *above chance* (was 0.48) |

So the corrected physics (a) **preserves the spacing skill** (~22% ≈ the confirmed 23.6%), (b)
makes **giants selective** instead of universal, and (c) gives the model **real, above-chance
giant discrimination**. The fit found the giant-selective regime on its own: M_crit 6→9.7,
sigma0 3500→958, t_disk 9.7→5.8 (higher runaway threshold, less-massive/shorter-lived disks).

## What still FAILS (the goal)

The giant discrimination is **entirely redundant with stellar metallicity + mass.** Proper
incremental-value test (logistic regression, TRAIN-fit → HELD-OUT AUC, 3 splits):

| | feh + M* | feh + M* + **model** | Δ |
|---|---|---|---|
| split 432 | 0.709 | 0.664 | **−0.045** |
| split 7 | 0.715 | 0.712 | **−0.003** |
| split 99 | 0.694 | 0.689 | **−0.005** |

Adding the model's giant score to a metallicity+mass baseline does **not** improve held-out
giant-host prediction (Δ ≤ 0 everywhere). The model's giant signal is a **noisier proxy for the
stellar properties it is built from** (feh → dust; L, M* → thermal structure) — it discovers
nothing about giant demographics that the star doesn't already tell you. Metallicity alone
(AUC ~0.70) remains the better predictor, and the physics adds no independent information.

## Verdict

The scoped cycle delivered a **more correct model** (flux-limited growth, selective giants,
positions preserved) — genuine progress in physical realism. But the **scientific goal fails**:
the boundary + growth physics does **not** predict which systems host giants beyond the known
stellar correlations. Combined with the spacing result being near its predictability ceiling
(`EXPLORATORY_hill_regularity.md`), the honest overall picture sharpens:

> The model captures the **deterministic geometric organization** of planetary systems
> (Hill-regulated spacing) near the achievable limit, but carries **no independent predictive
> information about planet demographics** (giant occurrence) beyond stellar metallicity and mass.

## Repository state
- Default `evolve` (flux_limited=False) = the confirmed, pre-registered model (23.6%). Untouched.
- `evolve(flux_limited=True)` = corrected physics; used by `fit_giant.py`. Params in
  `runs/fit_giant/fit_giant.json`.
- Adopting the corrected physics as the default would supersede the M7 pre-registration and
  requires its own fresh pre-registered confirmation (positions ~22%). Deferred as a decision,
  not done unilaterally.
