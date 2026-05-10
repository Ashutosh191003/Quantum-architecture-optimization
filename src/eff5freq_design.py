"""
eff5freq_design.py

Implements the eff-5-freq architecture design algorithm (Li et al. ASPLOS 2020,
Ref [32] in the paper), as described in Section "Result Comparison" and
Fig. 13 of the replication paper.

Key detail: the priority ordering uses the COUPLING STRENGTH (gate count)
matrix M, not just the 0/1 adjacency A. The paper states:
  "the eff-5-freq algorithm first calculates the coupling degree of each q_i
   based on M with the calculation formula being Σ M(i,j)"
"""

import networkx as nx
from .arch_graph import build_arch_graph


def design_eff5freq(A, M, n):
    """
    A : n×n upper-triangular 0/1 adjacency matrix (for arch_graph constraints)
    M : n×n symmetric gate-count matrix (for priority ordering and placement)
    n : number of qubits
    """
    # 1. Coupling degree priority: descending Σ_j M[i][j]
    coupling_degree = [sum(M[i]) for i in range(n)]
    order = sorted(range(n), key=lambda i: coupling_degree[i], reverse=True)

    # 2. Grid dimensions
    if n <= 4:    w, h = 2, 2
    elif n <= 9:  w, h = 3, 3
    elif n <= 16: w, h = 4, 4
    else:         w, h = 5, 5

    coords = [None] * n
    used   = set()

    # Place highest-priority qubit at grid centre
    coords[order[0]] = (w // 2, h // 2)
    used.add((w // 2, h // 2))

    def free_neighbors(cell):
        x, y = cell
        return [(x + dx, y + dy)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx, dy) != (0, 0)
                and 0 <= x + dx < w and 0 <= y + dy < h
                and (x + dx, y + dy) not in used]

    for q in order[1:]:
        # Find already-placed qubits that are coupled to q (by M)
        placed_coupled = [(M[q][p], p)
                          for p in range(n)
                          if coords[p] is not None and M[q][p] > 0]
        placed_coupled.sort(reverse=True)   # highest coupling first

        chosen = None

        for _, p in placed_coupled:
            free = free_neighbors(coords[p])
            if free:
                # Tie-break: maximise total coupling-weighted proximity to
                # all already-placed qubits (eff-5-freq tie-breaker)
                def score(cell, _q=q, _p=p):
                    s = 0
                    for r in range(n):
                        if coords[r] is not None and r != _p and M[_q][r] > 0:
                            x1, y1 = cell
                            x2, y2 = coords[r]
                            s -= max(abs(x1 - x2), abs(y1 - y2)) * M[_q][r]
                    return s
                chosen = max(free, key=score)
                break

        if chosen is None:
            # Fallback: try any free cell adjacent to ANY placed qubit
            for p in range(n):
                if coords[p] is None:
                    continue
                free = free_neighbors(coords[p])
                if free:
                    chosen = free[0]
                    break

        if chosen is None:
            # Last resort: any free cell in the grid
            for x in range(w):
                for y in range(h):
                    if (x, y) not in used:
                        chosen = (x, y)
                        break
                if chosen is not None:
                    break

        if chosen is None:
            raise RuntimeError(
                f'eff5freq: no free cell for qubit {q} '
                f'(grid {w}×{h}, {len(used)} used)'
            )

        coords[q] = chosen
        used.add(chosen)

    G1, G2 = build_arch_graph(coords, A, w, h)

    # The paper says eff-5-freq picks "the processor architecture with the
    # best performance and yield rate". In practice this means: try both
    # pruning variants and pick the one with fewer edges (fewer edges =
    # less collision risk = higher yield, and the paper's eff-5-freq
    # typically also has fewer SWAP gates in this variant).
    return G1 if G1.number_of_edges() <= G2.number_of_edges() else G2