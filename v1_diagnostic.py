"""
diagnostic.py
A single quantitative workflow diagnostic for an AEC practice.

One workflow is defined once (its steps, an influence matrix, and a transition
matrix) and three coherent views come out of it:

  1. FLOW          a value-stream-style map of the steps, annotated with the
                   measured share of effort each one absorbs, with the rework
                   loops drawn in (the bit a plain VSM hides).
  2. TIME          the steady-state share of effort per step, solved by power
                   iteration and cross-checked against the dominant eigenvector.
                   Maps to your Task 4 (tunnel boring machine).
  3. SENSITIVITY   each step's Active Sum and Passive Sum on the active/reactive/
                   critical/buffering plane, to find the leverage points.
                   Maps to your Task 3 (stakeholder analysis) and the coupling-
                   cost intuition from Task 10.

Honesty of inputs: the TRANSITION matrix can come from real logged time data
(e.g. Rapport3 extracts), in which case the time view is measured. The
INFLUENCE matrix usually comes from a structured workshop, so the sensitivity
view is elicited expert judgement made rankable, not measurement. State which
is which whenever you present it. The sensitivity method is Vester's
Sensitivitaetsmodell, an established systems-consulting technique.
"""

from dataclasses import dataclass
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Patch
import bernstein as B
import model as _M


@dataclass
class Workflow:
    steps: list          # names of the workflow steps
    influence: np.ndarray  # influence[i, j] = how strongly i drives j (0..3)
    transition: np.ndarray  # transition[i, j] = P(next step = j | current = i)
    # Bernstein layer (each attribute drives a recommendation, not decoration):
    routine: np.ndarray   # 0..1, how ROUTINE the step is (1 = fully routine).
                          #   Bernstein's routine vs non-routine distinction.
    phase: np.ndarray     # 0..1, position on the project timeline (0 early, 1 late).
                          #   Used for the MacLeamy front-loading check (ch 3.3).

    def __post_init__(self):
        n = len(self.steps)
        assert self.influence.shape == (n, n)
        assert self.transition.shape == (n, n)
        assert np.allclose(self.transition.sum(axis=1), 1.0), \
            "transition rows must each sum to 1"
        assert self.routine.shape == (n,) and self.phase.shape == (n,)
        assert np.all((0 <= self.routine) & (self.routine <= 1))
        assert np.all((0 <= self.phase) & (self.phase <= 1))


# ----------------------------------------------------------------------
# View 2: TIME  (Markov steady state, your Task 4)
# ----------------------------------------------------------------------
def time_allocation(wf):
    n = len(wf.steps)
    pi = np.full(n, 1.0 / n)
    for _ in range(2000):
        nxt = pi @ wf.transition
        if np.max(np.abs(nxt - pi)) < 1e-14:
            break
        pi = nxt
    pi_power = pi / pi.sum()

    vals, vecs = np.linalg.eig(wf.transition.T)
    idx = np.argmin(np.abs(vals - 1.0))
    pi_eig = np.real(vecs[:, idx])
    pi_eig = pi_eig / pi_eig.sum()
    return pi_power, pi_eig


# ----------------------------------------------------------------------
# View 3: SENSITIVITY  (Vester, your Task 3 + Task 10)
# ----------------------------------------------------------------------
def sensitivity(wf):
    active_sum = wf.influence.sum(axis=1)   # how much each step DRIVES
    passive_sum = wf.influence.sum(axis=0)  # how much each step IS DRIVEN
    criticality = active_sum * passive_sum  # Vester's P = AS * PS
    return active_sum, passive_sum, criticality


def classify(active_sum, passive_sum):
    as_mid, ps_mid = active_sum.mean(), passive_sum.mean()
    labels = []
    for a, p in zip(active_sum, passive_sum):
        if a >= as_mid and p < ps_mid:
            labels.append("active (lever)")
        elif a >= as_mid and p >= ps_mid:
            labels.append("critical")
        elif a < as_mid and p >= ps_mid:
            labels.append("reactive")
        else:
            labels.append("buffering")
    return labels


