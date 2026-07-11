# EXPLORATORY — is the "geometric null" actually the physics? (Hill-regularity)

> **Status: EXPLORATORY.** Not pre-registered, single data snapshot (PSCompPars 2026-07-11),
> multiple hypotheses examined. Nothing here is a confirmed claim. It exists to decide where to
> point a future *pre-registered* test. Read alongside `M7_failure_analysis.md`.

## Why this thread

All session the geometric-regularity null was treated as a trivial strawman the physics kept
losing to (M7: population-fit model beats it 23.6%). But real systems are astonishingly regular
(intra-system spacing scatter ~0.08 dex, 10× tighter than the model). That raised a suspicion:
**what if the geometric null isn't trivial — what if it IS the physics?** Specifically,
mutual-Hill-regulated packing (our Branch C) predicts near-constant spacing for near-equal-mass
planets, which *looks* geometric.

## Tests (data: 311 systems with ≥3 mass-measured planets; masses partly from M–R relations)

**(a) Do observed spacings imply a clustered Hill spacing K?**
Implied K per adjacent pair (from positions + measured masses): **median 19.7, IQR [14.7, 28.4]**
— centered on the Pu & Wu (2015) stability value (~20–30 for Kepler multis). Real systems sit
where mutual-Hill stability says they should. *Supports Hill regulation.*

**(b) Peas-in-a-pod: does mass uniformity track spacing uniformity?**
Within-system dispersion of log-mass vs log-(period ratio): **Spearman r = +0.36, p = 1×10⁻¹⁰
(n = 311).** Uniform-mass systems are uniform-spacing systems — exactly Hill's prediction.
Strong and robust. *(Caveat: some `pl_bmasse` come from mass–radius relations, so this specific
correlation is partly circular; but Weiss+ 2018 established the same effect in directly-measured
radii, so the phenomenon is real.)*

**(c) Does the mass-informed Hill model beat a plain geometric ratio on positions?**
Same one free parameter each (fitted ratio vs fitted K). Median position RMS: geometric **0.0311**
dex vs Hill **0.0338** dex; geometric wins in 57% of systems (Wilcoxon p = 0.004). **The strong
form of H-Hill is refuted:** Hill does *not* out-predict a geometric ratio.

Resolution: within a system the masses are uniform enough (and noisy enough) that the Hill ratio
is nearly constant → **a geometric ratio is the smooth limit of Hill packing.** The two are nearly
the same object for this population.

**(d) Does OUR forward model reproduce peas-in-a-pod?**
Model (population-fit params) within-system mass-disp vs spacing-disp: **r = +0.83, p = 5×10⁻⁷⁷
(n = 293).** The model **has** the mechanism — in fact *too strongly*: observed is +0.36, the model
is +0.83. The model over-determines spacing from mass; reality carries extra scatter (formation
stochasticity, later dynamics, measurement noise) that loosens the link.

## What this reframes

1. **The geometric null was never a strawman.** It is the emergent smooth limit of mutual-Hill
   packing (K ≈ 20, confirmed) — real physics. So M7's "model beats geometric only 24%" is the
   model competing against physics, not against a toy. Beating it at all is meaningful.
2. **Our model is not missing the core organizing principle.** It contains Hill-regulated
   peas-in-a-pod packing and expresses it strongly. The 24% ceiling is therefore *not* "wrong
   mechanism."
3. **The real gap is dispersion + gaps, not mechanism.** The model's peas correlation is too tight
   (0.83 vs 0.36) and its architecture is bimodal (tight chains + spurious giant-cleared voids,
   intra-system scatter 0.68 vs 0.08 dex). The frontier is (i) suppress the gap-making giants and
   (ii) add realistic scatter — *calibration*, not a missing ingredient.

## Where I'd point the next PRE-REGISTERED test

**H (pre-registerable):** With the giant-overproduction suppressed and a realistic spacing
dispersion, the model's binding-constraint verdict (M6 `analyze_log`) for compact systems is
`hill_packing`-dominated, and its intra-system spacing scatter matches the observed 0.08 dex within
a factor of ~2. Frozen metric: intra-system log-ratio scatter distribution vs observed (KS test);
plus the peas correlation r within [0.25, 0.50]. This turns "does the model have the mechanism"
(exploratory answer: yes) into "does the model have the mechanism at the right strength" (a clean,
falsifiable, one-shot test).

## Detour recorded: stellar spin → scale (the toroidal-geometry thread)
Pulled NASA rotation data (`data/spin_hosts.json`, 389 hosts). After controlling for stellar mass
(v·sin i vs mass r = +0.53, a strong confound), a faint partial correlation survives — faster spin
↔ more compact systems (|r| ~ 0.2, p ~ 0.01–0.02) — but it does **not** survive multiple-comparison
correction across the 8 tests run, and today's spin is a poor proxy for natal angular momentum
(magnetic spin-down). Recorded as *checked, weak, confounded*; not pursued further without
age-controlled, deprojected spins and a single pre-registered directional prediction.
