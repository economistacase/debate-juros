"""Testes do modelo de transmissão (Blocos 4 e 5: potência da Selic e canal de renda)."""
import json
import math
from dataclasses import replace

import pytest

from src.teoria import transmissao as tr

B = tr.ParTransmissao()


def test_linearidade():
    """Dobrar o aperto dobra todas as respostas."""
    r1, r2 = tr.resposta(B), tr.resposta(replace(B, delta=2.0))
    assert r2["inflacao"] == pytest.approx([2 * x for x in r1["inflacao"]])


def test_aperto_desinfla_sem_canal_de_renda():
    assert all(x < 0 for x in tr.resposta(B)["inflacao"])
    assert tr.potencia(B) > 0


def test_direcionado_reduz_a_potencia_monotonicamente():
    pots = [tr.potencia(replace(B, s=s / 10)) for s in range(0, 10)]
    assert all(a > b for a, b in zip(pots, pots[1:]))
    assert tr.potencia(replace(B, s=1.0)) == pytest.approx(0.0, abs=1e-12)   # todo crédito imune: sem canal convencional


def test_aperto_necessario_e_o_inverso_da_potencia():
    p = replace(B, s=0.437)
    alvo = 1.0
    a = tr.aperto_necessario(p, alvo)
    assert -tr.resposta(replace(p, delta=a))["inflacao"][1] == pytest.approx(alvo)


def test_inercia_prolonga_o_efeito():
    sem, com = tr.resposta(replace(B, omega=0.0)), tr.resposta(replace(B, omega=0.7))
    assert abs(com["inflacao"][-1]) > abs(sem["inflacao"][-1])


def test_limiar_do_canal_de_renda():
    """Em c = c*, o efeito de impacto sobre o hiato é zero; acima, o aperto aquece a demanda."""
    c_estrela = tr.limiar_consumo(B)
    assert tr.efeito_impacto(replace(B, c=c_estrela))["liquido"] == pytest.approx(0.0, abs=1e-12)
    assert tr.efeito_impacto(replace(B, c=c_estrela * 1.1))["liquido"] > 0
    assert tr.efeito_impacto(replace(B, c=c_estrela * 0.9))["liquido"] < 0


def test_canal_de_renda_suficientemente_forte_inverte_o_sinal():
    """Com consumo da renda de juros bem acima do limiar, o aperto passa a elevar a inflação."""
    p = replace(B, c=min(1.0, tr.limiar_consumo(B) * 1.3))
    assert tr.resposta(p)["inflacao"][0] > 0
    assert tr.aperto_necessario(p) is None


def test_json_de_referencia():
    tr.exportar()
    dados = json.loads(tr.SAIDA_JSON.read_text(encoding="utf-8"))
    assert len(dados["casos_referencia"]) == 18
    for caso in dados["casos_referencia"]:
        p = tr.ParTransmissao(**caso["parametros"])
        assert tr.resposta(p)["inflacao"] == pytest.approx(caso["inflacao"], abs=1e-12)
        assert all(math.isfinite(x) for x in caso["inflacao"] + caso["hiato"])
