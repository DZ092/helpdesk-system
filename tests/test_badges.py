"""Badges de status e prioridade (visual novo, Fase 2)."""

import re
from pathlib import Path

import pytest

from extensions import db
from models import Chamado

RAIZ = Path(__file__).resolve().parent.parent
SENHA = "senha-de-teste"
EMOJIS_DE_STATUS = ("🔴", "🟡", "🟢")


def _macros(app):
    return app.jinja_env.get_template("_badges.html").module


@pytest.mark.parametrize(
    "status, classe",
    [
        ("Aberto", "status-aberto"),
        ("Em andamento", "status-andamento"),
        ("Resolvido", "status-resolvido"),
    ],
)
def test_badge_status_tem_classe_e_texto_certos(app, status, classe):
    html = str(_macros(app).badge_status(status))

    assert html == f'<span class="status {classe}">{status}</span>'


@pytest.mark.parametrize("status", ["Cancelado", "", None])
def test_status_desconhecido_cai_em_resolvido(app, status):
    html = str(_macros(app).badge_status(status))

    assert html == '<span class="status status-resolvido">Resolvido</span>'


@pytest.mark.parametrize(
    "prioridade, classe",
    [
        ("Baixa", "prioridade-baixa"),
        ("Média", "prioridade-media"),
        ("Alta", "prioridade-alta"),
        ("Crítica", "prioridade-critica"),
    ],
)
def test_badge_prioridade_tem_classe_e_texto_certos(app, prioridade, classe):
    html = str(_macros(app).badge_prioridade(prioridade))

    assert html == f'<span class="prioridade {classe}">{prioridade}</span>'


@pytest.mark.parametrize("prioridade", ["Urgente", "", None])
def test_prioridade_desconhecida_cai_em_media(app, prioridade):
    html = str(_macros(app).badge_prioridade(prioridade))

    assert html == '<span class="prioridade prioridade-media">Média</span>'


def test_bolinha_do_status_vem_do_css():
    css = (RAIZ / "static" / "css" / "style.css").read_text(encoding="utf-8")
    regra = re.search(r"\.status::before\s*\{([^}]*)\}", css)

    assert regra, "falta a regra .status::before"
    assert "background: currentColor" in regra.group(1)


def test_dashboard_usa_os_badges_sem_emoji(client, criar_usuario):
    criar_usuario(nome="Ana Admin", email="admin@teste.com", tipo="Administrador")
    client.post("/login", data={"email": "admin@teste.com", "senha": SENHA})
    for status in ("Aberto", "Em andamento", "Resolvido"):
        db.session.add(
            Chamado(usuario="Maria", setor="TI", titulo=f"Chamado {status}",
                    descricao="Teste", status=status, prioridade="Crítica")
        )
    db.session.commit()

    html = client.get("/dashboard").get_data(as_text=True)

    assert '<span class="status status-andamento">Em andamento</span>' in html
    assert '<span class="prioridade prioridade-critica">Crítica</span>' in html
    for emoji in EMOJIS_DE_STATUS:
        assert emoji not in html
