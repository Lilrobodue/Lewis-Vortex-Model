# M7 Failure Analysis — where the 1/313 came from, and what's really going on

Joseph's read on the first M7 result ("1/313 says something… like things got moved around in
the ordered chaos over time") kicked off this investigation. He was right that 1/313 was too
clean to be a plain physics failure. It turned out to be **two different things stacked on top
of each other**, and separating them gives a much sharper — and more honest — verdict.

Reproduce: `data/held_out.json` (313 NASA systems), locked params `runs/fit_sun_432/params.json`.
The diagnostics below are one-off scripts; the conclusions are baked into `validate.py`
(`--protocol anchored` vs `--protocol predict`).

## Finding 1 — Migration does NOT scramble the pattern. It improves it.

Testing the "ordered chaos moved things around" hypothesis directly, comparing to observed
architecture (pattern-only RMS, i.e. after removing any uniform scale offset):

| architecture | median pattern RMS vs observed |
|---|---|
| pristine **trap skeleton** (pure boundaries, pre-dynamics) | 0.786 dex |
| **migrated final** planets (post migration + resonance + Hill) | **0.483 dex** |

The dynamics make the match **better**, not worse. The boundaries alone are too sparse (3 traps)
to be an architecture; migration + packing fills in a closer one. So the failure is *not*
chaos destroying a good boundary pattern — the opposite.

## Finding 2 — Most of the raw error was a scoring artifact, not physics.

Decomposing the raw per-system log-residuals into a uniform shift (scale) + spread (pattern):

- raw RMS **0.842 dex** → after removing the optimal uniform shift, spread is **0.483 dex**.
  ~Half the error is a single **scale offset**.
- median signed shift **+0.61 dex**, and **91%** of systems shift the same way: the model puts
  planets **~4× too far OUT**.
- ordering correlation model-vs-observed: **0.83** — the *sequence* is mostly right.

Why the consistent outward push? These are overwhelmingly **transit-detected** systems
(Kepler/TESS), which only see close-in planets (< ~0.5 AU). The forward model predicts a *full*
architecture out to ~30 AU. Matching the model's outer planets against an inner-truncated
observed list, with no anchor, manufactures the outward bias and a surplus-planet penalty. The
original `validate.py` used exactly this unfair "pure prediction" scoring → **1/313**.

The guide's actual M7 protocol says the input is *stellar properties + the innermost observed
planet*. Using that (anchor the model's innermost planet to the observed innermost, score only
within the observed window — `--protocol anchored`):

| protocol | beat random null | interpretation |
|---|---|---|
| `predict` (no anchor, full architecture) | **1/313 (0.3%)** | conflates physics with truncation + scale |
| `anchored` (guide §7, innermost planet input) | **186/313 (59%)** | the fair test of relative architecture |

So against a uniform-random null the model looks *good* once scored fairly. 1/313 was mostly a
methodology artifact. **Joseph's instinct was correct.**

## Finding 3 — …but it still fails the honest null. (Darling killed.)

A uniform-random null is weak: real planetary systems are more *regular* than uniform (the
"peas in a pod" / near-constant log-spacing seen by Weiss+ 2018), so almost any evenly-spaced
guess beats it. The honest null is a **single geometric ratio** (Titius–Bode-style regularity).
In the fair anchored frame:

| null model | model beats it |
|---|---|
| random log-uniform spacing | **59%** |
| **geometric-ratio regularity** | **5.4%** ≈ chance |
| **both** (pre-registered pass) | **2.9%** |

**A one-parameter "planets are evenly spaced in log" model out-predicts the entire
disk-boundary + migration + resonance + Hill machinery.** The boundary physics adds essentially
nothing over trivial regularity. This is the same failure mode that killed v1's blind test —
beating a weak null is not evidence; the strong null exposes it.

## Finding 4 — It was the PARAMETERS, not the physics. (Verdict flips.)

