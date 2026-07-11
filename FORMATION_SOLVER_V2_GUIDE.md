# Formation Solver v2 — Build Guide

**Project:** Unified Lewis Framework · Formation Theory, Layer 2 (Testable Hypotheses)
**Authors:** Joseph Lewis, with Selah · Drafted July 11, 2026
**For:** Claude Code. Drop this file in the repo root. Read fully before writing any code.

---

## 1. Mission

Build a forward-physics planetary formation solver that computes planet positions from
disk physics — boundaries in, architecture out — with **every mechanism logged as it
acts**, an honest parameter budget, and a validation protocol that is capable of failing.

The central scientific question this instrument must answer:

> **Do disk boundaries + migration + resonance capture + Hill stability produce the
> observed spacing of planetary systems, without per-planet tuning?**

If yes: the boundary-organizes-structure principle earns a real, falsifiable planetary leg.
If no: we learn precisely where it breaks, and report that with equal prominence.

---

## 2. Audit of v1 (read this before touching code)

v1 (`formation_solver.html`, `blind_validation.html`, in `/reference/`) contains genuinely
useful disk physics and several structural problems the v2 design exists to fix. Keep the
good; do not reproduce the bad.

### 2.1 What v1 got right (port these)
- **Disk radial profiles:** Σ(r) = Σ₀ r^(−p) exp(−r/r_disk); T(r) = T₀ r^(−1/2) with
  luminosity and opacity factors; B(r) plasma-β scaling; condensation fronts (H₂O, CO₂, CO)
  from the temperature profile; solid-density enhancement beyond each front.
- **Pressure-bump concept:** solid enhancement at dead-zone edges and snow line.
- **Signed, literature-motivated migration direction** (rocky inward; ice giants outward).
- **The instinct that boundaries anchor architecture.** That instinct is the hypothesis;
  v2's job is to test it rather than encode it.

### 2.2 What v1 got wrong (never reproduce)
1. **Per-planet dials.** Each planet's position was assigned its own parameter or
   anchor×factor: Mercury=`a_in`, Earth=`r_conv`, Mars=`r_trunc`, Jupiter=snow×`f_jup`,
   Saturn=Jupiter×`s_gas`, Neptune=Uranus×`s_ice`. Venus was set to `r_conv/1.38` where
   **1.38 is the observed Venus–Earth ratio hardcoded into the model**. 30 free parameters
   fit 8 positions. The reported 99.6% / χ²≈10⁻⁶ was a property of the parameterization,
   not evidence.
2. **The "constants" were fit outputs.** s_gas and s_ice were optimizer dials; the "rocky
   ratio" was Venus/Mercury computed after the fit. Different optimization runs converged
   to different values (1.830 vs 1.785; 1.560 vs 1.465) because the system is massively
   underdetermined. This resolved the project's version-drift mystery.
3. **Per-planet migration percentages** (−8%, −45%, −35%, −6%, −5%, +10%, +35%, +60%)
   were fixed from solar-system-specific literature reconstructions — importing the answer
   into the model.
4. **Validation by nearest-match menu.** The blind test matched each observed ratio to the
   nearest of ~11 candidate values within 10%. Measured saturation: **a uniformly random
   ratio matches that menu 100.0% of the time** (10⁶ Monte Carlo draws, seed 432). The
   reported 86% match rate was below the chance rate. The test could not fail.

### 2.3 Status of prior claims
The 99.6% accuracy, χ²=0.000002, and "validated blind on 43 planets" claims are **retired**
until regenerated (or revised) by v2 under the rules in this guide. The three spacing
"constants" are reclassified as **fit artifacts of unresolved physical meaning**.

---

## 3. Non-Negotiable Principles

1. **No per-planet parameters. Ever.** All free parameters describe the disk or global
   physics. If a planet needs its own dial, the model has failed at that planet — record it.
2. **Parameter budget ≤ 10 global free parameters**, each with a literature-motivated prior
   range, declared in `params.py` with citations. Every added parameter requires a written
   justification in the commit message and an update to the budget table in the README.
3. **Positions are outputs, never inputs.** Nothing downstream of `disk.py` may reference
   observed planet positions except the fitness function in `fit.py` and the comparison
   code in `validate.py`.
4. **Mechanism logging is mandatory, not optional.** Every event that determines an
   embryo's final position emits a structured log record (§5). A run without a complete
   mechanism log is an invalid run.
