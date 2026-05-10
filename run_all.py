"""
run_all.py — Replicate Fig. 12 of the paper, with per-benchmark λ sweep.

Key design decisions matching the paper:
- IBM baseline archs use the FIXED stripe frequency pattern (Fig. 11 / freq_assign_20).
  Their yield is therefore determined purely by that pattern, not by the allocator.
- Custom archs (ours, eff5freq) use the graph-coloring + local-search allocator
  which maximises yield for the specific graph topology.
- evaluate() is a top-level function (not a closure) to avoid Python variable
  capture bugs across loop iterations.

LAMBDA SWEEP (new):
  For "ours", instead of a fixed λ=6, we run the GA for every λ ∈ {1…6}
  and pick the architecture that best balances gate count (↓) and yield (↑),
  matching the paper's statement: "λ takes different values depending on
  different quantum programs."  The winning λ is logged per benchmark.

FIXES applied vs original:
  FIX-A: extract_topology returns (A, M) — must unpack both.
  FIX-B: design_eff5freq takes (A, M, n) — M was missing.
  FIX-C: λ is now swept 1-6 per benchmark instead of fixed at 6.
  FIX-D: allocate_frequencies max_iter raised to 1000 for n > 12 so the
          local-search has enough restarts to find low-collision assignments
          on larger / denser graphs.
"""

import json
import statistics
from tqdm import tqdm

from src.benchmarks_config import BENCHMARKS
from src.topology import extract_topology
from src.ga_design import evolve_best_lambda
from src.eff5freq_design import design_eff5freq
from src.general_purpose import IBM_ARCHS, freq_assign_20
from src.freq_alloc import allocate_frequencies
from src.collisions import yield_rate
from src.perf_eval import post_mapping_gate_count


# Pre-compute the fixed IBM frequency assignment (same for all benchmarks)
IBM_FREQS = freq_assign_20()


def build_neighbors(edges, n):
    nbrs = {q: set() for q in range(n)}
    for a, b in edges:
        nbrs[a].add(b)
        nbrs[b].add(a)
    return nbrs


def evaluate_custom(qasm_path, edges, n):
    """
    Evaluate a CUSTOM architecture (ours / eff5freq) on a specific benchmark.
    Uses the freq allocator to find the best frequency assignment for this graph.
    FIX-D: use more restarts for larger circuits.
    Returns (gates, yield_rate).
    """
    # Gate count: median over 5 SABRE seeds
    gates = statistics.median(
        post_mapping_gate_count(qasm_path, edges, n, custom_arch=True, seed=s)
        for s in range(5)
    )
    # FIX-D: scale allocator iterations with qubit count
    max_iter = 1000 if n > 12 else 500

    # Frequency allocation: graph-coloring + local search + yield-aware selection
    f    = allocate_frequencies(edges, n, max_iter=max_iter)
    nbrs = build_neighbors(edges, n)
    y    = yield_rate(f, edges, nbrs, trials=100_000, seed=42)
    return gates, y


def evaluate_ibm(qasm_path, ibm_edges, n_circuit):
    """
    Evaluate an IBM baseline architecture.
    Uses the FIXED stripe pattern (Fig. 11) — not the allocator — exactly
    as the paper does. The 20-qubit device always uses the same freq map.
    """
    n_phys = 20

    # Gate count
    gates = statistics.median(
        post_mapping_gate_count(qasm_path, ibm_edges, n_phys, custom_arch=False, seed=s)
        for s in range(5)
    )

    # Fixed stripe frequencies for all 20 qubits
    f    = IBM_FREQS
    nbrs = build_neighbors(ibm_edges, n_phys)
    y    = yield_rate(f, ibm_edges, nbrs, trials=100_000, seed=42)
    return gates, y


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

results     = {}
best_lambdas = {}   # record which λ won for each benchmark

for name, path, n in tqdm(BENCHMARKS, desc='Benchmarks'):
    print(f'\n=== {name}  ({n} qubits) ===')

    # FIX-A: extract_topology returns (A, M) — unpack both
    A, M = extract_topology(path, n)

    # ── Our GA method: λ sweep 1–6, pick best (gates↓, yield↑) ─────────────
    print('  Running GA λ sweep 1-6 …')

    # evaluate_fn is a closure over path and n — safe here because we
    # do not reuse it across loop iterations (new closure each iteration).
    def make_eval(qasm_path, qubit_n):
        def _eval(edges):
            return evaluate_custom(qasm_path, edges, qubit_n)
        return _eval

    G_ours, best_lam, _, _, lambda_results = evolve_best_lambda(
        A, n,
        evaluate_fn=make_eval(path, n),
        seed=0,
        verbose=True,
    )
    best_lambdas[name] = best_lam
    edges_ours = list(G_ours.edges())

    # Final evaluation of the winning architecture (already computed inside
    # evolve_best_lambda, but re-evaluated here for consistency with the
    # evaluate_custom pipeline used by eff5freq and IBM baselines).
    gates_ours, yield_ours = evaluate_custom(path, edges_ours, n)

    # ── eff-5-freq baseline — FIX-B: pass M as required ────────────────────
    print('  Running eff-5-freq …')
    G_eff     = design_eff5freq(A, M, n)
    edges_eff = list(G_eff.edges())

    bench = {
        'ours':     (gates_ours, yield_ours),
        'eff5freq': evaluate_custom(path, edges_eff, n),
    }

    for ibm_name, ibm_edges in IBM_ARCHS.items():
        bench[ibm_name] = evaluate_ibm(path, ibm_edges, n)

    results[name] = bench
    print(f'  best λ={best_lam}  results={bench}')

# Save results
with open('results.json', 'w') as fh:
    json.dump(results, fh, indent=2)

with open('best_lambdas.json', 'w') as fh:
    json.dump(best_lambdas, fh, indent=2)

print('\nSaved results.json and best_lambdas.json')
print('\nBest λ per benchmark:')
for name, lam in best_lambdas.items():
    print(f'  {name}: λ={lam}')