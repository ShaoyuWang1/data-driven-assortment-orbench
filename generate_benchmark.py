"""
Build the OR-Bench submission package for the Data-Driven Assortment problem.

    OR-Bench Dataset.csv          # Problem ID, Text Description, Domain,
                                  #   Dataset_address, Optimal Value, Optimal Solution
    Data/
      n10/ m100_01.csv ... m300_20.csv      (one self-contained CSV per instance)
      n20/ ...   n30/ ...

Grid: n in {10,20,30}; m in {100,200,300}; 20 instances per (n,m)  ->  180 instances.

Each instance is ONE self-contained CSV with columns
    price_1,...,price_n, offered_1,...,offered_n, choice
(price_j constant down its column; each instance has its own random prices). Transactions
come from a HIDDEN MNL (data-generating process only; not shipped, not the answer).

Ground-truth optima are computed with the BENDERS solver (fastest at this scale). They are
certified independently: brute force for n=10 (every instance) and the SP-I MILP on a sample
of the larger instances.
"""

import os
import csv
import numpy as np

from solver_benders import solve_benders     # ground-truth optimizer (fast)
from solver_direct import solve_direct        # independent MILP cross-check (sampled)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "Data")
GRID_N = [10, 20, 30]
GRID_M = [100, 200, 300]
N_PER = 20
DOMAIN = "Revenue Management"
TEXT_DESC = open(os.path.join(HERE, "text_description.md")).read()


# closed-form objective + brute-force oracle (brute force used only to certify n=10)
def _f(S, I_i, c_i, prices):
    if c_i == 0 or c_i not in S:
        return 0.0
    return min(prices[j] for j in ({c_i} | (set(S) - set(I_i))))

def revenue(S, prices, records):
    return sum(_f(S, I, c, prices) for (I, c) in records) / len(records)

def brute_force(n, prices, records):
    import itertools
    best_S, best_R = [], -1.0
    for r in range(n + 1):
        for combo in itertools.combinations(range(1, n + 1), r):
            R = revenue(set(combo), prices, records)
            if R > best_R + 1e-12:
                best_R, best_S = R, sorted(combo)
    return best_S, best_R

def ro_best(n, prices, records):
    return max(revenue(set(range(1, k + 1)), prices, records) for k in range(n + 1))


def gen_prices(n, rng):
    while True:
        vals = np.round(rng.uniform(1.0, 10.0, size=n), 2)
        if len(set(vals.tolist())) == n:
            break
    return [0.0] + sorted(vals.tolist(), reverse=True)        # p_1 > ... > p_n

def gen_records(n, m, prices, rng):
    v = np.concatenate([[1.0], rng.uniform(0.2, 2.5, size=n)])   # hidden MNL
    recs = []
    for _ in range(m):
        offered = [j for j in range(1, n + 1) if rng.random() < 0.5]
        if not offered:
            offered = [int(rng.integers(1, n + 1))]
        support = [0] + offered
        w = np.array([v[j] for j in support]); w = w / w.sum()
        recs.append((frozenset(offered), int(rng.choice(support, p=w))))
    return recs


def pick_instance(n, m, base_seed, seen, budget=15):
    """Scan seeds (own random prices+data); optimum via Benders; prefer discriminating."""
    fallback, fallback_sig = None, None
    for t in range(budget):
        rng = np.random.default_rng(base_seed * 100003 + t)
        prices = gen_prices(n, rng)
        recs = gen_records(n, m, prices, rng)
        sig = (tuple(prices), tuple(sorted((tuple(sorted(I)), c) for (I, c) in recs)))
        if sig in seen or all(c == 0 for (_, c) in recs):
            continue
        S, R = solve_benders(n, prices, recs)                 # <-- Benders, per request
        if (1 not in S) or (len(S) == n):                     # most-profitable in S*, non-full
            continue
        heur = max(ro_best(n, prices, recs), revenue(set(range(1, n + 1)), prices, recs))
        disc = R >= heur * 1.03
        cand = (prices, recs, S, R, disc, heur)
        if disc:
            seen.add(sig); return cand
        if fallback is None or R - heur > fallback[3] - fallback[5]:
            fallback, fallback_sig = cand, sig
    if fallback:
        seen.add(fallback_sig)
    return fallback


def write_instance(path, n, prices, records):
    header = [f"price_{j}" for j in range(1, n + 1)] + \
             [f"offered_{j}" for j in range(1, n + 1)] + ["choice"]
    pvals = [prices[j] for j in range(1, n + 1)]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(header)
        for (I_i, c_i) in records:
            w.writerow(pvals + [1 if j in I_i else 0 for j in range(1, n + 1)] + [c_i])


def main():
    rows, pid, n_disc, brute_checks, spi_checks = [], 0, 0, 0, 0
    for n in GRID_N:
        ndir = os.path.join(DATA, f"n{n:02d}")
        os.makedirs(ndir, exist_ok=True)
        seen = set()
        for m in GRID_M:
            for idx in range(1, N_PER + 1):
                pid += 1
                cand = pick_instance(n, m, base_seed=pid, seen=seen)
                assert cand is not None, f"no instance for n={n}, m={m}, idx={idx}"
                prices, recs, S, R, disc, heur = cand
                n_disc += int(disc)

                fname = f"m{m:03d}_{idx:02d}.csv"
                write_instance(os.path.join(ndir, fname), n, prices, recs)

                # certification (independent of Benders)
                if n == 10:
                    _, Rb = brute_force(n, prices, recs)
                    assert abs(Rb - R) < 1e-6, f"brute != benders at pid {pid}"
                    brute_checks += 1
                elif pid % 25 == 0:
                    _, Rd = solve_direct(n, prices, recs)
                    assert abs(Rd - R) < 1e-6, f"SP-I != benders at pid {pid}"
                    spi_checks += 1

                rows.append({
                    "Problem ID": pid,
                    "Text Description": TEXT_DESC,
                    "Domain": DOMAIN,
                    "Dataset_address": f"Data/n{n:02d}/{fname}",
                    "Optimal Value": round(R, 6),
                    "Optimal Solution": "S* = {" + ", ".join(str(j) for j in S) + "}",
                })
        print(f"n={n} done")

    out_csv = os.path.join(HERE, "OR-Bench Dataset.csv")
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["Problem ID", "Text Description", "Domain",
                                           "Dataset_address", "Optimal Value", "Optimal Solution"])
        w.writeheader(); w.writerows(rows)

    print(f"wrote {len(rows)} instances -> {out_csv}")
    print(f"discriminating (opt beats heuristics by >=3%): {n_disc}/{len(rows)}")
    print(f"certified: brute force (n=10) x{brute_checks}, SP-I cross-check x{spi_checks}")


if __name__ == "__main__":
    main()
