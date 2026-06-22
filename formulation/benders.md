# Benders / branch-and-cut formulation

Notation: products $1,\dots,n$ with distinct prices $p_1 > \cdots > p_n$ and no-purchase price
$p_0 = 0$; transactions $(I_i, c_i)$, $i = 1,\dots,m$. Variables: $U_j \in \{0,1\}$ (offer product
$j$) and $\theta_i \ge 0$ (revenue from transaction $i$).

$$
\begin{aligned}
\max_{U,\,\theta}\quad & \frac{1}{m}\sum_{i=1}^{m} \theta_i\\
\text{s.t.}\quad
& \theta_i = 0, && \text{if } c_i = 0,\\
& \theta_i \le p_{c_i}\, U_{c_i}, && \text{if } c_i \neq 0,\\
& \theta_i \le p_{c_i} - (p_{c_i} - p_j)\, U_j, && \forall i,\ j \notin I_i:\ p_j < p_{c_i},\\
& U_j \in \{0,1\}, \quad \theta_i \ge 0.
\end{aligned}
$$

The optimality cuts (third constraint family) are separated lazily within branch-and-cut. The
optimal objective value is $R(S^\star)$ and the optimal assortment is $S^\star = \{\, j : U_j = 1 \,\}$.
