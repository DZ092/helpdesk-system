import hashlib
import hmac
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, render_template, request, session
from flask_mail import Message
from werkzeug.security import check_password_hash, generate_password_hash

from constantes import (
    FUSO_EXIBICAO,
    JANELA_BLOQUEIO_LOGIN_SEGUNDOS,
    JANELA_BLOQUEIO_SEGUNDOS,
    MAX_TENTATIVAS_LOGIN,
    MAX_TENTATIVAS_SENHA,
    PERFIS_TECNICOS,
    PRIORIDADES,
    SENHAS_PROIBIDAS,
    STATUS_CHAMADO,
    TAMANHO_MINIMO_SENHA,
    TIPOS_USUARIO,
)
from extensions import csrf, db, mail
from models import Chamado, Comentario, LogAuditoria, Usuario

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///chamados.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# A SECRET_KEY assina o cookie de sessão. Sem uma chave secreta e imprevisível,
# qualquer pessoa consegue forjar uma sessão de Administrador — por isso a
# aplicação se recusa a subir sem ela em vez de cair num valor padrão conhecido.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    if os.environ.get("FLASK_ENV") == "development" or app.config.get("TESTING"):
        app.config["SECRET_KEY"] = "chave-apenas-para-desenvolvimento"
    else:
        raise RuntimeError(
            "SECRET_KEY não definida. Crie um arquivo .env com uma chave gerada por "
            "`python -c \"import secrets; print(secrets.token_hex(32))\"`."
        )

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

db.init_app(app)
mail.init_app(app)
csrf.init_app(app)


@app.template_filter("data_local")
def formatar_data_local(valor, formato="%d/%m/%Y às %H:%M"):
    """Converte um datetime UTC do banco para o horário de Brasília."""
    if valor is None:
        return "—"
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(FUSO_EXIBICAO).strftime(formato)


# ==============================================================================
# USUÁRIO DA REQUISIÇÃO E CONTROLE DE ACESSO
# ==============================================================================
def impressao_sessao(usuario):
    """Assinatura da sessão, derivada do hash da senha.

    Guardada no cookie e conferida a cada requisição. Como o valor deriva do
    hash da senha, trocar a senha muda a assinatura e derruba automaticamente
    todas as sessões abertas em outros dispositivos — que é justamente o que se
    espera de uma troca de senha feita porque a antiga vazou.

    É um HMAC com a SECRET_KEY: o cookie carrega só o resultado, nunca o hash
    da senha em si.
    """
    return hmac.new(
        app.config["SECRET_KEY"].encode(),
        usuario.senha.encode(),
        hashlib.sha256,
    ).hexdigest()


def usuario_atual():
    """Usuário logado, sempre relido do banco.

    O perfil não pode sair da sessão: o cookie é escrito no login e nunca mais
    revisado, então um técnico rebaixado a Usuário — ou uma conta já excluída —
    continuaria com os privilégios antigos até fazer logout. Lendo do banco a
    cada requisição, qualquer mudança de perfil vale imediatamente.
    """
    if "usuario" not in g:
        usuario_id = session.get("usuario_id")
        usuario = db.session.get(Usuario, usuario_id) if usuario_id else None

        # Conta excluída, ou senha trocada desde que esta sessão foi criada.
        if usuario is not None and not hmac.compare_digest(
            session.get("auth", ""), impressao_sessao(usuario)
        ):
            usuario = None

        if usuario_id and usuario is None:
            session.clear()

        g.usuario = usuario
    return g.usuario


@app.before_request
def _limpar_cache_usuario():
    """Zera o cache de `usuario_atual()` no início de cada requisição.

    O `g` costuma nascer vazio a cada requisição, mas o Flask reaproveita um
    contexto de aplicação já ativo (é o que acontece nos testes), e aí o
    usuário ficaria preso entre requisições. Limpar aqui torna a releitura do
    banco garantida em qualquer cenário.
    """
    g.pop("usuario", None)


@app.context_processor
def injetar_usuario():
    """Deixa `usuario_logado` disponível em todos os templates."""
    return {"usuario_logado": usuario_atual()}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if usuario_atual() is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def tecnico_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = usuario_atual()
        if usuario is None:
            return redirect("/login")
        if not usuario.eh_tecnico:
            flash("Essa ação é restrita a Técnicos e Administradores.")
            return redirect("/chamados")
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = usuario_atual()
        if usuario is None:
            return redirect("/login")
        if not usuario.eh_admin:
            flash("Essa área é restrita a Administradores.")
            return redirect("/dashboard")
        return f(*args, **kwargs)

    return decorated_function


