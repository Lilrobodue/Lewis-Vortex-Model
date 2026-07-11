# reference/ — v1 artifacts (READ-ONLY)

These are the v1 HTML tools, preserved for regression comparison only. **Do not edit them
and do not import their formation logic.** See guide §2 for the full audit.

- `formation_solver.html` — v1 forward model. Its **disk profiles** (Σ, T, B, ice lines,
  solid enhancement, pressure bumps, H/r) are verified correct and are ported into
  `src/solver/disk.py`. Everything below the `PHYSICS-ANCHORED 8-PLANET FORMATION MODEL`
  banner (per-planet anchors `a_in`/`r_conv`/`r_trunc`, `s_gas`/`s_ice` dials, hardcoded
  `migProfile` percentages, Venus = `r_conv/1.38`) is the design v2 exists to replace and is
  **not** ported.
- `blind_validation.html` — v1 "blind" test. Measured at 100% chance saturation (a uniformly
  random ratio matched its menu 100.0% of the time). Retired; replaced by
  `src/solver/validate.py` with real null models and Monte Carlo chance rates.

Retired v1 claims (99.6% accuracy, χ²≈2e-6, "validated on 43 planets") stay retired until
regenerated under the v2 rules.
