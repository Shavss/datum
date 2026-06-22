"""views.py - one standalone, themed figure per function."""
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Patch
import theme as T
import bernstein as B
import timesheets as TS
from model import (steady_state, stage_effort, task_future,
                   automatability_by_stage)

OUT = "figures"


def _save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    fig.savefig(p)
    plt.close(fig)
    return p


# ===== stage layer (sequential, from timesheets) =====================
def fig_stage_flow():
    eff = stage_effort()
    n = B.NS
    fig, ax = plt.subplots(figsize=(6.8, 8))
    ys = np.arange(n)[::-1]
    bw, bh = 2.6, 0.6
    for i in range(n):
        ax.add_patch(Rectangle((-bw/2, ys[i]-bh/2), bw, bh,
                     facecolor=T.ACCENT_SOFT, edgecolor=T.ACCENT, lw=1.2))
        ax.text(0, ys[i], f"{B.STAGES[i]}\n{eff[i]*100:.0f}% of effort",
                ha="center", va="center", fontsize=8.5)
    for i in range(n-1):
        ax.add_patch(FancyArrowPatch((0, ys[i]-bh/2), (0, ys[i+1]+bh/2),
                     arrowstyle="-|>", mutation_scale=13, color=T.MUTED, lw=1.2))
    for i in range(n):
        for j in range(n):
            if j < i and TS.STAGE_TRANSITION[i, j] > 0.10:
                ax.add_patch(FancyArrowPatch((bw/2, ys[i]), (bw/2, ys[j]),
                             connectionstyle="arc3,rad=-0.4",
                             arrowstyle="-|>", mutation_scale=10,
                             color=T.RED, alpha=0.55, lw=1.1))
    ax.text(bw/2+0.2, ys[0], "rework\nloops", color=T.RED, fontsize=9,
            va="center", ha="left")
    ax.set_xlim(-bw/2-0.6, bw/2+1.5)
    ax.set_ylim(-1, n)
    ax.axis("off")
    T.titlecard(ax, "Workflow flow by stage",
                "RIBA stages run in sequence; effort and rework from timesheets")
    return _save(fig, "01_stage_flow.png")


