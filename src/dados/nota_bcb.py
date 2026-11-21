"""Leitura automática das Notas de Estatísticas Fiscais do BCB (planilhas xlsx).

Endereço das edições: https://www.bcb.gov.br/content/estatisticas/hist_estatisticasfiscais/AAAAMM_Tabelas_de_estatisticas_fiscais.xlsx
(AAAAMM = mês de publicação; a edição de out/2026 traz dados até set/2026).

O que é lido (tabelas localizadas pelo TÍTULO e linhas pelo RÓTULO, para resistir a renumerações):
    Tabela 19 — DBGG, fatores condicionantes, fluxos acumulados no ano (% do PIB, colunas de dezembro)
    Tabela 21 — DBGG, participação percentual por indexador
    Tabela 24 — taxa de juros implícita na DBGG, acumulada em 12 meses
    Tabela 25 — cronograma de vencimento da DBGG

`atualizar()` baixa a edição mais recente, atualiza `src/dados/nota_fiscal.json` (preservando o que não é lido
automaticamente) e reconstrói os fatores anuais de 2016 em diante a partir das edições de outubro, para conferir
a decomposição de referência. Sem rede, o arquivo manual continua valendo.

Segurança: as planilhas baixadas ficam em `src/dados/_cache/` (fora do git) e são apenas lidas pelo openpyxl,
em modo somente leitura e sem fórmulas (`data_only=True`).
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CACHE = Path(__file__).with_name("_cache")
NOTA_JSON = Path(__file__).with_name("nota_fiscal.json")
URL = "https://www.bcb.gov.br/content/estatisticas/hist_estatisticasfiscais/{aaaamm}_Tabelas_de_estatisticas_fiscais.xlsx"
MESES = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
MESES_CURTOS = [m[:3] for m in MESES]
ANO_INICIAL_DECOMPOSICAO = 2016


# ----------------------------------------------------------------------------- utilitários

def normalizar(txt) -> str:
    """minúsculas, sem acentos, travessões viram hífen, espaços simples."""
    t = str(txt or "").replace("–", "-").replace("—", "-")      # travessões ANTES de remover não-ASCII
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", t).strip()


def mes_numero(txt) -> int | None:
    t = normalizar(txt)[:3]
    return MESES_CURTOS.index(t) + 1 if t in MESES_CURTOS else None


def baixar(aaaamm: str, pasta: Path = CACHE) -> Path | None:
    """Baixa (ou reaproveita do cache) a edição AAAAMM. Devolve None se não existir."""
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{aaaamm}.xlsx"
    if destino.exists() and destino.stat().st_size > 10_000:
        return destino
    req = urllib.request.Request(URL.format(aaaamm=aaaamm), headers={"User-Agent": "Mozilla/5.0 (painel-juros)"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            dados = resp.read()
    except Exception:
        return None
    if not dados.startswith(b"PK"):          # xlsx é um zip; página de erro não é
        return None
    destino.write_bytes(dados)
    return destino


def edicao_mais_recente(hoje: date | None = None, recuo: int = 8) -> tuple[str, Path] | None:
    hoje = hoje or date.today()
    a, m = hoje.year, hoje.month
    for _ in range(recuo):
        aaaamm = f"{a}{m:02d}"
        caminho = baixar(aaaamm)
        if caminho:
            return aaaamm, caminho
        a, m = (a, m - 1) if m > 1 else (a - 1, 12)
    return None


def abrir(caminho: Path):
    import openpyxl
    return openpyxl.load_workbook(caminho, read_only=True, data_only=True)


def achar_aba(wb, *termos: str, excluir: tuple[str, ...] = ()):
    """Aba cujo título (3 primeiras linhas) contém todos os termos (normalizados) e nenhum excluído."""
    for nome in wb.sheetnames:
        topo = normalizar(" ".join(str(c) for row in wb[nome].iter_rows(min_row=1, max_row=4, values_only=True)
                                   for c in row if c not in (None, "")))
        if all(t in topo for t in termos) and not any(e in topo for e in excluir):
            return wb[nome]
    raise KeyError(f"tabela não encontrada: {termos}")


def linhas(ws) -> list[list]:
    return [list(r) for r in ws.iter_rows(values_only=True)]


def linha_por_rotulo(rows: list[list], prefixo: str) -> list | None:
    p = normalizar(prefixo)
    for r in rows:
        if r and normalizar(r[0]).startswith(p):
            return r
    return None


def ultimo_numero(r: list) -> float:
    return [c for c in r if isinstance(c, (int, float))][-1]


# ----------------------------------------------------------------------------- tabelas

def ler_juro_implicito(wb) -> dict:
    """Tabela 24: taxa implícita da DBGG em 12 meses, último mês disponível."""
    rows = linhas(achar_aba(wb, "taxa de juros implicita na dbgg", "doze meses"))
    ano = next(int(c) for r in rows[:8] for c in r if isinstance(c, (int, float, str)) and re.fullmatch(r"20\d\d", str(c).strip()))
    meses = [mes_numero(c) for r in rows[:9] for c in r if mes_numero(c)]
    valor = ultimo_numero(linha_por_rotulo(rows, "Dívida bruta total"))
    return {"valor": round(float(valor), 2), "data": f"{ano}-{meses[-1]:02d}",
            "fonte": "BCB, Nota de Estatísticas Fiscais, Tabela 24 (taxa implícita da DBGG, 12 meses)"}


def ler_composicao(wb) -> dict:
    """Tabela 21: última linha de participação por indexador."""
    ws = achar_aba(wb, "divida bruta do governo geral", "participacao percentual por indexador")
    rows = linhas(ws)
    # cabeçalhos: localizar colunas pelas palavras da linha de rótulos
    cab = {}
    for r in rows[:12]:
        for j, c in enumerate(r):
            n = normalizar(c)
            if n in ("selic", "tjlp/tlp", "tjlp", "tr", "pre-fixado", "prefixado", "cambial", "indices de precos"):
                cab.setdefault(n, j)
    # a linha de subcabeçalhos (Interna | Externa | Total | IGP-M | IGP-DI | IPCA | Total) traz os totais
    # dos grupos cambial e preços, nessa ordem; o "Total" geral fica em outra linha
    sub = next(r for r in rows[:12] if any(normalizar(c) == "interna" for c in r) and any(normalizar(c) == "ipca" for c in r))
    total_por_grupo = {"totais": [j for j, c in enumerate(sub) if normalizar(c) == "total"]}
    dados = [r for r in rows if sum(isinstance(c, (int, float)) for c in r) >= 8]
    ult = dados[-1]
    ano = next((int(str(r[0]).strip()) for r in reversed(dados) if r[0] and re.fullmatch(r"20\d\d", str(r[0]).strip())), None)
    mes = mes_numero(ult[1]) or 12
    totais = total_por_grupo.get("totais", [])
    # ordem na tabela: Saldo | Cambial (Int, Ext, Total) | Preços (IGP-M, IGP-DI, IPCA, Total) | Selic | TJLP/TLP | TR | Pré | Total
    j_saldo = next(j for j, c in enumerate(ult) if isinstance(c, (int, float)))
    cambio = ult[totais[0]] if len(totais) > 0 else None
    precos = ult[totais[1]] if len(totais) > 1 else None
    selic = ult[cab["selic"]]
    tjlp = ult[cab.get("tjlp/tlp", cab.get("tjlp"))]
    tr = ult[cab["tr"]]
    pre = ult[cab.get("pre-fixado", cab.get("prefixado"))]
    fatias = {"Selic (inclui compromissadas)": round(float(selic), 2), "Preços": round(float(precos), 2),
              "Prefixada": round(float(pre), 2), "Câmbio": round(float(cambio), 2)}
    return {"data": f"{ano}-{mes:02d}", "fatias": fatias,
            "outros_tjlp_tr": round(float(tjlp) + float(tr), 2),
            "saldo_rs_milhoes": round(float(ult[j_saldo]), 2),
            "fonte": "BCB, Nota de Estatísticas Fiscais, Tabelas 21 e 25"}


def ler_vencimento_12m(wb) -> float:
    """Tabela 25: % da DBGG que vence em até 1 ano."""
    rows = linhas(achar_aba(wb, "cronograma de vencimento da dbgg"))
    r = linha_por_rotulo(rows, "Dívida bruta total")
    nums = [c for c in r if isinstance(c, (int, float))]
    return round(100.0 * nums[0] / nums[-1], 2)


def ler_fatores(wb) -> dict[tuple[int, int], dict]:
    """Tabela 19 (fluxos acumulados no ano): {(ano, mês): {componente: % do PIB}} para cada coluna '%'."""
    ws = achar_aba(wb, "divida bruta do governo geral", "fatores condicionantes", "fluxos acumulados no ano",
                   excluir=("detalhamento",))
    rows = linhas(ws)
    linha_ano = next(i for i, r in enumerate(rows[:12]) if any(re.fullmatch(r"20\d\d", str(c or "").strip()) for c in r))
    linha_mes = next(i for i, r in enumerate(rows[:12]) if i > linha_ano and any(mes_numero(c) for c in r))
    linha_pct = next(i for i, r in enumerate(rows[:14]) if i > linha_mes and any(str(c or "").strip().startswith("%") for c in r))
    colunas, ano, mes = {}, None, None
    for j in range(len(rows[linha_pct])):
        a = str(rows[linha_ano][j] or "").strip() if j < len(rows[linha_ano]) else ""
        if re.fullmatch(r"20\d\d", a):
            ano = int(a)
        mm = mes_numero(rows[linha_mes][j]) if j < len(rows[linha_mes]) else None
        if mm:
            mes = mm
        if str(rows[linha_pct][j] or "").strip().startswith("%") and ano and mes:
            colunas[(ano, mes)] = j
    rotulos = {
        "saldo": "Dívida bruta do Governo Geral - saldo",
        "variacao": "Dívida bruta do Gov. Geral - var. acum. no ano",
        "emissoes": "Emissões líquidas",
        "juros": "Juros nominais",
        "cambio": "Ajuste cambial",
        "outros_externa": "Dívida externa - outros ajustes",
        "reconhecimento": "Reconhecimento de dívidas",
        "privatizacoes": "Privatizações",
        "efeito_pib": "Efeito crescimento PIB",
    }
    saida = {}
    for chave, j in colunas.items():
        v = {}
        for nome, rot in rotulos.items():
            r = linha_por_rotulo(rows, rot)
            v[nome] = float(r[j]) if r and j < len(r) and isinstance(r[j], (int, float)) else 0.0
        saida[chave] = v
    return saida


# ----------------------------------------------------------------------------- decomposição histórica

def fatores_anuais(ano_inicial: int = ANO_INICIAL_DECOMPOSICAO, ano_final: int | None = None) -> dict[int, dict]:
    """Fatores de dezembro de cada ano, lidos das edições de outubro dos anos seguintes."""
    ano_final = ano_final or date.today().year - 1
    anuais: dict[int, dict] = {}
    for ano in range(ano_inicial, ano_final + 1):
        for edicao in (f"{ano + 1}10", f"{ano + 2}10"):
            caminho = baixar(edicao)
            if not caminho:
                continue
            f = ler_fatores(abrir(caminho))
            if (ano, 12) in f:
                anuais[ano] = dict(f[(ano, 12)], edicao=edicao)
                break
    return anuais


def resumo_decomposicao(anuais: dict[int, dict]) -> dict:
    """Somas no formato do BCB, comparáveis aos agregados da decomposição de referência."""
    soma = lambda k: round(sum(v[k] for v in anuais.values()), 1)
    outros = round(sum(v["cambio"] + v["outros_externa"] + v["reconhecimento"] + v["privatizacoes"]
                       for v in anuais.values()), 1)
    anos = sorted(anuais)
    return {
        "periodo": f"{anos[0]}–{anos[-1]}" if anos else "",
        "anos": anos,
        "juros_nominais": soma("juros"),
        "efeito_pib_nominal": soma("efeito_pib"),
        "juros_mais_pib": round(soma("juros") + soma("efeito_pib"), 1),
        "emissoes_liquidas": soma("emissoes"),
        "cambio_e_outros": outros,
        "soma_variacoes": soma("variacao"),
        "por_ano": {str(a): {k: round(v[k], 2) for k in ("juros", "efeito_pib", "emissoes", "cambio", "variacao")}
                    | {"edicao": v["edicao"]} for a, v in sorted(anuais.items())},
        "fonte": "BCB, Notas de Estatísticas Fiscais, Tabela 19 (dezembro de cada ano, edições de outubro seguintes)",
    }


# ----------------------------------------------------------------------------- atualização

def atualizar(historico: bool = True) -> dict:
    """Atualiza nota_fiscal.json com a edição mais recente. Devolve um resumo do que mudou."""
    achado = edicao_mais_recente()
    if not achado:
        return {"status": "sem rede ou sem edição disponível; mantido o arquivo manual"}
    aaaamm, caminho = achado
    wb = abrir(caminho)
    nota = json.loads(NOTA_JSON.read_text(encoding="utf-8"))

    juro = ler_juro_implicito(wb)
    comp = ler_composicao(wb)
    comp["vence_12m"] = ler_vencimento_12m(wb)
    fat = ler_fatores(wb)
    ultimo = max(fat)
    saldo_pib = round(fat[ultimo]["saldo"], 2)

    nota["juro_implicito_dbgg"] = juro
    nota["composicao_dbgg"] = comp
    ref_mes = f"{MESES_CURTOS[ultimo[1] - 1]}/{ultimo[0]}"
    r = nota["retrato"]
    r["referencia"] = ref_mes
    r["fonte"] = f"BCB, Nota de Estatísticas Fiscais (edição {aaaamm[4:]}/{aaaamm[:4]}, dados até {ref_mes}); leitura automática"
    for item in r["itens"]:
        if item["id"] == "dbgg":
            item["valor"] = round(saldo_pib, 1)
        elif item["id"] == "juro":
            item["valor"] = round(juro["valor"], 1)
        elif item["id"] == "selic":
            item["valor"] = round(comp["fatias"]["Selic (inclui compromissadas)"], 1)
            item["nota"] = "vence em 12 meses: " + f"{comp['vence_12m']:.1f}".replace(".", ",") + "%"
    nota["automatico"] = {"edicao": aaaamm, "lido_em": date.today().isoformat(),
                          "dbgg_pct_pib": saldo_pib, "referencia": f"{ultimo[0]}-{ultimo[1]:02d}"}
    if historico:
        nota["verificacao_decomposicao"] = resumo_decomposicao(fatores_anuais())
    NOTA_JSON.write_text(json.dumps(nota, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"status": "ok", "edicao": aaaamm, "referencia": nota["automatico"]["referencia"],
            "juro_implicito": juro["valor"], "selic_pct": comp["fatias"]["Selic (inclui compromissadas)"],
            "vence_12m": comp["vence_12m"], "dbgg_pct_pib": saldo_pib}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(atualizar(), ensure_ascii=False, indent=1))
    v = json.loads(NOTA_JSON.read_text(encoding="utf-8")).get("verificacao_decomposicao", {})
    print(json.dumps({k: v[k] for k in v if k != "por_ano"}, ensure_ascii=False, indent=1))
