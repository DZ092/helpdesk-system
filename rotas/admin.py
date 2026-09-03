"""Painel administrativo: gestão de usuários e trilha de auditoria."""

from flask import Blueprint, flash, redirect, render_template

from auditoria import registrar_log
from extensions import db
from formularios import FormularioAlterarTipoUsuario
from models import Chamado, Comentario, LogAuditoria, Usuario
from seguranca import admin_required, usuario_atual

admin = Blueprint("admin", __name__)


@admin.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    usuarios = (
        db.session.execute(db.select(Usuario).order_by(Usuario.nome)).scalars().all()
    )

    return render_template("admin_usuarios.html", usuarios=usuarios)


@admin.route("/admin/usuarios/<int:id>/tipo", methods=["POST"])
@admin_required
def admin_alterar_tipo(id):
    usuario = db.get_or_404(Usuario, id)

    form = FormularioAlterarTipoUsuario()
    if not form.validate_on_submit():
        flash("Tipo de usuário inválido.")
        return redirect("/admin/usuarios")

    novo_tipo = form.tipo_usuario.data

    if usuario.id == usuario_atual().id and novo_tipo != "Administrador":
        flash("Você não pode remover seu próprio acesso de Administrador.")
        return redirect("/admin/usuarios")

    usuario.tipo_usuario = novo_tipo
    db.session.commit()

    registrar_log("Alteração de perfil", f"Perfil de {usuario.nome} alterado para '{novo_tipo}'")

    flash(f"Perfil de {usuario.nome} atualizado para '{novo_tipo}'.")
    return redirect("/admin/usuarios")


@admin.route("/admin/usuarios/<int:id>/excluir", methods=["POST"])
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


@admin.route("/admin/logs")
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
