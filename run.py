"""run.py - print the report and write every figure (each standalone)."""
import numpy as np
import theme
import bernstein as B
from model import task_catalogue, task_future, stage_effort
import views
import rnm
import sensitivity as S
import activities as A
import tooling as TL
import cost as C
import inputs as _inp


def print_report(cat):
    print("=" * 96)
    print("DATUM  -  workflow diagnostic (Bernstein grid + stage timesheets)")
    print("=" * 96)
    cur_group = None
    for r in sorted(cat, key=lambda r: (B.GROUPS.index(r["group"]), -r["effort"])):
        if r["group"] != cur_group:
            print(f"\n[{r['group']}]")
            cur_group = r["group"]
        tag = "  (multi-class)" if r["multiclass"] else ""
        print(f"  {r['task']:50s} {r['effort']*100:4.1f}%  "
              f"{r['cls']:24s} {r['action']}{tag}")
        if r["proposal"]:
            p = r["proposal"]
            print(f"      proposed AI: {p['ai']}")
            print(f"      metric: {p['metric']}")

    routine = sum(r["effort"] for r in cat if r["auto"] >= 0.875)
    oversight = sum(r["effort"] for r in cat if 0.625 <= r["auto"] < 0.875)
    nonroutine = sum(r["effort"] for r in cat if r["auto"] < 0.375)
    middle = 1 - routine - oversight - nonroutine
    cur, fut = task_future(cat, 0.7)
    print("\n" + "-" * 96)
    print("Routine / non-routine split (the old axis, now from Bernstein's class):")
    print(f"  pure procedural, straightforwardly automatable: {routine*100:4.0f}%")
    print(f"  procedural-integrative, automate WITH oversight: {oversight*100:4.0f}%")
    print(f"  integrative middle, augment:                     {middle*100:4.0f}%")
    print(f"  perceptive / judgement, protect:                 {nonroutine*100:4.0f}%")
    print(f"Freed / redeployable capacity at 70% adoption: "
          f"{(cur.sum()-fut.sum())*100:.0f}% (redeploy, not a fee cut).")


def print_grouping(cat):
    """Iteration 3: the grouping is derived, not imposed. Report all three
    constructions, then the recommended grain and its blocks."""
    print("\n" + "=" * 96)
    print("GROUPING  -  derived from the grid by RNM (Eber 5.3.4), not imposed")
    print("=" * 96)
    val = rnm._validate()
    print("RNM check on Eber 5.4.1 toy nets (expect 1, 2, 2): "
          + ", ".join(f"{k.split()[0]}={v}" for k, v in val.items()))
    bl = rnm.bernstein_labels()
    print("\nConstruction        segments(data)   agreement with Bernstein's 5")
    for name in ("cooccurrence", "class", "blend"):
        A = rnm.ADJACENCIES[name]()
        kg, _ = rnm.segment_count(A)
        lab, _ = rnm.grouping(A)
        print(f"  {name:16s}  {kg:^14d}   Rand index {rnm.rand_index(lab, bl):.2f}")
    print("\nVerdict: by WHEN work happens the practice does not separate (1 block):")
    print("  the always-on management, coordination and client work binds the")
    print("  lifecycle, so AI gains cannot be siloed in one phase. By HOW")
    print("  automatable the work is, the data supports THREE blocks, not five.")

    labels, k = rnm.grouping(rnm.ADJACENCIES["class"]())
    prof = rnm.cluster_profile(labels)
    order = sorted(prof, key=lambda c: -prof[c]["mean_auto"])
    role = ["Automate", "Augment", "Protect"]
    eff = {r["task"]: r["effort"] for r in cat}
    cur, fut = task_future(cat, 0.7)
    fut_by = {r["task"]: f for r, f in zip(cat, fut)}
    print("\n" + "-" * 96)
    print("Recommended grain for the opportunity map: three blocks (class-affinity)")
    for i, c in enumerate(order):
        members = prof[c]["members"]
        e = sum(eff[m] for m in members)
        freed = sum(eff[m] - fut_by[m] for m in members)
        nm = role[i] if i < len(role) else f"block {c}"
        print(f"\n[{nm} block]  mean automatability {prof[c]['mean_auto']:.2f}  "
              f"| {e*100:.0f}% of effort  | frees {freed*100:.0f}% at 70% adoption")
        for m in members:
            print(f"    {m}")
    total_freed = (cur.sum() - fut.sum()) * 100
    print("\n" + "-" * 96)
    print(f"Total freed at 70% adoption: {total_freed:.0f}% of effort, concentrated")
    print("in the Automate block. (Practice is inseparable, so the freed time")
    print("lands across the system rather than in one stage.)")


