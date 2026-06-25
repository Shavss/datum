"""
ingest.py - adapter for a real practice timesheet export (Datum service layer).

The engine speaks band / RIBA-stage / hours. A real export does not: it carries
the firm's own role titles, its own project-phase names, and a free activity
column, and its rate column is charge-out, not salary cost. This adapter is the
one place that messy reality is reconciled with the clean engine, so the model
never sees a firm-specific string.

It is built against the JSE-001 export (Raff-style timesheet tool, 14 columns,
no header). Point it at another firm's export by editing the three mapping tables
below; nothing downstream changes.

THE THREE MAPPINGS ARE JUDGEMENT, NOT MECHANISM. They are exposed at the top, not
buried, because signing them off is the billable conversation with the firm. Run
`python ingest.py example_client/timesheets.csv` to print the coverage report:
every role, phase and activity, where it mapped, and what did not map. Verify that
before trusting any number built on it.

Honesty of inputs (unchanged):
  measured     hours, and the stage / task effort split derived from them
  provisional  the salary-cost rates (the file has charge-out only; finance must
               supply cost; SALARY_COST_RATES below is a labelled placeholder)
  elicited     autonomy and adoption, as before, from the workshop
"""
import csv
import os
from collections import defaultdict

import bernstein as B

# ---- column layout ---------------------------------------------------------
# The canonical export columns, in order. Some exports ship this as a header row
# (Employee, Date, Project#, Project Name, Role, Rate, Hours, Value, Activity,
# Billable, Phase, Fee Type, Note); others ship raw with no header. When a header
# is present its names are used (robust to reordering); otherwise these fixed
# positions apply. Either way the engine only needs role, phase, activity, hours.
COL = dict(name=0, date=1, code=2, project=3, role=4, rate=5, hours=6,
           amount=7, activity=8, billable=9, phase=10, feetype=11, desc=12)

# field -> header names that identify it (lowercased). role/hours/activity/phase
# are essential; rate (charge-out) is optional, used for the measured growth route.
HEADER_NAMES = {"role": {"role"}, "hours": {"hours", "hrs"},
                "activity": {"activity", "task"}, "phase": {"phase", "stage"}}
_OPTIONAL_HEADERS = {"rate": {"rate", "charge-out", "chargeout"},
                     "employee": {"employee", "name", "staff"}}


def _resolve_columns(first_row):
    """If first_row looks like a header, return field->index by name; else None
    and the fixed COL positions are used."""
    low = [c.strip().lower() for c in first_row]
    idx = {}
    for field, names in {**HEADER_NAMES, **_OPTIONAL_HEADERS}.items():
        for i, c in enumerate(low):
            if c in names:
                idx[field] = i
                break
    return idx if all(f in idx for f in HEADER_NAMES) else None


# ---- 1. ROLE -> Datum band -------------------------------------------------
# Datum bands, junior to senior: Part I, Part II, Architect, Associate, Director.
# Year tags ("Associate 2023") and spacing are normalised before lookup. Marked
# (?) are the calls most worth a second look with the firm.
ROLE_TO_BAND = {
    "Intern": "Part I",
    "Project Designer": "Part II",          # unlicensed designer
    "Junior Architect": "Architect",        # newly licensed
    "Junior Arch": "Architect",
    "Intermediate Architect": "Architect",
    "Intermediate Arch": "Architect",
    "Senior Architect": "Architect",        # (?) could be Associate
    "Project Manager": "Associate",         # (?) function not grade; rate ~ Associate
    "Associate": "Associate",
    "Principal": "Director",
}


# ---- 2. project PHASE -> RIBA stage (Datum B.STAGES name) ------------------
# Canadian / OAA phases do not line up one-to-one with RIBA. Most are clean; the
# (?) lines are judgement. Permits & Approvals has no native RIBA home.
PHASE_TO_STAGE = {
    "1 - Pre-Design": "Preparation + Briefing",
    "2 - Schematic Design": "Concept Design",
    "3 - Design Development": "Spatial Coordination",
    "4 - Construction Documentation": "Technical Design",
    "5 - Permits & Approvals": "Technical Design",      # (?) permit drawings are technical
    "7 - Construction Administration": "Manufacturing + Construction",
    "10 - Interior Design": "Technical Design",         # negligible hours
    # "11 - Additional Scope": intentionally unmapped -> excluded from the base
}


