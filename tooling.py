"""
tooling.py - the 2026 layer (Datum v5).

This turns Datum from a single 2022 snapshot into a trajectory. Each task now
carries where its AI sat in 2022 and where it sits in 2026, classified by
computation type, plus the human-AI relationship label.

Computation type is a separate axis from automatability. It says HOW the AI
computes, not how much of the task it takes over. The ladder, from the bottom of
the source table:
    Algorithmic   deterministic, rule-based         level 1
    Empiricist    statistical / ML, learns patterns  level 2
    Cognitive     reasoning, inference, RAG, agents  level 3
    (combined)    agentic-RAG combines all three     level 4
Combinations score above their strongest single type, because the frontier tools
fuse them. This is the durable structure; the named products under each entry are
the perishable evidence and will need refreshing.

The Label (Supporting / Automating / Collaborating) is the human-AI relationship,
which is the degree-of-automation axis, distinct again from computation type.
"""

# task -> 2022 and 2026 state. comp strings are scored by comp_level().
LADDER_2026 = {
    "Getting / assigning / managing staffing": dict(
        label="Supporting", comp22="Algorithmic", comp26="Cognitive + Empiricist",
        ai26="Agentic RAG over historical timesheets; proposes staffing, surfaces skill gaps, flags utilisation risk",
        metric26="Staff utilisation %; skill-match score per project"),
    "Monitoring practice financial health": dict(
        label="Automating", comp22="Algorithmic", comp26="Cognitive + Empiricist",
        ai26="AI agents (Briq, Datagrid) across ERP and project data, flagging margin erosion",
        metric26="Profit margin %; at-risk jobs flagged vs resolved"),
    "Setting business strategy": dict(
        label="Supporting", comp22=None, comp26="Cognitive",
        ai26="LLM + RAG over market data, past fee records and sector benchmarks",
        metric26="Evidence-backed options surfaced; win rate trend"),
    "Managing practice operations": dict(
        label="Supporting", comp22=None, comp26="Cognitive",
        ai26="Orchestration agents monitoring workload, capacity and delivery status",
        metric26="Capacity utilisation %; overdue tasks flagged"),
    "Obtaining work": dict(
        label="Supporting", comp22="Algorithmic + Empiricist", comp26="Cognitive + Empiricist",
        ai26="Mercator-style AI tracking rezoning, permits and stakeholder relationships; ranks bids",
        metric26="Win rate %; bid pipeline conversion rate"),
    "Managing project staffing resources": dict(
        label="Collaborating", comp22=None, comp26="Algorithmic + Cognitive",
        ai26="AI scheduling agents (Karmen) auto-generating resource allocations from project models",
        metric26="Staff utilisation %; allocation conflicts resolved per sprint"),
    "Assigning and coordinating work": dict(
        label="Collaborating", comp22=None, comp26="Cognitive",
        ai26="Multi-agent orchestration: coordinator assigns to specialist agents and consolidates",
        metric26="Task completion rate; average handoff time"),
    "Maintaining budgets and schedules": dict(
        label="Supporting", comp22="Algorithmic", comp26="Empiricist",
        ai26="nPlan, SmartPM: ML on historical schedules; predicts delays, recommends corrections",
        metric26="Schedule variance %; forecast accuracy vs actual"),
    "Coordinating consultants and others": dict(
        label="Collaborating", comp22="Algorithmic", comp26="Cognitive + Empiricist",
        ai26="Agentic RAG over project documents (TrunkTools); monitors RFI/submittal logs, routes queries",
        metric26="Deliverable schedule adherence %; RFI response time"),
    "Documenting design decisions": dict(
        label="Automating", comp22=None, comp26="Empiricist + Cognitive",
        ai26="LLM with session memory (Notion AI, Claude Projects); captures design intent from voice or text",
        metric26="Decision retrieval rate; % of decisions traceable to brief"),
    "Resolving conflicting requirements": dict(
        label="Supporting", comp22=None, comp26="Cognitive",
        ai26="Graph RAG over brief and constraints; maps conflicts as a knowledge graph, surfaces contradictions",
        metric26="Conflicts identified vs resolved per stage"),
    "Analysing and understanding the brief": dict(
        label="Supporting", comp22=None, comp26="Cognitive",
        ai26="RAG over brief and precedents: extracts parameters, links to past projects, flags ambiguities",
        metric26="% of brief parameters extracted and cross-referenced"),
    "Generating alternatives": dict(
        label="Supporting", comp22="Algorithmic", comp26="Empiricist + Cognitive",
        ai26="Generative and parametric agents (ArkDesign.ai); layout options optimised for density, cost, carbon",
        metric26="Viable alternatives; carbon delta between options"),
    "Evaluating and selecting alternatives": dict(
        label="Supporting", comp22="Algorithmic + Cognitive", comp26="Cognitive",
        ai26="Multi-criteria agents: evaluate options against brief, carbon, cost, planning risk; scored matrix",
        metric26="Score variance across criteria; brief conformance % per option"),
    "Evaluating and managing project costs": dict(
        label="Automating", comp22="Algorithmic", comp26="Empiricist",
        ai26="Beam AI, Togal AI: read drawings, automate quantity takeoffs, generate estimates with QA",
        metric26="Target value vs cost budget; takeoff time vs manual"),
    "Performing engineering analysis": dict(
        label="Automating", comp22=None, comp26="Algorithmic + Empiricist",
        ai26="AI co-pilots in Autodesk and Rhino: run structural, energy and daylight simulations autonomously",
        metric26="Simulation iterations per hour; carbon delta between options"),
    "Coordinating spatial and technical systems": dict(
        label="Automating", comp22="Algorithmic", comp26="Algorithmic + Cognitive",
        ai26="Articulate, Structured AI: agents detect clashes and code issues, auto-generate RFIs",
        metric26="% clashes auto-resolved vs escalated; RFI generation time"),
    "Reviewing and approving technical documents": dict(
        label="Supporting", comp22=None, comp26="Cognitive",
        ai26="Document Crunch, Firmus: RAG review; flags risks, gaps and obligations across specs",
        metric26="Risk clauses flagged per document; review turnaround time"),
    "Determining conformance to the brief": dict(
        label="Automating", comp22="Algorithmic", comp26="Cognitive",
        ai26="Agentic RAG continuously mapping deliverables to brief, flagging drift, logging conformance",
        metric26="Variance from brief parameters; conformance log completeness"),
    "Evaluating / integrating technical considerations": dict(
        label="Supporting", comp22=None, comp26="Cognitive",
        ai26="LLM + knowledge graph over building regulations and past technical packages",
        metric26="% of applicable code clauses checked; gaps logged"),
    "Producing technical documentation": dict(
        label="Automating", comp22=None, comp26="Algorithmic + Empiricist",
        ai26="AI drafting agents auto-produce schedules, spec sections and annotations from BIM data",
        metric26="Time from BIM update to issued document; error rate vs manual"),
    "Reviewing construction progress": dict(
        label="Automating", comp22="Algorithmic", comp26="Empiricist",
        ai26="OpenSpace, Buildots, Track3D: computer vision maps site scans to BIM, flags deviations",
        metric26="% completion; deviation rate vs BIM model"),
    "Meeting / managing clients and decisions": dict(
        label="Collaborating", comp22=None, comp26="Empiricist + Cognitive",
        ai26="LLM meeting agents: transcription, summary and action-item extraction; client decision logs",
        metric26="Action item completion rate; decision log completeness"),
    "Interfacing with public / communities": dict(
        label="Collaborating", comp22=None, comp26="Empiricist + Cognitive",
        ai26="RAG-powered chatbots on project data; multimodal AI for public engagement visualisations",
        metric26="Query response accuracy; public engagement reach"),
    "Coordinating with regulators": dict(
        label="Collaborating", comp22="Algorithmic", comp26="Algorithmic + Cognitive",
        ai26="CertChain AI, Articulate: continuous planning and code compliance, auto-generated variance narratives",
        metric26="Permits and approvals achieved; compliance check turnaround time"),
}

