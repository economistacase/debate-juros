"""Orquestra o projeto: dados (opcional), cenários teóricos, carimbo de versão, testes e verificação no navegador.

Uso:
    python build.py                    # cenários + carimbo + testes + verificação no Chrome (se disponível)
    python build.py --dados            # baixa também os dados do BCB/Focus (requer internet)
    python build.py --sem-navegador    # pula a verificação no Chrome
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    from src.teoria import regimes_tfnp
    from src.dados import nota
    from src import publicacao

    if "--dados" in sys.argv:
        from src.dados import bcb, nota_bcb
        print("== 0/4  Lendo a Nota de Estatísticas Fiscais mais recente (BCB)")
        r = nota_bcb.atualizar()
        print("   " + ", ".join(f"{k}={v}" for k, v in r.items()))
        print("== 0/4  Baixando dados do BCB (SGS + Focus)")
        destino = bcb.exportar()
        print(f"   ok: {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1024:.0f} KB)")
        from src.empirico import onda2
        print("== 0/4  Onda 2: Tesouro Direto, Focus e Copom (estimativa de γ e eventos)")
        print(f"   ok: {onda2.exportar(renovar=True).relative_to(RAIZ)}")

    print("== 1/4  Nota Fiscal e cenários teóricos")
    print(f"   ok: {nota.publicar().relative_to(RAIZ)}")
    destino = regimes_tfnp.exportar()
    print(f"   ok: {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1024:.1f} KB)")
    from src.teoria import transmissao
    print(f"   ok: {transmissao.exportar().relative_to(RAIZ)}")

    print("== 2/4  Carimbo de versão nos CSS/JS (evita cache antigo no navegador)")
    for arq in publicacao.carimbar_todas():
        print(f"   ok: {arq}")

    print("== 3/4  Testes de consistência", flush=True)
    codigo = subprocess.call([sys.executable, "-m", "pytest", "-q", "tests"], cwd=RAIZ)
    if codigo != 0:
        return codigo

    if "--sem-navegador" not in sys.argv:
        print("== 4/4  Verificação da página no navegador", flush=True)
        codigo = subprocess.call([sys.executable, str(RAIZ / "tools" / "verificar_pagina.py")], cwd=RAIZ)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
