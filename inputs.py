"""
inputs.py - the client input schema (Datum service layer).

This is the boundary between the fixed methodology and one firm's engagement. The
framework (classes, task grid, the 2026 proposals) stays in code, the same for
every firm. What changes per firm comes through here, validated on the way in:

  measured   timesheet (hours by band by stage), band cost rates
  firm        fee multiplier (charge-out over cost)
  elicited    adoption bands, tool autonomy per task

Anything not supplied falls back to a labelled default, so the demo still runs,
but a real engagement replaces the lot. Load order:

    inputs.load_inputs("client.yaml")   # or .json, with a CSV timesheet
    cost.set_inputs(those_inputs)

Validation is the point. A schema that does not reject bad data is decoration, so
load_inputs raises on anything that would silently corrupt the numbers, and warns
on data that is merely incomplete.
"""
from dataclasses import dataclass, field
import json
import csv
import os
import bernstein as B
import model as M
import tooling as TL

try:
    import yaml
    _HAS_YAML = True
except Exception:
    _HAS_YAML = False

VALID_STAGES = list(B.STAGES)
VALID_TASKS = [t for _g, t in B.TASK_ORDER]


class InputError(ValueError):
    pass


@dataclass
class ClientInputs:
    timesheet: list                 # list of {"band","stage","hours"}
    band_rates: dict                # band -> cost GBP/hour
    fee_multiplier: float           # charge-out / cost
    adoption: dict                  # {"low","expected","high"} in [0,1]
    autonomy: dict                  # task -> [0,1], full coverage of VALID_TASKS
    source: str = "default"
    warnings: list = field(default_factory=list)

    @property
    def bands(self):
        return list(self.band_rates)


# ---- validation ------------------------------------------------------------
def _num(x, where):
    try:
        return float(x)
    except (TypeError, ValueError):
        raise InputError(f"{where}: '{x}' is not a number")


def validate(ci):
    errs, warns = [], []
    if not ci.band_rates:
        errs.append("band_rates is empty")
    for b, r in ci.band_rates.items():
        if _num(r, f"band_rates[{b}]") <= 0:
            errs.append(f"band_rates[{b}] must be positive, got {r}")

    seen_stage_hours = {s: 0.0 for s in VALID_STAGES}
    for i, row in enumerate(ci.timesheet):
        where = f"timesheet row {i}"
        for k in ("band", "stage", "hours"):
            if k not in row:
                errs.append(f"{where}: missing '{k}'"); break
        else:
            if row["band"] not in ci.band_rates:
                errs.append(f"{where}: band '{row['band']}' has no rate in band_rates")
            if row["stage"] not in VALID_STAGES:
                errs.append(f"{where}: stage '{row['stage']}' is not a RIBA stage")
            h = _num(row["hours"], where)
            if h < 0:
                errs.append(f"{where}: hours negative ({h})")
            if row["stage"] in seen_stage_hours:
                seen_stage_hours[row["stage"]] += h

    a = ci.adoption
    for k in ("low", "expected", "high"):
        if k not in a:
            errs.append(f"adoption missing '{k}'")
        elif not 0 <= _num(a[k], f"adoption[{k}]") <= 1:
            errs.append(f"adoption[{k}] must be in [0,1], got {a[k]}")
    if all(k in a for k in ("low", "expected", "high")):
        if not a["low"] <= a["expected"] <= a["high"]:
            errs.append("adoption must satisfy low <= expected <= high")

    if _num(ci.fee_multiplier, "fee_multiplier") < 1:
        warns.append(f"fee_multiplier {ci.fee_multiplier} < 1 implies charge-out below cost")

    for t, v in ci.autonomy.items():
        if t not in VALID_TASKS:
            errs.append(f"autonomy: '{t}' is not a known task")
        elif not 0 <= _num(v, f"autonomy[{t}]") <= 1:
            errs.append(f"autonomy[{t}] must be in [0,1], got {v}")

    for s, h in seen_stage_hours.items():
        if h == 0:
            warns.append(f"no timesheet hours booked to stage '{s}'")
    missing = [t for t in VALID_TASKS if t not in ci.autonomy]
    if missing:
        warns.append(f"{len(missing)} task(s) using default autonomy (not elicited)")

    if errs:
        raise InputError("invalid client inputs:\n  - " + "\n  - ".join(errs))
    ci.warnings = warns
    return ci