# ---- 3. ACTIVITY -> Bernstein task (removes the even-split placeholder) -----
# Lossy by nature: one activity word stands for a task. The dominant bucket,
# "Design Work" (28% of rows), is the call that moves the most, marked (!). Edit
# freely; unmapped activities are reported and excluded from the task split.
ACTIVITY_TO_TASK = {
    "Design Work": "Coordinating spatial and technical systems",     # (!) dominant; detailed design in DD/CD
    "Specialized Design": "Coordinating spatial and technical systems",
    "Internal Meeting": "Assigning and coordinating work",
    "Meeting Preparation": "Assigning and coordinating work",
    "Project Planning": "Managing project staffing resources",
    "Administration": "Managing practice operations",
    "Principal Hours": "Reviewing and approving technical documents",  # (?) principal oversight
    "Client Communications": "Meeting / managing clients and decisions",
    "Client Meeting": "Meeting / managing clients and decisions",
    "Consultant Coordination and Communications": "Coordinating consultants and others",
    "Contractor Communications": "Reviewing construction progress",
    "Construction Drawings": "Producing technical documentation",
    "Building Permit Drawings": "Producing technical documentation",
    "Measured Drawings": "Analysing and understanding the brief",     # existing-conditions survey
    "Site Plan": "Producing technical documentation",
    "Authorities Communication": "Coordinating with regulators",
    "Committee of Adjustment Process": "Coordinating with regulators",
    "Approvals Process": "Coordinating with regulators",
    "Building Permit Process": "Coordinating with regulators",
    "PPR or ZC Process": "Coordinating with regulators",
    "Zoning Review": "Coordinating with regulators",
    "Building Code Review": "Evaluating / integrating technical considerations",
    "Products and Materials": "Evaluating / integrating technical considerations",
    "Library / Samples / Resources": "Evaluating / integrating technical considerations",
    "Material Review": "Reviewing and approving technical documents",
    "Drawing Review": "Reviewing and approving technical documents",
    "Site Meeting": "Reviewing construction progress",
    "Research": "Analysing and understanding the brief",
    # Non-billable, Travel, Extra/Additional Work: real hours but no task home;
    # they count toward stage cost but are excluded from the task-effort split.
}
_NO_TASK = {"Non-billable", "Travel", "Extra/Additional Work"}


# ---- 4. salary-cost rates (PROVISIONAL) ------------------------------------
# The export's rate column is CHARGE-OUT, not cost. The cost base and the
# margin / growth logic need salary cost. These placeholders are derived from
# this firm's own hours-weighted charge-out per band divided by 2.8 (a typical
# charge-out / cost ratio), so the pilot shows believable numbers in the right
# currency. REPLACE with finance figures: fully-loaded hourly cost per band, i.e.
# (annual salary x on-cost factor) / annual productive hours. Until then the cost
# base is provisional and the report says so.
CURRENCY = "CA$"                 # the export is Canadian
SALARY_COST_RATES = {            # CA$/hour, salary based - PLACEHOLDER, replace
    "Part I": 38, "Part II": 42, "Architect": 51, "Associate": 57, "Director": 91,
}
RATES_ARE_PROVISIONAL = True


def _canon_role(raw):
    """Strip year tags and whitespace, then look up. Returns (band or None)."""
    s = raw.strip()
    for tag in ("2021", "2022", "2023", "2024", "2025"):
        s = s.replace(tag, "")
    s = " ".join(s.split())
    return ROLE_TO_BAND.get(s)