def fig_stage_effort():
    eff = stage_effort()
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(range(B.NS), eff*100, color=T.ACCENT, width=0.66)
    ax.set_xticks(range(B.NS))
    ax.set_xticklabels(B.STAGES, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("% of effort")
    ax.grid(axis="x", visible=False)
    T.titlecard(ax, "Effort by stage", "measured from timesheets (dummy data)")
    return _save(fig, "02_stage_effort.png")


def fig_macleamy():
    """Effort by stage vs a stylised front-loaded reference. Stage-based, so it
    no longer collapses each task to one phase point."""
    eff = stage_effort()
    n = B.NS
    x = np.arange(n)
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.bar(x, eff*100, color=T.ACCENT_SOFT, edgecolor=T.ACCENT, width=0.6,
           label="actual effort", zorder=2)
    ideal = (n - x).astype(float)
    ideal = ideal / ideal.sum() * 100
    ax.plot(x, ideal, color=T.GREEN, lw=2, ls="--", marker="o",
            label="front-loaded reference", zorder=3)
    wstage = float((eff * x).sum() / eff.sum())
    ax.axvline(wstage, color=T.RED, lw=1.3,
               label=f"effort-weighted stage = {wstage:.1f}")
    ax.set_xticks(x)
    ax.set_xticklabels(B.STAGES, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("% of effort")
    ax.grid(axis="x", visible=False)
    ax.legend()
    T.titlecard(ax, "MacLeamy check",
                "is effort front-loaded, or paid for late in technical design and construction?")
    return _save(fig, "03_macleamy.png")


def fig_convergence(n_iter=40):
    n = B.NS
    pi = np.full(n, 1.0/n)
    hist = [pi.copy()]
    for _ in range(n_iter):
        pi = pi @ TS.STAGE_TRANSITION
        hist.append(pi.copy())
    hist = np.array(hist)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for j in range(n):
        ax.plot(hist[:, j]*100, lw=1.8, label=B.STAGES[j])
    ax.set_xlabel("iteration")
    ax.set_ylabel("% of effort")
    ax.legend(fontsize=7, ncol=2, loc="upper right")
    T.titlecard(ax, "Method check: stage-flow convergence",
                "the stage Markov settles quickly onto a stable distribution")
    return _save(fig, "04_convergence.png")


# ===== task layer (classification from the grid) =====================
def fig_task_automatability(cat, aggressiveness=0.7):
    cur, fut = task_future(cat, aggressiveness)
    order = np.argsort(cur)
    labels = [cat[i]["task"] + (" *" if cat[i]["multiclass"] else "")
              for i in order]
    colors = [T.CLASS_COLOR[cat[i]["cls"]] for i in order]
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.barh(y, cur[order]*100, color=colors, alpha=0.30)
    ax.barh(y, fut[order]*100, color=colors, alpha=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("% of total effort  (faded = current, solid = human after AI;  * = multi-class)")
    ax.grid(axis="y", visible=False)
    handles = [Patch(color=c, label=k) for k, c in T.CLASS_COLOR.items()]
    ax.legend(handles=handles, loc="lower right", title="dominant class")
    T.titlecard(ax, "Task automatability",
                "effort from timesheets via the grid; automatability is the mean across stages")
    return _save(fig, "05_task_automatability.png")


def _block_colours(labels):
    """task -> colour and task -> role name, by RNM block ordered on automatability."""
    import rnm
    prof = rnm.cluster_profile(labels)
    order = sorted(prof, key=lambda c: -prof[c]["mean_auto"])
    names = ["Automate", "Augment", "Protect", "block 4", "block 5"]
    palette = [T.CLASS_COLOR["procedural"], T.CLASS_COLOR["integrative"],
               T.CLASS_COLOR["perceptive"], T.ACCENT, T.GREEN]
    col, role = {}, {}
    for i, c in enumerate(order):
        for t in prof[c]["members"]:
            col[t] = palette[i % len(palette)]
            role[t] = names[i] if i < len(names) else f"block {i}"
    return col, role, order, palette, names


def fig_intervention_map(cat, task_crit, labels):
    """Four-quadrant map: routineness across (can AI do it) against systemic
    criticality up (is it risky to let AI change it), bubble = effort, colour =
    the RNM block. The triangulation that decides where AI goes and how safely."""
    col, role, order, palette, names = _block_colours(labels)
    crit_mid = float(np.median([task_crit[r["task"]] for r in cat]))
    fig, ax = plt.subplots(figsize=(10.5, 7.2))

    # group tasks that share an (almost) identical position and fan them out on a
    # small ring, so genuine ties read as a cluster instead of one overprinted dot
    from collections import defaultdict
    groups = defaultdict(list)
    for r in cat:
        groups[(round(r["auto"], 2), round(task_crit[r["task"]], 3))].append(r)
    placed = {}
    for (ax0, ay0), members in groups.items():
        g = len(members)
        for idx, r in enumerate(sorted(members, key=lambda r: -r["effort"])):
            if g == 1:
                dx, dy = 0.0, 0.0
            else:
                ang = 2 * np.pi * idx / g
                rad = 0.018 + 0.004 * g
                dx, dy = rad * np.cos(ang), rad * 0.85 * np.sin(ang)
            placed[r["task"]] = (r["auto"] + dx, task_crit[r["task"]] + dy)

    for r in cat:
        x, y = placed[r["task"]]
        ax.scatter(x, y, s=80 + r["effort"]*3600, color=col[r["task"]],
                   edgecolor="white", lw=1.1, alpha=0.9, zorder=3)
    for r in cat:
        x, y = placed[r["task"]]
        ha = "left" if x >= 0.45 else "right"
        ox = 7 if ha == "left" else -7
        ax.annotate(r["task"], (x, y), xytext=(ox, 3),
                    textcoords="offset points", fontsize=6.2, ha=ha,
                    color=T.INK, alpha=0.85)
    ax.axvline(0.5, color=T.MUTED, lw=0.9, ls="--")
    ax.axhline(crit_mid, color=T.MUTED, lw=0.9, ls="--")
    ax.text(0.01, 0.98, "AUGMENT\nhuman in the loop", transform=ax.transAxes,
            ha="left", va="top", color=T.RED, fontsize=9.5)
    ax.text(0.99, 0.98, "AUTOMATE\nwith oversight", transform=ax.transAxes,
            ha="right", va="top", color=T.CLASS_COLOR["procedural-integrative"],
            fontsize=9.5)
    ax.text(0.01, 0.02, "ASSIST\nlow priority", transform=ax.transAxes,
            ha="left", va="bottom", color=T.MUTED, fontsize=9.5)
    ax.text(0.99, 0.02, "AUTOMATE", transform=ax.transAxes,
            ha="right", va="bottom", color=T.GREEN, fontsize=9.5)
    handles = [Patch(color=palette[i], label=names[i]) for i in range(len(order))]
    ax.legend(handles=handles, loc="center left", title="block (RNM)", fontsize=8.5)
    ax.set_xlabel("routineness  (0 judgement  ->  1 routine / procedural)")
    ax.set_ylabel("systemic criticality  (active x passive, from stage flow)")
    ax.set_xlim(-0.05, 1.05)
    T.titlecard(ax, "Intervention map",
                "where AI helps (across) crossed with how risky it is to change (up); bubble = effort")
    return _save(fig, "06_intervention_map.png")


def fig_states(cat, aggressiveness=0.7):
    cur, fut = task_future(cat, aggressiveness)
    g_cur = {g: 0.0 for g in B.GROUPS}
    g_fut = {g: 0.0 for g in B.GROUPS}
    for r, c, f in zip(cat, cur, fut):
        g_cur[r["group"]] += c
        g_fut[r["group"]] += f
    groups = sorted(B.GROUPS, key=lambda g: g_cur[g])
    y = np.arange(len(groups))
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh(y+0.2, [g_cur[g]*100 for g in groups], height=0.4,
            color=T.MUTED, label="current")
    ax.barh(y-0.2, [g_fut[g]*100 for g in groups], height=0.4,
            color=T.ACCENT, label="future (human effort)")
    ax.set_yticks(y)
    ax.set_yticklabels(groups)
    ax.set_xlabel("% of today's total effort")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    freed = (cur.sum()-fut.sum())*100
    T.titlecard(ax, "Current vs future state",
                f"at {int(aggressiveness*100)}% adoption, {freed:.0f}% of effort freed to redeploy")
    return _save(fig, "07_states.png")


def fig_task_stage_grid():
    ordered = [t for (g, t, c, p) in B.TASKS]
    n = B.NS
    fig, ax = plt.subplots(figsize=(11, 9))
    for row, task in enumerate(reversed(ordered)):
        cells = B.TASK_STAGE.get(task, {})
        for s in range(n):
            cls = cells.get(s)
            color = T.CLASS_COLOR[cls] if cls else "#f7fafc"
            ax.add_patch(Rectangle((s, row), 1, 1, facecolor=color,
                                   edgecolor="white", lw=1.5))
        ax.text(-0.2, row+0.5, task, ha="right", va="center", fontsize=7.5)
    for name, stages in B.SERVICE_CATEGORIES:
        lo, hi = min(stages), max(stages)
        ax.plot([lo, hi+1], [-0.6, -0.6], color=T.INK, lw=1.5)
        ax.text((lo+hi+1)/2, -1.1, name, ha="center", va="top", fontsize=7.5)
    ax.set_xlim(-0.05, n)
    ax.set_ylim(-1.6, len(ordered))
    ax.set_xticks(np.arange(n)+0.5)
    ax.set_xticklabels(B.STAGES, rotation=35, ha="right", fontsize=7.5)
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.grid(False)
    handles = [Patch(color=c, label=k) for k, c in T.CLASS_COLOR.items()]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
              title="class")
    T.titlecard(ax, "Task x stage grid",
                "service categories overlap (Definition and Design share stages 1-2)")
    return _save(fig, "08_task_stage_grid.png")


def fig_automatability_by_stage():
    auto = automatability_by_stage()
    n = B.NS
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    bands = ["#edf2f7", "#e2e8f0"]
    for i, (name, stages) in enumerate(B.SERVICE_CATEGORIES):
        lo, hi = min(stages), max(stages)+1
        ax.axvspan(lo, hi, color=bands[i % 2], alpha=0.5, zorder=0)
        ax.text((lo+hi)/2, 1.02, name, ha="center", va="bottom", fontsize=7.5,
                color=T.MUTED)
    x = np.arange(n)+0.5
    ax.plot(x, auto, color=T.ACCENT, lw=2.4, marker="o", ms=8, zorder=3)
    ax.axhline(0.5, color=T.MUTED, lw=0.9, ls="--")
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1.08)
    ax.set_xticks(x)
    ax.set_xticklabels(B.STAGES, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("mean automatability of active work")
    ax.grid(axis="x", visible=False)
    T.titlecard(ax, "Automatability across the lifecycle",
                "early work is judgement to protect, technical stages are procedural to automate")
    return _save(fig, "09_automatability_by_stage.png")


# ===== iteration 3: RNM-derived grouping ============================
def fig_rnm_separation(construction="class", iters=36):
    import rnm
    adj = rnm.ADJACENCIES[construction]()
    hist = rnm.separation_history(adj, z=1, iters=iters)
    labels, k = rnm.grouping(adj)
    # name clusters by mean automatability so colour reads as a role band
    prof = rnm.cluster_profile(labels)
    order = sorted(prof, key=lambda c: -prof[c]["mean_auto"])
    palette = [T.CLASS_COLOR["procedural"], T.CLASS_COLOR["integrative"],
               T.CLASS_COLOR["perceptive"], T.ACCENT, T.GREEN]
    cmap = {c: palette[i % len(palette)] for i, c in enumerate(order)}
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for i in range(rnm.N):
        ax.plot(hist[:, i], color=cmap[labels[i]], lw=1.3, alpha=0.8)
    ax.set_xlabel("RNM iteration  (neighbourhood averaging)")
    ax.set_ylabel("node value")
    ax.set_ylim(-1.5, 1.4)
    role = {order[0]: "Automate block", order[1] if k > 1 else order[0]: "Augment block"}
    if k > 2:
        role[order[2]] = "Protect block"
    handles = [Patch(color=cmap[c], label=role.get(c, f"block {c}")) for c in order]
    ax.legend(handles=handles, loc="upper right")
    T.titlecard(ax, "How the grouping emerges (RNM)",
                f"random values averaged over neighbours separate into {k} automatability blocks")
    return _save(fig, "10_rnm_separation.png")


def fig_segments_supported():
    import rnm
    names = ["cooccurrence\n(when)", "class\n(how automatable)", "blend"]
    keys = ["cooccurrence", "class", "blend"]
    counts = [rnm.segment_count(rnm.ADJACENCIES[k]())[0] for k in keys]
    fig, ax = plt.subplots(figsize=(8.5, 5))
    bars = ax.bar(names, counts, color=[T.MUTED, T.ACCENT, T.MUTED], width=0.6)
    ax.axhline(5, color=T.RED, lw=1.4, ls="--")
    ax.text(2.45, 5.05, "Bernstein imposes 5", color=T.RED, fontsize=9,
            ha="right", va="bottom")
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width()/2, c + 0.08, str(c), ha="center",
                va="bottom", fontsize=12, fontweight="bold")
    ax.set_ylabel("segments the data supports (eigen-gap)")
    ax.set_ylim(0, 6)
    ax.grid(axis="x", visible=False)
    T.titlecard(ax, "Are five groups right?",
                "by when work happens the practice is one inseparable system; by how automatable it is, three blocks")
    return _save(fig, "11_segments_supported.png")


def fig_opportunity_map(cat, labels, k):
    """Every task in its data-derived block, placed by automatability (class
    baseline lifted by the proposed AI), sized by effort, with the proposed AI
    shown on the right. One row per task, so nothing collides."""
    import rnm
    import textwrap
    prof = rnm.cluster_profile(labels)
    order = sorted(prof, key=lambda c: -prof[c]["mean_auto"])
    role = ["Automate", "Augment", "Protect", "block 4", "block 5"]
    palette = [T.CLASS_COLOR["procedural"], T.CLASS_COLOR["integrative"],
               T.CLASS_COLOR["perceptive"], T.ACCENT, T.GREEN]
    cmap = {c: palette[i % len(palette)] for i, c in enumerate(order)}
    rec = {r["task"]: r for r in cat}

    rows, band_spans, yt, ytl = [], [], [], []
    y = 0
    for i, c in enumerate(order):
        members = sorted(prof[c]["members"], key=lambda m: rec[m]["effort"])
        start = y
        for m in members:
            rows.append((m, y, cmap[c]))
            yt.append(y); ytl.append(m)
            y += 1
        band_spans.append((start - 0.5, y - 0.5, c, i))
        y += 0.6

    fig, ax = plt.subplots(figsize=(14.5, 9.5))
    for lo, hi, c, i in band_spans:
        ax.axhspan(lo, hi, color=cmap[c], alpha=0.07, zorder=0)
        share = sum(rec[m]["effort"] for m in prof[c]["members"]) * 100
        ax.text(2.42, (lo + hi) / 2, f"{role[i]}\n{share:.0f}% effort",
                ha="left", va="center", fontsize=8.5, color=cmap[c],
                fontweight="bold")
    for task, yy, col in rows:
        r = rec[task]
        base, adj, e = r["auto"], r["auto_adj"], r["effort"]
        if adj - base > 0.01:                       # proposed-AI lift
            ax.scatter(base, yy, s=70, facecolors="none", edgecolors=T.MUTED,
                       lw=1.1, zorder=2)
            ax.annotate("", xy=(adj, yy), xytext=(base, yy),
                        arrowprops=dict(arrowstyle="-|>", color=T.GREEN, lw=1.3))
        ax.scatter(adj, yy, s=120 + e * 4200, color=col, edgecolor="white",
                   lw=1.2, alpha=0.92, zorder=3)
        if r["proposal"]:                           # the proposed AI, on the map
            txt = textwrap.shorten(r["proposal"]["ai"], width=52, placeholder=" ...")
            ax.text(1.1, yy, txt, ha="left", va="center", fontsize=6.4,
                    color=T.INK, alpha=0.85)
    ax.axvline(0.5, color=T.MUTED, lw=0.9, ls="--", zorder=1)
    ax.text(1.1, y - 0.3, "proposed AI (Bernstein 1.5.4)", fontsize=7.5,
            color=T.MUTED, style="italic")
    ax.set_yticks(yt)
    ax.set_yticklabels(ytl, fontsize=7.4)
    ax.set_ylim(-1, y - 0.6)
    ax.set_xlim(-0.05, 2.95)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("automatability  (class baseline, green arrow = lift from the proposed AI)")
    ax.grid(axis="y", visible=False)
    T.titlecard(ax, "AI opportunity map",
                "blocks by RNM; bubble = effort; arrow = the proposed AI lifting the class baseline")
    return _save(fig, "12_opportunity_map.png")



def fig_sensitivity_plane():
    """The Vester plane on the nine RIBA stages, derived from the measured
    stage flow. Position = role, size = recursiveness (loop involvement),
    faint ghost + arrow = drift from first-order to higher-order."""
    import sensitivity as S
    r = S.stage_roles()
    AS, PS, AS1, PS1, rec = r["AS"], r["PS"], r["AS1"], r["PS1"], r["rec"]
    asmid, psmid = AS.mean(), PS.mean()
    fig, ax = plt.subplots(figsize=(9.5, 7.2))
    ax.axvline(psmid, color=T.MUTED, lw=0.9, ls="--")
    ax.axhline(asmid, color=T.MUTED, lw=0.9, ls="--")
    for i in range(len(AS)):
        ax.annotate("", xy=(PS[i], AS[i]), xytext=(PS1[i], AS1[i]),
                    arrowprops=dict(arrowstyle="-|>", color=T.MUTED, lw=1.0,
                                    alpha=0.6))
        ax.scatter(PS1[i], AS1[i], s=30, color=T.MUTED, alpha=0.4, zorder=2)
    sizes = 120 + rec * 520
    ax.scatter(PS, AS, s=sizes, color=T.ACCENT, edgecolor="white", lw=1.2,
               alpha=0.92, zorder=3)
    for i, s in enumerate(S.STAGES):
        ax.annotate(s, (PS[i], AS[i]), xytext=(7, 5),
                    textcoords="offset points", fontsize=7.4)
    ax.text(0.01, 0.98, "ACTIVE\nlevers", transform=ax.transAxes, ha="left",
            va="top", color=T.GREEN, fontsize=10)
    ax.text(0.99, 0.98, "CRITICAL\nhandle with care", transform=ax.transAxes,
            ha="right", va="top", color=T.RED, fontsize=10)
    ax.text(0.01, 0.02, "BUFFERING\ninert", transform=ax.transAxes, ha="left",
            va="bottom", color=T.MUTED, fontsize=10)
    ax.text(0.99, 0.02, "REACTIVE\nindicators", transform=ax.transAxes,
            ha="right", va="bottom", color=T.ACCENT, fontsize=10)
    ax.set_xlabel("passive sum  (how much the stage is DRIVEN)")
    ax.set_ylabel("active sum  (how much the stage DRIVES)")
    T.titlecard(ax, "Stage sensitivity (higher order)",
                f"derived from stage flow; bubble = recursiveness; arrows = first order -> grade {r['m']}")
    return _save(fig, "13_sensitivity_plane.png")


# ===== v4: work-activity layer =======================================
def _auto_band_colour(a):
    if a >= 0.625:
        return T.CLASS_COLOR["procedural"]      # automate
    if a >= 0.375:
        return T.CLASS_COLOR["integrative"]     # augment
    return T.CLASS_COLOR["perceptive"]          # protect


def fig_activity_flow():
    """Vertical work flow over the activities, with rework loops drawn in red.
    The value-stream map with the loops a linear stage model cannot show."""
    import activities as A
    rows = A.activity_table()
    eff = {r["activity"]: r["effort"] for r in rows}
    T_ = A.activity_flow()
    n = A.NA
    fig, ax = plt.subplots(figsize=(7.4, 9))
    ys = np.arange(n)[::-1]
    bw, bh = 3.0, 0.6
    for i, a in enumerate(A.ACT_ORDER):
        ax.add_patch(Rectangle((-bw/2, ys[i]-bh/2), bw, bh,
                     facecolor=T.ACCENT_SOFT, edgecolor=T.ACCENT, lw=1.2))
        ax.text(0, ys[i], f"{a}  ({eff[a]*100:.0f}%)", ha="center",
                va="center", fontsize=8.5)
    for i in range(n-1):
        ax.add_patch(FancyArrowPatch((0, ys[i]-bh/2), (0, ys[i+1]+bh/2),
                     arrowstyle="-|>", mutation_scale=12, color=T.MUTED, lw=1.1))
    # rework: edges that run back up the order, above a visibility threshold
    for i in range(n):
        for j in range(n):
            if j < i and T_[i, j] > 0.12:
                ax.add_patch(FancyArrowPatch(
                    (bw/2, ys[i]), (bw/2, ys[j]),
                    connectionstyle=f"arc3,rad=-{0.18+0.04*(i-j)}",
                    arrowstyle="-|>", mutation_scale=10, color=T.RED,
                    lw=0.6+2.2*T_[i, j], alpha=0.55))
    ax.text(bw/2+0.2, ys[1], "rework\nloops", color=T.RED, fontsize=9,
            va="center", ha="left", alpha=0.85)
    ax.set_xlim(-bw/2-0.4, bw/2+1.6)
    ax.set_ylim(-1, n)
    ax.axis("off")
    T.titlecard(ax, "Workflow (effort share + rework loops)",
                "effort = long-run share from the activity flow; red = rework back to design")
    return _save(fig, "14_activity_flow.png")


def fig_influence_graph():
    """The activity influence graph: node size = criticality, edge width =
    elicited influence. The structure the stage sequence could not show."""
    import networkx as nx
    import activities as A
    sens = A.activity_sensitivity()
    W = A.activity_influence()
    G = nx.DiGraph()
    for a in A.ACT_ORDER:
        G.add_node(a)
    for i in range(A.NA):
        for j in range(A.NA):
            if W[i, j] > 0:
                G.add_edge(A.ACT_ORDER[i], A.ACT_ORDER[j], w=W[i, j])
    pos = nx.spring_layout(G, seed=4, k=1.4, iterations=300)
    fig, ax = plt.subplots(figsize=(11, 8.5))
    sizes = [300 + sens["crit"][A._IX[a]] * 4200 for a in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=T.ACCENT_SOFT,
                           edgecolors=T.ACCENT, linewidths=1.4, ax=ax)
    edges = list(G.edges(data=True))
    widths = [0.5 + d["w"] * 1.1 for _u, _v, d in edges]
    nx.draw_networkx_edges(G, pos, edgelist=[(u, v) for u, v, _ in edges],
                           width=widths, edge_color=T.MUTED, alpha=0.5,
                           arrowsize=10, node_size=sizes,
                           connectionstyle="arc3,rad=0.07", ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=8.2, ax=ax)
    ax.axis("off")
    T.titlecard(ax, "Workflow influence graph",
                "node size = systemic criticality (higher order); edge width = elicited influence")
    return _save(fig, "15_influence_graph.png")


def fig_activity_intervention():
    """Four-quadrant map at the activity grain: clean, ~10 nodes. Routineness
    (proposal-adjusted) across, criticality up, bubble = effort, colour = band."""
    import activities as A
    rows = A.activity_table(adjusted=True)
    base = {r["activity"]: r["auto_base"] for r in A.activity_table(adjusted=False)}
    sens = A.activity_sensitivity()
    crit = {a: sens["crit"][A._IX[a]] for a in A.ACT_ORDER}
    cmid = float(np.median(list(crit.values())))
    fig, ax = plt.subplots(figsize=(10, 7))
    for r in rows:
        a = r["activity"]
        ax.scatter(r["auto"], crit[a], s=120 + r["effort"]*5200,
                   color=_auto_band_colour(r["auto"]), edgecolor="white",
                   lw=1.3, alpha=0.92, zorder=3)
        if abs(r["auto"] - base[a]) > 0.01:           # proposed-AI lift
            ax.annotate("", xy=(r["auto"], crit[a]), xytext=(base[a], crit[a]),
                        arrowprops=dict(arrowstyle="-|>", color=T.GREEN, lw=1.4))
    for r in rows:
        a = r["activity"]
        ax.annotate(a, (r["auto"], crit[a]), xytext=(7, 5),
                    textcoords="offset points", fontsize=7.6)
    ax.axvline(0.5, color=T.MUTED, lw=0.9, ls="--")
    ax.axhline(cmid, color=T.MUTED, lw=0.9, ls="--")
    ax.text(0.01, 0.98, "AUGMENT\nhuman in the loop", transform=ax.transAxes,
            ha="left", va="top", color=T.RED, fontsize=9.5)
    ax.text(0.99, 0.98, "AUTOMATE\nwith oversight", transform=ax.transAxes,
            ha="right", va="top", color=T.CLASS_COLOR["procedural-integrative"],
            fontsize=9.5)
    ax.text(0.01, 0.02, "ASSIST\nlow priority", transform=ax.transAxes,
            ha="left", va="bottom", color=T.MUTED, fontsize=9.5)
    ax.text(0.99, 0.02, "AUTOMATE", transform=ax.transAxes, ha="right",
            va="bottom", color=T.GREEN, fontsize=9.5)
    ax.set_xlabel("routineness  (class + proposed AI; green arrow = the proposal lift)")
    ax.set_ylabel("systemic criticality  (active x passive, from influence)")
    ax.set_xlim(-0.05, 1.05)
    T.titlecard(ax, "Intervention map (activities)",
                "where AI helps across, how risky to change up, bubble = effort")
    return _save(fig, "16_activity_intervention.png")


def fig_activity_opportunity():
    """AI opportunity map at the activity grain: automatability vs effort, with
    the proposed-AI lift over the class baseline surfaced."""
    import activities as A
    base = {r["activity"]: r for r in A.activity_table(adjusted=False)}
    adj = {r["activity"]: r for r in A.activity_table(adjusted=True)}
    fig, ax = plt.subplots(figsize=(10.5, 7))
    for a in A.ACT_ORDER:
        b, t = base[a], adj[a]
        y = b["effort"] * 100
        ax.scatter(t["auto"], y, s=130 + b["effort"]*5200,
                   color=_auto_band_colour(t["auto"]), edgecolor="white",
                   lw=1.3, alpha=0.92, zorder=3)
        if abs(t["auto"] - b["auto"]) > 0.01:
            ax.annotate("", xy=(t["auto"], y), xytext=(b["auto"], y),
                        arrowprops=dict(arrowstyle="-|>", color=T.GREEN, lw=1.5))
        tag = a + (f"  [{b['n_proposals']} AI]" if b["n_proposals"] else "")
        ax.annotate(tag, (t["auto"], y), xytext=(8, 5),
                    textcoords="offset points", fontsize=7.4)
    ax.axvline(0.5, color=T.MUTED, lw=0.9, ls="--")
    ax.text(0.99, 0.02, "AUTOMATE", transform=ax.transAxes, ha="right",
            va="bottom", color=T.GREEN, fontsize=10)
    ax.text(0.01, 0.02, "PROTECT / AUGMENT", transform=ax.transAxes,
            ha="left", va="bottom", color=T.RED, fontsize=10)
    ax.set_xlabel("automatability  (green arrow = class baseline -> proposed-AI adjusted)")
    ax.set_ylabel("% of effort")
    ax.set_xlim(-0.05, 1.05)
    T.titlecard(ax, "AI opportunity map (activities)",
                "bubble = effort; [n AI] = Bernstein proposals; arrow = proposal lift")
    return _save(fig, "17_activity_opportunity.png")


def fig_activity_sensitivity():
    import activities as A
    sens = A.activity_sensitivity()
    AS, PS, rec = sens["AS"], sens["PS"], sens["rec"]
    asm, psm = AS.mean(), PS.mean()
    fig, ax = plt.subplots(figsize=(9.5, 7.2))
    ax.axvline(psm, color=T.MUTED, lw=0.9, ls="--")
    ax.axhline(asm, color=T.MUTED, lw=0.9, ls="--")
    ax.scatter(PS, AS, s=120 + rec*620, color=T.ACCENT, edgecolor="white",
               lw=1.2, alpha=0.92, zorder=3)
    for i, a in enumerate(A.ACT_ORDER):
        ax.annotate(a, (PS[i], AS[i]), xytext=(7, 5),
                    textcoords="offset points", fontsize=7.6)
    ax.text(0.01, 0.98, "ACTIVE\nlevers", transform=ax.transAxes, ha="left",
            va="top", color=T.GREEN, fontsize=10)
    ax.text(0.99, 0.98, "CRITICAL\nhandle with care", transform=ax.transAxes,
            ha="right", va="top", color=T.RED, fontsize=10)
    ax.text(0.01, 0.02, "BUFFERING\ninert", transform=ax.transAxes, ha="left",
            va="bottom", color=T.MUTED, fontsize=10)
    ax.text(0.99, 0.02, "REACTIVE\nindicators", transform=ax.transAxes,
            ha="right", va="bottom", color=T.ACCENT, fontsize=10)
    ax.set_xlabel("passive sum  (how much the activity is DRIVEN)")
    ax.set_ylabel("active sum  (how much the activity DRIVES)")
    T.titlecard(ax, "Activity sensitivity (higher order)",
                f"on the activity influence graph; bubble = recursiveness; grade {sens['m']}")
    return _save(fig, "18_activity_sensitivity.png")


# ===== v5: the 2026 trajectory ======================================
_LABEL_COLOUR = {"Automating": T.GREEN,
                 "Supporting": T.CLASS_COLOR["integrative"],
                 "Collaborating": T.ACCENT}


def fig_computation_climb():
    """The climb: each task's AI computation type in 2022 vs 2026. Shows how far
    the line has moved, grouped by the Bernstein function. x = the ladder."""
    import bernstein as B
    import tooling as TL
    import rnm
    groups = B.GROUPS
    fig, ax = plt.subplots(figsize=(11.5, 10.5))
    y = 0
    yt, ytl, band = [], [], []
    for g in groups:
        tasks = [t for (gg, t) in B.TASK_ORDER if gg == g]
        tasks = sorted(tasks, key=lambda t: TL.autonomy_2026(t))
        start = y
        for t in tasks:
            a, b = TL.autonomy_2022(t), TL.autonomy_2026(t)
            col = _LABEL_COLOUR[TL.label_of(t)]
            ax.plot([a, b], [y, y], color=col, lw=1.6, alpha=0.5, zorder=2)
            ax.scatter(a, y, s=42, facecolors="white", edgecolors=T.MUTED,
                       lw=1.2, zorder=3)
            ax.annotate("", xy=(b, y), xytext=(a, y),
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.6))
            ax.scatter(b, y, s=130, color=col, edgecolor="white", lw=1.2, zorder=4)
            yt.append(y); ytl.append(t)
            y += 1
        band.append((start - 0.5, y - 0.5, g))
        y += 0.7
    for lo, hi, g in band:
        ax.axhspan(lo, hi, color=T.GRID, alpha=0.5, zorder=0)
        ax.text(1.02, (lo + hi) / 2, g, ha="left", va="center", fontsize=8,
                color=T.INK, fontweight="bold")
    ax.set_yticks(yt); ax.set_yticklabels(ytl, fontsize=7.2)
    ax.set_ylim(-1, y - 0.7)
    ax.set_xlim(-0.05, 1.18)
    ax.set_xticks(list(TL.AUTONOMY_TICKS))
    ax.set_xticklabels([TL.AUTONOMY_TICKS[k] for k in TL.AUTONOMY_TICKS], fontsize=8.5)
    ax.grid(axis="y", visible=False)
    handles = [Patch(color=c, label=k) for k, c in _LABEL_COLOUR.items()]
    ax.legend(handles=handles, loc="lower right", title="human-AI relationship",
              fontsize=8, frameon=True, facecolor="white", framealpha=0.92,
              edgecolor=T.GRID)
    T.titlecard(ax, "The climb: tool autonomy, 2022 to 2026",
                "hollow = 2022, filled = 2026; agentic tools top the autonomy axis and stay cognitive in type")
    return _save(fig, "19_computation_climb.png")


