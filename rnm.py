"""
rnm.py - derive the task grouping from the grid, instead of imposing Bernstein's
five groups.

Source: Eber, *Project Management2 - Platform Oriented Management* (TUM),
5.3.4 (Symmetrize, normalize and find submatrices - RNM) and 2.3.1 Remark 2
(the multiplicity of the dominant eigenvalue counts the independent subsystems).

The method, faithfully: build a task-to-task adjacency from the grid, symmetrise
it, normalise it, then let neighbourhood averaging separate the segments. Eber's
"average the weighted component of all directly connected neighbours for each
node" is neighbourhood averaging; the random-vector iteration he describes is
power iteration whose limit is the leading eigen-subspace, so the clustering is
done on that subspace (RNM done exactly rather than approximately) while the
iteration itself is kept for the separation-development picture.

Nothing here imposes a number of groups. The eigen-gap reports how many segments
the data actually supports, which is the answer to "are five groups right?".

Three honest ways to build the adjacency from the grid, because the construction
decides the result and so is a positioning choice, not a mechanical one:

  cooccurrence  edge = Jaccard overlap of the stages two tasks are active in.
                Groups by WHEN work happens. Jaccard (not raw count) so a task
                active in all nine stages does not trivially link to everyone.
  class         edge = cosine of the two tasks' class histograms. Groups by HOW
                automatable the work is. Recovers the automatability bands, so it
                largely re-states the class labels.
  blend         edge = per-shared-stage class agreement, summed and normalised by
                the union of active stages. Groups by work that happens together
                AND behaves alike: the intervention-block reading.
"""
import numpy as np
import bernstein as B

TASKS = [t for (_g, t) in B.TASK_ORDER]
N = len(TASKS)
GROUP_OF = {t: g for (g, t) in B.TASK_ORDER}
CLASSES = ["procedural", "procedural-integrative", "integrative",
           "integrative-perceptive", "perceptive"]
_CIX = {c: k for k, c in enumerate(CLASSES)}


# ---- grid as matrices ------------------------------------------------------
def incidence():
    """task x stage, 1 where the task is active."""
    M = np.zeros((N, B.NS))
    for i, t in enumerate(TASKS):
        for s in B.TASK_STAGE[t]:
            M[i, s] = 1.0
    return M


def class_grid():
    """task x stage automatability value (Bernstein SCALE), nan where inactive."""
    G = np.full((N, B.NS), np.nan)
    for i, t in enumerate(TASKS):
        for s, cls in B.TASK_STAGE[t].items():
            G[i, s] = B.SCALE[cls]
    return G


def class_histograms():
    """task x 5 count of stages spent in each class band."""
    H = np.zeros((N, 5))
    for i, t in enumerate(TASKS):
        for _s, cls in B.TASK_STAGE[t].items():
            H[i, _CIX[cls]] += 1.0
    return H


# ---- the three adjacencies -------------------------------------------------
def adj_cooccurrence():
    M = incidence()
    inter = M @ M.T
    deg = M.sum(axis=1)
    union = deg[:, None] + deg[None, :] - inter
    A = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)
    np.fill_diagonal(A, 0.0)
    return A


def adj_class():
    H = class_histograms()
    nrm = np.linalg.norm(H, axis=1, keepdims=True)
    Hn = np.divide(H, nrm, out=np.zeros_like(H), where=nrm > 0)
    A = Hn @ Hn.T
    np.fill_diagonal(A, 0.0)
    return np.clip(A, 0, None)


def adj_blend():
    G = class_grid()
    A = np.zeros((N, N))
    for i in range(N):
        ai = ~np.isnan(G[i])
        for j in range(i + 1, N):
            aj = ~np.isnan(G[j])
            shared = ai & aj
            if not shared.any():
                continue
            agree = 1.0 - np.abs(G[i, shared] - G[j, shared])  # per stage, [0,1]
            union = (ai | aj).sum()
            A[i, j] = A[j, i] = agree.sum() / union
    return A


ADJACENCIES = {"cooccurrence": adj_cooccurrence,
               "class": adj_class, "blend": adj_blend}


# ---- normalised operators --------------------------------------------------
def _symmetric_normalised(adj):
    """D^-1/2 A D^-1/2 - symmetric, eigenvalues in [-1, 1]. The leading
    eigenvectors carry the segment structure (limit of the random-vector RNM)."""
    A = (adj + adj.T) / 2.0
    d = A.sum(axis=1)
    dinv = np.divide(1.0, np.sqrt(d), out=np.zeros_like(d), where=d > 0)
    return (A * dinv[:, None]) * dinv[None, :]


def _row_stochastic(adj):
    """Row-normalised neighbourhood-averaging operator, for the iterative view."""
    A = (adj + adj.T) / 2.0
    r = A.sum(axis=1, keepdims=True)
    return np.divide(A, r, out=np.zeros_like(A), where=r > 0)


