"""M2 — Migration traps, *found* from the disk state, never assigned (guide §4).

A trap is a computed property of the disk:
  1. a local gas-pressure maximum (∂P/∂r = 0, ∂²P/∂r² < 0), where pebbles/planets pile up;
  2. a radius where the normalized Type I torque changes sign (a planet trap; Masset+ 2006).

The finder is generic — it scans the profiles and reports whatever extrema/zero-crossings
exist. For a fiducial solar disk it should surface the two dead-zone edges and the snow
line without being told they are there (M2 acceptance test).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from .disk import DiskModel


@dataclass(frozen=True)
class Trap:
    r_AU: float
    kind: str            # "pressure_max" | "torque_reversal"
    label: str           # nearest derived feature: dead_zone_inner|dead_zone_outer|snow_line|unknown
    strength: float      # dimensionless: bump prominence (pressure) or |dΓ/dr| (torque)


# ── Normalized Type I torque (gradient-only; mass cancels out) ──────────────
# Locally-isothermal linear torque, Paardekooper, Baruteau & Kley (2010/2011) compact form:
#   γ Γ / Γ0 ≈ -(C0 + C_Σ·s_Σ + C_T·s_T),   s_Σ = -dlnΣ/dlnr,  s_T = -dlnT/dlnr
# Γ0 = (q/h)² Σ r⁴ Ω² > 0, so the SIGN of this proxy is the migration-direction sign:
# negative → inward, positive → outward. In a smooth disk (s_Σ≈p, s_T≈0.5) it is negative
# everywhere (planets migrate in); it flips to positive on the rising inner flank of a
# surface-density bump, so a zero-crossing that goes + → − with increasing r is a stable
# trap. Uses the *effective* gas Σ (with dead-zone-edge bumps), consistent with pressure.
C0, C_SIGMA, C_TEMP = 0.85, 1.0, 0.9


def normalized_typeI_torque(disk: DiskModel, r=None) -> np.ndarray:
    """Return γΓ/Γ0 on the disk grid (or at r). Sign = migration direction (−=inward)."""
    r = disk.r if r is None else np.asarray(r, float)
    lnr = np.log(r)
    s_sigma = -np.gradient(np.log(disk.Sigma_gas_eff(r)), lnr)
    s_temp = -np.gradient(np.log(disk.T_profile(r)), lnr)
    return -(C0 + C_SIGMA * s_sigma + C_TEMP * s_temp)


def _label_for(disk: DiskModel, r: float, tol_frac: float = 0.15) -> str:
    """Name the nearest derived feature within tol_frac, else 'unknown'."""
    candidates = {"snow_line": disk.r_h2o}
    if disk.has_dead_zone():
        candidates["dead_zone_inner"] = disk.dz_in
        candidates["dead_zone_outer"] = disk.dz_out
    best, best_rel = "unknown", tol_frac
    for name, loc in candidates.items():
        if loc is None:
            continue
        rel = abs(r - loc) / max(loc, 1e-6)
        if rel < best_rel:
            best, best_rel = name, rel
    return best


def _refine_max(r: np.ndarray, y: np.ndarray, i: int) -> float:
    """Parabolic sub-grid refinement of a local maximum at index i."""
    if i <= 0 or i >= len(r) - 1:
        return float(r[i])
    x0, x1, x2 = r[i - 1], r[i], r[i + 1]
    y0, y1, y2 = y[i - 1], y[i], y[i + 1]
    denom = (y0 - 2 * y1 + y2)
    if denom == 0:
        return float(x1)
    delta = 0.5 * (y0 - y2) / denom
    return float(x1 + delta * (x2 - x0) / 2.0)


def find_pressure_maxima(disk: DiskModel, min_prominence: float = 0.02) -> List[Trap]:
    """Local maxima of P(r). Prominence = (P_peak − P_smooth)/P_smooth vs the power-law
    baseline, so the monotone background does not register as a trap."""
    r, P = disk.r, disk.pressure
    # Baseline: pressure without bumps (smooth background) for prominence.
    P_base = disk.Pressure(r) / disk._bump_factor(r)
    traps: List[Trap] = []
    for i in range(1, len(r) - 1):
        if P[i] > P[i - 1] and P[i] >= P[i + 1]:
            prom = (P[i] - P_base[i]) / P_base[i]
            if prom >= min_prominence:
                rp = _refine_max(r, P, i)
                traps.append(Trap(rp, "pressure_max", _label_for(disk, rp), float(prom)))
    return traps


def find_torque_reversals(disk: DiskModel, min_slope: float = 0.0) -> List[Trap]:
    """Radii where γΓ/Γ0 crosses zero from + to − with increasing r (stable planet traps)."""
    r = disk.r
    G = normalized_typeI_torque(disk)
    traps: List[Trap] = []
    for i in range(len(r) - 1):
        if G[i] > 0 >= G[i + 1]:  # + → − : convergent, stable
            # linear interpolation of the zero crossing
            t = G[i] / (G[i] - G[i + 1])
            rz = float(r[i] + t * (r[i + 1] - r[i]))
            slope = abs(G[i + 1] - G[i]) / (r[i + 1] - r[i])
            if slope >= min_slope:
                traps.append(Trap(rz, "torque_reversal", _label_for(disk, rz), float(slope)))
    return traps


def find_traps(disk: DiskModel) -> List[Trap]:
    """All traps, sorted inward → outward. Pressure maxima and torque reversals both listed;
    they typically coincide at each derived feature (evolve.py de-duplicates when snapping)."""
    traps = find_pressure_maxima(disk) + find_torque_reversals(disk)
    return sorted(traps, key=lambda t: t.r_AU)


def trap_locations(disk: DiskModel, merge_frac: float = 0.08) -> List[Trap]:
    """De-duplicated trap centers: merge pressure_max + torque_reversal that fall within
    merge_frac of each other into one trap (prefer the pressure_max, keep its label)."""
    traps = find_traps(disk)
    merged: List[Trap] = []
    for t in traps:
        if merged and abs(t.r_AU - merged[-1].r_AU) / max(merged[-1].r_AU, 1e-6) < merge_frac:
            prev = merged[-1]
            keep = prev if prev.kind == "pressure_max" else t
            label = keep.label if keep.label != "unknown" else (
                prev.label if prev.label != "unknown" else t.label)
            merged[-1] = Trap(0.5 * (prev.r_AU + t.r_AU), "trap", label,
                              max(prev.strength, t.strength))
        else:
            merged.append(t)
    return merged