def fig_readiness_map():
    """The opportunity map gains a second axis: automatable in principle (across)
    against how autonomous the tooling is now (up). Autonomy is the real
    Activity grain, bubble = effort, colour = the human-AI relationship."""
    import activities as A
    import tooling as TL
    from collections import Counter
    rows = A.activity_table(adjusted=True)
    fig, ax = plt.subplots(figsize=(10.5, 7.5))
    for r in rows:
        a = r["activity"]
        tasks = A.ACTIVITY_TASKS[a]
        ready = float(np.mean([TL.autonomy_2026(t) for t in tasks]))
        lab = Counter(TL.label_of(t) for t in tasks).most_common(1)[0][0]
        ax.scatter(r["auto"], ready, s=140 + r["effort"]*5400,
                   color=_LABEL_COLOUR[lab], edgecolor="white", lw=1.3,
                   alpha=0.9, zorder=3)
        dy = 7 if (rows.index(r) % 2 == 0) else -13
        ax.annotate(a, (r["auto"], ready), xytext=(8, dy),
                    textcoords="offset points", fontsize=7.4)
    ax.axvline(0.5, color=T.MUTED, lw=0.9, ls="--")
    ax.axhline(0.5, color=T.MUTED, lw=0.9, ls="--")
    ax.text(0.99, 0.98, "AUTOMATABLE +\nautonomous tooling\n= act now", transform=ax.transAxes,
            ha="right", va="top", color=T.GREEN, fontsize=9)
    ax.text(0.01, 0.98, "human-led, but\ncapable tooling exists\n= augment / collaborate",
            transform=ax.transAxes, ha="left", va="top", color=T.ACCENT, fontsize=9)
    ax.text(0.99, 0.02, "automatable in principle,\ntooling still basic\n= watch / build",
            transform=ax.transAxes, ha="right", va="bottom", color=T.MUTED, fontsize=9)
    ax.set_xlabel("automatable in principle  (routineness, class + proposed AI)")
    ax.set_ylabel("tool autonomy now  (assistive  ->  autonomous; agentic at top)")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(0, 1.0)
    ax.set_yticks(list(TL.AUTONOMY_TICKS))
    ax.set_yticklabels([TL.AUTONOMY_TICKS[k] for k in TL.AUTONOMY_TICKS], fontsize=8)
    handles = [Patch(color=c, label=k) for k, c in _LABEL_COLOUR.items()]
    ax.legend(handles=handles, loc="lower left", fontsize=8, title="human-AI relationship")
    T.titlecard(ax, "Readiness map (2026)",
                "can AI do it, across; is the tooling here yet, up; bubble = effort")
    return _save(fig, "20_readiness_map.png")


