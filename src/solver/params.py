"""Parameter registry, bounds, citations, and the hard budget guard.

Guide §3 / §6. There are exactly TEN global free parameters, every one describing the
disk or global physics — none describes a planet. Anything a planet "needs" (its position,
its migration fraction, its spacing ratio) is an OUTPUT, computed downstream, never a knob.

Stellar mass / luminosity / metallicity are *inputs per system*, not free parameters.
Dead-zone edges, ice lines, trap positions, and migration rates are *derived*.

The budget is enforced at import time and by a test: adding an 11th free parameter is a
deliberate act that must fail loudly until the README budget table and a commit
justification are updated (guide §3.2).
"""
from __future__ import annotations

from dataclasses import dataclass, fields, asdict
from typing import Dict, Tuple, List

# ─────────────────────────────────────────────────────────────────────────────
# Physical constants (CGS) — ported verbatim from v1's diskModel so the M1
# regression against reference/formation_solver.html is exact.
# ─────────────────────────────────────────────────────────────────────────────
G_CGS = 6.674e-8          # gravitational constant [cm^3 g^-1 s^-2]
M_SUN = 1.989e33          # solar mass [g]
M_EARTH = 5.972e27        # Earth mass [g]
AU_CM = 1.496e13          # 1 AU [cm]
K_BOLTZ = 1.38e-16        # Boltzmann constant [erg/K]
M_H = 1.67e-24            # hydrogen mass [g]
MU_GAS = 2.34             # mean molecular weight (H2 + He)
YEAR_S = 3.156e7          # seconds per year
MYR_S = YEAR_S * 1e6

# ─────────────────────────────────────────────────────────────────────────────
# The parameter budget. Each entry: (name, lo, hi, unit, citation).
# ORDER IS THE OPTIMIZER VECTOR ORDER — do not reorder without updating fit.py.
# ─────────────────────────────────────────────────────────────────────────────
PARAM_BUDGET: List[Tuple[str, float, float, str, str]] = [
    ("sigma0",      200.0, 5000.0, "g/cm^2", "MMSN (Hayashi 1981) to massive disk"),
    ("p",             0.5,    1.5,  "-",      "observed disk profiles (Andrews+ 2010)"),
    ("T0",          200.0,  400.0,  "K",      "passive irradiated disk midplane"),
    ("r_disk",       20.0,   80.0,  "AU",     "observed disk scale radii"),
    ("t_disk",        1.0,   10.0,  "Myr",    "cluster IR-excess surveys (Haisch+ 2001)"),
    ("dust_to_gas",   0.005,  0.03, "-",      "ISM value + metallicity spread"),
    ("f_ice",         2.0,    4.0,  "-",      "H2O condensation solid boost"),
    ("M_crit",        5.0,   15.0,  "M_earth","core-accretion runaway (Pollack+ 1996)"),
    ("K",             8.0,   12.0,  "-",      "Kepler-multi Hill spacing (Pu & Wu 2015)"),
    ("f_capture",     0.1,    1.0,  "-",      "resonance-capture calibration (this work)"),
]

MAX_FREE_PARAMS = 10  # guide §3.2 hard ceiling

PARAM_NAMES: List[str] = [row[0] for row in PARAM_BUDGET]
BOUNDS: List[Tuple[float, float]] = [(row[1], row[2]) for row in PARAM_BUDGET]


@dataclass(frozen=True)
class Params:
    """The ten global free parameters. Defaults sit inside each prior range and give a
    reasonable solar-type disk; the optimizer explores the bounds from here."""
    sigma0: float = 1700.0      # MMSN-ish
    p: float = 1.0
    T0: float = 280.0
    r_disk: float = 40.0
    t_disk: float = 3.0
    dust_to_gas: float = 0.015
    f_ice: float = 3.0
    M_crit: float = 10.0
    K: float = 10.0
    f_capture: float = 0.5

    def to_vector(self) -> List[float]:
        return [getattr(self, n) for n in PARAM_NAMES]

    @classmethod
    def from_vector(cls, vec) -> "Params":
        if len(vec) != len(PARAM_NAMES):
            raise ValueError(f"expected {len(PARAM_NAMES)} params, got {len(vec)}")
        return cls(**{n: float(v) for n, v in zip(PARAM_NAMES, vec)})

    def clipped(self) -> "Params":
        """Return a copy with every value clamped into its prior range."""
        vals = {}
        for n, (lo, hi) in zip(PARAM_NAMES, BOUNDS):
            vals[n] = min(max(getattr(self, n), lo), hi)
        return Params(**vals)

    def in_bounds(self) -> bool:
        return all(lo <= getattr(self, n) <= hi for n, (lo, hi) in zip(PARAM_NAMES, BOUNDS))

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Per-system stellar inputs. NOT free parameters (guide §6). Luminosity and mass
# scale the temperature and orbital dynamics; metallicity scales dust_to_gas.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class StellarInput:
    name: str
    M_star: float      # solar masses
    L_star: float      # solar luminosities
    feh: float = 0.0   # [Fe/H] dex; scales solid fraction as 10**feh

    def dust_scale(self) -> float:
        return 10.0 ** self.feh


SUN = StellarInput("sun", M_star=1.0, L_star=1.0, feh=0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Observed architecture. Guide §3: this may ONLY be read by fit.py and validate.py.
# No module downstream of disk.py may import OBSERVED for anything else.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ObservedPlanet:
    name: str
    au: float
    mass: float        # Earth masses
    kind: str          # "rocky" | "gas" | "ice"


OBSERVED: Dict[str, List[ObservedPlanet]] = {
    "sun": [
        ObservedPlanet("Mercury", 0.387,   0.055, "rocky"),
        ObservedPlanet("Venus",   0.723,   0.815, "rocky"),
        ObservedPlanet("Earth",   1.000,   1.000, "rocky"),
        ObservedPlanet("Mars",    1.524,   0.107, "rocky"),
        ObservedPlanet("Jupiter", 5.203, 317.800, "gas"),
        ObservedPlanet("Saturn",  9.537,  95.160, "gas"),
        ObservedPlanet("Uranus", 19.190,  14.540, "ice"),
        ObservedPlanet("Neptune",30.070,  17.150, "ice"),
    ],
}


def _check_budget() -> None:
    n_free = len(PARAM_BUDGET)
    if n_free > MAX_FREE_PARAMS:
        raise AssertionError(
            f"Parameter budget exceeded: {n_free} > {MAX_FREE_PARAMS} free parameters. "
            "Guide §3.2: adding a parameter needs a written justification and a README "
            "budget-table update. Remove it or raise MAX_FREE_PARAMS deliberately."
        )
    # The dataclass and the budget table must describe the SAME parameters.
    dataclass_names = {f.name for f in fields(Params)}
    budget_names = set(PARAM_NAMES)
    if dataclass_names != budget_names:
        raise AssertionError(
            f"Params dataclass {dataclass_names} disagrees with PARAM_BUDGET {budget_names}"
        )


_check_budget()
