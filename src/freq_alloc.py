"""
freq_alloc.py

Frequency allocator matching the paper (Section "Parameter Setting"):
  "we use the frequency allocation algorithm of Ref. [32], and the
   candidate frequencies are selected according to IBM's 5-frequency
   scheme [27]."

IBM 5-frequency palette (Fig. 11, 70 MHz spacing):
  5000, 5070, 5140, 5210, 5280 MHz

Algorithm (Ref [32] = eff-5-freq paper, Li et al. ASPLOS 2020):
  Random-restart local search minimising design-point collisions.
  Among zero-collision solutions, pick the one with best fast-yield.
  Seeded with a graph-coloring initial solution.
"""

import random
import numpy as np
import networkx as nx

# IBM 5-frequency palette — 70 MHz spacing (Fig. 11)
CANDIDATE_FREQS_MHZ = [5000.0, 5070.0, 5140.0, 5210.0, 5280.0]

DELTA = -340.0   # MHz


# ── Inline collision checks ──────────────────────────────────────────────────

def _two_q(fj, fk):
    if abs(fj - fk) < 17.0:                return True
    if abs(fj - (fk - DELTA / 2.0)) < 4.0: return True
    if abs(fj - (fk - DELTA)) < 25.0:      return True
    if fj > fk - DELTA:                    return True
    if fk > fj - DELTA:                    return True   # symmetric check
    return False


def _three_q(fi, fj, fk):
    if abs(fi - fk) < 17.0:                        return True
    if abs(fi - (fk - DELTA)) < 25.0:              return True
    if abs((2.0 * fj + DELTA) - (fk + fi)) < 17.0: return True
    return False


def _score(freq, edges, neighbors, n):
    c = 0
    for a, b in edges:
        if _two_q(freq[a], freq[b]):
            c += 1
    for j in range(n):
        nb = list(neighbors[j])
        for x in range(len(nb)):
            for y in range(x + 1, len(nb)):
                if _three_q(freq[nb[x]], freq[j], freq[nb[y]]):
                    c += 1
    return c


def _fast_yield(freq, edges, neighbors, n, trials=5_000, seed=0):
    """Approximate yield for tie-breaking among zero-collision solutions."""
    rng  = np.random.default_rng(seed)
    qs   = list(range(n))
    fdes = np.array([freq[q] for q in qs])
    good = 0
    for _ in range(trials):
        noise = rng.normal(0.0, 30.0, size=n)
        f = {q: fdes[q] + noise[q] for q in qs}
        ok = True
        for a, b in edges:
            if _two_q(f[a], f[b]):
                ok = False; break
        if ok:
            for j in range(n):
                if not ok: break
                nb = list(neighbors[j])
                for x in range(len(nb)):
                    if not ok: break
                    for y in range(x + 1, len(nb)):
                        if _three_q(f[nb[x]], f[j], f[nb[y]]):
                            ok = False; break
        if ok:
            good += 1
    return good / trials


# ── Graph-coloring seed ──────────────────────────────────────────────────────

def _coloring_seed(edges, n):
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for a, b in edges:
        G.add_edge(a, b)
    coloring = nx.coloring.greedy_color(G, strategy='largest_first')
    n_colors = max(coloring.values()) + 1 if n > 0 else 1
    # Space colors as far apart as possible in the 5-freq palette
    step = max(1, len(CANDIDATE_FREQS_MHZ) // n_colors)
    color_map = {c: CANDIDATE_FREQS_MHZ[min(c * step, len(CANDIDATE_FREQS_MHZ) - 1)]
                 for c in range(n_colors)}
    return {q: color_map[coloring[q]] for q in range(n)}


# ── Local search ─────────────────────────────────────────────────────────────

def _local_search(f, edges, neighbors, n, rng_seed=0):
    rng = random.Random(rng_seed)
    order = list(range(n))
    improved = True
    while improved:
        improved = False
        rng.shuffle(order)
        for q in order:
            cur_f = f[q]
            cur_s = _score(f, edges, neighbors, n)
            best_f, best_s = cur_f, cur_s
            for cand in CANDIDATE_FREQS_MHZ:
                if cand == cur_f:
                    continue
                f[q] = cand
                s = _score(f, edges, neighbors, n)
                if s < best_s:
                    best_s, best_f = s, cand
            f[q] = best_f
            if best_f != cur_f:
                improved = True
    return f


# ── Public API ───────────────────────────────────────────────────────────────

def allocate_frequencies(graph_edges, n_qubits, max_iter=500, seed=0):
    """
    Returns dict {qubit → MHz} for qubits 0..n_qubits-1.

    Phase 1: graph-coloring seed + local search
    Phase 2: random-restart local search
    Phase 3: among minimum-collision solutions, pick highest fast-yield
    """
    rng = random.Random(seed)

    neighbors = {q: set() for q in range(n_qubits)}
    for a, b in graph_edges:
        neighbors[a].add(b)
        neighbors[b].add(a)

    candidates = []   # (collision_score, freq_dict)

    # Phase 1: structured seed
    f0 = _coloring_seed(graph_edges, n_qubits)
    f0 = _local_search(f0, graph_edges, neighbors, n_qubits, rng_seed=seed)
    candidates.append((_score(f0, graph_edges, neighbors, n_qubits), dict(f0)))

    # Phase 2: random restarts
    zero_found = 0
    for it in range(max_iter):
        f = {q: rng.choice(CANDIDATE_FREQS_MHZ) for q in range(n_qubits)}
        f = _local_search(f, graph_edges, neighbors, n_qubits, rng_seed=seed + it + 1)
        s = _score(f, graph_edges, neighbors, n_qubits)
        candidates.append((s, dict(f)))
        if s == 0:
            zero_found += 1
            if zero_found >= 30:   # enough zero-collision solutions
                break

    # Phase 3: best among minimum-collision solutions
    min_s     = min(c[0] for c in candidates)
    top       = [c[1] for c in candidates if c[0] == min_s]

    if len(top) == 1:
        return top[0]

    best_f, best_y = None, -1.0
    for f in top:
        y = _fast_yield(f, graph_edges, neighbors, n_qubits,
                        trials=5_000, seed=seed)
        if y > best_y:
            best_y, best_f = y, f
    return best_f