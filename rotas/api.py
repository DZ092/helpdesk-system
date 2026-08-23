"""API REST somente leitura dos chamados.

Primeira fatia da issue #9: consultar chamados de fora do navegador, com um
token de API em vez do cookie de sessão (ver `seguranca.token_api_required`).
Abrir chamado, mudar status e comentar continuam só pela interface web — ficam
para uma próxima fatia.
"""

from flask import Blueprint, jsonify, request

from constantes import PRIORIDADES, STATUS_CHAMADO
from extensions import db
from models import Chamado, Comentario
from seguranca import token_api_required

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
