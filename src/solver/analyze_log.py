"""M6 — Mechanism verdict.

Reads a run's mechanism log + final architecture and classifies each final adjacent-pair
spacing by its BINDING CONSTRAINT:

  resonance(p:q) — the outer body is locked in a mean-motion resonance with the inner  [Branch A]
  trap_anchor    — the spacing is set by one/both bodies sitting at a disk boundary trap [Branch B]
  hill_packing   — the spacing is set by the mutual-Hill stability floor                [Branch C]
  unbound        — none of the above constrains it

The distribution of these constraints across a converged run *is* the Branch A/B/C verdict,
read from data instead of argued from proximity (guide §5/§6). This module makes no claim
about which branch "should" win — it reports what the mechanism log says.

Run:  py -3.11 -m src.solver.analyze_log runs/<name>/mechanism.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

from .logger import read_jsonl


@dataclass
class PairVerdict:
    inner_id: int
    outer_id: int
    a_inner: float
    a_outer: float
    ratio: float            # period ratio
    constraint: str         # resonance | trap_anchor | hill_packing | unbound
    detail: str


def classify_pairs(architecture: List[dict], records: List[dict]) -> List[PairVerdict]:
    """Classify each adjacent pair. Precedence: an explicit resonance lock wins; else a trap
    anchor; else a logged Hill limit; else unbound."""
    arch = sorted(architecture, key=lambda a: a["a_AU"])
    hill_events = {(r.get("with_"), r.get("body")) for r in records if r["event"] == "hill_limited"}
    trapped_ids = {a["id"] for a in arch if a.get("trapped")}

    verdicts: List[PairVerdict] = []
    for inner, outer in zip(arch[:-1], arch[1:]):
        pr = (outer["a_AU"] / inner["a_AU"]) ** 1.5
        if outer.get("pq"):
            constraint, detail = "resonance", outer["pq"]
        elif inner["id"] in trapped_ids or outer["id"] in trapped_ids:
            anchor = "both" if (inner["id"] in trapped_ids and outer["id"] in trapped_ids) \
                else ("inner" if inner["id"] in trapped_ids else "outer")
            constraint, detail = "trap_anchor", f"{anchor} at trap"
        elif (inner["id"], outer["id"]) in hill_events:
            constraint, detail = "hill_packing", "K mutual-Hill floor"
        else:
            constraint, detail = "unbound", ""
        verdicts.append(PairVerdict(inner["id"], outer["id"], inner["a_AU"],
                                    outer["a_AU"], round(pr, 3), constraint, detail))
    return verdicts


def branch_verdict(dist: Counter) -> str:
    mapping = {"resonance": "Branch A (resonance-organized)",
               "trap_anchor": "Branch B (boundary-anchored)",
               "hill_packing": "Branch C (Hill-packed)",
               "unbound": "unconstrained"}
    if not dist:
        return "no adjacent pairs to classify (0 or 1 surviving planet)"
    top, n = dist.most_common(1)[0]
    total = sum(dist.values())
    return f"dominant constraint: {mapping[top]} — {n}/{total} pairs"


def analyze(run_dir_or_jsonl: str) -> dict:
    if run_dir_or_jsonl.endswith(".jsonl"):
        jsonl = run_dir_or_jsonl
        run_dir = os.path.dirname(jsonl)
    else:
        run_dir = run_dir_or_jsonl
        jsonl = os.path.join(run_dir, "mechanism.jsonl")
    records = read_jsonl(jsonl)
    manifest_path = os.path.join(run_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"need manifest.json alongside the log at {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    verdicts = classify_pairs(manifest["architecture"], records)
    dist = Counter(v.constraint for v in verdicts)
    event_counts = Counter(r["event"] for r in records)
    return {"verdicts": verdicts, "distribution": dist, "event_counts": event_counts,
            "manifest": manifest}


def report(res: dict) -> str:
    verdicts: List[PairVerdict] = res["verdicts"]
    dist: Counter = res["distribution"]
    lines = [
        "=" * 64,
        "M6 MECHANISM VERDICT (guide §6) — read from the log, not argued",
        "=" * 64,
        f"system: {res['manifest'].get('system')}   "
        f"planets: {len(res['manifest']['architecture'])}   "
        f"log complete: {res['manifest'].get('complete_log')}",
        "",
        "adjacent-pair binding constraints:",
        f"  {'inner→outer (AU)':>22s} {'ratio':>7s}  constraint",
    ]
    for v in verdicts:
        lines.append(f"  {v.a_inner:9.3f} → {v.a_outer:8.3f} {v.ratio:7.3f}  "
                     f"{v.constraint:13s} {v.detail}")
    lines += ["", "distribution:"]
    total = sum(dist.values()) or 1
    for k in ("resonance", "trap_anchor", "hill_packing", "unbound"):
        n = dist.get(k, 0)
        lines.append(f"  {k:13s} {n:3d}  ({100*n/total:5.1f}%)")
    lines += ["", branch_verdict(dist),
              "",
              "event tally: " + ", ".join(f"{k}={v}" for k, v in
                                          sorted(res["event_counts"].items())),
              "=" * 64]
    return "\n".join(lines)


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="M6 mechanism verdict.")
    ap.add_argument("log", help="path to mechanism.jsonl or the run directory")
    args = ap.parse_args(argv)
    res = analyze(args.log)
    print(report(res))


if __name__ == "__main__":
    main()
