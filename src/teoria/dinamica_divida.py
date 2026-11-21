"""Dinâmica da dívida bruta/PIB com e sem reação de mercado.

Identidade (anual):
    Δd_t = (r_t - θ_t) / (1 + θ_t) · d_{t-1} - pb_t  [+ efeito cambial no regime com reação]

Este módulo é a referência numérica do simulador do Bloco 1. O arquivo
`docs/js/modelo.js` é o espelho exato em JavaScript; os casos de referência
exportados em `casos_referencia()` são conferidos pelo navegador ao carregar.

Todas as taxas estão em fração (0.13 = 13% a.a.); dívida e primário em fração do PIB.

Notação: γ (gamma) é a sensibilidade do prêmio de risco ao hiato de credibilidade. O símbolo k fica
reservado ao coeficiente da regra de Taylor (Bloco 2); κ, à inclinação da curva de Phillips (Bloco 3).

Composição da dívida (BCB, set/2026): Selic 56,9% | IPCA 19,9% | prefixada 17,9% | câmbio 4,6%.

Repasse da Selic ao custo médio:
- a parcela indexada à Selic (φ) reprecifica imediatamente;
- a parcela não-Selic reprecifica pela rolagem (λ = 26,8% ao ano). Como a dívida vence ao longo do ano,
  a taxa nova vale em média por meio ano no ano da rolagem (convenção de meio de ano). Assim, 1 p.p. de
  Selic muda o custo do ano 1 em φ + (1-φ)·λ/2 ≈ 0,63 p.p. e a dívida em ≈ 0,49 p.p. do PIB, perto da
  sensibilidade de 0,48 p.p. publicada pelo BCB.

Regime "Mundo Mecânico": nenhum preço reage; só a Selic e a reprecificação do estoque mudam o custo.
Regime "Reação de Mercado": se a Selic fica abaixo do juro neutro nominal (r_n + π^e), abre-se um
hiato de credibilidade g que (i) eleva o prêmio exigido na rolagem (γ·g), (ii) deprecia o câmbio, que
(iii) repassa para a inflação, que (iv) realimenta π^e e o próprio hiato. A inflação mais alta tem
dois efeitos opostos sobre a dívida: corrói o estoque (θ maior) e encarece a parcela atrelada ao IPCA.

A Selic pode ser um número (constante no horizonte) ou uma sequência com um valor por ano (2027, ...).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from typing import Sequence, Union

ANO_INICIAL = 2026
HORIZONTE = 10

Selic = Union[float, Sequence[float]]

# Proposta de Lara Resende (2026), na leitura do gráfico 3.1 do dossiê de referência:
# custo médio de 7,5% em 2027–2030 e de 5,5% a partir de 2031.
TRAJETORIA_PROPOSTA = (0.075,) * 4 + (0.055,) * 6


@dataclass(frozen=True)
class Parametros:
    """Calibração-base: BCB, Nota de Estatísticas Fiscais (set/2026)."""

    d0: float = 0.829          # DBGG/PIB em set/2026
    custo0: float = 0.13       # juro implícito da DBGG, 12 meses até set/2026
    selic: Selic = 0.145       # Selic (constante ou trajetória anual) — controle do usuário
    theta: float = 0.07        # crescimento do PIB nominal (controle do usuário)
    pb: float = -0.005         # resultado primário, % do PIB (déficit de 0,5%)
    phi: float = 0.569         # fatia da dívida indexada à Selic (controle do usuário)
    fatia_ipca: float = 0.199  # fatia indexada a preços
    fatia_cambio: float = 0.046  # fatia cambial
    m: float = 0.268           # fração que vence em 12 meses (renova o prêmio)
    lam: float = 0.268         # rolagem anual da parcela não-Selic (reprecificação)
    tau: float = 0.0           # prêmio de prazo da parcela não-Selic sobre a Selic
    selic0: float = 0.145      # Selic efetiva média out/2025–set/2026 (SGS 4189: 14,54%), calibra c0
    # --- bloco de reação de mercado ---
    reacao: bool = False
    r_neutro: float = 0.05     # juro real neutro
    pi0: float = 0.045         # inflação corrente = âncora das expectativas
    gamma: float = 1.00        # prêmio na rolagem (p.p.) por p.p. de hiato (γ = 1 é o limiar)
    eta: float = 3.0           # depreciação cambial (p.p.) por p.p. de hiato
    repasse: float = 0.10      # repasse cambial para a inflação
    persist: float = 0.50      # persistência da inflação


def selic_no_ano(p: Parametros, t: int) -> float:
    """Selic do ano t (t = 1 é o primeiro ano projetado)."""
    if isinstance(p.selic, (int, float)):
        return float(p.selic)
    return float(p.selic[min(t, len(p.selic)) - 1])


def custo_nao_selic_inicial(p: Parametros) -> float:
    """Custo da parcela não-Selic que reproduz o juro implícito do ano-base.

    Usa `phi` do ano-base (0,569) para que mudar a composição não altere o custo inicial.
    """
    phi_base = Parametros.phi
    return (p.custo0 - phi_base * p.selic0) / (1.0 - phi_base)


def variacao_divida(d_ant: float, r: float, theta: float, pb: float) -> float:
    """Identidade contábil: Δd = (r-θ)/(1+θ)·d_{t-1} - pb."""
    return (r - theta) / (1.0 + theta) * d_ant - pb


def primario_estabilizador(d: float, r: float, theta: float) -> float:
    """pb* que zera Δd dado (d, r, θ)."""
    return (r - theta) / (1.0 + theta) * d


def trajetoria_custo_fixo(d0: float, custo: float, theta: float, pb: float,
                          horizonte: int = HORIZONTE) -> list[float]:
    """Trajetória com custo médio constante (formato do gráfico 3.1 do dossiê)."""
    return trajetoria_custo_caminho(d0, [custo] * horizonte, theta, pb)


def trajetoria_custo_caminho(d0: float, custos: Sequence[float], theta: float, pb: float) -> list[float]:
    """Aritmética pura: custo médio imposto ano a ano, sem composição nem reação."""
    d = [d0]
    for r in custos:
        d.append(d[-1] + variacao_divida(d[-1], r, theta, pb))
    return d


def simular(p: Parametros, horizonte: int = HORIZONTE) -> dict:
    """Simula a razão dívida/PIB por `horizonte` anos.

    Retorna séries de comprimento horizonte+1 (ano-base incluído).
    """
    c = custo_nao_selic_inicial(p)
    premio = 0.0
    pi = p.pi0
    d = p.d0
    cambio_acum = 0.0

    s = {
        "ano": [ANO_INICIAL], "divida": [d], "custo": [p.custo0], "theta": [p.theta],
        "inflacao": [pi], "premio": [0.0], "hiato": [0.0], "cambio": [0.0], "selic": [p.selic0],
    }
    for t in range(1, horizonte + 1):
        selic = selic_no_ano(p, t)
        if p.reacao:
            hiato = max(0.0, p.r_neutro + pi - selic)    # π^e_t = π_{t-1} (adaptativa)
            dep = p.eta * hiato
            pi = p.pi0 + p.persist * (pi - p.pi0) + p.repasse * dep
            novo_premio = p.gamma * hiato
        else:
            hiato = dep = novo_premio = 0.0
        premio = (1.0 - p.m) * premio + p.m * novo_premio
        c_fim = (1.0 - p.lam) * c + p.lam * (selic + p.tau)
        c_medio = 0.5 * (c + c_fim)                      # convenção de meio de ano
        c = c_fim
        surpresa_pi = pi - p.pi0
        r = (p.phi * selic + (1.0 - p.phi) * c_medio + premio
             + p.fatia_ipca * surpresa_pi)
        theta = p.theta + surpresa_pi
        efeito_cambial = p.fatia_cambio * d * dep / (1.0 + theta)
        d = d + variacao_divida(d, r, theta, p.pb) + efeito_cambial
        cambio_acum = (1.0 + cambio_acum) * (1.0 + dep) - 1.0

        s["ano"].append(ANO_INICIAL + t)
        s["divida"].append(d)
        s["custo"].append(r)
        s["theta"].append(theta)
        s["inflacao"].append(pi)
        s["premio"].append(premio)
        s["hiato"].append(hiato)
        s["cambio"].append(cambio_acum)
        s["selic"].append(selic)

    s["pb_estabilizador"] = primario_estabilizador(s["divida"][-1], s["custo"][-1], s["theta"][-1])
    return s


def sensibilidade_selic(p: Parametros = Parametros(), delta: float = 0.01) -> float:
    """Queda da dívida (p.p. do PIB) no 1º ano para um corte de `delta` na Selic, no mundo mecânico."""
    base = simular(replace(p, reacao=False))["divida"][1]
    corte = simular(replace(p, reacao=False, selic=selic_no_ano(p, 1) - delta))["divida"][1]
    return (base - corte) * 100


def selic_que_minimiza_divida(p: Parametros, grade=None) -> tuple[float, float]:
    """Varre a Selic (2% a 20%, passo 0,1 p.p.) e devolve (selic*, dívida final mínima)."""
    if grade is None:
        grade = [x / 1000 for x in range(20, 201)]
    melhor = min(grade, key=lambda sel: simular(replace(p, selic=sel))["divida"][-1])
    return melhor, simular(replace(p, selic=melhor))["divida"][-1]


def casos_referencia() -> list[dict]:
    """Casos que o motor JS deve reproduzir exatamente (conferidos no navegador)."""
    casos = []
    for reacao in (False, True):
        for selic in (0.145, 0.10, 0.075, 0.05, list(TRAJETORIA_PROPOSTA)):
            par = Parametros(selic=selic, reacao=reacao)
            sim = simular(par)
            d = asdict(par)
            casos.append({"parametros": d, "divida": sim["divida"], "inflacao": sim["inflacao"]})
    return casos
