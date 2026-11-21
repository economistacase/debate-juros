"""Integridade estática da página: ids usados no JS existem no HTML e os arquivos estão carimbados."""
import re
from pathlib import Path

import pytest

from src import publicacao

DOCS = Path(__file__).resolve().parents[1] / "docs"
HTML = (DOCS / "index.html").read_text(encoding="utf-8")
IDS_HTML = set(re.findall(r'\bid="([\w-]+)"', HTML))
# ids criados pelo próprio JS em tempo de execução
DINAMICOS = re.compile(r"^g-r-")


@pytest.mark.parametrize("arquivo", sorted(p.name for p in (DOCS / "js").glob("*.js")))
def test_ids_do_js_existem_no_html(arquivo):
    js = (DOCS / "js" / arquivo).read_text(encoding="utf-8")
    usados = set(re.findall(r'\$\("([\w-]+)"\)', js)) | set(re.findall(r'getElementById\("([\w-]+)"\)', js))
    faltando = sorted(i for i in usados if i not in IDS_HTML and not DINAMICOS.match(i))
    assert not faltando, f"{arquivo} usa ids ausentes do index.html: {faltando}"


def test_scripts_e_estilos_locais_existem_e_estao_carimbados():
    refs = publicacao.referencias(HTML)
    nomes = {c for c, _ in refs}
    assert {"css/style.css", "js/modelo.js", "js/app.js", "js/dados.js", "js/pagina.js"} <= nomes
    for caminho, versao in refs:
        arquivo = DOCS / caminho
        assert arquivo.exists(), caminho
        assert versao == publicacao.hash_arquivo(arquivo), \
            f"{caminho} desatualizado no index.html: rode `python build.py` para recarimbar"


def test_ids_unicos():
    ids = re.findall(r'\bid="([\w-]+)"', HTML)
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    assert not repetidos, f"ids repetidos: {repetidos}"
