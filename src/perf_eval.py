"""
perf_eval.py

Post-mapping gate count via Qiskit transpiler.

From the paper (Section "Parameter Setting"):
  "qubit mapping is realized by the SABRE algorithm, optimization_level=3"
  "for our method and eff-5-freq, q_i corresponds to Q_i one by one
   [trivial/initial layout]"
  "for general-purpose architectures, we do not specify the corresponding
   relationship between logical qubits and physical qubits [SABRE layout]"

Therefore:
  custom_arch=True  → initial_layout = [0, 1, ..., n-1]  (trivial, no SABRE layout)
  custom_arch=False → layout_method='sabre'               (IBM general-purpose)
"""

import networkx as nx
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap


def _make_connected_cmap(edges, n_phys):
    """
    Build a CouplingMap that covers all n_phys qubits and is connected.
    If the edge list leaves some qubits isolated or creates a disconnected
    graph, bridge edges are added (lowest-index per component → qubit 0).
    """
    G = nx.Graph()
    G.add_nodes_from(range(n_phys))
    for a, b in edges:
        G.add_edge(a, b)

    # Connect any disconnected components with a single bridge edge each
    components = list(nx.connected_components(G))
    if len(components) > 1:
        anchor = min(components[0])
        for comp in components[1:]:
            G.add_edge(anchor, min(comp))

    cm_edges = []
    for a, b in G.edges():
        cm_edges.append([a, b])
        cm_edges.append([b, a])
    return CouplingMap(cm_edges)


def post_mapping_gate_count(qasm_path, edges, n_phys,
                            custom_arch=False, seed=0):
    """
    qasm_path   : path to the benchmark .qasm file
    edges       : architecture edge list
    n_phys      : number of physical qubits in the coupling map
    custom_arch : True  → trivial initial layout (q_i → Q_i)
                  False → SABRE layout (IBM general-purpose)
    seed        : transpiler seed for reproducibility
    """
    qc   = QuantumCircuit.from_qasm_file(qasm_path)
    cmap = _make_connected_cmap(edges, n_phys)

    if custom_arch:
        # Trivial layout: logical qubit i → physical qubit i
        n_circ = qc.num_qubits
        initial_layout = list(range(n_circ))
        tqc = transpile(
            qc,
            coupling_map=cmap,
            basis_gates=['u3', 'cx'],
            initial_layout=initial_layout,
            layout_method='trivial',
            routing_method='sabre',
            optimization_level=3,
            seed_transpiler=seed,
        )
    else:
        tqc = transpile(
            qc,
            coupling_map=cmap,
            basis_gates=['u3', 'cx'],
            layout_method='sabre',
            routing_method='sabre',
            optimization_level=3,
            seed_transpiler=seed,
        )

    return sum(tqc.count_ops().values())