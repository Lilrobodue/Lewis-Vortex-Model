# EXPLORATORY — giant-presence prediction: the model's distinctive test, and it FAILS

> **Status: EXPLORATORY.** Single data snapshot. The verdict is a clean negative; recorded with
> the same prominence as the successes (guide §6). Reproduce:
> `py -3.11 -m src.solver.giant_test --params runs/fit_population/population_fit.json`

## Why this test

M7 + `EXPLORATORY_hill_regularity.md` showed the model's *spacing* skill is near a predictability
ceiling — because the geometric-regularity null is itself Hill-packing physics. The model's one
distinctive prediction that the geometric null is *blind* to is **which systems host giant
planets and where**. That was the natural place to look for un-ceilinged skill. So: does the
forward model predict giant-host systems better than the known stellar baselines?

## Result — the model FAILS; metallicity wins

| predictor of "system hosts a giant (>100 M⊕)" | AUC (0.5 = chance) |
|---|---|
| stellar **[Fe/H]** (Fischer & Valenti 2005) | **0.717** |
| stellar mass | 0.646 |
| **model max planet mass** | **0.482 (chance)** |

- Observed giant rate: **22.7%**. Model giant rate: **100%** — the model makes a giant in *every*
  system. It has no discriminating power (AUC ≈ 0.5), and metallicity beats it outright.
- The planet–metallicity correlation is strongly present in the data (r = +0.30, p = 10⁻⁸), so
  there is a real signal to capture — the model just doesn't capture it.

## Why the model over-predicts giants (diagnosis)

Giant formation in the model is gated by **pebble-isolation mass vs M_crit** — a thermal/structural
threshold (isolation mass = 25(h/0.05)³, set by the disk aspect ratio), *not* by metallicity. At
the population-fit parameters (M_crit ≈ 6 M⊕, near its prior minimum) that gate is almost always
open, so nearly every disk makes a giant.

Deeper cause: **core growth is not time-critical.** A core reaches M_crit in ~0.01 Myr — 1000×
faster than the disk lifetime (~10 Myr) — because `pebble_growth_rate` used the *entire local solid
column* as the accretion reservoir. Real pebble accretion is **flux-limited**: a core accretes only
a fraction of the pebbles *drifting past* (Σ_peb ~ 1000× smaller). Since growth finishes almost
instantly regardless of metallicity, the feh → dust → growth chain the model *does* contain cannot
gate giant presence.

## What was tried, and why it's deferred (not adopted)

Implemented **flux-limited pebble accretion** (Σ_peb from the inward pebble flux, not the full
column) — the physically correct fix. It made growth realistically slow (Σ_peb ~ 0.1–1 g/cm²,
time-to-M_crit ~ 0.1–0.7 Myr) but **still not time-critical** at the fitted params (t_disk ≈ 9.7 Myr,
M_crit ≈ 6), so giants stayed universal. More importantly, changing the growth physics **invalidated
the position fit**: the confirmed M7 beat-geometric rate collapsed from ~24% to ~7.5%, because the
population-fit parameters were optimized for the old growth.

Conclusion: flux-limited growth is the right direction but **cannot be dropped in** — it requires a
full **refit of the ten globals + a new pre-registered M7 confirmation**. That is a scoped, separate
effort, not a patch. The change was therefore reverted to keep the repository reproducing the
pre-registered result (M7 confirmation `runs/prereg_M7/`).

## Honest verdict

The boundary + migration + resonance + Hill model, at its confirmed parameters:
- **captures planetary spacing** about as well as it can be captured (near the predictability
  ceiling — a real, pre-registered, partial success), but
- **does not capture giant-planet demographics**: it over-produces giants (100% vs 22.7%) and
  carries no information about which systems host them (AUC 0.48 vs metallicity 0.72).

So the physics' one un-ceilinged distinctive prediction, tested fairly, **fails** — for a
now-understood reason (non-time-critical, over-efficient core growth) with a concrete, motivated
remedy (flux-limited growth + refit). Metallicity remains the better giant predictor.

## The next scoped effort, if pursued
1. Adopt flux-limited pebble accretion (code drafted this session; reverted pending refit).
2. Re-fit the ten globals on the train split with the new growth. Check whether the position-
   optimal regime is now giant-*selective* (marginal time-to-M_crit) — it may or may not be.
3. Re-run the pre-registered M7 confirmation (positions) AND this giant-presence test on held-out
   systems. Only if BOTH hold does the model earn a giant-demographics leg.