# ----------------------------------------------------------------------
# Bernstein layer: routine/non-routine + automated/autonomous placement
# ----------------------------------------------------------------------
def recommend(wf, AS, PS):
    """Per-step intervention, combining Bernstein's two axes.

    Routineness decides automate vs augment (his routine/non-routine split).
    Systemic criticality (high Active AND high Passive) decides how much human
    oversight is needed (his caution against autonomous tools in entangled,
    high-stakes work).
    """
    as_mid, ps_mid = AS.mean(), PS.mean()
    recs = []
    for i in range(len(wf.steps)):
        critical = (AS[i] >= as_mid) and (PS[i] >= ps_mid)
        routine = wf.routine[i] >= 0.5
        if routine and not critical:
            recs.append("Automate")
        elif routine and critical:
            recs.append("Automate w/ oversight")
        elif (not routine) and critical:
            recs.append("Augment (human in loop)")
        else:
            recs.append("Assist / low priority")
    return recs


def automation_priority(wf, pi):
    """Where the routine effort is concentrated = best automation ROI.
    Operationalises Bernstein's 'automate the routine, high-volume tasks'."""
    score = pi * wf.routine
    return score / score.sum()


def macleamy_check(wf, pi):
    """Effort-weighted mean phase. Higher = effort sits later than ideal,
    which is the MacLeamy violation (ch 3.3): late effort is expensive."""
    weighted_phase = float(np.sum(pi * wf.phase))
    late_share = float(np.sum(pi[wf.phase >= 0.55]))
    return weighted_phase, late_share


# ----------------------------------------------------------------------
# Combined text report
# ----------------------------------------------------------------------
def report(wf):
    pi, pi_eig = time_allocation(wf)
    AS, PS, P = sensitivity(wf)
    labels = classify(AS, PS)
    recs = recommend(wf, AS, PS)

    print("=" * 78)
    print("WORKFLOW DIAGNOSTIC")
    print("=" * 78)
    header = (f"{'Step':20s} {'Effort%':>8s} {'Routine':>8s} "
              f"{'Role':>16s} {'Action':>22s}")
    print(header)
    print("-" * 78)
    order = np.argsort(-pi)
    for i in order:
        print(f"{wf.steps[i]:20s} {pi[i]*100:7.1f}% {wf.routine[i]:8.2f} "
              f"{labels[i]:>16s} {recs[i]:>22s}")

    print("-" * 78)
    print(f"Eigenvector cross-check, max abs diff: "
          f"{np.max(np.abs(pi - pi_eig)):.2e}")

    # Automation priority: where the routine effort is concentrated,
    # restricted to steps actually recommended for automation so it never
    # contradicts the Action column.
    prio = automation_priority(wf, pi)
    auto_mask = np.array([r.startswith("Automate") for r in recs])
    prio = prio * auto_mask
    if prio.sum() > 0:
        prio = prio / prio.sum()
        print("\nAutomation priority (automatable steps, effort x routineness):")
        for i in np.argsort(-prio):
            if prio[i] > 0:
                print(f"  {wf.steps[i]:20s} {prio[i]*100:5.1f}% "
                      f"of the automatable load")

    # MacLeamy front-loading check
    wphase, late = macleamy_check(wf, pi)
    print(f"\nMacLeamy check: effort-weighted phase = {wphase:.2f} "
          f"(0 early, 1 late); {late*100:.0f}% of effort sits in late phases.")

    # plain-language headline lines a partner can read
    waste = [i for i, s in enumerate(wf.steps)
             if s.lower() in ("rework", "admin/overhead")]
    waste_pct = sum(pi[i] for i in waste) * 100
    automatable = sum(pi[i] for i in range(len(wf.steps))
                      if recs[i].startswith("Automate"))
    crit = [wf.steps[i] for i in range(len(wf.steps)) if labels[i] == "critical"]
    print("\nPlain-language summary:")
    print(f"  About {waste_pct:.0f}% of effort goes to rework and overhead "
          f"before design value is added.")
    print(f"  Roughly {automatable*100:.0f}% of effort sits in steps that are "
          f"safe to automate, which is")
    print(f"  redeployable capacity for non-routine work, NOT a fee cut "
          f"(avoids Bernstein's productivity trap).")
    if crit:
        print(f"  Protect the human role in: {', '.join(crit)} "
              f"(critical and non-routine).")


