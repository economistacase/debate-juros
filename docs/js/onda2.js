/*
 * Onda 2 — página de resultados empíricos. Lê docs/data/onda2.json (gerado por src/empirico/onda2.py).
 * Nenhum número é digitado aqui: estimativas, séries e eventos vêm do JSON.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const nf = (c) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
  const num = (v, c = 2) => (v == null ? "–" : nf(c).format(v));
  const sinal = (v, c = 3) => (v > 0 ? "+" : v < 0 ? "−" : "") + nf(c).format(Math.abs(v));
  const cor = (n) => getComputedStyle(document.documentElement).getPropertyValue("--" + n).trim();
  const CONFIG = { displayModeBar: false, responsive: true };
  const ROTULO = { lft: "Spread da LFT", premio_pre: "Prêmio prefixado" };
  let dados = null, rn = 5;

  function layout(extra) {
    return Object.assign({
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", separators: ",.",
      font: { family: "Source Sans 3, Segoe UI, sans-serif", size: 12, color: cor("tinta-2") },
      margin: { l: 48, r: 14, t: 12, b: 40 }, showlegend: false, hovermode: "x unified",
      hoverlabel: { bgcolor: cor("superficie"), bordercolor: cor("linha"), font: { color: cor("tinta"), size: 12 } },
    }, extra);
  }
  const eixo = (e) => Object.assign({ gridcolor: cor("grade"), zeroline: false, linecolor: cor("linha"), fixedrange: true }, e);
  const plotar = (id, tr, lay) => window.Plotly && Plotly.react($(id), tr, lay, CONFIG);
  const x = () => dados.mensal.meses.map((m) => m + "-01");

  function serie(id, chave, c, extra) {
    plotar(id, [{ x: x(), y: dados.mensal[chave], type: "scatter", mode: "lines", connectgaps: false,
      line: { color: cor(c), width: 2 }, hovertemplate: "%{y:.2f}<extra></extra>" }],
      layout(Object.assign({ xaxis: eixo({ type: "date", tickformat: "%Y", hoverformat: "%m/%Y" }), yaxis: eixo({ zeroline: true, zerolinecolor: cor("tinta-3") }) }, extra)));
  }

  function renderSeries() {
    serie("g-o2-hiato", "g_5.0", "s1");
    serie("g-o2-pre", "premio_pre", "s2");
    serie("g-o2-lft", "lft", "s3");
    const m = dados.mensal;
    const neutro = m.pi_e.map((p) => (p == null ? null : 5 + p));
    const tr = [["selic", "Selic efetiva", "s1", "solid"], ["selic_esperada", "Selic esperada (Focus, 3 anos)", "s2", "solid"]]
      .map(([k, rot, c, d]) => ({ x: x(), y: m[k], type: "scatter", mode: "lines", name: rot, line: { color: cor(c), width: 2, dash: d },
        hovertemplate: "%{y:.2f}<extra>" + rot + "</extra>" }));
    tr.push({ x: x(), y: neutro, type: "scatter", mode: "lines", name: "Neutro nominal (5% + π esperada)",
      line: { color: cor("ref"), width: 1.5, dash: "dash" }, hovertemplate: "%{y:.2f}<extra>Neutro nominal</extra>" });
    plotar("g-o2-selic", tr, layout({ xaxis: eixo({ type: "date", tickformat: "%Y", hoverformat: "%m/%Y" }), yaxis: eixo({ ticksuffix: "%" }) }));
    $("leg-o2-selic").innerHTML = tr.map((t) => '<li><i class="' + (t.line.dash === "dash" ? "tracejada" : "") + '" style="border-color:' +
      t.line.color + '"></i>' + t.name + "</li>").join("");
  }

  const estimativa = (medida, r) => dados.gamma.find((e) => e.medida === medida && e.r_neutro === r);

  function renderEstimativa() {
    const rns = [...new Set(dados.gamma.map((e) => e.r_neutro))];
    $("o2-rn").innerHTML = "<span>Juro real neutro:</span>" + rns.map((r) =>
      '<button type="button" data-rn="' + r + '" aria-pressed="' + (r === rn) + '">' + num(r, 1) + "%</button>").join("");
    $("o2-rn").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { rn = +b.dataset.rn; renderEstimativa(); }));

    const cards = ["lft", "premio_pre"].map((m) => {
      const e = estimativa(m, rn), g = e.gamma, lp = e.dinamico.gamma_longo_prazo;
      return '<div class="card"><p class="card__rot">γ medido pelo ' + (m === "lft" ? "spread da LFT" : "prêmio prefixado") + "</p><p class=\"card__val\">" + sinal(g.valor) +
        '</p><p class="card__sub">IC 95%: ' + sinal(g.ic95[0], 2) + " a " + sinal(g.ic95[1], 2) + " · longo prazo " + sinal(lp.valor) +
        "</p><p class=\"card__fonte\">" + e.periodo[0] + " a " + e.periodo[1] + ", " + e.n + " meses (" + e.meses_com_hiato + " com g > 0)</p></div>";
    });
    cards.push('<div class="card card--alerta"><p class="card__rot">Limiar do Bloco 1</p><p class="card__val">γ = 1</p>' +
      '<p class="card__sub">acima dele, cortar abaixo do neutro eleva a dívida</p></div>');
    $("o2-cards").innerHTML = cards.join("");

    const m = dados.mensal;
    // g para o r_n escolhido: recalculado a partir das séries (o JSON traz o de 5%)
    const g = m.pi_e.map((p, i) => (p == null || m.selic[i] == null ? null : Math.max(0, rn + p - m.selic[i])));
    for (const [medida, id, c] of [["premio_pre", "g-o2-disp-pre", "s2"], ["lft", "g-o2-disp-lft", "s3"]]) {
      const e = estimativa(medida, rn);
      const xs = [], ys = [];
      m[medida].forEach((v, i) => { if (v != null && g[i] != null) { xs.push(g[i]); ys.push(v); } });
      const xmax = Math.max(...xs);
      plotar(id, [
        { x: xs, y: ys, type: "scatter", mode: "markers", marker: { color: cor(c), size: 6, opacity: 0.55 }, hovertemplate: "g = %{x:.2f}, prêmio = %{y:.2f}<extra></extra>" },
        { x: [0, xmax], y: [e.constante, e.constante + e.gamma.valor * xmax], type: "scatter", mode: "lines",
          line: { color: cor("marinho"), width: 2 }, hoverinfo: "skip" },
      ], layout({ hovermode: "closest", xaxis: eixo({ title: { text: "hiato de credibilidade g, p.p.", font: { size: 11 } } }),
        yaxis: eixo({ title: { text: "prêmio, p.p.", font: { size: 11 } } }) }));
    }

    $("o2-tabela").querySelector("tbody").innerHTML = dados.gamma.map((e) => "<tr><td>" + ROTULO[e.medida] + "</td><td>" + num(e.r_neutro, 1) +
      "%</td><td>" + sinal(e.gamma.valor) + " (" + sinal(e.gamma.ic95[0], 2) + " a " + sinal(e.gamma.ic95[1], 2) + ")</td><td>" +
      sinal(e.dinamico.gamma_longo_prazo.valor) + " (" + num(e.dinamico.gamma_longo_prazo.ep, 3) + ")</td><td>" + e.n + "</td><td>" +
      e.meses_com_hiato + "</td></tr>").join("");

    const maxIC = Math.max(...dados.gamma.map((e) => e.gamma.ic95[1]));
    const lpMax = Math.max(...dados.gamma.map((e) => e.dinamico.gamma_longo_prazo.valor + 1.96 * e.dinamico.gamma_longo_prazo.ep));
    $("o2-leitura").innerHTML =
      "<p><strong>O que os dados dizem.</strong> Nos meses em que a Selic esteve abaixo do juro neutro nominal (2012–13 e 2017–21), o prêmio " +
      "exigido para rolar a dívida subiu pouco. Em todas as combinações de medida e juro neutro, o limite superior do intervalo de 95% para γ é de no " +
      "máximo " + num(maxIC, 2) + " (" + num(lpMax, 2) + " no longo prazo), muito abaixo do limiar de 1 do Bloco 1.</p>" +
      "<p><strong>O que isso implica.</strong> Pesa contra a versão extrema da crítica, segundo a qual qualquer corte abaixo do neutro dispara o prêmio. " +
      "Nos episódios observados, o mundo do Bloco 1 se pareceu mais com o mecânico do que com o de reação forte.</p>" +
      "<p><strong>O que isso não implica.</strong> Não valida a proposta de 2026. Os cortes do passado foram decididos por um Banco Central com metas " +
      "de inflação, não impostos por um conselho fiscal-monetário, e a estimativa tem viés para baixo (ver o quadro abaixo).</p>";
    // maior limite superior de 95% entre as duas medidas, levado ao passo do slider (0,05)
    const sup = Math.max(...["lft", "premio_pre"].map((m) => estimativa(m, rn).gamma.ic95[1]));
    const gLab = Math.max(0.05, Math.round(sup / 0.05) * 0.05);           // valor do slider (passo 0,05) mais próximo
    $("o2-link-lab").href = "./?selic=7.5&theta=7&pb=-0.5&phi=56.9&reacao=1&gamma=" + gLab.toFixed(2) + "#divida";
    $("o2-link-lab").textContent = "Testar no laboratório com γ = " + num(gLab, 2) + " (próximo do limite superior de 95%, " + num(sup, 3) +
      ") e Selic de 7,5% →";
  }

  function renderEventos() {
    const ev = dados.eventos;
    for (const [chave, id, c, unidade] of [["cambio", "g-o2-ev-cambio", "s2", "%"], ["ltn", "g-o2-ev-ltn", "s1", " p.p."]]) {
      const pts = ev.lista.filter((r) => r[chave] != null);
      plotar(id, [{ x: pts.map((r) => r.surpresa), y: pts.map((r) => r[chave]), text: pts.map((r) => r.data), type: "scatter", mode: "markers",
        marker: { color: cor(c), size: 7, opacity: 0.6 }, hovertemplate: "%{text}: surpresa %{x:.2f} → %{y:.2f}" + unidade + "<extra></extra>" }],
        layout({ hovermode: "closest", xaxis: eixo({ title: { text: "surpresa, p.p.", font: { size: 11 } }, zeroline: true, zerolinecolor: cor("tinta-3") }),
          yaxis: eixo({ zeroline: true, zerolinecolor: cor("tinta-3") }) }));
    }
    const nomes = { cambio: "Câmbio (% no dia seguinte)", ltn: "LTN 2–4 anos (p.p.)", lft: "Spread da LFT (p.p.)", pi_e: "Inflação esperada 12m (p.p., 1 semana)" };
    $("o2-eventos").querySelector("tbody").innerHTML = Object.entries(ev.regressoes).map(([k, r]) => "<tr><td>" + nomes[k] + "</td><td>" +
      sinal(r.coef.valor) + " (ep " + num(r.coef.ep, 3) + ")</td><td>" + num(r.coef.p, 3) + "</td><td>" + r.n + "</td><td>" + r.surpresas_nao_nulas + "</td></tr>").join("");
    const c = ev.regressoes.cambio;
    $("o2-leitura-eventos").textContent = "Uma surpresa de +1 p.p. na Selic move o dólar em " + sinal(c.coef.valor, 2) + "% no dia seguinte (p = " +
      num(c.coef.p, 2) + "): juros acima do esperado apreciam o real, como prevê a teoria. Os efeitos sobre a LTN e sobre a inflação esperada não são " +
      "estatisticamente significativos. Só " + c.surpresas_nao_nulas + " das " + c.n + " reuniões tiveram surpresa, o que limita o poder dos testes.";
  }

  async function iniciar() {
    if (window.renderMathInElement) renderMathInElement(document.body, {
      delimiters: [{ left: "$$", right: "$$", display: true }, { left: "\\(", right: "\\)", display: false }], throwOnError: false });
    try {
      const r = await fetch("data/onda2.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      dados = await r.json();
    } catch (e) {
      $("o2-leitura").textContent = "Não foi possível carregar os resultados (" + e.message + "). Abra a página por um servidor: python servidor.py";
      return;
    }
    const data = dados.meta.gerado_em.split("-").reverse().join("/");
    $("o2-gerado").textContent = data;
    $("rodape-o2").textContent = data;
    $("o2-fontes").textContent = dados.meta.fontes.join("; ");
    renderSeries();
    renderEstimativa();
    renderEventos();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