def print_sensitivity(roles):
    print("\n" + "=" * 96)
    print("SENSITIVITY  -  systemic roles from the stage flow (Eber 4.2, higher order)")
    print("=" * 96)
    asmid, psmid = roles["AS"].mean(), roles["PS"].mean()
    print(f"converged at grade m = {roles['m']}  "
          "(small drift from first order: the stage flow is near-acyclic)")
    print(f"\n{'stage':30s} {'drives':>7} {'driven':>7} {'recursive':>10}  role")
    for i, s in enumerate(B.STAGES):
        lab = S.role_label(roles["AS"][i], roles["PS"][i], asmid, psmid)
        print(f"{s:30s} {roles['AS'][i]:7.2f} {roles['PS'][i]:7.2f} "
              f"{roles['rec'][i]:10.2f}  {lab}")
    print("\nRecursiveness flags the rework-entangled stages: those are the ones")
    print("to stabilise before automating around them.")


def print_activities():
    print("\n" + "=" * 96)
    print("WORK ACTIVITIES (v4)  -  our categories, mapped to the Bernstein ground truth")
    print("=" * 96)
    base = A.activity_table(adjusted=False)
    adj = {r["activity"]: r for r in A.activity_table(adjusted=True)}
    sens = A.activity_sensitivity()
    asm, psm = sens["AS"].mean(), sens["PS"].mean()
    print(f"{'activity':24s} {'eff%':>5} {'auto':>5} {'+prop':>6} {'crit':>5} {'role':>10}  tasks")
    for i, r in enumerate(base):
        a = r["activity"]
        role = S.role_label(sens["AS"][i], sens["PS"][i], asm, psm)
        print(f"{a:24s} {r['effort']*100:5.0f} {r['auto']:5.2f} "
              f"{adj[a]['auto']:6.2f} {sens['crit'][i]:5.2f} {role:>10}  {len(r['tasks'])}")
    print("\nProposed-AI lift (Bernstein 1.5.4 strength over the class baseline):")
    for i, r in enumerate(base):
        d = adj[r["activity"]]["auto"] - r["auto"]
        if d > 0.005:
            print(f"   {r['auto']:.2f} -> {adj[r['activity']]['auto']:.2f}  {r['activity']}")
    print("\nReading: Technical Design is the critical hub and a big effort sink,")
    print("highly automatable, but risky to change because the rework loops run")
    print("through it. Briefing & Concept and Client & Approvals are the active")
    print("levers. Generative tooling lifts Briefing & Concept the most.")


def print_proposals(cat):
    print("\n" + "=" * 96)
    print("PROPOSED AI per task (Bernstein 1.5.4), with the automatability lift it gives")
    print("=" * 96)
    print(f"{'task':42s} {'class':>5} {'+AI':>5}  proposed AI")
    for r in cat:
        if r["proposal"]:
            ai = r["proposal"]["ai"]
            ai = ai if len(ai) <= 60 else ai[:57] + "..."
            print(f"{r['task']:42s} {r['auto']:5.2f} {r['auto_adj']:5.2f}  {ai}")


def print_trajectory(cat):
    import bernstein as B
    print("\n" + "=" * 96)
    print("TRAJECTORY 2022 -> 2026  -  the climb up the computation ladder")
    print("=" * 96)
    print(f"{'task':42s} {'2022':>6} {'2026':>6}  {'label':12s} 2026 computation")
    climbs = []
    for _g, t in B.TASK_ORDER:
        a, b = TL.level_2022(t), TL.level_2026(t)
        climbs.append(b - a)
        c22 = TL.LADDER_2026[t]["comp22"] or "none"
        print(f"{t:42s} {c22[:6]:>6} {TL.LADDER_2026[t]['comp26'][:6]:>6}  "
              f"{TL.label_of(t):12s} {TL.LADDER_2026[t]['comp26']}")
    import numpy as _np
    print(f"\nMean climb across tasks: +{_np.mean(climbs):.1f} ladder levels.")
    print("Most movement is into Cognitive and agentic-RAG, which run on the")
    print("firm's own structured data: climbing the ladder needs the data in order.")