# ----------------------------------------------------------------------
# Combined three-panel figure
# ----------------------------------------------------------------------
def figure(wf, path="diagnostic.png"):
    pi, _ = time_allocation(wf)
    AS, PS, P = sensitivity(wf)
    n = len(wf.steps)

    fig = plt.figure(figsize=(15, 5))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.2, 1, 1], wspace=0.3)

    # --- Panel 1: FLOW with rework loops drawn in (vertical stack) ---
    ax1 = fig.add_subplot(gs[0])
    ax1.set_title("1. Flow (effort share + rework loops)")
    ys = np.arange(n)[::-1]   # first step at the top
    box_w, box_h = 2.2, 0.5
    for i in range(n):
        ax1.add_patch(Rectangle((-box_w/2, ys[i] - box_h/2), box_w, box_h,
                                facecolor="#bee3f8", edgecolor="#2b6cb0"))
        ax1.text(0, ys[i], f"{wf.steps[i]}  ({pi[i]*100:.0f}%)",
                 ha="center", va="center", fontsize=8)
    # forward arrows down the main line
    for i in range(n - 1):
        ax1.add_patch(FancyArrowPatch((0, ys[i] - box_h/2),
                      (0, ys[i+1] + box_h/2),
                      arrowstyle="-|>", mutation_scale=11, color="grey"))
    # big loop-back transitions (the waste a linear VSM cannot show)
    for i in range(n):
        for j in range(n):
            if j < i and wf.transition[i, j] > 0.25:
                ax1.add_patch(FancyArrowPatch(
                    (box_w/2, ys[i]), (box_w/2, ys[j]),
                    connectionstyle="arc3,rad=-0.45",
                    arrowstyle="-|>", mutation_scale=10,
                    color="#c53030", alpha=0.65))
    ax1.text(box_w/2 + 0.15, n - 1, "rework\nloops", color="#c53030",
             fontsize=8, va="top", ha="left", alpha=0.8)
    ax1.set_xlim(-box_w/2 - 0.5, box_w/2 + 1.2)
    ax1.set_ylim(-1, n)
    ax1.axis("off")

    # --- Panel 2: TIME bar -------------------------------------------
    ax2 = fig.add_subplot(gs[1])
    ax2.set_title("2. Effort share (Markov steady state)")
    order = np.argsort(pi)
    ax2.barh([wf.steps[i] for i in order], [pi[i]*100 for i in order],
             color="#2b6cb0")
    ax2.set_xlabel("% of long-run effort")
    ax2.tick_params(axis="y", labelsize=8)

    # --- Panel 3: SENSITIVITY plane ----------------------------------
    ax3 = fig.add_subplot(gs[2])
    ax3.set_title("3. Sensitivity (Vester plane)")
    ax3.scatter(PS, AS, s=60, color="#2b6cb0", zorder=3)
    for i in range(n):
        ax3.annotate(wf.steps[i], (PS[i], AS[i]),
                     xytext=(4, 3), textcoords="offset points", fontsize=7)
    ax3.axvline(PS.mean(), color="grey", lw=0.8, ls="--")
    ax3.axhline(AS.mean(), color="grey", lw=0.8, ls="--")
    ax3.set_xlabel("Passive Sum (driven)")
    ax3.set_ylabel("Active Sum (drives)")

    fig.savefig(path, dpi=130, bbox_inches="tight")
    print(f"\nSaved combined figure to {path}")


# ----------------------------------------------------------------------
# Default synthetic AEC practice workflow
# ----------------------------------------------------------------------
def default_workflow():
    steps = [
        "Concept Design",
        "Technical Design",
        "Internal Review",
        "Consultant Coord",
        "Client Review",
        "Rework",
        "Documentation",
        "Admin/Overhead",
    ]
    # influence[i, j]: how strongly step i drives step j (0..3)
    influence = np.array([
        [0, 3, 1, 1, 2, 1, 1, 1],  # Concept Design
        [1, 0, 2, 3, 1, 2, 3, 1],  # Technical Design
        [1, 2, 0, 1, 2, 2, 0, 1],  # Internal Review
        [0, 2, 1, 0, 1, 2, 2, 1],  # Consultant Coord
        [0, 1, 1, 0, 0, 3, 2, 1],  # Client Review
        [0, 3, 1, 1, 0, 0, 1, 1],  # Rework
        [0, 1, 0, 1, 0, 0, 0, 2],  # Documentation
        [0, 0, 0, 0, 0, 0, 0, 0],  # Admin/Overhead
    ], dtype=float)
    # transition[i, j]: P(next = j | current = i), rows sum to 1
    transition = np.array([
        [0.00,0.40,0.20,0.10,0.10,0.05,0.00,0.15],  # Concept Design
        [0.05,0.00,0.25,0.25,0.05,0.15,0.15,0.10],  # Technical Design
        [0.15,0.25,0.00,0.10,0.25,0.20,0.00,0.05],  # Internal Review
        [0.05,0.30,0.10,0.00,0.10,0.20,0.15,0.10],  # Consultant Coord
        [0.05,0.10,0.05,0.05,0.00,0.45,0.20,0.10],  # Client Review
        [0.10,0.40,0.15,0.10,0.05,0.00,0.15,0.05],  # Rework
        [0.00,0.10,0.05,0.05,0.05,0.10,0.00,0.65],  # Documentation
        [0.15,0.40,0.10,0.05,0.05,0.05,0.20,0.00],  # Admin/Overhead
    ], dtype=float)
    # routine[i]: how routine the step is, 0 (pure judgement) .. 1 (pure routine)
    routine = np.array([0.10, 0.40, 0.30, 0.50, 0.20, 0.40, 0.80, 0.90])
    # phase[i]: position on the project timeline, 0 (early) .. 1 (late)
    phase = np.array([0.10, 0.40, 0.45, 0.50, 0.55, 0.60, 0.80, 0.50])
    return Workflow(steps, influence, transition, routine, phase)


