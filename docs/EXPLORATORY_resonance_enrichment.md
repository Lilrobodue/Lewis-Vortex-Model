# EXPLORATORY — is the marginal 22% earned by the resonance module? (No — inverted.)

> **Status: EXPLORATORY.** Selah's question, offered as teammate: the model wins preferentially
> where non-geometric structure exists (room↔wins r = +0.39) — *are those wins enriched in known
> resonant chains?* If so, the resonance module (the last living piece of Branch A) would be what
> earns the skill above the Hill floor. This is that one-afternoon analysis. Reproduce inline
> below; data = `data/held_out.json`, params = `runs/fit_giant/fit_giant.json` (the adopted 22%
> model) and `runs/fit_population/population_fit.json` (the 24% legacy model).

## Task 1 — the M6 binding-constraint distribution, quantified

**Trained solar run** (`analyze_log runs/fit_sun_432/mechanism.jsonl`): 3 planets, 2 adjacent
pairs, **both `trap_anchor` — 100% Branch B**. `resonance` 0%, `hill_packing` 0%. Ten
`resonance_capture` events fired during evolution but **none survived** to the final architecture
(they merged). The trained solar system's spacing is entirely boundary-anchored.

**Population level** (all 2120 adjacent pairs across the 313 held-out corrected-model runs), the
model's *own* spacings are dominated by resonance:

| binding constraint | share of model spacings |
|---|---|
| resonance (Branch A) | **71.1%** |
| trap_anchor (Branch B) | 12.2% |
| unbound | 16.6% |
| hill_packing (Branch C) | 0.1%* |

*The crude population classifier under-counts Hill-packing (post-relaxation pairs sit ≥K apart
and fall to "unbound"); the trap-vs-resonance split is the reliable part. **Branch A is by far the
model's most *active* mechanism.**

## Task 2 — but the SKILL is not resonant. It's anti-resonant.

Testing whether held-out wins (model beats the geometric null) concentrate in observed resonant
chains. Resonance score = fraction of a system's adjacent pairs within 3% of a low-order MMR
(2:1, 3:2, 4:3, 5:4, 6:5, 5:3, 5:2, 7:5, 3:1, 7:4).

| system class | corrected model (22%) | legacy model (24%) |
|---|---|---|
| overall win-rate | 21.7% | 26.8% |
| res_frac ≥ 0.8 (strong chains) | **2.1%** | **8.5%** |
| res_frac < 0.8 | 25.2% | 30.1% |
| **perfect chains (res_frac = 1.0)** | **1/45 = 2%** | **3/45 = 7%** |

Fisher exact for "wins **enriched** in chains": p ≈ 1.0 (i.e. the opposite). Point-biserial
(win, res_frac) = −0.10. **Robust across both models: the model's win-rate on tightly resonant
chains collapses to a small fraction of its rate on non-resonant systems.** The resonant chains
are the model's **worst** regime, not its source of skill.

**Named canonical chains** (adopted model): losses on **TOI-178, Kepler-223, HD 110067,
Kepler-80, Kepler-60, GJ 876, K2-138, TOI-1136** — 8 of 9 in the sample; the lone win is
Kepler-402 (res_frac 0.67). TRAPPIST-1 is not in the dwarf held-out set. On several it *fires*
abundant resonances (Kepler-223: 10 model-resonances; HD 110067: 8) and **still loses** — the
locks form at the wrong ratios/scale to reproduce the real ultra-compact chain.

## What this means

Selah's hypothesis is not just refuted — it's **inverted**, and the inversion is informative:

- The resonance module (**Branch A**) is the model's *most active* mechanism (71% of its
  spacings) but earns **negative** marginal value where it matters: on real resonant chains the
  model performs *worst*. It produces resonances indiscriminately, at ratios that happen to be
  near-geometric (3:2, 4:3 …), which is why they blur into the Hill-regular / geometric spacing
  that the ceiling analysis already identified as the model's real skill.
- The marginal ~22% therefore comes from **non-resonant, near-geometric (boundary/Hill-regular)
  systems** — Branch B/C territory — **not** from reproducing Branch A resonant chains.
- The physical reason is legible: the model's traps sit at solar-scale radii (snow line,
  dead-zone edges), so its resonant captures land at wide spacings; the observed chains
  (TOI-178, HD 110067) are sub-AU, tightly packed at *specific* commensurabilities the static-disk
  model does not place correctly.

**Bottom line for the Branch verdict:** the last living piece of Branch A is *active but not
skill-earning*, and is the model's blind spot precisely on the systems built to showcase it. The
confirmed spacing skill rests on boundary-anchored, Hill-regular structure — not on resonance.

## Reproduce
```python
# per system: model win (anchored beat-geometric) vs observed resonance fraction
from src.solver.evolve import evolve
from src.solver.validate import _anchor_and_window, _rms_matched, geometric_ratio_null
# win = _rms_matched(_anchor_and_window(evolve(params, star, flux_limited=True).positions(), obs), obs)
#        <= geometric_ratio_null(obs)
# res_frac = fraction of adjacent observed period ratios within 3% of a low-order MMR
# → wins are DEPLETED, not enriched, in high-res_frac systems (Fisher p ≈ 1.0)
```
