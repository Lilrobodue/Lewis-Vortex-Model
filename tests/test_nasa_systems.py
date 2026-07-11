"""The NASA held-out loader. Skips if the CSV isn't present (it's large and not committed)."""
import glob
import os

import pytest

from src.solver import nasa_systems as N

CSV = next(iter(sorted(glob.glob("PSCompPars_*.csv"))), None)
pytestmark = pytest.mark.skipif(CSV is None, reason="NASA PSCompPars CSV not present")


def test_fnum_parses_and_guards():
    assert N._fnum("1.5") == 1.5
    assert N._fnum("") is None
    assert N._fnum(None) is None


def test_classify_by_mass():
    assert N._classify(0.5) == "rocky"
    assert N._classify(10) == "ice"
    assert N._classify(300) == "gas"
    assert N._classify(None) == "unknown"


def test_build_systems_schema_and_filters():
    systems = N.build_systems(CSV, min_planets=3, max_systems=25)
    assert systems, "expected at least one qualifying multi-planet system"
    for s in systems:
        # schema validate.py depends on
        assert {"name", "M_star", "L_star", "feh", "planets"} <= set(s)
        assert s["n_planets"] >= 3
        assert N.M_LO <= s["M_star"] <= N.M_HI      # host-mass filter
        assert s["L_star"] > 0                        # derived luminosity is positive
        a = [p["au"] for p in s["planets"]]
        assert a == sorted(a) and all(x > 0 for x in a)  # sorted, positive semi-major axes


def test_luminosity_derivation_sane():
    # a Sun-like host (M~1, T~5772, R~1) should land near L~1
    systems = N.build_systems(CSV, min_planets=3)
    sunlike = [s for s in systems if 0.9 <= s["M_star"] <= 1.1]
    assert sunlike
    assert any(0.3 <= s["L_star"] <= 3.0 for s in sunlike)
