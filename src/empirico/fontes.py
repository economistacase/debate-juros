"""Download e cache das fontes da Onda 2 (Tesouro Direto, SGS diário, Focus, Copom)."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).with_name("_cache")
URL_TD = ("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/"
          "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{c}/dados?formato=json&dataInicial={i}&dataFinal={f}"
URL_FOCUS = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/{entidade}?"
URL_COPOM = "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=400"
UA = {"User-Agent": "Mozilla/5.0 (painel-juros)", "Cache-Control": "no-cache", "Pragma": "no-cache"}


def _get(url: str, binario: bool = False, tentativas: int = 5):
    """GET com novas tentativas. A API do BCB às vezes responde 304 (Not Modified) sem pedido condicional,
    vindo de um cache intermediário: nesse caso, repete com um parâmetro anti-cache."""
    alvo = url
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(alvo, headers=UA), timeout=180) as r:
                dados = r.read()
            return dados if binario else json.loads(dados.decode("utf-8"))
        except Exception:
            if i == tentativas - 1:
                raise
            alvo = url + ("&" if "?" in url else "?") + f"nc={int(time.time() * 1000)}{i}"
            time.sleep(2 * (i + 1))


def _cache_json(nome: str, produtor, renovar: bool):
    CACHE.mkdir(exist_ok=True)
    arq = CACHE / nome
    if arq.exists() and not renovar:
        return json.loads(arq.read_text(encoding="utf-8"))
    dados = produtor()
    arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def tesouro_direto(renovar: bool = False) -> pd.DataFrame:
    """Taxas diárias do Tesouro Direto (todas as famílias de títulos)."""
    CACHE.mkdir(exist_ok=True)
    arq = CACHE / "PrecoTaxaTesouroDireto.csv"
    if renovar or not arq.exists():
        arq.write_bytes(_get(URL_TD, binario=True))
    df = pd.read_csv(arq, sep=";", decimal=",")
    df["data"] = pd.to_datetime(df["Data Base"], dayfirst=True)
    df["vencimento"] = pd.to_datetime(df["Data Vencimento"], dayfirst=True)
    df["prazo_anos"] = (df["vencimento"] - df["data"]).dt.days / 365.25
    df["taxa"] = df["Taxa Compra Manha"]
    return df[["Tipo Titulo", "data", "vencimento", "prazo_anos", "taxa"]]


def sgs_diaria(codigo: int, inicio: str = "2004-01-01", renovar: bool = False) -> pd.Series:
    """Série diária do SGS, baixada em janelas de 5 anos (a API limita séries diárias a 10 anos)."""
    def produzir():
        saida, ini = [], date.fromisoformat(inicio)
        hoje = date.today() - timedelta(days=1)          # janela termina ontem (evita respostas vazias/304)
        while ini <= hoje:
            fim = min(date(ini.year + 5, ini.month, ini.day) - timedelta(days=1), hoje)
            url = URL_SGS.format(c=codigo, i=ini.strftime("%d/%m/%Y"), f=fim.strftime("%d/%m/%Y"))
            saida += _get(url)
            ini = fim + timedelta(days=1)
        return saida
    bruto = _cache_json(f"sgs_{codigo}.json", produzir, renovar)
    s = pd.Series({pd.to_datetime(d["data"], dayfirst=True): float(d["valor"]) for d in bruto if d["valor"] not in ("", None)})
    return s.sort_index()


def sgs_mensal(codigo: int, inicio: str = "01/01/2004", renovar: bool = False) -> pd.Series:
    bruto = _cache_json(f"sgs_m_{codigo}.json", lambda: _get(URL_SGS.format(c=codigo, i=inicio, f=date.today().strftime("%d/%m/%Y"))), renovar)
    s = pd.Series({pd.to_datetime(d["data"], dayfirst=True): float(d["valor"]) for d in bruto if d["valor"] not in ("", None)})
    return s.sort_index()


def focus(entidade: str, filtro: str, campos: str, nome_cache: str, renovar: bool = False) -> pd.DataFrame:
    def produzir():
        url = URL_FOCUS.format(entidade=entidade) + urllib.parse.urlencode(
            {"$filter": filtro, "$select": campos, "$orderby": "Data", "$top": "300000", "$format": "json"},
            quote_via=urllib.parse.quote)
        return _get(url)["value"]
    return pd.DataFrame(_cache_json(nome_cache, produzir, renovar))


def copom(renovar: bool = False) -> pd.DataFrame:
    dados = _cache_json("copom.json", lambda: _get(URL_COPOM)["conteudo"], renovar)
    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["dataReferencia"])
    return df.sort_values("data").reset_index(drop=True)
