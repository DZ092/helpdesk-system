"""Fábrica da aplicação.

Nada aqui é criado na importação: `create_app()` monta uma aplicação nova a
cada chamada, com a configuração que receber. É isso que permite a suíte de
testes levantar uma instância isolada, apontada para um banco em memória, sem
depender de variáveis de ambiente definidas na ordem certa.
"""

import os
import secrets
from datetime import timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template, request

from constantes import FUSO_EXIBICAO
from extensions import csrf, db, limiter, migrate
from rotas.admin import admin
from rotas.api import api
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

    # Host fixo para o redirecionamento HTTPS (ver `_forcar_https`). Vem do
    # ambiente, nunca da requisição: um `Host` forjado não pode influenciar
    # para onde o redirect aponta.
    app.config["HOST_CONFIAVEL"] = os.environ.get(
        "HOST_CONFIAVEL", "helpdesk-system-cci1.onrender.com"
    )

    # E-mail via API HTTP do Resend (não SMTP): o plano free do Render bloqueia
    # as portas SMTP (25/465/587) desde set/2025, então smtplib nunca conectava.
    # RESEND_API_KEY vem de resend.com; MAIL_REMETENTE precisa ser um remetente
    # verificado lá (ex.: onboarding@resend.dev para testes, ou um domínio seu).
    app.config["RESEND_API_KEY"] = os.environ.get("RESEND_API_KEY")
    app.config["MAIL_REMETENTE"] = os.environ.get("MAIL_REMETENTE", "onboarding@resend.dev")

    # Guarda o rate limit em memória do próprio processo — suficiente para a
    # única instância do plano gratuito do Render, e evita depender de um
    # Redis só para isso. Testes desligam o rate limit inteiro (ver
    # tests/conftest.py) em vez de usar esse armazenamento.
    app.config.setdefault("RATELIMIT_STORAGE_URI", "memory://")

    # Captcha (Cloudflare Turnstile) nos formulários públicos. A Site Key é
    # pública — vai para o HTML dos templates sem problema. Sem a Secret Key
    # configurada, `TURNSTILE_ENABLED` nasce False e os formulários seguem
    # funcionando normalmente, só sem essa camada extra — é o caso do
    # desenvolvimento local de quem não tem chave própria configurada.
    app.config["TURNSTILE_SITE_KEY"] = os.environ.get("TURNSTILE_SITE_KEY")
    app.config["TURNSTILE_SECRET_KEY"] = os.environ.get("TURNSTILE_SECRET_KEY")
    app.config.setdefault("TURNSTILE_ENABLED", bool(app.config.get("TURNSTILE_SECRET_KEY")))

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

    @app.before_request
    def _gerar_nonce_csp():
        """Um valor aleatório novo por requisição, para liberar só os
        scripts que a própria aplicação serviu.

        Sem isso o Content-Security-Policy exigiria 'unsafe-inline' no
        script-src, que anula a proteção contra injeção de script que o CSP
        existe para dar — qualquer script injetado por um ataque de XSS
        rodaria igual. Com o nonce, cada `<script>` da própria aplicação
        carrega esse valor (função `csp_nonce()`, registrada mais abaixo) e
        só ele é aceito; um script injetado não tem como adivinhar o valor
        de uma requisição que ainda nem existia.
        """
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.before_request
    def _forcar_https():
        """Redireciona para HTTPS quando a aplicação espera servir por HTTPS.

        O Render termina o TLS antes da aplicação: a requisição chega ao
        Flask como HTTP simples, e o proxy anota o esquema original em
        X-Forwarded-Proto. Sem ProxyFix, `request.is_secure` não reflete
        isso — por isso a checagem lê o cabeçalho direto. Usa a mesma flag
        de `SESSION_COOKIE_SECURE`: só faz sentido exigir HTTPS quando a
        aplicação já está configurada para servir por HTTPS (produção); em
        desenvolvimento local, sem essa flag, o redirecionamento fica
        desligado para não atrapalhar quem roda `flask run` em HTTP puro.

        A URL de destino usa `HOST_CONFIAVEL` (config, vindo do ambiente) em
        vez do host da própria requisição: um `Host` forjado pelo cliente
        nunca decide para onde o redirect aponta — só o caminho e a
        querystring vêm da requisição, o domínio é sempre o nosso.

        A regra é deliberadamente restrita: só redireciona quando o cabeçalho
        existe E diz "http". Cabeçalho ausente significa que não dá para saber
        o esquema de origem, e redirecionar nesse caso é justamente o que
        derrubou a produção em 16/09/2026 — o Waitress apagava o cabeçalho
        (ver `opcoes_de_proxy` em serve.py), a aplicação assumia HTTP e
        redirecionava para a mesma URL infinitamente (ERR_TOO_MANY_REDIRECTS).
        Na dúvida, servir a página é sempre melhor que entrar em loop.

        Não é preciso tratar o cabeçalho com vários valores ("https, http",
        que acontece quando cada proxy anexa em vez de substituir): o próprio
        Waitress recusa essa requisição com 400 antes de chegar aqui.
        """
        if not app.config.get("SESSION_COOKIE_SECURE"):
            return None

        if request.headers.get("X-Forwarded-Proto") != "http":
            return None

        caminho = request.full_path if request.query_string else request.path
        url_https = f"https://{app.config['HOST_CONFIAVEL']}{caminho}"
        return redirect(url_https, code=308)

    @app.after_request
    def _headers_de_seguranca(resposta):
        """Cabeçalhos HTTP de segurança que o Flask não define por padrão.

        Nenhum sozinho impede um ataque — são instruções para o navegador não
        fazer coisas que abrem brecha: não deixar a página entrar num
        <iframe> de outro site (clickjacking), não tentar adivinhar o tipo de
        um arquivo servido (MIME sniffing) e não vazar a URL completa como
        referrer para outro site. Content-Security-Policy fica de fora por
        enquanto: os templates têm um <script> inline de propósito (evita
        piscar no tema errado antes do CSS carregar — ver tema.js) e um CSP
        correto exigiria nonce por requisição em cada um deles — capítulo
        separado.
        """
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if app.config.get("SESSION_COOKIE_SECURE"):
            # Mesma flag que endurece o cookie de sessão: só faz sentido pedir
            # HTTPS na próxima visita quando a aplicação já está servindo por
            # HTTPS.
            resposta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content-Security-Policy — cada diretiva libera só o que a aplicação
        # de fato usa: 'self' para tudo que ela mesma serve, o nonce da
        # requisição para os scripts inline (ver `_gerar_nonce_csp`), a fonte
        # do Google Fonts que o CSS importa, e o domínio do Cloudinary para
        # as imagens dos anexos (a URL do anexo aponta pra lá, não pro
        # próprio servidor). frame-ancestors 'none' é a versão do CSP do
        # X-Frame-Options acima — mantemos os dois porque nem todo navegador
        # antigo entende frame-ancestors.
        nonce = g.get("csp_nonce", "")
        resposta.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://challenges.cloudflare.com; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data: https://res.cloudinary.com; "
            "connect-src 'self'; "
            "frame-src https://challenges.cloudflare.com; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        return resposta

    app.jinja_env.globals["csp_nonce"] = lambda: g.get("csp_nonce", "")

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

    @app.errorhandler(403)
    def erro_403(excecao):
        return render_template(
            "erro.html", codigo=403, mensagem="Você não tem permissão para acessar esta página."
        ), 403

    @app.errorhandler(404)
    def erro_404(excecao):
        return render_template(
            "erro.html", codigo=404, mensagem="Esta página não existe ou foi removida."
        ), 404

    @app.errorhandler(429)
    def erro_429(excecao):
        return render_template(
            "erro.html",
            codigo=429,
            mensagem="Muitas tentativas em pouco tempo. Aguarde um minuto e tente de novo.",
        ), 429

    @app.errorhandler(500)
    def erro_500(excecao):
        # O SQLAlchemy deixa a sessão "suja" depois de uma exceção não tratada
        # (uma transação pendente, por exemplo); sem o rollback, a primeira
        # consulta da próxima requisição herdaria esse estado e falharia
        # também, mesmo sendo uma requisição sem nenhum problema.
        db.session.rollback()
        return render_template(
            "erro.html", codigo=500, mensagem="Algo deu errado do nosso lado. Tente novamente em instantes."
        ), 500


def create_app(ajustes=None):
    """Monta uma aplicação pronta para servir."""
    app = Flask(__name__)

    _configurar(app, ajustes or {})

    db.init_app(app)
    csrf.init_app(app)

    # Os padrões do Flask-Migrate já servem aqui: `render_as_batch` recria a
    # tabela quando o SQLite não sabe executar o ALTER pedido (ele só aceita
    # uma fração do comando), e `compare_type` faz o autogenerate enxergar
    # troca de tipo de coluna, não só coluna que entrou ou saiu.
    migrate.init_app(app, db)
    limiter.init_app(app)

    app.register_blueprint(auth)
    app.register_blueprint(chamados)
    app.register_blueprint(admin)
    app.register_blueprint(api)

    # A API se autentica por token no cabeçalho, não por cookie de sessão — e é
    # a sessão em cookie que torna um endpoint vulnerável a CSRF (o navegador
    # anexa o cookie sozinho a qualquer requisição, de qualquer origem). Sem
    # esse mecanismo ambiente, o token de CSRF não protege nada aqui e só
    # atrapalharia um cliente que nunca terá acesso a ele.
    csrf.exempt(api)

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
