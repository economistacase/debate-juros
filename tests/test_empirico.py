"""Onda 2: estatística (MQO robusto) e integridade dos resultados exportados."""
import json
import math

import numpy as np
import pytest

from src.empirico import onda2
from src.empirico.estatistica import lags_newey_west, ols


def test_ols_recupera_coeficientes_sem_ruido():
    x = np.linspace(0, 10, 50)
    r = ols(2 + 3 * x, np.column_stack([np.ones(50), x]), nomes=["c", "b"])
    assert r["coef"]["c"]["valor"] == pytest.approx(2) and r["coef"]["b"]["valor"] == pytest.approx(3)


def test_erro_padrao_white_confere_com_formula():
    rng = np.random.default_rng(1)
    x = rng.normal(size=200)
    y = 1 + 0.5 * x + rng.normal(size=200) * (1 + np.abs(x))
    X = np.column_stack([np.ones(200), x])
    r = ols(y, X, lags=0, nomes=["c", "b"])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    u = y - X @ beta
    bread = np.linalg.inv(X.T @ X)
    V = bread @ (X.T * u**2) @ X @ bread * 200 / 198
    assert r["coef"]["b"]["ep"] == pytest.approx(math.sqrt(V[1, 1]))


def test_newey_west_com_autocorrelacao_aumenta_o_erro_padrao():
    rng = np.random.default_rng(2)
    e = np.zeros(400)
    for t in range(1, 400):
        e[t] = 0.8 * e[t - 1] + rng.normal()
    x = np.cumsum(rng.normal(size=400)) / 10
    X = np.column_stack([np.ones(400), x])
    y = 1 + x + e
    assert ols(y, X, lags=8)["coef"]["b1"]["ep"] > ols(y, X, lags=0)["coef"]["b1"]["ep"]
    assert lags_newey_west(240) == 4


@pytest.fixture(scope="module")
def dados():
    if not onda2.SAIDA.exists():
        pytest.skip("rode `python -m src.empirico.onda2`")
    return json.loads(onda2.SAIDA.read_text(encoding="utf-8"))


def test_hiato_de_credibilidade_segue_a_definicao(dados):
    m = dados["mensal"]
    for s, pi, g in zip(m["selic"], m["pi_e"], m["g_5.0"]):
        if None not in (s, pi, g):
            assert g == pytest.approx(max(0.0, 5.0 + pi - s), abs=1e-3)


def test_estimativas_completas_e_finitas(dados):
    est = dados["gamma"]
    assert len(est) == 2 * len(onda2.R_NEUTROS)
    for e in est:
        g = e["gamma"]
        assert math.isfinite(g["valor"]) and g["ep"] > 0 and g["ic95"][0] < g["valor"] < g["ic95"][1]
        assert e["n"] >= 100 and e["meses_com_hiato"] >= 30


def test_eventos_do_copom(dados):
    ev = dados["eventos"]
    assert len(ev["lista"]) >= 150
    assert all(abs(x["surpresa"]) < 2 for x in ev["lista"])            # surpresas de Copom são pequenas
    assert set(ev["regressoes"]) == {"ltn", "lft", "cambio", "pi_e"}
