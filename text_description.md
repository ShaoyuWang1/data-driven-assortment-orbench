# Data-Driven Assortment Optimization from Transaction Records

A firm sells products $1, \dots, n$, each with a distinct price $p_j > 0$; a no-purchase option $0$
has $p_0 = 0$. Transaction $i$ ($i = 1, \dots, m$) records the offered set $I_i \subseteq \{1,\dots,n\}$
shown to a past customer and the product $c_i \in \{0\} \cup I_i$ she chose ($c_i = 0$ = no purchase).

**Data file.** Each instance is one CSV; every row is a transaction with columns
`price_1, …, price_n, offered_1, …, offered_n, choice`. Here `price_j` (constant down its column) is
the price $p_j$; `offered_j` $\in \{0,1\}$ is $1$ iff product $j$ was shown ($I_i = \{j : \texttt{offered\_j}=1\}$);
and `choice` $\in \{0,\dots,n\}$ is $c_i$. So $n$ is the number of `price_*` columns and $m$ the number
of rows; product $0$ (price $0$) is implicit.

**What a transaction reveals.** Choosing $c_i$ reveals only a partial preference: the customer liked
$c_i$ at least as much as every other offered product and as not buying, i.e. $c_i \succeq j$ for all
$j \in \{0\} \cup I_i$. Nothing is revealed about products not shown to her. Let $\Sigma_i$ be the set
of strict rankings of $\{0, 1, \dots, n\}$ consistent with this partial order.

**Objective.** The firm offers one assortment $S \subseteq \{1, \dots, n\}$ (option $0$ is always
available). A future customer who shares the preference of past customer $i$ buys the highest-ranked
product of $S$ under her ranking $\sigma \in \Sigma_i$, or nothing if $0$ outranks all of $S$. Since
$\sigma$ is known only to lie in $\Sigma_i$, the firm scores $S$ by the worst case
$$f(S, c_i, I_i) = \min_{\sigma \in \Sigma_i} p_{\pi(S, \sigma)},$$
where $\pi(S, \sigma)$ is the product bought (price $0$ if no purchase). Treating a future customer as
equally likely to match any one of the $m$ past customers, choose $S$ to maximize
$$R(S) = \frac{1}{m} \sum_{i=1}^{m} f(S, c_i, I_i).$$
Report an optimal assortment $S^\star$ and the optimal value $R(S^\star)$.
