"""Cadastro, login, logout e troca de senha."""

from flask import Blueprint, flash, g, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from flask import url_for

from auditoria import registrar_log
from constantes import TAMANHO_MINIMO_SENHA
from emails import enviar_email_redefinicao
from extensions import db
from models import Usuario
from seguranca import (
    gerar_token_redefinicao,
    impressao_sessao,
    login_required,
    throttle_login,
    throttle_redefinicao,
    throttle_senha,
    usuario_atual,
    usuario_do_token,
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

        bloqueio = throttle_login.segundos_de_bloqueio(email)
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
            throttle_login.limpar(email)
            # Troca o identificador de sessão no login para evitar fixação de sessão.
            session.clear()
            session["usuario_id"] = usuario.id
            session["auth"] = impressao_sessao(usuario)
            session.permanent = True
            g.usuario = usuario
            registrar_log("Login realizado")
            return redirect("/dashboard")

        throttle_login.registrar(email)

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
        bloqueio = throttle_senha.segundos_de_bloqueio(usuario.id)
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
            throttle_senha.registrar(usuario.id)
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

        throttle_senha.limpar(usuario.id)
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


@auth.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    """Pede o e-mail e dispara o link de redefinição."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        bloqueio = throttle_redefinicao.segundos_de_bloqueio(email)
        if bloqueio:
            return render_template(
                "esqueci_senha.html",
                erro=f"Pedidos demais para esse e-mail. Tente de novo em {bloqueio // 60 + 1} minuto(s).",
            )

        throttle_redefinicao.registrar(email)

        usuario = db.session.execute(
            db.select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()

        if usuario:
            link = url_for("auth.redefinir_senha", token=gerar_token_redefinicao(usuario), _external=True)
            enviar_email_redefinicao(usuario, link)
            registrar_log("Redefinição de senha solicitada", f"Link enviado para {usuario.email}")
        else:
            registrar_log("Redefinição de senha solicitada", f"E-mail não cadastrado: {email}")

        # A resposta é a mesma nos dois casos. Dizer "esse e-mail não existe"
        # transformaria a tela num verificador de quem tem conta no sistema.
        return render_template("esqueci_senha.html", enviado=True)

    return render_template("esqueci_senha.html")


@auth.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    """Valida o link recebido por e-mail e troca a senha."""
    usuario, motivo = usuario_do_token(token)

    if usuario is None:
        return render_template("redefinir_senha.html", motivo=motivo)

    if request.method == "POST":
        nova_senha = request.form.get("nova_senha", "")
        confirmacao = request.form.get("confirmacao", "")

        if nova_senha != confirmacao:
            return render_template(
                "redefinir_senha.html", token=token, nome=usuario.nome,
                erro="A nova senha e a confirmação não conferem.",
            )

        problema = validar_forca_senha(nova_senha, usuario)
        if problema:
            return render_template(
                "redefinir_senha.html", token=token, nome=usuario.nome, erro=problema
            )

        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()

        # Trocar o hash invalida o próprio token usado, os links antigos ainda
        # na caixa de entrada e as sessões abertas em outros dispositivos.
        throttle_senha.limpar(usuario.id)
        throttle_login.limpar(usuario.email)
        registrar_log("Senha redefinida", f"Redefinição por link para {usuario.email}")

        # Sem login automático: quem abriu o link prova que sabe a senha nova
        # entrando com ela.
        flash("Senha redefinida com sucesso. Faça login com a nova senha.")
        return redirect("/login")

    return render_template("redefinir_senha.html", token=token, nome=usuario.nome)
