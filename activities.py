"""
activities.py - the work-activity layer (Datum v4).

Lesson from v1 to v3: RIBA stages are a contractual sequence, not how work
actually moves, so flow and influence over the stages came out near-acyclic and
the systemic analysis had little to bite on. The fix is to model the work the
practice actually performs as a set of activities, with real task-to-task flow
and rework loops, the way the impressive v1 graph did.

These activities are OUR categories, chosen to make sense for the engagement,
but each one maps onto a set of Bernstein tasks (the ground truth), so
automatability stays anchored to the published classification rather than
invented. The mapping is a clean partition: every task belongs to exactly one
activity, so effort is conserved.

Honesty of inputs:
  measured-in-principle   activity effort (summed from task effort, itself from
                          timesheets; dummy now)
  classified judgement    activity automatability (from Bernstein class per task)
  elicited (workshop)     ACTIVITY_FLOW and ACTIVITY_INFLUENCE, authored here as
                          realistic dummies, the numbers a client workshop fills
  elicited (tooling)      TOOLING_SHIFT, where 2026 tools have moved past the
                          2022 book class
"""
import numpy as np
import bernstein as B
import model as M
import sensitivity as S

# ---- the activities, in rough work order -----------------------------------
ACT_ORDER = [
    "Briefing & Concept",
    "Technical Design",
    "Spatial Coordination",
    "Consultant Coordination",
    "Cost & Programme",
    "Reviews & Conformance",
    "Client & Approvals",
    "Regulatory & Public",
    "Construction Oversight",
    "Practice Management",
]

# ---- mapping to the Bernstein ground truth (a partition of all 25 tasks) ----
ACTIVITY_TASKS = {
    "Briefing & Concept": [
        "Analysing and understanding the brief",
        "Generating alternatives",
        "Evaluating and selecting alternatives"],
    "Technical Design": [
        "Performing engineering analysis",
        "Producing technical documentation",
        "Documenting design decisions",
        "Evaluating / integrating technical considerations"],
    "Spatial Coordination": [
        "Coordinating spatial and technical systems"],
    "Consultant Coordination": [
        "Coordinating consultants and others"],
    "Cost & Programme": [
        "Evaluating and managing project costs",
        "Maintaining budgets and schedules"],
    "Reviews & Conformance": [
        "Reviewing and approving technical documents",
        "Determining conformance to the brief",
        "Resolving conflicting requirements"],
    "Client & Approvals": [
        "Meeting / managing clients and decisions"],
    "Regulatory & Public": [
        "Coordinating with regulators",
        "Interfacing with public / communities"],
    "Construction Oversight": [
        "Reviewing construction progress"],
    "Practice Management": [
        "Obtaining work",
        "Getting / assigning / managing staffing",
        "Monitoring practice financial health",
        "Setting business strategy",
        "Managing practice operations",
        "Managing project staffing resources",
        "Assigning and coordinating work"],
}
NA = len(ACT_ORDER)
_IX = {a: i for i, a in enumerate(ACT_ORDER)}

# safety: the mapping must be a clean partition of the 25 tasks
_mapped = [t for ts in ACTIVITY_TASKS.values() for t in ts]
assert set(_mapped) == set(B.TASK_STAGE), "activity map is not a partition of tasks"
assert len(_mapped) == len(set(_mapped)) == len(B.TASK_STAGE), "duplicate/missing task"


# Automatability now carries a second signal: the strength of Bernstein's
# proposed AI for the task (model.composite_auto), which lifts the cognitive
# class where a real AI intervention exists. This replaces the earlier hand-coded
# tooling deltas with something grounded in Bernstein's own proposal column.
def task_auto(task, adjusted=False):
    return M.composite_auto(task) if adjusted else M.task_mean_auto(task)


# ---- activity attributes inherited from its tasks --------------------------
def activity_table(adjusted=False):
    cat = {r["task"]: r for r in M.task_catalogue()}
    pi, _ = M.steady_state(activity_flow())     # effort = where work accumulates
    rows = []
    for i, a in enumerate(ACT_ORDER):
        tasks = ACTIVITY_TASKS[a]
        auto = np.mean([task_auto(t, adjusted) for t in tasks])
        base = np.mean([task_auto(t, False) for t in tasks])
        proposals = [cat[t]["proposal"] for t in tasks if cat[t]["proposal"]]
        rows.append(dict(
            activity=a, tasks=tasks, effort=float(pi[i]),
            auto=float(auto), auto_base=float(base),
            n_proposals=len(proposals), proposals=proposals))
    return rows