def print_cost():
    NL = chr(10)
    print(NL + "=" * 96)
    print("COST IMPACT  -  cost base MEASURED from timesheets x band rate; released capacity is a projection")
    print("=" * 96)
    print(f"{'stage':26s} {'hours':>8} {'GBP cost':>11} {'releas%':>8} {'GBP released':>12}")
    for r in C.by_stage():
        print(f"{r['stage']:26s} {r['hours']:8,.0f} {r['cost']:11,.0f} "
              f"{r['saved_frac']*100:7.0f}% {r['saved_cost']:12,.0f}")
    print(NL + "Who gets freed (expected adoption):")
    for b, d in C.by_band().items():
        print(f"  {b:10s} {d['saved_hours']:7,.0f} h   GBP {d['saved_cost']:9,.0f}")
    t = C.totals()
    print(NL + "Capacity released per year, by adoption scenario:")
    for k in ("low", "expected", "high"):
        print(f"  {k:9s} {C.ADOPTION[k]:.0%}:  {t[k]['saved_hours']:7,.0f} h   "
              f"GBP {t[k]['saved_cost']:,.0f}  ({t[k]['saved_cost']/t[k]['cost']*100:.0f}% of base)")
    cv = C.conversion()
    print(NL + "Capacity released does not book itself. Two conversion routes:")
    print(f"  Margin route (cost avoided, needs fewer hours):  GBP {cv['margin_value']:,.0f}/yr")
    print(f"  Growth route (extra fee, needs more work won):   GBP {cv['growth_value']:,.0f}/yr")
    print("  Doing neither reabsorbs the time and books nothing.")
    print(NL + "Cost base is real once the dummy TIMESHEET and RATE_BY_BAND in cost.py")
    print("are replaced with the firm's hours-by-band-by-stage and salary-cost rates.")
    print("Released capacity is salaried cost of freed hours, booked only if hours")
    print("fall or the time is redeployed into fee.")


def main():
    import sys
    if len(sys.argv) > 1:
        C.set_inputs(_inp.load_inputs(sys.argv[1]))
        print(f"using client inputs: {C.INPUTS.source}")
        for w in C.INPUTS.warnings:
            print(f"  warning: {w}")
    theme.apply_theme()
    cat = task_catalogue()
    print_report(cat)
    print_grouping(cat)
    labels, k = rnm.grouping(rnm.ADJACENCIES["class"]())
    roles = S.stage_roles()
    task_crit = S.task_criticality(roles["crit"])
    print_sensitivity(roles)
    print_activities()
    print_proposals(cat)
    print_trajectory(cat)
    print_cost()
    paths = [
        views.fig_stage_effort(),
        views.fig_macleamy(),
        views.fig_convergence(),
        views.fig_task_automatability(cat),
        views.fig_intervention_map(cat, task_crit, labels),
        views.fig_states(cat),
        views.fig_task_stage_grid(),
        views.fig_automatability_by_stage(),
        views.fig_activity_flow(),
        views.fig_influence_graph(),
        views.fig_activity_intervention(),
        views.fig_activity_opportunity(),
        views.fig_activity_sensitivity(),
        views.fig_computation_climb(),
        views.fig_readiness_map(),
        views.fig_type_shift(),
        views.fig_cost_saved(),
        views.fig_savings_bands(),
        views.fig_released_by_band(),
        views.fig_capacity_conversion(),
        views.fig_roadmap(),
        views.fig_rnm_separation("class"),
        views.fig_segments_supported(),
        views.fig_opportunity_map(cat, labels, k),
    ]
    print("\nFigures:")
    for p in paths:
        print(" ", p)


if __name__ == "__main__":
    main()