# ---- how many segments does the data support (eigen-gap) -------------------
def segment_count(adj, kmax=8):
    """Eber 2.3.1 Remark 2: segment count = multiplicity of the dominant
    eigenvalue, read here as the position of the largest gap in the top
    eigenvalues of the symmetric normalised operator."""
    P = _symmetric_normalised(adj)
    ev = np.sort(np.linalg.eigvalsh(P))[::-1]
    top = ev[:min(kmax + 1, len(ev))]
    gaps = top[:-1] - top[1:]
    return int(np.argmax(gaps) + 1), ev


# ---- clustering (numpy k-means on the leading eigen-subspace) --------------
def _kmeans(X, k, seed=0, restarts=12, iters=200):
    rng = np.random.default_rng(seed)
    best_lab, best_in = None, np.inf
    for _ in range(restarts):
        ctr = X[rng.choice(len(X), k, replace=False)].copy()
        lab = np.zeros(len(X), dtype=int)
        for _it in range(iters):
            d = np.linalg.norm(X[:, None, :] - ctr[None, :, :], axis=2)
            new = d.argmin(axis=1)
            if np.array_equal(new, lab) and _it:
                break
            lab = new
            for c in range(k):
                if (lab == c).any():
                    ctr[c] = X[lab == c].mean(axis=0)
        inertia = float(((X - ctr[lab]) ** 2).sum())
        if inertia < best_in:
            best_in, best_lab = inertia, lab.copy()
    return best_lab


def grouping(adj, k=None, seed=0):
    """Return integer labels per task. k defaults to the eigen-gap count."""
    if k is None:
        k, _ = segment_count(adj)
    P = _symmetric_normalised(adj)
    ev, vec = np.linalg.eigh(P)
    emb = vec[:, np.argsort(ev)[::-1][:k]]   # leading-k eigenvectors
    nrm = np.linalg.norm(emb, axis=1, keepdims=True)
    emb = np.divide(emb, nrm, out=np.zeros_like(emb), where=nrm > 0)
    return _kmeans(emb, k, seed=seed), k


# ---- iterative separation development, for the figure ----------------------
def separation_history(adj, z=1, iters=40, seed=1):
    P = _row_stochastic(adj)
    rng = np.random.default_rng(seed)
    Y = rng.standard_normal((N, z))
    hist = [Y[:, 0].copy()]
    for _ in range(iters):
        Y = P @ Y
        hist.append(Y[:, 0].copy())
    return np.array(hist)   # iters+1 x N, the first random coordinate per node


# ---- agreement between two partitions (Rand index, dependency-free) --------
def rand_index(a, b):
    a, b = np.asarray(a), np.asarray(b)
    same_a = a[:, None] == a[None, :]
    same_b = b[:, None] == b[None, :]
    iu = np.triu_indices(len(a), 1)
    agree = (same_a[iu] == same_b[iu]).mean()
    return float(agree)


def bernstein_labels():
    return np.array([B.GROUPS.index(GROUP_OF[t]) for t in TASKS])


# ---- cluster character, for naming blocks on the opportunity map -----------
def cluster_profile(labels):
    """For each cluster: member tasks, mean automatability, dominant class."""
    import model as M
    prof = {}
    for c in sorted(set(labels)):
        members = [TASKS[i] for i in range(N) if labels[i] == c]
        autos = [M.task_mean_auto(t) for t in members]
        prof[c] = dict(members=members, n=len(members),
                       mean_auto=float(np.mean(autos)))
    return prof


# ---- validation against Eber's own toy networks (5.4.1) --------------------
def _validate():
    """Reproduce Eber 5.4.1: one segment, two separated, two weakly connected.
    Confirms the method recovers known structure before it touches the grid."""
    def clique(nodes, n):
        A = np.zeros((n, n))
        for i in nodes:
            for j in nodes:
                if i != j:
                    A[i, j] = 1.0
        return A

    n = 6
    seg1, seg2 = [0, 2, 3], [1, 4, 5]
    one = clique(list(range(n)), n)                      # #1 one segment
    two = clique(seg1, n) + clique(seg2, n)              # #2 two, separated
    weak = two.copy()                                    # #3 two, weakly linked
    weak[3, 1] = weak[1, 3] = 0.5
    out = {}
    out["#1 one segment"] = segment_count(one, kmax=4)[0]
    out["#2 two separated"] = segment_count(two, kmax=4)[0]
    out["#3 two weak (0.5)"] = segment_count(weak, kmax=4)[0]
    return out


if __name__ == "__main__":
    print("RNM validation on Eber 5.4.1 toy networks (expected 1, 2, 2):")
    for k, v in _validate().items():
        print(f"  {k:22s} segments found: {v}")
