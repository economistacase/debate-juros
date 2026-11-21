"""Verificação ponta a ponta da página no Chrome (headless).

Sobe um servidor temporário sem cache, abre a página, injeta um verificador e exercita os blocos:
gráficos desenhados, ausência de erros de JavaScript, presets, reação de mercado, slider de Taylor,
abas de regimes, períodos, ponte "levar ao laboratório" e link compartilhável (conferido contra o Python).

Uso:  python tools/verificar_pagina.py        → código de saída 0 se tudo passou
Sem Chrome disponível, a verificação é pulada (saída 0, com aviso).
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
sys.path.insert(0, str(RAIZ))

CANDIDATOS_CHROME = [
    os.environ.get("CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]

# Verificador injetado no <head>, antes de qualquer script da página.
VERIFICADOR = r"""
<script>
window.__erros = [];
window.addEventListener("error", function (e) { window.__erros.push((e.message || "") + " @ " + (e.filename || "").split("/").pop() + ":" + e.lineno); });
window.addEventListener("unhandledrejection", function (e) { window.__erros.push("promise: " + e.reason); });
window.__resultado = function (obj) { obj.erros = window.__erros; document.title = "RESULTADO " + JSON.stringify(obj); };
const __esperar = (ms) => new Promise((r) => setTimeout(r, ms));
const __desenhado = (id) => { const el = document.getElementById(id); return !!(el && el.querySelector(".main-svg")); };
const __txt = (id) => (document.getElementById(id) || {}).textContent || "";
const __mover = (id, v) => { const el = document.getElementById(id); el.value = v; el.dispatchEvent(new Event("input")); };
window.addEventListener("load", async function () {
  await __esperar(4000);
  const r = {};
  try { await (CENARIO)(r); } catch (e) { r.excecao = String(e); }
  window.__resultado(r);
});
</script>
"""

CENARIOS = {
    "carga": r"""async (r) => {
        const ids = ["g-divida","g-varredura","g-taylor","g-taylor-traj","g-decomposicao","g-dados-juros","g-dados-real",
                     "g-dados-divida","g-dados-fiscal","g-dados-cambio","g-dados-composicao",
                     "g-r-inflacao","g-r-juro_nominal","g-r-juro_real","g-r-cambio","g-r-divida_pib","g-r-hiato"];
        r.vazios = ids.filter((i) => !__desenhado(i));
        r.conferencia = __txt("conferencia").slice(0, 2);
        r.d10 = __txt("c-d10"); r.placar = document.querySelectorAll("#placar .card").length;
        r.retrato = document.querySelectorAll(".retrato__item").length;
        r.indice = document.querySelectorAll(".indice a").length;
        r.katex = document.querySelectorAll(".katex").length;
        r.lentes = document.querySelectorAll(".lente").length;
        r.faixa_erro = !!document.querySelector(".faixa-erro");
    }""",
    "interacao": r"""async (r) => {
        const d0 = __txt("c-d10");
        document.querySelector('[data-preset="proposta"]').click(); await __esperar(300);
        r.proposta_selic = __txt("out-selic"); r.proposta_muda = __txt("c-d10") !== d0;
        r.leitura_proposta = __txt("leitura-divida").length > 50;
        document.getElementById("bt-reacao").click(); await __esperar(300);
        r.card_reacao_visivel = !document.querySelector(".card--reacao").hidden;
        __mover("sl-gamma", 1.5); await __esperar(300);
        document.querySelector('[data-preset="status"]').click(); await __esperar(300);
        r.status_selic = __txt("out-selic");
        r.leitura_varredura_minimo = /mínima/.test(__txt("leitura-varredura"));
        __mover("sl-k", 0.6); await __esperar(300);
        r.regime_k06 = document.getElementById("veredito-taylor").dataset.regime;
        __mover("sl-k", 1.5); await __esperar(300);
        r.regime_k15 = document.getElementById("veredito-taylor").dataset.regime;
        r.abas = [];
        for (const b of document.querySelectorAll("#abas-regimes button")) {
          b.click(); await __esperar(400);
          r.abas.push([b.dataset.cenario, document.querySelectorAll("#legenda-regimes li").length, __desenhado("g-r-inflacao")]);
        }
        for (const b of document.querySelectorAll("#periodos button")) { b.click(); await __esperar(300); }
        r.periodos_ok = __desenhado("g-dados-juros");
        document.getElementById("bt-levar").click(); await __esperar(400);
        r.levar_selic = document.getElementById("sl-selic").value;
    }""",
    "url": r"""async (r) => {
        r.selic = __txt("out-selic"); r.d10 = __txt("c-d10");
        r.reacao = document.getElementById("bt-reacao").getAttribute("aria-checked");
        r.gamma = __txt("out-gamma");
    }""",
}


class Injetor(http.server.SimpleHTTPRequestHandler):
    cenario = "carga"

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass

    def do_GET(self):
        caminho = self.path.split("?")[0]
        if caminho in ("/", "/index.html"):
            html = (DOCS / "index.html").read_text(encoding="utf-8")
            html = html.replace("<head>", "<head>" + VERIFICADOR.replace("CENARIO", CENARIOS[self.cenario_da_url()]), 1)
            dados = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
        else:
            super().do_GET()

    def cenario_da_url(self) -> str:
        m = re.search(r"[?&]__cenario=(\w+)", self.path)
        return m.group(1) if m else "carga"


def achar_chrome() -> str | None:
    for c in CANDIDATOS_CHROME:
        if c and (Path(c).exists() or shutil.which(c)):
            return c if Path(c).exists() else shutil.which(c)
    return None


def rodar(chrome: str, url: str, largura: int = 1600) -> dict:
    proc = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", f"--window-size={largura},3000",
                           "--virtual-time-budget=30000", "--dump-dom", url],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    m = re.search(r"<title>RESULTADO (.*?)</title>", proc.stdout, re.S)
    if not m:
        return {"falha": "sem resultado (página não terminou de carregar?)"}
    import html as _html
    return json.loads(_html.unescape(m.group(1)))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    chrome = achar_chrome()
    if not chrome:
        print("Chrome não encontrado: verificação no navegador pulada.")
        return 0
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Injetor, directory=str(DOCS)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    falhas: list[str] = []

    def checar(cond: bool, msg: str):
        print(("  ok    " if cond else "  FALHA ") + msg)
        if not cond:
            falhas.append(msg)

    for largura in (1280, 1600):
        r = rodar(chrome, base + "?__cenario=carga", largura)
        print(f"[carga {largura}px]")
        checar(not r.get("falha") and not r.get("excecao"), f"página carregou ({r.get('falha') or r.get('excecao') or 'ok'})")
        checar(r.get("erros") == [], f"sem erros de JavaScript {r.get('erros')}")
        checar(r.get("vazios") == [], f"todos os gráficos desenhados (vazios: {r.get('vazios')})")
        checar(r.get("conferencia") == "✓ ", "motor JS confere com o Python")
        checar(r.get("placar") == 8 and r.get("retrato") == 5 and r.get("lentes") == 6, "placar, retrato e lentes completos")
        checar(r.get("katex", 0) > 20, f"equações renderizadas ({r.get('katex')})")
        checar(r.get("faixa_erro") is False, "sem faixa de erro")
        if largura == 1600:
            checar(r.get("indice") == 11, f"índice lateral ({r.get('indice')} itens)")

    r = rodar(chrome, base + "?__cenario=interacao")
    print("[interações]")
    checar(r.get("erros") == [] and not r.get("excecao"), f"sem erros ({r.get('erros')} {r.get('excecao', '')})")
    checar("→" in r.get("proposta_selic", "") and r.get("proposta_muda") and r.get("leitura_proposta"), "preset da proposta")
    checar(r.get("card_reacao_visivel") is True, "reação de mercado liga o card de inflação")
    checar(r.get("status_selic") == "14,50%", f"preset status quo ({r.get('status_selic')})")
    checar(r.get("leitura_varredura_minimo") is True, "varredura com γ = 1,5 aponta Selic mínima")
    checar(r.get("regime_k06") == "neofisher" and r.get("regime_k15") == "taylor", "interruptor de Taylor")
    abas = r.get("abas", [])
    checar(len(abas) == 3 and all(n > 0 and ok for _, n, ok in abas), f"abas do Bloco 3 {abas}")
    checar(r.get("periodos_ok") is True, "seletor de período")
    checar(r.get("levar_selic") == "13.75", f"ponte dados → laboratório (Selic {r.get('levar_selic')})")

    from src.teoria import dinamica_divida as dd
    esperado = dd.simular(dd.Parametros(selic=list(dd.TRAJETORIA_PROPOSTA), pb=0.0, reacao=True, gamma=1.5))["divida"][-1]
    esperado_txt = f"{esperado * 100:.1f}".replace(".", ",") + "%"
    r = rodar(chrome, base + "?__cenario=url&cen=proposta&theta=7&pb=0&phi=56.9&reacao=1&gamma=1.5")
    print("[link compartilhável]")
    checar(r.get("erros") == [], f"sem erros ({r.get('erros')})")
    checar(r.get("d10") == esperado_txt and r.get("reacao") == "true", f"cenário reaberto: {r.get('d10')} (Python: {esperado_txt})")

    srv.shutdown()
    print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'} na verificação do navegador.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
