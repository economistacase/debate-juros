# Painel Juros — O Debate dos Juros no Brasil

*Raimundo Casé - economista*

**Página:** https://economistacase.github.io/debate-juros/

Em setembro de 2026, André Lara Resende propôs derrubar a Selic de forma anunciada, com o argumento de que
os juros são o “único motor” da dívida pública. A aritmética da proposta está certa *dados* os juros. Mas,
como reconhece o próprio dossiê de referência do debate, *nenhuma identidade contábil resolve essa pergunta:
ela depende de um modelo de como os agentes reagem*.

Este repositório é a camada **interativa, reproduzível e viva** do debate: em vez de mais um PDF expositivo,
um laboratório aberto onde o leitor liga e desliga a reação dos agentes e vê, em tempo real, o que muda.

## A página em cinco partes

A pergunta organizadora é permanente: **por que o juro brasileiro é tão alto, e o que aconteceria se caísse?**
A proposta de André Lara Resende (2026) entra como gancho e estudo de caso, não como eixo.

1. **Os dados.** Placar com 8 indicadores, a conta da dívida com os números do mês e seis gráficos históricos
   desde 2002, com seletor de período e marcos. Um botão leva os números atuais ao laboratório.
2. **As lentes.** Seis explicações, do consenso à heterodoxia, cada uma com diagnóstico, mecanismo, proposta,
   referências e status da evidência no Brasil (forte, mista ou em aberto):
   (1) novo-keynesiana e regime de metas; (2) fiscal e prêmio de risco; (3) institucional e microestrutural;
   (4) teoria fiscal e neofisheriana; (5) pós-keynesiana e novo-desenvolvimentista; (6) finanças funcionais e MMT,
   mais a lente transversal da inércia e indexação.
3. **O laboratório.** Os três blocos teóricos abaixo, cada um marcado com as lentes que representa.
4. **O mapa do debate.** Sete afirmações × seis lentes (concorda, em parte, discorda, não central) e como arbitrar.
5. **O episódio de 2026.** A proposta de Lara Resende, as críticas e o que o laboratório mostra.

Próximas etapas: experimentos para as lentes 3, 5 e 6 (potência da Selic, canal de renda dos juros) e a Onda 2,
que estima com dados brasileiros os parâmetros que discriminam as lentes.

Dados: BCB/SGS (4189, 432, 13522, 13762, 4513, 5793, 5760, 4382, 3696), Focus e Nota de Estatísticas
Fiscais. Atualização automática semanal (`.github/workflows/atualiza-dados.yml`); para atualizar à mão,
`python build.py --dados`.

## Proposta em duas ondas

| Onda | Pergunta | Entrega | Status |
|---|---|---|---|
| **1. Laboratório Teórico** | *Por que* os modelos divergem? | Página interativa com três blocos de teoria e mapa do debate | ✅ publicada |
| **2. Laboratório Empírico** | *Qual* deles os dados brasileiros confirmam? | SVAR e estudo de eventos do Copom com SGS/BCB, Focus e curva de juros; painel com atualização mensal via GitHub Actions | 🔜 |

A página é organizada em camadas: **(1)** interação imediata (sliders e cards, para qualquer leitor);
**(2)** narrativa econômica (o texto de cada bloco); **(3)** caixa-preta aberta (seções “camada técnica”,
este código e os testes).

## Recursos da página

- Retrato factual (Nota de Estatísticas Fiscais) e placar com dados do SGS/Focus atualizados toda semana.
- Presets do simulador: **Status quo (BCB set/2026)** e **Proposta Lara Resende (2026)**.
- **Link compartilhável** do cenário do Bloco 1 (`?cen=proposta&reacao=1&gamma=1.5#divida`).
- **Download das séries em CSV**, **Imprimir / Salvar PDF** e índice lateral com a seção ativa.
- Identidade visual comum ao Boletim Macroeconômico Semanal e ao Painel IPCA.

## Fundamentação dos blocos interativos

### Bloco 1: Laboratório da dívida
Identidade da dinâmica da dívida bruta/PIB:

$$\Delta d_t = \frac{r_t - \theta_t}{1 + \theta_t}\, d_{t-1} - pb_t, \qquad pb^* = \frac{r-\theta}{1+\theta}\, d$$

- **Mundo mecânico:** só a Selic e a reprecificação gradual do estoque não-Selic mudam o custo implícito.
- **Reação de mercado:** com a Selic abaixo do juro neutro nominal ($r^n + \pi^e$), abre-se um hiato de
  credibilidade $g_t$ que eleva o prêmio na rolagem ($\gamma g_t$, sobre os 26,8% que vencem em 12 meses),
  deprecia o câmbio e realimenta a inflação. A inflação maior corrói o estoque, mas encarece a parcela em
  IPCA, e a depreciação reavalia a parcela cambial.
- **Resultado-chave:** abaixo do neutro nominal, o corte ainda reduz a dívida se $\gamma < 1$ e passa a
  **elevá-la** se $\gamma > 1$. O valor de $\gamma$ é uma pergunta empírica: é a ponte para a Onda 2.

Calibração-base: BCB, Nota de Estatísticas Fiscais (set/2026). O motor reproduz a conta do dossiê de
referência (custo de 12,7%, PIB nominal de 7%, primário zero ⇒ ~138% do PIB em 2036), o $pb^*$ de 4,7% do PIB e a
elasticidade de ~0,48 p.p. do PIB por ponto de Selic.

