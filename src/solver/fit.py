"""M5 — Solar-system training run.

Differential-evolution optimization of the ≤10 GLOBAL parameters against the 8 planets.
The only place (with validate.py) allowed to read observed positions (guide §3). We report
the honest χ² and per-planet errors, whatever they are — a 30% RMS position error from real
forward physics is worth more than v1's 0.4% from per-planet dials (guide §7 M5).

Fitness is defined in log-position space and is robust to the model producing a different
NUMBER of planets than observed: predicted bodies are optimally matched to observed ones,
matched residuals contribute χ², and any count mismatch is penalized. The number of planets
the model makes is itself a reported output, not something the fitness hides.

Run:  py -3.11 -m src.solver.fit --system sun --seed 432 [--maxiter 30] [--out runs/fit_sun]
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from scipy.optimize import differential_evolution, linear_sum_assignment

from .params import Params, StellarInput, SUN, OBSERVED, BOUNDS, PARAM_NAMES
from .evolve import evolve, write_run, ForwardResult

COUNT_PENALTY = 0.30    # χ² added per unmatched planet (dex²-scale); reported separately too


@dataclass
class FitScore:
    chi2: float                     # total, including count penalty
    chi2_position: float            # matched-pair position term only
    rms_dex: float                  # RMS of log10(a_pred/a_obs) over matched pairs
    n_pred: int
    n_obs: int
    matches: List[Tuple[str, Optional[float], float]]  # (obs_name, a_pred or None, a_obs)


def _match(pred_a: List[float], obs) -> List[Tuple[str, Optional[float], float]]:
    """Optimally assign predicted radii to observed planets minimizing summed |Δ log a|.
    Returns per-observed (name, matched a_pred or None, a_obs)."""
    obs_a = [o.au for o in obs]
    if not pred_a:
        return [(o.name, None, o.au) for o in obs]
    # cost matrix in dex; Hungarian assignment on the min(n_obs, n_pred) block
    C = np.abs(np.log10(np.array(pred_a)[None, :]) - np.log10(np.array(obs_a)[:, None]))
    rows, cols = linear_sum_assignment(C)
    assigned = {int(r): int(c) for r, c in zip(rows, cols)}
    out = []
    for i, o in enumerate(obs):
        if i in assigned:
            out.append((o.name, pred_a[assigned[i]], o.au))
        else:
            out.append((o.name, None, o.au))
    return out


def score(result: ForwardResult, system: str = "sun") -> FitScore:
    obs = OBSERVED[system]
    pred_a = result.positions()
    matches = _match(pred_a, obs)

    resid = [abs(np.log10(ap / ao)) for (_, ap, ao) in matches if ap is not None]
    chi2_pos = float(np.sum(np.square(resid))) if resid else 0.0
    rms = float(np.sqrt(np.mean(np.square(resid)))) if resid else float("nan")

    n_pred, n_obs = len(pred_a), len(obs)
    # penalize BOTH unmatched observed planets and surplus predicted ones
    n_matched = sum(1 for (_, ap, _) in matches if ap is not None)
    unmatched_obs = n_obs - n_matched
    surplus_pred = max(0, n_pred - n_matched)
    chi2 = chi2_pos + COUNT_PENALTY * (unmatched_obs + surplus_pred)
    return FitScore(chi2, chi2_pos, rms, n_pred, n_obs, matches)


def _objective(vec, system, seed, n_steps, n_seeds):
    try:
        res = evolve(Params.from_vector(vec), SUN, seed=seed, n_steps=n_steps, n_seeds=n_seeds)
    except Exception:
        return 1e6
    return score(res, system).chi2


def fit(system: str = "sun", seed: int = 432, maxiter: int = 30, popsize: int = 12,
        n_steps: int = 300, n_seeds: int = 24, workers: int = 1, verbose: bool = True
        ) -> Tuple[Params, FitScore, ForwardResult]:
    result = differential_evolution(
        _objective, BOUNDS, args=(system, seed, n_steps, n_seeds),
        maxiter=maxiter, popsize=popsize, seed=seed, tol=1e-4, polish=False,
        mutation=(0.5, 1.0), recombination=0.7, workers=workers, updating="deferred",
        disp=verbose,
    )
    best = Params.from_vector(result.x)
    # final high-resolution forward run with the best params
    final = evolve(best, SUN, seed=seed, n_steps=max(n_steps, 500), n_seeds=n_seeds)
    return best, score(final, system), final


def report(best: Params, sc: FitScore) -> str:
    lines = [
        "═" * 64,
        "M5 TRAINING RESULT — solar system (honest report, guide §7)",
        "═" * 64,
        f"planets predicted: {sc.n_pred}   observed: {sc.n_obs}",
        f"χ² (total): {sc.chi2:.5f}   χ² (position only): {sc.chi2_position:.5f}",
        f"RMS position error: {sc.rms_dex:.4f} dex  "
        f"(≈ ×{10**sc.rms_dex:.2f}, i.e. {100*(10**sc.rms_dex-1):.0f}% in a)",
        "",
        "per-observed-planet match:",
        f"  {'planet':8s} {'a_obs':>8s} {'a_pred':>9s} {'Δdex':>8s}",
    ]
    for name, ap, ao in sc.matches:
        if ap is None:
            lines.append(f"  {name:8s} {ao:8.3f} {'—':>9s} {'MISSED':>8s}")
        else:
            lines.append(f"  {name:8s} {ao:8.3f} {ap:9.3f} {np.log10(ap/ao):+8.3f}")
    lines += ["", "best-fit global parameters:"]
    for n in PARAM_NAMES:
        lines.append(f"  {n:12s} = {getattr(best, n):.4f}")
    lines.append("═" * 64)
    return "\n".join(lines)


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="M5 DE training run.")
    ap.add_argument("--system", default="sun")
    ap.add_argument("--seed", type=int, default=432)
    ap.add_argument("--maxiter", type=int, default=30)
    ap.add_argument("--popsize", type=int, default=12)
    ap.add_argument("--n-steps", type=int, default=300)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    best, sc, final = fit(args.system, args.seed, args.maxiter, args.popsize,
                          args.n_steps, workers=args.workers)
    text = report(best, sc)
    print(text)

    out = args.out or os.path.join("runs", f"fit_{args.system}_{args.seed}")
    write_run(final, out)
    with open(os.path.join(out, "params.json"), "w", encoding="utf-8") as fh:
        json.dump({"system": args.system, "seed": args.seed,
                   "params": best.as_dict(),
                   "score": {"chi2": sc.chi2, "chi2_position": sc.chi2_position,
                             "rms_dex": sc.rms_dex, "n_pred": sc.n_pred, "n_obs": sc.n_obs}},
                  fh, indent=2)
    with open(os.path.join(out, "M5_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\nwritten -> {out}/")


if __name__ == "__main__":
    main()
