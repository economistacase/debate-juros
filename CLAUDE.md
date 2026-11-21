# O Debate dos Juros — Laboratório Teórico e Empírico

Briefing persistente do projeto. Leia antes de qualquer alteração.

## Objetivo e escopo

O repositório é a camada **interativa, reproduzível e viva** do debate sobre a Selic aberto pelo artigo
de André Lara Resende ("Eu acuso", 25/09/2026). O dossiê de referência (Análise Macro, nov/2026) para
na contabilidade da dívida e reconhece que "nenhuma identidade contábil resolve essa pergunta: ela
depende de um modelo de como os agentes reagem". Este projeto ocupa exatamente esse espaço.

- **Onda 1 (atual): Laboratório Teórico.** Página estática em `docs/` (GitHub Pages) com três blocos
  interativos (dívida, Fisher–Taylor, regimes monetário × fiscal) e um mapa do debate. Motor de cálculo
  e testes em Python (`src/teoria/`, `tests/`).
- **Onda 2 (futura): Laboratório Empírico.** Pipeline em `src/empirico/` consumindo SGS/BCB, Notas de
  Estatísticas Fiscais, Focus e curva de juros; SVAR e estudo de eventos do Copom; atualização mensal via
  GitHub Actions (`.github/workflows/`).

Arquivos de terceiros (dossiê da Análise Macro, prints) ficam em `referencias/`, que **não** é versionada.

## As três equações centrais

### 1. Dinâmica da dívida (Bloco 1)

$$\Delta d_t = \frac{r_t - \theta_t}{1 + \theta_t} d_{t-1} - pb_t$$

`d` = DBGG/PIB, `r` = custo nominal implícito, `θ` = crescimento do PIB nominal, `pb` = primário.
Primário estabilizador: $pb^* = \frac{r-\theta}{1+\theta} d$.

Custo implícito com composição: $r_t = \phi\,(selic_t + p_t) + (1-\phi)\,(c_t + p_t)$, em que `φ` é a fatia
indexada à Selic, `c_t` o custo da parcela não-Selic (reprecifica à taxa `λ` por ano em direção a
`selic_t + τ`) e `p_t` o prêmio de risco do estoque, que se renova pela fração `m` que vence em 12 meses:
$p_t = (1-m)p_{t-1} + m\,\kappa\,g_t$.

Extensão endógena ("Reação de Mercado"): hiato de credibilidade $g_t = \max(0,\ r^n + \pi^e_t - selic_t)$;
depreciação $\Delta e_t = \eta g_t$; inflação $\pi_t = \pi^* + a(\pi_{t-1}-\pi^*) + b\,\Delta e_t$;
expectativas adaptativas $\pi^e_t = \pi_{t-1}$; $\theta_t = \theta^{base} + (\pi_t - \pi^*)$.
No "Mundo Mecânico", `κ = η = 0` (sem reação de preços e taxas).

### 2. Fisher + regra de política (Bloco 2, Loyo 2017)

$i = r + \pi^e$ e $i = k\pi + z$ ⇒ $\pi = \dfrac{z - r}{1 - k}$.
`k > 1` (princípio de Taylor): aperto (`z↑`) reduz a inflação. `k < 1`: aperto eleva a inflação
(neofisheriano). Dinâmica com aprendizado adaptativo: $\pi_t = (\pi_{t-1} + r - z)/k$, estável só se `k > 1`.

### 3. Lastro fiscal / TFNP (Bloco 3)

$$\frac{B_{t-1}}{P_t} = E_t \sum_{j=0}^{\infty} \beta^j s_{t+j}$$

Modelo Novo Keynesiano linearizado (trimestral) com dívida de maturidade geométrica `ω` (Cochrane):
IS, Phillips, regra $i_t = \phi_\pi \pi_t + u_t$, preço do portfólio $q_t = \omega\beta E_t q_{t+1} - i_t$,
valor da dívida $\beta v_t = v_{t-1} + (\omega\beta q_t - q_{t-1}) - \pi_t - s_t$ e regra fiscal $s_t = \alpha v_{t-1}$.
Dominância monetária: `φπ > 1`, `α > 1-β`. Dominância fiscal/TFNP: `φπ < 1`, `α = 0`.
`ω = 0` ≈ dívida pós-fixada (LFT); `ω` alto ≈ prefixada longa. Câmbio via UIP real (bloco recursivo).
Resolvido por Klein (QZ) com checagem de Blanchard–Kahn em `src/teoria/regimes_tfnp.py`.

## Regra absoluta

**Nunca inventar ou desenhar curvas ilustrativas "à mão".** Toda trajetória exibida no front-end deve
ser (a) calculada por fórmulas exatas em JavaScript (`docs/js/modelo.js`, espelho de
`src/teoria/dinamica_divida.py`, para sliders em tempo real) ou (b) carregada de `.json` gerado e
validado pelos scripts Python em `src/teoria/`. O JS confere-se contra os casos de referência
exportados pelo Python ao carregar a página. Mudou uma fórmula em Python? Mude o espelho em JS e
rode `python build.py`.

## Idioma e convenções

- Todo código, comentários, testes e interface em **português (pt-BR)**.
- Front-end estático: HTML/CSS/JS puro, Plotly.js e KaTeX via CDN, sem Node.js/frameworks.
- Fluxo: `python build.py` → gera `docs/data/cenarios_teoricos.json` e roda `pytest`.
- Servidor local: `python -m http.server 8000 -d docs`.