# ==============================================================================
# REGISTRO DE LOGS E AUDITORIA
# ==============================================================================
def registrar_log(acao, detalhes=None):
    usuario = usuario_atual()
    log = LogAuditoria(
        usuario_id=usuario.id if usuario else None,
        usuario_nome=usuario.nome if usuario else "Público",
        acao=acao,
        detalhes=detalhes,
    )
    db.session.add(log)
    db.session.commit()


# ==============================================================================
# NOTIFICAÇÕES POR E-MAIL
# ==============================================================================
def _enviar_em_segundo_plano(app_obj, mensagem):
    with app_obj.app_context():
        try:
            mail.send(mensagem)
            app_obj.logger.info("E-mail de notificação enviado.")
        except Exception:
            app_obj.logger.exception("Falha ao enviar e-mail de notificação.")


def notificar_tecnicos_novo_chamado(chamado):
    """Avisa técnicos e administradores sobre um chamado novo.

    O envio vai para uma thread separada de propósito: a abertura de chamado é
    pública e ficava presa esperando o SMTP responder, então um servidor de
    e-mail lento ou fora do ar travava a página do usuário por minutos.
    """
    tecnicos = (
        db.session.execute(
            db.select(Usuario).where(Usuario.tipo_usuario.in_(PERFIS_TECNICOS))
        )
        .scalars()
        .all()
    )

    if not app.config.get("MAIL_USERNAME"):
        app.logger.warning("MAIL_USERNAME não configurado — notificação não enviada.")
        return

    # A conta que envia não precisa receber cópia do próprio aviso. Como ela
    # costuma estar cadastrada como Administrador para poder atender chamados,
    # sem esse filtro o sistema mandaria e-mail dela para ela mesma.
    remetente = app.config["MAIL_USERNAME"].strip().lower()
    destinatarios = [
        tecnico.email for tecnico in tecnicos if tecnico.email.strip().lower() != remetente
    ]

    if not destinatarios:
        app.logger.info("Nenhum destinatário para notificar — e-mail não enviado.")
        return

    corpo = (
        f"Novo chamado aberto no Help Desk!\n\n"
        f"Título: {chamado.titulo}\n"
        f"Usuário: {chamado.usuario}\n"
        f"Setor: {chamado.setor}\n"
        f"Prioridade: {chamado.prioridade}\n\n"
        f"Descrição:\n{chamado.descricao}\n\n"
        f"Acesse o sistema para ver mais detalhes e atender o chamado."
    )

    mensagem = Message(
        subject=f"[Help Desk] Novo chamado: {chamado.titulo}",
        recipients=destinatarios,
        body=corpo,
    )

    threading.Thread(
        target=_enviar_em_segundo_plano,
        args=(app, mensagem),
        daemon=True,
    ).start()


# ==============================================================================
# HELPERS DE VALIDAÇÃO
# ==============================================================================
def campo_obrigatorio(nome, tamanho_maximo):
    """Lê um campo do formulário, remove espaços e corta no tamanho da coluna."""
    valor = request.form.get(nome, "").strip()
    return valor[:tamanho_maximo]


