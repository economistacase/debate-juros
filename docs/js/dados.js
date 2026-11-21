/*
 * Parte 1 — painel de dados reais. Lê docs/data/painel.json (gerado por src/dados/bcb.py a partir do SGS/BCB e do Focus).
 * Nenhum número é digitado aqui: placar, texto e gráficos saem do JSON.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const nf = (c) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
  const f = (v, c = 1) => nf(c).format(v);
  const cor = (n) => getComputedStyle(document.documentElement).getPropertyValue("--" + n).trim();
  const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const mesExt = (iso) => { const [a, m] = iso.split("-"); return MESES[+m - 1] + "/" + a; };
  const CONFIG = { displayModeBar: false, responsive: true };

  let painel = null;
  let faixa = null;   // [inicio, fim] em 'AAAA-MM-DD'

  // ------------------------------------------------------------------ placar
  const CARDS = [
    ["selic_meta", "Meta Selic", "% a.a.", 2],
    ["ipca_12m", "IPCA em 12 meses", "%", 2],
    ["expectativa_12m", "Inflação esperada, 12 meses", "% (Focus)", 2],
    ["juro_real_ex_ante", "Juro real ex ante", "% a.a.", 1],
    ["dbgg", "Dívida bruta", "% do PIB", 1],
    ["primario", "Primário em 12 meses", "% do PIB", 2],
    ["juros_nominais", "Juros nominais em 12 meses", "% do PIB", 1],
    ["primario_estabilizador", "Primário que estabiliza a dívida", "% do PIB", 1],
  ];

  function dataCurta(d) { return d.length === 7 ? mesExt(d) : d.split("-").reverse().join("/"); }

  function renderPlacar() {
    const p = painel.placar;
    $("placar").innerHTML = CARDS.map(([k, rot, un, c]) => {
      const it = p[k];
      const alerta = k === "primario_estabilizador" ? " card--alerta" : "";
      return '<div class="card' + alerta + '"><p class="card__rot">' + rot + '</p><p class="card__val">' + f(it.valor, c) +
        '<small style="font-size:.5em;font-weight:500"> ' + un + '</small></p><p class="card__sub">' + dataCurta(it.data) +
        '</p><p class="card__fonte">' + it.fonte + "</p></div>";
    }).join("");

    const d = p.dbgg.valor, r = p.juro_implicito_dbgg.valor, th = p.pib_nominal_12m.valor;
    const pb = p.primario.valor, pbe = p.primario_estabilizador.valor;
    $("conta-real").innerHTML =
      "Com a dívida bruta em <strong>" + f(d) + "% do PIB</strong> (" + mesExt(p.dbgg.data) + "), juro implícito de <strong>" + f(r) +
      "%</strong> e PIB nominal crescendo <strong>" + f(th) + "%</strong> em 12 meses, estabilizar a dívida exigiria um superávit primário de <strong>" +
      f(pbe) + "% do PIB</strong>. O resultado atual é " + (pb >= 0 ? "um superávit" : "um déficit") + " de <strong>" + f(Math.abs(pb), 2) +
      "%</strong>. É essa distância de " + f(pbe - pb) + " pontos do PIB que dá força à proposta, e é por isso que o debate gira em torno do juro.";

    const ultimoMes = painel.meses[painel.meses.length - 1];
    $("meta-atualizado").textContent = painel.meta.atualizado_em.split("-").reverse().join("/");
    $("rodape-ref").textContent = mesExt(ultimoMes) + " (BCB/SGS e Focus)";
    $("fonte-dados").textContent = "Fontes: BCB/SGS (séries 4189, 432, 13522, 13762, 4513, 5793, 5760, 4382, 3696), Focus/BCB " +
      "(expectativa de IPCA 12 meses, mediana) e Nota de Estatísticas Fiscais (juro implícito e composição, " + mesExt(painel.composicao.data) +
      "). Dados atualizados em " + painel.meta.atualizado_em.split("-").reverse().join("/") + ".";
  }

  // ------------------------------------------------------------------ gráficos
  const GRAFICOS = {
    juros: { div: "g-dados-juros", series: [["selic", "Selic efetiva", "s1"], ["ipca_12m", "IPCA 12 meses", "s2"], ["expectativa_12m", "Expectativa 12 meses (Focus)", "s3", "dot"]] },
    real: { div: "g-dados-real", series: [["juro_real_ex_ante", "Ex ante", "s1"], ["juro_real_ex_post", "Ex post", "s2"]], zero: true },
    divida: { div: "g-dados-divida", series: [["dbgg", "Dívida bruta", "s1"], ["dlsp", "Dívida líquida", "s3"]] },
    fiscal: { div: "g-dados-fiscal", series: [["juros_nominais", "Juros nominais", "s2"], ["primario", "Resultado primário", "s1"]], zero: true },
    cambio: { div: "g-dados-cambio", series: [["cambio", "R$/US$", "s1"]], semLegenda: true },
  };

  function layout(extra) {
    const t2 = cor("tinta-2"), grade = cor("grade");
    return Object.assign({
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", separators: ",.",
      font: { family: "Inter, system-ui, sans-serif", size: 11, color: t2 },
      margin: { l: 40, r: 12, t: 18, b: 26 }, showlegend: false, hovermode: "x unified",
      hoverlabel: { bgcolor: cor("superficie"), bordercolor: cor("linha"), font: { color: cor("tinta"), size: 12 } },
    }, extra);
  }

  function marcos(range, largura) {
    const shapes = [], annotations = [];
    const curto = largura < 480;
    for (const m of painel.marcos) {
      const x = m.data + "-01";
      if (range && (x < range[0] || x > range[1])) continue;
      shapes.push({ type: "line", x0: x, x1: x, yref: "paper", y0: 0, y1: 1, line: { color: cor("tinta-3"), width: 1, dash: "dot" } });
      annotations.push({ x, yref: "paper", y: 1, yanchor: "bottom", xanchor: "right", xshift: -2, text: curto ? m.curto : m.rotulo, showarrow: false, font: { size: 10, color: cor("tinta-2") } });
    }
    return { shapes, annotations };
  }

  function renderGraficos() {
    const x = painel.meses.map((m) => m + "-01");
    const texto = painel.meses.map(mesExt);
    const range = faixa;
    for (const [chave, g] of Object.entries(GRAFICOS)) {
      const traces = g.series.map(([k, rot, c, dash]) => ({
        x, y: painel.series[k], type: "scatter", mode: "lines", name: rot, connectgaps: false,
        line: { color: cor(c), width: 2, dash: dash || "solid" }, customdata: texto,
        hovertemplate: "%{y:.2f}<extra>" + rot + "</extra>",
      }));
      const m = marcos(range, $(g.div).clientWidth);
      if (g.zero) m.shapes.push({ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: { color: cor("tinta-3"), width: 1 } });
      Plotly.react($(g.div), traces, layout({
        xaxis: { type: "date", range, gridcolor: cor("grade"), tickformat: "%Y", hoverformat: "%m/%Y", fixedrange: true, linecolor: cor("linha") },
        yaxis: { gridcolor: cor("grade"), zeroline: false, fixedrange: true, autorange: true },
        shapes: m.shapes, annotations: m.annotations,
      }), CONFIG);
      const leg = document.querySelector('[data-legenda="' + chave + '"]');
      if (leg) leg.innerHTML = g.series.map(([, rot, c, dash]) =>
        '<li><i class="' + (dash ? "tracejada" : "") + '" style="border-color:' + cor(c) + '"></i>' + rot + "</li>").join("");
    }
    ajustarEixoY();
    renderComposicao();
  }

  // reescala o eixo y à janela visível
  function ajustarEixoY() {
    if (!faixa) return;
    const i0 = painel.meses.findIndex((m) => m + "-01" >= faixa[0]);
    for (const g of Object.values(GRAFICOS)) {
      let lo = Infinity, hi = -Infinity;
      for (const [k] of g.series) {
        painel.series[k].slice(i0).forEach((v) => { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } });
      }
      if (g.zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
      const folga = (hi - lo) * 0.08 || 1;
      Plotly.relayout($(g.div), { "yaxis.range": [lo - folga, hi + folga] });
    }
  }

  function renderComposicao() {
    const c = painel.composicao;
    const cores = ["s1", "s2", "s3", "s4"];
    const traces = Object.entries(c.fatias).map(([rot, v], i) => ({
      type: "bar", orientation: "h", y: [""], x: [v], name: rot, text: [rot + "<br><b>" + f(v) + "%</b>"],
      textposition: v > 8 ? "inside" : "none", insidetextanchor: "middle", textfont: { color: "#fff", size: 11 },
      marker: { color: cor(cores[i]), line: { color: cor("superficie"), width: 2 } },
      hovertemplate: rot + ": %{x:.1f}%<extra></extra>",
    }));
    Plotly.react($("g-dados-composicao"), traces, layout({
      barmode: "stack", hovermode: "closest", showlegend: true, legend: { orientation: "h", y: -0.1, x: 0, traceorder: "normal", font: { size: 11 } },
      margin: { l: 8, r: 8, t: 8, b: 8 },
      xaxis: { range: [0, 100], visible: false, fixedrange: true }, yaxis: { visible: false, fixedrange: true },
    }), CONFIG);
    $("nota-composicao").textContent = "Mais da metade da dívida bruta paga Selic, e " + f(c.vence_12m) +
      "% vence em até 12 meses: cada mudança da Selic chega rápido ao custo da dívida, nos dois sentidos. Fonte: " + c.fonte + ", " + mesExt(c.data) + ".";
  }

  // ------------------------------------------------------------------ período
  function definirFaixa(btn) {
    const fim = painel.meses[painel.meses.length - 1];
    let ini;
    if (btn.dataset.anos) {
      const [a, m] = fim.split("-");
      ini = (+a - +btn.dataset.anos) + "-" + m;
    } else ini = btn.dataset.desde;
    const [a, m] = fim.split("-");
    faixa = [ini + "-01", a + "-" + m + "-28"];
    document.querySelectorAll("#periodos button").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
  }

  document.querySelectorAll("#periodos button").forEach((b) => b.addEventListener("click", () => {
    if (!painel) return;
    definirFaixa(b);
    renderGraficos();
  }));

  // ------------------------------------------------------------------ ponte para o laboratório
  $("bt-levar").addEventListener("click", () => {
    if (!painel) return;
    const p = painel.placar;
    const ajustar = (id, v, passo) => {
      const el = $(id);
      if (!el) return;
      el.value = Math.min(+el.max, Math.max(+el.min, Math.round(v / passo) * passo));
      el.dispatchEvent(new Event("input"));
    };
    ajustar("sl-selic", p.selic_meta.valor, 0.25);
    ajustar("sl-theta", p.pib_nominal_12m.valor, 0.25);
    ajustar("sl-pb", p.primario.valor, 0.1);
    ajustar("sl-phi", painel.composicao.fatias["Selic (inclui compromissadas)"], 0.1);
    $("divida").scrollIntoView({ behavior: "smooth" });
  });

  // ------------------------------------------------------------------ retrato e decomposição (Nota Fiscal)
  let nota = null;

  function renderRetrato() {
    const r = nota.retrato;
    $("retrato-ref").textContent = "BCB, ref. " + r.referencia;
    $("retrato-itens").innerHTML = r.itens.map((it) => {
      const dec = Math.abs(it.valor) < 1 && it.id === "sensibilidade" ? 2 : 1;
      const val = it.valor2 != null
        ? f(it.valor, 1) + "% <span class='retrato__vs'>vs.</span> +" + f(it.valor2, 1) + "%"
        : f(it.valor, dec) + (it.unidade.startsWith("%") ? "%" : "");
      const un = it.valor2 != null ? it.unidade.replace(/^% /, "") : it.unidade.replace(/^% ?/, "");
      return '<div class="retrato__item"><p class="retrato__val">' + val + ' <small>' + un + '</small></p><p class="retrato__lab">' +
        it.rotulo + (it.nota ? '<br><span>' + it.nota + "</span>" : "") + "</p></div>";
    }).join("");
    $("retrato-fonte").textContent = "Fonte: " + r.fonte + ". O placar da Parte 1 usa as séries do SGS já revisadas, por isso pode diferir em 0,1 ponto.";
  }

  function renderDecomposicao() {
    const d = nota.decomposicao_dbgg;
    const x = [d.inicio.rotulo], base = [0], y = [d.inicio.valor], cores = [cor("tinta-3")], texto = [f(d.inicio.valor) + "%"];
    let nivel = d.inicio.valor;
    const conectores = [];
    d.fatores.forEach((fat, i) => {
      x.push(fat.rotulo);
      base.push(fat.valor >= 0 ? nivel : nivel + fat.valor);
      y.push(Math.abs(fat.valor));
      cores.push(fat.valor >= 0 ? cor("s2") : cor("s1"));
      texto.push((fat.valor > 0 ? "+" : "−") + f(Math.abs(fat.valor)));
      conectores.push({ de: i, nivel });
      nivel += fat.valor;
    });
    conectores.push({ de: d.fatores.length, nivel });
    x.push(d.fim.rotulo); base.push(0); y.push(d.fim.valor); cores.push(cor("tinta-3")); texto.push(f(d.fim.valor) + "%");
    const hover = x.map((rot, i) => i === 0 || i === x.length - 1 ? rot + ": " + texto[i] + " do PIB" : rot + ": " + texto[i] + " p.p. do PIB");
    // conector do topo de cada barra (índice c.de) até a seguinte, no nível acumulado
    const shapes = conectores.map((c) => ({
      type: "line", xref: "x", x0: c.de + 0.4, x1: c.de + 0.6, y0: c.nivel, y1: c.nivel,
      line: { color: cor("tinta-3"), width: 1, dash: "dot" },
    }));
    Plotly.react($("g-decomposicao"), [{
      type: "bar", x, y, base, text: texto, textposition: "outside", cliponaxis: false,
      marker: { color: cores, line: { color: cor("superficie"), width: 2 } },
      hovertext: hover, hoverinfo: "text", textfont: { color: cor("tinta"), size: 12 },
    }], layout({
      hovermode: "closest", margin: { l: 44, r: 12, t: 24, b: 40 },
      xaxis: { type: "category", fixedrange: true, tickfont: { size: 11 } },
      yaxis: { range: [0, 105], ticksuffix: "%", gridcolor: cor("grade"), fixedrange: true },
      shapes,
    }), CONFIG);
    const m = d.memoria, dl = d.divida_liquida;
    $("nota-decomposicao").innerHTML =
      "Entre dez/2015 e dez/2025, a dívida bruta subiu " + f(d.variacao_total) + " pontos do PIB, e o juro real sozinho somou <strong>+" + f(m.juro_real) +
      "</strong>. Memória: os juros nominais somaram " + f(m.juros_nominais) + " p.p., dos quais " + f(m.erosao_inflacionaria) +
      " apenas repuseram a inflação (erosão inflacionária). A identidade atribui, mas não identifica causalidade. <strong>Na dívida líquida a história é outra:</strong> " +
      "superávits primários subtraíram " + f(Math.abs(dl.superavits_2003_2013), 0) + " p.p. do PIB entre 2003 e 2013, e déficits somaram " +
      f(dl.deficits_2014_2025, 0) + " p.p. entre 2014 e 2025. Diferenças de 0,1 p.p. por arredondamento. Fonte: " + d.fonte + ".";
  }

  // ------------------------------------------------------------------ carga
  async function iniciar() {
    try {
      const rn = await fetch("data/nota_fiscal.json", { cache: "no-cache" });
      if (rn.ok) {
        nota = await rn.json();
        renderRetrato();
        renderDecomposicao();
      }
    } catch (e) { /* o retrato é complementar: segue sem ele */ }
    try {
      const r = await fetch("data/painel.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      painel = await r.json();
      renderPlacar();
      definirFaixa(document.querySelector('#periodos [aria-pressed="true"]'));
      renderGraficos();
    } catch (e) {
      $("conta-real").textContent = "Não foi possível carregar os dados (" + e.message + "). Abra a página por um servidor: python -m http.server 8000 -d docs";
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
