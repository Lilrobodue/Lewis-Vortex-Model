"""Build a held-out validation set from the NASA Exoplanet Archive.

Reads the Planetary Systems Composite Parameters (PSCompPars) CSV and emits the systems JSON
that `validate.py` consumes: multi-planet systems around main-sequence-ish hosts, with each
planet's semi-major axis and the host's mass / luminosity / metallicity. Luminosity is
derived from effective temperature and radius (L = R² (T/T_sun)⁴) since the table has no
direct L column.

Selection (all at the author's discretion, documented so it is auditable):
  • ≥ MIN_PLANETS planets with a measured semi-major axis (need an architecture to predict)
  • host mass, T_eff, radius all present
  • dwarf hosts only (log g ≥ MIN_LOGG) — evolved giants are not planet-formation disks
  • host mass in [M_LO, M_HI] M_sun — the regime the disk model is meant for

These are genuinely held out: the forward model never sees a planet position; M7 predicts the
architecture from stellar inputs alone and scores against these observed positions.

Run:  py -3.11 -m src.solver.nasa_systems --csv PSCompPars_*.csv --out data/held_out.json
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

T_SUN = 5772.0            # K, IAU nominal solar effective temperature

MIN_PLANETS = 3
MIN_LOGG = 4.0           # dwarf cut (giants have log g ≲ 3.5)
M_LO, M_HI = 0.1, 3.0    # solar-mass units


def _fnum(x: str) -> Optional[float]:
    try:
        v = float(x)
        return v
    except (TypeError, ValueError):
        return None


def _classify(mass_Me: Optional[float]) -> str:
    if mass_Me is None:
        return "unknown"
    if mass_Me < 2.0:
        return "rocky"
    if mass_Me < 50.0:
        return "ice"
    return "gas"


def read_rows(csv_path: str) -> List[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def build_systems(csv_path: str, min_planets: int = MIN_PLANETS,
                  max_systems: Optional[int] = None) -> List[dict]:
    rows = read_rows(csv_path)
    by_host: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        by_host[r["hostname"]].append(r)

    systems = []
    for host, planets in sorted(by_host.items()):
        good = [p for p in planets if _fnum(p["pl_orbsmax"]) and _fnum(p["pl_orbsmax"]) > 0]
        if len(good) < min_planets:
            continue
        p0 = good[0]
        M_star = _fnum(p0["st_mass"])
        teff = _fnum(p0["st_teff"])
        rad = _fnum(p0["st_rad"])
        if M_star is None or teff is None or rad is None:
            continue
        logg = _fnum(p0["st_logg"])
        if logg is not None and logg < MIN_LOGG:
            continue
        if not (M_LO <= M_star <= M_HI):
            continue

        L_star = (rad ** 2) * (teff / T_SUN) ** 4
        feh = _fnum(p0["st_met"]) or 0.0
        pl = []
        for p in sorted(good, key=lambda q: _fnum(q["pl_orbsmax"])):
            pl.append({"name": p["pl_name"], "au": _fnum(p["pl_orbsmax"]),
                       "mass": _fnum(p["pl_bmasse"]), "kind": _classify(_fnum(p["pl_bmasse"]))})
        systems.append({"name": host, "M_star": M_star, "L_star": round(L_star, 5),
                        "feh": feh, "n_planets": len(pl), "planets": pl})

    systems.sort(key=lambda s: (-s["n_planets"], s["name"]))
    if max_systems is not None:
        systems = systems[:max_systems]
    return systems


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Build held-out systems JSON from NASA PSCompPars.")
    ap.add_argument("--csv", default=None, help="path to PSCompPars CSV (default: newest in cwd)")
    ap.add_argument("--out", default="data/held_out.json")
    ap.add_argument("--min-planets", type=int, default=MIN_PLANETS)
    ap.add_argument("--max-systems", type=int, default=None)
    args = ap.parse_args(argv)

    csv_path = args.csv or (sorted(glob.glob("PSCompPars_*.csv"))[-1]
                            if glob.glob("PSCompPars_*.csv") else None)
    if not csv_path:
        raise SystemExit("no PSCompPars CSV found; pass --csv")

    systems = build_systems(csv_path, args.min_planets, args.max_systems)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"source": os.path.basename(csv_path),
                   "selection": {"min_planets": args.min_planets, "min_logg": MIN_LOGG,
                                 "M_star_range": [M_LO, M_HI]},
                   "systems": systems}, fh, indent=2)
    n_pl = sum(s["n_planets"] for s in systems)
    print(f"{len(systems)} systems, {n_pl} planets → {args.out}")
    print("largest systems:")
    for s in systems[:8]:
        print(f"  {s['name']:16s} n={s['n_planets']}  M*={s['M_star']:.2f}  "
              f"L*={s['L_star']:.3f}  [Fe/H]={s['feh']:+.2f}")


if __name__ == "__main__":
    main()
