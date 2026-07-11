"""Run the pre-registered M7 confirmation (docs/PREREGISTRATION_M7.md).

Reads ONLY the frozen inputs, applies the frozen metric, and evaluates the frozen pass
criterion. Verifies the sha256 hashes recorded in the pre-registration so a changed input
cannot masquerade as the registered one. Emits a single PASS/FAIL with a binomial p-value.

Run:  py -3.11 -m src.solver.preregister_confirm
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from scipy.stats import binomtest

from .params import Params, StellarInput, ObservedPlanet
from .validate import validate_system

# Frozen references from docs/PREREGISTRATION_M7.md — must match or the run is not valid.
PARAMS_PATH = "runs/fit_population/population_fit.json"
HELDOUT_PATH = "data/heldout_confirm.json"
PARAMS_SHA16 = "66bec6c0802f819b"
HELDOUT_SHA16 = "032295d0a1f63c16"

# Frozen pass criterion.
CHANCE_P0 = 0.05
RATE_THRESHOLD = 0.15
PVALUE_THRESHOLD = 1e-3
SEED = 432
N_STEPS = 500


def _sha16(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def _wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def run() -> dict:
    # 1) integrity: the inputs must be exactly what was pre-registered
    for path, want in ((PARAMS_PATH, PARAMS_SHA16), (HELDOUT_PATH, HELDOUT_SHA16)):
        got = _sha16(path)
        if got != want:
            raise SystemExit(f"INTEGRITY FAIL: {path} sha256[:16]={got} != registered {want}. "
                             "The pre-registration is void for this input.")

    params = Params(**json.load(open(PARAMS_PATH, encoding="utf-8"))["params"])
    systems = json.load(open(HELDOUT_PATH, encoding="utf-8"))["systems"]

    # 2) frozen metric over the frozen held-out list
    beats = 0
    n = 0
    for s in systems:
        star = StellarInput(s["name"], s["M_star"], s["L_star"], s.get("feh", 0.0))
        obs = [ObservedPlanet(p["name"], p["au"], p.get("mass", float("nan")),
                              p.get("kind", "?")) for p in sorted(s["planets"], key=lambda q: q["au"])]
        sc = validate_system(star, obs, params, seed=SEED, n_mc=2000, n_steps=N_STEPS,
                             protocol="anchored")
        beats += int(sc.beats_geometric)
        n += 1

    rate = beats / n
    lo, hi = _wilson(beats, n)
    pval = binomtest(beats, n, CHANCE_P0, alternative="greater").pvalue
    passed = (rate >= RATE_THRESHOLD) and (pval < PVALUE_THRESHOLD)
    return {"n_systems": n, "beats_geometric": beats, "rate": rate,
            "wilson95": [lo, hi], "binomial_p_vs_0.05": float(pval),
            "rate_threshold": RATE_THRESHOLD, "pvalue_threshold": PVALUE_THRESHOLD,
            "passed": bool(passed),
            "params_sha16": PARAMS_SHA16, "heldout_sha16": HELDOUT_SHA16}


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    res = run()
    print("=" * 64)
    print("M7 PRE-REGISTERED CONFIRMATION (docs/PREREGISTRATION_M7.md)")
    print("=" * 64)
    print(f"held-out systems:        {res['n_systems']}")
    print(f"beat geometric null:     {res['beats_geometric']}/{res['n_systems']} "
          f"= {100*res['rate']:.1f}%   95% CI [{100*res['wilson95'][0]:.1f}, "
          f"{100*res['wilson95'][1]:.1f}]%")
    print(f"binomial p vs 5% chance: {res['binomial_p_vs_0.05']:.2e}")
    print(f"criterion: rate >= {100*res['rate_threshold']:.0f}% AND p < {res['pvalue_threshold']:.0e}")
    print(f"\nDECISION: {'PASS — H1 confirmed' if res['passed'] else 'FAIL — H1 not confirmed'}")
    print("=" * 64)

    out = "runs/prereg_M7"
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "confirmation.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print(f"written -> {out}/confirmation.json")
    return res


if __name__ == "__main__":
    main()
