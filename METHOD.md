# Datum method note: every assumption, formula and constant

This is the one place where the whole calculation is written down so you and the
team can verify it. It is organised by the quantity produced, and for each one it
gives the formula, the inputs, where the input sits on the honesty-of-inputs
split, the constants involved, and the file and function that compute it. If a
number in a figure or the report looks wrong, it is specified here.

UK English, no rounding hidden: where a constant is a judgement call it is
labelled as one. Nothing in the pipeline is a black box.

## The honesty-of-inputs split, used throughout

Every input is one of three kinds, and the report states which is which.

- **Measured.** Arithmetic on the firm's data. The timesheet (hours by band by
  stage), the band cost rates, and everything derived from them (cost per stage,
  effort shares). Currently dummy; becomes real when the firm's export drops in.
- **Read from the book.** Phil Bernstein, *Machine Learning: Architecture in the
  Age of Artificial Intelligence* (RIBA, 2022), Figures 1.5.3 and 1.5.4. The task
  classes and the proposed AI applications. Carries his reasoning, not ours, and
  should be checked against the source.
- **Elicited.** Structured judgement from the workshop: tool autonomy, adoption
  bands, the work-flow and influence matrices, the 2026 tooling positions. Made
  comparable, never presented as measurement.

A fourth label, **placeholder**, marks a dummy that a real engagement replaces
(the even-within-stage effort split, the dummy timesheet, the elicited flow
matrices authored as realistic dummies).

---

## 1. The task classification (read from the book)

**Source.** `bernstein.py`. Bernstein Figure 1.5.3 is a task x RIBA-stage grid;
each cell carries one of five classes. The grid (`_GRID_SPEC`, then `TASK_STAGE`)
is the single source of truth. 25 tasks, 9 RIBA stages.

**The five-band class scale** (`B.SCALE`), the only place class becomes a number:

| class | value |
|---|---|
| procedural | 1.00 |
| procedural-integrative | 0.75 |
| integrative | 0.50 |
| integrative-perceptive | 0.25 |
| perceptive | 0.00 |

This is a linear, evenly-spaced reading of Bernstein's ordered five-band legend.
The even spacing is an assumption: it treats the gap between adjacent bands as
equal. If you think the bands are not evenly spaced, this table is the one place
to change it, and every automatability number moves with it.

**A task's class** when it carries more than one across its stages: the dominant
class is the most frequent, ties broken toward the *lower* automatability
(`_dominant_class`, `min` on `SCALE`). This is deliberately conservative: a tie
does not flatter the automatable side.

**A task's phase** (`_mean_phase`): the mean of its active stage indices,
normalised to [0, 1] by dividing by `NS - 1 = 8`. Used only to place tasks on the
MacLeamy time axis.

---

## 2. Task automatability (read from the book, then lifted by an elicited signal)

Two automatability numbers exist per task. Keep them distinct.

**Base automatability** `task_mean_auto(task)` (`model.py`): the **mean** of
`SCALE[class]` across the task's active cells. Mean, not max or min, so a
multi-class task is handled honestly rather than collapsed to one label.

**Proposal-adjusted automatability** `composite_auto(task, alpha=0.6)`
(`model.py`): the base lifted toward the strength of Bernstein's proposed AI for
that task, where the proposal is stronger than the class implies.

```
composite = base + alpha * max(0, proposal_strength - base)
```

- `alpha = 0.6` is a judgement constant: how much weight the proposed-AI signal
  gets over the raw class. Editable.
- **Upward only.** A missing proposal never lowers automatability, because
  Bernstein's 1.5.4 proposal list is not exhaustive (`if s is None: return c`).
  Absence of a proposal is not evidence against automatability.
- `proposal_strength` (`B.PROPOSAL_STRENGTH`) is graded by the **verbs** in
  Bernstein's proposal text: informs/flags/scores ~0.35, augments/recommends
  ~0.55, generates/clears/fixes ~0.75+. This is read-from-the-book evidence
  turned into a number by our judgement, so it is editable and should be
  spot-checked against the proposal wording in `B.AI_PROPOSALS`.

**Which one is used where.** The opportunity map, the cost saving rate, and the
activity "+prop" column use `composite_auto`. The headline routine/non-routine
split and the per-task class use `task_mean_auto`. The report says "automatability"
for both; if challenged, point to this section.

**The action label** `_action_from_auto(a)` (`model.py`), thresholds on
automatability:

