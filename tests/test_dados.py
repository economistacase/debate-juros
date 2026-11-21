"""Testes do painel de dados (sem rede: funções puras + integridade do JSON exportado)."""
import json
import math

import pytest

from src.dados import bcb


def test_juro_real_fisher_exata():
    assert bcb.juro_real(13.75, 5.0) == pytest.approx((1.1375 / 1.05 - 1) * 100)
    assert bcb.juro_real(5.0, 5.0) == pytest.approx(0.0)


def test_variacao_12m():
    serie = {"2025-01": 100.0, "2025-02": 110.0, "2026-01": 107.0, "2026-02": 121.0}
    assert bcb.variacao_12m(serie) == pytest.approx({"2026-01": 7.0, "2026-02": 10.0})


def test_media_mensal():
    pares = [("2026-01-02", 4.0), ("2026-01-30", 6.0), ("2026-02-01", 5.0)]
    assert bcb.media_mensal(pares) == {"2026-01": 5.0, "2026-02": 5.0}


def test_primario_estabilizador_reproduz_dossie():
    assert bcb.primario_estabilizador(82.9, 13.0, 7.0) == pytest.approx(4.65, abs=0.01)


def test_para_colunas_alinha_meses():
    c = bcb.para_colunas({"a": {"2026-01": 1.0, "2026-02": 2.0}, "b": {"2026-02": 3.0}})
    assert c["meses"] == ["2026-01", "2026-02"]
    assert c["series"]["b"] == [None, 3.0]


@pytest.fixture(scope="module")
def painel():
    assert bcb.SAIDA.exists(), "rode `python -m src.dados.bcb` para gerar o painel"
    return json.loads(bcb.SAIDA.read_text(encoding="utf-8"))


def test_painel_integro(painel):
    meses = painel["meses"]
    assert meses == sorted(meses) and len(meses) > 200
    for nome, serie in painel["series"].items():
        assert len(serie) == len(meses), nome
        validos = [v for v in serie if v is not None]
        assert len(validos) > 100, f"{nome} quase vazia"
        assert all(math.isfinite(v) for v in validos), nome


@pytest.mark.parametrize("chave,lo,hi", [
    ("selic", 1, 30), ("ipca_12m", -2, 20), ("expectativa_12m", 1, 15), ("dbgg", 40, 120),
    ("dlsp", 25, 90), ("juros_nominais", 2, 15), ("primario", -12, 6), ("cambio", 1, 10),
])
def test_faixas_plausiveis(painel, chave, lo, hi):
    validos = [v for v in painel["series"][chave] if v is not None]
    assert lo < min(validos) and max(validos) < hi, chave


def test_placar_coerente(painel):
    p = painel["placar"]
    esperado = bcb.primario_estabilizador(p["dbgg"]["valor"], p["juro_implicito_dbgg"]["valor"],
                                          p["pib_nominal_12m"]["valor"])
    assert p["primario_estabilizador"]["valor"] == pytest.approx(esperado)
    assert sum(painel["composicao"]["fatias"].values()) == pytest.approx(99.3, abs=1.0)


# ----------------------------------------------------------------- Nota Fiscal (manual) e catálogo da Onda 2

def test_nota_fiscal_consistente():
    from src.dados import nota
    dados = json.loads(nota.ORIGEM.read_text(encoding="utf-8"))
    nota.validar(dados)                                   # levanta AssertionError se incoerente
    dec = dados["decomposicao_dbgg"]
    assert dec["inicio"]["valor"] == 65.5 and dec["fim"]["valor"] == 78.6
    assert sum(f["valor"] for f in dec["fatores"][:4]) == pytest.approx(dec["soma_publicada"], abs=0.2)


def test_nota_publicada_igual_a_origem():
    from src.dados import nota
    origem = json.loads(nota.ORIGEM.read_text(encoding="utf-8"))
    origem.pop("_comentario", None)
    assert json.loads(nota.DESTINO.read_text(encoding="utf-8")) == origem


def test_catalogo_onda2():
    from src.empirico import fontes_bcb as f
    assert f.series_para_coleta() == sorted([4513, 4535, 5760, 5793, 4382, 13522, 433, 3696])
    assert set(f.TABELAS_NOTA) == {19, 21, 24, 25}
    assert all(s.nome and s.uso for s in f.SERIES_SGS.values())
