# O Debate dos Juros — Laboratório Teórico e Empírico

Briefing persistente do projeto. Leia antes de qualquer alteração.

## Objetivo e escopo

O repositório é a camada **interativa, reproduzível e viva** do debate sobre a Selic aberto pelo artigo
de André Lara Resende ("Eu acuso", 25/09/2026). O dossiê de referência (Análise Macro, nov/2026) para
na contabilidade da dívida e reconhece que "nenhuma identidade contábil resolve essa pergunta: ela
depende de um modelo de como os agentes reagem". Este projeto ocupa exatamente esse espaço.

- **Eixo editorial:** a pergunta permanente “por que o juro brasileiro é alto e o que aconteceria se caísse?”,
  vista por seis lentes, do consenso à heterodoxia (1 NK/metas, 2 fiscal/prêmio, 3 institucional, 4 TFNP/
  neofisheriana, 5 pós-keynesiana, 6 MMT). Lara Resende (2026) é estudo de caso (Parte 5), não eixo.
  Página: 1 dados → 2 lentes → 3 laboratório → 4 mapa (afirmações × lentes) → 5 episódio 2026.
  Apresentar cada lente em sua melhor versão, com status de evidência; evitar falso equilíbrio.
- **Parte 1 da página: Dados reais.** `src/dados/bcb.py` baixa SGS/BCB (4189, 432, 13522, 13762, 4513,
  5793, 5760, 4382, 3696 — códigos conferidos pelo nome oficial) e Focus (IPCA 12m) e grava
  `docs/data/painel.json`; `docs/js/dados.js` desenha placar, conta da dívida e gráficos. Juro implícito
  da DBGG e composição por indexador não estão no SGS: ficam em `src/dados/nota_fiscal.json`
  (atualização manual). Workflow `atualiza-dados.yml` roda toda segunda. Fluxo de página:
  dados → intuição (laboratório) → dados reais no laboratório (Onda 2).
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
indexada à Selic, `c_t` o custo da parcela não-Selic (reprecifica à taxa `λ = 26,8%` por ano em direção a
`selic_t + τ`, convenção de meio de ano) e `p_t` o prêmio de risco do estoque, que se renova pela fração `m` que vence em 12 meses:
$p_t = (1-m)p_{t-1} + m\,\gamma\,g_t$.

Extensão endógena ("Reação de Mercado"): hiato de credibilidade $g_t = \max(0,\ r^n + \pi^e_t - selic_t)$;
depreciação $\Delta e_t = \eta g_t$; inflação $\pi_t = \pi^* + a(\pi_{t-1}-\pi^*) + b\,\Delta e_t$;
expectativas adaptativas $\pi^e_t = \pi_{t-1}$; $\theta_t = \theta^{base} + (\pi_t - \pi^*)$.
No "Mundo Mecânico", `γ = η = 0` (sem reação de preços e taxas).
Repasse: parcela Selic imediata; não-Selic reprecifica pela rolagem λ = 26,8%/ano com convenção de meio de ano
(sensibilidade ≈ 0,49 p.p. do PIB por p.p. de Selic em 12 meses; BCB: 0,48). Selic pode ser trajetória anual
(preset da proposta: 7,5% em 2027–2030, 5,5% a partir de 2031).

**Notação reservada:** γ = sensibilidade do prêmio (Bloco 1); k = reação da regra de Taylor (Bloco 2);
κ = inclinação da curva de Phillips (Bloco 3). Não reutilizar.

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

## Identidade visual e autoria

- Autor: **Raimundo Casé - economista** (economistacase@gmail.com), assinatura no rodapé no mesmo formato do
  Boletim Macroeconômico Semanal e do Painel IPCA (título · referência / Elaborado por / Fontes primárias / isenção).
- Paleta alinhada às páginas irmãs (Chakra): marinho `#1a365d` (títulos, cabeçalhos de tabela), azul `#2b6cb0`
  (destaque, botões, série 1), cinzas `#4a5568`/`#718096`/`#e2e8f0`, laranja `#dd6b20` (série 2), alerta `#c53030`.
  Tipografia Source Sans 3; só modo claro; títulos com filete inferior; índice lateral em telas largas;
  botão "Imprimir / Salvar PDF" com folha de impressão.

## Idioma e convenções

- Todo código, comentários, testes e interface em **português (pt-BR)**.
- Front-end estático: HTML/CSS/JS puro, Plotly.js e KaTeX via CDN, sem Node.js/frameworks.
- Fluxo: `python build.py` → gera `docs/data/cenarios_teoricos.json` e roda `pytest`;
  `python build.py --dados` baixa antes os dados do BCB (requer internet).
- Nenhum número de dado real é digitado no HTML/JS: tudo vem de `painel.json`.
- Servidor local: `python servidor.py` (sem cache). Não usar `python -m http.server`: o navegador guarda JS/CSS antigos
  e mistura com o HTML novo, quebrando os blocos (aconteceu na rodada de 21/11/2026).
- `build.py` carimba `?v=<hash>` em todo CSS/JS do index.html (src/publicacao.py) e roda `tools/verificar_pagina.py`
  (Chrome headless: gráficos, erros de JS, presets, abas, link compartilhável). Só publicar com "TUDO OK".
- Não usar `requestAnimationFrame` para re-renderizar após controles: o navegador o suspende; renderizar direto.
- `tests/test_pagina.py` exige que todo `$("id")` do JS exista no index.html. Ao renomear um id, mude HTML e JS juntos.