# ---- elicited flow: work sequence + real rework loops ----------------------
# (from, to, propensity). Back-edges to Technical Design / Briefing are the
# rework a linear stage model cannot show.
_FLOW_EDGES = [
    ("Briefing & Concept", "Technical Design", 0.55),
    ("Briefing & Concept", "Cost & Programme", 0.20),
    ("Briefing & Concept", "Client & Approvals", 0.25),
    ("Technical Design", "Spatial Coordination", 0.35),
    ("Technical Design", "Consultant Coordination", 0.20),
    ("Technical Design", "Reviews & Conformance", 0.30),
    ("Technical Design", "Cost & Programme", 0.15),
    ("Spatial Coordination", "Technical Design", 0.45),   # coordination rework
    ("Spatial Coordination", "Consultant Coordination", 0.30),
    ("Spatial Coordination", "Reviews & Conformance", 0.25),
    ("Consultant Coordination", "Technical Design", 0.45),
    ("Consultant Coordination", "Spatial Coordination", 0.30),
    ("Consultant Coordination", "Reviews & Conformance", 0.25),
    ("Cost & Programme", "Technical Design", 0.40),       # value-engineering rework
    ("Cost & Programme", "Client & Approvals", 0.35),
    ("Cost & Programme", "Reviews & Conformance", 0.25),
    ("Reviews & Conformance", "Technical Design", 0.55),  # the main rework loop
    ("Reviews & Conformance", "Briefing & Concept", 0.20),
    ("Reviews & Conformance", "Client & Approvals", 0.25),
    ("Client & Approvals", "Briefing & Concept", 0.30),   # client-driven change
    ("Client & Approvals", "Technical Design", 0.25),
    ("Client & Approvals", "Regulatory & Public", 0.20),
    ("Client & Approvals", "Construction Oversight", 0.25),
    ("Regulatory & Public", "Technical Design", 0.45),    # compliance rework
    ("Regulatory & Public", "Reviews & Conformance", 0.30),
    ("Regulatory & Public", "Client & Approvals", 0.25),
    ("Construction Oversight", "Technical Design", 0.45),  # RFIs back to design
    ("Construction Oversight", "Consultant Coordination", 0.30),
    ("Construction Oversight", "Cost & Programme", 0.25),
    ("Practice Management", "Briefing & Concept", 0.25),
    ("Practice Management", "Technical Design", 0.25),
    ("Practice Management", "Cost & Programme", 0.25),
    ("Practice Management", "Client & Approvals", 0.25),
]


def activity_flow():
    """Row-stochastic transition with self-retention, from the edge list."""
    T = np.zeros((NA, NA))
    for f, t, w in _FLOW_EDGES:
        T[_IX[f], _IX[t]] += w
    for i in range(NA):
        T[i, i] += 0.45                 # work continues within the activity
        # every activity reports back to Practice Management (light coupling)
        if ACT_ORDER[i] != "Practice Management":
            T[i, _IX["Practice Management"]] += 0.10
    return T / T.sum(axis=1, keepdims=True)


# ---- elicited influence (Vester 0..3): who forces change in whom ------------
_INFLUENCE_EDGES = [
    ("Briefing & Concept", "Technical Design", 3), ("Briefing & Concept", "Cost & Programme", 2),
    ("Briefing & Concept", "Client & Approvals", 2), ("Briefing & Concept", "Reviews & Conformance", 1),
    ("Technical Design", "Spatial Coordination", 3), ("Technical Design", "Consultant Coordination", 2),
    ("Technical Design", "Reviews & Conformance", 3), ("Technical Design", "Cost & Programme", 2),
    ("Technical Design", "Construction Oversight", 2),
    ("Spatial Coordination", "Technical Design", 2), ("Spatial Coordination", "Consultant Coordination", 2),
    ("Spatial Coordination", "Construction Oversight", 2),
    ("Consultant Coordination", "Technical Design", 2), ("Consultant Coordination", "Spatial Coordination", 2),
    ("Cost & Programme", "Technical Design", 2), ("Cost & Programme", "Client & Approvals", 2),
    ("Cost & Programme", "Reviews & Conformance", 1),
    ("Reviews & Conformance", "Technical Design", 3), ("Reviews & Conformance", "Briefing & Concept", 1),
    ("Client & Approvals", "Briefing & Concept", 3), ("Client & Approvals", "Technical Design", 2),
    ("Client & Approvals", "Cost & Programme", 2), ("Client & Approvals", "Regulatory & Public", 1),
    ("Regulatory & Public", "Technical Design", 2), ("Regulatory & Public", "Client & Approvals", 1),
    ("Construction Oversight", "Cost & Programme", 1), ("Construction Oversight", "Consultant Coordination", 1),
    ("Practice Management", "Briefing & Concept", 2), ("Practice Management", "Technical Design", 1),
    ("Practice Management", "Cost & Programme", 2), ("Practice Management", "Client & Approvals", 1),
    ("Practice Management", "Construction Oversight", 1),
]


def activity_influence():
    W = np.zeros((NA, NA))
    for f, t, w in _INFLUENCE_EDGES:
        W[_IX[f], _IX[t]] = w
    return W


def activity_sensitivity():
    """Higher-order Vester roles on the activity influence graph. Scaled so the
    cumulation converges, then read at the converged grade."""
    W = activity_influence() ** 2                  # Eber variance weighting
    sr = max(np.abs(np.linalg.eigvals(W)).max(), 1e-9)
    W = W / (sr * 1.2)                             # keep spectral radius < 1
    m = S.converged_grade(W)
    AS, PS, rec = S.roles(W, m)
    AS, PS = S._maxnorm(AS, PS)
    rec = rec / (rec.max() or 1.0)
    return dict(m=m, AS=AS, PS=PS, rec=rec, crit=AS * PS)


if __name__ == "__main__":
    print("ACTIVITY LAYER (v4)\n")
    base = activity_table(adjusted=False)
    adj = {r["activity"]: r for r in activity_table(adjusted=True)}
    sens = activity_sensitivity()
    asm, psm = sens["AS"].mean(), sens["PS"].mean()
    print(f"{'activity':24s} {'eff%':>5} {'auto':>5} {'+prop':>6} {'crit':>5} {'AIprop':>7}  role")
    for i, r in enumerate(base):
        a = r["activity"]
        role = S.role_label(sens["AS"][i], sens["PS"][i], asm, psm)
        print(f"{a:24s} {r['effort']*100:5.0f} {r['auto']:5.2f} "
              f"{adj[a]['auto']:6.2f} {sens['crit'][i]:5.2f} {r['n_proposals']:7d}  {role}")
    print(f"\nsensitivity converged at grade m = {sens['m']}")
