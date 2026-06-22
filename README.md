# Datum

A quantitative workflow diagnostic for architecture and engineering practices.
Second iteration.

Datum takes a description of how a practice delivers work and produces measured
evidence about it, then translates that evidence into plain language for a
non-technical audience. The point is to put numbers under a technology
conversation rather than opinion.

## What is new in this iteration

- The automatability of each task is no longer invented. It is read from Phil
  Bernstein's *Machine Learning: Architecture in the Age of Artificial
  Intelligence* (RIBA, 2022), Figure 1.5.3, and his proposed AI applications and
  metrics from Figure 1.5.4. Both are encoded in `bernstein.py`.
- The code is split into clean modules instead of one script.
- Every view is a separate, themed figure. Nothing is crammed into multi-panel
  grids.
- The report now states, per task, the recommended action, Bernstein's proposed
  AI application, and the metric to track.

## Structure

    bernstein.py   the framework as data: task taxonomy, five-band class per
                   task (Fig 1.5.3), and goal / metric / proposed AI (Fig 1.5.4)
    rnm.py         derives the task grouping from the grid (Eber 5.3.4), with
                   the block count read from the eigen-gap; nothing imposed
    sensitivity.py higher-order Vester roles (Eber 4.2) from the flow
    activities.py  the work-activity layer: our categories mapped to the
                   Bernstein tasks, with task-to-task flow and influence
    tooling.py     the 2026 layer: computation type, autonomy, and the
                   2022->2026 trajectory per task
    cost.py        cost per stage measured from timesheets x band rate, the
                   released capacity, and the margin/growth conversion
    SERVICE.md     how Datum is sold as an AI-readiness diagnostic
    inputs.py      client input schema (validated) separating data from logic
    tests.py       validation and engine checks
    example_client/ a worked client config (inputs.yaml + timesheet.csv)
    model.py       the engine: Workflow, Markov steady state, sensitivity,
                   MacLeamy, current vs future. No plotting.
    theme.py       one shared visual language for every figure
    views.py       one function per standalone figure
    run.py         entry point: prints the report, writes every figure
    figures/       generated output

## Cost impact (v6)

The business case, split into a measured part and a projected part. Cost per RIBA
stage is hours times band cost rate, summed over the people who booked to the
stage, which is real once the timesheet export drops in. The released capacity on
top is automatability times autonomy times adoption, run as low, expected and high
bands. Because the band rate is salary cost, the figure is the salaried cost of
freed capacity, booked only if hours fall or the time is redeployed into fee.
Computation type (which kind of AI) and autonomy (how end-to-end) are separate
axes, so agentic tools top autonomy while staying cognitive in type.

## The 2026 trajectory (v5)

Datum is a trajectory, not a single snapshot. Each task carries its AI computation
type in 2022 and in 2026 (algorithmic, empiricist, cognitive, climbing to agentic
RAG), a separate axis from automatability, plus the human-AI relationship. The
climb up the ladder is the opportunity, and because the upper rungs are cognitive
and agentic-RAG tools that run on the firm's own data, the trajectory doubles as
the argument for getting that data in order.

## Work-activity layer (v4)

RIBA stages are a contractual sequence, not how work moves, so flow and influence
over them came out near-acyclic. v4 adds a layer of about ten work activities,
each a partition of the Bernstein tasks, with flow and influence authored
task-to-task so the rework loops are real. Effort is the Markov steady state of
that flow. Automatability is inherited from the Bernstein class and then lifted by the
strength of the task's proposed AI (Bernstein 1.5.4), upward only, so an existing
AI intervention raises automatability where the class alone understates it. These
are the v1-style views (influence graph, flow with rework, four-quadrant map),
now anchored to the ground truth and at a grain that reads cleanly.

## Where the grouping comes from

The task grouping is no longer Bernstein's five groups taken as given. It is
derived from the grid by the RNM algorithm (Eber 5.3.4), and the number of
blocks is read from the eigen-gap rather than chosen, so the data decides it.
Three adjacencies were built from the grid and compared. Grouping by when work
happens leaves the practice inseparable, because the management, coordination
and client work spans the whole lifecycle and binds it. Grouping by how
automatable the work is gives three clean blocks, Automate, Augment and Protect,
which is the grain the AI opportunity map uses. The inseparability result is
kept as the reason freed capacity is reinvested across the system rather than
banked in one stage.

## Two levels, on purpose

The two halves of the method have different data appetites, so they run at
different grains.

The classification views (automatability, MacLeamy, current vs future, the
proposed-AI report, the opportunity map) run on the full task list, because they
need only per-task attributes, which are cheap. Group effort from the Markov
steady state is distributed across each group's tasks; an even split is the
placeholder a real timesheet split replaces.

The flow views (stage flow, effort, convergence) run on the nine sequential RIBA
stages, where timesheets are tagged. The higher-order systemic view runs there
too: active and passive sums, criticality and recursiveness are derived from the
measured stage flow (Eber 4.2), not an elicited matrix, then pushed onto the
tasks through the grid so the intervention map can place each task by routineness
and criticality at once. An elicited influence matrix, at whatever grain a
workshop prefers, would slot in as the alternative input the same maths runs on.

## Honesty of inputs

Three kinds of input, and you must always say which is which.

Measured: the group transition matrix and the effort shares can come from logged
time data. Elicited: the group influence matrix comes from a workshop, so the
sensitivity view is structured judgement made rankable, not measurement. Read
from the book: the task classes and proposed AI come from Bernstein, so they
carry his reasoning rather than yours, and should be checked against the source.

The freed capacity is always reported as redeployable into non-routine work, not
as a saving, to stay clear of Bernstein's productivity-fee trap.

## Use

    pip install -r requirements.txt
    python run.py

## What Bernstein's figures are, and what this adds

Figure 1.5.3 is a static, qualitative classification of architectural work.
Figure 1.5.4 lists proposed AI applications for a subset of tasks. Datum keeps
both as its automatability and intervention layer and adds the measured effort,
the systemic influence, the flow with rework loops, and the current-versus-
future simulation on top. The book classifies. This measures and simulates.


## Running with client data

The framework lives in code and is the same for every firm. A firm's own numbers
come through inputs.py, validated on load:

    python run.py example_client/inputs.yaml

The config carries the timesheet (inline or a CSV path), band cost rates, the fee
multiplier, the adoption bands, and any elicited autonomy overrides. Anything
omitted falls back to a labelled default. Validation rejects unknown bands or
stages, negative rates or hours, and bad adoption values, and warns on stages
with no booked hours. Run `python tests.py` for the checks.
