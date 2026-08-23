"""Fábrica da aplicação.

Nada aqui é criado na importação: `create_app()` monta uma aplicação nova a
cada chamada, com a configuração que receber. É isso que permite a suíte de
testes levantar uma instância isolada, apontada para um banco em memória, sem
depender de variáveis de ambiente definidas na ordem certa.
"""

import os
from datetime import timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, g

from constantes import FUSO_EXIBICAO
from extensions import csrf, db, mail, migrate
from rotas.admin import admin
from rotas.auth import auth
from rotas.chamados import chamados
from seguranca import usuario_atual

load_dotenv()


def _url_do_banco():
    """URL do banco, com o esquema que o SQLAlchemy 2 aceita.

    Provedores de PostgreSQL gerenciado (Render, Neon, Heroku) entregam a URL
    começando com `postgres://`, um esquema que o SQLAlchemy 2 removeu. Sem
    esta troca a aplicação sobe normalmente e só quebra na primeira consulta —
    é o tropeço clássico do primeiro deploy.
    """
    url = os.environ.get("DATABASE_URL", "sqlite:///chamados.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _configurar(app, ajustes):
    """Preenche a configuração a partir do ambiente e aplica os ajustes."""
    app.config["SQLALCHEMY_DATABASE_URI"] = _url_do_banco()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

    # Endurecimento do cookie de sessão.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]

    # Os ajustes vêm por último para poderem sobrescrever qualquer padrão —
    # é assim que os testes trocam o banco e a chave sem tocar no ambiente.
    app.config.update(ajustes)

    # A SECRET_KEY assina o cookie de sessão. Sem uma chave imprevisível,
    # qualquer pessoa consegue forjar uma sessão de Administrador — por isso a
    # aplicação se recusa a subir sem ela em vez de cair num valor conhecido.
    if not app.config.get("SECRET_KEY"):
        if os.environ.get("FLASK_ENV") == "development" or app.config.get("TESTING"):
            app.config["SECRET_KEY"] = "chave-apenas-para-desenvolvimento"
        else:
            raise RuntimeError(
                "SECRET_KEY não definida. Crie um arquivo .env com uma chave gerada por "
                "`python -c \"import secrets; print(secrets.token_hex(32))\"`."
            )


def _registrar_ganchos(app):
    """Filtro de template e ganchos de requisição que valem para o app inteiro."""

    @app.template_filter("data_local")
    def formatar_data_local(valor, formato="%d/%m/%Y às %H:%M"):
        """Converte um datetime UTC do banco para o horário de Brasília."""
        if valor is None:
            return "—"
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(FUSO_EXIBICAO).strftime(formato)

    @app.before_request
    def _limpar_cache_usuario():
        """Zera o cache de `usuario_atual()` no início de cada requisição.

        O `g` costuma nascer vazio a cada requisição, mas o Flask reaproveita um
        contexto de aplicação já ativo (é o que acontece nos testes), e aí o
        usuário ficaria preso entre requisições. Limpar aqui torna a releitura
        do banco garantida em qualquer cenário.
        """
        g.pop("usuario", None)

    @app.context_processor
    def injetar_usuario():
        """Deixa `usuario_logado` disponível em todos os templates."""
        return {"usuario_logado": usuario_atual()}


def create_app(ajustes=None):
    """Monta uma aplicação pronta para servir."""
    app = Flask(__name__)

    _configurar(app, ajustes or {})

    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # Os padrões do Flask-Migrate já servem aqui: `render_as_batch` recria a
    # tabela quando o SQLite não sabe executar o ALTER pedido (ele só aceita
    # uma fração do comando), e `compare_type` faz o autogenerate enxergar
    # troca de tipo de coluna, não só coluna que entrou ou saiu.
    migrate.init_app(app, db)

    app.register_blueprint(auth)
    app.register_blueprint(chamados)
    app.register_blueprint(admin)

    _registrar_ganchos(app)

    return app


if __name__ == "__main__":
    aplicacao = create_app()

    # O esquema do banco pertence às migrações. Numa cópia recém-clonada, rode
    # `flask db upgrade` uma vez antes de subir a aplicação: criar as tabelas
    # aqui com `db.create_all()` deixaria o banco sem registro de versão, e a
    # primeira migração futura tentaria criar o que já existe.
    #
    # O debugger do Werkzeug permite execução remota de código: ele só pode
    # ligar quando explicitamente pedido pelo ambiente, nunca por padrão.
    aplicacao.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
