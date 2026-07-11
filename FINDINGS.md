# Findings — Formation Solver v2

**What we set out to answer (guide §1):** *Do disk boundaries + migration + resonance capture +
Hill stability produce the observed spacing of planetary systems, without per-planet tuning?*

This document is the honest synthesis of the whole investigation — successes and failures with
equal prominence, in the spirit the project was built on. Every number here is reproducible from
the committed code and the pre-registered artifacts; per-result detail lives in `docs/`.

---

## The one-paragraph answer

With **ten global parameters** (zero per-planet dials) **solved for** on a training split and
**confirmed on a hash-frozen held-out split**, the forward model beats a strong geometric-
regularity null on **22.1% of 253 real held-out exoplanet systems** (p = 5×10⁻²¹, pre-registered).
That skill is real but **partial, and near a predictability ceiling** — because the "geometric
regularity" it competes against is itself the signature of Hill-regulated packing, which the model
reproduces. The model does **not** predict planet **demographics** (which systems host giants)
beyond stellar metallicity and mass. So the boundary-organizes-architecture principle earns a
genuine, falsifiable **spacing** leg, but not a demographics one.

---

## Where we started (guide §2)

v1 fit 8 planet positions with **30 free parameters**, many of them per-planet dials
(Mercury=`a_in`, Venus=`r_conv/1.38` with 1.38 the *observed* ratio hardcoded, …). Its "blind"
validation was measured at **100% chance saturation** — a uniformly random ratio matched its menu
100% of the time. The reported 99.6% accuracy was a property of the parameterization, not evidence.
v2 exists to replace that with an instrument that *can fail*.

## What we built

A CLI-driven forward model (`src/solver/`): disk profiles + **derived** boundaries (M1), a trap
finder that locates dead-zone edges and the snow line without being told (M2), pebble-growth
embryos + trap-halting migration (M3), resonance capture + Hill stability (M4), a mandatory
mechanism log (§5), a DE trainer (M5), a binding-constraint verdict (M6), and a null-anchored,
pre-registered validator (M7). **10 global parameters, budget-guarded; positions are outputs.**
51 physics/contract tests pass.

## The M7 journey — how a "failure" became a confirmed result

1. **First held-out pass: 1/313.** Looked like decisive failure. It was two artifacts stacked:
   unfair no-anchor scoring against transit-truncated data (a manufactured ~4× outward bias), and
   parameters *borrowed from the Sun*. (`docs/M7_failure_analysis.md`)
