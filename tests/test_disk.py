"""M1 acceptance: reproduce v1's Σ/T/B profiles within 1% on identical inputs; ice lines and
the DERIVED dead zone behave. The v1 formulas are recomputed here independently (from
reference/formation_solver.html diskModel) so the regression is not self-referential."""
import numpy as np
import pytest

from src.solver.params import Params, SUN
from src.solver.disk import (DiskModel, PLASMA_BETA, T_H2O, T_CO2, T_CO, T_ION, SIGMA_DZ)


@pytest.fixture
def disk():
    return DiskModel(Params(), SUN)


def test_sigma_matches_v1(disk):
    # v1: Σ = σ0 * r^-p * exp(-r/r_disk)
    r = np.linspace(0.1, 50, 500)
    v1 = disk.p.sigma0 * r ** (-disk.p.p) * np.exp(-r / disk.p.r_disk)
    got = disk.Sigma_gas(r)
    assert np.allclose(got, v1, rtol=1e-3)


def test_temperature_matches_v1(disk):
    # v1: T = T0 * L^0.25 * r^-0.5 (opacity_f=1, L=1)
    r = np.linspace(0.1, 50, 500)
    v1 = disk.p.T0 * (SUN.L_star ** 0.25) * r ** (-0.5)
    assert np.allclose(disk.T_profile(r), v1, rtol=1e-3)


def test_B_matches_v1(disk):
    r = np.linspace(0.1, 50, 500)
    v1 = 13.0 * PLASMA_BETA ** (-0.5) * r ** (-13.0 / 8.0)
    assert np.allclose(disk.B_profile(r), v1, rtol=1e-3)


def test_ice_lines_ordered(disk):
    # colder condensates freeze out farther from the star
    assert disk.r_h2o < disk.r_co2 <= disk.r_co


def test_ice_line_temperature_consistency(disk):
    # T at the snow line must equal the H2O condensation temperature (unless capped)
    if disk.r_h2o < disk.p.r_disk:
        assert disk.T_profile(disk.r_h2o) == pytest.approx(T_H2O, rel=1e-6)


def test_dead_zone_derived_not_free(disk):
    # dz_in/out are computed from ionization criteria, not parameters
    assert disk.has_dead_zone()
    assert disk.dz_in < disk.dz_out
    # inner edge is where T crosses the ionization temperature
    assert disk.T_profile(disk.dz_in) == pytest.approx(T_ION, rel=1e-3)
    # outer edge is where the column thins to the penetration threshold
    assert disk.Sigma_gas(disk.dz_out) == pytest.approx(SIGMA_DZ, rel=1e-2)


def test_alpha_suppressed_in_dead_zone(disk):
    from src.solver.disk import ALPHA_ACTIVE, DEAD_ZONE_ALPHA_FRAC
    mid = 0.5 * (disk.dz_in + disk.dz_out)
    a_mid = disk.alpha_profile(np.array([mid]))[0]
    assert a_mid == pytest.approx(ALPHA_ACTIVE * DEAD_ZONE_ALPHA_FRAC)


def test_pressure_positive_and_finite(disk):
    assert np.all(np.isfinite(disk.pressure))
    assert np.all(disk.pressure > 0)


def test_no_observed_positions_imported():
    # guide §3.3: disk.py must not reference observed planet positions
    import inspect
    import src.solver.disk as d
    src = inspect.getsource(d)
    assert "OBSERVED" not in src and "0.387" not in src  # Mercury's a as a canary
