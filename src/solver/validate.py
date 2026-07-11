"""M7 — Validation, redesigned so it *can fail* (guide §5/§7).

v1's "blind" test matched each observed ratio to the nearest of ~11 candidates within 10%
and a uniformly random ratio matched that menu 100.0% of the time — the test could not fail.
This module replaces it with a protocol built around null models and Monte-Carlo chance
rates computed BEFORE the metric touches a real system:

  metric        RMS of log10(a_pred / a_obs) over Hungarian-matched planets [dex]
  null (a)      random log-uniform spacing in the observed radial range
  null (b)      a single best-fit geometric ratio (Titius–Bode-style) — a strong null
  chance rate   P(null RMS ≤ model RMS), estimated by Monte Carlo

The model earns a system only if it beats the pre-registered threshold against BOTH nulls.
The forward model never reads observed positions (stronger than the guide's "innermost
planet only" input), so there is zero position leakage.

Real held-out validation needs an exoplanet system table (stellar props + observed planets).
None is bundled yet, so this runs as a SELF-TEST on the Sun and says so loudly. Drop a
systems JSON via --systems to validate real held-out architectures.

Run:  py -3.11 -m src.solver.validate --params runs/fit_sun_432/params.json [--mc 20000]
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from .params import Params, StellarInput, SUN, OBSERVED, ObservedPlanet
from .evolve import evolve
from .fit import _match

# ── Pre-registration (guide §7: thresholds fixed BEFORE scoring real systems) ──
PREREGISTRATION = {
    "metric": "RMS log10(a_pred/a_obs) over Hungarian-matched planets [dex]",
    "null_models": ["random log-uniform spacing", "single best-fit geometric ratio"],
    "chance_rate_estimator": "Monte Carlo, P(null RMS <= model RMS)",
    "pass_threshold": {
        "vs_random_null": "model RMS below the 5th percentile of the random-null RMS "
                          "distribution (chance rate < 0.05)",
        "vs_geometric_null": "model RMS <= geometric-null RMS",
    },
    "instrument_rejection": "if the random null's chance rate of 'matching' exceeds ~0.50 "
                            "the metric is saturated and is rejected as an instrument "
                            "(the failure mode that killed v1's blind test)",
    "seed": 432,
}


@dataclass
class SystemScore:
    system: str
    n_obs: int
    n_pred: int
    model_rms: float
    random_null_rms_p5: float          # 5th percentile of random-null RMS (lower = harder null)
    random_null_median: float
    chance_rate_vs_random: float        # P(random null RMS <= model RMS)
    geometric_null_rms: float
    beats_random: bool
    beats_geometric: bool
    passed: bool


MISS_PENALTY_DEX = 0.5
WINDOW_MARGIN = 1.3        # keep model planets within [a_in/margin, a_out*margin] of observed


def _rms_matched(pred_a: List[float], obs: List[ObservedPlanet]) -> float:
    """RMS of |log10(a_pred/a_obs)| over matched observed planets; unmatched observed planets
    contribute a fixed large residual so a model that produces too few planets is penalized."""
    matches = _match(sorted(pred_a), obs)
    resid = []
    for _, ap, ao in matches:
        resid.append(abs(np.log10(ap / ao)) if ap is not None else MISS_PENALTY_DEX)
    return float(np.sqrt(np.mean(np.square(resid))))


def _anchor_and_window(pred_a: List[float], obs: List[ObservedPlanet],
                       margin: float = WINDOW_MARGIN) -> List[float]:
    """Guide §7 protocol: the ONLY positional input is the innermost observed planet. Shift
    the predicted architecture in log-a so its innermost planet sits on the observed
    innermost, then keep only predictions inside the observed radial span (widened by
    `margin`). This removes the absolute-scale degeneracy and — crucially — stops us
    penalizing the model for predicting OUTER planets a transit survey could never detect
    (the truncation that made pure-prediction scoring unfair)."""
    if not pred_a:
        return []
    a_in = min(o.au for o in obs)
    a_out = max(o.au for o in obs)
    shift = np.log10(a_in) - np.log10(min(pred_a))
    shifted = [10 ** (np.log10(p) + shift) for p in pred_a]
    return [p for p in shifted if a_in / margin <= p <= a_out * margin]


def random_spacing_null(obs: List[ObservedPlanet], n_draw: int,
                        rng: np.random.Generator, n_mc: int) -> np.ndarray:
    """Monte-Carlo RMS distribution for n_draw planets placed log-uniformly across the
    observed radial range. Computed BEFORE comparing to the model (guide §5)."""
    lo, hi = np.log10(min(o.au for o in obs)), np.log10(max(o.au for o in obs))
    out = np.empty(n_mc)
    for i in range(n_mc):
        draw = 10 ** rng.uniform(lo, hi, size=n_draw)
        out[i] = _rms_matched(list(draw), obs)
    return out


def geometric_ratio_null(obs: List[ObservedPlanet]) -> float:
    """Best single geometric ratio (Titius–Bode-style): fit log(a) linear in planet index,
    predict a_k = a0·ratio^k, score. A strong, physically-motivated null."""
    a = np.array([o.au for o in obs])
    k = np.arange(len(a))
    # least-squares log a = b0 + b1 k  →  a0 = 10^b0, ratio = 10^b1
    b1, b0 = np.polyfit(k, np.log10(a), 1)
    pred = 10 ** (b0 + b1 * k)
    return _rms_matched(list(pred), obs)


def validate_system(star: StellarInput, obs: List[ObservedPlanet], params: Params,
                    seed: int = 432, n_mc: int = 20000, n_steps: int = 500,
                    protocol: str = "anchored", flux_limited: bool = False) -> SystemScore:
    """protocol='anchored' (guide §7 default): innermost observed planet is the only positional
    input; predictions are anchored to it and scored within the observed window.
    protocol='predict': stricter — score the raw predicted architecture with no anchor (this
    conflates the failure with transit-truncation and absolute-scale error; kept for contrast).
    """
    rng = np.random.default_rng(seed)
    result = evolve(params, star, seed=seed, n_steps=n_steps, flux_limited=flux_limited)
    pred_a = result.positions()

    if protocol == "anchored":
        pred_a = _anchor_and_window(pred_a, obs)
    n_pred = len(pred_a)

    model_rms = _rms_matched(pred_a, obs)
    # nulls drawn with the SAME planet count the model produced (fair matched comparison)
    n_draw = max(n_pred, 1)
    null_rms = random_spacing_null(obs, n_draw, rng, n_mc)
    geo_rms = geometric_ratio_null(obs)

    chance = float(np.mean(null_rms <= model_rms))
    p5 = float(np.percentile(null_rms, 5))
    beats_random = chance < 0.05
    beats_geo = model_rms <= geo_rms
    return SystemScore(
        system=star.name, n_obs=len(obs), n_pred=n_pred, model_rms=model_rms,
        random_null_rms_p5=p5, random_null_median=float(np.median(null_rms)),
        chance_rate_vs_random=chance, geometric_null_rms=geo_rms,
        beats_random=beats_random, beats_geometric=beats_geo,
        passed=bool(beats_random and beats_geo),
    )


def load_systems(path: Optional[str]) -> List[Tuple[StellarInput, List[ObservedPlanet], bool]]:
    """Return [(star, observed, is_self_test)]. Without a file, self-test on the Sun."""
    if path is None:
        return [(SUN, OBSERVED["sun"], True)]
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    systems = []
    for s in data["systems"]:
        star = StellarInput(s["name"], s["M_star"], s["L_star"], s.get("feh", 0.0))
        obs = [ObservedPlanet(p["name"], p["au"], p.get("mass", float("nan")),
                              p.get("kind", "unknown")) for p in s["planets"]]
        systems.append((star, obs, False))
    return systems


def _aggregate(scores: List[SystemScore]) -> List[str]:
    n = len(scores)
    if n == 0:
        return ["no systems scored."]
    passed = sum(s.passed for s in scores)
    beat_rand = sum(s.beats_random for s in scores)
    beat_geo = sum(s.beats_geometric for s in scores)
    med_model = float(np.median([s.model_rms for s in scores]))
    med_chance = float(np.median([s.chance_rate_vs_random for s in scores]))
    # Under a pre-registered α=0.05, a USELESS model passes 'beats random' ~5% of the time by
    # chance. So the honest headline is the pass rate vs that 5% baseline.
    exp_false = 0.05 * n
    return [
        "AGGREGATE (the M7 headline):",
        f"  systems scored: {n}",
        f"  PASS (beat BOTH nulls): {passed}/{n} ({100*passed/n:.1f}%)",
        f"  beat random null (chance<0.05): {beat_rand}/{n} ({100*beat_rand/n:.1f}%)  "
        f"— expected ~{exp_false:.0f} by chance alone at α=0.05",
        f"  beat geometric-ratio null: {beat_geo}/{n} ({100*beat_geo/n:.1f}%)",
        f"  median model RMS: {med_model:.3f} dex   median chance-rate vs random: {med_chance:.3f}",
        "",
    ]


def report(scores: List[SystemScore], self_test: bool, per_system: bool = True) -> str:
    lines = ["=" * 72,
             "M7 VALIDATION (guide §7) — pre-registered, null-anchored, can fail",
             "=" * 72]
    if self_test:
        lines += ["!! SELF-TEST ON THE SUN (the training system) — NOT held-out validation.",
                  "!! Provide --systems <file> with real exoplanet architectures for M7 proper.",
                  ""]
    lines += ["pre-registration:",
              f"  metric: {PREREGISTRATION['metric']}",
              f"  pass: beat random null (chance<0.05) AND geometric null", ""]
    if len(scores) > 1:
        lines += _aggregate(scores)
    if per_system:
        lines.append(f"  {'system':16s} {'nP/nO':>6s} {'model':>7s} {'rand p5':>8s} "
                     f"{'chance':>7s} {'geom':>7s}  verdict")
        for s in scores:
            verdict = "PASS" if s.passed else "FAIL"
            lines.append(f"  {s.system:16s} {s.n_pred:2d}/{s.n_obs:<3d} {s.model_rms:7.3f} "
                         f"{s.random_null_rms_p5:8.3f} {s.chance_rate_vs_random:7.3f} "
                         f"{s.geometric_null_rms:7.3f}  {verdict}")
    lines += ["",
              "reading: 'chance' is P(a random-spacing model scores at least as well). A high "
              "chance rate means the metric is near-saturated — exactly v1's failure mode.",
              "=" * 72]
    return "\n".join(lines)


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="M7 validation with null models + MC chance rates.")
    ap.add_argument("--params", required=True, help="locked params.json from an M5 fit")
    ap.add_argument("--systems", default=None, help="held-out systems JSON (default: Sun self-test)")
    ap.add_argument("--mc", type=int, default=20000, help="Monte Carlo draws per system")
    ap.add_argument("--seed", type=int, default=432)
    ap.add_argument("--protocol", choices=["anchored", "predict"], default="anchored",
                    help="anchored = guide §7 (innermost planet input); predict = strict no-anchor")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    with open(args.params, "r", encoding="utf-8") as fh:
        params = Params(**json.load(fh)["params"])
    systems = load_systems(args.systems)
    self_test = all(st for _, _, st in systems)

    scores = [validate_system(star, obs, params, seed=args.seed, n_mc=args.mc,
                              protocol=args.protocol)
              for star, obs, _ in systems]
    text = f"protocol: {args.protocol}\n" + report(scores, self_test)
    print(text)

    out = args.out or os.path.dirname(args.params)
    payload = {"preregistration": PREREGISTRATION, "self_test": self_test,
               "scores": [asdict(s) for s in scores]}
    with open(os.path.join(out, "M7_validation.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    with open(os.path.join(out, "M7_validation.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\nwritten -> {out}/M7_validation.(json|txt)")


if __name__ == "__main__":
    main()
