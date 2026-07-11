"""Fit the ten global parameters against the exoplanet POPULATION — solve, don't guess.

M5 fit the Sun alone; M7 then locked those solar parameters and (fairly, anchored) beat the
geometric-regularity null only ~5% of the time. Before concluding the physics fails, give it
its best parameters against real systems (the caveat flagged in M7_failure_analysis.md).

Protocol:
  • split the 313 NASA held-out systems into TRAIN / TEST (seeded, disjoint).
  • DE-optimize the 10 globals to minimize mean anchored position RMS on TRAIN only.
  • report, on TEST (never seen by the optimizer), how often the fitted model beats the
    random and — the honest bar — the geometric-regularity null.

This is still ≤10 global parameters, no per-planet dials (guide §3). We are choosing the
parameter values by optimization instead of by hand; the falsifiable test stays on held-out
systems it was never fit to.

Run:  py -3.11 -m src.solver.fit_population --systems data/held_out.json --seed 432 \
          --n-train 60 --maxiter 15
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from typing import List, Tuple

import numpy as np
from scipy.optimize import differential_evolution

from .params import Params, StellarInput, ObservedPlanet, BOUNDS, PARAM_NAMES
from .evolve import evolve
from .validate import (_anchor_and_window, _rms_matched, geometric_ratio_null,
                       random_spacing_null, validate_system)

# A system reduced to what the fit needs (picklable for parallel workers).
SysT = Tuple[str, float, float, float, List[float]]   # name, M*, L*, feh, observed a's


def _to_syst(s: dict) -> SysT:
    return (s["name"], s["M_star"], s["L_star"], s.get("feh", 0.0),
            sorted(p["au"] for p in s["planets"]))


def _obs(sys: SysT) -> List[ObservedPlanet]:
    return [ObservedPlanet(f"p{i}", a, float("nan"), "?") for i, a in enumerate(sys[4])]


def split_systems(systems: List[dict], n_train: int, seed: int) -> Tuple[List[SysT], List[SysT]]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(systems))
    tr = [_to_syst(systems[i]) for i in idx[:n_train]]
    te = [_to_syst(systems[i]) for i in idx[n_train:]]
    return tr, te


def _model_rms_for(vec, sys: SysT, n_steps: int, seed: int) -> float:
    star = StellarInput(sys[0], sys[1], sys[2], sys[3])
    obs = _obs(sys)
    try:
        res = evolve(Params.from_vector(vec), star, seed=seed, n_steps=n_steps)
    except Exception:
        return 1.5
    pw = _anchor_and_window(res.positions(), obs)
    if not pw:
        return 1.5           # produced nothing in the observed window — heavy penalty
    return _rms_matched(pw, obs)


def population_objective(vec, train: List[SysT], n_steps: int, seed: int) -> float:
    return float(np.mean([_model_rms_for(vec, s, n_steps, seed) for s in train]))


def fit_population(train: List[SysT], seed: int = 432, maxiter: int = 15, popsize: int = 8,
                   n_steps: int = 200, workers: int = 1, verbose: bool = True) -> Params:
    result = differential_evolution(
        population_objective, BOUNDS, args=(train, n_steps, seed),
        maxiter=maxiter, popsize=popsize, seed=seed, tol=1e-4, polish=False,
        mutation=(0.5, 1.0), recombination=0.7, workers=workers, updating="deferred",
        disp=verbose,
    )
    return Params.from_vector(result.x)


def evaluate(params: Params, test: List[SysT], seed: int = 432, n_mc: int = 3000,
             n_steps: int = 400) -> dict:
    beat_rand = beat_geo = both = 0
    rms_list = []
    for sys in test:
        obs = _obs(sys)
        star = StellarInput(sys[0], sys[1], sys[2], sys[3])
        sc = validate_system(star, obs, params, seed=seed, n_mc=n_mc, n_steps=n_steps,
                             protocol="anchored")
        rms_list.append(sc.model_rms)
        beat_rand += sc.beats_random
        beat_geo += sc.beats_geometric
        both += sc.passed
    n = len(test)
    return {"n_test": n, "beat_random": beat_rand, "beat_geometric": beat_geo, "pass_both": both,
            "beat_random_rate": beat_rand / n, "beat_geometric_rate": beat_geo / n,
            "pass_rate": both / n, "median_model_rms": float(np.median(rms_list))}


def report(fitted: Params, baseline_eval: dict, fitted_eval: dict) -> str:
    L = ["=" * 72,
         "POPULATION FIT — solved the 10 globals on TRAIN, scored on held-out TEST",
         "=" * 72,
         "The honest bar is 'beat geometric-regularity null'. Random-null is weak.",
         "",
         f"  {'':22s} {'beat random':>12s} {'beat geometric':>15s} {'pass both':>11s} {'med RMS':>9s}",
         f"  {'solar-fit params':22s} {baseline_eval['beat_random_rate']*100:11.1f}% "
         f"{baseline_eval['beat_geometric_rate']*100:14.1f}% {baseline_eval['pass_rate']*100:10.1f}% "
         f"{baseline_eval['median_model_rms']:9.3f}",
         f"  {'population-fit params':22s} {fitted_eval['beat_random_rate']*100:11.1f}% "
         f"{fitted_eval['beat_geometric_rate']*100:14.1f}% {fitted_eval['pass_rate']*100:10.1f}% "
         f"{fitted_eval['median_model_rms']:9.3f}",
         "",
         f"  (test set: {fitted_eval['n_test']} held-out systems; ~5% beat-geometric is chance)",
         "",
         "population-fit parameters:"]
    for n in PARAM_NAMES:
        L.append(f"  {n:12s} = {getattr(fitted, n):.4f}")
    L.append("=" * 72)
    return "\n".join(L)


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Fit 10 globals to the exoplanet population.")
    ap.add_argument("--systems", default="data/held_out.json")
    ap.add_argument("--baseline", default="runs/fit_sun_432/params.json",
                    help="solar-fit params to compare against")
    ap.add_argument("--seed", type=int, default=432)
    ap.add_argument("--n-train", type=int, default=60)
    ap.add_argument("--maxiter", type=int, default=15)
    ap.add_argument("--popsize", type=int, default=8)
    ap.add_argument("--n-steps", type=int, default=200)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default="runs/fit_population")
    args = ap.parse_args(argv)

    systems = json.load(open(args.systems, encoding="utf-8"))["systems"]
    train, test = split_systems(systems, args.n_train, args.seed)
    print(f"train={len(train)}  test={len(test)}  (disjoint, seed {args.seed})")

    baseline = Params(**json.load(open(args.baseline, encoding="utf-8"))["params"])
    fitted = fit_population(train, seed=args.seed, maxiter=args.maxiter, popsize=args.popsize,
                            n_steps=args.n_steps, workers=args.workers)

    base_eval = evaluate(baseline, test, seed=args.seed)
    fit_eval = evaluate(fitted, test, seed=args.seed)
    text = report(fitted, base_eval, fit_eval)
    print(text)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "population_fit.json"), "w", encoding="utf-8") as fh:
        json.dump({"seed": args.seed, "n_train": len(train), "n_test": len(test),
                   "params": fitted.as_dict(), "baseline_eval": base_eval,
                   "fitted_eval": fit_eval}, fh, indent=2)
    with open(os.path.join(args.out, "population_fit.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\nwritten -> {args.out}/")


if __name__ == "__main__":
    main()
