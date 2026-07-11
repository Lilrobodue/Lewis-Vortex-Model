"""Giant-presence prediction test — does the forward model predict WHICH systems host a
giant planet better than the known stellar baselines (metallicity, mass)?

Motivation: M7 showed the model's spacing skill is near a predictability ceiling because the
geometric-regularity null is itself Hill-packing physics (see EXPLORATORY_hill_regularity.md).
The model's *distinctive* prediction — where/whether giants form — is blind to that null, so it
was the natural place to look for un-ceilinged skill. This module runs that test honestly.

Metric: AUC (rank-based, 0.5 = chance) of a score predicting observed giant presence
(any planet with mass > threshold). Baselines: stellar [Fe/H] (the Fischer & Valenti 2005
planet-metallicity correlation) and stellar mass. Model score: the model's maximum predicted
planet mass. All out-of-sample — the model's giant production was never fit to giant presence.

Caveat (stated up front): observed giant presence is transit-truncated (cold giants beyond the
detectable window are missing), so the observed label is a lower bound. Reported anyway because
the model *over*-predicts giants, which no selection effect can rescue.

Run:  py -3.11 -m src.solver.giant_test --params runs/fit_population/population_fit.json
"""
from __future__ import annotations

import argparse
import json
import math
from typing import List

import numpy as np
from scipy.stats import mannwhitneyu, pointbiserialr

from .params import Params, StellarInput
from .evolve import evolve

GIANT_THRESHOLD_ME = 100.0     # a "giant" = any planet above this mass [M_earth] (~0.3 M_Jup)


def _has_mass(p) -> bool:
    m = p.get("mass")
    return m is not None and isinstance(m, (int, float)) and math.isfinite(m)


def auc(score: np.ndarray, label: np.ndarray) -> float:
    """Rank AUC = P(score[positive] > score[negative]); 0.5 = chance."""
    score = np.asarray(score, float)
    label = np.asarray(label)
    pos, neg = score[label == 1], score[label == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    U = mannwhitneyu(pos, neg, alternative="greater").statistic
    return float(U / (len(pos) * len(neg)))


def run(systems: List[dict], params: Params, seed: int = 432, n_steps: int = 400,
        threshold: float = GIANT_THRESHOLD_ME, flux_limited: bool = False) -> dict:
    label = np.array([1 if any(_has_mass(p) and p["mass"] > threshold for p in s["planets"])
                      else 0 for s in systems])
    feh = np.array([s.get("feh", 0.0) for s in systems])
    mstar = np.array([s["M_star"] for s in systems])

    model_max = []
    model_giant = 0
    for s in systems:
        star = StellarInput(s["name"], s["M_star"], s["L_star"], s.get("feh", 0.0))
        res = evolve(params, star, seed=seed, n_steps=n_steps, flux_limited=flux_limited)
        mmax = max([e.mass for e in res.survivors] or [0.0])
        model_max.append(mmax)
        model_giant += int(mmax > threshold)
    model_max = np.array(model_max)

    r_feh, p_feh = pointbiserialr(label, feh)
    return {
        "n_systems": len(systems),
        "threshold_Me": threshold,
        "observed_giant_rate": float(label.mean()),
        "model_giant_rate": model_giant / len(systems),
        "auc_metallicity": auc(feh, label),
        "auc_stellar_mass": auc(mstar, label),
        "auc_model_maxmass": auc(model_max, label),
        "planet_metallicity_corr_r": float(r_feh),
        "planet_metallicity_corr_p": float(p_feh),
    }


def report(res: dict) -> str:
    L = ["=" * 64,
         "GIANT-PRESENCE PREDICTION TEST",
         "=" * 64,
         f"systems: {res['n_systems']}   giant threshold: >{res['threshold_Me']:.0f} M_earth",
         f"observed giant rate: {100*res['observed_giant_rate']:.1f}%   "
         f"model giant rate: {100*res['model_giant_rate']:.1f}%",
         f"planet-metallicity correlation (data): r={res['planet_metallicity_corr_r']:+.2f} "
         f"(p={res['planet_metallicity_corr_p']:.1e})",
         "",
         "AUC (0.5 = chance, higher = better giant-host discrimination):",
         f"  [Fe/H] baseline (Fischer-Valenti): {res['auc_metallicity']:.3f}",
         f"  stellar mass baseline:             {res['auc_stellar_mass']:.3f}",
         f"  MODEL max planet mass:             {res['auc_model_maxmass']:.3f}",
         ""]
    beats = res["auc_model_maxmass"] > res["auc_metallicity"]
    L.append(f"VERDICT: model {'BEATS' if beats else 'does NOT beat'} the metallicity baseline "
             f"on giant-host prediction.")
    if res["model_giant_rate"] > 0.9:
        L.append("NOTE: the model produces a giant in nearly every system (rate ≫ observed), so "
                 "it has little discriminating power — giant formation is not selective at these "
                 "parameters (isolation-mass gate almost always open; growth not time-critical).")
    L.append("=" * 64)
    return "\n".join(L)


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Giant-presence prediction test.")
    ap.add_argument("--params", required=True)
    ap.add_argument("--systems", default="data/held_out.json")
    ap.add_argument("--seed", type=int, default=432)
    ap.add_argument("--threshold", type=float, default=GIANT_THRESHOLD_ME)
    args = ap.parse_args(argv)

    params = Params(**json.load(open(args.params, encoding="utf-8"))["params"])
    systems = json.load(open(args.systems, encoding="utf-8"))["systems"]
    res = run(systems, params, seed=args.seed, threshold=args.threshold)
    print(report(res))


if __name__ == "__main__":
    main()
