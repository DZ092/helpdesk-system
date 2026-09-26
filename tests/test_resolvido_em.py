"""Coluna resolvido_em e a regra única de troca de status (visual novo, Fase 1)."""

from datetime import datetime

from extensions import db
from models import Chamado

SENHA = "senha-de-teste"


def _chamado(status="Aberto"):
    chamado = Chamado(
        usuario="Maria",
        setor="Financeiro",
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status=status,
        prioridade="Alta",
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def _entrar_como_tecnico(client, criar_usuario):
    criar_usuario(nome="Ana Técnica", email="tecnica@teste.com", tipo="Técnico")
    client.post("/login", data={"email": "tecnica@teste.com", "senha": SENHA})


def test_definir_status_grava_resolvido_em_ao_resolver(app):
    chamado = _chamado()

    chamado.definir_status("Resolvido")

    assert chamado.status == "Resolvido"
    assert isinstance(chamado.resolvido_em, datetime)
    assert chamado.resolvido_em.tzinfo is None  # UTC naive, padrão do banco


def test_definir_status_limpa_resolvido_em_ao_reabrir(app):
    chamado = _chamado()
    chamado.definir_status("Resolvido")

    chamado.definir_status("Em andamento")

    assert chamado.status == "Em andamento"
    assert chamado.resolvido_em is None


def test_definir_status_mesmo_status_nao_altera_data(app):
    chamado = _chamado()
    chamado.definir_status("Resolvido")
    primeira = chamado.resolvido_em

    chamado.definir_status("Resolvido")

    assert chamado.resolvido_em == primeira


def test_resolver_de_novo_depois_de_reabrir_grava_a_nova_data(app):
    chamado = _chamado()
    chamado.definir_status("Resolvido")
    chamado.resolvido_em = datetime(2020, 1, 1, 12, 0)  # resolução antiga
    chamado.definir_status("Aberto")

    chamado.definir_status("Resolvido")

    assert chamado.resolvido_em > datetime(2020, 1, 1, 12, 0)


def test_atualizar_status_pela_rota_grava_resolvido_em(client, criar_usuario):
    _entrar_como_tecnico(client, criar_usuario)
    chamado = _chamado()

    client.post(f"/chamados/{chamado.id}/status", data={"status": "Resolvido"})

    db.session.refresh(chamado)
    assert chamado.status == "Resolvido"
    assert chamado.resolvido_em is not None


def test_atualizar_status_pela_api_grava_resolvido_em(client, criar_usuario):
    _entrar_como_tecnico(client, criar_usuario)
    token = client.post("/meu-token").get_data(as_text=True).split("<code>")[1].split("</code>")[0]
    chamado = _chamado()

    resposta = client.post(
        f"/api/v1/chamados/{chamado.id}/status",
        json={"status": "Resolvido"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    db.session.refresh(chamado)
    assert chamado.resolvido_em is not None


def test_migracao_preenche_resolvido_em_dos_chamados_ja_resolvidos(tmp_path):
    """Chamados resolvidos antes da coluna existir recebem atualizado_em."""
    from flask_migrate import upgrade
    from sqlalchemy import text

    from app import create_app

    banco = tmp_path / "backfill.db"
    aplicacao = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{banco}",
            "SECRET_KEY": "chave-de-teste",
        }
    )

    with aplicacao.app_context():
        upgrade(revision="d835773a6a22")  # esquema antes de resolvido_em
        with db.engine.begin() as conexao:
            conexao.execute(
                text(
                    "INSERT INTO chamado (usuario, setor, titulo, descricao, status, prioridade, criado_em, atualizado_em) "
                    "VALUES ('Maria', 'TI', 'Resolvido antigo', 'd', 'Resolvido', 'Alta', "
                    "'2026-09-01 10:00:00', '2026-09-02 15:30:00')"
                )
            )
            conexao.execute(
                text(
                    "INSERT INTO chamado (usuario, setor, titulo, descricao, status, prioridade, criado_em, atualizado_em) "
                    "VALUES ('João', 'TI', 'Ainda aberto', 'd', 'Aberto', 'Baixa', "
                    "'2026-09-01 10:00:00', '2026-09-03 09:00:00')"
                )
            )

        upgrade()  # aplica a migração nova

        with db.engine.connect() as conexao:
            linhas = conexao.execute(text("SELECT titulo, resolvido_em FROM chamado ORDER BY id")).all()

    assert str(linhas[0][1]).startswith("2026-09-02 15:30:00")
    assert linhas[1][1] is None
