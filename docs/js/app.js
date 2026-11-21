/*
 * Interface do Laboratório. Cálculos: docs/js/modelo.js (tempo real) e
 * docs/data/cenarios_teoricos.json (gerado por src/teoria/regimes_tfnp.py).
 */
(function () {
  "use strict";

  const M = window.Modelo;
  const $ = (id) => document.getElementById(id);
  const nf = (casas) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  const pct = (fracao, casas = 1) => nf(casas).format(fracao * 100) + "%";
  const num = (v, casas = 2) => nf(casas).format(v);
  const sinal = (v, casas = 2) => (v > 0 ? "+" : v < 0 ? "−" : "") + nf(casas).format(Math.abs(v));
  const cor = (nome) => getComputedStyle(document.documentElement).getPropertyValue("--" + nome).trim();

  const CONFIG = { displayModeBar: false, responsive: true, locale: "pt-BR" };

  function layoutBase(extra = {}) {
    const tinta2 = cor("tinta-2"), grade = cor("grade"), linha = cor("linha");
    const base = {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Inter, system-ui, sans-serif", size: 12, color: tinta2 },
      margin: { l: 48, r: 16, t: 12, b: 36 },
      hovermode: "x unified",
      hoverlabel: { bgcolor: cor("superficie"), bordercolor: linha, font: { color: cor("tinta"), size: 12 } },
      showlegend: false,
      separators: ",.",
      xaxis: { gridcolor: grade, zeroline: false, linecolor: linha, tickfont: { color: tinta2 }, fixedrange: true },
      yaxis: { gridcolor: grade, zerolinecolor: cor("tinta-3"), zerolinewidth: 1, linecolor: linha, tickfont: { color: tinta2 }, fixedrange: true },
    };
    for (const k of Object.keys(extra)) {
      base[k] = typeof extra[k] === "object" && !Array.isArray(extra[k]) && base[k] ? Object.assign({}, base[k], extra[k]) : extra[k];
    }
    return base;
  }

  function linha(x, y, nome, corLinha, opcoes = {}) {
    return Object.assign({
      x, y, name: nome, type: "scatter", mode: "lines",
      line: { color: corLinha, width: 2.5, shape: "linear" },
      hovertemplate: "%{y:.2f}<extra>" + nome + "</extra>",
    }, opcoes);
  }

  const texNum = (v, casas) => num(v, casas).replace(",", "{,}");
  const plotar = (id, traces, layout) => window.Plotly && Plotly.react($(id), traces, layout, CONFIG);

  // ================================================================= BLOCO 1 — dívida
  const sl = {
    selic: $("sl-selic"), theta: $("sl-theta"), pb: $("sl-pb"), phi: $("sl-phi"), gamma: $("sl-gamma"),
  };
  const btReacao = $("bt-reacao");
  // preset: null | "status" | "proposta". Na proposta, a Selic segue a trajetória anual de Lara Resende (2026).
  const estado = { reacao: false, preset: "status" };
  const BASE = M.PARAMETROS_BASE;

  function parametrosDivida() {
    const selic = estado.preset === "proposta" ? M.TRAJETORIA_PROPOSTA.slice() : +sl.selic.value / 100;
    return {
      selic, theta: +sl.theta.value / 100, pb: +sl.pb.value / 100,
      phi: +sl.phi.value / 100, gamma: +sl.gamma.value, reacao: estado.reacao,
    };
  }

  function marcarPreset() {
    document.querySelectorAll("[data-preset]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.preset === estado.preset)));
  }

  function aplicarPreset(nome) {
    estado.preset = nome;
    sl.theta.value = BASE.theta * 100;
    sl.phi.value = BASE.phi * 100;
    if (nome === "status") {
      sl.selic.value = BASE.selic0 * 100;
      sl.pb.value = BASE.pb * 100;
    } else {
      sl.selic.value = M.TRAJETORIA_PROPOSTA[0] * 100;
      sl.pb.value = 0;
    }
    marcarPreset();
    renderBloco1();
  }

  function renderDivida() {
    const p = parametrosDivida();
    const trajetoria = Array.isArray(p.selic);
    $("out-selic").textContent = trajetoria
      ? pct(M.TRAJETORIA_PROPOSTA[0], 1) + " → " + pct(M.TRAJETORIA_PROPOSTA[M.HORIZONTE - 1], 1)
      : pct(p.selic, 2);
    $("out-theta").textContent = pct(p.theta, 2);
    $("out-pb").textContent = pct(p.pb, 1);
    $("out-phi").textContent = pct(p.phi, 1);
    $("out-gamma").textContent = num(p.gamma, 2);

    const mec = M.simularDivida(Object.assign({}, p, { reacao: false }));
    const sim = p.reacao ? M.simularDivida(p) : mec;
    const statusQuo = M.simularDivida(Object.assign({}, p, { selic: BASE.selic0, reacao: false }));
    const H = M.HORIZONTE;
    const y = (s) => s.divida.map((v) => v * 100);

    // cards
    const d10 = sim.divida[H];
    $("c-d10").textContent = pct(d10, 1);
    $("c-d10-sub").textContent = sinal((d10 - sim.divida[0]) * 100, 1) + " p.p. desde 2026";
    const pb0 = M.primarioEstabilizador(BASE.d0, BASE.custo0, p.theta);
    $("c-pb0").textContent = pct(pb0, 1);
    $("c-pb0-sub").textContent = "juro implícito de 13% e PIB nominal de " + pct(p.theta, 1) + "; primário atual: " + pct(p.pb, 1);
    $("c-pb10").textContent = pct(sim.pb_estabilizador, 1);
    $("c-pb10-sub").textContent = "custo de " + pct(sim.custo[H], 1) + " e PIB nominal de " + pct(sim.theta[H], 1);
    const cardPi = document.querySelector(".card--reacao");
    cardPi.hidden = !p.reacao;
    $("c-pi10").textContent = pct(sim.inflacao[H], 1);
    $("c-pi10-sub").textContent = "prêmio de " + sinal(sim.premio[H] * 100, 1) + " p.p.; câmbio " + sinal(sim.cambio[H] * 100, 0) + "% no acumulado";

    // trajetória
    const traces = [];
    const rotSQ = "Selic mantida em " + pct(BASE.selic0, 1) + " (demais parâmetros iguais)";
    if (trajetoria || Math.abs(p.selic - BASE.selic0) > 1e-9) {
      traces.push(linha(sim.ano, y(statusQuo), rotSQ, cor("ref"), { line: { color: cor("ref"), width: 1.5, dash: "dash" } }));
    }
    let aritmetica = null;
    if (trajetoria) {
      aritmetica = M.trajetoriaCustoCaminho(BASE.d0, M.TRAJETORIA_PROPOSTA, p.theta, p.pb);
      traces.push(linha(sim.ano, aritmetica.map((v) => v * 100), "Aritmética da proposta (custo imposto)", cor("s4"),
        { line: { color: cor("s4"), width: 2, dash: "dash" } }));
    }
    traces.push(linha(sim.ano, y(mec), "Mundo mecânico", cor("s1"), p.reacao ? { line: { color: cor("s1"), width: 2, dash: "dot" } } : {}));
    if (p.reacao) traces.push(linha(sim.ano, y(sim), "Com reação de mercado", cor("s2")));
    // rótulos diretos no fim das linhas
    const anotacoes = traces.map((t) => ({
      x: t.x[H], y: t.y[H], text: "<b>" + num(t.y[H], 0) + "%</b>", showarrow: false,
      xanchor: "left", xshift: 6, font: { color: cor("tinta"), size: 12 },
    }));
    plotar("g-divida", traces, layoutBase({
      margin: { l: 48, r: 48, t: 12, b: 36 },
      showlegend: true, legend: { orientation: "h", y: 1.1, x: 0, font: { size: 12 }, entrywidthmode: "pixels", entrywidth: 240 },
      yaxis: { ticksuffix: "%" }, xaxis: { dtick: 2, range: [2025.8, 2036.2] }, annotations: anotacoes,
      shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: sim.divida[0] * 100, y1: sim.divida[0] * 100,
        line: { color: cor("tinta-3"), width: 1, dash: "dot" } }],
    }));

    const leituraD = $("leitura-divida");
    if (trajetoria) {
      leituraD.textContent = "Mesma trajetória de juros, dois resultados. Na aritmética da proposta, o custo médio cai para 7,5% já em 2027 e a dívida chega a " +
        pct(aritmetica[H], 1) + " do PIB em 2036. No simulador, só a parcela atrelada à Selic (" + pct(p.phi, 1) + ") acompanha o corte de imediato; " +
        "o resto reprecifica na rolagem, e o custo médio de 2027 fica em " + pct(mec.custo[1], 1) + ". Resultado: " + pct(mec.divida[H], 1) +
        " em 2036" + (p.reacao ? ", e " + pct(sim.divida[H], 1) + " com reação de mercado." : ". Ative a reação de mercado para ver o efeito do prêmio de risco.");
    } else {
      leituraD.textContent = "";
    }

    // varredura em Selic constante
    const vMec = M.varrerSelic(Object.assign({}, p, { reacao: false }));
    const vRea = M.varrerSelic(Object.assign({}, p, { reacao: true }));
    const xs = vMec.selics.map((s) => s * 100);
    const neutro = (BASE.r_neutro + BASE.pi0) * 100;
    const atual = p.reacao ? vRea : vMec;
    const iAtual = trajetoria ? -1 : atual.selics.findIndex((s) => Math.abs(s - p.selic) < 1e-6);
    const tracesV = [
      linha(xs, vMec.finais.map((v) => v * 100), "Mundo mecânico", cor("s1"), { hovertemplate: "%{y:.1f}%<extra>Mecânico</extra>" }),
      linha(xs, vRea.finais.map((v) => v * 100), "Com reação (γ = " + num(p.gamma, 2) + ")", cor("s2"), { hovertemplate: "%{y:.1f}%<extra>Com reação</extra>" }),
    ];
    if (iAtual >= 0) {
      tracesV.push({ x: [xs[iAtual]], y: [atual.finais[iAtual] * 100], type: "scatter", mode: "markers", name: "Sua escolha",
        marker: { size: 11, color: p.reacao ? cor("s2") : cor("s1"), line: { color: cor("superficie"), width: 2 } }, hoverinfo: "skip", showlegend: false });
    }
    plotar("g-varredura", tracesV, layoutBase({
      showlegend: true, legend: { orientation: "h", y: 1.14, x: 0, entrywidthmode: "pixels", entrywidth: 200 },
      xaxis: { title: { text: "Selic constante 2027–2036", font: { size: 11 } }, ticksuffix: "%", dtick: 2 },
      yaxis: { ticksuffix: "%" }, hovermode: "x unified", margin: { l: 48, r: 16, t: 24, b: 48 },
      shapes: [{ type: "line", x0: neutro, x1: neutro, yref: "paper", y0: 0, y1: 1, line: { color: cor("tinta-3"), width: 1, dash: "dot" } }],
      annotations: [{ x: neutro, yref: "paper", y: 0.02, text: "neutro nominal " + num(neutro, 1) + "%", showarrow: false,
        xanchor: "left", xshift: 4, yanchor: "bottom", font: { size: 11, color: cor("tinta-2") } }],
    }));

    const leitura = $("leitura-varredura");
    if (!p.reacao) {
      leitura.textContent = "No mundo mecânico, cada corte reduz a dívida: a linha azul só desce. É a aritmética da proposta. " +
        "Ative a reação de mercado para ver o que muda abaixo do juro neutro nominal.";
    } else if (vRea.selicMin > 0.021) {
      leitura.textContent = "Com γ = " + num(p.gamma, 2) + ", a dívida de 2036 é mínima com a Selic em " + pct(vRea.selicMin, 2) +
        " (" + pct(vRea.dividaMin, 1) + " do PIB). Abaixo disso, o prêmio de risco e o câmbio passam a pesar mais do que o alívio dos juros: o corte forçado eleva a dívida.";
    } else {
      leitura.textContent = "Com γ = " + num(p.gamma, 2) + ", o corte ainda reduz a dívida em toda a faixa, mas menos que no mundo mecânico, e às custas da inflação: " +
        pct(M.simularDivida(Object.assign({}, p, { selic: 0.05 })).inflacao[H], 1) + " em 2036 com Selic de 5%. Aumente γ acima de 1 para ver o corte se inverter.";
    }

    // sensibilidade do simulador (camada técnica)
    const sens = $("sens-simulador");
    if (sens) sens.textContent = num(M.sensibilidadeSelic({ phi: p.phi, theta: p.theta, pb: p.pb }), 2);
  }

  function renderBloco1() { renderDivida(); }   // renderização direta: rAF é suspenso pelo navegador em várias situações
  Object.entries(sl).forEach(([nome, el]) => el.addEventListener("input", () => {
    // mover a Selic sai do preset da proposta (a trajetória vira Selic constante)
    if (nome === "selic" && estado.preset === "proposta") estado.preset = null;
    else if (nome !== "gamma" && estado.preset === "status") estado.preset = null;
    marcarPreset();
    renderBloco1();
  }));
  btReacao.addEventListener("click", () => {
    estado.reacao = !estado.reacao;
    btReacao.setAttribute("aria-checked", String(estado.reacao));
    $("ctl-gamma").hidden = !estado.reacao;
    renderBloco1();
  });
  document.querySelectorAll("[data-preset]").forEach((b) => b.addEventListener("click", () => aplicarPreset(b.dataset.preset)));

  // ================================================================= BLOCO 2 — Fisher-Taylor
  const R_NEUTRO = 5, PI_INICIAL = 3;

  function renderTaylor() {
    const k = +$("sl-k").value, dz = +$("sl-dz").value;
    $("out-k").textContent = num(k, 2);
    $("out-dz").textContent = sinal(dz, 2) + " p.p.";
    const indeterminado = Math.abs(1 - k) < 1e-9;
    const traj = M.trajetoriaFisherTaylor(k, dz, R_NEUTRO, PI_INICIAL);

    // equação com números
    const eq = $("eq-taylor");
    const tex = indeterminado
      ? String.raw`\pi = \frac{z-r}{1-k}\;\Rightarrow\; k = 1:\ \text{sem equilíbrio único}`
      : String.raw`\pi = \frac{z-r}{1-k} = \frac{${texNum(traj.z1, 2)} - ${R_NEUTRO}}{1 - ${texNum(k, 2)}} = ${texNum(traj.piNovo, 2)}\%`;
    if (window.katex) katex.render(tex, eq, { throwOnError: false, displayMode: true });
    else eq.textContent = tex;

    const v = $("veredito-taylor");
    if (indeterminado) {
      v.dataset.regime = "indeterminado";
      v.innerHTML = "<strong>Fronteira: k = 1</strong>O juro acompanha a inflação um para um; a regra não pina a inflação.";
    } else if (k > 1) {
      v.dataset.regime = "taylor";
      v.innerHTML = "<strong>Princípio de Taylor (k &gt; 1)</strong>Um aperto de " + sinal(dz, 2) + " p.p. leva a inflação de " +
        num(PI_INICIAL, 1) + "% para " + num(traj.piNovo, 2) + "%.";
    } else {
      v.dataset.regime = "neofisher";
      v.innerHTML = "<strong>Regime neofisheriano (k &lt; 1)</strong>O mesmo aperto de " + sinal(dz, 2) + " p.p. leva a inflação de " +
        num(PI_INICIAL, 1) + "% para " + num(traj.piNovo, 2) + "%.";
    }

    // efeito de longo prazo Δπ(k)
    const ksT = [], ysT = [], ksN = [], ysN = [];
    for (let i = 20; i <= 250; i++) {
      const kk = i / 100;
      if (Math.abs(1 - kk) < 0.04) continue;
      const efeito = dz / (1 - kk);
      (kk > 1 ? ksT : ksN).push(kk);
      (kk > 1 ? ysT : ysN).push(efeito);
    }
    const lim = Math.max(4, Math.abs(dz) * 8);
    const tr = [
      linha(ksN, ysN, "k < 1 (neofisheriano)", cor("s2"), { hovertemplate: "k = %{x:.2f}: %{y:+.2f} p.p.<extra></extra>" }),
      linha(ksT, ysT, "k > 1 (Taylor)", cor("s1"), { hovertemplate: "k = %{x:.2f}: %{y:+.2f} p.p.<extra></extra>" }),
    ];
    if (!indeterminado) {
      tr.push({ x: [k], y: [dz / (1 - k)], type: "scatter", mode: "markers", hoverinfo: "skip",
        marker: { size: 12, color: k > 1 ? cor("s1") : cor("s2"), line: { color: cor("superficie"), width: 2 } } });
    }
    plotar("g-taylor", tr, layoutBase({
      hovermode: "closest",
      xaxis: { title: { text: "k (reação do juro à inflação)", font: { size: 11 } }, range: [0.2, 2.5] },
      yaxis: { range: [-lim, lim], title: { text: "Δπ, p.p.", font: { size: 11 } } },
      margin: { l: 52, r: 16, t: 12, b: 48 },
      shapes: [{ type: "line", x0: 1, x1: 1, yref: "paper", y0: 0, y1: 1, line: { color: cor("tinta-3"), width: 1, dash: "dot" } }],
      annotations: [
        { x: 0.6, xref: "x", yref: "paper", y: 0.98, text: "neofisheriano", showarrow: false, font: { size: 11, color: cor("tinta-2") } },
        { x: 1.75, xref: "x", yref: "paper", y: 0.98, text: "princípio de Taylor", showarrow: false, font: { size: 11, color: cor("tinta-2") } },
      ],
    }));

    // trajetórias
    const t = traj.racional.map((_, i) => i);
    const LIM = 25;
    let divergiu = false;
    const adapt = traj.adaptativa.map((val) => {
      if (divergiu || Math.abs(val) > LIM) { divergiu = true; return null; }
      return val;
    });
    const trT = [
      linha(t, adapt, "Aprendizado adaptativo", cor("s4"), { mode: "lines+markers", marker: { size: 6 } }),
    ];
    if (!indeterminado) trT.unshift(linha(t, traj.racional, "Expectativas racionais", cor("s3"), { line: { color: cor("s3"), width: 2.5, shape: "hv" } }));
    plotar("g-taylor-traj", trT, layoutBase({
      showlegend: true, legend: { orientation: "h", y: 1.14, x: 0, entrywidthmode: "pixels", entrywidth: 200 },
      xaxis: { title: { text: "períodos após o aperto", font: { size: 11 } }, dtick: 2 },
      yaxis: { ticksuffix: "%" }, margin: { l: 48, r: 16, t: 24, b: 48 },
    }));

    const leit = $("leitura-taylor");
    if (indeterminado) leit.textContent = "Em k = 1 não há equilíbrio único: a inflação fica à deriva.";
    else if (k > 1) leit.textContent = "Com k > 1, os dois mundos concordam: com expectativas racionais a inflação salta para o novo equilíbrio, e com aprendizado ela converge para o mesmo ponto.";
    else leit.textContent = "Com k < 1, as expectativas racionais saltam para o equilíbrio neofisheriano, mas com aprendizado adaptativo a inflação se afasta dele" +
      (divergiu ? " e diverge (a linha sai do gráfico)." : ".") + " É o argumento de García-Schmidt e Woodford: o resultado depende do critério de seleção de equilíbrio.";
  }
  ["sl-k", "sl-dz"].forEach((id) => $(id).addEventListener("input", renderTaylor));

  // ================================================================= BLOCO 3 — regimes
  const PAINEIS = [
    ["inflacao", "Inflação", "desvio, p.p. a.a."],
    ["juro_nominal", "Juro nominal (Selic)", "desvio, p.p. a.a."],
    ["juro_real", "Juro real", "desvio, p.p. a.a."],
    ["cambio", "Câmbio nominal", "desvio %, alta = depreciação"],
    ["divida_pib", "Dívida/PIB", "desvio, pontos do PIB"],
    ["hiato", "Hiato do produto", "desvio, %"],
  ];
  // cor fixa por entidade (regime/composição), nunca por posição
  const COR_LINHA = { dm: "s1", dm_anunciado: "s1", df_lft: "s2", df_anunciado: "s2", df_pre: "s3", df_lastro: "s4" };
  let dados = null;
  let cenarioAtual = "dominancia_monetaria";

  function estiloLinha(l) {
    if (l.papel === "referencia") return { color: cor("ref"), width: 1.5, dash: "dash" };
    return { color: cor(COR_LINHA[l.id] || "s1"), width: 2.5 };
  }

  function montarMultiplos() {
    const cont = $("g-regimes");
    cont.innerHTML = "";
    for (const [chave, titulo, unidade] of PAINEIS) {
      const fig = document.createElement("figure");
      fig.className = "grafico";
      fig.innerHTML = '<figcaption><strong>' + titulo + '</strong> · ' + unidade + '</figcaption><div class="plot" id="g-r-' + chave + '" role="img" aria-label="' + titulo + '"></div>';
      cont.appendChild(fig);
    }
  }

  function renderRegimes() {
    if (!dados) return;
    const cen = dados.cenarios[cenarioAtual];
    $("desc-cenario").textContent = cen.descricao;
    const leg = $("legenda-regimes");
    leg.innerHTML = cen.linhas.map((l) => {
      const e = estiloLinha(l);
      return '<li><i class="' + (e.dash ? "tracejada" : "") + '" style="border-color:' + e.color + '"></i>' + l.rotulo + "</li>";
    }).join("");

    const t = dados.trimestres;
    for (const [chave] of PAINEIS) {
      const traces = cen.linhas.slice().reverse().map((l) =>
        linha(t, l.series[chave], l.rotulo, null, { line: estiloLinha(l), hovertemplate: "%{y:.2f}<extra>" + l.rotulo + "</extra>" }));
      const shapes = [];
      const annotations = [];
      if (cen.marcador != null) {
        shapes.push({ type: "line", x0: cen.marcador, x1: cen.marcador, yref: "paper", y0: 0, y1: 1, line: { color: cor("tinta-3"), width: 1, dash: "dot" } });
        annotations.push({ x: cen.marcador, yref: "paper", y: 1, text: "corte", showarrow: false, xanchor: "left", xshift: 3, yanchor: "top", font: { size: 10, color: cor("tinta-2") } });
      }
      plotar("g-r-" + chave, traces, layoutBase({
        margin: { l: 40, r: 8, t: 6, b: 30 },
        xaxis: { dtick: 4, title: { text: "trimestres", font: { size: 10 } } },
        shapes, annotations,
      }));
    }

    // leitura calculada a partir do JSON
    const partes = cen.linhas.filter((l) => l.papel !== "referencia").map((l) =>
      l.rotulo + ": inflação " + sinal(l.series.inflacao[0]) + " p.p. no impacto, câmbio " + sinal(l.series.cambio[dados.trimestres.length - 1], 1) + "% em 5 anos");
    $("leitura-regimes").textContent = "Corte de 100 pontos-base no juro. " + partes.join("; ") + ".";
  }

  document.querySelectorAll("#abas-regimes button").forEach((b) => {
    b.addEventListener("click", () => {
      cenarioAtual = b.dataset.cenario;
      document.querySelectorAll("#abas-regimes button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
      renderRegimes();
    });
  });

  async function carregarCenarios() {
    try {
      const resp = await fetch("data/cenarios_teoricos.json", { cache: "no-cache" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      dados = await resp.json();
      montarMultiplos();
      renderRegimes();
      const desvio = M.conferirReferencia(dados.divida.casos_referencia);
      $("conferencia").textContent = (desvio < 1e-9 ? "✓ " : "⚠ ") + "Motor JavaScript conferido contra o Python em " +
        dados.divida.casos_referencia.length + " casos de referência: desvio máximo de " + desvio.toExponential(1) +
        " (cenários gerados em " + dados.meta.gerado_em + ").";
      if (desvio >= 1e-9) console.warn("Motor JS divergente do Python:", desvio);
    } catch (e) {
      const el = $("erro-json");
      el.hidden = false;
      el.textContent = "Não foi possível carregar os cenários (" + e.message + "). Abra a página por um servidor: python -m http.server 8000 -d docs";
    }
  }

  // ================================================================= captação
  const form = $("form-cadastro");
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const status = $("form-status");
    const nome = $("f-nome").value.trim(), email = $("f-email").value.trim();
    if (form.website.value) return;                                         // honeypot
    if (!nome || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      status.dataset.tipo = "erro"; status.textContent = "Preencha nome e um e-mail válido."; return;
    }
    const endpoint = form.dataset.endpoint;
    if (!endpoint) {
      status.dataset.tipo = "erro";
      status.textContent = "O cadastro será ativado em breve. Volte para conferir.";
      return;
    }
    const corpo = new FormData();
    corpo.append(form.dataset.campoNome || "nome", nome);
    corpo.append(form.dataset.campoEmail || "email", email);
    try {
      await fetch(endpoint, { method: "POST", body: corpo, mode: "no-cors" });
      status.dataset.tipo = "ok"; status.textContent = "Pronto! Confirme a inscrição no seu e-mail.";
      form.reset();
    } catch (e) {
      status.dataset.tipo = "erro"; status.textContent = "Não foi possível enviar agora. Tente de novo.";
    }
  });

  // ================================================================= inicialização
  function renderTudo() { renderDivida(); renderTaylor(); renderRegimes(); }

  function iniciar() {
    if (window.renderMathInElement) {
      renderMathInElement(document.body, {
        delimiters: [{ left: "$$", right: "$$", display: true }, { left: "\\(", right: "\\)", display: false }],
        ignoredClasses: ["equacao"], throwOnError: false,
      });
    }
    lerCenarioDaURL();
    renderDivida();
    renderTaylor();
    carregarCenarios();
  }

  // ================================================================= link compartilhável do Bloco 1
  // ?cen=proposta|status&selic=7.5&theta=7&pb=0&phi=56.9&reacao=1&gamma=1.5#divida
  function lerCenarioDaURL() {
    const q = new URLSearchParams(location.search);
    if (![...q.keys()].length) return;
    if (q.get("cen") === "proposta") aplicarPreset("proposta");
    const fixar = (nome, el) => { if (q.has(nome) && isFinite(+q.get(nome))) el.value = +q.get(nome); };
    fixar("theta", sl.theta); fixar("pb", sl.pb); fixar("phi", sl.phi); fixar("gamma", sl.gamma);
    if (q.has("selic")) { fixar("selic", sl.selic); estado.preset = null; }
    else if (q.get("cen") !== "proposta" && (q.has("theta") || q.has("pb") || q.has("phi"))) estado.preset = null;
    if (q.get("reacao") === "1") {
      estado.reacao = true;
      btReacao.setAttribute("aria-checked", "true");
      $("ctl-gamma").hidden = false;
    }
    marcarPreset();
  }

  $("bt-compartilhar").addEventListener("click", async () => {
    const q = new URLSearchParams();
    if (estado.preset === "proposta") q.set("cen", "proposta"); else q.set("selic", sl.selic.value);
    q.set("theta", sl.theta.value); q.set("pb", sl.pb.value); q.set("phi", sl.phi.value);
    if (estado.reacao) { q.set("reacao", "1"); q.set("gamma", sl.gamma.value); }
    const url = location.origin + location.pathname + "?" + q.toString() + "#divida";
    const st = $("status-compartilhar");
    try { await navigator.clipboard.writeText(url); st.textContent = "Link copiado. Quem abrir verá este mesmo cenário."; }
    catch (e) { st.textContent = url; }
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