| automatability a | action |
|---|---|
| a >= 0.875 | Automate |
| 0.625 <= a < 0.875 | Automate w/ oversight |
| 0.375 <= a < 0.625 | Augment |
| 0.125 <= a < 0.375 | Augment (human-led) |
| a < 0.125 | Protect (human only) |

These cut-points are the midpoints between the five `SCALE` values (0.875 is
halfway between 1.00 and 0.75, and so on), so the bands are the class bands, not
an independent choice. The headline keeps "pure procedural" (a >= 0.875) separate
from "automate with oversight" (0.625-0.875) on purpose; merging them overstates
the safely-automatable share.

---

## 3. Effort (measured, with one placeholder split)

**Stage effort** `stage_effort()` (`model.py`): stage hours divided by total
hours. Pure arithmetic on the timesheet. Measured.

**Task effort** `task_catalogue()` (`model.py`): each stage's effort is split
**evenly** across the tasks active in that stage, then summed per task. The even
split is a **placeholder** (`share = eff_stage[s] / len(active[s])`) that a real
per-task timesheet detail replaces. This is the single biggest placeholder in the
measured layer, and it is flagged wherever task effort is shown.

**Activity effort** `activity_table()` (`activities.py`): not a sum of task
effort. It is the **steady-state** of the elicited activity-flow matrix (section
6), i.e. where work accumulates in the long run, which is why a high-rework
activity like Technical Design carries more effort than its task count alone.

---

## 4. The current-vs-future simulation (projection)

`task_future(cat, aggressiveness=0.7)` (`model.py`):

```
future_effort = current_effort * (1 - automatability * aggressiveness)
```

- `aggressiveness = 0.7` is the headline adoption-style lever for the
  redeployable-capacity figure in the console report and the states figure. It is
  a judgement constant, separate from the cost model's adoption bands (section 5),
  and the report calls the result "redeployable capacity at 70%".
- "Freed" effort is `current.sum() - future.sum()`, always reported as
  redeployable into non-routine work, never as a fee saving (the productivity-fee
  trap).

Note there are **two** adoption-style levers in the codebase: `aggressiveness`
here (drives the effort-shift figures) and the `adoption` bands in section 5
(drive the cost figures). They are independent; do not assume they match.

---

## 5. The cost model (measured base, projected release)

**Source.** `cost.py`, with all firm-specific numbers injected via
`inputs.ClientInputs` (`inputs.py`), never hard-coded in `cost.py`.

**Measured cost base** `by_stage()`:

```
stage_cost = sum over timesheet lines in the stage of (hours * band_rate[band])
```

`band_rate` is **salary cost**, not charge-out, so the cost base is the salaried
cost of the work. Fully measured.

**Stage saving rate** `stage_saving_rate(s)`: the releasable fraction of a stage
before adoption is taken up:

```
rate = mean over tasks active in the stage of ( composite_auto(task) * autonomy[task] )
```

This is the product of the two axes: **automatability** (can AI do the cognitive
work, section 2, read-from-the-book + judgement) times **autonomy** (how
end-to-end the 2026 tool is, elicited per task, `tooling.AUTONOMY_2026`). Keeping
them as a product is the core modelling choice: a task that is automatable in
principle but has only assistive tooling releases little, and vice versa.

**Released capacity** `by_stage()`, per stage:

```
saved_hours = stage_hours * rate * adoption
saved_cost  = stage_cost  * rate * adoption
```

`adoption` is elicited, run as three bands (section 7). The release is a labelled
projection on top of the measured base; the report never collapses it to one
number.

**Conversion** `conversion(scenario)`: released hours are not money until
converted, by one of two routes:

```
margin_value = saved_cost                        # salary cost avoided (fewer hours)
growth_value = saved_cost * fee_multiplier       # freed time re-sold as fee
```

- `fee_multiplier` (default 2.8, elicited per firm) is charge-out over cost.
- Doing neither route reabsorbs the time and books nothing. The output is a
  decision, not a promise.

---

## 6. The systemic / flow analysis (Eber + Vester)

**Source.** Eber, *Project Management² – Platform Oriented Management* (TUM),
sections 4.2 (higher-order cross-impact) and 5.3.4 (RNM grouping). Two grains: the
9 RIBA stages (`sensitivity.py`, weighted by the measured stage transition) and
the 10 work activities (`activities.py`, weighted by the elicited influence
matrix).

