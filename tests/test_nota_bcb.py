"""Leitura automática da Nota de Estatísticas Fiscais e conferência com a decomposição de referência."""
import json

import pytest

from src.dados import nota_bcb as nb

NOTA = json.loads(nb.NOTA_JSON.read_text(encoding="utf-8"))
EDICAO_REF = nb.CACHE / "202610.xlsx"


def test_normalizar_trata_travessoes_e_acentos():
    assert nb.normalizar("Dívida bruta do Governo Geral – saldo") == "divida bruta do governo geral - saldo"
    assert nb.normalizar("  Emissões   líquidas ") == "emissoes liquidas"


def test_mes_numero():
    assert nb.mes_numero("Setembro") == 9 and nb.mes_numero("Mar") == 3 and nb.mes_numero("Saldos") is None


def test_composicao_fecha_100():
    c = NOTA["composicao_dbgg"]
    total = sum(c["fatias"].values()) + c.get("outros_tjlp_tr", 0.0)
    assert total == pytest.approx(100.0, abs=0.15)


def test_decomposicao_oficial_confere_com_a_referencia():
    """As somas reconstruídas das Notas oficiais batem com a cascata de referência (dentro de revisões do PIB)."""
    v = NOTA.get("verificacao_decomposicao")
    if not v:
        pytest.skip("verificação ainda não gerada (rode `python build.py --dados`)")
    ref = NOTA["decomposicao_dbgg"]
    assert v["anos"] == list(range(2016, 2026))
    assert v["juros_nominais"] == pytest.approx(ref["memoria"]["juros_nominais"], abs=0.5)
    assert v["emissoes_liquidas"] == pytest.approx(ref["fatores"][2]["valor"], abs=0.3)
    assert v["cambio_e_outros"] == pytest.approx(ref["fatores"][3]["valor"], abs=0.5)
    assert v["soma_variacoes"] == pytest.approx(ref["soma_publicada"], abs=1.5)


@pytest.mark.skipif(not EDICAO_REF.exists(), reason="planilha de out/2026 fora do cache local")
def test_leitura_da_edicao_out2026():
    wb = nb.abrir(EDICAO_REF)
    assert nb.ler_juro_implicito(wb) == {"valor": 13.03, "data": "2026-09",
                                         "fonte": "BCB, Nota de Estatísticas Fiscais, Tabela 24 (taxa implícita da DBGG, 12 meses)"}
    comp = nb.ler_composicao(wb)
    assert comp["fatias"]["Selic (inclui compromissadas)"] == 56.87 and comp["fatias"]["Câmbio"] == 4.57
    assert nb.ler_vencimento_12m(wb) == pytest.approx(26.77, abs=0.01)
    f = nb.ler_fatores(wb)
    assert f[(2026, 9)]["saldo"] == pytest.approx(82.93, abs=0.005) and f[(2025, 12)]["juros"] == pytest.approx(8.85, abs=0.005)
