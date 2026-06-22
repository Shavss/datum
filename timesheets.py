"""
timesheets.py - dummy stage-tagged timesheet data.

Work stages run one after another, so effort and flow are naturally indexed by
stage, not by task group. This is the workflow-mapping basis (the same idea as
the Markov process model in the PM coursework), now over the real RIBA stages.

Real Rapport3 / Deltek extracts replace both arrays:
  STAGE_HOURS      = hours logged per stage  (measured directly)
  STAGE_TRANSITION = stage-to-stage flow, estimated from sequenced entries
"""

import numpy as np
import bernstein as B

# Dummy hours per stage (plausible shape: ramps to technical design and
# construction, tails off through handover and use).
STAGE_HOURS = np.array([
    400,    # Strategic Definition
    700,    # Preparation + Briefing
    1100,   # Concept Design
    1400,   # Spatial Coordination
    2200,   # Technical Design
    600,    # Procurement
    1800,   # Manufacturing + Construction
    500,    # Handover
    300,    # Use
], dtype=float)


def _stage_transition():
    """Sequential forward flow with rework loops back to earlier stages.
    A real version is counted from timesheet sequences."""
    n = B.NS
    T = np.zeros((n, n))
    for i in range(n):
        T[i, i] += 0.30                      # continue within the stage
        if i < n - 1:
            T[i, i + 1] += 0.50              # advance to the next stage
        else:
            T[i, i] += 0.50                  # last stage absorbs
        if i >= 1:
            T[i, i - 1] += 0.12              # rework one stage back
        if i >= 3:
            T[i, i - 2] += 0.08              # deeper rework
    return T / T.sum(axis=1, keepdims=True)


STAGE_TRANSITION = _stage_transition()
assert np.allclose(STAGE_TRANSITION.sum(axis=1), 1.0)