**Steady state** `steady_state(transition)` (`model.py`): the equilibrium of a
row-stochastic flow, computed by power iteration (up to 2000 steps, tol 1e-14) and
cross-checked against the eigenvector of `transitionᵀ` for eigenvalue 1. This is
Eber's equilibrium-via-T. Used for stage effort distribution and for activity
effort.

**Influence weighting.** Both layers square the adjacency before cumulating
(`W ** 2`), Eber's variance-style weighting that emphasises strong handoffs over
weak ones. At the stage grain the adjacency is the measured stage transition with
the diagonal zeroed (`stage_influence`); at the activity grain it is the elicited
0-3 Vester matrix (`activity_influence`).

**Higher-order roles** `roles(W, m)` (`sensitivity.py`), on the cumulated matrix
`S = W + W² + ... + Wᵐ`:

- **Active sum (AS)** = row sums of S: how much a node drives others, indirect
  paths included.
- **Passive sum (PS)** = column sums of S: how much it is driven.
- **Recursiveness** = the diagonal of S: how far a node sits inside loops. At the
  stage/activity grain this is rework.
- **Criticality** = `AS * PS` (normalised), the quantity that sizes the nodes on
  the influence graph and places tasks on the intervention map.

**The grade m is not guessed.** `converged_grade(W)` increases m until the
max-normalised (AS, PS) stop moving (tol 1e-3), Eber's stopping rule. The
activity matrix is first scaled by `1 / (spectral_radius * 1.2)` so the cumulation
converges (spectral radius < 1).

**Role labels** `role_label`: a node is `critical` (high AS and high PS),
`active` (high AS only), `reactive` (high PS only), or `buffering` (neither),
split at the mean of AS and PS. Vester's quadrants.

**Caveat to state aloud.** Vester is contested in the literature. Criticality is
framed as structured judgement made comparable, a second lens for sequencing what
is risky to change, never as objective fact. At the activity grain the influence
matrix is elicited (dummy now), so the whole systemic layer there is elicited.

**The activity flow matrix** `activity_flow()` (`activities.py`): built from the
elicited `_FLOW_EDGES`, plus a 0.45 self-retention on the diagonal (work
continues within an activity) and a 0.10 back-edge from every activity to Practice
Management (light coupling), then row-normalised. The 0.45 and 0.10 are authored
constants in the dummy; a real workshop replaces the edge list.

---

## 7. The RNM grouping (data decides the number of blocks)

**Source.** `rnm.py`. Eber 5.3.4 (symmetrise, normalise, find submatrices) and
2.3.1 Remark 2 (the number of segments is the multiplicity of the dominant
eigenvalue).

**Nothing imposes the number of groups.** Three adjacencies are built from the
grid, each a different positioning choice:

- **cooccurrence** — Jaccard overlap of the stages two tasks share. Groups by
  *when* work happens.
- **class** — cosine similarity of the two tasks' class histograms. Groups by
  *how automatable* the work is. **This is the adopted one.**
- **blend** — per-shared-stage class agreement over the union of active stages.
  Groups by work that happens together *and* behaves alike.

**Block count** `segment_count(adj)`: the position of the largest gap in the top
eigenvalues of the symmetric-normalised operator `D^(-1/2) A D^(-1/2)`
(the eigen-gap). Read, not chosen.

**Clustering** `grouping(adj)`: k-means (own numpy implementation, 12 restarts) on
the row-normalised leading-k eigenvectors of the same operator.

**Validation** `_validate()`: the algorithm is run first on Eber's own 5.4.1 toy
networks and must return 1, 2, 2 segments before it is trusted on the grid. This
check prints at the top of the grouping report.

**Result, on the current grid.** Grouping by *when* leaves the practice as one
inseparable block (management, coordination and client work span the whole
lifecycle and bind it). Grouping by *how automatable* gives three clean blocks:
Automate, Augment, Protect. The inseparability result is kept as the reason freed
capacity is reinvested across the system, not banked in one stage.

**Agreement** with Bernstein's five groups is reported as a Rand index
(`rand_index`), a dependency-free partition-agreement measure.

---

## 8. The 2026 trajectory and computation type (elicited)

**Source.** `tooling.py`. Per task, where its AI sat in 2022 and 2026.

**Computation-type ladder** `comp_level(s)`: Algorithmic = 1, Empiricist = 2,
Cognitive = 3. A combination scores `max(values) + 0.5 * (count - 1)`, so fused
tools (agentic-RAG) score above their strongest single type, topping out around
level 4. This is the *type* of AI, a categorical axis, **not** how much of the
task it takes over.

