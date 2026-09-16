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


def opcoes_de_proxy():
    """Ajustes do Waitress para quando a aplicação roda atrás de um proxy.

    O Waitress 3 vem com `clear_untrusted_proxy_headers` ligado: sem declarar
    um proxy confiável, ele APAGA os cabeçalhos `X-Forwarded-*` antes de
    entregar a requisição ao Flask. É uma proteção correta — impede que um
    cliente qualquer forje o esquema ou o IP de origem — mas em produção ela
    apagava justamente o `X-Forwarded-Proto` que o `_forcar_https` precisa ler,
    e a aplicação passava a redirecionar para sempre (ERR_TOO_MANY_REDIRECTS).

    A mesma flag que marca produção no resto do projeto decide aqui: com
    `SESSION_COOKIE_SECURE` ligada, a aplicação está atrás do proxy do Render
    (que por sua vez está atrás do Cloudflare) e só é alcançável através dele,
    então confiar nos cabeçalhos é seguro. Em desenvolvimento a flag fica
    desligada, não há proxy nenhum, e o Waitress segue limpando tudo.
    """
    if os.environ.get("SESSION_COOKIE_SECURE", "0") != "1":
        return {}

    return {
        "trusted_proxy": "*",
        "trusted_proxy_headers": {
            "x-forwarded-proto",
            "x-forwarded-for",
            "x-forwarded-host",
        },
    }


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

    serve(app, host=host, port=port, threads=threads, **opcoes_de_proxy())


if __name__ == "__main__":
    main()
