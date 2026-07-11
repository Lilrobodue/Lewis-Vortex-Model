"""M4 — Convergent-migration resonance capture.

When two convergently migrating embryos bring their period ratio down through a p:q
commensurability (q ≤ 5, order ≤ 4), attempt capture with a probability that *rises* with
resonance strength (lower order) and *falls* with the relative migration speed — a
calibrated logistic in the convergence rate over the resonance width, scaled by the one
global parameter f_capture (guide param #10). On capture the pair locks just wide of the
nominal ratio by a dissipation offset.

This is where Branch A physics is finally *simulated* instead of asserted (guide §4).

Determinism: capture is a Bernoulli draw; the RNG is threaded in from evolve.py (seed 432
by project convention) so a run is reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from typing import List, Optional, Tuple

import numpy as np

from .embryos import Embryo

# First-to-fourth-order resonances with q ≤ 5, p > q, reduced. Period ratio = p/q > 1.
def _build_resonances(max_q: int = 5, max_order: int = 4) -> List[Tuple[int, int, int]]:
    res = []
    for q in range(1, max_q + 1):
        for p in range(q + 1, q + max_order + 1):
            if gcd(p, q) == 1:
                res.append((p, q, p - q))  # (p, q, order)
    # sort by period ratio descending (wide → tight) so convergence crosses them in order
    return sorted(res, key=lambda t: -t[0] / t[1])


RESONANCES = _build_resonances()

# Capture-window half-width in period ratio, per unit order strength. First-order resonances
# are wide; higher orders narrow rapidly. Calibrated, dimensionless.
WIDTH_BASE = 0.06
DISSIPATION_OFFSET = 0.01     # pair locks this fraction *wide* of nominal (eccentricity damping)


def period_ratio(inner: Embryo, outer: Embryo) -> float:
    """T_out / T_in = (a_out/a_in)^{3/2} ≥ 1 when properly ordered."""
    return (outer.a / inner.a) ** 1.5


def _resonance_width(order: int) -> float:
    return WIDTH_BASE / order          # order 1 wide, order 4 narrow


def nearest_resonance(pr: float) -> Optional[Tuple[int, int, int]]:
    """Return the (p,q,order) whose ratio p/q is closest to pr within its width, else None."""
    best = None
    best_rel = None
    for p, q, order in RESONANCES:
        ratio = p / q
        if abs(pr - ratio) <= _resonance_width(order) * ratio:
            rel = abs(pr - ratio)
            if best_rel is None or rel < best_rel:
                best, best_rel = (p, q, order), rel
    return best


def capture_probability(order: int, conv_rate: float, width: float, f_capture: float) -> float:
    """Logistic capture probability.

    conv_rate = |d(period_ratio)/dt| normalized by the resonance width (dimensionless "speed
    through the resonance"). Slow crossing → near-certain capture; fast crossing → escape.
    Lower order → intrinsically stronger → shifts the logistic toward capture. Scaled by
    f_capture ∈ [0,1].
    """
    # speed in units of widths crossed per unit time; 1 ⇒ marginal
    x = conv_rate / max(width, 1e-9)
    strength = 1.0 / order                      # 1.0 (first order) … 0.25 (fourth)
    # logistic centered so that slow (x≪1) → ~1, fast (x≫1) → ~0; strength shifts the center out
    z = float(np.clip((x - strength) / (0.35 * strength), -60.0, 60.0))
    p = 1.0 / (1.0 + np.exp(z))
    return float(f_capture * p)


def apply_capture(inner: Embryo, outer: Embryo, p: int, q: int) -> float:
    """Lock the outer embryo just wide of the nominal p:q ratio. Returns the applied offset.

    Sets a_out so that T_out/T_in = (p/q)(1 + offset). Inner is the anchor (usually the one
    already trapped); the pair then migrates as a unit. Capture happens during CONVERGENT
    (inward) migration, so it may pull the outer body in to the exact resonance but must
    never push it *outward* — capture cannot add orbital energy (guard against teleporting
    the outermost link of a chain to large radii).
    """
    target_pr = (p / q) * (1.0 + DISSIPATION_OFFSET)
    a_target = inner.a * target_pr ** (2.0 / 3.0)
    outer.a = min(outer.a, a_target)
    outer.partner = inner.id
    outer.pq = f"{p}:{q}"
    return DISSIPATION_OFFSET


def attempt_capture(inner: Embryo, outer: Embryo, pr_prev: float, pr_now: float,
                    dt_Myr: float, f_capture: float,
                    rng: np.random.Generator) -> Optional[Tuple[int, int, float]]:
    """Called each step for an adjacent, convergent pair.

    If the period ratio crossed (or sits within the window of) a resonance this step, draw a
    Bernoulli with capture_probability. On success, lock the pair and return (p, q, offset);
    else None. Only convergent motion (pr decreasing toward the commensurability) captures.
    """
    if pr_now >= pr_prev:            # diverging — no capture
        return None
    res = nearest_resonance(pr_now)
    if res is None:
        # also catch a fast crossing that skipped the window between samples
        for p, q, order in RESONANCES:
            ratio = p / q
            if pr_now < ratio < pr_prev:
                res = (p, q, order)
                break
        if res is None:
            return None
    p, q, order = res
    width = _resonance_width(order) * (p / q)
    conv_rate = abs(pr_prev - pr_now) / max(dt_Myr, 1e-9)
    prob = capture_probability(order, conv_rate, width, f_capture)
    if rng.random() < prob:
        offset = apply_capture(inner, outer, p, q)
        return p, q, offset
    return None
