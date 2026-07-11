"""Giant-aware population fit (the scoped follow-up to giant_test.py).

After adopting flux-limited pebble accretion (embryos.py), refit the ten globals on a TRAIN
split with a two-term objective: (i) mean anchored position RMS (as in fit_population.py),
plus (ii) a light penalty for missing the observed giant-occurrence RATE. Term (ii) gives the
model a fair shot at forming giants selectively; it targets only the base RATE on TRAIN, so
the held-out giant-presence AUC (discrimination) and the held-out M7 positions remain honest
out-of-sample tests.

Still ≤10 global parameters, no per-planet dials. LAMBDA_GIANT is a single reported weight.

Run:  py -3.11 -m src.solver.fit_giant --systems data/held_out.json --seed 432 \
          --n-train 60 --maxiter 20 --workers -1
"""
from __future__ import annotations

import argparse
import json
import math
import os
from typing import List, Tuple

import numpy as np
from scipy.optimize import differential_evolution

from .params import Params, StellarInput, ObservedPlanet, BOUNDS, PARAM_NAMES
from .evolve import evolve
from .validate import _anchor_and_window, _rms_matched
from .fit_population import evaluate as evaluate_positions
from .giant_test import run as giant_run, GIANT_THRESHOLD_ME

LAMBDA_GIANT = 0.5      # weight of the giant-rate term relative to position RMS (reported)

# Train tuple: (name, M*, L*, feh, [observed a's], observed_giant_bool)
GSysT = Tuple[str, float, float, float, List[float], int]


def _has_mass(p):
    m = p.get("mass"); return m is not None and isinstance(m, (int, float)) and math.isfinite(m)


def _to_gsyst(s: dict, thr: float) -> GSysT:
    giant = 1 if any(_has_mass(p) and p["mass"] > thr for p in s["planets"]) else 0
    return (s["name"], s["M_star"], s["L_star"], s.get("feh", 0.0),
            sorted(p["au"] for p in s["planets"]), giant)


def split(systems: List[dict], n_train: int, seed: int, thr: float):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(systems))
    tr = [_to_gsyst(systems[i], thr) for i in idx[:n_train]]
    te_idx = idx[n_train:]
    return tr, [systems[i] for i in te_idx]


def giant_objective(vec, train: List[GSysT], obs_rate: float, n_steps: int, seed: int,
                    lam: float, thr: float) -> float:
    params = Params.from_vector(vec)
    rms_terms = []
    model_giants = []
    for name, M, L, feh, a_obs, _g in train:
        star = StellarInput(name, M, L, feh)
        obs = [ObservedPlanet(f"p{i}", a, float("nan"), "?") for i, a in enumerate(a_obs)]
        try:
            res = evolve(params, star, seed=seed, n_steps=n_steps, flux_limited=True)
        except Exception:
            rms_terms.append(1.5); model_giants.append(1); continue
        pw = _anchor_and_window(res.positions(), obs)
        rms_terms.append(_rms_matched(pw, obs) if pw else 1.5)
        mmax = max([e.mass for e in res.survivors] or [0.0])
        model_giants.append(1 if mmax > thr else 0)
    pos = float(np.mean(rms_terms))
    giant_rate = float(np.mean(model_giants))
    return pos + lam * abs(giant_rate - obs_rate)


def fit(train: List[GSysT], obs_rate: float, seed: int = 432, maxiter: int = 20,
        popsize: int = 8, n_steps: int = 200, workers: int = 1, lam: float = LAMBDA_GIANT,
        thr: float = GIANT_THRESHOLD_ME, verbose: bool = True) -> Params:
    result = differential_evolution(
        giant_objective, BOUNDS, args=(train, obs_rate, n_steps, seed, lam, thr),
        maxiter=maxiter, popsize=popsize, seed=seed, tol=1e-4, polish=False,
        mutation=(0.5, 1.0), recombination=0.7, workers=workers, updating="deferred",
        disp=verbose,
    )
    return Params.from_vector(result.x)


def _positions_tuples(systems: List[dict]):
    from .fit_population import _to_syst
    return [_to_syst(s) for s in systems]


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Giant-aware population fit + held-out eval.")
    ap.add_argument("--systems", default="data/held_out.json")
    ap.add_argument("--seed", type=int, default=432)
    ap.add_argument("--n-train", type=int, default=60)
    ap.add_argument("--maxiter", type=int, default=20)
    ap.add_argument("--popsize", type=int, default=8)
    ap.add_argument("--n-steps", type=int, default=200)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--lam", type=float, default=LAMBDA_GIANT)
    ap.add_argument("--thr", type=float, default=GIANT_THRESHOLD_ME)
    ap.add_argument("--out", default="runs/fit_giant")
    args = ap.parse_args(argv)

    systems = json.load(open(args.systems, encoding="utf-8"))["systems"]
    train, test = split(systems, args.n_train, args.seed, args.thr)
    obs_rate = float(np.mean([g[5] for g in train]))
    print(f"train={len(train)}  test={len(test)}  train giant-rate={obs_rate:.2f}  lam={args.lam}")

    fitted = fit(train, obs_rate, seed=args.seed, maxiter=args.maxiter, popsize=args.popsize,
                 n_steps=args.n_steps, workers=args.workers, lam=args.lam, thr=args.thr)

    # held-out evaluation: POSITIONS (M7) and GIANTS (AUC), both on the test split only,
    # using the corrected flux-limited growth the model was fit with.
    pos_eval = evaluate_positions(fitted, _positions_tuples(test), seed=args.seed, n_mc=3000,
                                  flux_limited=True)
    giant_eval = giant_run(test, fitted, seed=args.seed, threshold=args.thr, flux_limited=True)

    print("\n" + "=" * 64)
    print("GIANT-AWARE REFIT — held-out results (test split never seen)")
    print("=" * 64)
    print("positions (M7):")
    print(f"  beat geometric: {100*pos_eval['beat_geometric_rate']:.1f}%   "
          f"median RMS {pos_eval['median_model_rms']:.3f}   (confirmed model: 23.6% / 0.05)")
    print("giants:")
    print(f"  model giant rate {100*giant_eval['model_giant_rate']:.1f}% "
          f"(observed {100*giant_eval['observed_giant_rate']:.1f}%)")
    print(f"  AUC  metallicity {giant_eval['auc_metallicity']:.3f}  "
          f"model {giant_eval['auc_model_maxmass']:.3f}")
    print("fitted params:")
    for n in PARAM_NAMES:
        print(f"  {n:12s} = {getattr(fitted, n):.4f}")
    print("=" * 64)

    os.makedirs(args.out, exist_ok=True)
    json.dump({"seed": args.seed, "lam": args.lam, "n_train": len(train), "n_test": len(test),
               "params": fitted.as_dict(), "positions_eval": pos_eval, "giant_eval": giant_eval},
              open(os.path.join(args.out, "fit_giant.json"), "w"), indent=2)
    print(f"written -> {args.out}/fit_giant.json")


if __name__ == "__main__":
    main()
