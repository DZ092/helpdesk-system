"""Agregações do dashboard (visual novo, Fase 1)."""

from datetime import date, datetime, timedelta

import pytest

import metricas
from extensions import db
from models import Chamado

# Quinta-feira, 24/09/2026, 15h UTC (12h em Brasília). A semana dela começa
# na segunda 21/09.
AGORA = datetime(2026, 9, 24, 15, 0)


def _chamado(criado_em, status="Aberto", prioridade="Média", setor="Financeiro", resolvido_em=None):
    chamado = Chamado(
        usuario="Maria",
        setor=setor,
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status=status,
        prioridade=prioridade,
        criado_em=criado_em,
        resolvido_em=resolvido_em,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


# ------------------------------------------------------------------ período
def test_inicio_do_periodo_30_dias():
    assert metricas.inicio_do_periodo("30", AGORA) == AGORA - timedelta(days=30)


def test_inicio_do_periodo_tudo_nao_tem_limite():
    assert metricas.inicio_do_periodo("tudo", AGORA) is None


def test_inicio_do_periodo_chave_invalida_usa_o_padrao():
    assert metricas.chave_de_periodo_valida("abacaxi") == "30"
    assert metricas.chave_de_periodo_valida(None) == "30"
    assert metricas.inicio_do_periodo("abacaxi", AGORA) == AGORA - timedelta(days=30)


# ------------------------------------------------------------------ kpis
def test_kpis_com_banco_vazio(app):
    resultado = metricas.kpis(None)

    assert resultado["total"] == 0
    assert resultado["pct_resolvidos"] == 0
    assert resultado["tempo_medio"] is None


def test_kpis_contam_por_status(app):
    ontem = AGORA - timedelta(days=1)
    _chamado(ontem, status="Aberto")
    _chamado(ontem, status="Aberto")
    _chamado(ontem, status="Em andamento")
    _chamado(ontem, status="Resolvido", resolvido_em=ontem + timedelta(hours=2))

    resultado = metricas.kpis(None)

    assert resultado["total"] == 4
    assert resultado["abertos"] == 2
    assert resultado["em_andamento"] == 1
    assert resultado["em_aberto"] == 3
    assert resultado["resolvidos"] == 1
    assert resultado["pct_resolvidos"] == 25


def test_kpis_ignoram_chamados_criados_antes_do_periodo(app):
    _chamado(AGORA - timedelta(days=40))
    _chamado(AGORA - timedelta(days=5))

    resultado = metricas.kpis(AGORA - timedelta(days=30))

    assert resultado["total"] == 1


# ------------------------------------------------------------------ tempo médio
def test_tempo_medio_usa_resolvido_em(app):
    inicio = AGORA - timedelta(days=3)
    _chamado(inicio, status="Resolvido", resolvido_em=inicio + timedelta(hours=2))
    _chamado(inicio, status="Resolvido", resolvido_em=inicio + timedelta(hours=4))

    assert metricas.tempo_medio_resolucao(None) == timedelta(hours=3)


def test_tempo_medio_ignora_resolucoes_fora_do_periodo(app):
    antigo = AGORA - timedelta(days=60)
    _chamado(antigo, status="Resolvido", resolvido_em=antigo + timedelta(hours=10))
    recente = AGORA - timedelta(days=2)
    _chamado(recente, status="Resolvido", resolvido_em=recente + timedelta(hours=1))

    assert metricas.tempo_medio_resolucao(AGORA - timedelta(days=30)) == timedelta(hours=1)


def test_tempo_medio_no_periodo_tudo_inclui_resolucoes_antigas(app):
    antigo = AGORA - timedelta(days=400)
    _chamado(antigo, status="Resolvido", resolvido_em=antigo + timedelta(hours=10))
    recente = AGORA - timedelta(days=2)
    _chamado(recente, status="Resolvido", resolvido_em=recente + timedelta(hours=2))

    assert metricas.tempo_medio_resolucao(None) == timedelta(hours=6)


# ------------------------------------------------------------------ distribuições
def test_por_prioridade_inclui_zeros_na_ordem_oficial(app):
    _chamado(AGORA, prioridade="Alta")

    assert metricas.por_prioridade(None) == [("Baixa", 0), ("Média", 0), ("Alta", 1), ("Crítica", 0)]


def test_por_status_inclui_zeros_na_ordem_oficial(app):
    _chamado(AGORA, status="Resolvido", resolvido_em=AGORA)

    assert metricas.por_status(None) == [("Aberto", 0), ("Em andamento", 0), ("Resolvido", 1)]


def test_por_setor_ordena_do_maior_para_o_menor_e_respeita_o_limite(app):
    for setor, quantidade in [("TI", 3), ("RH", 2), ("Financeiro", 1), ("Comercial", 1),
                              ("Jurídico", 1), ("Compras", 1), ("Logística", 1)]:
        for _ in range(quantidade):
            _chamado(AGORA, setor=setor)

    resultado = metricas.por_setor(None)

    assert len(resultado) == 6
    assert resultado[0] == ("TI", 3)
    assert resultado[1] == ("RH", 2)


# ------------------------------------------------------------------ evolução
def test_evolucao_semanal_tem_8_semanas_terminando_na_atual(app):
    semanas = metricas.evolucao_semanal(AGORA)

    assert len(semanas) == 8
    assert semanas[-1]["inicio"] == date(2026, 9, 21)
    assert semanas[0]["inicio"] == date(2026, 8, 3)
    assert all(s["criados"] == 0 and s["resolvidos"] == 0 for s in semanas)


def test_evolucao_semanal_agrupa_no_fuso_de_brasilia(app):
    # 21/09 02h UTC = domingo 20/09 23h em Brasília → semana de 14/09.
    _chamado(datetime(2026, 9, 21, 2, 0))

    semanas = {s["inicio"]: s for s in metricas.evolucao_semanal(AGORA)}

    assert semanas[date(2026, 9, 14)]["criados"] == 1
    assert semanas[date(2026, 9, 21)]["criados"] == 0


def test_evolucao_semanal_conta_resolvidos_pela_data_de_resolucao(app):
    _chamado(datetime(2026, 9, 8, 15, 0), status="Resolvido", resolvido_em=datetime(2026, 9, 22, 15, 0))

    semanas = {s["inicio"]: s for s in metricas.evolucao_semanal(AGORA)}

    assert semanas[date(2026, 9, 7)]["criados"] == 1
    assert semanas[date(2026, 9, 21)]["resolvidos"] == 1
    assert semanas[date(2026, 9, 7)]["resolvidos"] == 0


# ------------------------------------------------------------------ formatação
@pytest.mark.parametrize(
    "duracao, esperado",
    [
        (None, "—"),
        (timedelta(0), "0min"),
        (timedelta(minutes=45), "45min"),
        (timedelta(hours=6, minutes=20), "6h20"),
        (timedelta(days=2, hours=4, minutes=30), "2d 4h"),
    ],
)
def test_formatar_duracao(duracao, esperado):
    assert metricas.formatar_duracao(duracao) == esperado
