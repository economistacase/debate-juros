"""Testes de consistência matemática dos modelos teóricos da Onda 1."""
import json
import math
from dataclasses import replace

import numpy as np
import pytest

from src.teoria import dinamica_divida as dd
from src.teoria import regimes_tfnp as rt


# ---------------------------------------------------------------- Bloco 1: dívida

def test_primario_estabilizador_zera_variacao():
    """pb* mantém Δd = 0 no regime mecânico, para várias combinações (d, r, θ)."""
    for d in (0.6, 0.829, 1.2):
        for r in (0.075, 0.13, 0.15):
            for theta in (0.05, 0.07, 0.10):
                pb = dd.primario_estabilizador(d, r, theta)
                assert dd.variacao_divida(d, r, theta, pb) == pytest.approx(0.0, abs=1e-15)
                traj = dd.trajetoria_custo_fixo(d, r, theta, pb)
                assert max(abs(x - d) for x in traj) < 1e-12


def test_pb_estabilizador_reproduz_dossie():
    """Com juro implícito de 13%, PIB nominal de 7% e dívida de 82,9%: pb* ≈ 4,7% do PIB."""
    assert dd.primario_estabilizador(0.829, 0.13, 0.07) == pytest.approx(0.0465, abs=5e-4)


def test_aritmetica_do_dossie_custo_127():
    """Custo de 12,7%, θ = 7% e primário zero levam a dívida a ~138% do PIB em 2036."""
    assert dd.trajetoria_custo_fixo(0.825, 0.127, 0.07, 0.0)[-1] == pytest.approx(1.38, abs=0.01)


def test_sensibilidade_selic_bate_com_bcb():
    """Mundo mecânico: corte de 1 p.p. na Selic, com 56,9% indexada, reduz a DBGG em 0,47–0,49 p.p. do PIB em 12 meses."""
    p = dd.Parametros()
    assert p.phi == pytest.approx(0.569) and p.lam == pytest.approx(0.268)
    base = dd.simular(p)["divida"][1]
    corte = dd.simular(replace(p, selic=p.selic - 0.01))["divida"][1]
    assert 0.47 <= (base - corte) * 100 <= 0.49
    assert dd.sensibilidade_selic() == pytest.approx((base - corte) * 100)


def test_repasse_gradual_da_parcela_nao_selic():
    """No ano 1 a parcela não-Selic absorve só meia rolagem; o repasse completo leva vários anos."""
    p = dd.Parametros()
    cortes = [(dd.simular(p)["custo"][t] - dd.simular(replace(p, selic=p.selic - 0.01))["custo"][t]) * 100
              for t in (1, 2, 10)]
    assert cortes[0] == pytest.approx(p.phi + (1 - p.phi) * p.lam / 2, abs=1e-9)
    assert cortes[0] < cortes[1] < cortes[2] < 1.0


def test_aritmetica_da_proposta_reproduz_dossie():
    """Custo de 7,5% (2027–2030) e 5,5% (2031+), θ = 7%, primário zero: dívida perto de 78% do PIB em 2036."""
    assert dd.trajetoria_custo_caminho(0.825, dd.TRAJETORIA_PROPOSTA, 0.07, 0.0)[-1] == pytest.approx(0.775, abs=0.01)


def test_trajetoria_de_selic_reprecifica_mais_devagar_que_a_aritmetica():
    """Com a mesma trajetória na Selic, a composição da dívida deixa a dívida acima da aritmética pura."""
    sim = dd.simular(dd.Parametros(selic=list(dd.TRAJETORIA_PROPOSTA), pb=0.0))
    arit = dd.trajetoria_custo_caminho(0.829, dd.TRAJETORIA_PROPOSTA, 0.07, 0.0)
    assert sim["divida"][-1] > arit[-1]
    assert sim["selic"][1:] == pytest.approx(list(dd.TRAJETORIA_PROPOSTA))


def test_mecanico_monotono_na_selic():
    """No mundo mecânico, Selic menor sempre implica dívida final menor."""
    finais = [dd.simular(dd.Parametros(selic=s / 100))["divida"][-1] for s in range(3, 16)]
    assert all(a < b for a, b in zip(finais, finais[1:]))


def test_reacao_neutra_acima_do_juro_neutro():
    """Acima do neutro nominal (r_n + π0 = 9,5%) a reação de mercado não altera nada."""
    for s in (0.10, 0.125, 0.15):
        mec = dd.simular(dd.Parametros(selic=s))["divida"]
        rea = dd.simular(dd.Parametros(selic=s, reacao=True))["divida"]
        assert mec == pytest.approx(rea, abs=1e-15)


def test_reacao_inverte_o_efeito_do_corte_com_premio_alto():
    """Com γ > 1, cortar abaixo do neutro passa a ELEVAR a dívida; com γ < 1, ainda reduz."""
    def final(selic, gamma):
        return dd.simular(dd.Parametros(selic=selic, reacao=True, gamma=gamma))["divida"][-1]
    assert final(0.06, 1.5) > final(0.095, 1.5)
    assert final(0.06, 0.5) < final(0.095, 0.5)
    sel, _ = dd.selic_que_minimiza_divida(dd.Parametros(reacao=True, gamma=1.5))
    assert sel == pytest.approx(0.095, abs=1e-9)


