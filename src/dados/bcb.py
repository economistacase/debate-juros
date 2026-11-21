"""Painel de dados do Banco Central: Selic, inflação, expectativas, dívida e conta fiscal.

Fontes (códigos conferidos pelo nome oficial no web service do SGS):
    432    Meta Selic definida pelo Copom (% a.a., diária)            → placar
    4189   Selic acumulada no mês anualizada, base 252 (% a.a.)        → gráfico
    13522  IPCA em 12 meses (%)
    13762  Dívida bruta do governo geral (% PIB), metodologia 2008
    4513   Dívida líquida do setor público (% PIB), consolidado
    5793   NFSP 12 meses (% PIB), resultado primário (positivo = déficit)
    5760   NFSP 12 meses (% PIB), juros nominais
    4382   PIB acumulado em 12 meses, valores correntes (R$ milhões)
    3696   Câmbio livre R$/US$, venda, fim de período
    Focus  ExpectativasMercadoInflacao12Meses (IPCA, suavizada, mediana)

O juro implícito da dívida bruta e a composição por indexador não estão no SGS: vêm da Nota de
Estatísticas Fiscais e ficam em `src/dados/nota_fiscal.json` (atualização manual, com fonte e data).

Uso:  python -m src.dados.bcb      (requer internet; grava docs/data/painel.json)
"""
from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "docs" / "data" / "painel.json"
NOTA_FISCAL = Path(__file__).with_name("nota_fiscal.json")
INICIO = "01/01/2002"

SERIES_MENSAIS = {
    "selic": (4189, "Selic efetiva (% a.a.)"),
    "ipca_12m": (13522, "IPCA em 12 meses (%)"),
    "dbgg": (13762, "Dívida bruta do governo geral (% do PIB)"),
    "dlsp": (4513, "Dívida líquida do setor público (% do PIB)"),
    "nfsp_primario": (5793, "NFSP primária em 12 meses (% do PIB, + = déficit)"),
    "juros_nominais": (5760, "Juros nominais em 12 meses (% do PIB)"),
    "pib_12m": (4382, "PIB em 12 meses (R$ milhões correntes)"),
    "cambio": (3696, "Câmbio R$/US$ (fim de período)"),
}

URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={inicio}"
URL_SGS_ULTIMO = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"
URL_FOCUS = ("https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
             "ExpectativasMercadoInflacao12Meses?")

# Marcos do debate exibidos nos gráficos (datas verificáveis).
MARCOS = [
    {"data": "2017-01", "rotulo": "Debate de 2017", "curto": "2017"},
    {"data": "2020-03", "rotulo": "Pandemia", "curto": "Covid"},
    {"data": "2026-09", "rotulo": "“Eu acuso”", "curto": "LR"},
]


# ----------------------------------------------------------------------------- rede

def _get_json(url: str, tentativas: int = 4):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "painel-debate-juros/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(2 * (i + 1))


def baixar_sgs(codigo: int, inicio: str = INICIO) -> dict[str, float]:
    """Série mensal do SGS como {'AAAA-MM': valor}."""
    dados = _get_json(URL_SGS.format(codigo=codigo, inicio=inicio))
    return {_mes(d["data"]): float(d["valor"]) for d in dados if d.get("valor") not in (None, "")}


def ultimo_sgs(codigo: int) -> tuple[str, float]:
    d = _get_json(URL_SGS_ULTIMO.format(codigo=codigo))[0]
    return datetime.strptime(d["data"], "%d/%m/%Y").date().isoformat(), float(d["valor"])


def baixar_focus_12m() -> dict[str, float]:
    """Mediana da expectativa de IPCA 12 meses à frente (suavizada), média mensal."""
    filtro = "Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0 and Data ge '2002-01-01'"
    url = URL_FOCUS + urllib.parse.urlencode(
        {"$filter": filtro, "$select": "Data,Mediana", "$orderby": "Data", "$top": "100000",
         "$format": "json"}, quote_via=urllib.parse.quote)
    linhas = _get_json(url)["value"]
    return media_mensal([(l["Data"], float(l["Mediana"])) for l in linhas])


# ----------------------------------------------------------------------------- transformações puras

def _mes(data_br: str) -> str:
    d, m, a = data_br.split("/")
    return f"{a}-{m}"


def media_mensal(pares: list[tuple[str, float]]) -> dict[str, float]:
    """Média por mês de observações diárias ('AAAA-MM-DD', valor)."""
    soma: dict[str, list[float]] = {}
    for data_iso, valor in pares:
        soma.setdefault(data_iso[:7], []).append(valor)
    return {m: sum(v) / len(v) for m, v in sorted(soma.items())}


def juro_real(nominal: float, inflacao: float) -> float:
    """Juro real (Fisher exata), tudo em % a.a."""
    return ((1 + nominal / 100) / (1 + inflacao / 100) - 1) * 100


def variacao_12m(serie: dict[str, float]) -> dict[str, float]:
    """Variação % sobre o mesmo mês do ano anterior."""
    saida = {}
    for mes, valor in serie.items():
        a, m = mes.split("-")
        anterior = f"{int(a) - 1}-{m}"
        if anterior in serie and serie[anterior]:
            saida[mes] = (valor / serie[anterior] - 1) * 100
    return saida


