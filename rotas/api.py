"""API REST dos chamados — leitura e escrita (issue #9).

Consultar, abrir, mudar status e comentar de fora do navegador, com um token
de API em vez do cookie de sessão (ver `seguranca.token_api_required`). As
regras de negócio e de permissão são as mesmas da interface web: abrir chamado
continua público, mudar status e comentar continuam restritos a Técnico e
Administrador (`seguranca.tecnico_api_required`) — só a forma de autenticar
muda.
"""

from flask import Blueprint, g, jsonify, request

from auditoria import registrar_log
from constantes import PRIORIDADES, STATUS_CHAMADO
from emails import notificar_tecnicos_novo_chamado
from extensions import db
from models import Chamado, Comentario
from seguranca import tecnico_api_required, token_api_required

api = Blueprint("api", __name__, url_prefix="/api/v1")


def _chamado_para_json(chamado):
    return {
        "id": chamado.id,
        "usuario": chamado.usuario,
        "setor": chamado.setor,
        "titulo": chamado.titulo,
        "descricao": chamado.descricao,
        "status": chamado.status,
        "prioridade": chamado.prioridade,
        "criado_em": chamado.criado_em.isoformat() + "Z",
        "atualizado_em": chamado.atualizado_em.isoformat() + "Z",
        "responsavel_id": chamado.responsavel_id,
    }


def _comentario_para_json(comentario):
    return {
        "id": comentario.id,
        "autor_id": comentario.autor_id,
        "autor_nome": comentario.autor.nome,
        "mensagem": comentario.mensagem,
        "criado_em": comentario.criado_em.isoformat() + "Z",
    }


@api.route("/chamados")
@token_api_required
def listar_chamados():
    """Lista chamados com os mesmos filtros da tela `/chamados`, em JSON.

    A visibilidade é a mesma da tela: qualquer usuário autenticado enxerga
    todos os chamados, não só os próprios — não é uma API "meus chamados".
    """
    status_filtro = request.args.get("status", "")
    prioridade_filtro = request.args.get("prioridade", "")
    setor_filtro = request.args.get("setor", "")
    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = min(request.args.get("por_pagina", 15, type=int) or 15, 100)

    stmt = db.select(Chamado)

    if status_filtro:
        if status_filtro not in STATUS_CHAMADO:
            return jsonify(erro=f"status precisa ser um de: {', '.join(STATUS_CHAMADO)}"), 400
        stmt = stmt.where(Chamado.status == status_filtro)

    if prioridade_filtro:
        if prioridade_filtro not in PRIORIDADES:
            return jsonify(erro=f"prioridade precisa ser um de: {', '.join(PRIORIDADES)}"), 400
        stmt = stmt.where(Chamado.prioridade == prioridade_filtro)

    if setor_filtro:
        stmt = stmt.where(Chamado.setor == setor_filtro)

    stmt = stmt.order_by(Chamado.id.desc())

    paginacao = db.paginate(stmt, page=pagina, per_page=por_pagina, error_out=False)

    return jsonify(
        chamados=[_chamado_para_json(c) for c in paginacao.items],
        pagina=paginacao.page,
        por_pagina=paginacao.per_page,
        total=paginacao.total,
        paginas=paginacao.pages,
    )


@api.route("/chamados/<int:id>")
@token_api_required
def detalhe_chamado(id):
    chamado = db.session.get(Chamado, id)
    if chamado is None:
        return jsonify(erro="Chamado não encontrado."), 404

    comentarios = (
        db.session.execute(
            db.select(Comentario)
            .where(Comentario.chamado_id == id)
            .order_by(Comentario.criado_em)
        )
        .scalars()
        .all()
    )

    dados = _chamado_para_json(chamado)
    dados["comentarios"] = [_comentario_para_json(c) for c in comentarios]
    return jsonify(dados)


def _campo_obrigatorio_json(dados, nome, tamanho_maximo):
    """Equivalente a `validacao.campo_obrigatorio`, mas lendo do corpo JSON.

    A versão original lê de `request.form` — a API recebe JSON, então precisa
    da mesma normalização (strip, corte no tamanho da coluna) sobre outra
    fonte, não de uma regra diferente.
    """
    valor = str(dados.get(nome, "")).strip()
    return valor[:tamanho_maximo]


@api.route("/chamados", methods=["POST"])
@token_api_required
def abrir_chamado():
    """Abre um chamado novo. Pública na tela, e continua sem exigir perfil aqui.

    A única diferença da tela é a autenticação: a tela aceita qualquer
    visitante sem login, a API exige um token válido — mas de qualquer
    usuário, sem checar `eh_tecnico`, porque abrir chamado nunca foi uma ação
    restrita.
    """
    dados = request.get_json(silent=True) or {}

    usuario = _campo_obrigatorio_json(dados, "usuario", 100)
    setor = _campo_obrigatorio_json(dados, "setor", 100)
    titulo = _campo_obrigatorio_json(dados, "titulo", 200)
    descricao = str(dados.get("descricao", "")).strip()
    prioridade = dados.get("prioridade", "Média")

    if not all((usuario, setor, titulo, descricao)):
        return jsonify(erro="Preencha todos os campos do chamado."), 400

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

    registrar_log(
        "Abertura de chamado",
        f"Chamado #{novo_chamado.id}: {novo_chamado.titulo} (via API)",
        usuario=g.usuario_api,
    )
    notificar_tecnicos_novo_chamado(novo_chamado)

    return jsonify(_chamado_para_json(novo_chamado)), 201


@api.route("/chamados/<int:id>/status", methods=["POST"])
@token_api_required
@tecnico_api_required
def atualizar_status_chamado_api(id):
    chamado = db.session.get(Chamado, id)
    if chamado is None:
        return jsonify(erro="Chamado não encontrado."), 404

    dados = request.get_json(silent=True) or {}
    novo_status = dados.get("status")

    if novo_status not in STATUS_CHAMADO:
        return jsonify(erro=f"status precisa ser um de: {', '.join(STATUS_CHAMADO)}"), 400

    chamado.status = novo_status

    if chamado.responsavel_id is None:
        chamado.responsavel_id = g.usuario_api.id

    db.session.commit()

    registrar_log(
        "Atualização de status",
        f"Chamado #{chamado.id} alterado para '{novo_status}' (via API)",
        usuario=g.usuario_api,
    )

    return jsonify(_chamado_para_json(chamado))


@api.route("/chamados/<int:id>/comentarios", methods=["POST"])
@token_api_required
@tecnico_api_required
def adicionar_comentario_api(id):
    chamado = db.session.get(Chamado, id)
    if chamado is None:
        return jsonify(erro="Chamado não encontrado."), 404

    dados = request.get_json(silent=True) or {}
    mensagem = str(dados.get("mensagem", "")).strip()
    if not mensagem:
        return jsonify(erro="A mensagem da atualização não pode ficar vazia."), 400

    novo_comentario = Comentario(
        chamado_id=chamado.id,
        autor_id=g.usuario_api.id,
        mensagem=mensagem,
    )
    db.session.add(novo_comentario)
    db.session.commit()

    registrar_log(
        "Comentário adicionado",
        f"Comentário adicionado ao chamado #{chamado.id} (via API)",
        usuario=g.usuario_api,
    )

    return jsonify(_comentario_para_json(novo_comentario)), 201
