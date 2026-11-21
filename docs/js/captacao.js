/*
 * Captação de e-mail: adaptadores para Brevo, Kit e Substack (ou endpoint próprio).
 *
 * Configuração no <form id="form-cadastro"> do index.html:
 *   data-provedor=""            → desligado (mostra "em breve" e não envia nada)
 *   data-provedor="brevo"       data-id="https://XXXX.sibforms.com/serve/YYYY"  (URL do formulário embutido do Brevo)
 *   data-provedor="kit"         data-id="1234567"                              (número do formulário no Kit)
 *   data-provedor="substack"    data-id="nomedapublicacao"                     (subdomínio: nomedapublicacao.substack.com)
 *   data-provedor="personalizado" data-endpoint="https://..." data-campo-nome="..." data-campo-email="..."
 *
 * `montarEnvio` é pura (sem efeitos), para poder ser testada; `enviar` executa.
 */
(function (global) {
  "use strict";

  const EMAIL_VALIDO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  /** Descreve o envio para o provedor configurado: {modo: "post"|"abrir"|"desligado", url, campos}. */
  function montarEnvio(config, nome, email) {
    const p = (config.provedor || "").trim().toLowerCase();
    const id = (config.id || "").trim();
    if (!p) return { modo: "desligado" };
    if (p === "brevo") {
      if (!/^https:\/\/[\w.-]+\.sibforms\.com\/serve\/[\w-]+$/.test(id)) throw new Error("Brevo: data-id deve ser a URL https://….sibforms.com/serve/…");
      return { modo: "post", url: id, campos: { EMAIL: email, FIRSTNAME: nome, email_address_check: "", locale: "pt" } };
    }
    if (p === "kit") {
      if (!/^\d+$/.test(id)) throw new Error("Kit: data-id deve ser o número do formulário");
      return { modo: "post", url: "https://app.kit.com/forms/" + id + "/subscriptions",
        campos: { email_address: email, "fields[first_name]": nome } };
    }
    if (p === "substack") {
      if (!/^[a-z0-9-]+$/i.test(id)) throw new Error("Substack: data-id deve ser o subdomínio da publicação");
      return { modo: "abrir", url: "https://" + id + ".substack.com/subscribe?email=" + encodeURIComponent(email) };
    }
    if (p === "personalizado") {
      if (!/^https?:\/\//.test(config.endpoint || "")) throw new Error("personalizado: informe data-endpoint");
      const campos = {};
      campos[config.campoNome || "nome"] = nome;
      campos[config.campoEmail || "email"] = email;
      return { modo: "post", url: config.endpoint, campos };
    }
    throw new Error("provedor desconhecido: " + p);
  }

  function configDoForm(form) {
    return {
      provedor: form.dataset.provedor, id: form.dataset.id, endpoint: form.dataset.endpoint,
      campoNome: form.dataset.campoNome, campoEmail: form.dataset.campoEmail,
    };
  }

  /** Valida, monta e executa o envio. Devolve {tipo: "ok"|"erro", mensagem}. */
  async function enviar(form, nome, email) {
    if (!nome || !EMAIL_VALIDO.test(email)) return { tipo: "erro", mensagem: "Preencha nome e um e-mail válido." };
    let envio;
    try { envio = montarEnvio(configDoForm(form), nome, email); }
    catch (e) { console.error("[captação]", e.message); return { tipo: "erro", mensagem: "Cadastro mal configurado. Avise o autor." }; }
    if (envio.modo === "desligado") return { tipo: "erro", mensagem: "O cadastro será ativado em breve. Volte para conferir." };
    if (envio.modo === "abrir") {
      global.open(envio.url, "_blank", "noopener");
      return { tipo: "ok", mensagem: "Abrimos a página de assinatura em outra aba. Conclua por lá." };
    }
    try {
      // no-cors: os provedores não liberam CORS; o envio acontece, mas a resposta é opaca.
      await fetch(envio.url, { method: "POST", mode: "no-cors", body: new URLSearchParams(envio.campos) });
      return { tipo: "ok", mensagem: "Pronto! Confirme a inscrição no e-mail que acabamos de enviar." };
    } catch (e) {
      return { tipo: "erro", mensagem: "Não foi possível enviar agora. Tente de novo." };
    }
  }

  global.Captacao = { montarEnvio, enviar, configDoForm };
})(typeof window !== "undefined" ? window : globalThis);
