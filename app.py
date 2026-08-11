import os
from datetime import datetime, timezone
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chamados.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "chave-secreta-trocar-em-producao")

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]

db = SQLAlchemy(app)
mail = Mail(app)

def obter_data_utc():
    return datetime.now(timezone.utc)

# ==============================================================================
# MODELOS DO BANCO DE DADOS
# ==============================================================================
class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100), nullable=False)
    setor = db.Column(db.String(100), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Aberto")
    prioridade = db.Column(db.String(20), default="Média")
    criado_em = db.Column(db.DateTime, default=obter_data_utc, nullable=False)
    atualizado_em = db.Column(
        db.DateTime, default=obter_data_utc, onupdate=obter_data_utc, nullable=False
    )
    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    responsavel = db.relationship("Usuario", backref="chamados_responsaveis")

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    tipo_usuario = db.Column(db.String(20), nullable=False, default="Usuário")

class Comentario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chamado_id = db.Column(db.Integer, db.ForeignKey("chamado.id"), nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, default=obter_data_utc, nullable=False)
    chamado = db.relationship(
        "Chamado", backref=db.backref("comentarios", lazy=True, cascade="all, delete-orphan")
    )
    autor = db.relationship("Usuario", backref="comentarios")

class LogAuditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    usuario_nome = db.Column(db.String(100), nullable=False)
    acao = db.Column(db.String(100), nullable=False)
    detalhes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=obter_data_utc, nullable=False)

# ==============================================================================
# DECORADORES DE CONTROLE DE ACESSO
# ==============================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def tecnico_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect("/login")
        if session.get("tipo_usuario") not in ("Técnico", "Administrador"):
            flash("Essa ação é restrita a Técnicos e Administradores.")
            return redirect("/chamados")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect("/login")
        if session.get("tipo_usuario") != "Administrador":
            flash("Essa área é restrita a Administradores.")
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# REGISTRO DE LOGS E AUDITORIA
# ==============================================================================
def registrar_log(acao, detalhes=None):
    log = LogAuditoria(
        usuario_id=session.get("usuario_id"),
        usuario_nome=session.get("usuario_nome", "Público"),
        acao=acao,
        detalhes=detalhes,
    )
    db.session.add(log)
    db.session.commit()

# ==============================================================================
# NOTIFICAÇÕES POR E-MAIL
# ==============================================================================
def notificar_tecnicos_novo_chamado(chamado):
    tecnicos = db.session.execute(
        db.select(Usuario).where(Usuario.tipo_usuario.in_(["Técnico", "Administrador"]))
    ).scalars().all()

    destinatarios = [tecnico.email for tecnico in tecnicos]

    if not destinatarios:
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

    try:
        mail.send(mensagem)
    except Exception as erro:
        print(f"[DEBUG] Erro ao enviar e-mail de notificação: {erro}", flush=True)