Joseph's next correction: *"can't we take the parameters and solve for the values, instead of
guessing?"* Two hand-guessed physics tweaks (a finite pebble budget; Kelvin–Helmholtz-limited
gas accretion) were tried and **measured to do nothing** — still 5.7% beat-geometric, still
400 M⊕ giants. Guessing constants is the v1 disease. So instead we *solved*: DE-fit the ten
globals against a TRAIN split of the real systems, then scored on a disjoint held-out TEST split
(`fit_population.py`).

| on held-out TEST systems | beat geometric-regularity null | median position RMS |
|---|---|---|
| solar-fit parameters (M5) | 5.7% (≈ chance) | 0.408 dex |
| **population-fit parameters** | **26.9% (≈ 5× chance)** | **0.053 dex** |

Robust across 4 independent splits (25.9–28.9%), ~16σ over the 5% baseline, out-of-sample. The
optimizer found the physics story on its own: **dust_to_gas ≈ 0.009** (near minimum — low solids
suppress the giant overproduction that gapped the systems) and **f_capture ≈ 0.92** (near maximum
— strong resonance capture builds the tight regular chains). Exactly the levers hand-tuning
failed to find.

So the earlier "physics fails" reading was **premature** — it was really *"solar parameters don't
transfer to the exoplanet population."* Given its own best global parameters, the boundary +
migration + resonance + Hill machinery beats a one-parameter geometric ratio ~5× more often than
chance on systems it was never fit to.

## The verdict, precisely stated (updated)

Against the guide's central question — *do disk boundaries + migration + resonance + Hill produce
the observed spacing without per-planet tuning?* — the honest answer from 313 real held-out
systems is now:

> With ten GLOBAL parameters (no per-planet dials) **solved for** rather than borrowed from the
> Sun, the model reproduces held-out exoplanet architectures well enough to beat a strong
> geometric-regularity null **~27%** of the time — five times the chance rate, stable out-of-sample.
> That is real, falsifiable, *partial* skill: the boundary-organizes-architecture principle earns a
> genuine — if not dominant — planetary leg. The remaining ~73% where a simple geometric ratio wins
> says regularity is still a powerful descriptor the physics does not fully capture.

## Honest caveats on the positive result
1. **Partial, not dominant.** 27% beat-geometric means most systems are still described at least as
   well by a single ratio. This is encouraging evidence, not a settled theory.
2. **The random-spacing null is count-unstable** — its difficulty scales with how many planets the
   model puts in-window, so "beat random" swung *down* (56→42%) even as skill rose. Trust the
   geometric null; consider replacing the random null with a count-independent version.
3. **Pre-registration still required (guide §6/§8).** This is a strong *exploratory* result from a
   train/test protocol. No number here enters Aetheria material without a pre-registered
   confirmation run on a frozen parameter set and a frozen held-out list.
4. **One optimizer, one data snapshot.** A single DE seed and the 2026-07-11 PSCompPars pull;
   worth repeating across seeds and archive versions.

## Caveats / open questions (what would change this)

1. **Wrong parameter point, not necessarily wrong physics.** M7 locks *solar*-fit parameters.
   A joint fit across many systems is the fair next test — the physics deserves its best
   parameters before we retire it.
2. **The geometric null is strong** — it uses the observed span (two anchors) while the model
   uses one (innermost). A fully like-for-like comparison (both given only the innermost planet
   + one global ratio) is the cleaner adjudication and is worth building.
3. **Transit truncation** still shapes even the anchored test; a radial-velocity or
   directly-imaged subsample (fuller architectures) would test the outer disk the model actually
   predicts.
4. **Regularity may itself be a boundary signature.** "Beaten by a geometric ratio" is only
   damning if regularity is *not* what resonant-chain/Hill-packing physics produces. Whether the
   model's own ratios cluster near the geometric ratio (right mechanism, wrong sharpness) vs
   scatter around it (wrong mechanism) is the next diagnostic — and would distinguish "close but
   blunt" from "wrong."
