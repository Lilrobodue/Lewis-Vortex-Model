"""Guide §3 non-negotiables that are checkable at the parameter layer."""
import pytest

from src.solver import params as P
from src.solver.params import Params, PARAM_NAMES, BOUNDS, MAX_FREE_PARAMS


def test_budget_at_or_under_ten():
    assert len(P.PARAM_BUDGET) <= MAX_FREE_PARAMS == 10


def test_dataclass_matches_budget():
    from dataclasses import fields
    assert {f.name for f in fields(Params)} == set(PARAM_NAMES)


def test_every_param_has_prior_and_citation():
    for name, lo, hi, unit, cite in P.PARAM_BUDGET:
        assert lo < hi, f"{name} has empty prior range"
        assert cite.strip(), f"{name} missing citation (guide §3.2)"


def test_defaults_in_bounds():
    assert Params().in_bounds()


def test_vector_roundtrip():
    p = Params()
    assert Params.from_vector(p.to_vector()).as_dict() == p.as_dict()


def test_clipped_enforces_bounds():
    wild = Params(sigma0=1e9, K=-5)
    c = wild.clipped()
    assert c.in_bounds()
    assert c.sigma0 == BOUNDS[PARAM_NAMES.index("sigma0")][1]
    assert c.K == BOUNDS[PARAM_NAMES.index("K")][0]


def test_no_per_planet_names():
    # guide §2.2 / §3.1: none of v1's per-planet dials may appear as free parameters
    banned = {"a_in", "r_conv", "r_trunc", "f_jup", "s_gas", "s_ice", "f_ur", "f_mig"}
    assert banned.isdisjoint(set(PARAM_NAMES))
