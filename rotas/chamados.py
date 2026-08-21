"""Abertura, listagem, detalhe e atendimento dos chamados."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request

from auditoria import registrar_log
from constantes import PERFIS_TECNICOS, PRIORIDADES, STATUS_CHAMADO
from emails import notificar_tecnicos_novo_chamado
from extensions import db
from models import Chamado, Comentario, Usuario
from seguranca import login_required, tecnico_required, usuario_atual
from validacao import campo_obrigatorio, inteiro_ou_none

chamados = Blueprint("chamados", __name__)


@chamados.route("/")
def home():
    return redirect("/dashboard")


@chamados.route("/dashboard")
@login_required
def dashboard():
    # Uma única consulta agrupada no lugar de quatro COUNT separados.
    contagens = dict(
        db.session.execute(
            db.select(Chamado.status, db.func.count(Chamado.id)).group_by(Chamado.status)
        ).all()
    )

    chamados = (
        db.session.execute(db.select(Chamado).order_by(Chamado.id.desc()).limit(5))
        .scalars()
        .all()
    )

    return render_template(
        "dashboard.html",
        total=sum(contagens.values()),
        abertos=contagens.get("Aberto", 0),
        andamento=contagens.get("Em andamento", 0),
        resolvidos=contagens.get("Resolvido", 0),
        chamados=chamados,
    )


@chamados.route("/chamado", methods=["GET", "POST"])
def chamado():
    if request.method == "POST":
        usuario = campo_obrigatorio("usuario", 100)
        setor = campo_obrigatorio("setor", 100)
        titulo = campo_obrigatorio("titulo", 200)
        descricao = request.form.get("descricao", "").strip()
        prioridade = request.form.get("prioridade", "Média")

        if not all((usuario, setor, titulo, descricao)):
            return render_template(
                "chamado.html", erro="Preencha todos os campos do chamado."
            )

        # Sem essa checagem, qualquer valor enviado no formulário era gravado
        # como prioridade e escapava dos filtros e das cores da interface.
        if prioridade not in PRIORIDADES:
            prioridade = "Média"

        novo_chamado = Chamado(
            usuario=usuario,
            setor=setor,
            titulo=titulo,
            descricao=descricao,
            status="Aberto",
            prioridade=prioridade,
        )
        db.session.add(novo_chamado)
        db.session.commit()
        registrar_log("Abertura de chamado", f"Chamado #{novo_chamado.id}: {novo_chamado.titulo}")
        notificar_tecnicos_novo_chamado(novo_chamado)
        flash("Chamado enviado com sucesso! Nossa equipe vai analisar em breve.")
        return redirect("/chamado")
    return render_template("chamado.html")


@chamados.route("/chamados")
@login_required
def lista_chamados():
    busca = request.args.get("busca", "").strip()
    status_filtro = request.args.get("status", "")
    prioridade_filtro = request.args.get("prioridade", "")
    setor_filtro = request.args.get("setor", "")
    responsavel_filtro = request.args.get("responsavel", "")
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")
    pagina = request.args.get("pagina", 1, type=int)

    stmt = db.select(Chamado)

    if busca:
        stmt = stmt.where(Chamado.titulo.ilike(f"%{busca}%"))

    if status_filtro in STATUS_CHAMADO:
        stmt = stmt.where(Chamado.status == status_filtro)

    if prioridade_filtro in PRIORIDADES:
        stmt = stmt.where(Chamado.prioridade == prioridade_filtro)

    if setor_filtro:
        stmt = stmt.where(Chamado.setor == setor_filtro)

    if responsavel_filtro == "nenhum":
        stmt = stmt.where(Chamado.responsavel_id.is_(None))
    elif responsavel_filtro:
        # `?responsavel=abc` derrubava a página com erro 500 no int().
        responsavel_id = inteiro_ou_none(responsavel_filtro)
        if responsavel_id is not None:
            stmt = stmt.where(Chamado.responsavel_id == responsavel_id)

    if data_inicio:
        try:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
            stmt = stmt.where(Chamado.criado_em >= inicio)
        except ValueError:
            pass

    if data_fim:
        try:
            fim = datetime.strptime(data_fim, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            stmt = stmt.where(Chamado.criado_em <= fim)
        except ValueError:
            pass

    stmt = stmt.order_by(Chamado.id.desc())

    paginacao = db.paginate(stmt, page=pagina, per_page=15, error_out=False)
    chamados = paginacao.items

    tecnicos = (
        db.session.execute(
            db.select(Usuario)
            .where(Usuario.tipo_usuario.in_(PERFIS_TECNICOS))
            .order_by(Usuario.nome)
        )
        .scalars()
        .all()
    )

    setores = (
        db.session.execute(db.select(Chamado.setor).distinct().order_by(Chamado.setor))
        .scalars()
        .all()
    )

    return render_template(
        "chamados.html",
        chamados=chamados,
        busca=busca,
        status_filtro=status_filtro,
        prioridade_filtro=prioridade_filtro,
        setor_filtro=setor_filtro,
        responsavel_filtro=responsavel_filtro,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tecnicos=tecnicos,
        setores=setores,
        paginacao=paginacao,
    )


@chamados.route("/chamados/<int:id>")
@login_required
def detalhe_chamado(id):
    chamado = db.get_or_404(Chamado, id)

    comentarios = (
        db.session.execute(
            db.select(Comentario)
            .where(Comentario.chamado_id == id)
            .order_by(Comentario.criado_em)
        )
        .scalars()
        .all()
    )

    return render_template("detalhe_chamado.html", chamado=chamado, comentarios=comentarios)


@chamados.route("/chamados/<int:id>/status", methods=["POST"])
@tecnico_required
def atualizar_status_chamado(id):
    chamado = db.get_or_404(Chamado, id)

    novo_status = request.form.get("status")

    if novo_status not in STATUS_CHAMADO:
        flash("Status inválido.")
        return redirect(f"/chamados/{id}")

    chamado.status = novo_status

    if chamado.responsavel_id is None:
        chamado.responsavel_id = usuario_atual().id

    db.session.commit()

    registrar_log("Atualização de status", f"Chamado #{chamado.id} alterado para '{novo_status}'")

    flash(f"Status do chamado atualizado para '{novo_status}'.")
    return redirect(f"/chamados/{id}")


@chamados.route("/chamados/<int:id>/comentarios", methods=["POST"])
@tecnico_required
def adicionar_comentario(id):
    chamado = db.get_or_404(Chamado, id)

    mensagem = request.form.get("mensagem", "").strip()
    if not mensagem:
        flash("A mensagem da atualização não pode ficar vazia.")
        return redirect(f"/chamados/{id}")

    novo_comentario = Comentario(
        chamado_id=chamado.id,
        autor_id=usuario_atual().id,
        mensagem=mensagem,
    )
    db.session.add(novo_comentario)
    db.session.commit()

    registrar_log("Comentário adicionado", f"Comentário adicionado ao chamado #{chamado.id}")

    flash("Atualização adicionada com sucesso.")
    return redirect(f"/chamados/{id}")


@chamados.route("/meus-chamados")
@tecnico_required
def meus_chamados():
    chamados = (
        db.session.execute(
            db.select(Chamado)
            .where(Chamado.responsavel_id == usuario_atual().id)
            .order_by(Chamado.id.desc())
        )
        .scalars()
        .all()
    )

    return render_template("meus_chamados.html", chamados=chamados)
