"""Onda 2 — primeira estimativa empírica de γ e estudo de eventos do Copom.

γ (Bloco 1) é o prêmio exigido na rolagem, em p.p., por p.p. de "hiato de credibilidade":
    g_t = max(0, r_n + π^e_t − Selic_t)        (Selic abaixo do juro neutro nominal)
Duas medidas de prêmio marginal:
    (a) spread da LFT (Tesouro Selic, 2 a 6 anos) sobre a Selic — o prêmio exigido na dívida pós-fixada
        (só a partir de 2016: antes disso a taxa do Tesouro Direto era praticamente fixa);
    (b) prêmio prefixado = taxa da LTN (Tesouro Prefixado, 2 a 4 anos) − Selic média esperada pelo Focus
        para o fim do ano corrente e dos dois seguintes.
Estimação mensal por MQO com erros de Newey-West; sensibilidade a r_n ∈ {4; 4,5; 5; 5,5; 6}%.

Estudo de eventos: para cada reunião do Copom desde 2006, surpresa = Selic decidida − mediana do Focus
para aquela reunião (última pesquisa antes da decisão). Respostas do dia seguinte: LTN, spread da LFT,
câmbio (PTAX) e, uma semana depois, a inflação esperada para 12 meses.

Limitação central (endogeneidade): o Banco Central tende a manter a Selic alta justamente quando o risco
fiscal é alto, o que reduz g quando o prêmio é alto e enviesa γ para BAIXO. A estimativa é exploratória;
a página diz isso com destaque.

Uso:  python -m src.empirico.onda2 [--renovar]   → docs/data/onda2.json
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src.empirico import fontes
from src.empirico.estatistica import lags_newey_west, ols

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "docs" / "data" / "onda2.json"
R_NEUTROS = [4.0, 4.5, 5.0, 5.5, 6.0]
R_NEUTRO_BASE = 5.0
INICIO = "2006-01-01"
INICIO_LFT = "2016-01-01"


# ----------------------------------------------------------------------------- construção dos dados

def taxas_diarias(td: pd.DataFrame, tipo: str, prazo_min: float, prazo_max: float) -> pd.Series:
    sel = td[(td["Tipo Titulo"] == tipo) & td["prazo_anos"].between(prazo_min, prazo_max)]
    return sel.groupby("data")["taxa"].mean().sort_index()


def focus_12m(renovar: bool) -> pd.Series:
    df = fontes.focus("ExpectativasMercadoInflacao12Meses",
                      "Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0 and Data ge '2004-01-01'",
                      "Data,Mediana", "focus_ipca12m.json", renovar)
    return pd.Series(df["Mediana"].values, index=pd.to_datetime(df["Data"])).sort_index()


def focus_selic_anual(renovar: bool) -> pd.Series:
    """Selic média esperada: média das medianas de fim de ano para os três anos à frente (horizonte da LTN)."""
    df = fontes.focus("ExpectativasMercadoAnuais", "Indicador eq 'Selic' and baseCalculo eq 0 and Data ge '2004-01-01'",
                      "Data,DataReferencia,Mediana", "focus_selic_anual.json", renovar)
    df["Data"] = pd.to_datetime(df["Data"])
    df["ref"] = df["DataReferencia"].astype(int)
    df = df.groupby(["Data", "ref"])["Mediana"].mean().reset_index()
    saida = {}
    for d, g in df.groupby("Data"):
        y = d.year
        vals = g.set_index("ref")["Mediana"]
        # três primeiros anos disponíveis a partir do corrente (em dezembro o Focus já começa no ano seguinte)
        anos = sorted(a for a in vals.index if a >= y)[:3]
        if len(anos) == 3 and anos[-1] - anos[0] == 2:
            saida[d] = float(vals[anos].mean())
    return pd.Series(saida).sort_index()


def painel_mensal(renovar: bool = False) -> pd.DataFrame:
    td = fontes.tesouro_direto(renovar)
    selic = fontes.sgs_mensal(4189, renovar=renovar)
    mensal = lambda s: s.resample("MS").mean()
    df = pd.DataFrame({
        "selic": selic.resample("MS").last(),
        "pi_e": mensal(focus_12m(renovar)),
        "selic_esperada": mensal(focus_selic_anual(renovar)),
        "ltn": mensal(taxas_diarias(td, "Tesouro Prefixado", 2, 4)),
        "lft": mensal(taxas_diarias(td, "Tesouro Selic", 2, 6)),
    })
    df = df[df.index >= INICIO]
    df.loc[df.index < INICIO_LFT, "lft"] = np.nan
    df["premio_pre"] = df["ltn"] - df["selic_esperada"]
    for rn in R_NEUTROS:
        df[f"g_{rn}"] = np.maximum(0.0, rn + df["pi_e"] - df["selic"])
    return df


# ----------------------------------------------------------------------------- estimação de γ

def estimar_gamma(df: pd.DataFrame, medida: str, rn: float) -> dict:
    d = df[[medida, f"g_{rn}"]].dropna()
    y, g = d[medida].values, d[f"g_{rn}"].values
    lags = lags_newey_west(len(d))
    est = ols(y, np.column_stack([np.ones(len(d)), g]), lags=lags, nomes=["const", "gamma"])
    # versão dinâmica: P_t = a + ρ P_{t-1} + b g_t  →  γ de longo prazo = b / (1 − ρ)
    dd = d.assign(lag=d[medida].shift(1)).dropna()
    din = ols(dd[medida].values, np.column_stack([np.ones(len(dd)), dd["lag"].values, dd[f"g_{rn}"].values]),
              lags=lags, nomes=["const", "rho", "b"])
    b, rho = din["coef"]["b"]["valor"], din["coef"]["rho"]["valor"]
    V = np.array(din["vcov"])[1:, 1:]                     # [rho, b]
    grad = np.array([b / (1 - rho) ** 2, 1 / (1 - rho)])
    ep_lp = float(math.sqrt(grad @ V @ grad))
    return {
        "medida": medida, "r_neutro": rn, "periodo": [d.index.min().strftime("%Y-%m"), d.index.max().strftime("%Y-%m")],
        "n": est["n"], "meses_com_hiato": int((g > 0).sum()), "lags": lags,
        "gamma": est["coef"]["gamma"], "constante": est["coef"]["const"]["valor"], "r2": est["r2"],
        "dinamico": {"rho": din["coef"]["rho"], "b": din["coef"]["b"], "gamma_longo_prazo": {"valor": b / (1 - rho), "ep": ep_lp}},
    }


# ----------------------------------------------------------------------------- estudo de eventos

def _antes(s: pd.Series, t) -> float | None:
    v = s[s.index <= t]
    return float(v.iloc[-1]) if len(v) else None


def _depois(s: pd.Series, t, dias: int = 0) -> float | None:
    v = s[s.index > t + pd.Timedelta(days=dias)]
    return float(v.iloc[0]) if len(v) else None


def eventos_copom(renovar: bool = False) -> pd.DataFrame:
    cop = fontes.copom(renovar)
    cop = cop[cop["data"] >= INICIO].copy()
    cop["ano"] = cop["data"].dt.year
    cop["k"] = cop.groupby("ano").cumcount() + 1
    meta = fontes.sgs_diaria(432, renovar=renovar)
    ptax = fontes.sgs_diaria(1, renovar=renovar)
    td = fontes.tesouro_direto(False)
    ltn = taxas_diarias(td, "Tesouro Prefixado", 2, 4)
    lft = taxas_diarias(td, "Tesouro Selic", 2, 6)
    pi12 = focus_12m(False)
    exp = fontes.focus("ExpectativasMercadoSelic", "baseCalculo eq 0 and Data ge '2004-01-01'",
                       "Data,Reuniao,Mediana", "focus_selic_reuniao.json", renovar)
    exp["Data"] = pd.to_datetime(exp["Data"])
    linhas = []
    for _, r in cop.iterrows():
        t = r["data"]
        cod = f"R{r['k']}/{r['ano']}"
        e = exp[(exp["Reuniao"] == cod) & (exp["Data"] < t)]
        decidido, anterior = _depois(meta, t), _antes(meta, t)
        if e.empty or decidido is None or anterior is None:
            continue
        esperado = float(e.iloc[-1]["Mediana"])
        resp = {}
        for nome, s, dias in (("ltn", ltn, 0), ("lft", lft, 0), ("cambio", ptax, 0), ("pi_e", pi12, 6)):
            a, b = _antes(s, t), _depois(s, t, dias)
            if a is not None and b is not None:
                resp[nome] = (b / a - 1) * 100 if nome == "cambio" else b - a
        if t < pd.Timestamp(INICIO_LFT):
            resp.pop("lft", None)
        linhas.append({"data": t.strftime("%Y-%m-%d"), "reuniao": int(r["nro_reuniao"]), "codigo": cod,
                       "selic_anterior": anterior, "selic_decidida": decidido, "esperado": esperado,
                       "surpresa": round(decidido - esperado, 4), "variacao": round(decidido - anterior, 4), **resp})
    return pd.DataFrame(linhas)


def regressoes_eventos(ev: pd.DataFrame) -> dict:
    saida = {}
    for nome in ("ltn", "lft", "cambio", "pi_e"):
        d = ev[["surpresa", nome]].dropna()
        est = ols(d[nome].values, np.column_stack([np.ones(len(d)), d["surpresa"].values]), lags=0, nomes=["const", "surpresa"])
        saida[nome] = {"n": est["n"], "surpresas_nao_nulas": int((d["surpresa"].abs() >= 0.05).sum()),
                       "coef": est["coef"]["surpresa"], "r2": est["r2"]}
    return saida


# ----------------------------------------------------------------------------- exportação

def exportar(renovar: bool = False, caminho: Path = SAIDA) -> Path:
    df = painel_mensal(renovar)
    estimativas = [estimar_gamma(df, m, rn) for m in ("lft", "premio_pre") for rn in R_NEUTROS]
    ev = eventos_copom(renovar)
    limpar = lambda v: None if (v is None or (isinstance(v, float) and not math.isfinite(v))) else round(float(v), 4)
    dados = {
        "meta": {"gerado_em": date.today().isoformat(), "gerador": "src/empirico/onda2.py", "r_neutro_base": R_NEUTRO_BASE,
                 "fontes": ["Tesouro Transparente — Taxas do Tesouro Direto (PrecoTaxaTesouroDireto.csv)",
                            "BCB/SGS 4189 (Selic efetiva mensal), 432 (meta Selic diária), 1 (PTAX venda)",
                            "BCB/Focus — IPCA 12 meses, Selic anual e Selic por reunião (mediana, base 0)",
                            "BCB — comunicados do Copom (datas das reuniões)"]},
        "mensal": {"meses": [d.strftime("%Y-%m") for d in df.index],
                   **{c: [limpar(v) for v in df[c].values] for c in ("selic", "pi_e", "selic_esperada", "ltn", "lft",
                                                                     "premio_pre", f"g_{R_NEUTRO_BASE}")}},
        "gamma": estimativas,
        "eventos": {"lista": json.loads(ev.to_json(orient="records")), "regressoes": regressoes_eventos(ev)},
    }
    caminho.write_text(json.dumps(dados, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return caminho


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    destino = exportar(renovar="--renovar" in sys.argv)
    d = json.loads(destino.read_text(encoding="utf-8"))
    print(f"{destino.relative_to(RAIZ)}: {len(d['mensal']['meses'])} meses, {len(d['eventos']['lista'])} reuniões")
    for e in d["gamma"]:
        g, lp = e["gamma"], e["dinamico"]["gamma_longo_prazo"]
        print(f"  {e['medida']:10s} r_n={e['r_neutro']}: γ={g['valor']:+.3f} (ep {g['ep']:.3f}, IC {g['ic95'][0]:+.2f} a {g['ic95'][1]:+.2f})"
              f"  γ_LP={lp['valor']:+.3f} (ep {lp['ep']:.3f})  n={e['n']} meses c/ hiato={e['meses_com_hiato']}  {e['periodo']}")
    for k, v in d["eventos"]["regressoes"].items():
        c = v["coef"]
        print(f"  evento {k:7s}: b={c['valor']:+.3f} (ep {c['ep']:.3f}, p={c['p']:.3f}) n={v['n']} surpresas≠0: {v['surpresas_nao_nulas']}")
