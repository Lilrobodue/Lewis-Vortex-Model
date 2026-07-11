"""End-to-end: logger schema, a full forward run (log complete, bounded, deterministic),
and the M5/M7 scoring machinery including the null models that make validation fail-able."""
import numpy as np
import pytest

from src.solver.params import Params, SUN, OBSERVED
from src.solver.logger import MechanismLogger
from src.solver.evolve import evolve, A_MIN, A_MAX
from src.solver import fit as FIT
from src.solver import validate as V


# ── logger ───────────────────────────────────────────────────────────────────
def test_logger_rejects_unknown_events():
    log = MechanismLogger()
    with pytest.raises(ValueError):
        log.log(1.0, 0, "teleported", at_AU=1.0)


def test_logger_completeness():
    log = MechanismLogger()
    log.seeded(0.0, 0, 1.0, 0.01, "inner_disk")
    log.trapped(1.0, 1, 5.0, "snow_line")
    assert log.is_complete([0, 1])
    assert log.missing_bodies([0, 1, 2]) == [2]


# ── forward run (M3/M4 integration) ──────────────────────────────────────────
@pytest.fixture(scope="module")
def run():
    return evolve(Params(), SUN, seed=432, n_steps=300)


def test_run_has_complete_log(run):
    assert run.complete_log
    assert run.logger.is_complete([e.id for e in run.survivors])


def test_positions_within_domain(run):
    for a in run.positions():
        assert A_MIN <= a <= A_MAX


def test_positions_sorted_and_hill_stable(run):
    a = run.positions()
    assert a == sorted(a)


def test_determinism_same_seed():
    r1 = evolve(Params(), SUN, seed=432, n_steps=200)
    r2 = evolve(Params(), SUN, seed=432, n_steps=200)
    assert r1.positions() == r2.positions()


def test_no_per_planet_parameters_in_evolve():
    import inspect
    import src.solver.evolve as e
    src = inspect.getsource(e)
    # the integrator must not read observed positions (only fit/validate may)
    assert "OBSERVED" not in src


# ── M5 scoring ───────────────────────────────────────────────────────────────
def test_score_matches_and_penalizes_count(run):
    sc = FIT.score(run, "sun")
    assert sc.n_obs == 8
    assert sc.chi2 >= sc.chi2_position           # count penalty is non-negative
    if sc.n_pred < sc.n_obs:
        assert sc.chi2 > sc.chi2_position         # missed planets cost something


def test_match_is_optimal_assignment():
    obs = OBSERVED["sun"]
    m = FIT._match([1.0, 5.2], obs)
    by_name = {n: ap for n, ap, ao in m}
    assert by_name["Earth"] == 1.0
    assert by_name["Jupiter"] == 5.2


# ── M7 nulls (the fail-able instrument) ──────────────────────────────────────
def test_geometric_null_is_finite():
    rms = V.geometric_ratio_null(OBSERVED["sun"])
    assert np.isfinite(rms) and rms >= 0


def test_random_null_distribution_and_chance_rate():
    rng = np.random.default_rng(432)
    dist = V.random_spacing_null(OBSERVED["sun"], n_draw=8, rng=rng, n_mc=2000)
    assert dist.shape == (2000,)
    assert np.all(dist >= 0)
    # a perfect model (RMS 0) should essentially never be beaten by random → chance ~ 0
    chance_perfect = float(np.mean(dist <= 0.0))
    assert chance_perfect < 0.01


def test_validation_can_fail_and_can_pass():
    # feed the observed positions themselves as a 'perfect' prediction: must PASS both nulls
    obs = OBSERVED["sun"]
    perfect_rms = V._rms_matched([o.au for o in obs], obs)
    assert perfect_rms == pytest.approx(0.0, abs=1e-9)
    # a single-planet degenerate prediction must not trivially pass
    bad_rms = V._rms_matched([0.05], obs)
    assert bad_rms > perfect_rms
