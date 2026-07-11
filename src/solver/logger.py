"""The mechanism logger (guide §5) — the whole point of the instrument.

Every position-determining event appends one structured record. A run without a complete
mechanism log is an invalid run (guide §3.4). Post-run, `analyze_log.py` classifies each
final adjacent-pair spacing by its *binding constraint* — and that distribution is the
Branch A / B / C verdict, read from data instead of argued from proximity.

Records are plain dicts so they serialize to JSONL directly. The canonical event vocabulary:

  seeded            {body, at_AU, mass_Me, trap}      embryo born at a trap
  growth            {body, at_AU, mass_Me}            pebble/gas mass update (throttled)
  migrating         {body, from_AU, to_AU, mode}      Type I / Type II step (throttled)
  trapped           {body, at_AU, trap}               halted at a migration trap
  released          {body, at_AU, trap}               left a trap (trap dissolved / pushed out)
  gap_opened        {body, at_AU}                      met the Type II gap criterion
  resonance_capture {body, with, pq, offset}          convergent pair locked into p:q
  hill_limited      {body, with, K}                    spacing set by the mutual-Hill floor
  ejected           {body, at_AU}                      stability relaxation removed it
  merged            {body, into, at_AU}                stability relaxation merged it
  disk_dissipated   {t_Myr}                            end of the gas phase
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TextIO

EVENTS = {
    "seeded", "growth", "migrating", "trapped", "released", "gap_opened",
    "resonance_capture", "hill_limited", "ejected", "merged", "disk_dissipated",
}

# Events that determine a body's *final position* — one of these must exist per surviving
# body for the log to be considered complete (guide §3.4).
POSITION_DETERMINING = {"trapped", "resonance_capture", "hill_limited", "seeded"}


@dataclass
class MechanismLogger:
    records: List[Dict[str, Any]] = field(default_factory=list)
    # Throttle high-frequency events so the log stays a *mechanism* trace, not a dump.
    _last_growth: Dict[int, float] = field(default_factory=dict)
    _last_migrate: Dict[int, float] = field(default_factory=dict)

    def log(self, t_Myr: float, body: Optional[int], event: str, **fields: Any) -> None:
        if event not in EVENTS:
            raise ValueError(f"unknown event '{event}' (guide §5 vocabulary: {sorted(EVENTS)})")
        rec: Dict[str, Any] = {"t_Myr": round(float(t_Myr), 4), "event": event}
        if body is not None:
            rec["body"] = int(body)
        for k, v in fields.items():
            rec[k] = round(v, 4) if isinstance(v, float) else v
        self.records.append(rec)

    # Convenience wrappers for the events the integrator emits most.
    def seeded(self, t, body, at_AU, mass_Me, trap):
        self.log(t, body, "seeded", at_AU=at_AU, mass_Me=mass_Me, trap=trap)

    def growth(self, t, body, at_AU, mass_Me, dt_throttle=0.1):
        if t - self._last_growth.get(body, -1e9) >= dt_throttle:
            self._last_growth[body] = t
            self.log(t, body, "growth", at_AU=at_AU, mass_Me=mass_Me)

    def migrating(self, t, body, from_AU, to_AU, mode, dt_throttle=0.1):
        if t - self._last_migrate.get(body, -1e9) >= dt_throttle:
            self._last_migrate[body] = t
            self.log(t, body, "migrating", from_AU=from_AU, to_AU=to_AU, mode=mode)

    def trapped(self, t, body, at_AU, trap):
        self.log(t, body, "trapped", at_AU=at_AU, trap=trap)

    def released(self, t, body, at_AU, trap):
        self.log(t, body, "released", at_AU=at_AU, trap=trap)

    def gap_opened(self, t, body, at_AU):
        self.log(t, body, "gap_opened", at_AU=at_AU)

    def resonance_capture(self, t, body, with_body, pq, offset):
        self.log(t, body, "resonance_capture", with_=with_body, pq=pq, offset=offset)

    def hill_limited(self, t, body, with_body, K):
        self.log(t, body, "hill_limited", with_=with_body, K=K)

    def ejected(self, t, body, at_AU):
        self.log(t, body, "ejected", at_AU=at_AU)

    def merged(self, t, body, into, at_AU):
        self.log(t, body, "merged", into=into, at_AU=at_AU)

    def disk_dissipated(self, t):
        self.log(t, None, "disk_dissipated")

    # ── Serialization ───────────────────────────────────────────────────────
    def write_jsonl(self, fh: TextIO) -> None:
        for rec in self.records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in self.records)

    # ── Completeness check (guide §3.4) ──────────────────────────────────────
    def is_complete(self, surviving_bodies: List[int]) -> bool:
        """A log is complete iff every surviving body has at least one position-determining
        event. Missing coverage means the run cannot explain a planet's position → invalid."""
        return not self.missing_bodies(surviving_bodies)

    def missing_bodies(self, surviving_bodies: List[int]) -> List[int]:
        determined = {
            r.get("body") for r in self.records if r["event"] in POSITION_DETERMINING
        }
        return [b for b in surviving_bodies if b not in determined]


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
