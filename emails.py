"""Notificações por e-mail.

O envio vai pela API HTTP do Resend (https://resend.com), não por SMTP: o
plano gratuito do Render bloqueia tráfego de saída nas portas SMTP (25, 465,
587) desde set/2025, então smtplib nunca conseguia conectar — a API do
Resend fala HTTPS na porta 443, que não é bloqueada.

O envio roda numa thread separada: a abertura de chamado é pública, e esperar
a API responder deixava a página do usuário travada quando o serviço de
e-mail estava lento ou fora do ar.
"""

import threading

import requests
from flask import current_app

from constantes import PERFIS_TECNICOS
from extensions import db
from models import Usuario

_URL_RESEND = "https://api.resend.com/emails"


def _enviar_em_segundo_plano(app_obj, remetente, destinatarios, assunto, corpo):
    with app_obj.app_context():
        try:
            resposta = requests.post(
                _URL_RESEND,
                headers={"Authorization": f"Bearer {app_obj.config['RESEND_API_KEY']}"},
                json={
                    "from": remetente,
                    "to": destinatarios,
                    "subject": assunto,
                    "text": corpo,
                },
                timeout=10,
            )
            if resposta.status_code >= 400:
                app_obj.logger.error(
                    "Falha ao enviar e-mail de notificação: %s %s",
                    resposta.status_code,
                    resposta.text,
                )
            else:
                app_obj.logger.info("E-mail de notificação enviado.")
        except requests.RequestException:
            app_obj.logger.exception("Falha ao enviar e-mail de notificação.")


def _disparar(destinatarios, assunto, corpo):
    """Confere se o envio está configurado e dispara a thread de envio.

    Sem `RESEND_API_KEY`, o sistema segue funcionando normalmente, só sem
    e-mails — mesma postura de "falha aberta" já usada para o captcha.
    """
    if not current_app.config.get("RESEND_API_KEY"):
        current_app.logger.warning("RESEND_API_KEY não configurado — e-mail não enviado.")
        return
    if not destinatarios:
        return

    remetente = current_app.config["MAIL_REMETENTE"]
    threading.Thread(
        target=_enviar_em_segundo_plano,
        args=(current_app._get_current_object(), remetente, destinatarios, assunto, corpo),
        daemon=True,
    ).start()


def notificar_tecnicos_novo_chamado(chamado):
    """Avisa técnicos e administradores sobre um chamado novo."""
    tecnicos = (
        db.session.execute(
            db.select(Usuario).where(Usuario.tipo_usuario.in_(PERFIS_TECNICOS))
        )
        .scalars()
        .all()
    )

    # A conta que envia não precisa receber cópia do próprio aviso. Como ela
    # costuma estar cadastrada como Administrador para poder atender chamados,
    # sem esse filtro o sistema mandaria e-mail dela para ela mesma.
    remetente = current_app.config.get("MAIL_REMETENTE", "").strip().lower()
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

    _disparar(destinatarios, f"[Help Desk] Novo chamado: {chamado.titulo}", corpo)


def enviar_email_redefinicao(usuario, link):
    """Manda o link de redefinição para o dono da conta.

    O corpo não repete a senha nem diz o que fazer se a pessoa não pediu além
    de "ignore": qualquer instrução extra é espaço para um golpe se copiar.
    """
    corpo = (
        f"Olá, {usuario.nome}.\n\n"
        "Recebemos um pedido para redefinir a senha da sua conta no Help Desk.\n"
        "Abra o endereço abaixo para escolher uma nova senha:\n\n"
        f"{link}\n\n"
        "O link vale por 1 hora e só pode ser usado uma vez.\n"
        "Se não foi você que pediu, ignore esta mensagem: nada muda até que "
        "o link seja aberto e uma nova senha seja confirmada.\n"
    )
    _disparar([usuario.email], "Redefinição de senha — Help Desk", corpo)


def enviar_email_boas_vindas(usuario):
    """Agradece o cadastro recém-criado.

    Não é confirmação de e-mail: o formulário de cadastro só confere o
    formato do endereço (validador `Email()`), não que a pessoa é dona da caixa
    de entrada. Este e-mail é só um agradecimento pelo cadastro, no mesmo padrão
    de envio em thread separada usado pelos outros e-mails do sistema.
    """
    corpo = (
        f"Olá, {usuario.nome}.\n\n"
        "Sua conta no Help Desk foi criada com sucesso. Obrigado por se cadastrar!\n\n"
        "Agora você já pode entrar no sistema e abrir seus chamados.\n"
    )
    _disparar([usuario.email], "Bem-vindo(a) ao Help Desk!", corpo)
