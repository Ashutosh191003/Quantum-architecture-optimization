"""
topology.py

Extracts two matrices from a QASM file:
  A[i][j]  — upper-triangular 0/1 adjacency (1 if any 2q gate between i,j)
  M[i][j]  — symmetric gate-count matrix    (number of 2q gates between i,j)

The paper uses A for arch_graph / GA fitness, and M for eff-5-freq priority.
"""

from qiskit import QuantumCircuit, transpile


def extract_topology(qasm_path, n):
    """
    Returns (A, M) where:
      A  — n×n upper-triangular 0/1 adjacency matrix
      M  — n×n symmetric gate-count matrix (M[i][j] = #2q gates on pair i,j)
    """
    qc = QuantumCircuit.from_qasm_file(qasm_path)
    # Decompose to CX basis so every 2-qubit instruction is a single CX
    qc = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=0)

    A = [[0] * n for _ in range(n)]
    M = [[0] * n for _ in range(n)]

    for instr, qargs, _ in qc.data:
        if len(qargs) == 2:
            i = qc.find_bit(qargs[0]).index
            j = qc.find_bit(qargs[1]).index
            if i == j:
                continue
            # Symmetric gate count
            M[i][j] += 1
            M[j][i] += 1
            # Upper-triangular adjacency
            if i > j:
                i, j = j, i
            A[i][j] = 1

    return A, M