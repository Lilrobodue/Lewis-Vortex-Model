"""The time integrator (guide §4) — marches a seeded embryo disk from formation to gas
dissipation, orchestrating M2–M4 and emitting the mechanism log for every position-
determining event. Output: the final architecture + a complete log.

v2.0 simplifications the guide permits: the disk is static; the "torque-reversal factor" is
the gradient-based normalized torque itself (which reverses at traps); capture is a
calibrated logistic. Everything is deterministic given the seed (project default 432).

Run:  py -3.11 -m src.solver.evolve --system sun [--seed 432] [--out runs/<name>]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .params import Params, StellarInput, SUN, M_EARTH, M_SUN
from .disk import DiskModel
from . import traps as trapmod
from .embryos import Embryo, seed_population, grow, pebble_growth_rate
from .migration import migrate_da_dt, gap_opened, _torque_interpolator
from .resonance import period_ratio, attempt_capture
from .stability import separation_in_hill, relax_post_disk, merge_pair
from .logger import MechanismLogger

MAX_DA_FRAC = 0.15      # cap |Δa| per step to this fraction of a (stability of the integrator)
COLLIDE_DELTA = 1.0     # in-disk: non-resonant pairs closer than this (mutual Hill radii) collide
A_MIN, A_MAX = 0.02, 55.0   # modeled domain [AU]; bodies cannot leave it (guide disk 0.05–50)
HILL_TAG_FRAC = 1.3     # a surviving non-resonant pair within K..HILL_TAG_FRAC·K is Hill-packed


@dataclass
class ForwardResult:
    params: Params
    star: StellarInput
    seed: int
    disk: DiskModel
    traps: List[trapmod.Trap]
    survivors: List[Embryo]
    logger: MechanismLogger
    n_steps: int
    complete_log: bool

    def positions(self) -> List[float]:
        return sorted(e.a for e in self.survivors)

    def architecture(self) -> List[dict]:
        out = []
        for e in sorted(self.survivors, key=lambda x: x.a):
            out.append({"id": e.id, "a_AU": round(e.a, 4), "mass_Me": round(e.mass, 4),
                        "kind": e.kind, "seed_zone": e.seed_trap,
                        "trapped": e.trapped, "pq": e.pq})
        return out


def _snap_to_trap(a_old: float, a_new: float, stable_traps: np.ndarray
                  ) -> Optional[float]:
    """If the motion a_old→a_new crosses a stable trap radius, return that radius, else None."""
    lo, hi = min(a_old, a_new), max(a_old, a_new)
    inside = stable_traps[(stable_traps >= lo) & (stable_traps <= hi)]
    if inside.size == 0:
        return None
    # snap to the first trap encountered in the direction of travel
    return float(inside.max() if a_new < a_old else inside.min())


def evolve(params: Params, star: StellarInput = SUN, seed: int = 432,
           n_steps: int = 500, n_seeds: int = 24, relax: bool = True) -> ForwardResult:
    params = params.clipped()
    rng = np.random.default_rng(seed)
    disk = DiskModel(params, star)
    trap_list = trapmod.trap_locations(disk)
    stable_traps = np.array(sorted(t.r_AU for t in trapmod.find_torque_reversals(disk)))
    trap_label = {round(t.r_AU, 3): t.label for t in trap_list}
    log = MechanismLogger()

    torque_interp = _torque_interpolator(disk)
    embryos = seed_population(disk, params, n_seeds=n_seeds)
    for e in embryos:
        log.seeded(0.0, e.id, e.a, e.mass, e.seed_trap)

    # Shared, depleting pebble budget: all cores draw from the disk's finite solid mass, so a
    # few winners reach giant mass and the rest stay small — instead of every embryo growing
    # to isolation independently. Parameter-free (derived from the disk).
    peb_budget = disk.total_solid_mass()

    t_disk = params.t_disk
    dt = t_disk / n_steps
    pr_prev: Dict[Tuple[int, int], float] = {}
    gap_logged: set = set()

    t = 0.0
    for _ in range(n_steps):
        t += dt
        alive = [e for e in embryos if e.alive]

        # 1) growth (draws from the shared pebble budget, fastest growers first)
        for e in sorted(alive, key=lambda x: -pebble_growth_rate(disk, x)):
            peb_budget -= grow(disk, e, dt, params, peb_budget)
            log.growth(t, e.id, e.a, e.mass)
            if not e.gap and gap_opened(disk, e) and e.id not in gap_logged:
                e.gap = True
                gap_logged.add(e.id)
                log.gap_opened(t, e.id, e.a)

        # 2) migration (skip trapped anchors and resonance-slaved bodies)
        for e in alive:
            if e.trapped or e.partner is not None:
                continue
            dadt, mode = migrate_da_dt(disk, e, torque_interp)
            da = dadt * dt
            da = float(np.clip(da, -MAX_DA_FRAC * e.a, MAX_DA_FRAC * e.a))
            a_new = float(np.clip(e.a + da, A_MIN, A_MAX))
            snap = _snap_to_trap(e.a, a_new, stable_traps)
            if snap is not None:
                lbl = trap_label.get(round(snap, 3), "trap")
                e.a = snap
                e.trapped = True
                log.trapped(t, e.id, e.a, lbl)
            else:
                log.migrating(t, e.id, e.a, a_new, mode)
                e.a = a_new

        # 3) resonance-slaved bodies follow their (possibly moved) partner. Clear partners
        #    orphaned by a merge (anchor no longer alive) so they resume free migration.
        by_id = {e.id: e for e in alive}
        for e in alive:
            if e.partner is not None and e.partner not in by_id:
                e.partner, e.pq = None, None
        for e in alive:
            if e.partner is not None and e.partner in by_id and e.pq:
                p, q = (int(x) for x in e.pq.split(":"))
                anchor = by_id[e.partner]
                from .resonance import DISSIPATION_OFFSET
                target = anchor.a * ((p / q) * (1.0 + DISSIPATION_OFFSET)) ** (2.0 / 3.0)
                # a locked pair migrates inward as a unit with its anchor; never outward
                e.a = min(e.a, target)

        # 4) resonance capture on adjacent convergent pairs
        alive.sort(key=lambda x: x.a)
        for i in range(len(alive) - 1):
            inner, outer = alive[i], alive[i + 1]
            if outer.partner is not None or inner.partner == outer.id:
                continue
            key = (inner.id, outer.id)
            pr_now = period_ratio(inner, outer)
            prev = pr_prev.get(key, pr_now)
            res = attempt_capture(inner, outer, prev, pr_now, dt, params.f_capture, rng)
            if res is not None:
                p, q, offset = res
                log.resonance_capture(t, outer.id, inner.id, f"{p}:{q}", offset)
            pr_prev[key] = period_ratio(inner, outer)

        # 5) in-disk collisions: non-resonant pairs that cross into ~1 mutual-Hill radius
        #    merge (orbit-crossing giant impact). This bounds crowding — instead of pushing
        #    bodies apart (which cascades to spurious large radii), overlapping bodies merge.
        alive.sort(key=lambda x: x.a)
        i = 0
        while i < len(alive) - 1:
            inner, outer = alive[i], alive[i + 1]
            if outer.partner != inner.id and \
                    separation_in_hill(inner, outer, star.M_star) < COLLIDE_DELTA:
                merge_pair(inner, outer, log, t)
                alive = [e for e in alive if e.alive]
            else:
                i += 1

    log.disk_dissipated(t)

    # 6) post-disk relaxation (merge residual Hill violators, spacing set by K)
    survivors = [e for e in embryos if e.alive]
    if relax:
        survivors = relax_post_disk(survivors, params.K, star.M_star, logger=log, t_Myr=t)

    # 7) tag Hill-packed survivors: non-resonant adjacent pairs sitting near the K floor have
    #    their spacing *set* by Hill stability — record it as their binding constraint (M6).
    survivors.sort(key=lambda e: e.a)
    for i in range(len(survivors) - 1):
        inner, outer = survivors[i], survivors[i + 1]
        if outer.partner == inner.id:
            continue
        delta = separation_in_hill(inner, outer, star.M_star)
        if params.K <= delta <= HILL_TAG_FRAC * params.K:
            log.hill_limited(t, outer.id, inner.id, round(delta, 3))

    surviving_ids = [e.id for e in survivors]
    complete = log.is_complete(surviving_ids)
    return ForwardResult(params, star, seed, disk, trap_list, survivors, log,
                         n_steps, complete)


# ── Run I/O ─────────────────────────────────────────────────────────────────
def _git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def write_run(result: ForwardResult, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "mechanism.jsonl"), "w", encoding="utf-8") as fh:
        result.logger.write_jsonl(fh)
    manifest = {
        "system": result.star.name,
        "seed": result.seed,
        "git": _git_hash(),
        "n_steps": result.n_steps,
        "params": result.params.as_dict(),
        "disk": result.disk.summary(),
        "traps_AU": [round(t.r_AU, 4) for t in result.traps],
        "complete_log": result.complete_log,
        "architecture": result.architecture(),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Forward formation run (guide M3/M4).")
    ap.add_argument("--system", default="sun")
    ap.add_argument("--seed", type=int, default=432)
    ap.add_argument("--n-steps", type=int, default=500)
    ap.add_argument("--n-seeds", type=int, default=24)
    ap.add_argument("--out", default=None, help="run directory (default: runs/<system>_<seed>)")
    args = ap.parse_args(argv)

    star = SUN if args.system == "sun" else SUN  # only the Sun is defined as an input for now
    result = evolve(Params(), star, seed=args.seed, n_steps=args.n_steps, n_seeds=args.n_seeds)

    print(f"disk: {result.disk.summary()}")
    print(f"traps: {[round(t.r_AU, 3) for t in result.traps]}")
    print(f"survivors ({len(result.survivors)}):")
    for a in result.architecture():
        print(f"  {a['a_AU']:8.3f} AU  {a['mass_Me']:9.3f} Me  {a['kind']:5s} "
              f"seed={a['seed_zone']:11s} trapped={a['trapped']} pq={a['pq']}")
    print(f"log complete: {result.complete_log}  ({len(result.logger.records)} events)")

    out = args.out or os.path.join("runs", f"{args.system}_{args.seed}")
    write_run(result, out)
    print(f"written -> {out}/")


if __name__ == "__main__":
    main()
