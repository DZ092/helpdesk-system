import os
import threading
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, render_template, request
from flask_mail import Message

from auditoria import registrar_log
from constantes import (
    FUSO_EXIBICAO,
    PERFIS_TECNICOS,
    PRIORIDADES,
    STATUS_CHAMADO,
    TIPOS_USUARIO,
)
from extensions import csrf, db, mail
from models import Chamado, Comentario, LogAuditoria, Usuario
from rotas.auth import auth
from seguranca import admin_required, login_required, tecnico_required, usuario_atual
from validacao import campo_obrigatorio, inteiro_ou_none

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

app.register_blueprint(auth)


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


# ==============================================================================
# REGISTRO DE LOGS E AUDITORIA
# ==============================================================================


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


# ==============================================================================
# ROTAS DA APLICAÇÃO
# ==============================================================================
@app.route("/")
def home():
    return redirect("/dashboard")


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