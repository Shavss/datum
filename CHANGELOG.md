# Changelog

## v6.3 - service-grade input schema and tests

- Added inputs.py, the client input schema. The boundary between fixed
  methodology and one engagement is now explicit: the framework stays in code,
  while the firm's measured data (timesheet hours by band by stage, band cost
  rates) and elicited assumptions (adoption bands, tool autonomy, fee multiplier)
  come through a validated ClientInputs loaded from YAML or JSON, with the
  timesheet as inline rows or a CSV path.
- Validation rejects what would silently corrupt the numbers (unknown band or
  stage, negative rate or hours, adoption out of [0,1] or out of order) and warns
  on what is merely incomplete (a stage with no booked hours, tasks left on
  default autonomy). A schema that does not reject bad data is decoration.
- cost.py no longer holds firm data. It reads from a swappable INPUTS via
  cost.set_inputs(...), defaulting to a labelled dummy set so the demo still runs.
  Numbers are unchanged on the default data.
- run.py takes a client file: `python run.py example_client/inputs.yaml`.
- Added example_client/ (inputs.yaml + timesheet.csv) and tests.py (validation
  and engine-reads-injected-inputs checks; 7 passing).

## v6.2 - capacity conversion, roadmap, and the service framing

- Closed the conceptual hole. The model produces released hours, not booked
  money, so the output no longer claims a saving. A conversion step (cost.py)
  splits released capacity into two routes, each with its precondition: the
  margin route (salary cost avoided, needs fewer hours, in the firm's control)
  and the growth route (extra fee from re-selling freed time, worth more per hour
  but needs a pipeline). Doing neither reabsorbs the time and books nothing.
  Figure 25 shows the fork; the output is a decision, not a promise.
- Added the sequenced roadmap (26): act now where capable tooling runs on project
  data, watch where value or tooling is not there yet, needs foundations where the
  AI needs the firm's own data first. The needs-foundations lane is the bridge to
  the data engagement. A firm-data-dependence flag (tooling.needs_firm_data) drives
  the split, read from the proposal text.
- Added SERVICE.md: Datum positioned as the instrument in a structured
  AI-readiness diagnostic, with the elicitation as the billable value, the
  deliverable set, and the land-and-expand commercial shape into the data layer.

## v6.1 - cost base measured from timesheets, not allocated

- Rebuilt cost.py to the real data grain. Cost per RIBA stage is now hours times
  band cost rate, summed over the people who booked to that stage: four bands on
  one stage are four lines that add. That is arithmetic on the firm's data once
  the dummy TIMESHEET (hours by band by stage) and RATE_BY_BAND (salary-cost
  rates) are replaced by the export.
- The cost base is measured; the saving is a labelled projection on top. The
  releasable fraction of a stage is the mean over the tasks active in that stage
  of automatability times autonomy, taken up by adoption (low / expected / high).
- Honest framing kept in the output: the rate is salary cost, so the figure is
  the salaried cost of capacity released, booked only if hours fall or the time
  is redeployed into fee. Not called booked profit.
- New view, who the AI frees (24): released capacity by band. It concentrates in
  the mid bands doing automatable production work, not evenly across seniority.
- Figure 21 is now per RIBA stage. Dummy run: measured base £2.56M/yr, released
  capacity £0.41M/yr expected, £0.23M-£0.60M band.

## v6 - cost impact, and type vs autonomy split

- Added `cost.py`. The map becomes a costed business case. The fraction of a
  task's hours an AI removes is modelled as automatability x autonomy x adoption,
  applied to hours per activity and a charge-out rate, rolled up to money saved
  per activity and in total. Adoption is run as low / expected / high bands, since
  the rate is the load-bearing assumption. Hours and rates are dummy in a CONFIG
  block, structured so real timesheet and resourcing data drops straight in.
  Dummy run: £5.4M base, ~£1.1M/yr saved at expected adoption (£0.6M-£1.6M band).
- Fixed the computation-type ladder, which wrongly stacked agentic RAG above
  cognitive. Type and autonomy are now separate. Computation type is categorical
  (algorithmic, empiricist, cognitive); autonomy is the real ladder (assistive to
  autonomous), and agentic tools top autonomy while staying cognitive in type.
  `tooling.AUTONOMY_2026` scores it from the 2026 proposals.
- The climb (19) now plots autonomy 2022 to 2026; the readiness map (20) uses
  autonomy on the vertical axis; a new type-shift figure (23) tells the
  algorithmic-to-cognitive story as categories.
- New figures: cost saved per activity (21) and the adoption band (22).
- Checked the label-vs-class correlation: the human-AI label is almost perfectly
  predicted by the Bernstein class (Automating 0.80 mean auto, Supporting 0.35,
  Collaborating 0.29, no exceptions), so the label is a readable summary of
  automatability, not an independent savings input. The savings model is driven by
  automatability and autonomy instead.
- Pruned the stage flow (01) and stage sensitivity (13) figures, superseded by
  the activity-grain versions, since stages are a contractual sequence not a work
  flow.

## v5 - the 2026 layer: Datum becomes a trajectory

- Added `tooling.py`. Each task now carries where its AI sat in 2022 and where it
  sits in 2026, classified by computation type, plus the human-AI relationship
  label (Supporting / Automating / Collaborating) and the 2026 proposal and
  metric. Datum is no longer a single 2022 snapshot; the movement between the two
  is the product.
- Computation type is scored on a ladder: Algorithmic 1, Empiricist 2, Cognitive
  3, with combinations above their strongest single type (agentic-RAG at the
  top, level 4). It is a SEPARATE axis from automatability: it says how the AI
  computes, not how much of the task it takes over. Clash detection is
  algorithmic yet fully automating; a client-meeting agent is cognitive yet stays
  human-led.
- Two figures. The climb (19): every task's 2022 to 2026 move up the ladder,
  grouped by function, coloured by relationship. The readiness map (20):
  automatable in principle across, against how capable the tooling is now up,
  bubble = effort, at the activity grain.
- Finding: most tasks climb hard into Cognitive and agentic-RAG, which run on the
  firm's own structured data, so climbing the ladder presupposes the firm's data
  is in order. That is the bridge from this map to a data-infrastructure
  recommendation. One task (Evaluating and selecting alternatives) scores
  slightly down, an honest flag that its 2022 input classification is debatable.
- The named tools are the perishable evidence under the durable computation-type
  structure, and should be refreshed rather than treated as fixed.

## v4.1 - proposed AI as a second automatability signal

- `bernstein.PROPOSAL_STRENGTH` grades each Bernstein 1.5.4 proposal by what the
  AI actually does (informs/flags ~0.35, augments/recommends ~0.55,
  generates/clears/fixes ~0.75+). `model.composite_auto` lifts the cognitive
  class toward that strength where the proposal is stronger, and only upward, so
  a missing proposal never counts against a task. This replaces the hand-coded
  tooling deltas with an adjustment grounded in Bernstein's own proposal column.
- The proposal carries information independent of class: five judgement-heavy
  tasks have a proposal (winning work, staffing, generating and selecting
  alternatives, regulators), three procedural ones do not, so the lift lands
  where it should (the non-routine work an AI intervention now reaches).
- The task-grain opportunity map (12) now shows, per task, the class baseline,
  a green arrow to the proposal-adjusted automatability, and the proposed AI
  itself on the right. A proposed-AI table is added to the report.
- SCALE and GROUPS are unchanged and still the backbone.

## v4 - work-activity layer; flow and influence over real work, not stages

- Added `activities.py`. The diagnostic now has a work-activity layer: about ten
  categories chosen to reflect the work the practice actually does, each mapping
  to a partition of the 25 Bernstein tasks, so automatability stays anchored to
  the published classification while flow and influence run task-to-task between
  activities. This fixes the v2/v3 weakness that RIBA stages are a contractual
  sequence, not how work moves, which made the systemic analysis near-acyclic.
- Effort is the Markov steady state of the activity flow, giving a realistic
  shape (Technical Design 28%, a rework-heavy middle, light tails), rather than
  the even task split that inflated overhead before.
- Automatability is inherited from the Bernstein class, plus a labelled 2026
  tooling shift (`TOOLING_SHIFT`) where generative and CV tooling have moved past
  the 2022 book: Generating alternatives +0.30, and four others. This answers the
  point that an existing AI proposal is itself evidence of automatability, and it
  is the advisory differentiator: the book's line has moved.
- Five activity-grain figures (14-18), all clean at about ten nodes, the v1
  legibility restored: workflow with rework loops, the influence graph (node size
  = higher-order criticality), the four-quadrant intervention map, the AI
  opportunity map (tooling-shift arrows and Bernstein proposal counts), and the
  activity sensitivity plane.
- Reading: Technical Design is the critical hub and the biggest effort sink,
  highly automatable but risky to change because the rework loops run through it;
  Briefing & Concept and Client & Approvals are the active levers; generative
  tooling lifts Briefing & Concept the most.
- Honesty of inputs is explicit per layer: effort measured-in-principle,
  automatability classified judgement, flow and influence and tooling elicited
  (the numbers a client workshop fills in).

## v2.5 - higher-order sensitivity, derived from flow (iteration 4, step 1)

- Added `sensitivity.py`. Systemic roles (active / passive / critical / buffering)
  now come from the MEASURED stage flow, not an elicited influence matrix. Active
  and passive sums are taken from the cumulated A + A^2 + ... + A^m, so they carry
  indirect effects and loops (Eber 4.2), with the diagonal read as recursiveness
  (loop involvement). A convergence-grade stopping rule replaces a fixed guess.
- Restored the two graphs from v1, with more rigour and no synthetic data:
  - `13_sensitivity_plane.png`: the Vester plane on the nine RIBA stages, bubble
    size = recursiveness, faint ghost + arrow = drift from first order to the
    converged grade.
  - `06_intervention_map.png` rewritten as the four-quadrant map: routineness
    across (can AI do it) against systemic criticality up (is it risky to change),
    bubble = effort, colour = the RNM block. Criticality is pushed from stages
    onto tasks through the grid.
- Finding: the stage flow is near-acyclic (converges at grade 7, only small
  first-to-higher-order drift). Strategic Definition is the pure driver, the
  early-to-middle stages are critical and loop-heavy (recursiveness peaks at
  Preparation and Concept), Use is inert. Higher order mostly confirms first
  order here and flags the rework-entangled stages to stabilise first.
- Two grains delivered as asked: the stage plane (derived) and the task
  intervention map (inherited). The practitioner-step v1 look would need an
  elicited matrix and is left as an option.
- Retired the `ACTION` dict; action labels come solely from the threshold band in
  `model.py`. Softened the reinvestment note to one caveat line, focus kept on
  automation and AI usage.

# Changelog

## v2.4 - grouping derived by RNM, not imposed (iteration 3, step 1)

- Added `rnm.py`. The task grouping is now derived from the grid by the RNM
  algorithm (Eber 5.3.4), instead of taking Bernstein's five groups as given.
  The number of blocks is read from the eigen-gap (Eber 2.3.1 Remark 2), so the
  data chooses it. Validated first against Eber's own 5.4.1 toy networks
  (recovers 1, 2, 2 segments).
- Three honest task-to-task adjacencies, all built from the grid: cooccurrence
  (shared stages), class (shared automatability), blend (both). Built all three
  and compared, since the construction decides the result.
- Finding: by WHEN work happens (cooccurrence) and under the blend, the practice
  does not separate at all (one block); the always-on management, coordination
  and client work binds the lifecycle. By HOW automatable the work is (class),
  the data supports THREE blocks (Automate 0.74 / Augment 0.41 / Protect 0.24),
  agreeing with Bernstein's five only at Rand 0.70, so it reorganises rather
  than relabels. The three-block class grouping is adopted as the opportunity-map
  grain; the inseparability result is carried as the reinvest-across-the-system
  caveat.
- Three standalone figures added: RNM separation development (10), segments the
  data supports vs Bernstein's five (11), and the AI opportunity map (12).
- Report now prints the toy-net check, the three-construction comparison, and
  the recommended blocks with per-block effort and freed capacity.

## v2.3 - stage-based flow, multi-class tasks, corrected MacLeamy

- Adopted the cross-validated 9-column grid (Procurement column; obtaining work
  to concept design; assigning/coordinating work integrative-perceptive; the two
  procedural bands on documenting and producing documentation; regulators to
  construction).
- Flow and effort moved from task GROUPS onto STAGES, which run in sequence and
  match how timesheets are tagged. timesheets.py holds dummy stage hours and a
  stage transition; both are replaced by real Rapport3/Deltek extracts.
- Task effort is now the timesheet stage effort distributed across the tasks
  active in each stage, via the grid, instead of an even within-group guess.
- Multi-class tasks (generating alternatives, documenting design decisions,
  etc.) resolve by MEAN automatability across their cells, not a single label.
- MacLeamy corrected: it now plots measured effort by stage against a front-
  loaded reference, instead of collapsing each task to one mean-phase point.
- Brought back the intervention map and restored the explicit routine vs non-
  routine split in the report (derived from Bernstein's class).
- Group influence/sensitivity figures parked pending the iteration-3 framework.

## v2.2 / v2.1 / v2 / v1
See prior entries: grid verification, stage-resolved grid, Bernstein-grounded
modular rebuild, and the original single-file prototype (mapped to the TUM PM
coursework: systemic substructures, stakeholder influence, Markov steady state,
stability vs complexity, coupling cost).
