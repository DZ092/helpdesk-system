"""Abertura, listagem, detalhe e atendimento dos chamados."""

from datetime import datetime

from flask import Blueprint, Response, flash, redirect, render_template, request

from armazenamento import enviar_anexo, extensao_valida
from auditoria import registrar_log
from constantes import PERFIS_TECNICOS, PRIORIDADES, STATUS_CHAMADO
from emails import notificar_tecnicos_novo_chamado
from extensions import db
from formularios import FormularioChamado, FormularioComentarioChamado, FormularioStatusChamado
from models import Anexo, Chamado, Comentario, Usuario
from relatorios import gerar_excel, gerar_pdf
from seguranca import login_required, tecnico_required, usuario_atual
from validacao import inteiro_ou_none

# Máximo de imagens aceitas de uma vez, na abertura do chamado ou num
# comentário. Sem teto, o `request.files.getlist` aceitaria centenas de
# arquivos numa única requisição — mais uma salvaguarda de cota do plano
# gratuito do Cloudinary, como `TAMANHO_MAXIMO_BYTES` em `armazenamento.py`.
MAX_ANEXOS_POR_ENVIO = 5


def _processar_anexos(arquivos, chamado_id, comentario_id=None):
    """Sobe cada arquivo de imagem válido e grava um `Anexo` por upload bem-sucedido.

    Não interrompe o fluxo em caso de arquivo inválido ou falha de upload: um
    anexo é sempre complementar ao texto do chamado ou do comentário, nunca a
    própria ação — silenciosamente ignorar o que não deu certo é melhor que
    perder a abertura do chamado ou o comentário por causa de uma imagem.
    """
    enviados = 0
    for arquivo in arquivos[:MAX_ANEXOS_POR_ENVIO]:
        if not arquivo or not arquivo.filename:
            continue
        if not extensao_valida(arquivo.filename):
            continue

        url = enviar_anexo(arquivo)
        if url is None:
            continue

        db.session.add(
            Anexo(
                chamado_id=chamado_id,
                comentario_id=comentario_id,
                url=url,
                nome_original=arquivo.filename[:255],
            )
        )
        enviados += 1

    if enviados:
        db.session.commit()
    return enviados


chamados = Blueprint("chamados", __name__)


def _primeiro_erro(form):
    """Primeira mensagem de validação do form, ou None se não houve erro.

    Mesmo padrão de `rotas/auth.py`: os templates deste módulo também mostram
    um único bloco `{% if erro %}`, não uma lista por campo.
    """
    for erros_do_campo in form.errors.values():
        if erros_do_campo:
            return erros_do_campo[0]
    return None


def query_chamados_filtrados(args):
    """Monta a consulta de `/chamados` a partir dos parâmetros da URL.

    Compartilhada com a exportação (ver `relatorios.py`): o relatório precisa
    baixar exatamente o que a tela está mostrando, com os mesmos filtros — não
    uma segunda implementação que pode divergir da primeira com o tempo.
    """
    busca = args.get("busca", "").strip()
    status_filtro = args.get("status", "")
    prioridade_filtro = args.get("prioridade", "")
    setor_filtro = args.get("setor", "")
    responsavel_filtro = args.get("responsavel", "")
    data_inicio = args.get("data_inicio", "")
    data_fim = args.get("data_fim", "")

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

    return stmt.order_by(Chamado.id.desc())


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
    form = FormularioChamado()
    if form.validate_on_submit():
        usuario = form.usuario.data.strip()[:100]
        setor = form.setor.data.strip()[:100]
        titulo = form.titulo.data.strip()[:200]
        descricao = form.descricao.data.strip()
        prioridade = form.prioridade.data or "Média"

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

        _processar_anexos(request.files.getlist("anexos"), chamado_id=novo_chamado.id)

        notificar_tecnicos_novo_chamado(novo_chamado)
        flash("Chamado enviado com sucesso! Nossa equipe vai analisar em breve.")
        return redirect("/chamado")
    return render_template("chamado.html", form=form, erro=_primeiro_erro(form))


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

    stmt = query_chamados_filtrados(request.args)

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


