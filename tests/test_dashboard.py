"""Dashboard com indicadores e gráficos (visual novo, Fase 1)."""

import re
from datetime import timedelta

from extensions import db
from models import Chamado, obter_data_utc

SENHA = "senha-de-teste"


def _entrar(client, criar_usuario):
    criar_usuario(nome="Ana Admin", email="admin@teste.com", tipo="Administrador")
    client.post("/login", data={"email": "admin@teste.com", "senha": SENHA})


def _chamado(dias_atras=1, status="Aberto", prioridade="Alta", setor="Financeiro", horas_para_resolver=None):
    criado = obter_data_utc() - timedelta(days=dias_atras)
    resolvido = criado + timedelta(hours=horas_para_resolver) if horas_para_resolver is not None else None
    chamado = Chamado(
        usuario="Maria",
        setor=setor,
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status=status,
        prioridade=prioridade,
        criado_em=criado,
        resolvido_em=resolvido,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def test_dashboard_mostra_os_quatro_graficos_com_tabelas_acessiveis(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado()
    _chamado(status="Resolvido", horas_para_resolver=2, setor="TI", prioridade="Baixa")

    html = client.get("/dashboard").get_data(as_text=True)

    assert html.count('role="img"') == 4
    assert html.count('<table class="sr-only">') == 4
    assert 'style="' not in html  # CSP: nada de estilo inline


def test_dashboard_mostra_os_kpis(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado()
    _chamado()
    _chamado(status="Resolvido", horas_para_resolver=2)

    html = client.get("/dashboard").get_data(as_text=True)

    assert re.search(r'Total de chamados</p>\s*<p class="kpi-valor">3</p>', html)
    assert "33% do total" in html
    assert '<p class="kpi-valor">2h00</p>' in html
    assert "2 abertos · 0 em andamento" in html


def test_dashboard_sem_chamados_mostra_estado_vazio(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/dashboard").get_data(as_text=True)

    assert 'role="img"' not in html
    assert "Nenhum chamado neste período." in html
    assert "Nenhum chamado nas últimas 8 semanas." in html


def test_periodo_invalido_usa_30_dias(client, criar_usuario):
    _entrar(client, criar_usuario)

    resposta = client.get("/dashboard?periodo=xyz")

    assert resposta.status_code == 200
    assert re.search(r'href="/dashboard\?periodo=30"\s+aria-current="true"', resposta.get_data(as_text=True))


def test_periodo_filtra_os_indicadores(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado(dias_atras=40)

    html_30 = client.get("/dashboard?periodo=30").get_data(as_text=True)
    html_tudo = client.get("/dashboard?periodo=tudo").get_data(as_text=True)

    assert "Nenhum chamado neste período." in html_30
    assert "Nenhum chamado neste período." not in html_tudo


def test_chamados_recentes_tem_link_para_a_lista(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado()

    html = client.get("/dashboard").get_data(as_text=True)

    assert "Chamados recentes" in html
    assert '<a class="painel-link" href="/chamados">Ver todos</a>' in html


def test_setor_com_html_vai_escapado_no_grafico_de_barras(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado(setor="<script>alert(1)</script>")

    html = client.get("/dashboard").get_data(as_text=True)

    assert "<script>alert(1)" not in html
    assert "&lt;script&gt;" in html
