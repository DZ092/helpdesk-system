"""Cadastro, login, logout e troca de senha."""

from flask import Blueprint, flash, g, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from auditoria import registrar_log
from constantes import TAMANHO_MINIMO_SENHA
from extensions import db
from models import Usuario
from seguranca import (
    impressao_sessao,
    limpar_tentativas_login,
    limpar_tentativas_senha,
    login_required,
    registrar_tentativa_login,
    registrar_tentativa_senha,
    segundos_de_bloqueio,
    segundos_de_bloqueio_login,
    usuario_atual,
    validar_forca_senha,
)
from validacao import campo_obrigatorio

auth = Blueprint("auth", __name__)


@auth.route("/cadastro", methods=["GET", "POST"])
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


@auth.route("/login", methods=["GET", "POST"])
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


@auth.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@auth.route("/senha", methods=["GET", "POST"])
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