# ===== v6: cost-impact business case ================================
def fig_cost_saved():
    """Per activity: the cost base and the slice AI removes at expected adoption.
    The business case, sorted by money saved."""
    import cost as C
    rows = sorted(C.by_stage(), key=lambda r: r["cost"])
    ys = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(ys, [r["cost"]/1e3 for r in rows], color=T.GRID, height=0.62,
            label="measured cost (timesheets x band rate)")
    ax.barh(ys, [r["saved_cost"]/1e3 for r in rows], color=T.GREEN, height=0.62,
            label="capacity released at expected adoption")
    for i, r in enumerate(rows):
        ax.text(r["cost"]/1e3 + 6, i,
                f"£{r['saved_cost']/1e3:,.0f}k  ({r['saved_frac']*100:.0f}%)",
                va="center", fontsize=7.6, color=T.INK)
    ax.set_yticks(ys); ax.set_yticklabels([r["stage"] for r in rows], fontsize=8)
    ax.set_xlabel("£ thousands per year")
    ax.set_xlim(0, max(r["cost"] for r in rows)/1e3 * 1.2)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", fontsize=8.5)
    tot = C.totals()["expected"]
    T.titlecard(ax, "Cost per stage, and the capacity AI releases",
                f"cost base measured £{tot['cost']/1e6:.2f}M/yr; released capacity £{tot['saved_cost']/1e6:.2f}M/yr expected (a projection, not booked saving)")
    return _save(fig, "21_cost_saved.png")


