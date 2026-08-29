"""Sessão, permissões e defesas contra abuso.

Reúne o que decide *quem é* o usuário da requisição e *o que ele pode fazer*:
a assinatura da sessão, a leitura do usuário a cada requisição, os decoradores
de perfil, a política de senha e os três limitadores de tentativas.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta
from functools import wraps

from flask import current_app, flash, g, jsonify, redirect, request, session
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
from models import TentativaAcesso, Usuario, obter_data_utc


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
    """Contador de tentativas com janela deslizante, guardado no banco.

    Não tem estado próprio: cada instância é só o escopo e os limites, e toda a
    contagem vive em `TentativaAcesso`. É o que faz um bloqueio continuar de pé
    depois de um reinício do serviço, de um deploy ou entre workers diferentes
    — antes ele evaporava junto com o processo.
    """

    def __init__(self, escopo, maximo, janela_segundos):
        self.escopo = escopo
        self.maximo = maximo
        self.janela = janela_segundos

    def _inicio_da_janela(self):
        return obter_data_utc() - timedelta(seconds=self.janela)

    def _desta_chave(self, chave):
        # A chave vira texto porque um limitador usa e-mail e outro usa id.
        return (
            TentativaAcesso.escopo == self.escopo,
            TentativaAcesso.chave == str(chave),
        )

    def registrar(self, chave):
        """Anota uma tentativa, aproveitando para varrer as que já expiraram.

        A varredura sai de graça aqui: só há escrita quando alguém erra, e sem
        ela a tabela cresceria para sempre com tentativas que não contam mais.
        """
        db.session.query(TentativaAcesso).filter(
            TentativaAcesso.escopo == self.escopo,
            TentativaAcesso.criado_em < self._inicio_da_janela(),
        ).delete(synchronize_session=False)

        db.session.add(TentativaAcesso(escopo=self.escopo, chave=str(chave)))
        db.session.commit()

    def segundos_de_bloqueio(self, chave):
        """Quantos segundos faltam para liberar. Zero se não estiver bloqueado."""
        tentativas = (
            db.session.execute(
                db.select(TentativaAcesso.criado_em)
                .where(
                    *self._desta_chave(chave),
                    TentativaAcesso.criado_em >= self._inicio_da_janela(),
                )
                .order_by(TentativaAcesso.criado_em)
            )
            .scalars()
            .all()
        )

        if len(tentativas) < self.maximo:
            return 0

        # A janela desliza a partir da tentativa mais antiga que ainda conta.
        decorrido = (obter_data_utc() - tentativas[0]).total_seconds()
        return int(self.janela - decorrido) + 1

    def limpar(self, chave):
        db.session.query(TentativaAcesso).filter(*self._desta_chave(chave)).delete(
            synchronize_session=False
        )
        db.session.commit()


# Senha atual errada na troca de senha, por usuário.
throttle_senha = Throttle("senha", MAX_TENTATIVAS_SENHA, JANELA_BLOQUEIO_SEGUNDOS)

# Senha errada no login, por e-mail — o throttle precisa existir antes de haver
# sessão, por isso a chave é o e-mail e não o id.
throttle_login = Throttle("login", MAX_TENTATIVAS_LOGIN, JANELA_BLOQUEIO_LOGIN_SEGUNDOS)

# Pedidos de redefinição por e-mail, para o formulário público não virar uma
# forma de disparar mensagens em massa contra uma caixa de entrada.
throttle_redefinicao = Throttle(
    "redefinicao", MAX_PEDIDOS_REDEFINICAO, JANELA_PEDIDOS_REDEFINICAO_SEGUNDOS
)


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


# ==============================================================================
# TOKEN DE API
# ==============================================================================
def _hash_token_api(token):
    """SHA-256 do token, o que fica gravado no banco.

    Mesmo raciocínio da senha: o banco guarda algo que serve para *conferir*
    o token, não o token em si. Diferente da senha, aqui um hash simples basta
    — o token já nasce com entropia alta (32 bytes aleatórios), então não há
    o risco de dicionário que justifica o custo do bcrypt/scrypt numa senha
    escolhida por humano.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def gerar_token_api(usuario):
    """Cria um token novo para o usuário e devolve o valor em texto puro.

    É a única vez que o valor bruto existe: só o hash é gravado. Gerar de novo
    substitui o anterior — não há como ter dois tokens válidos ao mesmo tempo,
    então revogar é só apagar ou trocar.
    """
    token = secrets.token_urlsafe(32)
    usuario.token_api_hash = _hash_token_api(token)
    db.session.commit()
    return token


def usuario_do_token_api(token):
    """Usuário dono do token, ou None se o token não existir ou não bater."""
    if not token:
        return None
    return db.session.execute(
        db.select(Usuario).where(Usuario.token_api_hash == _hash_token_api(token))
    ).scalar_one_or_none()


def token_api_required(f):
    """Autenticação da API: um `Authorization: Bearer <token>` válido.

    Não usa cookie de sessão de propósito — um script ou um app externo não
    tem navegador para guardar cookie, e reaproveitar a sessão amarraria a API
    a estar logado no mesmo browser. O erro sai em JSON, como o resto da API,
    nunca um redirecionamento para `/login`: quem chama aqui é código, não uma
    pessoa navegando.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        cabecalho = request.headers.get("Authorization", "")
        token = cabecalho[7:] if cabecalho.startswith("Bearer ") else None

        usuario = usuario_do_token_api(token)
        if usuario is None:
            return jsonify(erro="Token de API ausente ou inválido."), 401

        g.usuario_api = usuario
        return f(*args, **kwargs)

    return decorated_function


def tecnico_api_required(f):
    """Exige perfil Técnico/Administrador, em cima de `token_api_required`.

    Mudar status e comentar são ações restritas na tela (`tecnico_required`);
    a API replica a mesma regra em vez de ser mais permissiva que a interface
    web só porque a checagem de perfil ali usa sessão e aqui usa token. Espera
    ser aplicado depois de `token_api_required`, que é quem popula
    `g.usuario_api`.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.usuario_api.eh_tecnico:
            return jsonify(erro="Ação restrita a Técnicos e Administradores."), 403
        return f(*args, **kwargs)

    return decorated_function