def inteiro_ou_none(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def validar_forca_senha(senha, usuario=None):
    """Devolve uma mensagem de erro, ou None se a senha for aceitável.

    As regras cobrem o que costuma quebrar senha de sistema interno: curta
    demais, previsível, ou derivada do próprio nome/e-mail — que é a primeira
    coisa que alguém tenta.
    """
    if len(senha) < TAMANHO_MINIMO_SENHA:
        return f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres."

    if len(senha) > 128:
        # Limite de sanidade: hashes de senhas gigantes só consomem CPU à toa.
        return "A senha pode ter no máximo 128 caracteres."

    if senha.lower() in SENHAS_PROIBIDAS:
        return "Essa senha é comum demais. Escolha outra."

    if senha.isdigit():
        return "A senha não pode ser só números."

    if senha.isalpha():
        return "A senha precisa ter pelo menos um número ou símbolo."

    if len(set(senha)) < 4:
        return "A senha tem caracteres repetidos demais. Escolha outra."

    if usuario is not None:
        # Só pedaços de 4+ caracteres: um e-mail como "a@x.com" tem parte local
        # de uma letra, e comparar com ela reprovaria quase toda senha válida.
        pedacos = [usuario.email.split("@")[0]] + usuario.nome.split()
        pedacos = [p.lower() for p in pedacos if len(p) >= 4]
        if any(pedaco in senha.lower() for pedaco in pedacos):
            return "A senha não pode conter seu nome nem seu e-mail."

    return None


# Tentativas erradas da senha atual, por usuário: {id: [timestamps]}.
# Guardado em memória de propósito — é simples e suficiente para um processo
# único. Num deploy com vários workers, isso precisa ir para Redis ou banco
# (ver a recomendação de rate limiting no README).
_tentativas_senha = {}


def registrar_tentativa_senha(usuario_id):
    agora = time.monotonic()
    tentativas = [
        t for t in _tentativas_senha.get(usuario_id, []) if agora - t < JANELA_BLOQUEIO_SEGUNDOS
    ]
    tentativas.append(agora)
    _tentativas_senha[usuario_id] = tentativas


def segundos_de_bloqueio(usuario_id):
    """Quantos segundos faltam para liberar. Zero se não estiver bloqueado."""
    agora = time.monotonic()
    tentativas = [
        t for t in _tentativas_senha.get(usuario_id, []) if agora - t < JANELA_BLOQUEIO_SEGUNDOS
    ]
    _tentativas_senha[usuario_id] = tentativas

    if len(tentativas) < MAX_TENTATIVAS_SENHA:
        return 0
    return int(JANELA_BLOQUEIO_SEGUNDOS - (agora - tentativas[0])) + 1


def limpar_tentativas_senha(usuario_id):
    _tentativas_senha.pop(usuario_id, None)


# Tentativas de login com senha errada, por e-mail: {email: [timestamps]}.
# Mesma limitação do dicionário acima: em memória, serve para um processo
# único (ver a recomendação de rate limiting no README).
_tentativas_login = {}


def registrar_tentativa_login(email):
    agora = time.monotonic()
    tentativas = [
        t for t in _tentativas_login.get(email, []) if agora - t < JANELA_BLOQUEIO_LOGIN_SEGUNDOS
    ]
    tentativas.append(agora)
    _tentativas_login[email] = tentativas


def segundos_de_bloqueio_login(email):
    """Quantos segundos faltam para liberar. Zero se não estiver bloqueado."""
    agora = time.monotonic()
    tentativas = [
        t for t in _tentativas_login.get(email, []) if agora - t < JANELA_BLOQUEIO_LOGIN_SEGUNDOS
    ]
    _tentativas_login[email] = tentativas

    if len(tentativas) < MAX_TENTATIVAS_LOGIN:
        return 0
    return int(JANELA_BLOQUEIO_LOGIN_SEGUNDOS - (agora - tentativas[0])) + 1


def limpar_tentativas_login(email):
    _tentativas_login.pop(email, None)


# ==============================================================================
# ROTAS DA APLICAÇÃO
# ==============================================================================
@app.route("/")
def home():
    return redirect("/dashboard")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = campo_obrigatorio("nome", 100)
        email = campo_obrigatorio("email", 120).lower()
        senha = request.form.get("senha", "")

        if not nome or not email:
            return render_template("cadastro.html", erro="Preencha nome e e-mail.")

        if len(senha) < TAMANHO_MINIMO_SENHA:
            return render_template(
                "cadastro.html",
                erro=f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.",
            )

        usuario_existente = db.session.execute(
            db.select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()

        if usuario_existente:
            return render_template("cadastro.html", erro="Este e-mail já está cadastrado.")

        # O perfil NUNCA vem do formulário. O cadastro é aberto ao público, então
        # aceitar `tipo_usuario` do cliente deixaria qualquer visitante criar a
        # própria conta de Administrador. Promoção de perfil é feita só pelo
        # painel administrativo (ou pelo script promover_admin.py no primeiro uso).
        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha=generate_password_hash(senha),
            tipo_usuario="Usuário",
        )
        db.session.add(novo_usuario)
        db.session.commit()
        registrar_log("Cadastro de usuário", f"Novo usuário: {novo_usuario.email}")
        flash("Conta criada com sucesso! Faça login para continuar.")
        return redirect("/login")
    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        bloqueio = segundos_de_bloqueio_login(email)
        if bloqueio:
            registrar_log("Login bloqueado", f"Excesso de tentativas para {email}")
            return render_template(
                "login.html",
                erro=f"Tentativas demais. Tente de novo em {bloqueio // 60 + 1} minuto(s).",
            )

        usuario = db.session.execute(
            db.select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()

        if usuario and check_password_hash(usuario.senha, senha):
            limpar_tentativas_login(email)
            # Troca o identificador de sessão no login para evitar fixação de sessão.
            session.clear()
            session["usuario_id"] = usuario.id
            session["auth"] = impressao_sessao(usuario)
            session.permanent = True
            g.usuario = usuario
            registrar_log("Login realizado")
            return redirect("/dashboard")

        registrar_tentativa_login(email)

        # Mensagem genérica de propósito: dizer "e-mail não existe" permitiria
        # descobrir quais endereços estão cadastrados no sistema.
        return render_template("login.html", erro="E-mail ou senha inválidos.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/senha", methods=["GET", "POST"])
@login_required
def alterar_senha():
    """Troca de senha do próprio usuário."""
    usuario = usuario_atual()

    if request.method == "POST":
        bloqueio = segundos_de_bloqueio(usuario.id)
        if bloqueio:
            registrar_log(
                "Troca de senha bloqueada",
                f"Excesso de tentativas para {usuario.email}",
            )
            return render_template(
                "alterar_senha.html",
                erro=f"Tentativas demais. Tente de novo em {bloqueio // 60 + 1} minuto(s).",
            )

        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmacao = request.form.get("confirmacao", "")

        # Confirmar a senha atual impede que alguém com a sessão sequestrada
        # (ou um computador destravado) troque a senha e tome a conta.
        if not check_password_hash(usuario.senha, senha_atual):
            registrar_tentativa_senha(usuario.id)
            registrar_log("Senha atual incorreta", f"Tentativa de troca por {usuario.email}")
            return render_template("alterar_senha.html", erro="Senha atual incorreta.")

        if nova_senha != confirmacao:
            return render_template(
                "alterar_senha.html", erro="A nova senha e a confirmação não conferem."
            )

        if check_password_hash(usuario.senha, nova_senha):
            return render_template(
                "alterar_senha.html", erro="A nova senha precisa ser diferente da atual."
            )

        problema = validar_forca_senha(nova_senha, usuario)
        if problema:
            return render_template("alterar_senha.html", erro=problema)

        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()

        limpar_tentativas_senha(usuario.id)
        registrar_log("Senha alterada", f"Senha alterada por {usuario.email}")

        # A assinatura da sessão deriva do hash da senha, então trocar a senha
        # invalidou todas as sessões — inclusive esta. Reemitimos a desta aba
        # para o usuário não ser expulso logo depois de acertar tudo; as demais
        # continuam derrubadas.
        session.clear()
        session["usuario_id"] = usuario.id
        session["auth"] = impressao_sessao(usuario)
        session.permanent = True

        flash("Senha alterada com sucesso. As sessões em outros dispositivos foram encerradas.")
        return redirect("/dashboard")

    return render_template("alterar_senha.html")


@app.route("/dashboard")
@login_required
def dashboard():
    # Uma única consulta agrupada no lugar de quatro COUNT separados.
    contagens = dict(
        db.session.execute(
            db.select(Chamado.status, db.func.count(Chamado.id)).group_by(Chamado.status)
        ).all()
    )

    chamados = (
        db.session.execute(db.select(Chamado).order_by(Chamado.id.desc()).limit(5))
        .scalars()
        .all()
    )

    return render_template(
        "dashboard.html",
        total=sum(contagens.values()),
        abertos=contagens.get("Aberto", 0),
        andamento=contagens.get("Em andamento", 0),
        resolvidos=contagens.get("Resolvido", 0),
        chamados=chamados,
    )


@app.route("/chamado", methods=["GET", "POST"])
def chamado():
    if request.method == "POST":
        usuario = campo_obrigatorio("usuario", 100)
        setor = campo_obrigatorio("setor", 100)
        titulo = campo_obrigatorio("titulo", 200)
        descricao = request.form.get("descricao", "").strip()
        prioridade = request.form.get("prioridade", "Média")

        if not all((usuario, setor, titulo, descricao)):
            return render_template(
                "chamado.html", erro="Preencha todos os campos do chamado."
            )

        # Sem essa checagem, qualquer valor enviado no formulário era gravado
        # como prioridade e escapava dos filtros e das cores da interface.
        if prioridade not in PRIORIDADES:
            prioridade = "Média"

        novo_chamado = Chamado(
            usuario=usuario,
            setor=setor,
            titulo=titulo,
            descricao=descricao,
            status="Aberto",
            prioridade=prioridade,
        )
        db.session.add(novo_chamado)
        db.session.commit()
        registrar_log("Abertura de chamado", f"Chamado #{novo_chamado.id}: {novo_chamado.titulo}")
        notificar_tecnicos_novo_chamado(novo_chamado)
        flash("Chamado enviado com sucesso! Nossa equipe vai analisar em breve.")
        return redirect("/chamado")
    return render_template("chamado.html")


@app.route("/chamados")
@login_required
def lista_chamados():
    busca = request.args.get("busca", "").strip()
    status_filtro = request.args.get("status", "")
    prioridade_filtro = request.args.get("prioridade", "")
    setor_filtro = request.args.get("setor", "")
    responsavel_filtro = request.args.get("responsavel", "")
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")
    pagina = request.args.get("pagina", 1, type=int)

    stmt = db.select(Chamado)

    if busca:
        stmt = stmt.where(Chamado.titulo.ilike(f"%{busca}%"))

    if status_filtro in STATUS_CHAMADO:
        stmt = stmt.where(Chamado.status == status_filtro)

    if prioridade_filtro in PRIORIDADES:
        stmt = stmt.where(Chamado.prioridade == prioridade_filtro)

    if setor_filtro:
        stmt = stmt.where(Chamado.setor == setor_filtro)

    if responsavel_filtro == "nenhum":
        stmt = stmt.where(Chamado.responsavel_id.is_(None))
    elif responsavel_filtro:
        # `?responsavel=abc` derrubava a página com erro 500 no int().
        responsavel_id = inteiro_ou_none(responsavel_filtro)
        if responsavel_id is not None:
            stmt = stmt.where(Chamado.responsavel_id == responsavel_id)

    if data_inicio:
        try:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
            stmt = stmt.where(Chamado.criado_em >= inicio)
        except ValueError:
            pass

    if data_fim:
        try:
            fim = datetime.strptime(data_fim, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            stmt = stmt.where(Chamado.criado_em <= fim)
        except ValueError:
            pass

    stmt = stmt.order_by(Chamado.id.desc())

    paginacao = db.paginate(stmt, page=pagina, per_page=15, error_out=False)
    chamados = paginacao.items

    tecnicos = (
        db.session.execute(
            db.select(Usuario)
            .where(Usuario.tipo_usuario.in_(PERFIS_TECNICOS))
            .order_by(Usuario.nome)
        )
        .scalars()
        .all()
    )

    setores = (
        db.session.execute(db.select(Chamado.setor).distinct().order_by(Chamado.setor))
        .scalars()
        .all()
    )

    return render_template(
        "chamados.html",
        chamados=chamados,
        busca=busca,
        status_filtro=status_filtro,
        prioridade_filtro=prioridade_filtro,
        setor_filtro=setor_filtro,
        responsavel_filtro=responsavel_filtro,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tecnicos=tecnicos,
        setores=setores,
        paginacao=paginacao,
    )


@app.route("/chamados/<int:id>")
@login_required
def detalhe_chamado(id):
    chamado = db.get_or_404(Chamado, id)

    comentarios = (
        db.session.execute(
            db.select(Comentario)
            .where(Comentario.chamado_id == id)
            .order_by(Comentario.criado_em)
        )
        .scalars()
        .all()
    )

    return render_template("detalhe_chamado.html", chamado=chamado, comentarios=comentarios)


@app.route("/chamados/<int:id>/status", methods=["POST"])
@tecnico_required
def atualizar_status_chamado(id):
    chamado = db.get_or_404(Chamado, id)

    novo_status = request.form.get("status")

    if novo_status not in STATUS_CHAMADO:
        flash("Status inválido.")
        return redirect(f"/chamados/{id}")

    chamado.status = novo_status

    if chamado.responsavel_id is None:
        chamado.responsavel_id = usuario_atual().id

    db.session.commit()

    registrar_log("Atualização de status", f"Chamado #{chamado.id} alterado para '{novo_status}'")

    flash(f"Status do chamado atualizado para '{novo_status}'.")
    return redirect(f"/chamados/{id}")


@app.route("/chamados/<int:id>/comentarios", methods=["POST"])
@tecnico_required
def adicionar_comentario(id):
    chamado = db.get_or_404(Chamado, id)

    mensagem = request.form.get("mensagem", "").strip()
    if not mensagem:
        flash("A mensagem da atualização não pode ficar vazia.")
        return redirect(f"/chamados/{id}")

    novo_comentario = Comentario(
        chamado_id=chamado.id,
        autor_id=usuario_atual().id,
        mensagem=mensagem,
    )
    db.session.add(novo_comentario)
    db.session.commit()

    registrar_log("Comentário adicionado", f"Comentário adicionado ao chamado #{chamado.id}")

    flash("Atualização adicionada com sucesso.")
    return redirect(f"/chamados/{id}")


@app.route("/meus-chamados")
@tecnico_required
def meus_chamados():
    chamados = (
        db.session.execute(
            db.select(Chamado)
            .where(Chamado.responsavel_id == usuario_atual().id)
            .order_by(Chamado.id.desc())
        )
        .scalars()
        .all()
    )

    return render_template("meus_chamados.html", chamados=chamados)


@app.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    usuarios = (
        db.session.execute(db.select(Usuario).order_by(Usuario.nome)).scalars().all()
    )

    return render_template("admin_usuarios.html", usuarios=usuarios)


@app.route("/admin/usuarios/<int:id>/tipo", methods=["POST"])
@admin_required
def admin_alterar_tipo(id):
    usuario = db.get_or_404(Usuario, id)

    novo_tipo = request.form.get("tipo_usuario")

    if novo_tipo not in TIPOS_USUARIO:
        flash("Tipo de usuário inválido.")
        return redirect("/admin/usuarios")

    if usuario.id == usuario_atual().id and novo_tipo != "Administrador":
        flash("Você não pode remover seu próprio acesso de Administrador.")
        return redirect("/admin/usuarios")

    usuario.tipo_usuario = novo_tipo
    db.session.commit()

    registrar_log("Alteração de perfil", f"Perfil de {usuario.nome} alterado para '{novo_tipo}'")

    flash(f"Perfil de {usuario.nome} atualizado para '{novo_tipo}'.")
    return redirect("/admin/usuarios")


@app.route("/admin/usuarios/<int:id>/excluir", methods=["POST"])
@admin_required
def admin_excluir_usuario(id):
    usuario = db.get_or_404(Usuario, id)

    if usuario.id == usuario_atual().id:
        flash("Você não pode excluir a própria conta.")
        return redirect("/admin/usuarios")

    possui_comentarios = (
        db.session.execute(
            db.select(db.func.count(Comentario.id)).where(Comentario.autor_id == usuario.id)
        ).scalar_one()
        > 0
    )

    possui_chamados = (
        db.session.execute(
            db.select(db.func.count(Chamado.id)).where(Chamado.responsavel_id == usuario.id)
        ).scalar_one()
        > 0
    )

    if possui_comentarios or possui_chamados:
        flash(
            "Esse usuário já possui chamados ou comentários associados e não pode ser "
            "excluído. Altere o perfil dele em vez de excluir."
        )
        return redirect("/admin/usuarios")

    nome_excluido = usuario.nome
    email_excluido = usuario.email

    # Os logs guardam o nome como texto, mas o usuario_id vira uma referência
    # órfã depois da exclusão. Zeramos a FK para manter a integridade.
    db.session.execute(
        db.update(LogAuditoria)
        .where(LogAuditoria.usuario_id == usuario.id)
        .values(usuario_id=None)
    )

    db.session.delete(usuario)
    db.session.commit()

    registrar_log("Exclusão de usuário", f"Usuário {nome_excluido} ({email_excluido}) excluído")

    flash(f"Usuário {nome_excluido} excluído com sucesso.")
    return redirect("/admin/usuarios")


@app.route("/admin/logs")
@admin_required
def admin_logs():
    logs = (
        db.session.execute(
            db.select(LogAuditoria).order_by(LogAuditoria.id.desc()).limit(200)
        )
        .scalars()
        .all()
    )

    return render_template("admin_logs.html", logs=logs)


# ==============================================================================
# EXECUÇÃO DA APLICAÇÃO
# ==============================================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # O debugger do Werkzeug permite execução remota de código: ele só pode
    # ligar quando explicitamente pedido pelo ambiente, nunca por padrão.
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")