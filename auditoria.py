"""Trilha de auditoria.

Toda ação relevante — cadastro, login, mudança de status, exclusão de conta —
vira uma linha em `LogAuditoria`, com autor e data, consultável pelo painel
administrativo.
"""

from extensions import db
from models import LogAuditoria
from seguranca import usuario_atual


def registrar_log(acao, detalhes=None, usuario=None):
    """Grava a linha de auditoria, atribuída a `usuario` ou ao usuário da sessão.

    O parâmetro existe para quem chama de fora de uma requisição autenticada
    por cookie — a API REST, por exemplo, autentica por token e não tem sessão
    para `usuario_atual()` ler; sem essa saída, toda ação feita pela API
    apareceria no log como "Público", mesmo vindo de um usuário identificado.
    """
    if usuario is None:
        usuario = usuario_atual()
    log = LogAuditoria(
        usuario_id=usuario.id if usuario else None,
        usuario_nome=usuario.nome if usuario else "Público",
        acao=acao,
        detalhes=detalhes,
    )
    db.session.add(log)
    db.session.commit()
