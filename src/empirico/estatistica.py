"""Mínimos quadrados com erros-padrão robustos (Newey-West / White), em numpy puro."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats


def ols(y, X, lags: int = 0, nomes: list[str] | None = None) -> dict:
    """MQO de y em X (X já inclui a constante, se desejada).

    lags = 0  → erros-padrão de White (HC0 com correção de graus de liberdade, HC1);
    lags > 0  → Newey-West com núcleo de Bartlett e `lags` defasagens (com a mesma correção).
    """
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    u = y - X @ beta
    Xu = X * u[:, None]
    S = Xu.T @ Xu
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        G = Xu[l:].T @ Xu[:-l]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv * n / (n - k)
    se = np.sqrt(np.diag(V))
    t = beta / se
    gl = n - k
    p = 2 * (1 - stats.t.cdf(np.abs(t), gl))
    q = stats.t.ppf(0.975, gl)
    r2 = 1 - (u @ u) / ((y - y.mean()) @ (y - y.mean())) if n > 1 else float("nan")
    nomes = nomes or [f"b{i}" for i in range(k)]
    return {
        "n": int(n), "r2": float(r2), "lags": lags, "vcov": V.tolist(),
        "coef": {nm: {"valor": float(b), "ep": float(s), "t": float(tt), "p": float(pp),
                      "ic95": [float(b - q * s), float(b + q * s)]}
                 for nm, b, s, tt, pp in zip(nomes, beta, se, t, p)},
    }


def lags_newey_west(n: int) -> int:
    """Regra usual de Newey-West: floor(4 (n/100)^(2/9))."""
    return int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
