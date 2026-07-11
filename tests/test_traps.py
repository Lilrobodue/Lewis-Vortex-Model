"""M2 acceptance: for a fiducial solar disk, find pressure maxima at the dead-zone edges and
the snow line WITHOUT being told, and keep their positions stable under grid refinement."""
import numpy as np
import pytest

from src.solver.params import Params, SUN
from src.solver.disk import DiskModel
from src.solver import traps


def _fiducial():
    # slightly hotter disk so the inner dead-zone edge lands on the resolved grid (~0.2 AU)
    return DiskModel(Params(T0=380), SUN)


def test_finds_the_three_expected_traps():
    d = _fiducial()
    found = traps.trap_locations(d)
    labels = {t.label for t in found}
    assert "snow_line" in labels
    assert "dead_zone_outer" in labels
    assert "dead_zone_inner" in labels


def test_traps_coincide_with_derived_features():
    d = _fiducial()
    for t in traps.trap_locations(d):
        if t.label == "snow_line":
            assert t.r_AU == pytest.approx(d.r_h2o, rel=0.15)
        elif t.label == "dead_zone_outer":
            assert t.r_AU == pytest.approx(d.dz_out, rel=0.15)


def test_pressure_and_torque_agree():
    # each trap should show up as BOTH a pressure maximum and a torque reversal
    d = _fiducial()
    pmax = [t.r_AU for t in traps.find_pressure_maxima(d)]
    trev = [t.r_AU for t in traps.find_torque_reversals(d)]
    for rp in pmax:
        assert any(abs(rp - rt) / rp < 0.1 for rt in trev), f"no torque reversal near {rp}"


def test_positions_stable_under_grid_refinement():
    coarse = DiskModel(Params(T0=380), SUN, nr=400)
    fine = DiskModel(Params(T0=380), SUN, nr=1600)
    tc = sorted(t.r_AU for t in traps.trap_locations(coarse))
    tf = sorted(t.r_AU for t in traps.trap_locations(fine))
    assert len(tc) == len(tf)
    for a, b in zip(tc, tf):
        assert a == pytest.approx(b, rel=0.05)


def test_torque_reversals_are_stable_convergent():
    # at a found reversal the normalized torque goes + (inside) → − (outside)
    d = _fiducial()
    G = traps.normalized_typeI_torque(d)
    for t in traps.find_torque_reversals(d):
        i = np.searchsorted(d.r, t.r_AU)
        i = min(max(i, 1), len(d.r) - 2)
        assert G[i - 1] > 0 >= G[i + 1] or G[i] > 0 >= G[i + 1]
