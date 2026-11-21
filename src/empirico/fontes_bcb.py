"""Catálogo das fontes do Banco Central para a Onda 2 (sem chamadas de rede).

Ponte para a automação mensal: cada série do SGS e cada tabela das Notas de Estatísticas Fiscais
que a Onda 2 vai consumir, com o uso previsto no projeto. Os nomes das séries SGS foram conferidos
no web service oficial do SGS (método getUltimoValorXML) em nov/2026.

As tabelas da Nota são descritas pelo uso que o projeto faz delas. Os títulos oficiais e o layout das
planilhas devem ser confirmados na implementação do leitor automático, porque o BCB pode renumerar
ou reformatar tabelas entre edições.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SerieSGS:
    codigo: int
    nome: str            # nome oficial no SGS
    unidade: str
    periodicidade: str   # "M" mensal, "D" diária
    uso: str             # para que o projeto usa a série


@dataclass(frozen=True)
class TabelaNota:
    numero: int
    conteudo: str        # descrição do conteúdo usado (confirmar título oficial)
    uso: str


SERIES_SGS: dict[int, SerieSGS] = {s.codigo: s for s in [
    SerieSGS(4513, "Dívida Líquida do Setor Público (% PIB) - Total - Setor público consolidado", "% do PIB", "M",
             "Trajetória longa da dívida líquida; contraste superávits 2003–2013 × déficits 2014–2025."),
    SerieSGS(4535, "Dívida Líquida do Setor Público (% PIB) - Externa - Setor público consolidado", "% do PIB", "M",
             "Posição externa líquida do setor público (reservas): canal cambial da dívida."),
    SerieSGS(5760, "NFSP sem desvalorização cambial (% PIB) - Fluxo acumulado em 12 meses - Juros nominais - "
             "Total - Setor público consolidado", "% do PIB", "M", "Conta de juros em 12 meses."),
    SerieSGS(5793, "NFSP sem desvalorização cambial (% PIB) - Fluxo acumulado em 12 meses - Resultado primário - "
             "Total - Setor público consolidado", "% do PIB (+ = déficit)", "M", "Primário em 12 meses (sinal invertido na página)."),
    SerieSGS(4382, "PIB acumulado dos últimos 12 meses - Valores correntes (R$ milhões)", "R$ milhões", "M",
             "Crescimento do PIB nominal (θ) e conversão de fluxos em % do PIB."),
    SerieSGS(13522, "Índice nacional de preços ao consumidor - amplo (IPCA) - em 12 meses", "%", "M",
             "Inflação em 12 meses; juro real ex post."),
    SerieSGS(433, "Índice nacional de preços ao consumidor-amplo (IPCA)", "Var. % mensal", "M",
             "Separar juro real e erosão inflacionária na decomposição da dívida (formato FMI)."),
    SerieSGS(3696, "Taxa de câmbio - Livre - Dólar americano (venda) - Fim de período - mensal", "R$/US$", "M",
             "Câmbio; reação nas janelas do Copom."),
]}

TABELAS_NOTA: dict[int, TabelaNota] = {t.numero: t for t in [
    TabelaNota(19, "Fatores condicionantes da variação da dívida bruta do governo geral",
               "Decomposição anual da DBGG (juros, PIB, emissões líquidas, câmbio, outros)."),
    TabelaNota(21, "Composição da dívida bruta por indexador",
               "Fatias Selic (com compromissadas), preços, prefixada e câmbio."),
    TabelaNota(24, "Estrutura de vencimentos / prazo da dívida",
               "Parcela que vence em 12 meses (renovação do prêmio de risco no Bloco 1)."),
    TabelaNota(25, "Indicadores complementares de composição e custo da dívida bruta",
               "Juro implícito da DBGG e conferência da composição."),
]}


def series_para_coleta() -> list[int]:
    """Códigos que o pipeline mensal da Onda 2 deve baixar."""
    return sorted(SERIES_SGS)
