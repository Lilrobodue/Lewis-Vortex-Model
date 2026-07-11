# Lewis-Vortex-Model — Formation Solver v2

A forward-physics planetary-formation solver: **disk boundaries in, architecture out**, with
every position-determining mechanism logged as it acts. It exists to test one falsifiable
claim (guide §1):

> Do disk boundaries + migration + resonance capture + Hill stability produce the observed
> spacing of planetary systems, **without per-planet tuning?**

The full specification is [FORMATION_SOLVER_V2_GUIDE.md](FORMATION_SOLVER_V2_GUIDE.md).
Build/test/run commands are in [CLAUDE.md](CLAUDE.md). The v1 tools live read-only in
[reference/](reference/) — their disk physics was kept; their per-planet dials and
100%-chance-saturated "blind" test were not (guide §2).

## Parameter budget (target ≤ 10 global free parameters)

Every free parameter describes the **disk or global physics** — none describes a planet.
Enforced by `PARAM_BUDGET` in [src/solver/params.py](src/solver/params.py) and a test.

| # | Param | Meaning | Prior range | Source |
|---|-------|---------|-------------|--------|
| 1 | `sigma0` | gas surface density at 1 AU (g/cm²) | 200–5000 | MMSN–massive disk |
| 2 | `p` | surface-density slope | 0.5–1.5 | observed disks (Andrews+ 2010) |
| 3 | `T0` | temperature at 1 AU (K) | 200–400 | passive irradiated disk |
| 4 | `r_disk` | disk scale radius (AU) | 20–80 | observed disks |
| 5 | `t_disk` | disk lifetime (Myr) | 1–10 | cluster surveys (Haisch+ 2001) |
| 6 | `dust_to_gas` | solid mass fraction | 0.005–0.03 | ISM + metallicity |
| 7 | `f_ice` | solid boost past snow line | 2–4 | condensation |
| 8 | `M_crit` | runaway-gas core mass (M⊕) | 5–15 | core accretion (Pollack+ 1996) |
| 9 | `K` | min mutual-Hill spacing | 8–12 | Kepler statistics (Pu & Wu 2015) |
| 10 | `f_capture` | resonance-capture calibration | 0.1–1 | calibrated |

**Inputs per system (not free parameters):** stellar mass, luminosity, metallicity.
**Derived (never free):** dead-zone edges, snow/ice lines, trap positions, migration rates.

Adding a parameter requires a written justification in the commit message and an update to
this table (guide §3.2).

## Status

Milestones M1–M7 implemented and run; 48 tests pass. Full write-up:
[docs/M1-M7_milestone_report.md](docs/M1-M7_milestone_report.md).

**Held-out result (M7, the falsifiable test).** On **313 real multi-planet systems** from the
NASA Exoplanet Archive, scored fairly (guide's innermost-planet anchor) with the ten globals
**solved for** on a train split and confirmed on a disjoint, hash-frozen held-out split
(pre-registered, `preregister_confirm_v2.py`):

- **the model beats a geometric-regularity null 22.1%** of held-out systems (p = 5×10⁻²¹),
  ≈4–5× the chance baseline — **pre-registered and confirmed** (corrected-physics model;
  the legacy model confirmed at 23.6%, [PREREGISTRATION_M7.md](docs/PREREGISTRATION_M7.md)).

Two legs were tested to conclusion:
- **Spacing — earned (partial).** The skill sits near a *predictability ceiling*: the strong
  geometric null is itself Hill-regulated "peas-in-a-pod" physics, which the model reproduces
  ([docs/M7_failure_analysis.md](docs/M7_failure_analysis.md),
  [docs/EXPLORATORY_hill_regularity.md](docs/EXPLORATORY_hill_regularity.md)).
- **Giant demographics — failed.** The model does not predict which systems host giants beyond
  stellar metallicity + mass ([docs/EXPLORATORY_giant_refit.md](docs/EXPLORATORY_giant_refit.md)).

The full synthesis is in [FINDINGS.md](FINDINGS.md). With global (never per-planet) parameters
solved rather than borrowed, disk-boundary physics reproduces held-out exoplanet *spacing*
significantly better than trivial regularity, but adds no independent information about planet
*demographics*. No retired v1 number (99.6%, χ²≈2e-6) is revived.
