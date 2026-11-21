"""Orquestra a Onda 1: gera os cenários teóricos e roda a suíte de testes.

Uso:  python build.py
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    from src.teoria import regimes_tfnp

    print("== 1/2  Gerando cenários teóricos")
    destino = regimes_tfnp.exportar()
    print(f"   ok: {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1024:.1f} KB)")

    print("== 2/2  Rodando testes de consistência")
    return subprocess.call([sys.executable, "-m", "pytest", "-q", "tests"], cwd=RAIZ)


if __name__ == "__main__":
    sys.exit(main())
