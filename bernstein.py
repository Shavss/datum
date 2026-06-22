"""
bernstein.py - the framework encoded as data.
Source: Phil Bernstein, "Machine Learning: Architecture in the Age of Artificial
Intelligence" (RIBA, 2022). Figure 1.5.3 (task x stage grid) + 1.5.4 (AI).
Grid cross-validated against the book. The grid is the single source of truth;
each task's overall class and phase are derived from it.
"""
from collections import Counter
import numpy as np

SCALE = {"procedural": 1.00, "procedural-integrative": 0.75, "integrative": 0.50,
         "integrative-perceptive": 0.25, "perceptive": 0.00}
GROUPS = ["Practice Management", "Coordination", "Ideation / Design",
          "Technical Production", "Client / Regulatory"]

STAGES = ["Strategic Definition", "Preparation + Briefing", "Concept Design",
          "Spatial Coordination", "Technical Design", "Procurement",
          "Manufacturing + Construction", "Handover", "Use"]
NS = len(STAGES)

# service categories are groupings of stages (overlapping), (name, stages)
SERVICE_CATEGORIES = [
    ("Definition", [0, 1, 2]), ("Design", [1, 2, 3, 4]), ("Production", [3, 4]),
    ("Procurement", [5]), ("Construction", [6]), ("Operation", [8]),
]

TASK_ORDER = [
    ("Practice Management", "Obtaining work"),
    ("Practice Management", "Getting / assigning / managing staffing"),
    ("Practice Management", "Monitoring practice financial health"),
    ("Practice Management", "Setting business strategy"),
    ("Practice Management", "Managing practice operations"),
    ("Coordination", "Managing project staffing resources"),
    ("Coordination", "Assigning and coordinating work"),
    ("Coordination", "Maintaining budgets and schedules"),
    ("Coordination", "Coordinating consultants and others"),
    ("Ideation / Design", "Analysing and understanding the brief"),
    ("Ideation / Design", "Generating alternatives"),
    ("Ideation / Design", "Evaluating and selecting alternatives"),
    ("Ideation / Design", "Documenting design decisions"),
    ("Ideation / Design", "Resolving conflicting requirements"),
    ("Technical Production", "Determining conformance to the brief"),
    ("Technical Production", "Evaluating / integrating technical considerations"),
    ("Technical Production", "Performing engineering analysis"),
    ("Technical Production", "Evaluating and managing project costs"),
    ("Technical Production", "Coordinating spatial and technical systems"),
    ("Technical Production", "Producing technical documentation"),
    ("Technical Production", "Reviewing and approving technical documents"),
    ("Technical Production", "Reviewing construction progress"),
    ("Client / Regulatory", "Meeting / managing clients and decisions"),
    ("Client / Regulatory", "Coordinating with regulators"),
    ("Client / Regulatory", "Interfacing with public / communities"),
]

# task -> list of (class, [stages]); cross-validated against the book
_GRID_SPEC = {
    "Obtaining work": [("integrative-perceptive", [0, 1])],
    "Getting / assigning / managing staffing": [("integrative-perceptive", range(0, NS))],
    "Monitoring practice financial health": [("procedural-integrative", range(0, NS))],
    "Setting business strategy": [("integrative", range(0, NS))],
    "Managing practice operations": [("integrative-perceptive", range(0, NS))],
    "Managing project staffing resources": [("integrative-perceptive", range(0, NS))],
    "Assigning and coordinating work": [("integrative-perceptive", range(0, NS))],
    "Maintaining budgets and schedules": [("integrative", range(0, NS))],
    "Coordinating consultants and others": [("integrative", range(0, NS))],
    "Analysing and understanding the brief": [("perceptive", [0, 1, 2, 3]), ("integrative", [4])],
    "Generating alternatives": [("perceptive", [2]), ("procedural-integrative", [3, 4])],
    "Evaluating and selecting alternatives": [("perceptive", [2]), ("integrative", [3, 4])],
    "Documenting design decisions": [("procedural-integrative", [2, 3]), ("procedural", [4, 5, 6])],
    "Resolving conflicting requirements": [("perceptive", [2]), ("integrative-perceptive", [3, 4, 5, 6])],
    "Determining conformance to the brief": [("procedural-integrative", [2, 3, 4])],
    "Evaluating / integrating technical considerations": [("perceptive", [2]), ("procedural-integrative", [3, 4])],
    "Performing engineering analysis": [("procedural-integrative", [2, 3, 4, 5, 6])],
    "Evaluating and managing project costs": [("procedural-integrative", [1, 2, 3, 4, 5, 6])],
    "Coordinating spatial and technical systems": [("procedural-integrative", [3, 4, 5, 6])],
    "Producing technical documentation": [("procedural", [3, 4, 5])],
    "Reviewing and approving technical documents": [("integrative", [3, 4, 5, 6])],
    "Reviewing construction progress": [("procedural-integrative", [5, 6])],
    "Meeting / managing clients and decisions": [("integrative-perceptive", range(0, NS))],
    "Coordinating with regulators": [("integrative-perceptive", [0, 1, 2, 3, 4, 5, 6])],
    "Interfacing with public / communities": [("integrative-perceptive", range(0, NS))],
}

