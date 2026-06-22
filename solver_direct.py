"""
Reference solver #1 -- DIRECT mixed-integer program (SP-I), solved with Gurobi.

Data-Driven Assortment Optimization (Seller's Problem, SP):
    max_{S subseteq {1..n}}  R(S) = (1/m) sum_i f(S, c_i, I_i),
    f(S, c_i, I_i) = 0                                    if c_i = 0 or c_i not in S,
                   = min{ p_j : j in {c_i} U (S \\ I_i) }   if c_i in S.

DIRECT MILP reformulation (SP-I); prices need not be pre-sorted (we compare prices):
    Sets, per customer i (with c_i != 0):
        L_{c_i} = { j : p_j < p_{c_i} }                       (products cheaper than c_i)
        G_i     = {c_i} U ( ({1..n} \\ I_i) cap L_{c_i} )       (consideration set)
    Variables:  U_j in {0,1}  (offer j?),  x_{ij} in [0,1]  (i ends up buying j, j in G_i)
    max  sum_i sum_{j in G_i} (1/m) p_j x_{ij}
    s.t. x_{ij} <= U_j                              for all i, j in G_i
         x_{ij} <= 1 - U_k    for all i, j in G_i, k in G_i with p_k < p_j
         x_{ij} <= U_{c_i}                          for all i, j in G_i

Reference: Chen, Cire, Gao, Wang, "Assortment Optimization without Prediction:
An End-to-end Framework with Transaction Data" (Proposition: equivalence of SP and SP-I).

Input format -- one self-contained CSV per instance, columns:
    price_1,...,price_n, offered_1,...,offered_n, choice
where price_j is the (constant) price of product j, offered_j in {0,1} marks whether
product j was shown in that transaction, and choice in {0,...,n} is the purchased product
(0 = no purchase). Each row is one transaction.

Usage:
    python solver_direct.py <instance.csv>
"""

import sys
import csv
import json


def load_instance(instance_csv):
    """Read a single self-contained instance CSV.

    Returns n, prices[0..n] (prices[0]=0), records=[(frozenset I_i, c_i), ...].
    """
    with open(instance_csv, newline="") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames
        price_cols = sorted((c for c in cols if c.startswith("price_")),
                            key=lambda c: int(c.split("_")[1]))
        n = len(price_cols)
        rows = list(reader)

    prices = [0.0] + [float(rows[0][f"price_{j}"]) for j in range(1, n + 1)]
    records = []
    for row in rows:
        # prices are constant across rows; sanity-check the first few
        offered = frozenset(j for j in range(1, n + 1) if int(row[f"offered_{j}"]) == 1)
        c = int(row["choice"])
        assert c == 0 or c in offered, f"choice {c} must be 0 or an offered product"
        records.append((offered, c))
    return n, prices, records


def solve_direct(n, prices, records, lp_path=None):
    """Solve (SP-I) with Gurobi. Returns (S_sorted, optimal_value)."""
    import gurobipy as gp
    from gurobipy import GRB

    m = len(records)
    model = gp.Model("SP-I")
    model.Params.OutputFlag = 0
    U = model.addVars(range(1, n + 1), vtype=GRB.BINARY, name="U")

    G, x = [], {}
    for i, (I_i, c_i) in enumerate(records):
        if c_i == 0:
            G.append(set()); continue
        G_i = {c_i} | {j for j in range(1, n + 1) if j not in I_i and prices[j] < prices[c_i]}
        G.append(G_i)
        for j in G_i:
            x[i, j] = model.addVar(lb=0.0, ub=1.0, name=f"x_{i}_{j}")

    model.setObjective(
        gp.quicksum((1.0 / m) * prices[j] * x[i, j] for i in range(m) for j in G[i]),
        GRB.MAXIMIZE)

    for i, (I_i, c_i) in enumerate(records):
        for j in G[i]:
            model.addConstr(x[i, j] <= U[j])
            model.addConstr(x[i, j] <= U[c_i])
            for k in G[i]:
                if prices[k] < prices[j]:
                    model.addConstr(x[i, j] <= 1 - U[k])

    model.optimize()
    if lp_path:
        model.write(lp_path)
    S = sorted(j for j in range(1, n + 1) if U[j].X > 0.5)
    return S, model.ObjVal


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python solver_direct.py <instance.csv>")
    n, prices, records = load_instance(sys.argv[1])
    S, opt = solve_direct(n, prices, records)
    print(json.dumps({
        "n": n, "m": len(records),
        "optimal_value": round(opt, 6),
        "optimal_solution": "S* = {" + ", ".join(str(j) for j in S) + "}",
    }, indent=2))
