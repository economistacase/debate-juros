/*
 * Recursos de página: índice lateral com seção ativa, impressão/PDF e download dos dados em CSV.
 * (O link compartilhável do simulador fica em app.js, junto do estado do Bloco 1.)
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);

  // ------------------------------------------------------------------ índice lateral
  const ITENS = [
    ["retrato", "Retrato do debate"],
    ["dados", "1. Os dados"],
    ["lentes", "2. As lentes"],
    ["laboratorio", "3. O laboratório"],
    ["divida", "Bloco 1 — Dívida", true],
    ["taylor", "Bloco 2 — Taylor", true],
    ["regimes", "Bloco 3 — Regimes", true],
    ["mapa", "4. O mapa do debate"],
    ["episodio", "5. O episódio de 2026"],
    ["sintese", "Síntese e Perspectivas"],
    ["proximo", "Próxima etapa"],
  ];

  function montarIndice() {
    const nav = document.createElement("nav");
    nav.className = "indice";
    nav.setAttribute("aria-label", "Índice");
    nav.innerHTML = '<p class="indice__titulo">Índice</p><ul>' + ITENS.filter(([id]) => $(id)).map(([id, rot, sub]) =>
      '<li' + (sub ? ' class="sub"' : "") + '><a href="#' + id + '" data-alvo="' + id + '">' + rot + "</a></li>").join("") + "</ul>";
    document.body.appendChild(nav);

    const links = new Map([...nav.querySelectorAll("a")].map((a) => [a.dataset.alvo, a]));
    const visiveis = new Set();
    const obs = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => (e.isIntersecting ? visiveis.add(e.target.id) : visiveis.delete(e.target.id)));
      // seção ativa = a primeira, na ordem do índice, que está na faixa superior da tela
      const ativo = ITENS.map(([id]) => id).find((id) => visiveis.has(id));
      if (ativo) links.forEach((a, id) => a.classList.toggle("ativo", id === ativo));
    }, { rootMargin: "-80px 0px -65% 0px" });
    links.forEach((_, id) => obs.observe($(id)));
  }

  // ------------------------------------------------------------------ impressão
  function prepararImpressao() {
    $("bt-imprimir").addEventListener("click", () => {
      document.querySelectorAll("details.metodo").forEach((d) => (d.open = true));
      window.print();
    });
    // redimensiona os gráficos para a largura de impressão e de volta
    const ajustar = () => window.Plotly && document.querySelectorAll(".js-plotly-plot").forEach((g) => Plotly.Plots.resize(g));
    window.addEventListener("beforeprint", ajustar);
    window.addEventListener("afterprint", ajustar);
  }

  // ------------------------------------------------------------------ CSV
  async function baixarCSV() {
    const r = await fetch("data/painel.json", { cache: "no-cache" });
    const p = await r.json();
    const chaves = Object.keys(p.series);
    const linhas = [["mes", ...chaves].join(";")];
    p.meses.forEach((m, i) => linhas.push([m, ...chaves.map((k) => {
      const v = p.series[k][i];
      return v == null ? "" : String(v).replace(".", ",");
    })].join(";")));
    const blob = new Blob(["﻿" + linhas.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "painel-juros-bcb-" + p.meta.atualizado_em + ".csv";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }

  function iniciar() {
    montarIndice();
    prepararImpressao();
    const bt = $("bt-csv");
    if (bt) bt.addEventListener("click", () => baixarCSV().catch((e) => { bt.textContent = "Falha ao gerar CSV (" + e.message + ")"; }));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