# ==============================================================================
# ROTAS DA APLICAÇÃO
# ==============================================================================
@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        usuario_existente = db.session.execute(
            db.select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()

        if usuario_existente:
            return render_template("cadastro.html", erro="Este e-mail já está cadastrado.")

        novo_usuario = Usuario(
            nome=request.form["nome"].strip(),
            email=email,
            senha=generate_password_hash(request.form["senha"]),
            tipo_usuario=request.form["tipo_usuario"],
        )
        db.session.add(novo_usuario)
        db.session.commit()
        registrar_log("Cadastro de usuário", f"Novo usuário: {novo_usuario.email} ({novo_usuario.tipo_usuario})")
        return redirect("/login")
    return render_template("cadastro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = db.session.execute(
            db.select(Usuario).where(Usuario.email == request.form["email"].strip().lower())
        ).scalar_one_or_none()

        senha_confere = usuario and check_password_hash(usuario.senha, request.form["senha"])
        if senha_confere:
            session["usuario_id"] = usuario.id
            session["usuario_nome"] = usuario.nome
            session["tipo_usuario"] = usuario.tipo_usuario
            registrar_log("Login realizado")
            return redirect("/dashboard")
        return render_template("login.html", erro="E-mail ou senha inválidos.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
@login_required
def dashboard():
    total = db.session.execute(db.select(db.func.count(Chamado.id))).scalar_one()
    abertos = db.session.execute(db.select(db.func.count(Chamado.id)).where(Chamado.status == "Aberto")).scalar_one()
    andamento = db.session.execute(db.select(db.func.count(Chamado.id)).where(Chamado.status == "Em andamento")).scalar_one()
    resolvidos = db.session.execute(db.select(db.func.count(Chamado.id)).where(Chamado.status == "Resolvido")).scalar_one()

    chamados = db.session.execute(
        db.select(Chamado).order_by(Chamado.id.desc()).limit(5)
    ).scalars().all()

    return render_template(
        "dashboard.html",
        total=total,
        abertos=abertos,
        andamento=andamento,
        resolvidos=resolvidos,
        chamados=chamados
    )

@app.route("/chamado", methods=["GET", "POST"])
def chamado():
    if request.method == "POST":
        novo_chamado = Chamado(
            usuario=request.form["usuario"].strip(),
            setor=request.form["setor"].strip(),
            titulo=request.form["titulo"].strip(),
            descricao=request.form["descricao"].strip(),
            status="Aberto",
            prioridade=request.form["prioridade"],
        )
        db.session.add(novo_chamado)
        db.session.commit()
        registrar_log("Abertura de chamado", f"Chamado #{novo_chamado.id}: {novo_chamado.titulo}")
        notificar_tecnicos_novo_chamado(novo_chamado)
        flash("Chamado enviado com sucesso! Nossa equipe vai analisar em breve.")
        return redirect("/chamado")
    return render_template("chamado.html")

@app.route("/chamados")
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

    if status_filtro:
        stmt = stmt.where(Chamado.status == status_filtro)

    if prioridade_filtro:
        stmt = stmt.where(Chamado.prioridade == prioridade_filtro)

    if setor_filtro:
        stmt = stmt.where(Chamado.setor == setor_filtro)

    if responsavel_filtro == "nenhum":
        stmt = stmt.where(Chamado.responsavel_id.is_(None))
    elif responsavel_filtro:
        stmt = stmt.where(Chamado.responsavel_id == int(responsavel_filtro))

    if data_inicio:
        try:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            stmt = stmt.where(Chamado.criado_em >= inicio)
        except ValueError:
            pass

    if data_fim:
        try:
            fim = datetime.strptime(data_fim, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            stmt = stmt.where(Chamado.criado_em <= fim)
        except ValueError:
            pass

    stmt = stmt.order_by(Chamado.id.desc())

    paginacao = db.paginate(stmt, page=pagina, per_page=15, error_out=False)
    chamados = paginacao.items

    tecnicos = db.session.execute(
        db.select(Usuario)
        .where(Usuario.tipo_usuario.in_(["Técnico", "Administrador"]))
        .order_by(Usuario.nome)
    ).scalars().all()

    setores = db.session.execute(
        db.select(Chamado.setor).distinct().order_by(Chamado.setor)
    ).scalars().all()

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

@app.route("/chamados/<int:id>")
@login_required
def detalhe_chamado(id):
    chamado = db.get_or_404(Chamado, id)

    comentarios = db.session.execute(
        db.select(Comentario).where(Comentario.chamado_id == id).order_by(Comentario.criado_em)
    ).scalars().all()

    return render_template("detalhe_chamado.html", chamado=chamado, comentarios=comentarios)

@app.route("/chamados/<int:id>/status", methods=["POST"])
@tecnico_required
def atualizar_status_chamado(id):
    chamado = db.get_or_404(Chamado, id)

    novo_status = request.form.get("status")
    status_validos = ("Aberto", "Em andamento", "Resolvido")

    if novo_status not in status_validos:
        flash("Status inválido.")
        return redirect(f"/chamados/{id}")

    chamado.status = novo_status

    if chamado.responsavel_id is None:
        chamado.responsavel_id = session["usuario_id"]

    db.session.commit()

    registrar_log("Atualização de status", f"Chamado #{chamado.id} alterado para '{novo_status}'")

    flash(f"Status do chamado atualizado para '{novo_status}'.")
    return redirect(f"/chamados/{id}")

@app.route("/chamados/<int:id>/comentarios", methods=["POST"])
@tecnico_required
def adicionar_comentario(id):
    chamado = db.get_or_404(Chamado, id)

    mensagem = request.form.get("mensagem", "").strip()
    if not mensagem:
        flash("A mensagem da atualização não pode ficar vazia.")
        return redirect(f"/chamados/{id}")

    novo_comentario = Comentario(
        chamado_id=chamado.id,
        autor_id=session["usuario_id"],
        mensagem=mensagem,
    )
    db.session.add(novo_comentario)
    db.session.commit()

    registrar_log("Comentário adicionado", f"Comentário adicionado ao chamado #{chamado.id}")

    flash("Atualização adicionada com sucesso.")
    return redirect(f"/chamados/{id}")

@app.route("/meus-chamados")
@tecnico_required
def meus_chamados():
    chamados = db.session.execute(
        db.select(Chamado)
        .where(Chamado.responsavel_id == session["usuario_id"])
        .order_by(Chamado.id.desc())
    ).scalars().all()

    return render_template("meus_chamados.html", chamados=chamados)

@app.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    usuarios = db.session.execute(
        db.select(Usuario).order_by(Usuario.nome)
    ).scalars().all()

    return render_template("admin_usuarios.html", usuarios=usuarios)

@app.route("/admin/usuarios/<int:id>/tipo", methods=["POST"])
@admin_required
def admin_alterar_tipo(id):
    usuario = db.get_or_404(Usuario, id)

    novo_tipo = request.form.get("tipo_usuario")
    tipos_validos = ("Usuário", "Técnico", "Administrador")

    if novo_tipo not in tipos_validos:
        flash("Tipo de usuário inválido.")
        return redirect("/admin/usuarios")

    if usuario.id == session["usuario_id"] and novo_tipo != "Administrador":
        flash("Você não pode remover seu próprio acesso de Administrador.")
        return redirect("/admin/usuarios")

    usuario.tipo_usuario = novo_tipo
    db.session.commit()

    registrar_log("Alteração de perfil", f"Perfil de {usuario.nome} alterado para '{novo_tipo}'")

    flash(f"Perfil de {usuario.nome} atualizado para '{novo_tipo}'.")
    return redirect("/admin/usuarios")

@app.route("/admin/usuarios/<int:id>/excluir", methods=["POST"])
@admin_required
def admin_excluir_usuario(id):
    usuario = db.get_or_404(Usuario, id)

    if usuario.id == session["usuario_id"]:
        flash("Você não pode excluir a própria conta.")
        return redirect("/admin/usuarios")

    possui_comentarios = db.session.execute(
        db.select(db.func.count(Comentario.id)).where(Comentario.autor_id == usuario.id)
    ).scalar_one() > 0

    possui_chamados = db.session.execute(
        db.select(db.func.count(Chamado.id)).where(Chamado.responsavel_id == usuario.id)
    ).scalar_one() > 0

    if possui_comentarios or possui_chamados:
        flash("Esse usuário já possui chamados ou comentários associados e não pode ser excluído. Altere o perfil dele em vez de excluir.")
        return redirect("/admin/usuarios")

    nome_excluido = usuario.nome
    email_excluido = usuario.email

    db.session.delete(usuario)
    db.session.commit()

    registrar_log("Exclusão de usuário", f"Usuário {nome_excluido} ({email_excluido}) excluído")

    flash(f"Usuário {nome_excluido} excluído com sucesso.")
    return redirect("/admin/usuarios")

@app.route("/admin/logs")
@admin_required
def admin_logs():
    logs = db.session.execute(
        db.select(LogAuditoria).order_by(LogAuditoria.id.desc()).limit(200)
    ).scalars().all()

    return render_template("admin_logs.html", logs=logs)

# ==============================================================================
# EXECUÇÃO DA APLICAÇÃO
# ==============================================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)