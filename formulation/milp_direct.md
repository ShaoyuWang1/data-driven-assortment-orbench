# Direct MILP formulation (SP-I)

Notation: products $1,\dots,n$ with distinct prices $p_1 > \cdots > p_n$ and no-purchase price
$p_0 = 0$; transactions $(I_i, c_i)$, $i = 1,\dots,m$, with offered set $I_i$ and choice
$c_i \in \{0\} \cup I_i$. For each $i$ with $c_i \neq 0$, let
$G_i = \{c_i\} \cup \{\, j \notin I_i : p_j < p_{c_i} \,\}$. Variables: $U_j \in \{0,1\}$ (offer
product $j$) and $x_{ij} \in [0,1]$ for $j \in G_i$.

$$
\begin{aligned}
\max_{U,\,x}\quad & \frac{1}{m}\sum_{i=1}^{m}\sum_{j \in G_i} p_j\, x_{ij}\\
\text{s.t.}\quad
& x_{ij} \le U_j, && \forall i,\ j \in G_i,\\
& x_{ij} \le 1 - U_k, && \forall i,\ j \in G_i,\ k \in G_i:\ p_k < p_j,\\
& x_{ij} \le U_{c_i}, && \forall i,\ j \in G_i,\\
& U_j \in \{0,1\}, \quad 0 \le x_{ij} \le 1.
\end{aligned}
$$

The optimal objective value is $R(S^\star)$ and the optimal assortment is $S^\star = \{\, j : U_j = 1 \,\}$.
