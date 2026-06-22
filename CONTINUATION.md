# Datum - continuation brief (for iteration 3)

Paste this into the new chat, and upload `datum_v2.zip`, to pick up cleanly.

## What Datum is
A quantitative workflow diagnostic for architecture and engineering practices.
It takes how a practice delivers work and produces measured evidence: where
effort goes, which work is automatable versus must stay human, how the system
flows, and what changes if you intervene. It is the evidence layer under an
Innovia AI advisory engagement. Positioning: numbers, not opinion.

## Theoretical spine (now established, not invented)
- Classification: Phil Bernstein, *Machine Learning: Architecture in the Age of
  AI* (RIBA 2022), Figures 1.5.3 (task x stage class grid) and 1.5.4 (goal /
  metric / proposed AI). Encoded in `bernstein.py`, cross-validated against the
  book.
- Systemic + flow analysis: Eber, *Project Management² - Platform Oriented
  Management* (TUM), Cross-Impact Higher Order + Equilibrium. Our stage-flow
  steady state IS his equilibrium-via-T (eigenvector of the column-normalised
  transition). Our sensitivity IS his first-order active/passive sum. The
  tunnel-boring-machine task is our convergence check.

## Current architecture (v2.4, in datum_v2.zip)
- `bernstein.py`  task x stage GRID = single source of truth; per-task class and
  phase derived from it; multi-class tasks supported; 1.5.4 proposals attached.
- `rnm.py`  derives the task grouping from the grid (Eber 5.3.4). Three grid
  adjacencies (cooccurrence / class / blend); block count from the eigen-gap
  (Eber 2.3.1 Remark 2); validated on Eber's 5.4.1 toy nets. Adopted grouping is
  the class-affinity one: three blocks, Automate / Augment / Protect.
- `timesheets.py`  DUMMY stage hours + stage transition. Flow and effort run
  over the 9 sequential RIBA stages (not task groups), because stages are
  sequential and timesheets are stage-tagged. Real Rapport3/Deltek extracts
  replace both.
- `model.py`  engine: steady_state, stage_effort, task_catalogue (stage effort
  split across active tasks), task automatability = MEAN across its cells.
- `theme.py` shared styling; `views.py` one standalone figure each; `run.py`.

## Honesty-of-inputs (always state which is which)
- Measured: stage effort + stage transition (from timesheets; dummy now).
- Read from the book: task classes + proposed AI (Bernstein; verify cells).
- Elicited: any influence matrix (workshop). Report freed capacity as
  redeployable into non-routine work, NEVER as a fee saving (productivity trap).

## Most impactful next steps (after v6), in order
0a-0e. DONE: RNM grouping, higher-order sensitivity, work-activity layer,
   proposed-AI automatability signal, the 2026 trajectory, and (v6) the cost
   layer with the type/autonomy split.
1. **Real data is now the gating item, and the drop-in is simple.** Replace the
   dummy TIMESHEET (hours by band by stage) and RATE_BY_BAND (salary-cost rates)
   in cost.py with the firm export. Cost per stage then becomes measured. Person
   grain rolls up to band x stage with no loss because the rate is per band.
2. **Saving-rate calibration**: anchor the automatability x autonomy product to
   published AI productivity benchmarks where they exist, and pressure-test the
   adoption bands and the autonomy scores in the client workshop.
3. **Method note for Rowley**: the spine is now complete (RNM grouping, activity
   flow, higher-order sensitivity, proposal-adjusted automatability, the
   2022->2026 trajectory, the cost model). Write it.

## Axes, kept distinct (so the model stays coherent)
- automatability: can AI do the cognitive work (Bernstein class + proposed-AI lift)
- autonomy: how end-to-end the tool is (assistive -> autonomous); drives saving
- computation type: which kind of AI (algorithmic / empiricist / cognitive), categorical
- human-AI label (Supporting/Automating/Collaborating): a summary of automatability, not an input
- systemic criticality: risk to change (Vester, activity influence)
- effort and cost: where time and money go (timesheets)

## Validity stance (settled with Kacper)
Lead with the core: classification under measured effort, the opportunity map.
The systemic layer (influence graph, sensitivity) is a second lens for
sequencing what is risky to change, explicitly elicited, never presented as
measured. Vester is contested in the literature, so frame criticality as
structured judgement made comparable, not objective fact. Eliciting numbers from
the workshop is legitimate and is the billable value, not a weakness.

## Still open / to verify
- Grid cell values are read from the figure; spot-check any ambiguous ones.
- Even-within-stage task effort split is a placeholder for real timesheet detail.
- Pure procedural (~6%) vs automate-with-oversight (~21%) must be kept separate
  in any headline, or the automatable share is overstated.
- Discussion point worth carrying: a single task can carry multiple classes at
  the SUB-ACTIVITY level (e.g. analysing the brief = procedural extraction via
  RAG/PydanticAI + perceptive interpretation). The book predates this; current
  tooling has shifted the line, which is the advisory differentiator.

## Source PDFs to bring to the new chat (coursework)
- ESSENTIAL: `04_05 Cross-Impact - Higher Order` (RNM algorithm, higher-order
  AS/PS, equilibrium, TBM) - the implementation source for both priority builds.
- ESSENTIAL: `03 Stakeholder Analysis and CI` (first-order cross-impact, Vester
  role definitions, adjacency-matrix construction) - the sensitivity foundation.
- OPTIONAL: `02 Fundamentals` (the DES / C-matrix model both build on).
- Not needed now: 01 Intro, 06 Success, 07/08 Organisation, 09/10 Scheduling.
  Keep `11 Complexity` in reserve for the method note's coupling argument.

## Value Stream Mapping (the practitioner-facing wrapper)
VSM is the legible framing for an AEC audience, not a separate method. The stage
flow IS a value-stream map of the practice; the rework loops are the waste a VSM
exposes; current-vs-future is the VSM current-state/future-state convention. A
normal VSM assumes linear flow and cannot represent feedback or rework, which is
exactly the gap the cross-impact and equilibrium maths fills. Headline line:
Datum is a value-stream map with the loops and indirect effects a normal VSM
cannot see. Use VSM vocabulary when presenting; use Eber/Vester + Bernstein for
the rigour underneath.

## Working preferences
No em dashes; UK English; plain prose, no chained lists-of-three; clarifying
question before big builds; honest/direct over reassuring; each figure stands
alone (never combined); build in repo, deliver via zip + standalone figures.

## Deferred deliverable
The method note for Rowley: frame Datum as a deliberate operationalisation of
Bernstein (classification) + Eber/Vester (systemic analysis), carrying the
data-asks, the honesty-of-inputs split, the current-vs-future logic, and the
stopping rule. Write it once grouping is RNM-derived so the numbers are final.
