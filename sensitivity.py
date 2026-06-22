"""
sensitivity.py - systemic roles, derived from the measured stage flow rather
than an elicited influence matrix.

Source: Eber, *Project Management2 - Platform Oriented Management* (TUM), 4.2
Higher Order Analysis. The first-order Vester reading takes the active sum as a
node's row total (how much it drives) and the passive sum as its column total
(how much it is driven). The higher-order reading replaces the raw matrix with
the cumulated A + A^2 + ... + A^m, so the sums carry indirect effects and loops,
not just direct links. The diagonal of the cumulated matrix is recursiveness:
how far a node sits inside loops, which at the stage grain is rework.

Honesty of inputs: v1 ran this on a synthetic influence matrix. Here the weights
come from the stage transition (a measured object once real timesheets land), so
the plane is derived from flow rather than opinion. Flow is used as the
observable proxy for influence; a stage that hands work to many others drives
them, a stage many others feed into is driven.
"""
import numpy as np
import bernstein as B
import timesheets as TS
import rnm

STAGES = B.STAGES


def stage_influence(square=True):
    """W[i, j] = stage i drives stage j. Off-diagonal stage transition; squared
    to weight strong handoffs, per Eber's variance-style weighted adjacency."""
    W = TS.STAGE_TRANSITION.copy()
    np.fill_diagonal(W, 0.0)            # influence is on OTHER stages
    return W ** 2 if square else W


def _cumulate(W, m):
    """sum_{k=1}^m W^k. Converges because the weighted flow has spectral
    radius < 1, so longer paths fade and a finite grade suffices."""
    n = W.shape[0]
    S = np.zeros_like(W)
    P = np.eye(n)
    for _ in range(m):
        P = P @ W
        S = S + P
    return S


def roles(W, m):
    S = _cumulate(W, m)
    AS = S.sum(axis=1)                  # drives others (active)
    PS = S.sum(axis=0)                  # driven by others (passive)
    rec = np.diag(S)                    # recursiveness: loop involvement
    return AS, PS, rec


def _maxnorm(AS, PS):
    mx = max(AS.max(), PS.max(), 1e-12)
    return AS / mx, PS / mx


def converged_grade(W, tol=1e-3, mmax=200):
    """Smallest grade m beyond which the normalised roles stop moving - the
    stopping rule Eber asks for, instead of a fixed guess."""
    prev = None
    for m in range(1, mmax + 1):
        AS, PS, _ = roles(W, m)
        v = np.concatenate(_maxnorm(AS, PS))
        if prev is not None and np.max(np.abs(v - prev)) < tol:
            return m
        prev = v
    return mmax


def stage_roles(square=True):
    """Both the first-order and the converged higher-order roles, so the drift
    from direct-only to loops-included is visible."""
    W = stage_influence(square)
    m = converged_grade(W)
    AS1, PS1, _ = roles(W, 1)
    ASm, PSm, recm = roles(W, m)
    AS1, PS1 = _maxnorm(AS1, PS1)
    ASm, PSm = _maxnorm(ASm, PSm)
    rec = recm / (recm.max() or 1.0)
    return dict(m=m, AS1=AS1, PS1=PS1, AS=ASm, PS=PSm, rec=rec, crit=ASm * PSm)


def role_label(AS, PS, asmid, psmid):
    hi_a, hi_p = AS >= asmid, PS >= psmid
    if hi_a and hi_p:
        return "critical"
    if hi_a and not hi_p:
        return "active"
    if not hi_a and hi_p:
        return "reactive"
    return "buffering"


def task_criticality(stage_crit):
    """Push stage criticality onto tasks: a task is as systemically critical as
    the stages it works in. Even weight across active stages is the placeholder a
    real per-stage effort split replaces."""
    out = {}
    for t in rnm.TASKS:
        ss = list(B.TASK_STAGE[t].keys())
        out[t] = float(np.mean([stage_crit[s] for s in ss]))
    return out


if __name__ == "__main__":
    r = stage_roles()
    print(f"converged at grade m = {r['m']}")
    asmid, psmid = r["AS"].mean(), r["PS"].mean()
    print(f"{'stage':28s} {'AS':>5} {'PS':>5} {'rec':>5}  role")
    for i, s in enumerate(STAGES):
        lab = role_label(r["AS"][i], r["PS"][i], asmid, psmid)
        print(f"{s:28s} {r['AS'][i]:5.2f} {r['PS'][i]:5.2f} {r['rec'][i]:5.2f}  {lab}")
