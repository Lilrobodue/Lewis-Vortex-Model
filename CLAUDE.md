# CLAUDE.md — Formation Solver v2

Read [FORMATION_SOLVER_V2_GUIDE.md](FORMATION_SOLVER_V2_GUIDE.md) fully before touching code.
It is the spec. This file only records how to build, test, and run.

## Environment
- Python 3.11+. On this machine: `py -3.11` (has numpy, scipy, matplotlib, pytest).
- Install deps: `py -3.11 -m pip install -r requirements.txt`

## Commands
- Test:  `py -3.11 -m pytest -q`
- Evaluate a fiducial disk + single forward run:
  `py -3.11 -m src.solver.evolve --system sun`
- Train (M5, DE over global params):
  `py -3.11 -m src.solver.fit --system sun --seed 432`
- Mechanism verdict on a run (M6):
  `py -3.11 -m src.solver.analyze_log runs/<timestamp>/mechanism.jsonl`
- Build held-out set from NASA archive CSV (M7 data):
  `py -3.11 -m src.solver.nasa_systems --out data/held_out.json`
- Validation with null models (M7), Sun self-test:
  `py -3.11 -m src.solver.validate --params runs/<timestamp>/params.json`
- Validation on real held-out systems (M7 proper):
  `py -3.11 -m src.solver.validate --params runs/<timestamp>/params.json --systems data/held_out.json --mc 5000`

## Non-negotiables (see guide §3)
1. No per-planet parameters. All free params describe the disk / global physics.
2. Parameter budget ≤ 10 global free params (`params.py`, `PARAM_BUDGET`). Test enforces this.
3. Positions are outputs. Only `fit.py`/`validate.py` may read observed positions.
4. Mechanism logging is mandatory. A run without a complete log is invalid.
5. Validation must be able to fail — every metric ships a null + Monte Carlo chance rate.
6. Honest reporting. χ² as computed; failures reported as prominently as successes.

## Working agreements (guide §8)
- Run `pytest` before every commit; a failing physics sanity test blocks the commit.
- Every run writes `runs/<timestamp>/` with params, seed, git hash, log, outputs.
- Version-stamp any quoted constant with the run that produced it.
- When something contradicts the guide, stop and surface it to Joseph.