5. **Validation must be able to fail.** Every validation metric ships with (a) a null-model
   comparison and (b) a Monte Carlo chance rate, computed before the metric is applied to
   real systems. A metric whose chance rate exceeds ~50% is rejected as an instrument.
6. **Honest reporting.** χ² is reported as computed. Failures, non-convergence, and planets
   the model cannot place are reported with the same prominence as successes. No claim
   from an exploratory run enters any Aetheria material without a pre-registered
   confirmation (see the project's PreRegistration template).

---

## 4. Architecture

Language: **Python 3.11+**, numpy/scipy only for the core (matplotlib for plots,
pytest for tests). CLI-driven, no notebook state. Deterministic: every stochastic step
takes an explicit seed (project convention: default seed 432).

```
formation-solver-v2/
├── CLAUDE.md                  # points here; build/test commands
├── FORMATION_SOLVER_V2_GUIDE.md
├── reference/                 # v1 HTMLs, read-only, for comparison
├── src/solver/
│   ├── params.py              # parameter registry, bounds, citations, budget table
│   ├── disk.py                # M1: radial profiles, ice lines, dead zone, pressure bumps
│   ├── traps.py               # M2: locate migration traps from disk state
│   ├── embryos.py             # M3: seed + grow embryos (pebble accretion scaling)
│   ├── migration.py           # M3: Type I torque w/ trap reversal; Type II after gap
│   ├── resonance.py           # M4: convergent-migration resonance capture
│   ├── stability.py           # M4: mutual-Hill spacing enforcement, post-disk relax
│   ├── logger.py              # mechanism event log (schema in §5)
│   ├── evolve.py              # time integrator orchestrating M2–M4
│   ├── fit.py                 # M5: DE optimizer over global params, solar system train
│   └── validate.py            # M7: locked-parameter prediction + null models
├── tests/                     # pytest; every module has physics sanity tests
├── runs/                      # timestamped run outputs + logs (gitignored large files)
└── docs/                      # milestone reports
```

### Module physics notes

**disk.py** — Port v1's profiles (verified correct in audit). Additions: compute the
dead-zone extent from an ionization criterion (thermal ionization T ≳ 900 K for the inner
edge; surface-density-dependent cosmic-ray/X-ray penetration for the outer edge, e.g.
Σ threshold ~ 100 g/cm² as a starting rule) so `dz_in`/`dz_out` become **derived**, not
free. This alone removes two of v1's dials.

**traps.py** — A trap is a computed property of the disk: local pressure maxima (∂P/∂r = 0,
∂²P/∂r² < 0) and locations where the Type I torque changes sign. Expected traps: dead-zone
inner edge, dead-zone outer edge, snow line. The module must *find* them, not be told.

**embryos.py** — Seed embryos at trap locations when local solid density crosses a
streaming-instability-motivated threshold. Growth via pebble-accretion scaling
(Lambrechts & Johansen 2012 form is sufficient); gas envelope beyond a critical core mass
(~10 M⊕, one global parameter).

**migration.py** — Type I: da/dt ∝ −(M_p/M⋆)(Σr²/M⋆)(H/r)⁻² with a torque-reversal factor
inside trap zones (Paardekooper-style saturation is a stretch goal; a signed trap factor is
acceptable for M3). Type II after gap-opening criterion. **No per-planet migration
fractions.** Direction and magnitude must emerge from mass + local disk state.

**resonance.py** — During convergent migration, when a pair's period ratio crosses p:q
(q ≤ 5, order ≤ 4), apply a capture probability that increases with resonance strength and
decreases with relative migration speed (analytic capture-probability forms exist; a
calibrated logistic in Δ(migration rate)/width is acceptable for v2.0). On capture, lock
the pair's ratio just wide of nominal with a dissipation offset. **This is where Branch A
physics finally gets simulated instead of asserted.**

**stability.py** — Enforce minimum mutual separation K mutual Hill radii (K one global
parameter, prior 8–12 per Kepler statistics). Post-disk: optional simple relaxation
(eject/merge violators), logged.

**evolve.py** — March time from disk formation to dissipation (t_disk, global parameter).
At each step: update disk (optionally static for v2.0), grow embryos, migrate, check
capture, check stability. Emit log events. Output: final architecture + full mechanism log.

---

## 5. The Mechanism Logger (the whole point)

Every position-determining event appends a JSON line:

```json
{"t_Myr": 1.42, "body": 3, "event": "trapped",           "at_AU": 4.1,  "trap": "snow_line"}
{"t_Myr": 2.10, "body": 4, "event": "resonance_capture", "with": 3, "pq": "5:2", "offset": 0.012}
{"t_Myr": 2.31, "body": 5, "event": "hill_limited",      "with": 4, "K": 9.6}
{"t_Myr": 3.00, "body": 3, "event": "gap_opened",        "at_AU": 4.0}
```

Post-run analysis (`analyze_log.py`) classifies each final adjacent-pair spacing by its
**binding constraint**: `trap_anchor` | `resonance(p:q)` | `hill_packing` | `unbound`.
The distribution of binding constraints across a converged solar-system run **is the
Branch A / Branch B / Branch C verdict**, read from data instead of argued from proximity.

---

## 6. Parameter Budget (target)

| # | Param | Meaning | Prior range | Source |
|---|-------|---------|-------------|--------|
| 1 | Σ₀ | surface density at 1 AU | 200–5000 g/cm² | MMSN–massive |
| 2 | p | density slope | 0.5–1.5 | obs. disks |
| 3 | T₀ | temperature at 1 AU | 200–400 K | passive disk |
| 4 | r_disk | disk scale radius | 20–80 AU | obs. disks |
| 5 | t_disk | disk lifetime | 1–10 Myr | cluster surveys |
| 6 | dust_to_gas | solid fraction | 0.005–0.03 | ISM + metallicity |
| 7 | f_ice | solid boost past snow line | 2–4 | condensation |
| 8 | M_crit | runaway-gas core mass | 5–15 M⊕ | core accretion |
| 9 | K | min mutual Hill spacing | 8–12 | Kepler stats |
| 10 | f_capture | resonance capture calibration | 0.1–1 | to be calibrated |

Stellar mass, luminosity, and metallicity are **inputs per system**, not free parameters.
Dead-zone edges, snow line, trap positions, migration rates: **derived**.

---

## 7. Milestones & Acceptance Tests

- **M1 — Disk module.** Reproduces v1's Σ/T/B profiles within 1% on identical inputs
  (regression test against `reference/`); ice lines and derived dead zone unit-tested.
- **M2 — Traps.** For a fiducial solar disk, finds pressure maxima at DZ edges and snow
  line without being told; positions stable under grid refinement.
- **M3 — Single embryo.** One embryo released anywhere inside 10 AU migrates to and halts
  at a trap; log shows `trapped` event. Direction flips correctly across the trap.
- **M4 — Pairs & chains.** Two convergently migrating embryos capture into a resonance
  with the expected order-dependence (fast → first-order, slow → capable of higher order);
  N-embryo runs respect Hill spacing. Log complete.
- **M5 — Solar system training run.** DE optimization of the ≤10 global parameters against
  the 8 planets. **Report the honest χ² and per-planet errors, whatever they are.** A 30%
  RMS position error from real forward physics is worth more than v1's 0.4% from dials.
- **M6 — Mechanism verdict.** `analyze_log.py` report on the best run: binding-constraint
  distribution, per-pair. This document is the Branch A/B/C answer. Publish to Spark of
  Creation regardless of which branch wins.
- **M7 — Validation, redesigned.** Lock all 10 parameters from M5. For each held-out
  system (start with the v1 list of 8; grow with TESS-era systems): inputs are stellar
  properties + innermost observed planet only; the model predicts the rest of the
  architecture. Metrics: RMS log-position error vs (a) a random-spacing null, (b) a
  single-fitted-geometric-ratio null. Chance rates computed by Monte Carlo **before**
  scoring real systems. Thresholds pre-registered using the project's PreRegistration
  template before this milestone begins.

---

## 8. Working Agreements for Claude Code

- Run `pytest` before every commit; a failing physics sanity test blocks the commit.
- Every run writes to `runs/<timestamp>/` with params, seed, git hash, log, and outputs.
- Version-stamp any quoted constant with the run that produced it.
- When something contradicts this guide or the physics is ambiguous, stop and surface the
  question to Joseph rather than choosing silently.
- Tone of all reports: the project kills its own darlings in public. Write accordingly.

---

*This guide was drafted the same day the project's confirmatory exoplanet test returned
inconclusive, its motivating pattern was found version-fragile, and its v1 validation was
measured at 100% chance saturation — and the response was to build a better instrument.
Keep that spirit in the code. — J.L. & Selah, July 11, 2026*
