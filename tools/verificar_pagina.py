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
                     "g-r-inflacao","g-r-juro_nominal","g-r-juro_real","g-r-cambio","g-r-divida_pib","g-r-hiato",
                     "g-potencia","g-necessario","g-direcionado","g-canais","g-limiar"];
        r.vazios = ids.filter((i) => !__desenhado(i));
        r.conferencia = __txt("conferencia").slice(0, 2);
        r.d10 = __txt("c-d10"); r.placar = document.querySelectorAll("#placar .card").length;
        r.retrato = document.querySelectorAll(".retrato__item").length;
        r.indice = document.querySelectorAll(".indice a").length;
        r.katex = document.querySelectorAll(".katex").length;
        r.lentes = document.querySelectorAll(".lente").length;
        r.faixa_erro = !!document.querySelector(".faixa-erro");
        r.conf_transmissao = __txt("conferencia-transmissao").slice(0, 2);
        r.c4_nec = __txt("c4-nec"); r.c4_s = document.getElementById("sl-s").value; r.c5_lim = __txt("c5-lim"); r.c5_rs = __txt("c5-rs");
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
        __mover("sl-s", 0); await __esperar(200); r.b4_rel_s0 = __txt("c4-rel");
        __mover("sl-s", 43.7); await __esperar(200);
        __mover("sl-c", 0.9); await __esperar(200); r.b5_liq_c09 = __txt("c5-liq"); r.b5_leitura = __txt("leitura-renda");
        __mover("sl-sigma5", 0.15); await __esperar(200); r.b5_lim_sig015 = __txt("c5-lim");
        document.getElementById("bt-levar").click(); await __esperar(400);
        r.levar_selic = document.getElementById("sl-selic").value;
    }""",
    "captacao": r"""async (r) => {
        const f = document.getElementById("form-cadastro"), st = document.getElementById("form-status");
        const preencher = (n, e) => { document.getElementById("f-nome").value = n; document.getElementById("f-email").value = e; };
        r.config_publicada = { provedor: f.dataset.provedor, id: f.dataset.id };
        r.url_publicada = window.Captacao.montarEnvio({ provedor: f.dataset.provedor, id: f.dataset.id }, "x", "x@y.co").url || "";
        f.dataset.provedor = ""; f.dataset.id = "";          // nada de teste vai para a conta real
        const enviar = async () => { f.dispatchEvent(new Event("submit", { cancelable: true })); await __esperar(600); return st.textContent; };
        preencher("Ana", "ana@exemplo.com"); r.desligado = await enviar();
        preencher("Ana", "invalido"); f.dataset.provedor = "kit"; f.dataset.id = "123"; r.invalido = await enviar();
        const C = window.Captacao;
        r.kit = C.montarEnvio({ provedor: "kit", id: "123" }, "Ana", "a@b.co");
        r.brevo = C.montarEnvio({ provedor: "brevo", id: "https://abc.sibforms.com/serve/XYZ" }, "Ana", "a@b.co");
        r.substack = C.montarEnvio({ provedor: "substack", id: "minhapub" }, "Ana", "a@b.co");
        try { C.montarEnvio({ provedor: "kit", id: "abc" }, "Ana", "a@b.co"); r.kit_invalido = "aceitou"; } catch (e) { r.kit_invalido = "recusou"; }
        f.dataset.provedor = "personalizado"; f.dataset.endpoint = location.origin + "/__captacao";
        f.dataset.campoNome = "nome"; f.dataset.campoEmail = "email";
        preencher("Raimundo Teste", "teste@exemplo.com"); r.envio = await enviar();
        r.recebido = await (await fetch("/__captacao_ultimo")).text();
    }""",
    "onda2": r"""async (r) => {
        r.vazios = ["g-o2-hiato","g-o2-pre","g-o2-lft","g-o2-selic","g-o2-disp-pre","g-o2-disp-lft","g-o2-ev-cambio","g-o2-ev-ltn"].filter((i) => !__desenhado(i));
        r.cards = document.querySelectorAll("#o2-cards .card").length;
        r.linhas_tabela = document.querySelectorAll("#o2-tabela tbody tr").length;
        r.linhas_eventos = document.querySelectorAll("#o2-eventos tbody tr").length;
        r.card_lft = (document.querySelector("#o2-cards .card .card__val") || {}).textContent;
        const b = document.querySelector('#o2-rn [data-rn="4"]'); b.click(); await __esperar(300);
        r.card_lft_rn4 = (document.querySelector("#o2-cards .card .card__val") || {}).textContent;
        r.link_lab = document.getElementById("o2-link-lab").getAttribute("href");
        r.indice = document.querySelectorAll(".indice a").length;
        r.katex = document.querySelectorAll(".katex").length;
    }""",
    "url": r"""async (r) => {
        r.selic = __txt("out-selic"); r.d10 = __txt("c-d10");
        r.reacao = document.getElementById("bt-reacao").getAttribute("aria-checked");
        r.gamma = __txt("out-gamma");
    }""",
}


class Injetor(http.server.SimpleHTTPRequestHandler):
    cenario = "carga"
    ultimo_post = ""          # corpo do último POST recebido no endpoint simulado de captação

    def do_POST(self):
        if self.path.startswith("/__captacao"):
            n = int(self.headers.get("Content-Length", 0))
            Injetor.ultimo_post = self.rfile.read(n).decode("utf-8")
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass

    def do_GET(self):
        caminho = self.path.split("?")[0]
        if caminho == "/__captacao_ultimo":
            dados = Injetor.ultimo_post.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
            return
        if caminho in ("/", "/index.html", "/onda2.html"):
            html = (DOCS / ("onda2.html" if caminho == "/onda2.html" else "index.html")).read_text(encoding="utf-8")
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
            checar(r.get("indice") == 13, f"índice lateral ({r.get('indice')} itens)")
            from src.teoria import transmissao as tr
            nec = tr.aperto_necessario(tr.ParTransmissao(s=float(r.get("c4_s", 0)) / 100))
            nec_txt = f"{nec:.1f}".replace(".", ",") + " p.p."
            lim_txt = f"{tr.limiar_consumo(tr.ParTransmissao(s=float(r.get('c4_s', 0)) / 100)):.2f}".replace(".", ",")
            checar(r.get("conf_transmissao") == "✓ ", "motor dos Blocos 4 e 5 confere com o Python")
            checar(r.get("c4_s") == "43.7", f"Bloco 4 começa com o dado do SGS (s = {r.get('c4_s')}%)")
            checar(r.get("c4_nec") == nec_txt, f"aperto necessário {r.get('c4_nec')} (Python: {nec_txt})")
            checar(r.get("c5_lim") == lim_txt, f"limiar c* {r.get('c5_lim')} (Python: {lim_txt})")
            checar(r.get("c5_rs", "").startswith("R$"), f"renda de juros em R$ a partir da Nota ({r.get('c5_rs')})")

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
    checar(r.get("b4_rel_s0") == "100%", f"Bloco 4: sem direcionado, potência relativa 100% ({r.get('b4_rel_s0')})")
    checar(r.get("b5_liq_c09", "").startswith("+") and "domina: subir" in r.get("b5_leitura", ""),
           f"Bloco 5: com c = 0,9 o aperto aquece ({r.get('b5_liq_c09')})")
    checar(r.get("b5_lim_sig015") == "0,21", f"Bloco 5: limiar cai com σ = 0,15 ({r.get('b5_lim_sig015')})")

    r = rodar(chrome, base + "?__cenario=captacao")
    print("[captação de e-mail]")
    checar(r.get("erros") == [] and not r.get("excecao"), f"sem erros ({r.get('erros')} {r.get('excecao', '')})")
    cfg = r.get("config_publicada", {})
    checar(cfg.get("provedor") == "kit" and (cfg.get("id") or "").isdigit(), f"formulário publicado aponta para o Kit ({cfg})")
    checar(r.get("url_publicada") == f"https://app.kit.com/forms/{cfg.get('id')}/subscriptions", f"endpoint do Kit ({r.get('url_publicada')})")
    checar("em breve" in r.get("desligado", ""), "desligado: avisa 'em breve' e não envia")
    checar("válido" in r.get("invalido", ""), "valida o e-mail antes de enviar")
    kit, brevo, sub = r.get("kit", {}), r.get("brevo", {}), r.get("substack", {})
    checar(kit.get("url") == "https://app.kit.com/forms/123/subscriptions" and kit.get("campos", {}).get("email_address") == "a@b.co",
           "adaptador Kit")
    checar(brevo.get("campos", {}).get("EMAIL") == "a@b.co" and brevo.get("campos", {}).get("FIRSTNAME") == "Ana", "adaptador Brevo")
    checar(sub.get("modo") == "abrir" and "minhapub.substack.com/subscribe?email=a%40b.co" in sub.get("url", ""), "adaptador Substack")
    checar(r.get("kit_invalido") == "recusou", "recusa configuração inválida")
    checar("Pronto" in r.get("envio", "") and "nome=Raimundo+Teste" in r.get("recebido", "")
           and "email=teste%40exemplo.com" in r.get("recebido", ""), f"envio real ponta a ponta (recebido: {r.get('recebido')})")

    import json as _json
    o2 = _json.loads((DOCS / "data" / "onda2.json").read_text(encoding="utf-8"))
    est = {(e["medida"], e["r_neutro"]): e["gamma"]["valor"] for e in o2["gamma"]}
    fmt = lambda v: ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):.3f}".replace(".", ",")
    r = rodar(chrome, base + "onda2.html?__cenario=onda2", 1600)
    print("[onda 2]")
    checar(r.get("erros") == [] and not r.get("excecao"), f"sem erros ({r.get('erros')} {r.get('excecao', '')})")
    checar(r.get("vazios") == [], f"todos os gráficos desenhados (vazios: {r.get('vazios')})")
    checar(r.get("cards") == 3 and r.get("linhas_tabela") == len(o2["gamma"]) and r.get("linhas_eventos") == 4, "cards e tabelas completos")
    checar(r.get("card_lft") == fmt(est[("lft", 5.0)]), f"γ exibido {r.get('card_lft')} = JSON {fmt(est[('lft', 5.0)])}")
    checar(r.get("card_lft_rn4") == fmt(est[("lft", 4.0)]), f"seletor de juro neutro ({r.get('card_lft_rn4')})")
    checar("reacao=1" in (r.get("link_lab") or "") and "gamma=" in (r.get("link_lab") or ""), f"link para o laboratório ({r.get('link_lab')})")
    checar(r.get("indice") == 6 and r.get("katex", 0) >= 5, f"índice ({r.get('indice')}) e equações ({r.get('katex')})")

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
