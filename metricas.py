"""Indicadores do dashboard (visual novo, Fase 1).

Funções que consultam o banco e devolvem estruturas simples — nada de HTML
aqui. Toda função que depende do "agora" recebe esse instante como parâmetro,
para os testes controlarem o tempo sem mock. As datas no banco são UTC naive
(ver `obter_data_utc` em models.py); o agrupamento por semana acontece no fuso
de exibição, em Python, para dar o mesmo resultado no SQLite dos testes e no
Postgres de produção.
"""

from datetime import timedelta, timezone

from constantes import FUSO_EXIBICAO, PRIORIDADES, STATUS_CHAMADO
from extensions import db
from models import Chamado

PERIODOS = {"7": 7, "30": 30, "90": 90, "tudo": None}
PERIODO_PADRAO = "30"


def chave_de_periodo_valida(chave):
    """A chave pedida, se existir em PERIODOS; senão o período padrão."""
    return chave if chave in PERIODOS else PERIODO_PADRAO


def inicio_do_periodo(chave, agora):
    """Instante (UTC naive) a partir do qual contar; None significa "tudo"."""
    dias = PERIODOS[chave_de_periodo_valida(chave)]
    if dias is None:
        return None
    return agora - timedelta(days=dias)


def _contagem_por(coluna, desde):
    """{valor da coluna: quantidade} dos chamados criados desde `desde`."""
    consulta = db.select(coluna, db.func.count(Chamado.id)).group_by(coluna)
    if desde is not None:
        consulta = consulta.where(Chamado.criado_em >= desde)
    return dict(db.session.execute(consulta).all())


def tempo_medio_resolucao(desde):
    """Média de (resolvido_em − criado_em) das resoluções feitas desde `desde`."""
    consulta = db.select(Chamado.criado_em, Chamado.resolvido_em).where(Chamado.resolvido_em.is_not(None))
    if desde is not None:
        consulta = consulta.where(Chamado.resolvido_em >= desde)
    duracoes = [resolvido - criado for criado, resolvido in db.session.execute(consulta).all()]
    if not duracoes:
        return None
    return sum(duracoes, timedelta()) / len(duracoes)


def kpis(desde):
    """Os quatro números do topo do dashboard.

    As contagens consideram chamados *criados* no período, com o status atual
    de cada um; o tempo médio considera resoluções *feitas* no período.
    """
    por_status_atual = _contagem_por(Chamado.status, desde)
    total = sum(por_status_atual.values())
    abertos = por_status_atual.get("Aberto", 0)
    em_andamento = por_status_atual.get("Em andamento", 0)
    resolvidos = por_status_atual.get("Resolvido", 0)
    return {
        "total": total,
        "abertos": abertos,
        "em_andamento": em_andamento,
        "em_aberto": abertos + em_andamento,
        "resolvidos": resolvidos,
        "pct_resolvidos": round(resolvidos * 100 / total) if total else 0,
        "tempo_medio": tempo_medio_resolucao(desde),
    }


def por_setor(desde, limite=6):
    """Setores com mais chamados no período, do maior para o menor."""
    contagem = _contagem_por(Chamado.setor, desde)
    ordenado = sorted(contagem.items(), key=lambda item: (-item[1], item[0]))
    return ordenado[:limite]


def por_prioridade(desde):
    """Quantidade por prioridade, na ordem de PRIORIDADES, com zeros."""
    contagem = _contagem_por(Chamado.prioridade, desde)
    return [(prioridade, contagem.get(prioridade, 0)) for prioridade in PRIORIDADES]


def por_status(desde):
    """Quantidade por status atual, na ordem de STATUS_CHAMADO, com zeros."""
    contagem = _contagem_por(Chamado.status, desde)
    return [(status, contagem.get(status, 0)) for status in STATUS_CHAMADO]


def _data_local(instante_utc):
    return instante_utc.replace(tzinfo=timezone.utc).astimezone(FUSO_EXIBICAO).date()


def _segunda_feira(dia):
    return dia - timedelta(days=dia.weekday())


def evolucao_semanal(agora, semanas=8):
    """Criados × resolvidos por semana (segunda a domingo, fuso de Brasília).

    Ignora o seletor de período de propósito: mostra sempre as últimas
    `semanas` semanas, terminando na semana de `agora`.
    """
    semana_atual = _segunda_feira(_data_local(agora))
    inicios = [semana_atual - timedelta(weeks=n) for n in range(semanas - 1, -1, -1)]
    criados = dict.fromkeys(inicios, 0)
    resolvidos = dict.fromkeys(inicios, 0)

    # Um dia de folga na consulta; o corte exato é feito abaixo, no fuso local.
    limite = agora - timedelta(weeks=semanas, days=1)

    for (criado_em,) in db.session.execute(db.select(Chamado.criado_em).where(Chamado.criado_em >= limite)).all():
        semana = _segunda_feira(_data_local(criado_em))
        if semana in criados:
            criados[semana] += 1

    for (resolvido_em,) in db.session.execute(
        db.select(Chamado.resolvido_em).where(Chamado.resolvido_em >= limite)
    ).all():
        semana = _segunda_feira(_data_local(resolvido_em))
        if semana in resolvidos:
            resolvidos[semana] += 1

    return [{"inicio": inicio, "criados": criados[inicio], "resolvidos": resolvidos[inicio]} for inicio in inicios]


def formatar_duracao(duracao):
    """"45min", "6h20", "2d 4h" — ou "—" quando não há dado."""
    if duracao is None:
        return "—"
    minutos = int(duracao.total_seconds() // 60)
    if minutos < 60:
        return f"{minutos}min"
    horas, minutos = divmod(minutos, 60)
    if horas < 24:
        return f"{horas}h{minutos:02d}"
    dias, horas = divmod(horas, 24)
    return f"{dias}d {horas}h"
