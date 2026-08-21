import os
from datetime import timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, render_template, request

from auditoria import registrar_log
from constantes import FUSO_EXIBICAO, TIPOS_USUARIO
from extensions import csrf, db, mail
from models import Chamado, Comentario, LogAuditoria, Usuario
from rotas.auth import auth
from rotas.chamados import chamados
from seguranca import admin_required, usuario_atual

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
app.register_blueprint(chamados)


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


# ==============================================================================
# HELPERS DE VALIDAÇÃO
# ==============================================================================


# ==============================================================================
# ROTAS DA APLICAÇÃO
# ==============================================================================


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