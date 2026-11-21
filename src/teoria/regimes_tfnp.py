"""Regimes monetário × fiscal: modelo Novo Keynesiano com teoria fiscal do nível de preços.

Modelo linearizado, trimestral, em desvios do estado estacionário (inflação zero). Variáveis em %:

    IS        x_t = E_t x_{t+1} - σ (i_t - E_t π_{t+1})
    Phillips  π_t = β E_t π_{t+1} + κ x_t
    Regra     i_t = φ_π π_t + u_t,     u_t = ρ u_{t-1} + (choque, surpresa ou anunciado)
    Títulos   q_t = ωβ E_t q_{t+1} - i_t                       (preço do portfólio, maturidade geométrica ω)
    Dívida    β v_t = v_{t-1} + (ωβ q_t - q_{t-1}) - π_t - s_t (valor real de mercado da dívida)
    Fiscal    s_t = α v_{t-1} + w_t,  w_t = ρ_w w_{t-1}   (w < 0: perda de lastro fiscal)

Iterando a equação da dívida para frente obtém-se o lastro fiscal da TFNP,
B_{t-1}/P_t = E_t Σ β^j s_{t+j}: se `α = 0` (superávit não reage), é o nível de preços que se ajusta.

    Dominância monetária (DM): φ_π > 1 e α > 1-β  → o superávit se ajusta ao preço.
    Dominância fiscal / TFNP (DF): φ_π < 1 e α = 0 → o preço se ajusta ao superávit.

`ω = 0` representa dívida de um período, reprecificada a cada trimestre (≈ LFT);
`ω` próximo de 1 representa dívida prefixada longa.

Bloco cambial (recursivo, não retroalimenta): paridade descoberta real,
rx_t = E_t rx_{t+1} - r_t, e câmbio nominal e_t = rx_t + p_t (preços externos constantes).

Solução: método de Klein (decomposição QZ ordenada) com checagem de Blanchard–Kahn.
Execute `python -m src.teoria.regimes_tfnp` para gerar `docs/data/cenarios_teoricos.json`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, replace
from datetime import date
from pathlib import Path

import numpy as np
from scipy.linalg import ordqz

from src.teoria import dinamica_divida as dd

RAIZ = Path(__file__).resolve().parents[2]
SAIDA_JSON = RAIZ / "docs" / "data" / "cenarios_teoricos.json"

HORIZONTE = 20          # trimestres exibidos
HORIZONTE_LONGO = 600   # trimestres simulados (para somas infinitas do câmbio)
ANTECEDENCIA = 4        # trimestres entre o anúncio e o corte efetivo
DIVIDA_PIB = 0.829      # DBGG/PIB para converter o valor da dívida em pontos do PIB

# Ordem do vetor de estado: 8 predeterminadas + 4 de salto
PREDET = ["u", "n1", "n2", "n3", "n4", "w", "v_lag", "q_lag"]
SALTO = ["x", "pi", "q", "v"]
VARS = PREDET + SALTO
IDX = {nome: i for i, nome in enumerate(VARS)}


@dataclass(frozen=True)
class Calibracao:
    beta: float = 0.99     # fator de desconto trimestral
    sigma: float = 1.0     # elasticidade intertemporal
    kappa: float = 0.10    # inclinação da curva de Phillips
    rho: float = 0.75      # persistência do choque de juros
    phi_pi: float = 1.5    # reação do juro à inflação
    alpha: float = 0.05    # reação do superávit à dívida
    omega: float = 0.0     # maturidade geométrica da dívida (0 = LFT)
    rho_w: float = 0.90    # persistência do choque fiscal


REGIME_DM = dict(phi_pi=1.5, alpha=0.05)
REGIME_DF = dict(phi_pi=0.8, alpha=0.0)
CHOQUE = -0.25          # corte de 1 p.p. anualizado no juro (0,25 p.p. trimestral)
CHOQUE_FISCAL = -0.25   # queda do superávit (% do valor da dívida por trimestre), ρ_w = 0,9:
                        # valor presente ≈ 2,3% da dívida ≈ 1,9 ponto do PIB


class ErroBlanchardKahn(RuntimeError):
    """O modelo não tem solução única e estável com a calibração dada."""


def matrizes(c: Calibracao) -> tuple[np.ndarray, np.ndarray]:
    """Monta A E_t y_{t+1} = B y_t."""
    n = len(VARS)
    A = np.zeros((n, n))
    B = np.zeros((n, n))
    I = IDX
    linha = 0

    def nova():
        nonlocal linha
        linha += 1
        return linha - 1

    # Choque de política: u_{t+1} = ρ u_t + n1_t ; cadeia de notícias n1 ← n2 ← n3 ← n4
    r = nova(); A[r, I["u"]] = 1; B[r, I["u"]] = c.rho; B[r, I["n1"]] = 1
    for a, b in (("n1", "n2"), ("n2", "n3"), ("n3", "n4")):
        r = nova(); A[r, I[a]] = 1; B[r, I[b]] = 1
    r = nova(); A[r, I["n4"]] = 1
    # Choque fiscal: w_{t+1} = ρ_w w_t
    r = nova(); A[r, I["w"]] = 1; B[r, I["w"]] = c.rho_w
    # Defasagens
    r = nova(); A[r, I["v_lag"]] = 1; B[r, I["v"]] = 1
    r = nova(); A[r, I["q_lag"]] = 1; B[r, I["q"]] = 1
    # IS: E x' + σ E π' = x + σ(φ π + u)
    r = nova(); A[r, I["x"]] = 1; A[r, I["pi"]] = c.sigma
    B[r, I["x"]] = 1; B[r, I["pi"]] = c.sigma * c.phi_pi; B[r, I["u"]] = c.sigma
    # Phillips: β E π' = π - κ x
    r = nova(); A[r, I["pi"]] = c.beta; B[r, I["pi"]] = 1; B[r, I["x"]] = -c.kappa
    # Preço dos títulos: ωβ E q' = q + φ π + u
    r = nova(); A[r, I["q"]] = c.omega * c.beta
    B[r, I["q"]] = 1; B[r, I["pi"]] = c.phi_pi; B[r, I["u"]] = 1
    # Valor da dívida (estática): 0 = β v - (1-α) v_lag - ωβ q + q_lag + π + w
    r = nova()
    B[r, I["v"]] = c.beta; B[r, I["v_lag"]] = -(1 - c.alpha)
    B[r, I["q"]] = -c.omega * c.beta; B[r, I["q_lag"]] = 1; B[r, I["pi"]] = 1; B[r, I["w"]] = 1
    assert linha == n
    return A, B


def resolver(c: Calibracao) -> tuple[np.ndarray, np.ndarray]:
    """Método de Klein. Retorna (F, P): saltos = F·k_t e k_{t+1} = P·k_t."""
    A, B = matrizes(c)
    nk = len(PREDET)

    def estavel(alfa, beta_):
        # autovalor generalizado λ = beta/alfa (pencil B - λA); estável se |λ| < 1
        return np.abs(beta_) < np.abs(alfa) * (1 - 1e-10)

    S, T, alfa, beta_, Q, Z = ordqz(A, B, sort=estavel, output="complex")
    n_estaveis = int(np.sum(estavel(alfa, beta_)))
    if n_estaveis != nk:
        raise ErroBlanchardKahn(
            f"{n_estaveis} raízes estáveis para {nk} variáveis predeterminadas "
            f"({'indeterminação' if n_estaveis > nk else 'sem solução estável'})."
        )
    Z11, Z21 = Z[:nk, :nk], Z[nk:, :nk]
    S11, T11 = S[:nk, :nk], T[:nk, :nk]
    Z11_inv = np.linalg.inv(Z11)
    F = np.real(Z21 @ Z11_inv)
    P = np.real(Z11 @ np.linalg.solve(S11, T11) @ Z11_inv)
    return F, P


def simular(c: Calibracao, anunciado: bool = False, choque: float = CHOQUE,
            choque_fiscal: float = 0.0,
            periodos: int = HORIZONTE_LONGO) -> dict[str, np.ndarray]:
    """Resposta a um corte de juros, surpresa em t=0 ou anunciado em t=0 para t=ANTECEDENCIA.

    `choque_fiscal` < 0 acrescenta, em t=0, uma queda persistente dos superávits (perda de lastro).
    """
    F, P = resolver(c)
    k = np.zeros(len(PREDET))
    if anunciado:
        k[PREDET.index("n4")] = choque     # u_4 = choque, conhecido desde t = 0
    else:
        k[PREDET.index("u")] = choque
    k[PREDET.index("w")] = choque_fiscal
    Y = np.zeros((periodos, len(VARS)))
    for t in range(periodos):
        j = F @ k
        Y[t] = np.concatenate([k, j])
        k = P @ k
    return {nome: Y[:, IDX[nome]] for nome in VARS}


def derivar_series(c: Calibracao, s: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Séries exibidas (anualizadas onde cabe) a partir da simulação longa."""
    pi, u = s["pi"], s["u"]
    i = c.phi_pi * pi + u
    juro_real = i - np.append(pi[1:], 0.0)                  # r_t = i_t - π_{t+1}
    # rx_t = -Σ_{j≥t} r_j  (soma para frente)
    cambio_real = -np.cumsum(juro_real[::-1])[::-1]
    nivel_precos = np.cumsum(pi)
    superavit = c.alpha * s["v_lag"] + s["w"]
    return {
        "inflacao": 4 * pi,                                  # % a.a.
        "juro_nominal": 4 * i,                               # p.p. a.a.
        "juro_real": 4 * juro_real,                          # p.p. a.a.
        "cambio": cambio_real + nivel_precos,                # % (alta = depreciação)
        "nivel_precos": nivel_precos,                        # %
        "hiato": s["x"],                                     # %
        "divida_pib": DIVIDA_PIB * (s["v"] - s["x"]),        # pontos do PIB
        "superavit": superavit,                              # % do valor da dívida
    }


