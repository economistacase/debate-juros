"""Preparação da página para publicação: carimbo de versão nos arquivos estáticos.

Problema que resolve: o navegador (e o GitHub Pages, com cache de 10 minutos) pode reaproveitar um
`app.js` ou `style.css` antigo junto com um `index.html` novo. Se um `id` mudou de nome entre versões, o
script antigo quebra e os blocos interativos somem. Com o carimbo `?v=<hash do conteúdo>`, cada alteração
gera um endereço novo e o navegador é obrigado a buscar o arquivo atual.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
INDEX = DOCS / "index.html"

# referências locais a CSS/JS no index.html, com ou sem carimbo anterior
PADRAO = re.compile(r'(?P<attr>(?:href|src))="(?P<caminho>(?:css|js)/[\w.-]+\.(?:css|js))(?:\?v=[0-9a-f]+)?"')


def hash_arquivo(caminho: Path, tamanho: int = 10) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:tamanho]


def referencias(html: str) -> list[tuple[str, str | None]]:
    """[(caminho, versão carimbada ou None)] de cada CSS/JS local referenciado."""
    saida = []
    for m in re.finditer(r'(?:href|src)="((?:css|js)/[\w.-]+\.(?:css|js))(?:\?v=([0-9a-f]+))?"', html):
        saida.append((m.group(1), m.group(2)))
    return saida


def carimbar(index: Path = INDEX) -> list[str]:
    """Reescreve o index.html com ?v=<hash> em cada CSS/JS local. Devolve os arquivos carimbados."""
    html = index.read_text(encoding="utf-8")
    carimbados = []

    def troca(m: re.Match) -> str:
        arquivo = index.parent / m.group("caminho")
        if not arquivo.exists():
            raise FileNotFoundError(f"index.html referencia arquivo inexistente: {m.group('caminho')}")
        carimbados.append(m.group("caminho"))
        return f'{m.group("attr")}="{m.group("caminho")}?v={hash_arquivo(arquivo)}"'

    novo = PADRAO.sub(troca, html)
    if novo != html:
        index.write_text(novo, encoding="utf-8")
    return carimbados


if __name__ == "__main__":
    print("\n".join(carimbar()))
