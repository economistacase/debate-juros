"""Catálogo das fontes do Banco Central para a Onda 2 (sem chamadas de rede).

Ponte para a automação mensal: cada série do SGS e cada tabela das Notas de Estatísticas Fiscais
que a Onda 2 vai consumir, com o uso previsto no projeto. Os nomes das séries SGS foram conferidos
no web service oficial do SGS (método getUltimoValorXML) em nov/2026.

Os títulos das tabelas da Nota foram confirmados na edição de out/2026 e conferidos nas edições de
2018 a 2025 (numeração estável). O leitor automático (`src/dados/nota_bcb.py`) localiza as tabelas
pelo título e as linhas pelo rótulo, para resistir a renumerações futuras.
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
    TabelaNota(19, "Dívida bruta do Governo Geral — fatores condicionantes — fluxos acumulados no ano",
               "Decomposição anual da DBGG (juros, PIB, emissões líquidas, câmbio, outros)."),
    TabelaNota(21, "Dívida bruta do Governo Geral — participação percentual por indexador",
               "Fatias Selic (com compromissadas), preços, prefixada e câmbio."),
    TabelaNota(24, "Taxa de juros implícita na DBGG — taxa acumulada em doze meses",
               "Juro implícito da DBGG (custo médio da dívida no Bloco 1 e no retrato)."),
    TabelaNota(25, "Cronograma de vencimento da DBGG",
               "Parcela que vence em até 1 ano (renovação do prêmio de risco no Bloco 1)."),
]}


def series_para_coleta() -> list[int]:
    """Códigos que o pipeline mensal da Onda 2 deve baixar."""
    return sorted(SERIES_SGS)
