"""Population-fit plumbing: disjoint train/test split and a finite, sane objective."""
import numpy as np
import pytest

from src.solver.params import Params
from src.solver import fit_population as FP


def _fake_systems(n=20):
    # minimal system dicts with the fields split_systems / _to_syst need
    out = []
    for i in range(n):
        out.append({"name": f"S{i}", "M_star": 1.0, "L_star": 1.0, "feh": 0.0,
                    "planets": [{"au": 0.1 * (i % 3 + 1)}, {"au": 0.2 * (i % 3 + 1)},
                                {"au": 0.4 * (i % 3 + 1)}]})
    return out


def test_split_is_disjoint_and_covers_all():
    systems = _fake_systems(20)
    train, test = FP.split_systems(systems, n_train=8, seed=432)
    assert len(train) == 8 and len(test) == 12
    names_tr = {s[0] for s in train}
    names_te = {s[0] for s in test}
    assert names_tr.isdisjoint(names_te)                 # never train on a test system
    assert names_tr | names_te == {s["name"] for s in systems}


def test_split_is_deterministic():
    systems = _fake_systems(20)
    a = FP.split_systems(systems, 8, 432)[0]
    b = FP.split_systems(systems, 8, 432)[0]
    assert [s[0] for s in a] == [s[0] for s in b]


def test_objective_finite_and_penalizes_empty():
    systems = _fake_systems(6)
    train, _ = FP.split_systems(systems, 4, 432)
    val = FP.population_objective(Params().to_vector(), train, n_steps=80, seed=432)
    assert np.isfinite(val) and val >= 0
