"""M1 — Disk module.

Ports v1's radial profiles (Σ, T, B, ice lines, solid enhancement, H/r), which the audit
(guide §2.1) verified correct, and *derives* the dead zone from an ionization criterion so
`dz_in` / `dz_out` are no longer free dials (guide §4, disk.py note). Also exposes a gas
pressure profile with viscosity-transition and snow-line bumps — the raw material that
`traps.py` scans for pressure maxima and torque sign changes.

Design choice: the profiles are exposed as *analytic* methods (`Sigma_gas(r)`, `T(r)`, …)
so the M1 regression against `reference/formation_solver.html` is exact, not interpolated.
The gridded arrays (`self.r`, `self.sigma_gas`, …) are just those methods sampled on a grid.

Everything here is a function of the ten global params + per-system stellar inputs. Nothing
here references an observed planet position (guide §3).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from .params import (
    Params, StellarInput, SUN,
    G_CGS, M_SUN, AU_CM, K_BOLTZ, M_H, MU_GAS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Disk physics constants — global, literature-motivated, NOT free parameters.
# These replace v1's free dials logAlpha, logBeta, dz_in, dz_out, T_snow, opacity_f.
# ─────────────────────────────────────────────────────────────────────────────
ALPHA_ACTIVE = 1.0e-3        # Shakura-Sunyaev alpha in MRI-active gas
DEAD_ZONE_ALPHA_FRAC = 0.01  # alpha suppression inside the dead zone (v1 value)
T_ION = 900.0                # K, thermal (alkali) ionization onset -> MRI active (Desch & Turner 2015)
SIGMA_DZ = 100.0             # g/cm^2, CR/X-ray ionization penetration column (Turner+ 2007)
PLASMA_BETA = 1.0e4          # for the diagnostic B(r) profile only

# Condensation temperatures (K) — set the ice-line *positions* given T(r). Constants.
T_H2O = 170.0
T_CO2 = 70.0
T_CO = 20.0
CO2_BOOST = 1.3              # solid enhancement past CO2 line (v1)
CO_BOOST = 1.2              # solid enhancement past CO line (v1)

# Pressure-bump shape. A parametrized stand-in for the steady-state Σ overshoot at a
# viscosity transition (Dzyurkevich+ 2010): amplitude tied to the alpha contrast, width a
# few local scale heights. Positions are DERIVED (dz_in, dz_out, ice line), never set.
_ALPHA_CONTRAST = 1.0 / DEAD_ZONE_ALPHA_FRAC
BUMP_AMP_DZ = float(np.clip(np.log10(_ALPHA_CONTRAST), 0.0, 3.0))  # ~2.0 for contrast 100
BUMP_AMP_SNOW = 1.0         # sublimation/recondensation pile-up at the snow line
BUMP_WIDTH_H = 2.0          # bump sigma in units of local scale height H

NR_DEFAULT = 800
R_MIN = 0.05
R_MAX = 50.0


class DiskModel:
    """A static (v2.0) protoplanetary disk for one system."""

    def __init__(self, params: Params, star: StellarInput = SUN, nr: int = NR_DEFAULT,
                 r_min: float = R_MIN, r_max: float = R_MAX):
        self.p = params
        self.star = star
        # Log-spaced grid: fine inner resolution so the (narrow) inner dead-zone-edge trap
        # is resolved. The regression against v1 uses the *analytic* methods on v1's own
        # grid, so this choice does not affect apples-to-apples comparison (guide M1).
        self.r = np.geomspace(r_min, r_max, nr)

        # Derived boundaries (functions of the disk, not free).
        self.r_h2o = self._ice_line(T_H2O)
        self.r_co2 = self._ice_line(T_CO2)
        self.r_co = self._ice_line(T_CO)
        self.dz_in, self.dz_out = self._dead_zone()

        # Gridded profiles.
        self.sigma_gas = self.Sigma_gas(self.r)
        self.T = self.T_profile(self.r)
        self.B = self.B_profile(self.r)
        self.H_r = self.H_over_r(self.r)
        self.alpha = self.alpha_profile(self.r)
        self.sigma_solid = self.Sigma_solid(self.r)
        self.pressure = self.Pressure(self.r)

    # ── Stellar-scaled temperature normalization ────────────────────────────
    @property
    def _T0_eff(self) -> float:
        # v1: T0_eff = T0 * L_star_f^0.25, opacity_f folded in (=1 here).
        return self.p.T0 * self.star.L_star ** 0.25

    # ── Analytic profiles (ported from v1 diskModel) ────────────────────────
    def Sigma_gas(self, r):
        """Σ(r) = Σ₀ r^(−p) exp(−r/r_disk)  [g/cm²].  Verbatim v1."""
        r = np.maximum(np.asarray(r, float), 0.01)
        return self.p.sigma0 * r ** (-self.p.p) * np.exp(-r / self.p.r_disk)

    def T_profile(self, r):
        """T(r) = T₀_eff r^(−1/2)  [K].  Verbatim v1 (opacity_f=1)."""
        r = np.maximum(np.asarray(r, float), 0.01)
        return self._T0_eff * r ** (-0.5)

    def B_profile(self, r):
        """B(r) = 13 β^(−1/2) r^(−13/8)  [G].  Diagnostic only.  Verbatim v1."""
        r = np.maximum(np.asarray(r, float), 0.01)
        return 13.0 * PLASMA_BETA ** (-0.5) * r ** (-13.0 / 8.0)

    def sound_speed(self, r):
        """Isothermal sound speed [cm/s]."""
        return np.sqrt(K_BOLTZ * self.T_profile(r) / (MU_GAS * M_H))

    def Omega(self, r):
        """Keplerian angular frequency [1/s]."""
        r = np.maximum(np.asarray(r, float), 0.01)
        return np.sqrt(G_CGS * self.star.M_star * M_SUN / (r * AU_CM) ** 3)

    def H_over_r(self, r):
        """Aspect ratio H/r = c_s/(Ω r).  Verbatim v1."""
        r = np.maximum(np.asarray(r, float), 0.01)
        return self.sound_speed(r) / (self.Omega(r) * r * AU_CM)

    def scale_height_AU(self, r):
        return self.H_over_r(r) * np.asarray(r, float)

    # ── Derived ice lines and dead zone ─────────────────────────────────────
    def _ice_line(self, T_cond: float) -> float:
        """Radius where T(r) = T_cond, i.e. r = (T0_eff / T_cond)^2, capped at r_disk."""
        r = (self._T0_eff / T_cond) ** 2
        return float(min(r, self.p.r_disk))

    def _dead_zone(self):
        """Derive the MRI dead-zone annulus (guide §4).

        Inner edge: thermal ionization keeps gas MRI-active where T > T_ION, so the dead
        zone begins outward of r where T drops to T_ION → dz_in = (T0_eff/T_ION)^2.
        Outer edge: cosmic-ray / X-ray ionization reaches the midplane once the column
        thins below SIGMA_DZ, so the dead zone ends at the outer Σ(r)=SIGMA_DZ crossing.
        Returns (None, None) if no dead zone exists for these params.
        """
        dz_in = (self._T0_eff / T_ION) ** 2
        if dz_in >= R_MAX:
            return None, None

        def f(r):
            return self.Sigma_gas(r) - SIGMA_DZ

        lo, hi = max(dz_in, R_MIN), R_MAX
        # Σ falls with r (the exp cutoff guarantees an outer crossing if Σ(lo) > threshold).
        if f(lo) <= 0:
            return None, None  # column already thin at the inner edge; no dead zone
        if f(hi) > 0:
            dz_out = R_MAX     # still thick at grid edge; clip
        else:
            dz_out = float(brentq(f, lo, hi))
        if dz_out <= dz_in:
            return None, None
        return float(dz_in), dz_out

    def has_dead_zone(self) -> bool:
        return self.dz_in is not None and self.dz_out is not None

    def alpha_profile(self, r):
        """α(r): suppressed by DEAD_ZONE_ALPHA_FRAC inside the derived dead zone."""
        r = np.asarray(r, float)
        a = np.full(r.shape, ALPHA_ACTIVE)
        if self.has_dead_zone():
            dead = (r > self.dz_in) & (r < self.dz_out)
            a[dead] = ALPHA_ACTIVE * DEAD_ZONE_ALPHA_FRAC
        return a

    # ── Solids and condensation fronts (ported from v1) ─────────────────────
    def _condensation_enhancement(self, r):
        r = np.asarray(r, float)
        enh = np.ones(r.shape)
        enh = np.where(r > self.r_h2o, enh * self.p.f_ice, enh)
        enh = np.where(r > self.r_co2, enh * CO2_BOOST, enh)
        enh = np.where(r > self.r_co, enh * CO_BOOST, enh)
        return enh

    def _bump_factor(self, r):
        """Multiplicative pressure/solid bump at each DERIVED trap location.

        Gaussian bumps at dz_in, dz_out and the snow line, widths set by the local scale
        height. This is the v2.0 stand-in for the steady-state viscosity-transition
        overshoot; the trap *finder* (traps.py) does not know these locations — it scans.
        """
        r = np.asarray(r, float)
        factor = np.ones(r.shape)

        def _width(loc: float) -> float:
            # bump half-width = a few scale heights evaluated AT the trap location
            return max(BUMP_WIDTH_H * float(self.scale_height_AU(loc)), 1e-3)

        if self.has_dead_zone():
            w_in, w_out = _width(self.dz_in), _width(self.dz_out)
            factor = factor + BUMP_AMP_DZ * np.exp(-0.5 * ((r - self.dz_in) / w_in) ** 2)
            factor = factor + BUMP_AMP_DZ * np.exp(-0.5 * ((r - self.dz_out) / w_out) ** 2)
        w_snow = _width(self.r_h2o)
        factor = factor + BUMP_AMP_SNOW * np.exp(-0.5 * ((r - self.r_h2o) / w_snow) ** 2)
        return factor

    def Sigma_solid(self, r):
        """Solid surface density: dust_to_gas × Σ_gas × condensation × bump.  [g/cm²]"""
        r = np.asarray(r, float)
        base = self.p.dust_to_gas * self.star.dust_scale() * self.Sigma_gas(r)
        return base * self._condensation_enhancement(r) * self._bump_factor(r)

    def Sigma_gas_eff(self, r):
        """Gas Σ including the viscosity-transition / snow-line bumps.

        The clean power-law `Sigma_gas` is kept for the M1 regression and mass estimates;
        the *effective* gas profile carries the dead-zone-edge surface-density bumps that
        make the Type I torque reverse sign at a planet trap (Masset+ 2006). Used by the
        torque proxy in traps.py / migration.py, never for the regression.
        """
        return self.Sigma_gas(r) * self._bump_factor(r)

    # ── Gas pressure (for trap finding) ─────────────────────────────────────
    def Pressure(self, r):
        """Midplane gas pressure P = ρ_mid c_s², with the viscosity/snow bumps folded in.

        ρ_mid = Σ_gas / (√(2π) H). The bump factor makes P develop genuine local maxima at
        the derived trap locations, which `traps.py` locates via ∂P/∂r = 0, ∂²P/∂r² < 0.
        """
        r = np.asarray(r, float)
        H_cm = np.maximum(self.scale_height_AU(r) * AU_CM, 1e-3)
        rho_mid = self.Sigma_gas(r) / (np.sqrt(2.0 * np.pi) * H_cm)
        cs2 = self.sound_speed(r) ** 2
        return rho_mid * cs2 * self._bump_factor(r)

    def total_solid_mass(self) -> float:
        """∫ 2π r Σ_solid dr over the disk  [M_earth] — the finite pebble/solid budget that
        all cores must share. Derived from sigma0 / dust_to_gas / f_ice; NOT a new parameter.
        Uses the un-bumped condensation profile (bumps are local concentration, not extra
        mass) to avoid double-counting solids."""
        from .params import M_EARTH
        r = self.r
        sig = self.p.dust_to_gas * self.star.dust_scale() * self.Sigma_gas(r) \
            * self._condensation_enhancement(r)
        integrand = 2.0 * np.pi * (r * AU_CM) * sig            # g per cm of radius
        mass_g = np.trapz(integrand, r * AU_CM)
        return float(mass_g / M_EARTH)

    # ── Convenience ─────────────────────────────────────────────────────────
    def summary(self) -> dict:
        return {
            "star": self.star.name,
            "r_snow_AU": round(self.r_h2o, 4),
            "r_co2_AU": round(self.r_co2, 4),
            "r_co_AU": round(self.r_co, 4),
            "dz_in_AU": None if self.dz_in is None else round(self.dz_in, 4),
            "dz_out_AU": None if self.dz_out is None else round(self.dz_out, 4),
        }
