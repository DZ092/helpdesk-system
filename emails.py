"""Notificações por e-mail.

O envio roda numa thread separada: a abertura de chamado é pública, e esperar o
SMTP responder deixava a página do usuário travada quando o servidor de e-mail
estava lento ou fora do ar.
"""

import threading

from flask import current_app
from flask_mail import Message

from constantes import PERFIS_TECNICOS
from extensions import db, mail
from models import Usuario


def _enviar_em_segundo_plano(app_obj, mensagem):
    with app_obj.app_context():
        try:
            mail.send(mensagem)
            app_obj.logger.info("E-mail de notificação enviado.")
        except Exception:
            app_obj.logger.exception("Falha ao enviar e-mail de notificação.")


def notificar_tecnicos_novo_chamado(chamado):
    """Avisa técnicos e administradores sobre um chamado novo.

    O envio vai para uma thread separada de propósito: a abertura de chamado é
    pública e ficava presa esperando o SMTP responder, então um servidor de
    e-mail lento ou fora do ar travava a página do usuário por minutos.
    """
    tecnicos = (
        db.session.execute(
            db.select(Usuario).where(Usuario.tipo_usuario.in_(PERFIS_TECNICOS))
        )
        .scalars()
        .all()
    )

    if not current_app.config.get("MAIL_USERNAME"):
        current_app.logger.warning("MAIL_USERNAME não configurado — notificação não enviada.")
        return

    # A conta que envia não precisa receber cópia do próprio aviso. Como ela
    # costuma estar cadastrada como Administrador para poder atender chamados,
    # sem esse filtro o sistema mandaria e-mail dela para ela mesma.
    remetente = current_app.config["MAIL_USERNAME"].strip().lower()
    destinatarios = [
        tecnico.email for tecnico in tecnicos if tecnico.email.strip().lower() != remetente
    ]

    if not destinatarios:
        current_app.logger.info("Nenhum destinatário para notificar — e-mail não enviado.")
        return

    corpo = (
        f"Novo chamado aberto no Help Desk!\n\n"
        f"Título: {chamado.titulo}\n"
        f"Usuário: {chamado.usuario}\n"
        f"Setor: {chamado.setor}\n"
        f"Prioridade: {chamado.prioridade}\n\n"
        f"Descrição:\n{chamado.descricao}\n\n"
        f"Acesse o sistema para ver mais detalhes e atender o chamado."
    )

    mensagem = Message(
        subject=f"[Help Desk] Novo chamado: {chamado.titulo}",
        recipients=destinatarios,
        body=corpo,
    )

    threading.Thread(
        target=_enviar_em_segundo_plano,
        args=(current_app._get_current_object(), mensagem),
        daemon=True,
    ).start()
