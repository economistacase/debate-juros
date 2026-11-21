"""Valida e publica os dados manuais da Nota de Estatísticas Fiscais (sem rede).

Lê `src/dados/nota_fiscal.json`, confere a consistência interna e grava `docs/data/nota_fiscal.json`,
que a página usa no retrato factual e no gráfico de decomposição da dívida bruta.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ORIGEM = Path(__file__).with_name("nota_fiscal.json")
DESTINO = RAIZ / "docs" / "data" / "nota_fiscal.json"
TOLERANCIA_ARREDONDAMENTO = 0.2   # p.p. do PIB: os componentes publicados têm uma casa decimal


def validar(nota: dict) -> None:
    dec = nota["decomposicao_dbgg"]
    soma = sum(f["valor"] for f in dec["fatores"])
    variacao = dec["fim"]["valor"] - dec["inicio"]["valor"]
    assert abs(variacao - dec["variacao_total"]) < 1e-9, "variação total ≠ fim − início"
    assert abs(soma - dec["variacao_total"]) <= TOLERANCIA_ARREDONDAMENTO, f"fatores somam {soma:.1f}"
    m = dec["memoria"]
    assert abs(m["juro_real"] + m["erosao_inflacionaria"] - m["juros_nominais"]) <= TOLERANCIA_ARREDONDAMENTO
    fatias = nota["composicao_dbgg"]["fatias"].values()
    assert 98 <= sum(fatias) <= 101
    for item in nota["retrato"]["itens"]:
        assert math.isfinite(item["valor"])


def publicar(destino: Path = DESTINO) -> Path:
    nota = json.loads(ORIGEM.read_text(encoding="utf-8"))
    validar(nota)
    nota.pop("_comentario", None)
    destino.write_text(json.dumps(nota, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino


if __name__ == "__main__":
    print(publicar())
