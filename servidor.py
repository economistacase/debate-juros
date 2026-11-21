"""Servidor local para validar a página sem cache do navegador.

Uso:  python servidor.py            (http://localhost:8000)
      python servidor.py 8080

Diferente de `python -m http.server`, envia `Cache-Control: no-store`, então cada recarga busca
os arquivos atuais. Evita ver uma mistura de HTML novo com JS/CSS antigos durante o desenvolvimento.
"""
import functools
import http.server
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent / "docs"


class SemCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()


def main() -> None:
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    manipulador = functools.partial(SemCache, directory=str(DOCS))
    with http.server.ThreadingHTTPServer(("", porta), manipulador) as srv:
        print(f"Servindo {DOCS} em http://localhost:{porta} (sem cache). Ctrl+C para parar.")
        srv.serve_forever()


if __name__ == "__main__":
    main()
