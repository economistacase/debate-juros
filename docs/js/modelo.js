/*
 * Motor de cálculo do Laboratório (espelho exato de src/teoria/dinamica_divida.py).
 * Nenhuma curva é desenhada à mão: tudo o que os sliders mostram sai destas funções.
 * Se mudar uma fórmula aqui, mude também no Python e rode `python build.py`.
 */
(function (global) {
  "use strict";

  const ANO_INICIAL = 2026;
  const HORIZONTE = 10;

  /** Calibração-base (BCB, Nota de Estatísticas Fiscais, set/2026). */
  const PARAMETROS_BASE = Object.freeze({
    d0: 0.829, custo0: 0.13, selic: 0.15, theta: 0.07, pb: -0.005,
    phi: 0.569, fatia_ipca: 0.199, fatia_cambio: 0.046,
    m: 0.268, lam: 0.20, tau: 0.0, selic0: 0.15,
    reacao: false, r_neutro: 0.05, pi0: 0.045,
    kappa: 1.0, eta: 3.0, repasse: 0.10, persist: 0.50,
  });

  function custoNaoSelicInicial(p) {
    const phiBase = PARAMETROS_BASE.phi;
    return (p.custo0 - phiBase * p.selic0) / (1 - phiBase);
  }

  function variacaoDivida(dAnt, r, theta, pb) {
    return ((r - theta) / (1 + theta)) * dAnt - pb;
  }

  function primarioEstabilizador(d, r, theta) {
    return ((r - theta) / (1 + theta)) * d;
  }

  /** Simula a dívida/PIB por `horizonte` anos (mesma ordem de operações do Python). */
  function simularDivida(parcial, horizonte = HORIZONTE) {
    const p = Object.assign({}, PARAMETROS_BASE, parcial);
    let c = custoNaoSelicInicial(p);
    let premio = 0;
    let pi = p.pi0;
    let d = p.d0;
    let cambioAcum = 0;
    const s = {
      ano: [ANO_INICIAL], divida: [d], custo: [p.custo0], theta: [p.theta],
      inflacao: [pi], premio: [0], hiato: [0], cambio: [0],
    };
    for (let t = 1; t <= horizonte; t++) {
      let hiato = 0, dep = 0, novoPremio = 0;
      if (p.reacao) {
        hiato = Math.max(0, p.r_neutro + pi - p.selic);
        dep = p.eta * hiato;
        pi = p.pi0 + p.persist * (pi - p.pi0) + p.repasse * dep;
        novoPremio = p.kappa * hiato;
      }
      premio = (1 - p.m) * premio + p.m * novoPremio;
      c = (1 - p.lam) * c + p.lam * (p.selic + p.tau);
      const surpresaPi = pi - p.pi0;
      const r = p.phi * p.selic + (1 - p.phi) * c + premio + p.fatia_ipca * surpresaPi;
      const theta = p.theta + surpresaPi;
      const efeitoCambial = (p.fatia_cambio * d * dep) / (1 + theta);
      d = d + variacaoDivida(d, r, theta, p.pb) + efeitoCambial;
      cambioAcum = (1 + cambioAcum) * (1 + dep) - 1;

      s.ano.push(ANO_INICIAL + t);
      s.divida.push(d);
      s.custo.push(r);
      s.theta.push(theta);
      s.inflacao.push(pi);
      s.premio.push(premio);
      s.hiato.push(hiato);
      s.cambio.push(cambioAcum);
    }
    const n = s.divida.length - 1;
    s.pb_estabilizador = primarioEstabilizador(s.divida[n], s.custo[n], s.theta[n]);
    return s;
  }

  /** Dívida final para cada Selic de uma grade (2% a 20%). */
  function varrerSelic(parcial, passo = 0.0025) {
    const selics = [], finais = [];
    for (let s = 0.02; s <= 0.2 + 1e-9; s += passo) {
      const sel = Math.round(s * 10000) / 10000;
      selics.push(sel);
      finais.push(simularDivida(Object.assign({}, parcial, { selic: sel })).divida[HORIZONTE]);
    }
    let iMin = 0;
    finais.forEach((v, i) => { if (v < finais[iMin]) iMin = i; });
    return { selics, finais, selicMin: selics[iMin], dividaMin: finais[iMin] };
  }

  // ------------------------------------------------------------ Fisher + Taylor (Loyo, 2017)

  /** π de equilíbrio: π = (z - r)/(1 - k). Retorna null em k = 1 (sem equilíbrio único). */
  function inflacaoEquilibrio(z, r, k) {
    if (Math.abs(1 - k) < 1e-9) return null;
    return (z - r) / (1 - k);
  }

  /**
   * Trajetória após um aperto Δz, partindo de π = π0 (z0 calibrado para que π0 seja equilíbrio).
   * Expectativas racionais: salto imediato ao novo equilíbrio.
   * Aprendizado adaptativo (π^e_t = π_{t-1}):  kπ_t + z = r + π_{t-1}  ⇒  π_t = (π_{t-1} + r - z)/k.
   */
  function trajetoriaFisherTaylor(k, dz, r = 5, pi0 = 3, periodos = 12) {
    const z0 = r + pi0 * (1 - k);
    const z1 = z0 + dz;
    const piNovo = inflacaoEquilibrio(z1, r, k);
    const racional = [pi0], adaptativa = [pi0];
    let pi = pi0;
    for (let t = 1; t <= periodos; t++) {
      racional.push(piNovo);
      pi = (pi + r - z1) / k;
      adaptativa.push(pi);
    }
    return { z0, z1, piNovo, racional, adaptativa };
  }

  /** Confere o motor contra os casos exportados pelo Python. Retorna o desvio máximo. */
  function conferirReferencia(casos) {
    let desvio = 0;
    for (const caso of casos) {
      const sim = simularDivida(caso.parametros);
      caso.divida.forEach((v, i) => { desvio = Math.max(desvio, Math.abs(v - sim.divida[i])); });
    }
    return desvio;
  }

  global.Modelo = {
    ANO_INICIAL, HORIZONTE, PARAMETROS_BASE,
    variacaoDivida, primarioEstabilizador, simularDivida, varrerSelic,
    inflacaoEquilibrio, trajetoriaFisherTaylor, conferirReferencia,
  };
})(typeof window !== "undefined" ? window : globalThis);