def read_raw(path):
    with open(path, newline="") as f:
        all_rows = list(csv.reader(f))
    if not all_rows:
        return []
    col = _resolve_columns(all_rows[0])         # by header name, if present
    data = all_rows[1:] if col else all_rows    # skip the header row when found
    col = col or COL                            # else fixed positions
    rate_i = col.get("rate", COL["rate"])       # charge-out, optional
    emp_i = col.get("employee", COL["name"])    # person, for role recovery
    need = max(col["role"], col["phase"], col["activity"], col["hours"], rate_i, emp_i)
    rows = []
    for r in data:
        if len(r) <= need:
            continue
        try:
            h = float(r[col["hours"]])          # also skips any stray header / junk
        except ValueError:
            continue
        try:
            rate = float(r[rate_i])
        except (ValueError, IndexError):
            rate = None
        rows.append(dict(employee=r[emp_i].strip(), role=r[col["role"]],
                         phase=r[col["phase"]].strip(),
                         activity=r[col["activity"]].strip(), hours=h, rate=rate))
    return rows


def build(path):
    """Map a raw export into the engine's vocabulary. Returns a dict with the
    band/stage timesheet, the task-hours split, and a coverage report listing
    every value that did or did not map."""
    raw = read_raw(path)
    timesheet = []                      # {band, stage, hours} for cost + stage effort
    task_hours = defaultdict(float)     # task -> hours, the measured split
    unmapped = dict(role=defaultdict(float), phase=defaultdict(float),
                    activity=defaultdict(float))
    mapped = dict(role=defaultdict(float), phase=defaultdict(float),
                  activity=defaultdict(float))
    total = 0.0
    co_hours = defaultdict(float)       # band -> hours with a charge-out rate
    co_value = defaultdict(float)       # band -> charge-out value (rate x hours)

    # a person's grade, inferred from their own valid rows, so a mis-tagged role
    # (e.g. "2024") is recovered from who logged it rather than dropped.
    emp_band_hours = defaultdict(lambda: defaultdict(float))
    for r in raw:
        b = _canon_role(r["role"])
        if b:
            emp_band_hours[r["employee"]][b] += r["hours"]
    emp_band = {e: max(bh, key=bh.get) for e, bh in emp_band_hours.items()}
    recovered = defaultdict(float)      # employee -> hours recovered

    for r in raw:
        total += r["hours"]
        band = _canon_role(r["role"])
        stage = PHASE_TO_STAGE.get(r["phase"])
        if band is None and emp_band.get(r["employee"]):
            band = emp_band[r["employee"]]          # recover from the person
            recovered[f"{r['employee']} (role '{r['role'].strip()}' -> {band})"] += r["hours"]
        elif band is None:
            unmapped["role"][r["role"].strip()] += r["hours"]
        else:
            mapped["role"][r["role"].strip()] += r["hours"]
        if stage is None:
            unmapped["phase"][r["phase"]] += r["hours"]
        else:
            mapped["phase"][r["phase"]] += r["hours"]

        if band is not None and stage is not None:
            timesheet.append(dict(band=band, stage=stage, hours=r["hours"]))
        if band is not None and r.get("rate"):
            co_hours[band] += r["hours"]
            co_value[band] += r["rate"] * r["hours"]

        act = r["activity"]
        if act in _NO_TASK:
            mapped["activity"][act] += r["hours"]          # counted, no task home
        elif act in ACTIVITY_TO_TASK:
            task_hours[ACTIVITY_TO_TASK[act]] += r["hours"]
            mapped["activity"][act] += r["hours"]
        else:
            unmapped["activity"][act] += r["hours"]

    chargeout = {b: co_value[b] / co_hours[b] for b in co_hours if co_hours[b]}
    return dict(timesheet=timesheet, task_hours=dict(task_hours),
                mapped=mapped, unmapped=unmapped, recovered=dict(recovered),
                total_hours=total,
                chargeout=chargeout,                       # band -> hours-weighted charge-out
                notional_value=sum(co_value.values()),     # charge-out value of all time
                n_rows=len(raw), source=os.path.basename(path))


# ---- coverage report (verify the mappings before trusting the numbers) -----
def _section(title, mp, un):
    out = [f"\n{title}"]
    cov = sum(mp.values())
    for k, v in sorted(mp.items(), key=lambda kv: -kv[1]):
        out.append(f"  ok   {v:8.0f} h  {k}")
    for k, v in sorted(un.items(), key=lambda kv: -kv[1]):
        out.append(f"  ??   {v:8.0f} h  {k}   [UNMAPPED]")
    un_h = sum(un.values())
    out.append(f"  ---- mapped {cov:,.0f} h, unmapped {un_h:,.0f} h "
               f"({un_h/(cov+un_h)*100 if cov+un_h else 0:.1f}% of hours)")
    return "\n".join(out)


