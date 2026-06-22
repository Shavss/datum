"""
model.py - the computational engine. No plotting.

Flow and effort are now indexed by STAGE (sequential, timesheet-aligned).
Classification stays on the task x stage grid. A task's automatability is the
MEAN across its active cells, so tasks that carry more than one class (e.g.
generating alternatives, documenting design decisions) are handled honestly
rather than collapsed to a single label.
"""
import numpy as np
import bernstein as B
import timesheets as TS


def steady_state(transition):
    n = transition.shape[0]
    pi = np.full(n, 1.0 / n)
    for _ in range(2000):
        nxt = pi @ transition
        if np.max(np.abs(nxt - pi)) < 1e-14:
            break
        pi = nxt
    pi = pi / pi.sum()
    vals, vecs = np.linalg.eig(transition.T)
    pi_eig = np.real(vecs[:, np.argmin(np.abs(vals - 1.0))])
    return pi, pi_eig / pi_eig.sum()


def stage_effort():
    h = TS.STAGE_HOURS
    return h / h.sum()


def stage_steady_state():
    return steady_state(TS.STAGE_TRANSITION)[0]


def active_tasks_by_stage():
    active = {s: [] for s in range(B.NS)}
    for t, cells in B.TASK_STAGE.items():
        for s in cells:
            active[s].append(t)
    return active


def task_mean_auto(task):
    cells = B.TASK_STAGE[task]
    return float(np.mean([B.SCALE[c] for c in cells.values()]))


def proposal_strength(task):
    return B.PROPOSAL_STRENGTH.get(task)


def composite_auto(task, alpha=0.6):
    """Automatability as the cognitive class lifted by the proposed AI, where the
    proposal is stronger than the class implies. Upward only: a missing proposal
    never lowers it, since Bernstein's proposal list is not exhaustive."""
    c = task_mean_auto(task)
    s = proposal_strength(task)
    if s is None:
        return c
    return c + alpha * max(0.0, s - c)


def _action_from_auto(a):
    if a >= 0.875:
        return "Automate"
    if a >= 0.625:
        return "Automate w/ oversight"
    if a >= 0.375:
        return "Augment"
    if a >= 0.125:
        return "Augment (human-led)"
    return "Protect (human only)"


def task_catalogue():
    eff_stage = stage_effort()
    active = active_tasks_by_stage()
    task_eff = {t: 0.0 for t in B.TASK_STAGE}
    for s in range(B.NS):
        if active[s]:
            share = eff_stage[s] / len(active[s])
            for t in active[s]:
                task_eff[t] += share
    cat = []
    for g, t in B.TASK_ORDER:
        cells = B.TASK_STAGE[t]
        auto = task_mean_auto(t)
        cat.append(dict(
            group=g, task=t, cls=B._dominant_class(cells),
            classes=B.task_classes(t), multiclass=len(set(cells.values())) > 1,
            auto=auto, action=_action_from_auto(auto),
            auto_adj=composite_auto(t), prop_strength=proposal_strength(t),
            effort=task_eff[t], phase=B._mean_phase(cells),
            proposal=B.AI_PROPOSALS.get(t)))
    return cat


def task_future(cat, aggressiveness=0.7):
    cur = np.array([r["effort"] for r in cat])
    auto = np.array([r["auto"] for r in cat])
    return cur, cur * (1 - auto * aggressiveness)


def automatability_by_stage():
    per = {s: [] for s in range(B.NS)}
    for task, cells in B.TASK_STAGE.items():
        for s, cls in cells.items():
            per[s].append(B.SCALE[cls])
    return np.array([np.mean(per[s]) if per[s] else np.nan for s in range(B.NS)])
