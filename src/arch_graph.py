"""
arch_graph.py

Converts a qubit coordinate vector into an architecture graph G,
applying the three physical wiring constraints from the paper:

  Constraint 1 (Algorithm 1):
    A[i][j]=1 AND qubits i,j are grid-adjacent (|Δx|≤1, |Δy|≤1)
    → connect them (C[i][j]=1), otherwise prune (C[i][j]=0).

  Constraint 2 (Algorithm 2):
    For every 2×2 cell where BOTH diagonals are present in C
    → 4-qubit bus: add all 4 sides of that cell.

  Constraint 3 (Algorithm 3):
    No two adjacent squares may BOTH wire the shared edge
    (which happens when both are 4-qubit bus squares).
    Resolve by building two pruning schemes:
      C'1: for every Seq-1 square that conflicts with an adjacent Seq-2 square,
           prune that Seq-2 square's diagonals.
      C'2: for every Seq-2 square that conflicts with an adjacent Seq-1 square,
           prune that Seq-1 square's diagonals.
    Non-conflicting squares keep their diagonals in BOTH schemes.
    Return both resulting graphs G1, G2; caller picks the better one.

  Sequence assignment (Fig. 9):
    Each 2×2 cell is classified by the parity of its bottom-left corner:
      (x + y) % 2 == 1  →  Sequence 1  (odd parity  = "orange" in paper)
      (x + y) % 2 == 0  →  Sequence 2  (even parity = "green"  in paper)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG FIXED vs previous version
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Old prune() did a BLANKET prune: removed diagonals of ALL squares not in
keep_seq, even isolated squares with no adjacent conflict.

Paper Algorithm 3 only prunes diagonals of squares that ACTUALLY CONFLICT
with an adjacent square of the opposite sequence. A non-conflicting square
keeps its diagonals in both schemes.

Example: a lone 4-qubit bus square with no adjacent bus square has no C3
conflict; its diagonals should be kept in both G1 and G2.  The old code
removed them in one of the two schemes — silently under-connecting the graph.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import networkx as nx


def build_arch_graph(coord_vec, A, grid_w, grid_h):
    """
    coord_vec : list of (x, y) tuples, one per logical qubit (index = qubit id)
    A         : n×n upper-triangular 0/1 adjacency matrix (from topology.py)
    grid_w    : grid width  (number of columns of qubit positions)
    grid_h    : grid height (number of rows    of qubit positions)

    Returns (G1, G2) — both are nx.Graph over nodes 0..n-1.
    Caller selects the better graph by fitness (ga_design.py) or edge count
    (eff5freq_design.py).
    """
    n      = len(coord_vec)
    pos2q  = {coord_vec[i]: i for i in range(n)}

    # ── Algorithm 1: Constraint 1 ─────────────────────────────────────────────
    # C[i][j] = 1  iff  A[i][j]=1  AND  qubits i,j are within 1 step on the grid.
    # Initialise to zero; only set to 1 when both conditions hold.
    C = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if A[i][j] == 1:
                xi, yi = coord_vec[i]
                xj, yj = coord_vec[j]
                if abs(xi - xj) <= 1 and abs(yi - yj) <= 1:
                    C[i][j] = 1

    # ── Helper: read / write C symmetrically (upper-triangular storage) ───────
    def _e(u, v):
        u, v = (u, v) if u < v else (v, u)
        return C[u][v]

    def _set(u, v, val=1):
        u, v = (u, v) if u < v else (v, u)
        C[u][v] = val

    # ── Algorithm 2: Constraint 2 — 4-qubit bus closure ───────────────────────
    # Enumerate every 2×2 cell in the grid.
    # A cell at (x, y) has corners (BL, BR, TR, TL):
    #   BL=(x,y)  BR=(x+1,y)  TR=(x+1,y+1)  TL=(x,y+1)
    # If ALL 4 corners have qubits AND both diagonals (BL,TR) and (BR,TL) are
    # already in C, upgrade to a 4-qubit bus: add all 4 sides.
    #
    # Note: all-4-corners check is required — we need qubit indices for all
    # four positions to read/write C entries.  A cell with a missing corner
    # cannot form a 4-qubit bus.
    #
    # bus_squares: set of cell tuples (a,b,c,d) that triggered 4-qubit bus closure.
    # These are the only squares that can create a Constraint 3 conflict, because
    # only they add a shared edge that might duplicate a neighbour's shared edge.
    squares    = []   # all cells where all 4 corners have qubits
    bus_squares = set()  # subset that activated the 4-qubit bus

    for x in range(grid_w - 1):
        for y in range(grid_h - 1):
            # Corners in canonical order: BL, BR, TR, TL
            corners = [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]
            if not all(c in pos2q for c in corners):
                continue   # cell has an unoccupied corner — skip
            a, b, c, d = [pos2q[c] for c in corners]  # qubit ids
            sq = (a, b, c, d)
            squares.append(sq)

            # Both diagonals present → 4-qubit bus: add all 4 sides
            if _e(a, c) == 1 and _e(b, d) == 1:
                _set(a, b)
                _set(b, c)
                _set(c, d)
                _set(d, a)
                bus_squares.add(sq)

    # ── Algorithm 3: Constraint 3 — conflict-only diagonal pruning ────────────
    #
    # Sequence assignment (Fig. 9, paper):
    #   (x + y) % 2 == 1  →  Sequence 1
    #   (x + y) % 2 == 0  →  Sequence 2
    # where (x, y) is the bottom-left corner's GRID coordinate.
    def _seq(sq):
        """Return 1 or 2 for a square's sequence (Fig. 9)."""
        a = sq[0]
        x, y = coord_vec[a]   # BL corner coordinates
        return 1 if (x + y) % 2 == 1 else 2

    # Build a spatial index: grid position of BL corner → square tuple
    sq_by_bl = {}
    for sq in squares:
        x, y = coord_vec[sq[0]]
        sq_by_bl[(x, y)] = sq

    def _adjacent_squares(sq):
        """
        Return all squares that are edge-adjacent to sq (share a full edge,
        i.e., 2 qubits), regardless of whether they are bus squares.
        Adjacency: squares whose BL corners differ by (±1, 0) or (0, ±1).
        """
        x, y = coord_vec[sq[0]]
        adj = []
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nb = sq_by_bl.get((x + dx, y + dy))
            if nb is not None:
                adj.append(nb)
        return adj

    # Determine which bus squares CONFLICT with each other.
    # Two adjacent bus squares conflict because they both include the shared
    # edge in their wiring (each 4-qubit bus adds all 4 sides including the
    # side shared with the neighbour).
    conflicting = set()   # set of square tuples that have at least one conflict
    for sq in bus_squares:
        for nb in _adjacent_squares(sq):
            if nb in bus_squares:
                conflicting.add(sq)
                break   # one conflicting neighbour is enough to mark sq

    # Build the two pruning matrices C'1 and C'2 as independent copies of C.
    #
    # C'1 (scheme 1): for every CONFLICTING Seq-2 square, zero its diagonals.
    #   → Seq-1 squares' diagonals are always kept in C'1.
    #   → Seq-2 squares' diagonals are kept in C'1 ONLY IF they don't conflict.
    #
    # C'2 (scheme 2): for every CONFLICTING Seq-1 square, zero its diagonals.
    #   → Seq-2 squares' diagonals are always kept in C'2.
    #   → Seq-1 squares' diagonals are kept in C'2 ONLY IF they don't conflict.
    #
    # This matches Algorithm 3 lines 3-9 exactly:
    #   Seq-1 conflicting square → prune adjacent Seq-2 squares in C'1
    #   Seq-2 conflicting square → prune adjacent Seq-1 squares in C'2
    # (A square is pruned when it is the OPPOSITE-sequence conflicting neighbour.)

    def _copy(matrix):
        return [row[:] for row in matrix]

    M1 = _copy(C)
    M2 = _copy(C)

    def _prune_diagonals(matrix, sq):
        """Zero the two diagonals of sq in matrix (in-place)."""
        a, b, c, d = sq
        # diagonal 1: (a, c) = (BL, TR)
        u, v = (a, c) if a < c else (c, a)
        matrix[u][v] = 0
        # diagonal 2: (b, d) = (BR, TL)
        u, v = (b, d) if b < d else (d, b)
        matrix[u][v] = 0

    for sq in squares:
        if sq not in conflicting:
            continue   # no conflict → keep diagonals in both schemes
        s = _seq(sq)
        if s == 2:
            # Seq-2 square conflicts → prune ITS diagonals in scheme C'1
            _prune_diagonals(M1, sq)
        else:
            # Seq-1 square conflicts → prune ITS diagonals in scheme C'2
            _prune_diagonals(M2, sq)

    # ── Build NetworkX graphs from the two matrices ───────────────────────────
    def make_graph(matrix):
        g = nx.Graph()
        g.add_nodes_from(range(n))
        for i in range(n):
            for j in range(i + 1, n):
                if matrix[i][j] == 1:
                    g.add_edge(i, j)
        return g

    return make_graph(M1), make_graph(M2)