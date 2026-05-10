"""
collisions.py

Frequency collision conditions from Table 2 of the paper.
δ = −340 MHz (anharmonicity of fixed-frequency transmon qubits).

Conditions 1–4: two qubits j and k are connected.
Conditions 5–7: qubits i and k are both connected to qubit j (3-qubit case).
"""

import numpy as np

DELTA = -340.0   # MHz  (negative anharmonicity)


# ── Design-point collision checks ────────────────────────────────────────────

def two_qubit_collision(fj, fk):
    """True if the (fj, fk) pair violates any of conditions 1–4 (Table 2)."""
    # Condition 1: |fj - fk| < 17 MHz
    if abs(fj - fk) < 17.0:
        return True
    # Condition 2: |fj - (fk - δ/2)| < 4 MHz
    if abs(fj - (fk - DELTA / 2.0)) < 4.0:
        return True
    # Condition 3: |fj - (fk - δ)| < 25 MHz
    if abs(fj - (fk - DELTA)) < 25.0:
        return True
    # Condition 4: fj > fk - δ  (i.e. fj > fk + 340)
    # Note: with our 5-freq palette (max spread 280 MHz) this never fires,
    # but we keep it for correctness with arbitrary frequencies.
    if fj > fk - DELTA:
        return True
    return False


def three_qubit_collision(fi, fj, fk):
    """
    True if conditions 5–7 are violated.
    i and k are both connected to j.
    """
    # Condition 5: |fi - fk| < 17 MHz   (paper notation: fi ≅ fk)
    if abs(fi - fk) < 17.0:
        return True
    # Condition 6: |fi - (fk - δ)| < 25 MHz
    if abs(fi - (fk - DELTA)) < 25.0:
        return True
    # Condition 7: |2fj + δ - (fk + fi)| < 17 MHz
    if abs((2.0 * fj + DELTA) - (fk + fi)) < 17.0:
        return True
    return False


def has_any_collision(freqs, edges, neighbors):
    """
    freqs     : dict  qubit → MHz
    edges     : list of (j, k)  — undirected edge list
    neighbors : dict  qubit → set of neighbour qubits
    Returns True if any condition 1–7 is violated.
    """
    # Two-qubit conditions (1–4)
    for j, k in edges:
        if two_qubit_collision(freqs[j], freqs[k]):
            return True
        # Conditions are symmetric in the sense that we must also check (k,j)
        # for condition 4 (which is not symmetric).
        if two_qubit_collision(freqs[k], freqs[j]):
            return True

    # Three-qubit conditions (5–7): for every qubit j, all pairs (i, k) of
    # its neighbours.
    for j, nbrs in neighbors.items():
        nb = list(nbrs)
        for a in range(len(nb)):
            for b in range(a + 1, len(nb)):
                i, k = nb[a], nb[b]
                if three_qubit_collision(freqs[i], freqs[j], freqs[k]):
                    return True
                # condition 5/6 are symmetric in i,k; condition 7 is symmetric
                # in i,k too — so one call per pair suffices.
    return False


def yield_rate(design_freqs, edges, neighbors,
               sigma_f=30.0, trials=100_000, seed=0):
    """
    Monte-Carlo yield rate (paper: 100,000 trials, σ_f = 30 MHz).

    design_freqs : dict qubit → MHz (design-point frequencies)
    edges        : list of (j, k)
    neighbors    : dict qubit → set of neighbour qubits
    """
    rng    = np.random.default_rng(seed)
    qubits = sorted(design_freqs.keys())
    fdes   = np.array([design_freqs[q] for q in qubits])
    q_idx  = {q: i for i, q in enumerate(qubits)}

    good = 0
    for _ in range(trials):
        noise = rng.normal(0.0, sigma_f, size=len(qubits))
        f = {q: fdes[q_idx[q]] + noise[q_idx[q]] for q in qubits}
        if not has_any_collision(f, edges, neighbors):
            good += 1

    return good / trials