_BASE = {"Algorithmic": 1.0, "Empiricist": 2.0, "Cognitive": 3.0}
LADDER_TICKS = {0: "none", 1: "Algorithmic", 2: "Empiricist", 3: "Cognitive", 4: "Agentic RAG"}
LABELS = ["Automating", "Supporting", "Collaborating"]


def comp_level(s):
    """Score a computation-type string on the 1-4 ladder. Combinations score
    above their strongest single type, since fused tools are the frontier."""
    if not s:
        return 0.0
    parts = [p.strip() for p in s.replace("+", ",").split(",")]
    vals = [_BASE[p] for p in parts if p in _BASE]
    if not vals:
        return 0.0
    return max(vals) + 0.5 * (len(vals) - 1)


def level_2022(task):
    return comp_level(LADDER_2026.get(task, {}).get("comp22"))


def level_2026(task):
    return comp_level(LADDER_2026.get(task, {}).get("comp26"))


def label_of(task):
    return LADDER_2026.get(task, {}).get("label")


if __name__ == "__main__":
    import bernstein as B
    print(f"{'task':42s} {'2022':>5} {'2026':>5}  {'label':12s} comp 2026")
    for _g, t in B.TASK_ORDER:
        d = LADDER_2026[t]
        print(f"{t:42s} {level_2022(t):5.1f} {level_2026(t):5.1f}  "
              f"{d['label']:12s} {d['comp26']}")


