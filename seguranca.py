"""Sessão, permissões e defesas contra abuso.

Reúne o que decide *quem é* o usuário da requisição e *o que ele pode fazer*:
a assinatura da sessão, a leitura do usuário a cada requisição, os decoradores
de perfil, a política de senha e os dois limitadores de tentativas.
"""

import hashlib
import hmac
import time
from functools import wraps

from flask import current_app, flash, g, redirect, session

from constantes import (
    JANELA_BLOQUEIO_LOGIN_SEGUNDOS,
    JANELA_BLOQUEIO_SEGUNDOS,
    MAX_TENTATIVAS_LOGIN,
    MAX_TENTATIVAS_SENHA,
    SENHAS_PROIBIDAS,
    TAMANHO_MINIMO_SENHA,
)
from extensions import db
from models import Usuario


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
        current_app.config["SECRET_KEY"].encode(),
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
