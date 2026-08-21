"""Trilha de auditoria.

Toda ação relevante — cadastro, login, mudança de status, exclusão de conta —
vira uma linha em `LogAuditoria`, com autor e data, consultável pelo painel
administrativo.
"""

from extensions import db
from models import LogAuditoria
from seguranca import usuario_atual


def registrar_log(acao, detalhes=None):
    usuario = usuario_atual()
    log = LogAuditoria(
        usuario_id=usuario.id if usuario else None,
        usuario_nome=usuario.nome if usuario else "Público",
        acao=acao,
        detalhes=detalhes,
    )
    db.session.add(log)
    db.session.commit()