def convergence_figure(wf, path="convergence.png", n_iter=60):
    """Method-check view: the Markov chain settling onto its steady state.

    Mirrors the 'Convergence to Stationary Distribution' plot in your Task 4
    (tunnel boring machine). This is a rigour/appendix artefact, not a
    partner-facing finding.
    """
    n = len(wf.steps)
    pi = np.full(n, 1.0 / n)
    history = [pi.copy()]
    for _ in range(n_iter):
        pi = pi @ wf.transition
        history.append(pi.copy())
    history = np.array(history)

    fig, ax = plt.subplots(figsize=(8, 5))
    for j in range(n):
        ax.plot(history[:, j], lw=1.6, label=wf.steps[j])
    ax.set_xlabel("iteration")
    ax.set_ylabel("share of effort")
    ax.set_title("Convergence to steady state (method check)")
    ax.legend(fontsize=7, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"Saved convergence check to {path}")


def bernstein_figure(wf, path="bernstein_views.png"):
    """Two Bernstein-native views:
    (1) intervention map: routineness x systemic criticality, sized by effort,
        with the four actions (automate / augment / oversight / low priority).
    (2) MacLeamy check: effort by phase against a front-loaded ideal.
    """
    pi, _ = time_allocation(wf)
    AS, PS, P = sensitivity(wf)
    crit = AS * PS
    n = len(wf.steps)

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5.5))

    # --- Panel A: intervention map -----------------------------------
    axA.set_title("Intervention map (Bernstein)")
    sizes = 200 + 1800 * pi
    axA.scatter(wf.routine, crit, s=sizes, color="#2b6cb0", alpha=0.7, zorder=3)
    for i in range(n):
        axA.annotate(wf.steps[i], (wf.routine[i], crit[i]),
                     xytext=(6, 4), textcoords="offset points", fontsize=8)
    axA.axvline(0.5, color="grey", lw=0.8, ls="--")
    axA.axhline(crit.mean(), color="grey", lw=0.8, ls="--")
    axA.text(0.02, 0.98, "AUGMENT\n(human in loop)", transform=axA.transAxes,
             va="top", ha="left", color="#c53030", fontsize=10, alpha=0.8)
    axA.text(0.98, 0.98, "AUTOMATE\nw/ oversight", transform=axA.transAxes,
             va="top", ha="right", color="#b7791f", fontsize=10, alpha=0.8)
    axA.text(0.02, 0.02, "ASSIST\n(low priority)", transform=axA.transAxes,
             va="bottom", ha="left", color="grey", fontsize=10, alpha=0.8)
    axA.text(0.98, 0.02, "AUTOMATE", transform=axA.transAxes,
             va="bottom", ha="right", color="#2f855a", fontsize=10, alpha=0.8)
    axA.set_xlabel("Routineness  (0 judgement  ->  1 routine)")
    axA.set_ylabel("Systemic criticality (AS x PS)")
    axA.set_xlim(-0.05, 1.05)

    # --- Panel B: MacLeamy check -------------------------------------
    axB.set_title("MacLeamy check (effort vs phase)")
    axB.scatter(wf.phase, pi * 100, s=70, color="#2b6cb0", zorder=3)
    for i in range(n):
        axB.annotate(wf.steps[i], (wf.phase[i], pi[i] * 100),
                     xytext=(5, 3), textcoords="offset points", fontsize=8)
    # front-loaded ideal: more effort early, declining later
    xs = np.linspace(0, 1, 50)
    ideal = (1 - xs)
    ideal = ideal / ideal.sum() * (pi.sum() * 100) * (50 / n)
    axB.plot(xs, ideal, color="#2f855a", lw=1.5, ls="--",
             label="front-loaded ideal")
    wphase, _ = macleamy_check(wf, pi)
    axB.axvline(wphase, color="#c53030", lw=1.2,
                label=f"effort-weighted phase = {wphase:.2f}")
    axB.set_xlabel("Phase  (0 early  ->  1 late)")
    axB.set_ylabel("% of effort")
    axB.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"Saved Bernstein views to {path}")


