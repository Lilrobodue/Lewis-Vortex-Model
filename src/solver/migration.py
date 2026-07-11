"""M3 — Migration.

Type I torque with trap reversal, and Type II after a gap opens. The Type I rate uses the
SAME gradient-based normalized torque as the trap finder (`traps.normalized_typeI_torque`),
so a planet migrates until it reaches a zero-torque radius — a trap — and halts there, with
direction and magnitude emerging from mass + local disk state. There are NO per-planet
migration fractions (guide §4, migration.py note): v1's hardcoded −8%/−45%/…/+60% are gone.
"""
from __future__ import annotations

import numpy as np

from .params import M_EARTH, M_SUN, AU_CM, YEAR_S, MYR_S
from .disk import DiskModel
from .embryos import Embryo
from .traps import normalized_typeI_torque

# Gap-opening: thermal criterion R_Hill > H → q > 3 h³, with a viscous-aware coefficient.
# (Compact stand-in for Crida+ 2006; guide allows Type II "after gap-opening criterion".)
GAP_Q_COEFF = 1.0


def _torque_interpolator(disk: DiskModel):
    """Cache the normalized torque profile γΓ/Γ0(r) for fast per-embryo interpolation."""
    G = normalized_typeI_torque(disk)
    r = disk.r
    return lambda a: float(np.interp(a, r, G))


def gap_opened(disk: DiskModel, emb: Embryo) -> bool:
    """Thermal gap criterion: q = M_p/M* > GAP_Q_COEFF · 3 (H/r)³."""
    q = (emb.mass * M_EARTH) / (disk.star.M_star * M_SUN)
    h = float(disk.H_over_r(emb.a))
    return q > GAP_Q_COEFF * 3.0 * h ** 3


def type_I_da_dt(disk: DiskModel, emb: Embryo, torque_interp) -> float:
    """Type I da/dt [AU/Myr].

    da/dt = 2 Γ /(M_p Ω a), Γ = (γΓ/Γ0) · Γ0, Γ0 = (M_p/M*)² (H/r)⁻² Σ_gas a⁴ Ω².
    ⇒ da/dt = 2 (γΓ/Γ0) (M_p/M*²) (H/r)⁻² Σ_gas a³ Ω. Sign follows γΓ/Γ0 (−=inward), which
    reverses across traps — so the planet decelerates and stops at a zero-torque radius.
    """
    norm = torque_interp(emb.a)
    a_cm = emb.a * AU_CM
    Mp_g = emb.mass * M_EARTH
    Mstar_g = disk.star.M_star * M_SUN
    h = float(disk.H_over_r(emb.a))
    Sig = float(disk.Sigma_gas(emb.a))
    Omega = float(disk.Omega(emb.a))
    dadt_cgs = 2.0 * norm * (Mp_g / Mstar_g ** 2) * h ** (-2) * Sig * a_cm ** 3 * Omega
    return dadt_cgs / AU_CM * MYR_S       # cm/s → AU/Myr


def type_II_da_dt(disk: DiskModel, emb: Embryo) -> float:
    """Type II da/dt [AU/Myr]: viscous inflow, da/dt ≈ −1.5 ν / a, ν = α c_s H.
    Slow, inward, mass-independent to leading order (planet locked to the gas)."""
    from .disk import ALPHA_ACTIVE
    a_cm = emb.a * AU_CM
    h = float(disk.H_over_r(emb.a))
    cs = float(disk.sound_speed(emb.a))
    H_cm = h * a_cm
    alpha = float(disk.alpha_profile(np.array([emb.a]))[0])
    nu = alpha * cs * H_cm
    dadt_cgs = -1.5 * nu / a_cm
    return dadt_cgs / AU_CM * MYR_S


def migrate_da_dt(disk: DiskModel, emb: Embryo, torque_interp) -> tuple[float, str]:
    """Return (da/dt [AU/Myr], mode). Type II once a gap is open, else Type I."""
    if emb.gap:
        return type_II_da_dt(disk, emb), "II"
    return type_I_da_dt(disk, emb, torque_interp), "I"
