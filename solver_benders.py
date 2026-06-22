"""
Reference solver #2 -- BENDERS decomposition (branch-and-cut with lazy optimality
cuts), solved with Gurobi.

Same problem as solver_direct.py:
    max_{S}  R(S) = (1/m) sum_i f(S, c_i, I_i),
    f(S, c_i, I_i) = 0                                    if c_i = 0 or c_i not in S,
                   = min{ p_j : j in {c_i} U (S \\ I_i) }   if c_i in S.

Instead of the extended SP-I formulation, we keep only the assortment binaries U_j
and one continuous epigraph variable theta_i per record (theta_i models f). The inner
"customer subproblem" is solved in closed form inside a lazy-constraint callback, and
the corresponding optimality cut is added on the fly -- i.e. branch-and-cut.

Master:
    max  (1/m) sum_i theta_i
    s.t. theta_i = 0                      if c_i = 0
         theta_i <= p_{c_i} * U_{c_i}     if c_i != 0      (no revenue unless c_i offered)
         U_j in {0,1},  theta_i >= 0

Lazy optimality cut (added whenever, at an incumbent S, theta_i exceeds f(S,c_i,I_i)):
    let j*(S,i) = argmin{ p_j : j in (S \\ I_i), p_j < p_{c_i} }, or c_i if that set is empty.
        theta_i <= p_{c_i} - (p_{c_i} - p_{j*}) * U_{j*}
    Valid globally: if U_{j*}=1 then theta_i <= p_{j*} (a feasible substitute), else
    theta_i <= p_{c_i}; both upper-bound f for every assortment.

Reference: Chen, Cire, Gao, Wang, "Assortment Optimization without Prediction:
An End-to-end Framework with Transaction Data" (Benders / branch-and-cut solution method).

Usage:
    python solver_benders.py <prices.csv> <transactions.csv>
    python solver_benders.py <instance_dir>
"""

import sys
import json

from solver_direct import load_instance   # reuse the shared CSV reader


def _worst_substitute(S_set, I_i, c_i, prices):
    """j*(S,i): cheapest offered product not shown to i and cheaper than c_i; else c_i."""
    cands = [j for j in S_set if j not in I_i and prices[j] < prices[c_i]]
    if not cands:
        return c_i
    return min(cands, key=lambda j: prices[j])


def solve_benders(n, prices, records):
    """Solve via Benders / branch-and-cut. Returns (S_sorted, optimal_value)."""
    import gurobipy as gp
    from gurobipy import GRB

    m = len(records)
    model = gp.Model("SP-Benders")
    model.Params.OutputFlag = 0
    model.Params.LazyConstraints = 1

    U = model.addVars(range(1, n + 1), vtype=GRB.BINARY, name="U")
    theta = model.addVars(range(m), lb=0.0, name="theta")

    for i, (I_i, c_i) in enumerate(records):
        if c_i == 0:
            model.addConstr(theta[i] == 0)
        else:
            model.addConstr(theta[i] <= prices[c_i] * U[c_i])   # no offer -> no revenue

    model.setObjective((1.0 / m) * gp.quicksum(theta[i] for i in range(m)), GRB.MAXIMIZE)

    def callback(mod, where):
        if where != GRB.Callback.MIPSOL:
            return
        Uval = mod.cbGetSolution(U)
        thval = mod.cbGetSolution(theta)
        S = {j for j in range(1, n + 1) if Uval[j] > 0.5}
        for i, (I_i, c_i) in enumerate(records):
            if c_i == 0 or c_i not in S:
                continue
            js = _worst_substitute(S, I_i, c_i, prices)
            f_val = prices[js]                                   # worst-case revenue at S
            if thval[i] > f_val + 1e-9:
                mod.cbLazy(theta[i] <= prices[c_i]
                           - (prices[c_i] - prices[js]) * U[js])

    model.optimize(callback)
    S = sorted(j for j in range(1, n + 1) if U[j].X > 0.5)
    return S, model.ObjVal


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python solver_benders.py <instance.csv>")
    n, prices, records = load_instance(sys.argv[1])
    S, opt = solve_benders(n, prices, records)
    print(json.dumps({
        "n": n, "m": len(records),
        "optimal_value": round(opt, 6),
        "optimal_solution": "S* = {" + ", ".join(str(j) for j in S) + "}",
    }, indent=2))