def residuos(c: Calibracao, s: dict[str, np.ndarray]) -> dict[str, float]:
    """Erro máximo de cada equação ao longo da trajetória (deve ser ~0)."""
    x, pi, q, v, u, w = s["x"], s["pi"], s["q"], s["v"], s["u"], s["w"]
    i = c.phi_pi * pi + u
    t = slice(1, len(x) - 1)
    tp = slice(2, len(x))
    tm = slice(0, len(x) - 2)
    return {
        "IS": float(np.max(np.abs(x[t] - (x[tp] - c.sigma * (i[t] - pi[tp]))))),
        "Phillips": float(np.max(np.abs(pi[t] - (c.beta * pi[tp] + c.kappa * x[t])))),
        "titulos": float(np.max(np.abs(q[t] - (c.omega * c.beta * q[tp] - i[t])))),
        "divida": float(np.max(np.abs(
            c.beta * v[t] - (v[tm] + c.omega * c.beta * q[t] - q[tm] - pi[t] - c.alpha * v[tm] - w[t])))),
    }


def _linha(id_, rotulo, papel, c: Calibracao, anunciado=False, choque_fiscal=0.0) -> dict:
    s = simular(c, anunciado=anunciado, choque_fiscal=choque_fiscal)
    series = derivar_series(c, s)
    return {
        "id": id_, "rotulo": rotulo, "papel": papel,
        "calibracao": asdict(c), "anunciado": anunciado, "choque_fiscal": choque_fiscal,
        "series": {k: [round(float(val), 6) for val in arr[: HORIZONTE + 1]]
                   for k, arr in series.items()},
    }