def fig_savings_bands():
    """Total annual saving under low, expected and high adoption."""
    import cost as C
    t = C.totals()
    order = ["low", "expected", "high"]
    vals = [t[k]["saved_cost"]/1e6 for k in order]
    pct = [t[k]["saved_cost"]/t[k]["cost"]*100 for k in order]
    cols = [T.MUTED, T.GREEN, T.ACCENT]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(order, vals, color=cols, width=0.6)
    for b, v, p, k in zip(bars, vals, pct, order):
        ax.text(b.get_x()+b.get_width()/2, v+0.02,
                f"£{v:.2f}M\n{p:.0f}% of base\n({C.ADOPTION[k]:.0%} adoption)",
                ha="center", va="bottom", fontsize=8.5)
    ax.set_ylabel("£ millions saved per year")
    ax.set_ylim(0, max(vals)*1.32)
    ax.grid(axis="x", visible=False)
    T.titlecard(ax, "Capacity released depends on adoption",
                "salaried cost of freed hours; the rate is the load-bearing assumption, so a band not a point")
    return _save(fig, "22_savings_bands.png")


def fig_type_shift():
    """Computation type composition, 2022 vs 2026. The type shift as categories,
    not a height, so it does not imply agentic is a higher type than cognitive."""
    import tooling as TL
    cats = TL.TYPE_ORDER + ["none"]
    cmap = {"Algorithmic": T.MUTED, "Empiricist": T.CLASS_COLOR["integrative"],
            "Cognitive": T.ACCENT, "none": T.GRID}
    c22, c26 = TL.type_composition(2022), TL.type_composition(2026)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for x, comp in [(0, c22), (1, c26)]:
        bottom = 0
        for cat in cats:
            h = comp[cat]
            if h:
                ax.bar(x, h, bottom=bottom, color=cmap[cat], width=0.5,
                       edgecolor="white")
                ax.text(x, bottom + h/2, f"{cat} {h}", ha="center", va="center",
                        fontsize=7.5, color="white" if cat != "none" else T.INK)
                bottom += h
    ax.set_xticks([0, 1]); ax.set_xticklabels(["2022", "2026"], fontsize=11)
    ax.set_ylabel("tasks using each computation type")
    ax.grid(axis="x", visible=False)
    T.titlecard(ax, "The shift up the computation types",
                "2022 was rule-based with most tasks untouched; 2026 is mostly cognitive and empiricist")
    return _save(fig, "23_type_shift.png")