### Bloco 2: O interruptor de Taylor (Loyo, 2017)
Fisher ($i = r + \pi^e$) + regra ($i = k\pi + z$) ⇒ $\pi = \dfrac{z-r}{1-k}$.
Com $k > 1$, um aperto reduz a inflação; com $k < 1$, eleva (neofisheriano). O bloco mostra também a
dinâmica com **aprendizado adaptativo**, $\pi_t = (\pi_{t-1} + r - z)/k$: o equilíbrio neofisheriano é
instável sob aprendizado (García-Schmidt e Woodford, 2019).

### Bloco 3: Regimes monetário × fiscal (TFNP)
Modelo Novo Keynesiano trimestral com dívida de maturidade geométrica (Cochrane) e restrição de lastro:

$$\frac{B_{t-1}}{P_t} = E_t \sum_{j=0}^{\infty}\beta^j s_{t+j}$$

| Cenário | Regra monetária | Regra fiscal | O que mostra |
|---|---|---|---|
| Dominância monetária | $\phi_\pi = 1{,}5$ | $s_t = 0{,}05\,v_{t-1}$ | Corte eleva a inflação (livro-texto) |
| Dominância fiscal, LFT ($\omega=0$) | $\phi_\pi = 0{,}8$ | $s_t$ exógeno | Corte *reduz* a inflação (neofisheriano, base da proposta) |
| Dominância fiscal, prefixada ($\omega=0{,}95$) | idem | idem | A composição da dívida muda o sinal de curto prazo (o ponto de F. Lopes) |
| LFT + perda de lastro | idem | superávit cai | A própria TFNP prevê inflação e depreciação |
| Antecipação | corte anunciado para t = 4 | ambos | Câmbio e inflação se movem **no anúncio** |

Resolvido pelo método de Klein (QZ ordenada) com checagem de Blanchard–Kahn; os resíduos de todas as
equações são inferiores a $10^{-10}$, e o caso de dominância monetária confere com a solução analítica (Galí, cap. 3).

## Regra de integridade

Nenhuma curva é desenhada à mão. Tudo o que a página mostra é **(a)** calculado em tempo real por
`docs/js/modelo.js`, espelho exato de `src/teoria/dinamica_divida.py`, ou **(b)** lido de
`docs/data/cenarios_teoricos.json`, gerado e testado em Python. Ao carregar, a página confere o motor JS
contra os casos de referência exportados pelo Python e exibe o desvio máximo na seção técnica do Bloco 1.

## Estrutura

```
.
├── build.py                    # gera o JSON teórico e roda os testes
├── CLAUDE.md                   # briefing persistente do projeto
├── requirements.txt
├── src/
│   ├── dados/
│   │   ├── bcb.py              # Parte 1: coleta SGS + Focus → docs/data/painel.json
│   │   └── nota_fiscal.json    # juro implícito e composição (manual, da Nota Fiscal)
│   ├── teoria/
│   │   ├── dinamica_divida.py  # Bloco 1: dívida mecânica × reação de mercado
│   │   └── regimes_tfnp.py     # Bloco 3: NK + TFNP, solver de Klein, exportação do JSON
│   └── empirico/               # Onda 2 (reservado)
├── tests/                      # 42 testes: teoria + integridade dos dados
├── docs/                       # GitHub Pages
│   ├── index.html
│   ├── css/style.css
│   ├── js/modelo.js            # motor em tempo real (espelho do Python)
│   ├── js/app.js               # laboratório: interface, gráficos (Plotly) e equações (KaTeX)
│   ├── js/dados.js             # Parte 1: placar e séries históricas
│   └── data/                   # painel.json (dados reais) e cenarios_teoricos.json
└── .github/workflows/          # Onda 2: atualização mensal
```

## Como rodar localmente

```bash
pip install -r requirements.txt
python build.py                          # cenários + carimbo de versão + pytest + verificação no Chrome
python servidor.py                       # abra http://localhost:8000 (sem cache)
```

Só os testes: `python -m pytest -q`.

## Publicação no GitHub Pages

O site é servido a partir da pasta `/docs` da branch `main`:

```bash
gh api -X POST repos/economistacase/debate-juros/pages \
  -f "source[branch]=main" -f "source[path]=/docs"
```

Ou pela interface: *Settings → Pages → Build and deployment → Deploy from a branch → `main` / `/docs`*.

## Captação de e-mail

O formulário do Bloco 4 está pronto, mas desligado: com `data-endpoint` vazio, ele mostra um aviso e não envia
nada. Para ativar, preencha `data-endpoint` (e os nomes dos campos) em `docs/index.html`. As instruções para
Brevo, Kit e Substack estão no comentário acima do formulário.

## Referências

Lara Resende, A. (2026), “Eu acuso: uma proposta para eliminar os juros absurdos”. · Wilher, V. (2026),
*O debate dos juros*, Análise Macro. · Loyo, E. (2017), “Neofisherianismo: vai entender”. · Lopes, F. (2017),
“André, Cochrane e a teoria fiscal dos preços”. · Cochrane, J. (2023), *The Fiscal Theory of the Price Level*. ·
Sims, C. (1994). · Leeper, E. (1991). · Sargent, T. e Wallace, N. (1981). · Blanchard, O. (2004). ·
García-Schmidt, M. e Woodford, M. (2019), *AER*. · Galí, J. (2015), *Monetary Policy, Inflation, and the
Business Cycle*. · Klein, P. (2000), *JEDC*. · BCB, Notas de Estatísticas Fiscais.

---
Material didático; não é recomendação de investimento.
