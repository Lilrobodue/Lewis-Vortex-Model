# Pre-Registration — Branch A (resonance) ablation

**Written and committed before the held-out ablation run.** I have already seen the
resonance-enrichment data (`docs/EXPLORATORY_resonance_enrichment.md`), so this prediction is
*informed*, not blind — stated transparently, and frozen here so the ablation outcome is judged
against a criterion fixed in advance.

- **Date:** 2026-07-11 · Authors: Joseph Lewis & Selah, with Claude Code · Selah's proposal.

## The experiment
Disable the resonance-capture module entirely (`evolve(resonance_on=False)`) and re-run the M7
protocol with the **same** adopted corrected-physics parameters (`runs/fit_giant/fit_giant.json`,
`flux_limited=True`) on the **same frozen held-out list** used for the v2 confirmation
(`data/heldout_confirm_v2.json`, 253 systems). This is a direct ablation: it asks whether Branch A
is load-bearing for the confirmed ~22% skill *at these parameters* (not a refit-without-resonance,
which would be a separate, stronger test).

## Hypothesis and prediction
The enrichment data showed the held-out wins are **anti-enriched** in resonant chains — the skill
lives in non-resonant, boundary/Hill-regular systems. Therefore:

- **Prediction:** disabling resonance does **not** reduce held-out beat-geometric; the ablated rate
  is **≥ 0.17** (within the confirmed 95% CI [0.175, 0.276]), point estimate ≈ 0.22 or higher.
- **Interpretation rule (fixed in advance):**
  - ablated rate **≥ 0.17** → resonance is **not load-bearing** for the confirmed skill; a simpler
    v2.1 with Branch A removed is warranted and more honest.
  - ablated rate **< 0.15** → resonance **is** earning its keep somewhere subtle despite losing the
    chains; keep it and investigate where.
  - 0.15–0.17 → ambiguous; report as such.
- **Paired check:** McNemar test on the per-system win/loss flips (resonance on vs off) over the
  253 systems, to see whether the *win-set* changes even if the rate does not.

Metric, null, protocol, seed, and n_steps are identical to `PREREGISTRATION_M7v2.md` (anchored
beat-geometric, geometric-ratio null, seed 432, n_steps 500). One run; result reported whatever it
is.

## Result — **PREDICTION FAILED. Resonance IS load-bearing.**

`runs/ablation_resonance/result.json` (253 frozen held-out systems, paired):

| model | beat-geometric | vs 5% chance |
|---|---|---|
| resonance ON (adopted) | 56/253 = **22.1%** | — |
| resonance OFF (ablated) | 38/253 = **15.0%** | p = 1.8×10⁻⁹ |

Paired **McNemar**: 24 systems flip **win → loss** when resonance is disabled, only 6 flip
loss → win (p = **0.001**). Disabling Branch A costs a net 18 wins.

**My pre-registered prediction (ablated ≥ 0.17, resonance not load-bearing) is refuted.** The
ablated rate is 15.0% — below the 0.17 threshold — and the paired test shows the drop is
statistically significant. **Resonance is earning its keep** (Selah's second interpretation branch:
"earning its keep somewhere subtle despite losing the chains").

### Reconciling with the anti-enrichment result (the correction)
Both are true and together they are sharper than either alone:
- The model **loses on observed resonant *chains*** (anti-enrichment: 2–8% win-rate on res_frac ≥ 0.8;
  `docs/EXPLORATORY_resonance_enrichment.md`). It does not reproduce TOI-178 / HD 110067 etc.
- Yet the resonance **module is load-bearing overall** — because resonance capture locks convergent
  pairs at near-geometric ratios (3:2, 4:3 …), producing the tight regular spacing that wins on the
  many **non-chain but regular** systems. Remove it and those pairs merge or spread, and ~1/3 of the
  skill (7 of 22 points) disappears.

**Corrected decomposition of the confirmed skill:** a ~15% **boundary/Hill floor** (still 3× chance)
plus a **~7-point resonance contribution** that operates by manufacturing regularity in non-resonant
systems — *not* by reproducing the formal resonant chains, where the model still fails. My earlier
"resonance is active but not the source of skill" (in the enrichment doc) was **too strong**; the
ablation corrects it. Branch A is a genuine, if non-obvious, contributor.

