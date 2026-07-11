"""M3/M4 acceptance: embryo growth, trap-halting migration, resonance capture, Hill spacing."""
import numpy as np
import pytest

from src.solver.params import Params, SUN
from src.solver.disk import DiskModel
from src.solver import traps
from src.solver.embryos import (Embryo, isolation_mass, seed_population, grow,
                                pebble_growth_rate, Z_CRIT)
from src.solver.migration import type_I_da_dt, _torque_interpolator, gap_opened
from src.solver import resonance as R
from src.solver import stability as S


@pytest.fixture
def disk():
    return DiskModel(Params(T0=380), SUN)


# ── embryos ──────────────────────────────────────────────────────────────────
def test_isolation_mass_positive_and_grows_outward(disk):
    assert isolation_mass(disk, 1.0) > 0
    assert isolation_mass(disk, 20.0) > isolation_mass(disk, 1.0)  # h flares outward


def test_growth_is_monotone_and_bounded(disk):
    e = Embryo(0, 5.0, 0.01, 0.01)
    m0 = e.mass
    grow(disk, e, 0.1, Params(T0=380))
    assert e.mass >= m0
    # core never exceeds the local isolation mass
    assert e.core <= isolation_mass(disk, e.a) + 1e-9


def test_seed_population_respects_threshold(disk):
    embs = seed_population(disk, disk.p, n_seeds=24)
    assert embs, "fiducial disk should seed at least one embryo"
    for e in embs:
        z = float(disk.Sigma_solid(e.a)) / float(disk.Sigma_gas(e.a))
        assert z >= Z_CRIT


# ── migration halts at traps (M3) ────────────────────────────────────────────
def test_torque_direction_flips_across_a_trap(disk):
    ti = _torque_interpolator(disk)
    # use an actual torque-reversal radius; its basin of attraction is narrow, so probe close
    rz = traps.find_torque_reversals(disk)[0].r_AU
    inside = Embryo(0, rz * 0.99, 5.0, 5.0)
    outside = Embryo(1, rz * 1.01, 5.0, 5.0)
    v_in = type_I_da_dt(disk, inside, ti)
    v_out = type_I_da_dt(disk, outside, ti)
    # just outside the trap → inward; just inside → outward (converging on the trap)
    assert v_out < 0 < v_in


def test_gap_opens_only_for_massive_bodies(disk):
    small = Embryo(0, 5.0, 1.0, 1.0)
    big = Embryo(1, 5.0, 300.0, 300.0)
    assert not gap_opened(disk, small)
    assert gap_opened(disk, big)


# ── resonance (M4) ───────────────────────────────────────────────────────────
def test_capture_probability_falls_with_speed():
    slow = R.capture_probability(1, conv_rate=0.001, width=0.1, f_capture=1.0)
    fast = R.capture_probability(1, conv_rate=10.0, width=0.1, f_capture=1.0)
    assert slow > fast
    assert 0.0 <= fast <= slow <= 1.0


def test_lower_order_resonance_captures_more_easily():
    first = R.capture_probability(1, conv_rate=0.05, width=0.1, f_capture=1.0)
    fourth = R.capture_probability(4, conv_rate=0.05, width=0.1, f_capture=1.0)
    assert first >= fourth


def test_nearest_resonance_finds_2to1():
    res = R.nearest_resonance(2.0)
    assert res is not None and (res[0], res[1]) == (2, 1)


def test_capture_never_pushes_outward():
    inner = Embryo(0, 1.0, 5.0, 5.0)
    outer = Embryo(1, 1.4, 5.0, 5.0)   # already inside the 2:1 nominal (1.587)
    a_before = outer.a
    R.apply_capture(inner, outer, 2, 1)
    assert outer.a <= a_before + 1e-12
    assert outer.partner == inner.id and outer.pq == "2:1"


# ── stability (M4) ───────────────────────────────────────────────────────────
def test_mutual_hill_and_separation():
    inner = Embryo(0, 1.0, 1.0, 1.0)
    outer = Embryo(1, 1.5, 1.0, 1.0)
    rh = S.mutual_hill_radius(inner, outer, SUN.M_star)
    assert rh > 0
    assert S.separation_in_hill(inner, outer, SUN.M_star) == pytest.approx((0.5) / rh)


def test_merge_conserves_mass_and_kills_outer():
    inner = Embryo(0, 1.0, 2.0, 1.0)
    outer = Embryo(1, 1.2, 1.0, 0.5)
    S.merge_pair(inner, outer)
    assert inner.mass == pytest.approx(3.0)
    assert inner.core == pytest.approx(1.5)
    assert not outer.alive
    assert 1.0 <= inner.a <= 1.2