def gerar_cenarios() -> dict:
    base = Calibracao()
    dm = replace(base, **REGIME_DM)
    df_lft = replace(base, **REGIME_DF, omega=0.0)
    df_pre = replace(base, **REGIME_DF, omega=0.95)

    return {
        "meta": {
            "titulo": "O Debate dos Juros — cenários teóricos (Onda 1)",
            "gerado_em": date.today().isoformat(),
            "gerador": "src/teoria/regimes_tfnp.py",
            "choque": "corte de 1 p.p. (anualizado) no juro, persistência ρ = %.2f" % base.rho,
            "unidades": {
                "inflacao": "% a.a., desvio", "juro_nominal": "p.p. a.a., desvio",
                "juro_real": "p.p. a.a., desvio", "cambio": "% (alta = depreciação)",
                "nivel_precos": "%", "hiato": "%", "divida_pib": "pontos do PIB",
                "superavit": "% do valor da dívida",
            },
            "calibracao_base": asdict(base),
            "regimes": {"dominancia_monetaria": REGIME_DM, "dominancia_fiscal": REGIME_DF},
            "antecedencia_trimestres": ANTECEDENCIA,
            "choque_fiscal": CHOQUE_FISCAL,
        },
        "trimestres": list(range(HORIZONTE + 1)),
        "cenarios": {
            "dominancia_monetaria": {
                "titulo": "Dominância Monetária",
                "descricao": ("O Banco Central segue o princípio de Taylor (φπ = 1,5) e o Tesouro ajusta o "
                              "superávit à dívida. O corte de juros estimula a demanda e eleva a inflação: "
                              "o resultado de livro-texto."),
                "linhas": [_linha("dm", "Dominância monetária", "principal", dm),
                           _linha("df_lft", "Dominância fiscal (LFT)", "referencia", df_lft)],
            },
            "dominancia_fiscal": {
                "titulo": "Dominância Fiscal (TFNP)",
                "descricao": ("Juro reage pouco à inflação (φπ = 0,8) e o superávit não reage à dívida: o nível "
                              "de preços se ajusta para igualar o valor real da dívida ao lastro fiscal. "
                              "A composição da dívida passa a importar: com LFT o corte não reprecifica o "
                              "estoque; com prefixados longos, sim. E se o corte vier com superávits menores "
                              "(perda de lastro), a própria TFNP prevê inflação."),
                "linhas": [_linha("df_lft", "Dívida pós-fixada (LFT, ω = 0)", "principal", df_lft),
                           _linha("df_pre", "Dívida prefixada longa (ω = 0,95)", "secundaria", df_pre),
                           _linha("df_lastro", "LFT + perda de lastro fiscal", "alerta", df_lft,
                                  choque_fiscal=CHOQUE_FISCAL),
                           _linha("dm", "Dominância monetária", "referencia", dm)],
            },
            "antecipacao": {
                "titulo": "Efeito Antecipação",
                "descricao": ("O corte é anunciado hoje para daqui a %d trimestres. Com expectativas racionais, "
                              "câmbio, inflação e juro real se movem já no anúncio, antes de a Selic cair."
                              % ANTECEDENCIA),
                "marcador": ANTECEDENCIA,
                "linhas": [_linha("dm_anunciado", "Anunciado: dominância monetária", "principal", dm, True),
                           _linha("df_anunciado", "Anunciado: dominância fiscal (LFT)", "secundaria",
                                  df_lft, True),
                           _linha("dm", "Surpresa: dominância monetária", "referencia", dm)],
            },
        },
        "divida": {
            "calibracao": asdict(dd.Parametros()),
            "casos_referencia": dd.casos_referencia(),
            "fonte": "BCB, Nota de Estatísticas Fiscais (set/2026), via dossiê 'O debate dos juros' (nov/2026).",
        },
    }


def exportar(caminho: Path = SAIDA_JSON) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = gerar_cenarios()
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1, allow_nan=False),
                       encoding="utf-8")
    return caminho


if __name__ == "__main__":
    destino = exportar()
    print(f"JSON exportado: {destino.relative_to(RAIZ)}")