def coverage_report(b):
    L = ["=" * 78,
         f"INGEST COVERAGE - {b['source']}  ({b['n_rows']} rows, {b['total_hours']:,.0f} h)",
         "=" * 78,
         _section("ROLE -> band", b["mapped"]["role"], b["unmapped"]["role"]),
         _section("PHASE -> RIBA stage", b["mapped"]["phase"], b["unmapped"]["phase"]),
         _section("ACTIVITY -> Bernstein task", b["mapped"]["activity"], b["unmapped"]["activity"])]
    if b.get("recovered"):
        L.append("\nROLE recovered from the employee (mis-tagged role backfilled "
                 "from the person's other rows):")
        for k, v in sorted(b["recovered"].items(), key=lambda kv: -kv[1]):
            L.append(f"  ++   {v:8.1f} h  {k}")
    # task split summary
    th = b["task_hours"]
    L.append("\nTASK SPLIT (measured, replaces the even-split placeholder):")
    for t, h in sorted(th.items(), key=lambda kv: -kv[1]):
        L.append(f"  {h:8.0f} h  {t}")
    L.append(f"  ---- {sum(th.values()):,.0f} h assigned to {len(th)} of {len(B.TASK_STAGE)} tasks")
    # measured charge-out (price side, from the rate column)
    co = b.get("chargeout") or {}
    if co:
        L.append(f"\nCHARGE-OUT (measured from the rate column; the price side, not cost):")
        for band in ["Part I", "Part II", "Architect", "Associate", "Director"]:
            if band in co:
                cost = SALARY_COST_RATES.get(band)
                ratio = f"  ({co[band]/cost:.1f}x provisional cost)" if cost else ""
                L.append(f"  {CURRENCY}{co[band]:6.0f}/h  {band}{ratio}")
        L.append(f"  ---- notional fee value of all time: {CURRENCY}{b['notional_value']:,.0f}. "
                 f"Used to value the growth route at real rates.")
    if RATES_ARE_PROVISIONAL:
        L.append("\nNOTE: salary-cost rates are PROVISIONAL placeholders (the export has "
                 "charge-out only).\n      Replace SALARY_COST_RATES with finance figures "
                 "before the cost base is real.")
    return "\n".join(L)


# ---- bridge to the engine --------------------------------------------------
def to_client_inputs(b):
    """A validated ClientInputs from the mapped export: real hours, provisional
    salary-cost rates, default elicited assumptions (replaced in the workshop)."""
    import inputs as _inp
    import tooling as TL
    ci = _inp.ClientInputs(
        timesheet=b["timesheet"],
        band_rates=dict(SALARY_COST_RATES),
        fee_multiplier=2.8,
        adoption={"low": 0.30, "expected": 0.55, "high": 0.80},
        autonomy=dict(TL.AUTONOMY_2026),
        chargeout_rates=b.get("chargeout") or None,    # measured price side
        source=b["source"] + (" (pilot, provisional rates)" if RATES_ARE_PROVISIONAL
                              else " (pilot)"))
    return _inp.validate(ci)


def stage_hours_array(b):
    """Real hours per RIBA stage index, for model.set_measured."""
    import numpy as np
    arr = np.zeros(B.NS)
    idx = {n: i for i, n in enumerate(B.STAGES)}
    for r in b["timesheet"]:
        arr[idx[r["stage"]]] += r["hours"]
    return arr


def apply(path):
    """Ingest a raw export and wire it into the engine (cost inputs + measured
    effort overrides). Returns the build dict for the coverage report and framing."""
    import model as M
    import cost as C
    b = build(path)
    C.set_inputs(to_client_inputs(b))
    M.set_measured(stage_hours=stage_hours_array(b), task_hours=b["task_hours"])
    return b


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python ingest.py <raw_timesheet.csv>")
        raise SystemExit(1)
    b = build(sys.argv[1])
    print(coverage_report(b))
