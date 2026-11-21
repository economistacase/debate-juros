/*
 * Blocos 4 e 5 — potência da Selic (lente 3) e canal de renda dos juros (lentes 5 e 6).
 * Motor: espelho exato de src/teoria/transmissao.py, conferido contra docs/data/transmissao.json ao carregar.
 * Dados: fatia do crédito direcionado (painel.json, SGS 20593/20539) e saldo/composição da DBGG (nota_fiscal.json).
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------ motor (espelho do Python)
  const BASE = Object.freeze({ delta: 1.0, duracao: 2, sigma: 0.5, s: 0.437, omega: 0.5, kappa: 0.3,
    c: 0.0, tau: 0.15, phi: 0.569, d: 0.829 });
  const HORIZONTE = 6;

  function resposta(parcial, horizonte = HORIZONTE) {
    const p = Object.assign({}, BASE, parcial);
    const s = { ano: [], delta_i: [], delta_r: [], conv: [], renda: [], hiato: [], inflacao: [] };
    let piAnt = 0;
    for (let t = 1; t <= horizonte; t++) {
      const di = t <= p.duracao ? p.delta : 0;
      const dr = di - piAnt;
      const conv = -p.sigma * (1 - p.s) * dr;
      const renda = p.c * (1 - p.tau) * p.phi * p.d * di;
      const x = conv + renda;
      const pi = p.omega * piAnt + p.kappa * x;
      s.ano.push(t); s.delta_i.push(di); s.delta_r.push(dr); s.conv.push(conv); s.renda.push(renda);
      s.hiato.push(x); s.inflacao.push(pi);
      piAnt = pi;
    }
    return s;
  }
  const potencia = (p) => -resposta(Object.assign({}, p, { delta: 1 })).inflacao[1];
  const apertoNecessario = (p, alvo = 1) => { const pot = potencia(p); return pot > 1e-12 ? alvo / pot : null; };
  function efeitoImpacto(parcial) {
    const p = Object.assign({}, BASE, parcial);
    const conv = -p.sigma * (1 - p.s), renda = p.c * (1 - p.tau) * p.phi * p.d;
    return { convencional: conv, renda, liquido: conv + renda };
  }
  function limiarConsumo(parcial) {
    const p = Object.assign({}, BASE, parcial);
    return (p.sigma * (1 - p.s)) / ((1 - p.tau) * p.phi * p.d);
  }
  window.Transmissao = { BASE, resposta, potencia, apertoNecessario, efeitoImpacto, limiarConsumo };

  // ------------------------------------------------------------------ utilitários de interface
  const $ = (id) => document.getElementById(id);
  const nf = (c) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
  const num = (v, c = 2) => nf(c).format(v);
  const sinal = (v, c = 2) => (v > 0 ? "+" : v < 0 ? "−" : "") + nf(c).format(Math.abs(v));
  const cor = (n) => getComputedStyle(document.documentElement).getPropertyValue("--" + n).trim();
  const CONFIG = { displayModeBar: false, responsive: true };
  function layout(extra) {
    return Object.assign({
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", separators: ",.",
      font: { family: "Source Sans 3, Segoe UI, sans-serif", size: 12, color: cor("tinta-2") },
      margin: { l: 48, r: 16, t: 14, b: 40 }, showlegend: false, hovermode: "x unified",
      hoverlabel: { bgcolor: cor("superficie"), bordercolor: cor("linha"), font: { color: cor("tinta"), size: 12 } },
    }, extra);
  }
  const eixo = (extra) => Object.assign({ gridcolor: cor("grade"), zeroline: false, linecolor: cor("linha"), fixedrange: true }, extra);
  const plotar = (id, tr, lay) => window.Plotly && Plotly.react($(id), tr, lay, CONFIG);

  let historico = null;     // {x, y} da fatia direcionada
  let saldoDBGG = null;     // R$ milhões
  let fonteS = "";

  // ------------------------------------------------------------------ Bloco 4
  function par4() {
    return { s: +$("sl-s").value / 100, omega: +$("sl-omega").value, delta: +$("sl-delta4").value,
      duracao: +$("sl-dur4").value, sigma: +$("sl-sigma4").value };
  }

  function renderBloco4() {
    const p = par4();
    $("out-s").textContent = num(p.s * 100, 1) + "%";
    $("out-omega").textContent = num(p.omega, 2);
    $("out-delta4").textContent = num(p.delta, 2) + " p.p.";
    $("out-dur4").textContent = p.duracao + (p.duracao === 1 ? " ano" : " anos");
    $("out-sigma4").textContent = num(p.sigma, 2);

    const r = resposta(p), r0 = resposta(Object.assign({}, p, { s: 0 }));
    const pot = potencia(p), pot0 = potencia(Object.assign({}, p, { s: 0 }));
    const nec = apertoNecessario(p), nec0 = apertoNecessario(Object.assign({}, p, { s: 0 }));
    $("c4-rel").textContent = num(100 * pot / pot0, 0) + "%";
    $("c4-pi2").textContent = sinal(r.inflacao[1]) + " p.p.";
    $("c4-pi2-sub").textContent = "sem direcionado: " + sinal(r0.inflacao[1]) + " p.p.";
    $("c4-nec").textContent = nec == null ? "—" : num(nec, 1) + " p.p.";
    $("c4-nec-sub").textContent = nec == null ? "" : "sem direcionado: " + num(nec0, 1) + " p.p. (" + num(nec / nec0, 2) + "×)";
    $("c4-sac").textContent = num(r.hiato.reduce((a, b) => a + b, 0), 2);

    const anos = r.ano.map((t) => "ano " + t);
    plotar("g-potencia", [
      { x: anos, y: r0.inflacao, type: "scatter", mode: "lines+markers", name: "Sem crédito direcionado",
        line: { color: cor("ref"), width: 2, dash: "dash" }, marker: { size: 6 }, hovertemplate: "%{y:.3f} p.p.<extra>Sem direcionado</extra>" },
      { x: anos, y: r.inflacao, type: "scatter", mode: "lines+markers", name: "Com " + num(p.s * 100, 1) + "% direcionado",
        line: { color: cor("s1"), width: 2.5 }, marker: { size: 7 }, hovertemplate: "%{y:.3f} p.p.<extra>Com direcionado</extra>" },
    ], layout({ showlegend: true, legend: { orientation: "h", y: 1.15, x: 0, entrywidthmode: "pixels", entrywidth: 230 }, margin: { l: 52, r: 16, t: 26, b: 36 },
      xaxis: eixo({}), yaxis: eixo({ zeroline: true, zerolinecolor: cor("tinta-3"), ticksuffix: "" }) }));

    // aperto necessário em função de s (0 a 80%)
    const xs = [], ys = [];
    for (let k = 0; k <= 80; k++) { xs.push(k); ys.push(apertoNecessario(Object.assign({}, p, { s: k / 100 }))); }
    plotar("g-necessario", [
      { x: xs, y: ys, type: "scatter", mode: "lines", line: { color: cor("s1"), width: 2.5 }, hovertemplate: "s = %{x}%: %{y:.1f} p.p.<extra></extra>" },
      { x: [p.s * 100], y: [nec], type: "scatter", mode: "markers", hoverinfo: "skip",
        marker: { size: 11, color: cor("s1"), line: { color: cor("superficie"), width: 2 } } },
    ], layout({ hovermode: "closest", xaxis: eixo({ title: { text: "fatia do crédito direcionado", font: { size: 11 } }, ticksuffix: "%" }),
      yaxis: eixo({ title: { text: "aperto, p.p.", font: { size: 11 } }, rangemode: "tozero" }), margin: { l: 52, r: 16, t: 10, b: 46 } }));

    if (historico) {
      plotar("g-direcionado", [{ x: historico.x, y: historico.y, type: "scatter", mode: "lines", line: { color: cor("s3"), width: 2 },
        hovertemplate: "%{y:.1f}%<extra>direcionado</extra>" }],
        layout({ xaxis: eixo({ type: "date", tickformat: "%Y", hoverformat: "%m/%Y" }), yaxis: eixo({ ticksuffix: "%" }), margin: { l: 44, r: 12, t: 8, b: 28 } }));
    }
    $("leitura-potencia").textContent = "Com " + num(p.s * 100, 1) + "% do crédito fora do alcance da Selic, o mesmo aperto tem " +
      num(100 * pot / pot0, 0) + "% da potência que teria sem crédito direcionado: para reduzir a inflação em 1 p.p. no 2º ano, a Selic " +
      "precisa subir " + num(nec / nec0, 2) + " vezes mais. Essa proporção quase não depende de σ e κ; as magnitudes absolutas, sim." +
      (fonteS ? " " + fonteS : "");
  }

  // ------------------------------------------------------------------ Bloco 5
  function par5() {
    return { c: +$("sl-c").value, phi: +$("sl-phi5").value / 100, sigma: +$("sl-sigma5").value, s: +$("sl-s").value / 100 };
  }

  function renderBloco5() {
    const p = par5();
    $("out-c").textContent = num(p.c, 2);
    $("out-phi5").textContent = num(p.phi * 100, 1) + "%";
    $("out-sigma5").textContent = num(p.sigma, 2);
    const ef = efeitoImpacto(p), lim = limiarConsumo(p);
    const pp = Object.assign({}, BASE, p);
    const rendaPIB = (1 - pp.tau) * pp.phi * pp.d;   // p.p. do PIB por p.p. de Selic, líquido de IR
    if (saldoDBGG) {
      const bi = saldoDBGG * pp.phi * 0.01 / 1000;
      $("c5-rs").textContent = "R$ " + num(bi, 0) + " bi";
      $("c5-rs-sub").textContent = "por ano, brutos (" + num(pp.phi * pp.d, 2) + " p.p. do PIB); líquidos de IR: " + num(rendaPIB, 2) + " p.p.";
    } else {
      $("c5-rs").textContent = num(pp.phi * pp.d, 2) + " p.p.";
      $("c5-rs-sub").textContent = "do PIB por ano, antes do IR";
    }
    $("c5-lim").textContent = lim > 1 ? "> 1" : num(lim, 2);
    $("c5-liq").textContent = sinal(ef.liquido, 3);

    const rot = ["Canal convencional", "Canal de renda", "Efeito líquido"];
    plotar("g-canais", [{ type: "bar", orientation: "h", y: rot, x: [ef.convencional, ef.renda, ef.liquido],
      marker: { color: [cor("s1"), cor("s2"), cor("s3")], line: { color: cor("superficie"), width: 2 } },
      text: [ef.convencional, ef.renda, ef.liquido].map((v) => sinal(v, 3)), textposition: "outside", cliponaxis: false,
      hovertemplate: "%{y}: %{x:.3f} p.p.<extra></extra>" }],
      layout({ hovermode: "closest", xaxis: eixo({ zeroline: true, zerolinecolor: cor("tinta-3"), range: [-0.6, 0.6] }),
        yaxis: eixo({ autorange: "reversed" }), margin: { l: 130, r: 40, t: 8, b: 30 } }));

    const cs = [], liq = [];
    for (let k = 0; k <= 100; k++) { cs.push(k / 100); liq.push(efeitoImpacto(Object.assign({}, p, { c: k / 100 })).liquido); }
    const shapes = [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: { color: cor("tinta-3"), width: 1 } }];
    const annotations = [];
    if (lim <= 1) {
      shapes.push({ type: "line", x0: lim, x1: lim, yref: "paper", y0: 0, y1: 1, line: { color: cor("tinta-3"), width: 1, dash: "dot" } });
      annotations.push({ x: lim, yref: "paper", y: 1, yanchor: "top", xanchor: "left", xshift: 4, showarrow: false,
        text: "c* = " + num(lim, 2), font: { size: 11, color: cor("tinta-2") } });
    }
    plotar("g-limiar", [
      { x: cs, y: liq, type: "scatter", mode: "lines", line: { color: cor("s3"), width: 2.5 }, hovertemplate: "c = %{x:.2f}: %{y:.3f} p.p.<extra></extra>" },
      { x: [p.c], y: [ef.liquido], type: "scatter", mode: "markers", hoverinfo: "skip",
        marker: { size: 11, color: cor("s3"), line: { color: cor("superficie"), width: 2 } } },
    ], layout({ hovermode: "closest", shapes, annotations,
      xaxis: eixo({ title: { text: "propensão a consumir a renda de juros, c", font: { size: 11 } } }),
      yaxis: eixo({ title: { text: "efeito no hiato, p.p.", font: { size: 11 } } }), margin: { l: 56, r: 16, t: 10, b: 46 } }));

    $("leitura-renda").textContent = ef.liquido < 0
      ? "Com c = " + num(p.c, 2) + ", o canal convencional domina: o aperto esfria a demanda, mas " + num(100 * ef.renda / -ef.convencional, 0) +
        "% do seu efeito é anulado pela renda de juros. O aperto só passaria a aquecer a economia com c acima de " + (lim > 1 ? "1 (impossível com estes parâmetros)" : num(lim, 2)) + "."
      : "Com c = " + num(p.c, 2) + ", acima do limiar de " + num(lim, 2) + ", o canal de renda domina: subir a Selic aquece a demanda no curto prazo. " +
        "É o argumento das lentes 5 e 6; a evidência brasileira sobre c ainda está em aberto.";
  }

  // ------------------------------------------------------------------ carga
  async function iniciar() {
    if (!$("sl-s")) return;
    ["sl-s", "sl-omega", "sl-delta4", "sl-dur4", "sl-sigma4"].forEach((id) => $(id).addEventListener("input", () => { renderBloco4(); renderBloco5(); }));
    ["sl-c", "sl-phi5", "sl-sigma5"].forEach((id) => $(id).addEventListener("input", renderBloco5));
    try {
      const [rp, rn, rt] = await Promise.all(["data/painel.json", "data/nota_fiscal.json", "data/transmissao.json"].map((u) => fetch(u, { cache: "no-cache" })));
      if (rp.ok) {
        const p = await rp.json();
        const e = p.extras && p.extras.credito_direcionado_pct;
        if (e) {
          $("sl-s").value = Math.round(e.valor * 10) / 10;
          $("nota-s").textContent = "Valor inicial: " + num(e.valor, 1) + "% em " + e.data.split("-").reverse().join("/") + " (" + e.fonte + ").";
          fonteS = "Fatia direcionada observada: " + num(e.valor, 1) + "% (" + e.data.split("-").reverse().join("/") + ").";
        }
        const serie = p.series.credito_direcionado_pct;
        if (serie) {
          const x = [], y = [];
          p.meses.forEach((m, i) => { if (serie[i] != null) { x.push(m + "-01"); y.push(serie[i]); } });
          historico = { x, y };
        }
      }
      if (rn.ok) {
        const n = await rn.json();
        if (n.composicao_dbgg && n.composicao_dbgg.saldo_rs_milhoes) saldoDBGG = n.composicao_dbgg.saldo_rs_milhoes;
      }
      if (rt.ok) {
        const t = await rt.json();
        let desvio = 0;
        for (const caso of t.casos_referencia) {
          const r = resposta(caso.parametros);
          caso.inflacao.forEach((v, i) => { desvio = Math.max(desvio, Math.abs(v - r.inflacao[i])); });
        }
        $("conferencia-transmissao").textContent = (desvio < 1e-9 ? "✓ " : "⚠ ") + "Motor JavaScript dos Blocos 4 e 5 conferido contra o Python em " +
          t.casos_referencia.length + " casos de referência: desvio máximo de " + desvio.toExponential(1) + ".";
      }
    } catch (e) { /* segue com a calibração-base */ }
    renderBloco4();
    renderBloco5();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