# Teto de linhas por exportação. Sem ele, o mesmo filtro vazio que a tela pagina
# em 15 por vez viraria uma consulta e um documento sem limite nenhum — o
# suficiente pra travar a memória do processo num banco grande.
LIMITE_EXPORTACAO = 5000


@chamados.route("/chamados/exportar")
@tecnico_required
def exportar_chamados():
    """Baixa em Excel ou PDF o mesmo recorte filtrado da tela `/chamados`.

    Mais restrita que a própria listagem: `/chamados` é visível a qualquer
    usuário logado, mas gerar um relatório é tratado como uma ação de posse —
    fica no mesmo nível de quem já pode assumir chamado e mudar status.
    """
    formato = request.args.get("formato", "")
    if formato not in ("excel", "pdf"):
        flash("Escolha um formato de exportação válido.")
        return redirect(f"/chamados?{request.query_string.decode()}")

    stmt = query_chamados_filtrados(request.args).limit(LIMITE_EXPORTACAO)
    chamados_lista = db.session.execute(stmt).scalars().all()

    registrar_log(
        "Exportação de relatório",
        f"{len(chamados_lista)} chamado(s) exportado(s) em {formato}",
    )

    agora = datetime.now().strftime("%Y%m%d_%H%M%S")

    if formato == "excel":
        conteudo = gerar_excel(chamados_lista)
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        nome_arquivo = f"chamados_{agora}.xlsx"
    else:
        conteudo = gerar_pdf(chamados_lista)
        mimetype = "application/pdf"
        nome_arquivo = f"chamados_{agora}.pdf"

    return Response(
        conteudo,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
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

    # Só os anexos da abertura (comentario_id nulo); os anexos de comentário
    # vêm juntos de `comentario.anexos` (backref em `models.Anexo`), lidos
    # direto no template — não há por que duplicar a consulta aqui.
    anexos_chamado = (
        db.session.execute(
            db.select(Anexo)
            .where(Anexo.chamado_id == id, Anexo.comentario_id.is_(None))
            .order_by(Anexo.criado_em)
        )
        .scalars()
        .all()
    )

    return render_template(
        "detalhe_chamado.html",
        chamado=chamado,
        comentarios=comentarios,
        anexos_chamado=anexos_chamado,
    )


@chamados.route("/chamados/<int:id>/status", methods=["POST"])
@tecnico_required
def atualizar_status_chamado(id):
    chamado = db.get_or_404(Chamado, id)

    form = FormularioStatusChamado()
    if not form.validate_on_submit():
        flash(_primeiro_erro(form) or "Status inválido.")
        return redirect(f"/chamados/{id}")

    chamado.status = form.status.data

    if chamado.responsavel_id is None:
        chamado.responsavel_id = usuario_atual().id

    db.session.commit()

    registrar_log("Atualização de status", f"Chamado #{chamado.id} alterado para '{chamado.status}'")

    flash(f"Status do chamado atualizado para '{chamado.status}'.")
    return redirect(f"/chamados/{id}")


@chamados.route("/chamados/<int:id>/comentarios", methods=["POST"])
@tecnico_required
def adicionar_comentario(id):
    chamado = db.get_or_404(Chamado, id)

    form = FormularioComentarioChamado()
    if not form.validate_on_submit():
        flash(_primeiro_erro(form) or "A mensagem da atualização não pode ficar vazia.")
        return redirect(f"/chamados/{id}")

    novo_comentario = Comentario(
        chamado_id=chamado.id,
        autor_id=usuario_atual().id,
        mensagem=form.mensagem.data.strip(),
    )
    db.session.add(novo_comentario)
    db.session.commit()

    registrar_log("Comentário adicionado", f"Comentário adicionado ao chamado #{chamado.id}")

    _processar_anexos(
        request.files.getlist("anexos"), chamado_id=chamado.id, comentario_id=novo_comentario.id
    )

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
