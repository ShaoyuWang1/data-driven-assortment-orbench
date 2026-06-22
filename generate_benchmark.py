"""
Build the full OR-Bench submission package for the Data-Driven Assortment problem.

Layout produced:

    OR-Bench Dataset.csv          # 240 rows: Problem ID, Text Description, Domain,
                                  #           Dataset_address, Optimal Value, Optimal Solution
    Data/
      n04/ m050_01.csv ... m200_20.csv      (one self-contained CSV per instance)
      n06/ ...   n08/ ...   n10/ ...

Grid: n in {4,6,8,10}; m in {50,100,200}; 20 instances per (n,m)  ->  240 instances.

Each instance is ONE self-contained CSV with columns
    price_1,...,price_n, offered_1,...,offered_n, choice
where price_j (constant down the column) is the price of product j, offered_j in {0,1}
marks whether product j was shown in that transaction, and choice in {0,...,n} is the
purchased product (0 = no purchase). Every instance has its OWN random prices.

Transactions are drawn from a HIDDEN MNL model (data-generating process only -- not the
answer, not shipped). Each instance's optimum is certified by brute force == direct MIP
(SP-I); a sample is also cross-checked with the Benders solver. Where possible we prefer
"discriminating" instances whose optimum beats the revenue-ordered and offer-all
heuristics by >= 3%.
"""

import os
import csv
import numpy as np

from solver_direct import solve_direct
from solver_benders import solve_benders


# closed-form objective + brute-force oracle (used here for generation-time certification)
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

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "Data")
GRID_N = [4, 6, 8, 10]
GRID_M = [50, 100, 200]
N_PER = 20
DOMAIN = "Revenue Management"
TEXT_DESC = open(os.path.join(HERE, "text_description.md")).read()


def gen_prices(n, rng):
    """Per-instance distinct prices, sorted descending (product 1 = most expensive)."""
    while True:
        vals = np.round(rng.uniform(1.0, 10.0, size=n), 2)
        if len(set(vals.tolist())) == n:
            break
    return [0.0] + sorted(vals.tolist(), reverse=True)   # p_1 > ... > p_n


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


def ro_best(n, prices, records):
    return max(revenue(set(range(1, k + 1)), prices, records) for k in range(n + 1))


def pick_instance(n, m, base_seed, seen, budget=250):
    """Scan seeds (each with its own random prices+data); prefer discriminating."""
    fallback = None
    for t in range(budget):
        rng = np.random.default_rng(base_seed * 100003 + t)
        prices = gen_prices(n, rng)
        recs = gen_records(n, m, prices, rng)
        sig = (tuple(prices), tuple(sorted((tuple(sorted(I)), c) for (I, c) in recs)))
        if sig in seen or all(c == 0 for (_, c) in recs):
            continue
        S, R = brute_force(n, prices, recs)
        # require the most-profitable product (1) in the optimum, and a non-full assortment
        if (1 not in S) or (len(S) == n):
            continue
        heur = max(ro_best(n, prices, recs), revenue(set(range(1, n + 1)), prices, recs))
        disc = R >= heur * 1.03
        cand = (prices, recs, sig, S, R, disc, heur)
        if disc:
            seen.add(sig)
            return cand
        if fallback is None or R - heur > fallback[4] - fallback[6]:
            fallback = cand
    if fallback:
        seen.add(fallback[2])
    return fallback


def write_instance(path, n, prices, records):
    header = [f"price_{j}" for j in range(1, n + 1)] + \
             [f"offered_{j}" for j in range(1, n + 1)] + ["choice"]
    pvals = [prices[j] for j in range(1, n + 1)]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for (I_i, c_i) in records:
            w.writerow(pvals + [1 if j in I_i else 0 for j in range(1, n + 1)] + [c_i])


def main():
    rows, pid, n_disc, benders_checks = [], 0, 0, 0
    for n in GRID_N:
        ndir = os.path.join(DATA, f"n{n:02d}")
        os.makedirs(ndir, exist_ok=True)
        seen = set()
        for m in GRID_M:
            for idx in range(1, N_PER + 1):
                pid += 1
                cand = pick_instance(n, m, base_seed=pid, seen=seen)
                assert cand is not None, f"no instance for n={n}, m={m}, idx={idx}"
                prices, recs, sig, S, R, disc, heur = cand
                n_disc += int(disc)

                fname = f"m{m:03d}_{idx:02d}.csv"
                write_instance(os.path.join(ndir, fname), n, prices, recs)

                # certify: independent brute force == direct MIP; sample-check Benders
                S_d, R_d = solve_direct(n, prices, recs)
                assert abs(R_d - R) < 1e-6, f"direct != brute at pid {pid}"
                if pid % 30 == 0:
                    _, R_b = solve_benders(n, prices, recs)
                    assert abs(R_b - R) < 1e-6, f"benders != brute at pid {pid}"
                    benders_checks += 1

                sol = "S* = {" + ", ".join(str(j) for j in S) + "}"
                desc = f"In this instance, $n = {n}$ and $m = {m}$.\n\n" + TEXT_DESC
                rows.append({
                    "Problem ID": pid,
                    "Text Description": desc,
                    "Domain": DOMAIN,
                    "Dataset_address": f"Data/n{n:02d}/{fname}",
                    "Optimal Value": round(R, 6),
                    "Optimal Solution": sol,
                })

    out_csv = os.path.join(HERE, "OR-Bench Dataset.csv")
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["Problem ID", "Text Description", "Domain",
                                           "Dataset_address", "Optimal Value", "Optimal Solution"])
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {len(rows)} instances -> {out_csv}")
    print(f"discriminating (opt beats heuristics by >=3%): {n_disc}/{len(rows)}")
    print(f"benders cross-checks passed: {benders_checks}")


if __name__ == "__main__":
    main()
