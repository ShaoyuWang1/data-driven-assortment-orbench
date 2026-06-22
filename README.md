# Data-Driven Assortment Optimization — OR-Bench Contribution

## Overview

A data-driven assortment optimization problem: a firm chooses an assortment of products to offer to
future customers, using only past transaction records, by maximizing a worst-case revenue defined
directly from the data — no choice model is estimated. The full problem statement is in
`text_description.md` (and in each row's `Text Description`).

This is the end-to-end problem of Chen, Cire, Gao, and Wang, *Assortment Optimization without
Prediction: An End-to-end Framework with Transaction Data*; it is NP-hard.

## What the dataset contains

`OR-Bench Dataset.csv` has one row per instance with the standard OR-Bench fields:

| Field | Description |
|---|---|
| `Problem ID` | Unique instance identifier (1–240) |
| `Text Description` | Natural-language problem statement|
| `Domain` | `Revenue Management` |
| `Dataset_address` | Path to the instance's input CSV (`Data/n../m..._..csv`) |
| `Optimal Value` | Ground-truth optimal objective value $R(S^\star)$ |
| `Optimal Solution` | Ground-truth optimal assortment $S^\star$ (set of offered products), e.g. `S* = {1, 2, 4}` |

## Instances

240 instances on the grid **n ∈ {4, 6, 8, 10}** products × **m ∈ {50, 100, 200}** transactions,
with **20 instances per (n, m)**. Each instance is one self-contained CSV under `Data/`:

```
Data/n04/m050_01.csv … m050_20.csv  m100_01.csv … m200_20.csv
Data/n06/ …   Data/n08/ …   Data/n10/ …
```

**Data format.** Every row of an instance CSV is one transaction, with columns

```
price_1, …, price_n, offered_1, …, offered_n, choice
```

- `price_j` — the price of product `j` (constant down the column; each instance has its **own**
  random prices).
- `offered_j ∈ {0,1}` — whether product `j` was shown in that transaction.
- `choice ∈ {0,…,n}` — the purchased product (`0` = no purchase).

`n` = number of `price_*` columns, `m` = number of rows; the no-purchase option `0` (price `0`) is
implicit. A 3-product, 3-transaction example:

```
price_1,price_2,price_3,offered_1,offered_2,offered_3,choice
10,6,5,1,0,0,1
10,6,5,0,1,0,2
10,6,5,1,1,0,1
```

Each instance's transactions are drawn from a hidden MNL data-generating process (see
**Data generation**); that model is not part of the problem and is not shipped. The answer is the
optimum of the data-driven problem on the transactions, which in general differs from the generating
model's optimal assortment. In every instance the optimal assortment includes the most profitable
(highest-priced) product.

## Data generation

The transaction data are synthetic, produced by `generate_benchmark.py`. For each instance:

1. **Prices.** Draw `n` distinct prices uniformly from `[1, 10]` (rounded to 2 decimals) and sort
   them descending, so product `1` is the most expensive. Prices are drawn fresh per instance.
2. **Hidden choice model (MNL).** Draw multinomial-logit utilities with no-purchase utility
   `v_0 = 1` and `v_j ~ Uniform[0.2, 2.5]` per product. This model is used **only** to generate
   plausible transactions; it is never revealed and is **not** the answer.
3. **Transactions.** For each of the `m` records, offer each product independently with probability
   `0.5` (resampling to guarantee at least one offered product), then draw the customer's choice
   from the MNL distribution over the offered products plus the no-purchase option.
4. **Selection.** Compute the certified optimum and keep the instance only if its optimal assortment
   contains the most profitable product (product `1`) and is not the full set; among candidate seeds
   we prefer instances whose optimum beats the revenue-ordered and offer-all heuristics by ≥ 3%.
   Seeds are scanned deterministically and duplicate datasets are skipped.
5. **Certification.** Each kept instance's optimum is computed by exhaustive `2^n` brute force and
   cross-checked against the direct MIP (`solver_direct.py`); a sample is also checked with the
   Benders solver. The recorded `Optimal Value` / `Optimal Solution` are these certified values.

Re-running `python generate_benchmark.py` rebuilds the full `Data/` tree and `OR-Bench Dataset.csv`
from fixed seeds. The answer to each instance is the optimum of the **data-driven** problem on the
transactions, which need not coincide with the optimal assortment of the hidden MNL that produced
the data.

## Reference formulation and solver code

The mathematical formulation (the hidden reference) is provided two ways:

- `formulation/milp_direct.md` — the direct mixed-integer linear program **(SP-I)**.
- `formulation/benders.md` — the **Benders / branch-and-cut** formulation with one epigraph variable
  per transaction and lazily separated optimality cuts.

Working Gurobi (Python) solvers, one per formulation:

- `solver_direct.py` — solves (SP-I).
- `solver_benders.py` — solves via Benders / branch-and-cut.

**Setup.** Python 3 with the packages in `requirements.txt` (`gurobipy`, `numpy`). Gurobi requires
a license — a free academic license is available at gurobi.com; the instances here ($n \le 10$) also
solve under Gurobi's restricted trial license.

```bash
pip install -r requirements.txt
```

**Run a solver on any instance** (pass the single instance CSV):

```bash
python solver_direct.py  Data/n08/m100_01.csv
python solver_benders.py Data/n08/m100_01.csv
```

The solver reads the instance CSV, solves the model, and prints the optimal value and assortment
(see example below). `solver_direct.py` needs only `gurobipy`; `generate_benchmark.py` also uses
`numpy`.

Each prints the optimal value $R(S^\star)$ and the optimal assortment $S^\star$. Example output:

```json
{ "n": 8, "m": 100, "optimal_value": 2.61, "optimal_solution": "S* = {2, 4, 6}" }
```

**Regenerate everything:** `python generate_benchmark.py` rebuilds `Data/` and
`OR-Bench Dataset.csv` from scratch and certifies every instance (brute force == direct MIP, with
Benders cross-checks).

## Reference

N. Chen, A. Cire, P. Gao, S. Wang. *Assortment Optimization without Prediction: An End-to-end
Framework with Transaction Data.*