# ---- loading ---------------------------------------------------------------
def load_timesheet_csv(path):
    rows = []
    with open(path, newline="") as f:
        for i, r in enumerate(csv.DictReader(f)):
            need = {"band", "stage", "hours"}
            if not need <= set(r):
                raise InputError(f"{path}: header must contain {sorted(need)}")
            rows.append(dict(band=r["band"].strip(), stage=r["stage"].strip(),
                             hours=_num(r["hours"], f"{path} row {i}")))
    return rows


def _read_config(path):
    with open(path) as f:
        if path.endswith((".yaml", ".yml")):
            if not _HAS_YAML:
                raise InputError("YAML config needs pyyaml; use JSON instead")
            return yaml.safe_load(f)
        return json.load(f)


def load_inputs(path=None):
    """Load and validate a client config (.yaml/.json). Timesheet may be inline
    under 'timesheet' or a CSV path under 'timesheet_csv'. Missing autonomy is
    filled from the elicited 2026 defaults. None -> the dummy default set."""
    if path is None:
        return default_inputs()
    cfg = _read_config(path)
    base = os.path.dirname(os.path.abspath(path))
    if "timesheet_csv" in cfg:
        ts = load_timesheet_csv(os.path.join(base, cfg["timesheet_csv"]))
    elif "timesheet" in cfg:
        ts = [dict(band=r["band"], stage=r["stage"], hours=_num(r["hours"], "timesheet"))
              for r in cfg["timesheet"]]
    else:
        raise InputError("config needs 'timesheet' or 'timesheet_csv'")
    autonomy = dict(TL.AUTONOMY_2026)            # defaults
    autonomy.update(cfg.get("autonomy", {}))     # client overrides
    ci = ClientInputs(
        timesheet=ts,
        band_rates=cfg.get("band_rates", {}),
        fee_multiplier=float(cfg.get("fee_multiplier", 2.8)),
        adoption=cfg.get("adoption", {"low": 0.30, "expected": 0.55, "high": 0.80}),
        autonomy=autonomy,
        source=os.path.basename(path))
    return validate(ci)


# ---- default (dummy) set, so the demo runs with no client file -------------
_RATE = {"Part I": 24, "Part II": 32, "Architect": 42, "Associate": 58, "Director": 85}
_HEADCOUNT = {"Part I": 8, "Part II": 10, "Architect": 12, "Associate": 6, "Director": 4}
_HOURS = 1500.0
_PROD, _SENIOR = {3, 4, 6}, {0, 1, 2, 7}


def _skew(band, s):
    rank = list(_RATE).index(band)
    m = 1.0
    if s in _PROD:
        m *= 1.4 if rank <= 1 else (0.7 if rank >= 3 else 1.0)
    if s in _SENIOR:
        m *= 1.4 if rank >= 3 else (0.8 if rank <= 1 else 1.0)
    return m


def default_inputs():
    base = M.stage_effort()
    ts = []
    for band in _RATE:
        raw = {s: base[s] * _skew(band, s) for s in range(B.NS)}
        tot = sum(raw.values())
        target = _HEADCOUNT[band] * _HOURS
        for s in range(B.NS):
            ts.append(dict(band=band, stage=B.STAGES[s], hours=raw[s] / tot * target))
    ci = ClientInputs(timesheet=ts, band_rates=dict(_RATE), fee_multiplier=2.8,
                      adoption={"low": 0.30, "expected": 0.55, "high": 0.80},
                      autonomy=dict(TL.AUTONOMY_2026), source="default (dummy)")
    return validate(ci)


if __name__ == "__main__":
    import sys
    ci = load_inputs(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"loaded inputs from: {ci.source}")
    print(f"  bands: {', '.join(ci.bands)}")
    print(f"  timesheet rows: {len(ci.timesheet)}, total hours "
          f"{sum(r['hours'] for r in ci.timesheet):,.0f}")
    print(f"  fee multiplier: {ci.fee_multiplier}")
    print(f"  adoption: {ci.adoption}")
    if ci.warnings:
        print("  warnings:")
        for w in ci.warnings:
            print(f"    - {w}")
    else:
        print("  no warnings")