# --- autonomy: how end-to-end the 2026 tool is, separate from computation type.
# This is the real ladder (agentic RAG tops it and is still cognitive in TYPE).
# Graded from the 2026 proposal verbs: flags/checks ~0.4, recommends/surfaces
# ~0.55, generates/captures ~0.7, runs/auto-generates/continuous ~0.8.
AUTONOMY_2026 = {
    "Getting / assigning / managing staffing": 0.55,
    "Monitoring practice financial health": 0.60,
    "Setting business strategy": 0.40,
    "Managing practice operations": 0.50,
    "Obtaining work": 0.45,
    "Managing project staffing resources": 0.75,
    "Assigning and coordinating work": 0.70,
    "Maintaining budgets and schedules": 0.50,
    "Coordinating consultants and others": 0.60,
    "Documenting design decisions": 0.70,
    "Resolving conflicting requirements": 0.45,
    "Analysing and understanding the brief": 0.50,
    "Generating alternatives": 0.70,
    "Evaluating and selecting alternatives": 0.55,
    "Evaluating and managing project costs": 0.75,
    "Performing engineering analysis": 0.80,
    "Coordinating spatial and technical systems": 0.80,
    "Reviewing and approving technical documents": 0.40,
    "Determining conformance to the brief": 0.65,
    "Evaluating / integrating technical considerations": 0.45,
    "Producing technical documentation": 0.80,
    "Reviewing construction progress": 0.55,
    "Meeting / managing clients and decisions": 0.55,
    "Interfacing with public / communities": 0.55,
    "Coordinating with regulators": 0.65,
}
AUTONOMY_TICKS = {0.0: "none", 0.35: "assistive", 0.55: "recommends",
                  0.75: "generates", 0.9: "autonomous"}
TYPE_ORDER = ["Algorithmic", "Empiricist", "Cognitive"]
_TYPE_RANK = {t: i for i, t in enumerate(TYPE_ORDER)}


def autonomy_2026(task):
    return AUTONOMY_2026.get(task, 0.0)


def autonomy_2022(task):
    """2022 autonomy proxy: the strength of the 2022 proposal, 0 if none."""
    import bernstein as B
    return B.PROPOSAL_STRENGTH.get(task, 0.0) if LADDER_2026.get(task, {}).get("comp22") else 0.0


def types_in(s):
    if not s:
        return []
    return [p.strip() for p in s.replace("+", ",").split(",") if p.strip() in _TYPE_RANK]


def dominant_type(task, year=2026):
    s = LADDER_2026.get(task, {}).get("comp26" if year == 2026 else "comp22")
    ts = types_in(s)
    return max(ts, key=lambda t: _TYPE_RANK[t]) if ts else None


def type_composition(year):
    """Count of tasks per computation type for a year (a task with two types
    counts in both). For the type-shift story, told as categories not a height."""
    import bernstein as B
    out = {t: 0 for t in TYPE_ORDER}
    none = 0
    for _g, t in B.TASK_ORDER:
        ts = types_in(LADDER_2026[t].get("comp26" if year == 2026 else "comp22"))
        if not ts:
            none += 1
        for ty in ts:
            out[ty] += 1
    out["none"] = none
    return out


# Does the 2026 tool lean on the firm's OWN accumulated data (so it cannot work
# well until that data is in order)? Read from the proposal text. This is what
# separates "act now" tools that run on project artefacts from "needs
# foundations" tools that need the firm's history in a retrievable store.
_DATA_WORDS = ["historical", "past ", "knowledge graph", "records",
               "session memory", "project documents", "precedents",
               "timesheets", "benchmarks", "decision log"]


def needs_firm_data(task):
    ai = (LADDER_2026.get(task, {}).get("ai26") or "").lower()
    return any(w in ai for w in _DATA_WORDS)