def fig_released_by_band():
    """Who the AI frees: released cost by band. The release lands on the bands
    doing the automatable production work, not evenly across seniority."""
    import cost as C
    bands = C.BAND_ORDER
    d = C.by_band()
    vals = [d[b]["saved_cost"]/1e3 for b in bands]
    hrs = [d[b]["saved_hours"] for b in bands]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(bands, vals, color=T.ACCENT, width=0.62)
    for b, v_, h in zip(bars, vals, hrs):
        ax.text(b.get_x()+b.get_width()/2, v_+1.5,
                f"£{v_:,.0f}k\n{h:,.0f} h", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("£ thousands released per year")
    ax.set_ylim(0, max(vals)*1.3)
    ax.set_xlabel("band (cost rate rises left to right)")
    ax.grid(axis="x", visible=False)
    T.titlecard(ax, "Who the AI frees",
                "released capacity by band, expected adoption; the saving concentrates in mid bands")
    return _save(fig, "24_released_by_band.png")


def fig_capacity_conversion():
    """Released hours are not money until converted. Two routes, each with a
    precondition; doing neither reabsorbs the time. Turns the output into a
    decision rather than a promise."""
    import cost as C
    from matplotlib.patches import FancyBboxPatch
    c = C.conversion()
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    ax.axis("off")
    ax.text(0.5, 0.96, f"The model releases {c['released_hours']:,.0f} hours a year",
            ha="center", fontsize=13, fontweight="bold", color=T.INK,
            transform=ax.transAxes)
    ax.text(0.5, 0.89, "that is £0 on the books until the firm converts it; doing neither reabsorbs the time",
            ha="center", fontsize=9.5, color=T.MUTED, transform=ax.transAxes)

    def card(x, title, value, cond, col):
        ax.add_patch(FancyBboxPatch((x, 0.30), 0.36, 0.46, boxstyle="round,pad=0.02",
                     transform=ax.transAxes, facecolor=col, edgecolor="none", alpha=0.12))
        ax.text(x+0.18, 0.70, title, ha="center", fontsize=11.5, fontweight="bold",
                color=col, transform=ax.transAxes)
        ax.text(x+0.18, 0.58, value, ha="center", fontsize=17, fontweight="bold",
                color=T.INK, transform=ax.transAxes)
        ax.text(x+0.18, 0.46, cond, ha="center", va="top", fontsize=8.6,
                color=T.INK, wrap=True, transform=ax.transAxes)

    card(0.08, "Margin route", f"£{c['margin_value']/1e3:,.0f}k / yr",
         "salary cost avoided.\nRequires running the work\nwith fewer hours or fewer\npeople. Within the firm's\ncontrol, but the hard call.", T.GREEN)
    card(0.56, "Growth route", f"£{c['growth_value']/1e3:,.0f}k / yr",
         "extra fee from re-selling\nfreed time at charge-out.\nWorth more per hour, but\nneeds a pipeline to absorb\nit. Outside the firm's control.", T.ACCENT)
    ax.text(0.5, 0.06, "same released hours, two values; the decision, not the saving, is the deliverable",
            ha="center", fontsize=8.5, style="italic", color=T.MUTED, transform=ax.transAxes)
    return _save(fig, "25_capacity_conversion.png")


def fig_roadmap():
    """Sequenced roadmap: act now where capable tooling runs on project data;
    needs foundations where the AI needs the firm's own data first; watch the
    rest. The needs-foundations lane is the bridge to the data engagement."""
    import activities as A, tooling as TL, model as M
    from matplotlib.patches import FancyBboxPatch
    rows = A.activity_table(adjusted=True)
    eff = {r["activity"]: r["effort"] for r in rows}
    lanes = {"Act now": [], "Watch": [], "Needs foundations": []}
    for a in A.ACT_ORDER:
        ts = A.ACTIVITY_TASKS[a]
        pr = float(np.mean([M.composite_auto(t) * TL.autonomy_2026(t) for t in ts]))
        nd = np.mean([TL.needs_firm_data(t) for t in ts])
        if nd > 0.5:
            lanes["Needs foundations"].append((a, pr))
        elif pr >= 0.40:
            lanes["Act now"].append((a, pr))
        else:
            lanes["Watch"].append((a, pr))
    cols = {"Act now": T.GREEN, "Watch": T.MUTED, "Needs foundations": T.ACCENT}
    sub = {"Act now": "tooling ready, runs on project data",
           "Watch": "value or tooling not there yet",
           "Needs foundations": "needs the firm's own data first"}
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.axis("off")
    xs = {"Act now": 0.04, "Watch": 0.37, "Needs foundations": 0.70}
    for lane, x in xs.items():
        ax.add_patch(plt.Rectangle((x, 0.04), 0.28, 0.84, transform=ax.transAxes,
                     facecolor=cols[lane], alpha=0.07, edgecolor="none"))
        ax.text(x+0.14, 0.93, lane, ha="center", fontsize=12.5, fontweight="bold",
                color=cols[lane], transform=ax.transAxes)
        ax.text(x+0.14, 0.895, sub[lane], ha="center", fontsize=8, color=T.MUTED,
                transform=ax.transAxes)
        y = 0.80
        for a, pr in sorted(lanes[lane], key=lambda z: -z[1]):
            h = 0.06 + eff[a] * 0.7
            ax.add_patch(FancyBboxPatch((x+0.015, y-h), 0.25, h,
                         boxstyle="round,pad=0.006", transform=ax.transAxes,
                         facecolor=cols[lane], edgecolor="white", alpha=0.85))
            ax.text(x+0.14, y-h/2, f"{a}\n{eff[a]*100:.0f}% of effort",
                    ha="center", va="center", fontsize=8, color="white",
                    transform=ax.transAxes)
            y -= h + 0.025
    T.titlecard(ax, "Sequenced roadmap",
                "chip height = share of effort; the needs-foundations lane is the bridge to the data layer")
    return _save(fig, "26_roadmap.png")