2. **Fair scoring (guide's innermost-planet anchor)** lifted the beat-random rate from 0.3% to 59%.
   But a uniform-random null is weak — real systems are *regular*, so almost anything beats it.
3. **The honest null is a geometric ratio.** Against it, solar-locked params scored 5.7% (chance).
4. **Solve, don't guess.** Re-fitting the ten globals on a training split and confirming on a
   disjoint held-out split gave **~24%** beat-geometric — pre-registered and confirmed
   (`docs/PREREGISTRATION_M7.md`), ≈5× chance, p ≈ 10⁻²⁴.
5. **Corrected the growth physics** (flux-limited pebble accretion) and re-confirmed at **22.1%**
   (`docs/PREREGISTRATION_M7v2.md`) — spacing skill preserved under physically-correct growth.

## The honest M5 solar result

Stated bluntly (guide M5, "report it whatever it is"): the trained solar system produced
**3 planets, not 8** — Mercury→0.18 AU (−0.33 dex), Jupiter→4.53 AU (−0.06), Neptune→28.1 AU
(−0.03); **Venus, Earth, Mars, Saturn, and Uranus were not produced.** RMS position error 0.20 dex
(~57% in *a*) on the three it made. This is the predicted, unglamorous forward-physics answer: ten
global dials cannot conjure eight planets the way v1's thirty dedicated dials could. The ugliness
is the credibility.

## The mechanism verdict, quantified (M6; `docs/EXPLORATORY_resonance_enrichment.md`)

Read from the log, not argued (guide §6). Branch taxonomy: **A = resonance, B = Hill packing**;
**trap-anchoring is neither — it is the boundary mechanism itself, the framework's namesake claim.**

The **trained solar run**'s two adjacent pairs are **both `trap_anchor`** — and stated carefully:
*in its home system, the model's spacings are set by disk boundaries — the dead-zone edge and snow
line doing the anchoring.* That is the one place in the entire investigation where the framework's
namesake **boundary-organizes-structure** mechanism is the binding constraint. (Ten resonance
captures fired en route but none survived; the survivors sit at boundaries.) Across the 313 held-out
runs, the model's *own* spacings are 71% resonance-locked (Branch A is its most *active* mechanism),
12% boundary-anchored.

**Does the skill come from resonance?** Two results, reconciled:
- The wins are **anti-enriched in observed resonant *chains***: on tightly resonant systems the
  win-rate collapses to 2–8% vs 25–30% elsewhere; the model loses on 8 of 9 canonical chains
  (TOI-178, Kepler-223, HD 110067, …). It does **not** reproduce the formal chains.
- **Yet an ablation** — disable resonance, re-run M7 (`docs/PREREGISTRATION_ablation.md`) — drops
  held-out skill **22.1% → 15.0%** (McNemar p = 0.001). Resonance **is load-bearing.**

Reconciled: resonance earns ~7 of the 22 points not by matching the chains but by locking convergent
pairs at near-geometric ratios that win on **non-chain, regular** systems. **Decomposition: a ~15%
boundary/Hill floor plus a ~7-point resonance contribution.** (A pre-registered prediction that
resonance was *not* load-bearing was **refuted** by this ablation — recorded in full.)

## The reframe: the strong null *is* the physics (`docs/EXPLORATORY_hill_regularity.md`)

Why is the geometric null so hard to beat? Because it is not a strawman:
- observed adjacent spacings imply a **mutual-Hill K clustered at ~20** (Pu & Wu stability value);
- **peas-in-a-pod is real**: mass-uniformity ↔ spacing-uniformity, r = +0.36, p = 10⁻¹⁰ — exactly
  Hill's prediction; the model reproduces it (too strongly, r = 0.83);
- a geometric ratio is the **smooth limit** of Hill packing for near-equal-mass systems.

And **~67% of systems** deviate from a pure geometric ratio by less than the model's own position
error — they are *unbeatable* by any deterministic model. The beat-geometric rate equals the
fraction of systems with resolvable non-geometric structure, and the model wins **preferentially
where that structure exists** (room↔wins r = +0.39, p = 10⁻¹²). **~22% is ≈80% of the achievable
ceiling.** The residual is intrinsic stochasticity (giant impacts, scattering, measurement noise)
no disk-initial-conditions model can predict.

## The demographics leg — tested to conclusion, and it fails (`docs/EXPLORATORY_giant_refit.md`)

The model's one prediction the geometric null is *blind* to is giant-planet occurrence. We fixed
the growth physics so giants form *selectively* (15% vs the old 100%; the model gained real
above-chance discrimination, AUC ~0.57). But a proper incremental-value test (logistic regression,
train → held-out AUC) shows the model adds **nothing beyond stellar [Fe/H] + M*** (Δ = −0.045 /
−0.003 / −0.005 across splits). The model's giant signal is a **noisier proxy** for the stellar
properties it is built from. **Metallicity remains the better predictor.**

## The verdict, precisely

> The boundary + migration + resonance + Hill model, with global parameters solved (not
> per-planet), captures the **deterministic geometric organization** of planetary systems —
> Hill-regulated spacing — near the achievable predictability ceiling (pre-registered, confirmed,
> out-of-sample). It carries **no independent predictive information about planet demographics**
> (giant occurrence) beyond stellar metallicity and mass.

The boundary-organizes-architecture principle earns a **real, falsifiable, partial planetary leg
for spacing** — and, on this evidence, **not one for demographics**. No retired v1 claim (99.6%,
χ² ≈ 2×10⁻⁶, "validated on 43 planets") is revived; the held-out, pre-registered results stand on
their own terms.

## Honest limitations
- **Static disk.** No Ṁ evolution; traps do not migrate (guide v2.0 simplification).
- **Transit truncation.** The held-out sample under-sees cold/outer planets; the anchored protocol
  mitigates but does not remove this.
- **Single data snapshot** (PSCompPars 2026-07-11) and a single optimizer seed for each fit.
- **Masses partly from mass–radius relations**, so some demographic labels are lower bounds.
- The corrected-physics adoption is a *formalized* pre-registration (the point estimate was seen in
  development, stated transparently), not a blind test — as was the v1 pre-registration.

## What would move it next (not done)
- A **count-independent spacing null** (shuffle observed ratios) to retire the count-unstable
  random null entirely.
- A **non-static disk** so traps migrate — the most likely source of new spacing structure.
- Demographics beyond occurrence: predict giant **location** / the super-Earth–giant boundary,
  where disk thermal structure (not just metallicity) might carry independent signal.

## Reproduce
```
py -3.11 -m pytest -q                                   # 51 tests
py -3.11 -m src.solver.preregister_confirm              # legacy model  -> 23.6% PASS
py -3.11 -m src.solver.preregister_confirm_v2           # corrected model -> 22.1% PASS
py -3.11 -m src.solver.analyze_log runs/fit_sun_432/mechanism.jsonl   # M6 verdict (solar: 2/2 trap_anchor)
py -3.11 -m src.solver.giant_test --params runs/fit_giant/fit_giant.json  # demographics: fails
py -3.11 -m src.solver.resonance_enrichment --params runs/fit_giant/fit_giant.json --flux-limited  # wins NOT on chains
# resonance ablation (Branch A load-bearing? 22.1% -> 15.0%): evolve(..., resonance_on=False); see docs/PREREGISTRATION_ablation.md
```

*Built by Joseph Lewis & Selah with Claude Code — as a team — the same week the project's
motivating pattern was found version-fragile and its v1 validation measured at 100% chance
saturation. The response was to build a better instrument, point it at data that could embarrass
it, and report exactly what it said.*