# ----------------------------------------------------------------------
# Current state vs future state (the VSM payoff)
# ----------------------------------------------------------------------
def future_state(wf, automate=None, reduce_rework=0.0):
    """Model an intervention and recompute the workflow.

    automate:       dict {step_name: fraction of that step's human effort the
                    machine takes over, 0..1}. Reduces human effort in routine
                    steps.
    reduce_rework:  0..1, how much the inflow into 'Rework' is cut by better
                    upstream coordination and checking (the MacLeamy / Bernstein
                    front-loading move). Changes the chain dynamics, so the
                    benefit ripples downstream, not just at the touched step.

    Returns current and future human-effort distributions plus headline deltas.
    Everything is expressed as a fraction of today's total effort baseline, so
    the future numbers summing to less than one IS the freed capacity.
    """
    automate = automate or {}
    n = len(wf.steps)
    pi_current, _ = time_allocation(wf)

    # 1. structural change: less rework inflow
    T2 = wf.transition.copy()
    if reduce_rework > 0:
        for idx, s in enumerate(wf.steps):
            if s.lower() == "rework":
                T2[:, idx] *= (1 - reduce_rework)
        T2 = T2 / T2.sum(axis=1, keepdims=True)
    wf2 = Workflow(wf.steps, wf.influence, T2, wf.routine, wf.phase)
    pi_future_proc, _ = time_allocation(wf2)

    # 2. automation: machine takes a share of human effort in named steps
    human_factor = np.array([1 - automate.get(s, 0.0) for s in wf.steps])
    human_future = pi_future_proc * human_factor   # fraction of today's baseline

    waste_idx = [i for i, s in enumerate(wf.steps)
                 if s.lower() in ("rework", "admin/overhead")]
    res = {
        "pi_current": pi_current,
        "human_future": human_future,
        "waste_cur": float(pi_current[waste_idx].sum()),
        "waste_fut": float(human_future[waste_idx].sum()),
        "freed": float(1 - human_future.sum()),
        "phase_cur": float((pi_current * wf.phase).sum()),
        "phase_fut": float(((human_future / human_future.sum()) * wf.phase).sum()),
    }
    return res


def compare_states(wf, automate=None, reduce_rework=0.0, path="states.png"):
    r = future_state(wf, automate, reduce_rework)
    print("\n" + "=" * 64)
    print("CURRENT STATE vs FUTURE STATE")
    print("=" * 64)
    print(f"  Rework + overhead:   {r['waste_cur']*100:5.1f}%  ->  "
          f"{r['waste_fut']*100:5.1f}%")
    print(f"  Effort-weighted phase:{r['phase_cur']:5.2f}  ->  "
          f"{r['phase_fut']:5.2f}   (lower = more front-loaded)")
    print(f"  Freed / redeployable capacity:        {r['freed']*100:5.1f}%")

    cur, fut = r["pi_current"] * 100, r["human_future"] * 100
    order = np.argsort(-cur)
    labels = [wf.steps[i] for i in order]
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(y + 0.2, cur[order], height=0.4, color="#a0aec0",
            label="current state")
    ax.barh(y - 0.2, fut[order], height=0.4, color="#2b6cb0",
            label="future state (human effort)")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("% of today's total effort")
    ax.set_title("Current vs future state")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"\nSaved current-vs-future figure to {path}")
    return r


