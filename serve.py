"""Sobe a aplicação com o Waitress, um servidor WSGI de produção.

O `python app.py` usa o servidor embutido do Flask, que existe só para
desenvolvimento: atende uma requisição por vez, expõe páginas de erro
detalhadas e não foi endurecido para ficar acessível a estranhos — por isso ele
mesmo avisa isso no terminal a cada inicialização.

Este script serve a mesma aplicação pelo Waitress, que é multithread, roda no
Windows sem depender de nada além do Python e não imprime aquele aviso.

    python serve.py

Host, porta e número de threads vêm do ambiente (`.env`), com padrões seguros.
O `127.0.0.1` aceita conexões apenas desta máquina; para alcançar a aplicação
de outro aparelho da rede local, defina `HOST=0.0.0.0` — e faça isso só em rede
confiável, porque a aplicação passa a responder a qualquer um que a alcance.
"""

import os

from waitress import serve

from app import create_app


def main():
    # O esquema é responsabilidade das migrações, não deste script: o build do
    # Render roda `flask db upgrade` antes de chamar o serve.py, e localmente o
    # comando é o mesmo. Por isso aqui não há `db.create_all()`.
    app = create_app()

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    threads = int(os.environ.get("THREADS", "4"))

    print(f"Waitress servindo em http://{host}:{port} ({threads} threads)")
    print("Ctrl+C para encerrar.")

    serve(app, host=host, port=port, threads=threads)


if __name__ == "__main__":
    main()
