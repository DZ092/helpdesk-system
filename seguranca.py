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
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from constantes import (
    JANELA_BLOQUEIO_LOGIN_SEGUNDOS,
    JANELA_PEDIDOS_REDEFINICAO_SEGUNDOS,
    JANELA_BLOQUEIO_SEGUNDOS,
    MAX_PEDIDOS_REDEFINICAO,
    MAX_TENTATIVAS_LOGIN,
    MAX_TENTATIVAS_SENHA,
    SENHAS_PROIBIDAS,
    TAMANHO_MINIMO_SENHA,
    VALIDADE_TOKEN_SENHA_SEGUNDOS,
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


class Throttle:
    """Contador de tentativas em memória, com janela deslizante.

    Guardado no processo de propósito: é simples e suficiente enquanto a
    aplicação roda num processo só. Num deploy com vários workers isso precisa
    ir para Redis ou banco — está registrado como pendência no README.
    """

    def __init__(self, maximo, janela_segundos):
        self.maximo = maximo
        self.janela = janela_segundos
        self._registros = {}

    def _recentes(self, chave):
        agora = time.monotonic()
        tentativas = [t for t in self._registros.get(chave, []) if agora - t < self.janela]
        self._registros[chave] = tentativas
        return agora, tentativas

    def registrar(self, chave):
        _, tentativas = self._recentes(chave)
        tentativas.append(time.monotonic())

    def segundos_de_bloqueio(self, chave):
        """Quantos segundos faltam para liberar. Zero se não estiver bloqueado."""
        agora, tentativas = self._recentes(chave)
        if len(tentativas) < self.maximo:
            return 0
        return int(self.janela - (agora - tentativas[0])) + 1

    def limpar(self, chave):
        self._registros.pop(chave, None)


# Senha atual errada na troca de senha, por usuário.
throttle_senha = Throttle(MAX_TENTATIVAS_SENHA, JANELA_BLOQUEIO_SEGUNDOS)

# Senha errada no login, por e-mail — o throttle precisa existir antes de haver
# sessão, por isso a chave é o e-mail e não o id.
throttle_login = Throttle(MAX_TENTATIVAS_LOGIN, JANELA_BLOQUEIO_LOGIN_SEGUNDOS)

# Pedidos de redefinição por e-mail, para o formulário público não virar uma
# forma de disparar mensagens em massa contra uma caixa de entrada.
throttle_redefinicao = Throttle(MAX_PEDIDOS_REDEFINICAO, JANELA_PEDIDOS_REDEFINICAO_SEGUNDOS)


# ==============================================================================
# TOKEN DE REDEFINIÇÃO DE SENHA
# ==============================================================================
def _serializador():
    """Assinador dos links de redefinição.

    O `salt` isola este uso: um token assinado aqui não vale para nenhuma outra
    finalidade que use a mesma SECRET_KEY.
    """
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="redefinir-senha")


def gerar_token_redefinicao(usuario):
    """Token que identifica o usuário e morre assim que a senha muda.

    Além do id, o token carrega a impressão da sessão — um HMAC do hash da
    senha atual. Como redefinir a senha muda esse hash, o próprio link usado
    deixa de valer, e o mesmo acontece com qualquer link antigo ainda no
    e-mail. É o que dá o uso único sem precisar de tabela de tokens.
    """
    return _serializador().dumps({"id": usuario.id, "impressao": impressao_sessao(usuario)})


def usuario_do_token(token, validade_segundos=None):
    """Devolve (usuario, None) se o token servir, ou (None, motivo) se não.

    Motivos: "expirado" (passou da validade), "usado" (a senha já mudou desde
    que o link foi emitido) e "invalido" (assinatura quebrada ou conta apagada).
    """
    if validade_segundos is None:
        validade_segundos = VALIDADE_TOKEN_SENHA_SEGUNDOS

    try:
        dados = _serializador().loads(token, max_age=validade_segundos)
    except SignatureExpired:
        return None, "expirado"
    except BadSignature:
        return None, "invalido"

    usuario = db.session.get(Usuario, dados.get("id"))
    if usuario is None:
        return None, "invalido"

    if not hmac.compare_digest(dados.get("impressao", ""), impressao_sessao(usuario)):
        return None, "usado"

    return usuario, None
