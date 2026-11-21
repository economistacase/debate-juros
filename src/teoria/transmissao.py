"""Transmissão da Selic: potência (lente 3) e canal de renda dos juros (lentes 5 e 6).

Modelo anual, linear, em desvios em relação a um cenário-base. Um aperto de Δ p.p. na Selic dura D anos.

    Δi_t   = Δ se t ≤ D, senão 0
    Δr_t   = Δi_t − Δπ_{t−1}                       juro real (expectativas adaptativas)
    conv_t = −σ (1 − s) Δr_t                       canal convencional: só o crédito livre responde (s = fatia direcionada)
    renda_t = c (1 − τ) φ d Δi_t                    canal de renda: juros pagos sobre a dívida atrelada à Selic,
                                                   líquidos de IR, viram renda; a fração c é consumida
    x_t    = conv_t + renda_t                      hiato do produto (p.p.)
    Δπ_t   = ω Δπ_{t−1} + κ x_t                    curva de Phillips com inércia ω (indexação)

Potência = redução da inflação no 2º ano por 1 p.p. de aperto. Como o modelo é linear, o aperto necessário
para reduzir a inflação em A p.p. é A / potência (exato, sem busca numérica).

Notação: κ tem o mesmo significado do Bloco 3 (inclinação da curva de Phillips), aqui em frequência anual.
σ, κ e ω são calibrações ilustrativas: o laboratório mostra o mecanismo e as magnitudes RELATIVAS
(quanto a potência cai com o direcionado; quando o canal de renda domina). Estimá-las é tarefa da Onda 2.

`docs/js/transmissao.js` é o espelho exato em JavaScript, conferido contra `casos_referencia()`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SAIDA_JSON = RAIZ / "docs" / "data" / "transmissao.json"
HORIZONTE = 6


@dataclass(frozen=True)
class ParTransmissao:
    delta: float = 1.0      # aperto na Selic (p.p.)
    duracao: int = 2        # anos em que o aperto é mantido
    sigma: float = 0.5      # sensibilidade do hiato ao juro real no crédito livre (p.p. por p.p.)
    s: float = 0.437        # fatia do crédito direcionado (SGS 20593 / 20539, set/2026)
    omega: float = 0.5      # inércia: fração da inflação passada que se repete
    kappa: float = 0.3      # inclinação anual da curva de Phillips
    c: float = 0.0          # propensão a consumir a renda de juros (0 = canal de renda desligado)
    tau: float = 0.15       # IR sobre a renda de juros
    phi: float = 0.569      # fatia da dívida bruta atrelada à Selic
    d: float = 0.829        # dívida bruta / PIB


def resposta(p: ParTransmissao, horizonte: int = HORIZONTE) -> dict:
    """Trajetórias anuais (t = 1..horizonte) dos desvios provocados pelo aperto."""
    s = {k: [] for k in ("ano", "delta_i", "delta_r", "conv", "renda", "hiato", "inflacao")}
    pi_ant = 0.0
    for t in range(1, horizonte + 1):
        di = p.delta if t <= p.duracao else 0.0
        dr = di - pi_ant
        conv = -p.sigma * (1.0 - p.s) * dr
        renda = p.c * (1.0 - p.tau) * p.phi * p.d * di
        x = conv + renda
        pi = p.omega * pi_ant + p.kappa * x
        for k, v in zip(s, (t, di, dr, conv, renda, x, pi)):
            s[k].append(v)
        pi_ant = pi
    return s


def potencia(p: ParTransmissao) -> float:
    """Redução da inflação no 2º ano por 1 p.p. de aperto (positiva = o aperto desinfla)."""
    return -resposta(replace(p, delta=1.0))["inflacao"][1]


def aperto_necessario(p: ParTransmissao, alvo: float = 1.0) -> float | None:
    """Aperto (p.p.) para reduzir a inflação do 2º ano em `alvo` p.p.; None se o aperto não desinfla."""
    pot = potencia(p)
    return alvo / pot if pot > 1e-12 else None


def efeito_impacto(p: ParTransmissao) -> dict:
    """Decomposição do efeito de +1 p.p. de Selic sobre o hiato no 1º ano."""
    conv = -p.sigma * (1.0 - p.s)
    renda = p.c * (1.0 - p.tau) * p.phi * p.d
    return {"convencional": conv, "renda": renda, "liquido": conv + renda}


def limiar_consumo(p: ParTransmissao) -> float:
    """Propensão a consumir acima da qual o aperto AQUECE a demanda no 1º ano (c* = σ(1−s) / ((1−τ)φd))."""
    return p.sigma * (1.0 - p.s) / ((1.0 - p.tau) * p.phi * p.d)


def sacrificio(p: ParTransmissao) -> float:
    """Hiato acumulado (p.p.·ano) no horizonte: custo em atividade do aperto."""
    return sum(resposta(p)["hiato"])


def casos_referencia() -> list[dict]:
    casos = []
    for s in (0.0, 0.437, 0.7):
        for c in (0.0, 0.2, 0.8):
            for omega in (0.0, 0.5):
                p = ParTransmissao(s=s, c=c, omega=omega)
                r = resposta(p)
                casos.append({"parametros": asdict(p), "inflacao": r["inflacao"], "hiato": r["hiato"],
                              "potencia": potencia(p), "limiar": limiar_consumo(p)})
    return casos


def exportar(caminho: Path = SAIDA_JSON) -> Path:
    base = ParTransmissao()
    dados = {
        "meta": {"gerador": "src/teoria/transmissao.py", "horizonte": HORIZONTE,
                 "nota": "Calibração ilustrativa de σ, κ e ω; magnitudes relativas são o foco."},
        "calibracao": asdict(base),
        "casos_referencia": casos_referencia(),
    }
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1, allow_nan=False), encoding="utf-8")
    return caminho


if __name__ == "__main__":
    print(exportar())
