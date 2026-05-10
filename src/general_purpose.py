"""
general_purpose.py

IBM 20-qubit architectures and frequency assignment.

Fig. 11 of the paper shows the 5-frequency palette as:
  1 = 5.00 GHz
  2 = 5.07 GHz
  3 = 5.13 GHz
  4 = 5.20 GHz
  5 = 5.27 GHz
i.e. spacing is 70 MHz (not 80).

The grid pattern for all four IBM architectures is:
  qubit index = row*5 + col,  freq_index = (2*row + col) % 5
which matches the numbers printed in Fig. 11.
"""

# ── IBM 5-frequency palette (Fig. 11, 70 MHz spacing) ──────────────────────
FREQS = [5000.0, 5070.0, 5140.0, 5210.0, 5280.0]   # MHz


def freq_assign_20():
    """Fixed stripe frequency map for the 4×5 IBM grid (Fig. 11)."""
    return {r * 5 + c: FREQS[(2 * r + c) % 5]
            for r in range(4) for c in range(5)}


# ── Edge-list helpers ────────────────────────────────────────────────────────

def _grid_2q():
    """All-2-qubit-bus: only horizontal & vertical neighbours."""
    e = []
    for r in range(4):
        for c in range(5):
            q = r * 5 + c
            if c < 4: e.append((q, q + 1))
            if r < 3: e.append((q, q + 5))
    return e


def _max_4q():
    """Every 2×2 cell uses a 4-qubit bus → all 4 sides + 2 diagonals."""
    e = set(_grid_2q())
    for r in range(3):
        for c in range(4):
            a = r * 5 + c; b = a + 1; d = a + 5; cc = d + 1
            e.update([(a, cc), (b, d)])
    return [tuple(sorted(x)) for x in e]


def _penguin_v3():
    """IBM Penguin V3: checkerboard 4-qubit buses at (r+c)%2==0 cells."""
    e = set(_grid_2q())
    for r in range(3):
        for c in range(4):
            if (r + c) % 2 == 0:
                a = r * 5 + c; b = a + 1; d = a + 5; cc = d + 1
                e.update([(a, cc), (b, d)])
    return [tuple(sorted(x)) for x in e]


def _penguin_v4():
    """IBM Penguin V4: checkerboard 4-qubit buses at (r+c)%2==1 cells."""
    e = set(_grid_2q())
    for r in range(3):
        for c in range(4):
            if (r + c) % 2 == 1:
                a = r * 5 + c; b = a + 1; d = a + 5; cc = d + 1
                e.update([(a, cc), (b, d)])
    return [tuple(sorted(x)) for x in e]


IBM_ARCHS = {
    "ibm_v3": _penguin_v3(),
    "ibm_v4": _penguin_v4(),
    "all_2q": _grid_2q(),
    "max_4q": _max_4q(),
}