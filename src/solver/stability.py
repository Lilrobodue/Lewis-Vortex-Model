"""M4 — Hill stability: mutual-Hill spacing enforcement and post-disk relaxation.

Kepler multi-planet systems sit near a minimum mutual separation of K mutual Hill radii
(K one global parameter, prior 8–12; Pu & Wu 2015). During the disk phase we forbid pairs
tighter than K (a body pushed too close to its neighbour is held at the K·R_H,m floor —
`hill_limited`). Post-disk, an optional relaxation ejects/merges any residual violators.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .params import M_EARTH, M_SUN
from .disk import DiskModel
from .embryos import Embryo


def mutual_hill_radius(inner: Embryo, outer: Embryo, M_star: float) -> float:
    """R_H,m = ½(a_in+a_out) · ((m_in+m_out)/(3 M*))^{1/3}  [AU]."""
    m_sum = (inner.mass + outer.mass) * M_EARTH
    return 0.5 * (inner.a + outer.a) * (m_sum / (3.0 * M_star * M_SUN)) ** (1.0 / 3.0)


def separation_in_hill(inner: Embryo, outer: Embryo, M_star: float) -> float:
    """Δ = (a_out − a_in) / R_H,m  — the spacing in mutual Hill radii."""
    rh = mutual_hill_radius(inner, outer, M_star)
    if rh <= 0:
        return float("inf")
    return (outer.a - inner.a) / rh


def merge_pair(inner: Embryo, outer: Embryo, logger=None, t_Myr: float = 0.0) -> None:
    """Merge `outer` into `inner` at the mass-weighted position (a giant impact / scattering
    event). `outer` is marked dead. If `outer` was another body's resonance anchor the caller
    must re-home that partner; evolve does this by clearing orphaned partners each step."""
    a_new = (inner.a * inner.mass + outer.a * outer.mass) / (inner.mass + outer.mass)
    inner.a = a_new
    inner.mass += outer.mass
    inner.core += outer.core
    outer.alive = False
    if logger is not None:
        logger.merged(t_Myr, outer.id, into=inner.id, at_AU=a_new)


def relax_post_disk(embryos: List[Embryo], K: float, M_star: float, logger=None,
                    t_Myr: float = 0.0) -> List[Embryo]:
    """Post-gas relaxation: sweep inward→outward; any non-resonant pair still tighter than K
    mutual-Hill radii is merged (inner absorbs outer). Returns the surviving bodies, all of
    which are then either ≥K apart or held in a resonance lock."""
    alive = [e for e in embryos if e.alive]
    alive.sort(key=lambda e: e.a)
    changed = True
    while changed:
        changed = False
        for i in range(len(alive) - 1):
            inner, outer = alive[i], alive[i + 1]
            if outer.partner == inner.id:
                continue
            if separation_in_hill(inner, outer, M_star) < K:
                merge_pair(inner, outer, logger, t_Myr)
                alive = [e for e in alive if e.alive]
                changed = True
                break
    return alive