def combinar(a: dict[str, float], b: dict[str, float], f) -> dict[str, float]:
    return {m: f(a[m], b[m]) for m in sorted(set(a) & set(b))}


def primario_estabilizador(d: float, r: float, theta: float) -> float:
    """pb* em % do PIB, com d em % do PIB e r, θ em % a.a."""
    return (r - theta) / (100 + theta) * d


def para_colunas(series: dict[str, dict[str, float]]) -> dict:
    """Alinha séries mensais num eixo comum; ausências viram null."""
    meses = sorted(set().union(*[set(s) for s in series.values()]))
    return {"meses": meses,
            "series": {k: [round(s[m], 4) if m in s else None for m in meses] for k, s in series.items()}}


def ultimo(serie: dict[str, float]) -> tuple[str, float]:
    mes = max(serie)
    return mes, serie[mes]


# ----------------------------------------------------------------------------- montagem

def montar_painel() -> dict:
    brutas = {k: baixar_sgs(cod) for k, (cod, _) in SERIES_MENSAIS.items()}
    focus = baixar_focus_12m()
    data_meta, selic_meta = ultimo_sgs(432)
    nota = json.loads(NOTA_FISCAL.read_text(encoding="utf-8"))

    theta = variacao_12m(brutas["pib_12m"])
    primario = {m: -v for m, v in brutas["nfsp_primario"].items()}      # superávit positivo
    real_ante = combinar(brutas["selic"], focus, juro_real)
    real_post = combinar(brutas["selic"], brutas["ipca_12m"], juro_real)

    series = {
        "selic": brutas["selic"], "ipca_12m": brutas["ipca_12m"], "expectativa_12m": focus,
        "juro_real_ex_ante": real_ante, "juro_real_ex_post": real_post,
        "dbgg": brutas["dbgg"], "dlsp": brutas["dlsp"],
        "primario": primario, "juros_nominais": brutas["juros_nominais"],
        "cambio": brutas["cambio"], "pib_nominal_12m": theta,
    }

    m_d, dbgg = ultimo(brutas["dbgg"])
    m_t, th = ultimo(theta)
    m_p, prim = ultimo(primario)
    r_impl = nota["juro_implicito_dbgg"]["valor"]
    m_f, expect = ultimo(focus)
    placar = {
        "selic_meta": {"valor": selic_meta, "data": data_meta, "fonte": "SGS 432"},
        "ipca_12m": dict(zip(("data", "valor"), ultimo(brutas["ipca_12m"])), fonte="SGS 13522"),
        "expectativa_12m": {"valor": expect, "data": m_f, "fonte": "Focus, mediana"},
        "juro_real_ex_ante": {"valor": juro_real(selic_meta, expect), "data": data_meta,
                              "fonte": "Meta Selic deflacionada pela expectativa Focus 12m"},
        "dbgg": {"valor": dbgg, "data": m_d, "fonte": "SGS 13762"},
        "primario": {"valor": prim, "data": m_p, "fonte": "SGS 5793 (sinal invertido)"},
        "juros_nominais": dict(zip(("data", "valor"), ultimo(brutas["juros_nominais"])), fonte="SGS 5760"),
        "pib_nominal_12m": {"valor": th, "data": m_t, "fonte": "SGS 4382, variação anual"},
        "juro_implicito_dbgg": nota["juro_implicito_dbgg"],
        "primario_estabilizador": {
            "valor": primario_estabilizador(dbgg, r_impl, th), "data": m_d,
            "fonte": "pb* = (r − θ)/(1 + θ)·d com d e θ do SGS e r da Nota Fiscal"},
    }

    return {
        "meta": {"atualizado_em": date.today().isoformat(), "gerador": "src/dados/bcb.py",
                 "rotulos": {k: v[1] for k, v in SERIES_MENSAIS.items()}},
        "placar": placar,
        "composicao": nota["composicao_dbgg"],
        "marcos": MARCOS,
        **para_colunas(series),
    }


def exportar(caminho: Path = SAIDA) -> Path:
    painel = montar_painel()
    for v in painel["series"].values():
        assert all(x is None or math.isfinite(x) for x in v)
    # Mantém a data de atualização se nada além dela mudou (evita commits vazios no robô).
    if caminho.exists():
        anterior = json.loads(caminho.read_text(encoding="utf-8"))
        data_anterior = anterior["meta"]["atualizado_em"]
        anterior["meta"]["atualizado_em"] = painel["meta"]["atualizado_em"]
        if anterior == json.loads(json.dumps(painel, ensure_ascii=False)):
            painel["meta"]["atualizado_em"] = data_anterior
    caminho.write_text(json.dumps(painel, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                       encoding="utf-8")
    return caminho


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    destino = exportar()
    p = json.loads(destino.read_text(encoding="utf-8"))
    print(f"painel exportado: {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1024:.0f} KB), "
          f"{len(p['meses'])} meses, {p['meses'][0]} a {p['meses'][-1]}")
    for k, v in p["placar"].items():
        print(f"  {k:24s} {v['valor']:8.2f}  ({v['data']})")
