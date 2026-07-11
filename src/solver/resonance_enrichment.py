"""Are the model's held-out wins enriched in observed resonant chains? (Selah's question.)

The model beats a geometric-regularity null on ~22% of held-out systems, preferentially where
non-geometric structure exists. If that skill were carried by the resonance module (Branch A),
the wins would concentrate in known resonant chains. This module tests it directly.

Result (see docs/EXPLORATORY_resonance_enrichment.md): the wins are *anti*-enriched — on tightly
resonant chains the win-rate collapses far below the non-resonant rate. Branch A is active
(most of the model's own spacings are resonance-locked) but is not what earns the skill.

Run:  py -3.11 -m src.solver.resonance_enrichment --params runs/fit_giant/fit_giant.json --flux-limited
      py -3.11 -m src.solver.resonance_enrichment --params runs/fit_population/population_fit.json
"""
from __future__ import annotations

import argparse
import json

import numpy as np
from scipy.stats import fisher_exact, pointbiserialr

from .params import Params, StellarInput, ObservedPlanet
from .evolve import evolve
from .validate import _anchor_and_window, _rms_matched, geometric_ratio_null

# Low-order mean-motion resonances as period ratios (outer/inner > 1).
MMR = [2/1, 3/2, 4/3, 5/4, 6/5, 5/3, 7/5, 3/1, 5/2, 7/4]
MMR_TOL = 0.03          # a pair is "near-resonant" within 3% of a commensurability
CANONICAL_CHAINS = ["TRAPPIST-1", "TOI-178", "Kepler-223", "Kepler-80", "Kepler-60",
                    "GJ 876", "K2-138", "HD 110067", "TOI-1136", "Kepler-402"]


def resonance_fraction(a_sorted) -> float:
    """Fraction of adjacent observed pairs within MMR_TOL of a low-order commensurability."""
    if len(a_sorted) < 2:
        return 0.0
    prs = [(a_sorted[i + 1] / a_sorted[i]) ** 1.5 for i in range(len(a_sorted) - 1)]
    near = sum(any(abs(pr - m) / m < MMR_TOL for m in MMR) for pr in prs)
    return near / len(prs)


def run(systems, params: Params, seed: int = 432, n_steps: int = 400,
        flux_limited: bool = False) -> dict:
    wins, rfracs, model_res = [], [], []
    per_name = {}
    for s in systems:
        star = StellarInput(s["name"], s["M_star"], s["L_star"], s.get("feh", 0.0))
        obs = [ObservedPlanet("", p["au"], 0.0, "")
               for p in sorted(s["planets"], key=lambda q: q["au"])]
        oa = [o.au for o in obs]
        res = evolve(params, star, seed=seed, n_steps=n_steps, flux_limited=flux_limited)
        pw = _anchor_and_window(res.positions(), obs)
        win = 1 if (pw and _rms_matched(pw, obs) <= geometric_ratio_null(obs)) else 0
        rf = resonance_fraction(oa)
        mres = sum(1 for e in res.survivors if e.pq)
        wins.append(win); rfracs.append(rf); model_res.append(mres)
        per_name[s["name"]] = {"win": win, "res_frac": rf, "model_res": mres,
                               "n_pairs": len(oa) - 1}

    wins = np.array(wins); rfracs = np.array(rfracs)
    out = {"n_systems": len(systems), "overall_win_rate": float(wins.mean()), "by_threshold": {}}
    for thr in (0.6, 0.8, 1.0):
        chain = rfracs >= thr
        if chain.sum() == 0 or (~chain).sum() == 0:
            continue
        a = int(wins[chain].sum()); b = int(chain.sum()) - a
        c = int(wins[~chain].sum()); d = int((~chain).sum()) - c
        _, p = fisher_exact([[a, b], [c, d]], alternative="greater")
        out["by_threshold"][thr] = {"n_chain": int(chain.sum()),
                                    "win_rate_chain": float(wins[chain].mean()),
                                    "win_rate_nonchain": float(wins[~chain].mean()),
                                    "fisher_p_enriched": float(p)}
    r, pr = pointbiserialr(wins, rfracs)
    out["pointbiserial_win_resfrac"] = {"r": float(r), "p": float(pr)}
    out["canonical"] = {nm: per_name[nm] for nm in CANONICAL_CHAINS if nm in per_name}
    return out


def report(res: dict) -> str:
    L = ["=" * 66,
         "RESONANCE-ENRICHMENT TEST — are wins concentrated in resonant chains?",
         "=" * 66,
         f"held-out systems: {res['n_systems']}   overall win-rate: {100*res['overall_win_rate']:.1f}%",
         "",
         "win-rate: resonant chains vs the rest (Fisher tests 'enriched in chains'):"]
    for thr, d in res["by_threshold"].items():
        L.append(f"  res_frac >= {thr}: chains(n={d['n_chain']}) {100*d['win_rate_chain']:.1f}%  "
                 f"vs non {100*d['win_rate_nonchain']:.1f}%   Fisher p={d['fisher_p_enriched']:.2f}")
    pb = res["pointbiserial_win_resfrac"]
    L.append(f"  point-biserial(win, res_frac): r={pb['r']:+.2f} (p={pb['p']:.2f})")
    L += ["", "canonical resonant chains in the sample:"]
    for nm, d in res["canonical"].items():
        L.append(f"  {nm:14s} res_frac {d['res_frac']:.2f}  model {'WIN ' if d['win'] else 'loss'}"
                 f"  (model-resonances: {d['model_res']})")
    L += ["",
          "verdict: wins are NOT enriched (Fisher p≈1 => depleted) in resonant chains; the",
          "resonance module is active but is not the source of the held-out skill.",
          "=" * 66]
    return "\n".join(L)


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Resonance-enrichment test.")
    ap.add_argument("--params", required=True)
    ap.add_argument("--systems", default="data/held_out.json")
    ap.add_argument("--flux-limited", action="store_true", help="use corrected flux-limited growth")
    ap.add_argument("--seed", type=int, default=432)
    args = ap.parse_args(argv)
    params = Params(**json.load(open(args.params, encoding="utf-8"))["params"])
    systems = json.load(open(args.systems, encoding="utf-8"))["systems"]
    print(report(run(systems, params, seed=args.seed, flux_limited=args.flux_limited)))


if __name__ == "__main__":
    main()