TASK_STAGE = {}
for _task, _spec in _GRID_SPEC.items():
    cells = {}
    for _cls, _stages in _spec:
        for _s in _stages:
            cells[_s] = _cls
    TASK_STAGE[_task] = cells


def _dominant_class(cells):
    counts = Counter(cells.values())
    top = max(counts.values())
    cands = [c for c, n in counts.items() if n == top]
    return min(cands, key=lambda c: SCALE[c])


def _mean_phase(cells):
    s = list(cells)
    return (sum(s) / len(s)) / (NS - 1)


def task_classes(task):
    """All distinct classes a task carries (in automatability order)."""
    cs = set(TASK_STAGE[task].values())
    return sorted(cs, key=lambda c: -SCALE[c])


TASKS = [(g, t, _dominant_class(TASK_STAGE[t]), _mean_phase(TASK_STAGE[t]))
         for (g, t) in TASK_ORDER]

AI_PROPOSALS = {
    "Obtaining work": dict(goal="Win more of the right work", metric="Win rate",
        ai="Scores prospects and tags the projects most likely to be won"),
    "Getting / assigning / managing staffing": dict(goal="Use staff well across jobs",
        metric="Staff utilisation", ai="Proposes staffing from past projects and flags problems"),
    "Monitoring practice financial health": dict(goal="Protect financial health",
        metric="Profit and overhead", ai="Reads past records, supports fee proposals, flags at-risk jobs"),
    "Maintaining budgets and schedules": dict(goal="Keep time, staff and money aligned",
        metric="Hourly rate, target profit, utilisation", ai="Forecasts overruns and recommends corrections"),
    "Coordinating consultants and others": dict(goal="Keep consultant work accurate and on time",
        metric="Deliverable schedules", ai="Watches submission timing and detail and flags gaps"),
    "Generating alternatives": dict(goal="Open up the solution space",
        metric="Number of viable alternatives", ai="Suggests variables from project type and past schemes"),
    "Evaluating and selecting alternatives": dict(goal="Find the strongest options",
        metric="Number of viable alternatives", ai="Weighs trade-offs, adds an objective read on options"),
    "Determining conformance to the brief": dict(goal="Confirm the design meets the brief",
        metric="Variance from brief parameters (area, budget, volume)", ai="Maps deliverables to brief targets, flags gaps"),
    "Evaluating and managing project costs": dict(goal="Stay within the construction budget",
        metric="Target value vs cost budget", ai="Generates estimates, recommends cost-alignment strategies"),
    "Coordinating spatial and technical systems": dict(goal="Make systems work together in 3D",
        metric="Valid conflicts and interferences", ai="Finds clashes, clears trivial ones, proposes fixes"),
    "Reviewing construction progress": dict(goal="Keep build progress aligned to schedule and payments",
        metric="% completion, installation accuracy", ai="Reads site inputs and flags installation discontinuities"),
    "Coordinating with regulators": dict(goal="Meet regulatory constraints",
        metric="Permits and approvals achieved", ai="Checks code conformance and recommends variances"),
}

# group-level influence kept for now; will likely be replaced in iteration 3.
GROUP_INFLUENCE = np.array([[0,3,1,1,1],[1,0,2,3,1],[0,1,0,3,2],[0,1,1,0,1],[0,1,2,1,0]], dtype=float)


# Strength of each proposed AI, graded by what it DOES (read off the verbs in
# AI_PROPOSALS): informs/flags/scores ~0.35, augments/recommends ~0.55,
# generates/clears/fixes ~0.75+. Judgement, editable, and the second
# automatability signal alongside the cognitive class in SCALE. Only tasks with
# a proposal appear; absence is not evidence against automatability.
PROPOSAL_STRENGTH = {
    "Obtaining work": 0.35,                              # scores and tags
    "Getting / assigning / managing staffing": 0.55,     # proposes and flags
    "Monitoring practice financial health": 0.50,        # reads, supports, flags
    "Maintaining budgets and schedules": 0.60,           # forecasts, recommends
    "Coordinating consultants and others": 0.40,         # watches, flags
    "Generating alternatives": 0.70,                     # generative
    "Evaluating and selecting alternatives": 0.55,       # weighs trade-offs
    "Determining conformance to the brief": 0.50,        # maps, flags gaps
    "Evaluating and managing project costs": 0.70,       # generates estimates
    "Coordinating spatial and technical systems": 0.80,  # finds and clears clashes
    "Reviewing construction progress": 0.45,             # reads, flags
    "Coordinating with regulators": 0.50,                # checks, recommends
}
