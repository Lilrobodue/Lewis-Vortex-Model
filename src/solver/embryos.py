"""M3 — Embryo seeding and growth.

Seed embryos at trap locations where the local solid density crosses a streaming-instability
threshold; grow cores by pebble accretion (Lambrechts & Johansen 2012 scaling) up to the
pebble-isolation mass; open a gas envelope past the runaway core mass M_crit (the one global
parameter here). Isolation mass and every rate are DERIVED from the local disk state — no
per-planet dials (guide §3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .params import Params, M_EARTH, M_SUN, AU_CM, MYR_S
from .disk import DiskModel

# Streaming-instability seeding: the local solid-to-gas ratio must exceed a critical value
# for clumping. Carrera+ (2015) place the surface-density threshold near ~0.01 (settling
# concentrates dust further at the midplane). Above it, an embryo can nucleate.
Z_CRIT = 0.01
M_SEED_ME = 0.01                # initial embryo mass [M_earth] (~lunar/Mars-embryo seed)
ISO_COEFF = 25.0                # pebble-isolation-mass coefficient (Bitsch+ 2018): 25 (h/0.05)^3
T_KH0 = 1.0                     # Myr, gas-envelope KH time at core = M_crit (Ikoma+ 2000 scale)
KH_EXP = 3.0                    # steepness of t_KH ∝ (M_crit/core)^KH_EXP
GIANT_CAP_ME = 400.0            # ceiling on gas-giant mass [M_earth] (~1.3 Jupiter)


@dataclass
class Embryo:
    id: int
    a: float                    # semi-major axis [AU]
    mass: float                 # total mass [M_earth]
    core: float                 # core mass [M_earth]
    seed_trap: str = "unknown"  # label of the trap it was born at
    is_giant: bool = False
    gap: bool = False           # has opened a gas gap (→ Type II)
    trapped: bool = False       # currently held at a migration trap
    partner: Optional[int] = None  # resonance partner id
    pq: Optional[str] = None    # resonance ratio "p:q"
    alive: bool = True

    @property
    def kind(self) -> str:
        if self.is_giant and self.mass > 50:
            return "gas"
        if self.is_giant:
            return "ice"
        return "rocky"


def isolation_mass(disk: DiskModel, a: float) -> float:
    """Pebble-isolation mass [M_earth] from the local aspect ratio (Bitsch+ 2018)."""
    h = float(disk.H_over_r(a))
    return ISO_COEFF * (h / 0.05) ** 3


def seed_embryos(disk: DiskModel, trap_radii: List[float], trap_labels: List[str],
                 params: Params) -> List[Embryo]:
    """Seed one embryo at each trap where the local solid/gas ratio exceeds Z_CRIT.

    The trap concentrates solids (the pressure bump is already in Σ_solid), so seeding is a
    property of the disk + trap, not an assignment. Returns embryos ordered inward→outward.
    """
    embryos: List[Embryo] = []
    next_id = 0
    for r, label in sorted(zip(trap_radii, trap_labels)):
        sig_solid = float(disk.Sigma_solid(r))
        sig_gas = float(disk.Sigma_gas(r))
        z_local = sig_solid / max(sig_gas, 1e-30)
        if z_local >= Z_CRIT:
            embryos.append(Embryo(id=next_id, a=r, mass=M_SEED_ME, core=M_SEED_ME,
                                  seed_trap=label))
            next_id += 1
    return embryos


def seed_population(disk: DiskModel, params: Params, n_seeds: int = 24,
                    r_in: float = 0.2, r_out: float = 35.0) -> List[Embryo]:
    """Seed a disk-wide embryo population on a log-spaced radial grid wherever the local
    solid/gas ratio exceeds Z_CRIT. This is the realistic starting state: many embryos form,
    then migration → traps → resonance → Hill spacing sculpt them. The number and spacing of
    the SURVIVORS is an output, never assigned. Radii are disk-derived; masses are all the
    same seed mass (no per-planet mass dial)."""
    r_out = min(r_out, disk.p.r_disk)
    radii = np.geomspace(r_in, r_out, n_seeds)
    embryos: List[Embryo] = []
    next_id = 0
    for r in radii:
        z_local = float(disk.Sigma_solid(r)) / max(float(disk.Sigma_gas(r)), 1e-30)
        if z_local >= Z_CRIT:
            # label by the disk zone it formed in (diagnostic only, not a parameter)
            label = "beyond_snow" if r > disk.r_h2o else "inner_disk"
            embryos.append(Embryo(id=next_id, a=float(r), mass=M_SEED_ME, core=M_SEED_ME,
                                  seed_trap=label))
            next_id += 1
    return embryos


ST = 0.1                        # pebble Stokes number (drift-dominated size), constant


def pebble_surface_density(disk: DiskModel, a: float, pebble_flux_gs: float) -> float:
    """Σ_peb [g/cm²] of the DRIFTING pebble population, from mass conservation of the inward
    flux: Σ_peb = Ṁ_F / (2π a v_drift). This is the physically correct reservoir — far
    smaller than the total solid column — because only pebbles currently drifting past the
    core can be accreted (Lambrechts & Johansen 2014). v_drift = 2 η v_K St/(1+St²), with
    η = ½(H/r)²|dln P/dln r| the sub-Keplerian pressure support."""
    a_cm = a * AU_CM
    hr = float(disk.H_over_r(a))
    vk = float(disk.Omega(a)) * a_cm
    dlnP = disk.p.p + 1.75 + a / disk.p.r_disk        # |dlnP/dlnr| for Σr^-p exp, T r^-1/2
    eta = 0.5 * hr ** 2 * dlnP
    v_drift = 2.0 * eta * vk * ST / (1.0 + ST ** 2)
    if v_drift <= 0:
        return 0.0
    return pebble_flux_gs / (2.0 * np.pi * a_cm * v_drift)


def pebble_growth_rate(disk: DiskModel, emb: Embryo, pebble_flux_gs: float = None) -> float:
    """Core growth dM/dt [M_earth / Myr] by 2D Hill-regime pebble accretion.

    Lambrechts & Johansen (2012): Ṁ = 2 Ω a² (M_p/3M*)^{2/3} Σ_peb. Σ_peb is the DRIFTING
    pebble surface density from the inward flux (flux-limited) — not the full solid column,
    which over-fed every core and made giants form in ~10⁴ yr everywhere. Flux-limited growth
    is time-critical (competes with the disk lifetime) and metallicity-gated (flux ∝ solids).
    If pebble_flux_gs is None, falls back to the local solid column (legacy behaviour).
    Growth stops at the pebble-isolation mass.
    """
    if emb.core >= isolation_mass(disk, emb.a):
        return 0.0
    a_cm = emb.a * AU_CM
    Mp_g = emb.core * M_EARTH
    Mstar_g = disk.star.M_star * M_SUN
    Omega = float(disk.Omega(emb.a))
    if pebble_flux_gs is None:
        Sig_peb = float(disk.Sigma_solid(emb.a))
    else:
        Sig_peb = pebble_surface_density(disk, emb.a, pebble_flux_gs)
    mdot_cgs = 2.0 * Omega * a_cm ** 2 * (Mp_g / (3.0 * Mstar_g)) ** (2.0 / 3.0) * Sig_peb
    return mdot_cgs / M_EARTH * MYR_S       # g/s → M_earth/Myr


def grow(disk: DiskModel, emb: Embryo, dt_Myr: float, params: Params,
         peb_budget: float = float("inf"), pebble_flux_gs: float = None) -> float:
    """Advance an embryo's mass by dt and return the pebble mass consumed [M_earth].

    Core grows by pebble accretion toward the isolation mass, but only as far as the SHARED,
    depleting pebble budget allows — solids are finite, so a fast inner grower starves the
    outer disk instead of every embryo independently reaching isolation (the old behaviour
    that mass-produced giants). Once the core passes M_crit a gas envelope runs away (giant).
    Mutates the embryo in place. `peb_budget` is the reservoir remaining before this call.
    """
    M_iso = isolation_mass(disk, emb.a)
    consumed = 0.0

    # Core / pebble phase — limited by isolation AND the shared budget.
    if emb.core < M_iso and peb_budget > 0:
        want = min(pebble_growth_rate(disk, emb, pebble_flux_gs) * dt_Myr, M_iso - emb.core)
        consumed = max(0.0, min(want, peb_budget))
        emb.core += consumed

    # Gas phase: Kelvin-Helmholtz-limited runaway once the core passes M_crit (guide param #8).
    # The envelope e-folds on t_KH, which drops STEEPLY with core mass (Ikoma+ 2000): a core
    # that only just reaches M_crit near disk dispersal has no time to run away and ends as a
    # sub-Neptune, while a massive early core becomes a gas giant. This timing dependence — not
    # a per-planet dial — is what makes most cores stay small, as the observed super-Earth /
    # sub-Neptune population demands. t_KH uses only M_crit; the clock is the disk lifetime.
    if emb.core >= params.M_crit:
        emb.is_giant = True
        if emb.mass <= emb.core:
            emb.mass = emb.core * 1.05          # seed a thin envelope at crossing
        t_kh = T_KH0 * (params.M_crit / emb.core) ** KH_EXP     # Myr, steep mass dependence
        growth = float(np.exp(min(dt_Myr / max(t_kh, 1e-6), 2.0)))  # runaway, capped per step
        reservoir = emb.core + _feeding_zone_gas(disk, emb)
        emb.mass = min(emb.mass * growth, reservoir, GIANT_CAP_ME)
        emb.mass = max(emb.mass, emb.core)
    else:
        emb.mass = emb.core

    return consumed


def _feeding_zone_gas(disk: DiskModel, emb: Embryo) -> float:
    """Gas mass [M_earth] in an annulus of a few Hill radii — the runaway reservoir."""
    a_cm = emb.a * AU_CM
    Mp_g = max(emb.core * M_EARTH, 1e-6 * M_SUN)
    r_H = a_cm * (Mp_g / (3.0 * disk.star.M_star * M_SUN)) ** (1.0 / 3.0)
    width_cm = 8.0 * r_H
    area = 2.0 * np.pi * a_cm * width_cm
    return float(disk.Sigma_gas(emb.a) * area / M_EARTH)
