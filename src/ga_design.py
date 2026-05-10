"""
ga_design.py

Improved Genetic Algorithm for processor architecture design.
Matches Section "Automatic Processor Architecture Design Flow" of the paper.

Key parameters (paper, Section "Parameter Setting"):
  Population size  : 200
  Crossover prob   : 0.75
  Mutation prob    : 0.15
  Max generations  : 300
  Early stop       : last 100 gens, 50 consecutive no-change → stop
  α = β = 0.5
  λ ∈ [1, 6]

The fitness function is  Fit(G) = -f(G)  where:
  f(G) = α × Σd(i,j) + β × λ × Δ(G)   if G is connected
  f(G) = ∞ (→ -200 in practice)         if G is disconnected

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
λ SWEEP: FINDING THE BEST ARCHITECTURE PER BENCHMARK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The paper states: "λ takes different values depending on different
quantum programs. In this paper, the value range of λ is 1~6."

Rather than fixing λ = 6 for all benchmarks, `evolve_best_lambda`
runs the GA for every integer λ in {1, 2, 3, 4, 5, 6} and selects
the architecture with the best combined (gate count, yield) outcome.

Selection criterion — matches Fig. 12 of the paper ("top-left is best"):
  score(G) = −gates_norm + yield_norm
           = −(gates / max_gates_across_λ) + (yield / max_yield_across_λ)

Both metrics are normalised to [0,1] across the six λ runs so that
neither dominates.  The architecture with the highest score is returned.

If you only want the graph (no gate-count / yield evaluation), call
`evolve(A, n, lam)` directly with a fixed λ as before.

CALLER RESPONSIBILITIES
  The caller (`run_all.py`) must supply evaluate_fn, a callable:
      evaluate_fn(edges) → (gate_count, yield_rate)
  This avoids circular imports between ga_design ↔ perf_eval / freq_alloc.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import random
import numpy as np
import networkx as nx
from .arch_graph import build_arch_graph

POP            = 200
P_CX           = 0.75
P_MUT          = 0.15
GENS           = 300
ALPHA          = 0.5
BETA           = 0.5
LAMBDA_DEFAULT = 6      # kept for backward-compat; sweep uses 1..6

LAMBDA_RANGE   = list(range(1, 7))   # [1, 2, 3, 4, 5, 6]


def grid_size(n):
    if n <= 4:  return 2, 2
    if n <= 9:  return 3, 3
    if n <= 16: return 4, 4
    if n <= 25: return 5, 5
    return 6, 6


def random_individual(n, w, h, rng):
    cells = [(x, y) for x in range(w) for y in range(h)]
    rng.shuffle(cells)
    return cells[:n]


# ── Fitness ───────────────────────────────────────────────────────────────────

def fitness(ind, A, w, h, lam=LAMBDA_DEFAULT):
    """
    Evaluates both Constraint-3 pruning variants (Algorithm 3) and returns
    (best_fitness_value, best_graph).  Higher fitness = lower f(G) = better.
    """
    G1, G2 = build_arch_graph(ind, A, w, h)

    def f(G):
        if not nx.is_connected(G):
            return 200.0
        n = len(ind)
        s = 0
        for i in range(n):
            for j in range(i + 1, n):
                if A[i][j] == 1 and not G.has_edge(i, j):
                    try:
                        s += nx.shortest_path_length(G, i, j)
                    except nx.NetworkXNoPath:
                        return 200.0
        degs    = dict(G.degree()).values()
        max_deg = max(degs) if degs else 0
        return ALPHA * s + BETA * lam * max_deg

    f1, f2 = f(G1), f(G2)
    if f1 <= f2:
        return -f1, G1
    return -f2, G2


# ── GA operators ─────────────────────────────────────────────────────────────

def tournament(pop, fits, k=2):
    """Binary tournament selection (Algorithm 4)."""
    idx = random.sample(range(len(pop)), k)
    return pop[max(idx, key=lambda i: fits[i])]


def crossover(p1, p2):
    """
    Single-point crossover (Algorithm 5).
    Duplicate-coordinate children fall back to a randomly chosen parent.
    """
    pt = random.randrange(1, len(p1))
    c1 = p1[:pt] + p2[pt:]
    c2 = p2[:pt] + p1[pt:]

    num_fail = 0
    if len(set(c1)) != len(c1):
        num_fail += 1
        c1 = random.choice([p1, p2])[:]
    if len(set(c2)) != len(c2):
        num_fail += 1
        if num_fail == 1:
            c2 = random.choice([p1, p2])[:]
        else:                                   # both failed
            c2 = (p2 if c1 == p1 else p1)[:]
    return c1, c2


def mutate(ind, w, h):
    """
    Mutation (Algorithm 6):
      free cell exists  → move (p=0.5) or swap (p=0.5)
      grid full         → swap two qubits
    """
    occupied = set(ind)
    free = [(x, y) for x in range(w) for y in range(h)
            if (x, y) not in occupied]
    idx = random.randrange(len(ind))

    if free and random.random() >= 0.5:
        ind[idx] = random.choice(free)
    else:
        j = random.randrange(len(ind))
        while j == idx:
            j = random.randrange(len(ind))
        ind[idx], ind[j] = ind[j], ind[idx]
    return ind


# ── Main GA loop ──────────────────────────────────────────────────────────────

def evolve(A, n, lam=LAMBDA_DEFAULT, seed=0):
    """
    Returns (best_coord_vector, best_arch_graph) for a single fixed λ.

    A   : n×n upper-triangular 0/1 adjacency matrix
    n   : number of logical qubits
    lam : λ ∈ [1, 6]  (paper range)
    seed: RNG seed for reproducibility
    """
    random.seed(seed)
    np.random.seed(seed)
    rng = random.Random(seed)

    w, h = grid_size(n)
    pop  = [random_individual(n, w, h, rng) for _ in range(POP)]
    fits = [fitness(ind, A, w, h, lam)[0] for ind in pop]

    best_idx  = int(np.argmax(fits))
    best      = pop[best_idx][:]
    best_fit  = fits[best_idx]
    no_change = 0

    for gen in range(GENS):
        offspring = []
        while len(offspring) < POP:
            p1 = tournament(pop, fits)
            p2 = tournament(pop, fits)
            if random.random() < P_CX:
                c1, c2 = crossover(p1, p2)
            else:
                c1, c2 = p1[:], p2[:]
            if random.random() < P_MUT:
                c1 = mutate(c1, w, h)
            if random.random() < P_MUT:
                c2 = mutate(c2, w, h)
            offspring += [c1, c2]
        offspring = offspring[:POP]

        off_fits = [fitness(ind, A, w, h, lam)[0] for ind in offspring]

        # Elite replacement
        worst = int(np.argmin(off_fits))
        if best_fit > off_fits[worst]:
            offspring[worst] = best[:]
            off_fits[worst]  = best_fit

        pop, fits = offspring, off_fits

        cur_best = max(fits)
        if cur_best > best_fit:
            best_fit  = cur_best
            best      = pop[int(np.argmax(fits))][:]
            no_change = 0
        else:
            no_change += 1

        # Early stopping: gen ≥ 200 AND 50 consecutive no-change
        if gen >= 200 and no_change >= 50:
            break

    _, G = fitness(best, A, w, h, lam)
    return best, G


# ── Lambda sweep ──────────────────────────────────────────────────────────────

def evolve_best_lambda(A, n, evaluate_fn, seed=0, verbose=True):
    """
    Run the GA for every λ in {1, 2, 3, 4, 5, 6} and return the architecture
    that achieves the best combined (gate count ↓, yield ↑) outcome.

    Parameters
    ----------
    A           : n×n upper-triangular 0/1 adjacency matrix
    n           : number of logical qubits
    evaluate_fn : callable  edges → (gate_count: float, yield_rate: float)
                  Caller supplies this to keep ga_design free of perf/freq deps.
                  edges is a list of (int, int) pairs from G.edges().
    seed        : base RNG seed; each λ uses (seed + lam) for independence
    verbose     : print per-λ results if True

    Returns
    -------
    best_G      : networkx.Graph  — the winning architecture graph
    best_lam    : int             — the λ value that produced it
    best_gates  : float           — gate count for the winner
    best_yield  : float           — yield rate for the winner
    all_results : list of dicts   — full results for all 6 λ values
    """
    all_results = []

    for lam in LAMBDA_RANGE:
        lam_seed = seed + lam   # distinct seed per λ so runs are independent
        _, G = evolve(A, n, lam=lam, seed=lam_seed)
        edges = list(G.edges())
        gates, yr = evaluate_fn(edges)

        entry = {
            'lam'  : lam,
            'gates': gates,
            'yield': yr,
            'G'    : G,
        }
        all_results.append(entry)

        if verbose:
            print(f'    λ={lam}  gates={gates:.1f}  yield={yr:.4f}')

    # ── Normalise both metrics to [0, 1] across the 6 λ runs ─────────────────
    # Use safe normalisation: if all values identical, treat all as equal (0.5).
    gates_vals = [r['gates'] for r in all_results]
    yield_vals = [r['yield'] for r in all_results]

    g_min, g_max = min(gates_vals), max(gates_vals)
    y_min, y_max = min(yield_vals), max(yield_vals)

    def norm_gates(g):
        if g_max == g_min:
            return 0.5
        return (g - g_min) / (g_max - g_min)   # 0 = fewest gates (best)

    def norm_yield(y):
        if y_max == y_min:
            return 0.5
        return (y - y_min) / (y_max - y_min)   # 1 = highest yield (best)

    # Score: maximise yield, minimise gates → score = yield_norm − gates_norm
    # Higher score = closer to top-left in Fig. 12.
    best_entry = max(
        all_results,
        key=lambda r: norm_yield(r['yield']) - norm_gates(r['gates'])
    )

    if verbose:
        print(f'    ✓ Best λ={best_entry["lam"]}  '
              f'gates={best_entry["gates"]:.1f}  '
              f'yield={best_entry["yield"]:.4f}')

    return (
        best_entry['G'],
        best_entry['lam'],
        best_entry['gates'],
        best_entry['yield'],
        all_results,
    )