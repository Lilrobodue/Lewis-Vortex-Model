"""Run the pre-registered M7 v2 confirmation (docs/PREREGISTRATION_M7v2.md) — the
corrected-physics (flux-limited growth) model. Verifies the frozen sha256 hashes before
scoring, applies the frozen pass criterion, and emits a single PASS/FAIL with a binomial
p-value. Mirrors preregister_confirm.py but for the v2 params and flux_limited=True.

Run:  py -3.11 -m src.solver.preregister_confirm_v2
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from scipy.stats import binomtest

from .params import Params, StellarInput, ObservedPlanet
from .validate import validate_system
from .preregister_confirm import _wilson

PARAMS_PATH = "runs/fit_giant/fit_giant.json"
HELDOUT_PATH = "data/heldout_confirm_v2.json"
PARAMS_SHA16 = "af23af79e5518638"
HELDOUT_SHA16 = "d24deda2aba2b5b6"

CHANCE_P0 = 0.05
RATE_THRESHOLD = 0.15
PVALUE_THRESHOLD = 1e-3
SEED = 432
N_STEPS = 500


def _sha16(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def run() -> dict:
    for path, want in ((PARAMS_PATH, PARAMS_SHA16), (HELDOUT_PATH, HELDOUT_SHA16)):
        got = _sha16(path)
        if got != want:
            raise SystemExit(f"INTEGRITY FAIL: {path} sha256[:16]={got} != registered {want}.")

    params = Params(**json.load(open(PARAMS_PATH, encoding="utf-8"))["params"])
    systems = json.load(open(HELDOUT_PATH, encoding="utf-8"))["systems"]

    beats = 0
    n = 0
    for s in systems:
        star = StellarInput(s["name"], s["M_star"], s["L_star"], s.get("feh", 0.0))
        obs = [ObservedPlanet(p["name"], p["au"], p.get("mass", float("nan")),
                              p.get("kind", "?")) for p in sorted(s["planets"], key=lambda q: q["au"])]
        sc = validate_system(star, obs, params, seed=SEED, n_mc=1500, n_steps=N_STEPS,
                             protocol="anchored", flux_limited=True)     # corrected physics
        beats += int(sc.beats_geometric)
        n += 1

    rate = beats / n
    lo, hi = _wilson(beats, n)
    pval = binomtest(beats, n, CHANCE_P0, alternative="greater").pvalue
    passed = (rate >= RATE_THRESHOLD) and (pval < PVALUE_THRESHOLD)
    return {"model": "corrected-physics (flux-limited growth)", "n_systems": n,
            "beats_geometric": beats, "rate": rate, "wilson95": [lo, hi],
            "binomial_p_vs_0.05": float(pval), "rate_threshold": RATE_THRESHOLD,
            "pvalue_threshold": PVALUE_THRESHOLD, "passed": bool(passed),
            "params_sha16": PARAMS_SHA16, "heldout_sha16": HELDOUT_SHA16}


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    res = run()
    print("=" * 64)
    print("M7 v2 PRE-REGISTERED CONFIRMATION — corrected-physics model")
    print("=" * 64)
    print(f"held-out systems:        {res['n_systems']}")
    print(f"beat geometric null:     {res['beats_geometric']}/{res['n_systems']} "
          f"= {100*res['rate']:.1f}%   95% CI [{100*res['wilson95'][0]:.1f}, "
          f"{100*res['wilson95'][1]:.1f}]%")
    print(f"binomial p vs 5% chance: {res['binomial_p_vs_0.05']:.2e}")
    print(f"criterion: rate >= {100*res['rate_threshold']:.0f}% AND p < {res['pvalue_threshold']:.0e}")
    print(f"\nDECISION: {'PASS — H1 confirmed' if res['passed'] else 'FAIL — H1 not confirmed'}")
    print("=" * 64)
    out = "runs/prereg_M7v2"
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, "confirmation.json"), "w"), indent=2)
    print(f"written -> {out}/confirmation.json")
    return res


if __name__ == "__main__":
    main()
