"""
cost.py - effort and cost impact, costed from client inputs (Datum service layer).

Cost per RIBA stage is hours times band cost rate, summed over the people who
booked to that stage. Measured arithmetic on the firm's data. The saving on top
is a labelled projection: the releasable fraction of a stage is the mean over the
tasks active in it of automatability x autonomy, taken up by adoption.

All firm-specific numbers now come from inputs.ClientInputs, not from globals
here. Swap them with cost.set_inputs(inputs.load_inputs("client.yaml")). With no
client file the default (dummy) set is used so the demo runs.

The band rate is COST (salary based), so the figure is the salaried cost of
released capacity, booked only via the margin route (fewer hours) or the growth
route (re-sell freed time as fee). See conversion().
"""
import numpy as np
import bernstein as B
import model as M
import inputs as _inp

INPUTS = _inp.default_inputs()
ADOPTION = INPUTS.adoption          # kept for callers; synced by set_inputs
BAND_ORDER = INPUTS.bands


def set_inputs(ci):
    """Swap in a validated ClientInputs and resync the convenience globals."""
    global INPUTS, ADOPTION, BAND_ORDER
    INPUTS = ci
    ADOPTION = ci.adoption
    BAND_ORDER = ci.bands
    return INPUTS


def stage_saving_rate(s, ci=None):
    """Releasable fraction of a stage before adoption: mean over the tasks active
    in the stage of automatability x autonomy (autonomy from the client inputs)."""
    ci = ci or INPUTS
    tasks = [t for t in (tt for _g, tt in B.TASK_ORDER) if s in B.TASK_STAGE[t]]
    if not tasks:
        return 0.0
    return float(np.mean([M.composite_auto(t) * ci.autonomy[t] for t in tasks]))


def by_stage(adoption=None, ci=None):
    ci = ci or INPUTS
    adoption = ci.adoption["expected"] if adoption is None else adoption
    rate_of = ci.band_rates
    rows = []
    for s_idx, s_name in enumerate(B.STAGES):
        lines = [r for r in ci.timesheet if r["stage"] == s_name]
        hours = sum(r["hours"] for r in lines)
        cost = sum(r["hours"] * rate_of[r["band"]] for r in lines)
        rate = stage_saving_rate(s_idx, ci) * adoption
        rows.append(dict(stage=s_name, idx=s_idx, hours=hours, cost=cost,
                         saved_hours=hours * rate, saved_cost=cost * rate,
                         saved_frac=rate))
    return rows


def by_band(adoption=None, ci=None):
    ci = ci or INPUTS
    adoption = ci.adoption["expected"] if adoption is None else adoption
    stage_idx = {n: i for i, n in enumerate(B.STAGES)}
    out = {b: dict(hours=0.0, saved_hours=0.0, saved_cost=0.0) for b in ci.bands}
    for r in ci.timesheet:
        rate = stage_saving_rate(stage_idx[r["stage"]], ci) * adoption
        out[r["band"]]["hours"] += r["hours"]
        out[r["band"]]["saved_hours"] += r["hours"] * rate
        out[r["band"]]["saved_cost"] += r["hours"] * ci.band_rates[r["band"]] * rate
    return out


def totals(ci=None):
    ci = ci or INPUTS
    out = {}
    for name, adopt in ci.adoption.items():
        rows = by_stage(adopt, ci)
        out[name] = dict(cost=sum(r["cost"] for r in rows),
                         saved_cost=sum(r["saved_cost"] for r in rows),
                         saved_hours=sum(r["saved_hours"] for r in rows))
    return out


def conversion(scenario="expected", ci=None):
    """Released hours are not money until converted. Two routes, each with a
    precondition; doing neither reabsorbs the time."""
    ci = ci or INPUTS
    t = totals(ci)[scenario]
    rc, rh = t["saved_cost"], t["saved_hours"]
    return dict(released_hours=rh,
                margin_value=rc,                       # salary cost avoided
                growth_value=rc * ci.fee_multiplier,   # extra fee if re-sold
                cost=t["cost"])


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        set_inputs(_inp.load_inputs(sys.argv[1]))
    print(f"inputs: {INPUTS.source}")
    base_cost = sum(r["cost"] for r in by_stage())
    print(f"Measured cost base: GBP {base_cost/1e6:.2f}M/year\n")
    print(f"{'stage':26s} {'hours':>8} {'GBP cost':>11} {'releas%':>8} {'GBP released':>12}")
    for r in by_stage():
        print(f"{r['stage']:26s} {r['hours']:8,.0f} {r['cost']:11,.0f} "
              f"{r['saved_frac']*100:7.0f}% {r['saved_cost']:12,.0f}")
    c = conversion()
    print(f"\nReleased {c['released_hours']:,.0f} h/yr -> margin GBP {c['margin_value']:,.0f}"
          f" or growth GBP {c['growth_value']:,.0f}")