# ----------------------------------------------------------------------
# Bernstein-grounded pipeline (two levels: groups carry the matrices,
# tasks carry the classification)
# ----------------------------------------------------------------------
def build_group_workflow():
    """Group-level Workflow (5 nodes) for the systemic and flow views.
    Routine and phase per group are the mean of the group's tasks, so even the
    group layer is sourced from Bernstein's task classification."""
    autos = {g: [] for g in B.GROUPS}
    stages = {g: [] for g in B.GROUPS}
    for g, _, cls, stage in B.TASKS:
        autos[g].append(B.SCALE[cls])
        stages[g].append(stage)
    routine = np.array([np.mean(autos[g]) for g in B.GROUPS])
    phase = np.array([np.mean(stages[g]) for g in B.GROUPS])
    return Workflow(B.GROUPS, B.GROUP_INFLUENCE, B.GROUP_TRANSITION,
                    routine, phase)


def task_catalogue():
    """Every Bernstein task with its class, automatability, action, phase, and
    an effort share. Effort comes from the group-level Markov steady state,
    distributed evenly within each group (the placeholder a real timesheet
    split would replace)."""
    wf = build_group_workflow()
    pi_group, _ = time_allocation(wf)
    gidx = {g: i for i, g in enumerate(B.GROUPS)}
    counts = {g: 0 for g in B.GROUPS}
    for g, _, _, _ in B.TASKS:
        counts[g] += 1
    cat = []
    for g, task, cls, stage in B.TASKS:
        cat.append(dict(group=g, task=task, cls=cls, phase=stage,
                        auto=B.SCALE[cls], action=_M._action_from_auto(B.SCALE[cls]),
                        effort=pi_group[gidx[g]] / counts[g]))
    return cat


def task_report(cat=None):
    cat = cat or task_catalogue()
    print("=" * 92)
    print("BERNSTEIN-GROUNDED TASK DIAGNOSTIC")
    print("=" * 92)
    cur_group = None
    for r in sorted(cat, key=lambda r: (B.GROUPS.index(r["group"]), -r["effort"])):
        if r["group"] != cur_group:
            print(f"\n[{r['group']}]")
            cur_group = r["group"]
        print(f"  {r['task']:50s} {r['effort']*100:5.1f}%  "
              f"{r['cls']:24s} {r['action']}")
    autom = sum(r["effort"] for r in cat
                if r["cls"] in ("procedural", "procedural-integrative"))
    protect = sum(r["effort"] for r in cat
                  if r["cls"] in ("perceptive", "integrative-perceptive"))
    print("\n" + "-" * 92)
    print(f"Automatable (procedural-leaning) effort: {autom*100:4.0f}%")
    print(f"Protected (perceptive-leaning) effort:   {protect*100:4.0f}%")
    print(f"Integrative middle ground:               {(1-autom-protect)*100:4.0f}%")


def task_future(cat=None, aggressiveness=0.7):
    """Future human effort per task = effort x (1 - automatability x adoption).
    Perceptive tasks (automatability 0) are untouched; procedural tasks shed
    most of their human effort. 'aggressiveness' is the adoption level."""
    cat = cat or task_catalogue()
    cur = np.array([r["effort"] for r in cat])
    auto = np.array([r["auto"] for r in cat])
    fut = cur * (1 - auto * aggressiveness)
    return cat, cur, fut


def task_figure(path="bernstein_tasks.png", aggressiveness=0.7):
    cat, cur, fut = task_future(aggressiveness=aggressiveness)
    order = np.argsort(cur)
    labels = [cat[i]["task"] for i in order]
    colors = [B.CLASS_COLOR[cat[i]["cls"]] for i in order]
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.barh(y, cur[order] * 100, color=colors, alpha=0.35)
    ax.barh(y, fut[order] * 100, color=colors, alpha=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("% of total effort   (faded = current, solid = human effort "
                  "after automation)")
    ax.set_title("Task automatability, Bernstein-classified "
                 f"(adoption {int(aggressiveness*100)}%)")
    handles = [Patch(color=c, label=k) for k, c in B.CLASS_COLOR.items()]
    ax.legend(handles=handles, fontsize=8, loc="lower right", title="class")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    freed = cur.sum() - fut.sum()
    print(f"\nSaved task figure to {path}.")
    print(f"Freed / redeployable capacity at {int(aggressiveness*100)}% "
          f"adoption: {freed*100:.0f}% of total effort.")


if __name__ == "__main__":
    # Bernstein-grounded run is the headline
    task_report()
    task_figure(aggressiveness=0.7)
    # group-level systemic + flow views
    figure(build_group_workflow(), "group_systemic.png")