**Autonomy** `AUTONOMY_2026[task]` in [0, 1]: how end-to-end the 2026 tool is,
graded from the proposal verbs (flags/checks ~0.4, recommends/surfaces ~0.55,
generates/captures ~0.7, runs/continuous ~0.8). Elicited, editable, and the
quantity multiplied into the cost saving rate (section 5). The 2022 autonomy proxy
is the strength of the 2022 proposal, 0 if none.

**Needs-firm-data flag** `needs_firm_data(task)`: true if the 2026 proposal text
mentions the firm's own accumulated data (`historical`, `past`, `knowledge graph`,
`records`, `precedents`, `timesheets`, etc.). This keyword test is what separates
the "act now" lane (tools that run on project artefacts) from the
"needs foundations" lane (tools that need the firm's history in a retrievable
store) on the roadmap. It is a coarse text match and should be eyeballed.

**Perishability.** The named products under each task date fast. They are the
perishable evidence under the durable type-and-autonomy structure, and need a
refresh cadence. The structure (the ladder, the autonomy axis) is durable; the
product names are not.

---

## 9. The axes, kept distinct (so the model stays coherent)

The model's coherence depends on not collapsing these. If two of them are ever
merged into one chart or one number, that is a bug, not a simplification.

| axis | question | source | where |
|---|---|---|---|
| automatability | can AI do the cognitive work | Bernstein class + proposed-AI lift | `composite_auto` |
| autonomy | how end-to-end is the tool | elicited per task | `AUTONOMY_2026` |
| computation type | which kind of AI | elicited, categorical | `comp_level` |
| human-AI label | summary relationship | derived label, not an input | `label_of` |
| systemic criticality | risk to change | Vester higher-order | `sensitivity` / `activities` |
| effort and cost | where time and money go | timesheets | `cost` / `model` |

The opportunity map is automatability x effort. The readiness map is
automatability x autonomy (2026). The climb is autonomy over time. The cost saving
rate is the *product* automatability x autonomy x adoption. None of these is a
restatement of another.

---

## 10. Every tunable constant, in one list

For a sensitivity check, these are the judgement constants. Change one, re-run,
see what moves.

| constant | value | meaning | file |
|---|---|---|---|
| `SCALE` band values | 1.00 / 0.75 / 0.50 / 0.25 / 0.00 | class to automatability | `bernstein.py` |
| `PROPOSAL_STRENGTH` | 0.35–0.80 per task | proposed-AI strength from verbs | `bernstein.py` |
| `alpha` | 0.6 | weight of proposal lift in `composite_auto` | `model.py` |
| action thresholds | 0.875 / 0.625 / 0.375 / 0.125 | automatability to action band | `model.py` |
| `aggressiveness` | 0.7 | effort-shift lever (figures) | `model.py` |
| `AUTONOMY_2026` | 0.40–0.80 per task | tool autonomy | `tooling.py` |
| `adoption` bands | 0.30 / 0.55 / 0.80 | uptake, low/expected/high | `inputs.py` |
| `fee_multiplier` | 2.8 | charge-out / cost | `inputs.py` |
| flow self-retention | 0.45 | activity stays within itself | `activities.py` |
| Practice-Management coupling | 0.10 | back-edge weight | `activities.py` |
| influence squaring | `W ** 2` | Eber variance weighting | `sensitivity.py` / `activities.py` |
| convergence tol (grade) | 1e-3 | RNM/higher-order stopping rule | `sensitivity.py` |
| eigen-gap `kmax` | 8 | max blocks considered | `rnm.py` |

The measured inputs (timesheet hours, band rates) are not in this list because
they are data, not assumptions; they come from the firm.

---

## What to verify first

1. **The grid cells** in `_GRID_SPEC` against Bernstein Figure 1.5.3. Spot-check
   any task whose class looks off; the whole automatability layer rests on it.
2. **The five-band `SCALE` spacing.** Even spacing is an assumption. If the bands
   are not evenly spaced in Bernstein's intent, change the table.
3. **`PROPOSAL_STRENGTH` and `AUTONOMY_2026`** against the proposal wording. These
   are verbs turned into numbers by our judgement.
4. **The even within-stage effort split** (`task_catalogue`). It is a placeholder;
   a real timesheet with task tags removes it.
5. **The elicited flow and influence matrices** (`activities.py`). Dummy now; the
   workshop fills them. Until then the systemic layer is illustrative.