# ---------------------------------------------------------------- Bloco 2: Fisher–Taylor

def pi_equilibrio(z, r, k):
    return (z - r) / (1 - k)


@pytest.mark.parametrize("k", [0.2, 0.5, 0.8, 0.95])
def test_aperto_eleva_inflacao_se_k_menor_que_1(k):
    assert pi_equilibrio(4.0, 5.0, k) > pi_equilibrio(3.0, 5.0, k)


@pytest.mark.parametrize("k", [1.05, 1.5, 2.0, 2.5])
def test_aperto_reduz_inflacao_se_k_maior_que_1(k):
    assert pi_equilibrio(4.0, 5.0, k) < pi_equilibrio(3.0, 5.0, k)


def test_inversao_de_sinal_em_k_igual_1():
    """dπ/dz = 1/(1-k) troca de sinal exatamente em k = 1."""
    derivada = lambda k: 1 / (1 - k)
    assert derivada(1 - 1e-6) > 0 > derivada(1 + 1e-6)


def test_fisher_taylor_satisfaz_as_duas_equacoes():
    for k in (0.5, 1.5):
        r, z = 5.0, 3.5
        pi = pi_equilibrio(z, r, k)
        assert k * pi + z == pytest.approx(r + pi)   # regra = Fisher


# ---------------------------------------------------------------- Bloco 3: NK + TFNP

DM = replace(rt.Calibracao(), **rt.REGIME_DM)
DF = replace(rt.Calibracao(), **rt.REGIME_DF)


@pytest.mark.parametrize("cal", [DM, DF, replace(DF, omega=0.95), replace(DM, omega=0.95)])
def test_blanchard_kahn_e_residuos(cal):
    """Solução única e estável; todas as equações do modelo valem ao longo da trajetória."""
    for anunciado in (False, True):
        s = rt.simular(cal, anunciado=anunciado, choque_fiscal=rt.CHOQUE_FISCAL)
        assert max(rt.residuos(cal, s).values()) < 1e-10
        assert abs(s["pi"][-1]) < 1e-8          # retorna ao estado estacionário


def test_indeterminacao_detectada():
    """Juro passivo + fiscal passivo = indeterminação: o solver deve recusar."""
    with pytest.raises(rt.ErroBlanchardKahn):
        rt.resolver(replace(rt.Calibracao(), phi_pi=0.8, alpha=0.05))


def test_dm_bate_com_solucao_analitica():
    """Sob dominância monetária, π_t = -κΛu_t e x_t = -(1-βρ)Λu_t (Galí, cap. 3)."""
    c = DM
    lam = 1 / ((1 - c.beta * c.rho) * (1 - c.rho) / c.sigma + c.kappa * (c.phi_pi - c.rho))
    s = rt.simular(c, periodos=40)
    np.testing.assert_allclose(s["pi"], -c.kappa * lam * s["u"], atol=1e-12)
    np.testing.assert_allclose(s["x"], -(1 - c.beta * c.rho) * lam * s["u"], atol=1e-12)


def test_sinais_dos_regimes():
    """DM: corte eleva a inflação. DF com LFT: corte reduz (neofisheriano). Perda de lastro: eleva."""
    pi = lambda cal, **kw: rt.simular(cal, **kw)["pi"][0]
    assert pi(DM) > 0
    assert pi(DF) < 0
    assert pi(DF, choque_fiscal=rt.CHOQUE_FISCAL) > 0


def test_antecipacao_move_variaveis_antes_do_corte():
    s = rt.simular(DM, anunciado=True)
    assert np.all(np.abs(s["u"][: rt.ANTECEDENCIA]) < 1e-12)
    assert abs(s["pi"][0]) > 1e-3 and s["u"][rt.ANTECEDENCIA] == pytest.approx(rt.CHOQUE)


# ---------------------------------------------------------------- JSON exportado

def _numeros(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _numeros(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _numeros(v)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield obj


def test_json_integro():
    assert rt.SAIDA_JSON.exists(), "rode `python build.py` para gerar o JSON"
    dados = json.loads(rt.SAIDA_JSON.read_text(encoding="utf-8"))
    assert all(math.isfinite(x) for x in _numeros(dados)), "NaN/Inf no JSON"
    n = len(dados["trimestres"])
    assert n == rt.HORIZONTE + 1
    assert set(dados["cenarios"]) == {"dominancia_monetaria", "dominancia_fiscal", "antecipacao"}
    for cen in dados["cenarios"].values():
        assert cen["linhas"], "cenário sem linhas"
        for linha in cen["linhas"]:
            for nome, serie in linha["series"].items():
                assert len(serie) == n, f"{linha['id']}/{nome} vazia ou incompleta"
                assert any(abs(v) > 1e-9 for v in serie) or nome == "superavit"
    assert len(dados["divida"]["casos_referencia"]) >= 6


def test_json_reproduz_python():
    """Os casos de referência da dívida no JSON coincidem com o motor atual."""
    dados = json.loads(rt.SAIDA_JSON.read_text(encoding="utf-8"))
    for caso in dados["divida"]["casos_referencia"]:
        par = dd.Parametros(**caso["parametros"])
        assert dd.simular(par)["divida"] == pytest.approx(caso["divida"], abs=1e-12)
