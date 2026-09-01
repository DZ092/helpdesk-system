"""Cadastro, login, logout e troca de senha."""

from flask import Blueprint, flash, g, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from flask import url_for

from auditoria import registrar_log
from emails import enviar_email_redefinicao
from extensions import db
from formularios import (
    FormularioAlterarSenha,
    FormularioCadastro,
    FormularioEsqueciSenha,
    FormularioLogin,
    FormularioRedefinirSenha,
)
from models import Usuario
from seguranca import (
    gerar_token_api,
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

auth = Blueprint("auth", __name__)


def _primeiro_erro(form):
    """Primeira mensagem de validação do form, ou None se não houve erro.

    Os templates de auth mostram um único bloco `{% if erro %}` no topo da
    página — não uma lista por campo — então concentramos aqui a escolha de
    qual mensagem sobe, mantendo a tela igual à de antes da migração.
    """
    for erros_do_campo in form.errors.values():
        if erros_do_campo:
            return erros_do_campo[0]
    return None


@auth.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    form = FormularioCadastro()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        usuario_existente = db.session.execute(
            db.select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()

        if usuario_existente:
            return render_template("cadastro.html", form=form, erro="Este e-mail já está cadastrado.")

        # O perfil NUNCA vem do formulário. O cadastro é aberto ao público, então
        # aceitar `tipo_usuario` do cliente deixaria qualquer visitante criar a
        # própria conta de Administrador. Promoção de perfil é feita só pelo
        # painel administrativo (ou pelo script promover_admin.py no primeiro uso).
        novo_usuario = Usuario(
            nome=form.nome.data.strip()[:100],
            email=email,
            senha=generate_password_hash(form.senha.data),
            tipo_usuario="Usuário",
        )
        db.session.add(novo_usuario)
        db.session.commit()
        registrar_log("Cadastro de usuário", f"Novo usuário: {novo_usuario.email}")
        flash("Conta criada com sucesso! Faça login para continuar.")
        return redirect("/login")

    return render_template("cadastro.html", form=form, erro=_primeiro_erro(form))


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = FormularioLogin()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        senha = form.senha.data

        bloqueio = throttle_login.segundos_de_bloqueio(email)
        if bloqueio:
            registrar_log("Login bloqueado", f"Excesso de tentativas para {email}")
            return render_template(
                "login.html",
                form=form,
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
        return render_template("login.html", form=form, erro="E-mail ou senha inválidos.")

    return render_template("login.html", form=form, erro=_primeiro_erro(form))


@auth.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@auth.route("/senha", methods=["GET", "POST"])
@login_required
def alterar_senha():
    """Troca de senha do próprio usuário."""
    usuario = usuario_atual()
    form = FormularioAlterarSenha()

    if form.validate_on_submit():
        bloqueio = throttle_senha.segundos_de_bloqueio(usuario.id)
        if bloqueio:
            registrar_log(
                "Troca de senha bloqueada",
                f"Excesso de tentativas para {usuario.email}",
            )
            return render_template(
                "alterar_senha.html",
                form=form,
                erro=f"Tentativas demais. Tente de novo em {bloqueio // 60 + 1} minuto(s).",
            )

        # Confirmar a senha atual impede que alguém com a sessão sequestrada
        # (ou um computador destravado) troque a senha e tome a conta.
        if not check_password_hash(usuario.senha, form.senha_atual.data):
            throttle_senha.registrar(usuario.id)
            registrar_log("Senha atual incorreta", f"Tentativa de troca por {usuario.email}")
            return render_template("alterar_senha.html", form=form, erro="Senha atual incorreta.")

        nova_senha = form.nova_senha.data

        if check_password_hash(usuario.senha, nova_senha):
            return render_template(
                "alterar_senha.html", form=form, erro="A nova senha precisa ser diferente da atual."
            )

        # Regras genéricas de força já passaram nos validators do form; falta
        # só a checagem que depende de quem está logado (nome/e-mail na senha).
        problema = validar_forca_senha(nova_senha, usuario)
        if problema:
            return render_template("alterar_senha.html", form=form, erro=problema)

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

    return render_template("alterar_senha.html", form=form, erro=_primeiro_erro(form))


@auth.route("/meu-token", methods=["GET", "POST"])
@login_required
def meu_token():
    """Gera (ou substitui) o token que autentica este usuário na API.

    O valor bruto só existe na resposta deste POST — o banco guarda apenas o
    hash (ver `gerar_token_api`). Fechou a página sem copiar, o jeito de ver o
    token de novo é gerar outro, o que invalida o anterior.
    """
    usuario = usuario_atual()

    if request.method == "POST":
        token = gerar_token_api(usuario)
        registrar_log("Token de API gerado", f"Token gerado por {usuario.email}")
        return render_template("meu_token.html", token_gerado=token)

    return render_template("meu_token.html", tem_token=usuario.token_api_hash is not None)


@auth.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    """Pede o e-mail e dispara o link de redefinição."""
    form = FormularioEsqueciSenha()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        bloqueio = throttle_redefinicao.segundos_de_bloqueio(email)
        if bloqueio:
            return render_template(
                "esqueci_senha.html",
                form=form,
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

    return render_template("esqueci_senha.html", form=form, erro=_primeiro_erro(form))


@auth.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    """Valida o link recebido por e-mail e troca a senha."""
    usuario, motivo = usuario_do_token(token)

    if usuario is None:
        return render_template("redefinir_senha.html", motivo=motivo)

    form = FormularioRedefinirSenha()

    if form.validate_on_submit():
        nova_senha = form.nova_senha.data

        # Regras genéricas de força já passaram nos validators do form; falta
        # só a checagem que depende do usuário do token (nome/e-mail na senha).
        problema = validar_forca_senha(nova_senha, usuario)
        if problema:
            return render_template(
                "redefinir_senha.html", form=form, token=token, nome=usuario.nome, erro=problema
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

    return render_template(
        "redefinir_senha.html", form=form, token=token, nome=usuario.nome, erro=_primeiro_erro(form)
    )
