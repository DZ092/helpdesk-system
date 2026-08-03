from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chamados.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "chave-secreta-trocar-em-producao"
db = SQLAlchemy(app)


class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100), nullable=False)
    setor = db.Column(db.String(100), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Aberto")
    prioridade = db.Column(db.String(20), default="Média")
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
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
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    chamado = db.relationship(
        "Chamado", backref=db.backref("comentarios", lazy=True, cascade="all, delete-orphan")
    )
    autor = db.relationship("Usuario", backref="comentarios")


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


@app.route("/")
def home():
    return redirect("/dashboard")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if Usuario.query.filter_by(email=email).first():
            return render_template("cadastro.html", erro="Este e-mail já está cadastrado.")

        novo_usuario = Usuario(
            nome=request.form["nome"].strip(),
            email=email,
            senha=generate_password_hash(request.form["senha"]),
            tipo_usuario=request.form["tipo_usuario"],
        )
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect("/login")
    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = Usuario.query.filter_by(email=request.form["email"].strip().lower()).first()
        senha_confere = usuario and check_password_hash(usuario.senha, request.form["senha"])

        if senha_confere:
            session["usuario_id"] = usuario.id
            session["usuario_nome"] = usuario.nome
            session["tipo_usuario"] = usuario.tipo_usuario
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
    total = Chamado.query.count()
    abertos = Chamado.query.filter_by(status="Aberto").count()
    andamento = Chamado.query.filter_by(status="Em andamento").count()
    resolvidos = Chamado.query.filter_by(status="Resolvido").count()
    chamados = Chamado.query.order_by(Chamado.id.desc()).limit(5).all()
    return render_template(
        "dashboard.html", total=total, abertos=abertos, andamento=andamento,
        resolvidos=resolvidos, chamados=chamados
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
        flash("Chamado enviado com sucesso! Nossa equipe vai analisar em breve.")
        return redirect("/chamado")
    return render_template("chamado.html")


@app.route("/chamados")
@login_required
def lista_chamados():
    busca = request.args.get("busca", "").strip()
    status_filtro = request.args.get("status", "")
    query = Chamado.query
    if busca:
        query = query.filter(Chamado.titulo.ilike(f"%{busca}%"))
    if status_filtro:
        query = query.filter_by(status=status_filtro)
    chamados = query.order_by(Chamado.id.desc()).all()
    return render_template(
        "chamados.html", chamados=chamados, busca=busca, status_filtro=status_filtro
    )


@app.route("/chamados/<int:id>")
@login_required
def detalhe_chamado(id):
    chamado = Chamado.query.get_or_404(id)
    comentarios = Comentario.query.filter_by(chamado_id=id).order_by(Comentario.criado_em).all()
    return render_template("detalhe_chamado.html", chamado=chamado, comentarios=comentarios)


@app.route("/chamados/<int:id>/status", methods=["POST"])
@tecnico_required
def atualizar_status_chamado(id):
    chamado = Chamado.query.get_or_404(id)
    novo_status = request.form.get("status")
    if novo_status not in ("Em andamento", "Resolvido"):
        flash("Status inválido.")
    elif chamado.status == "Resolvido":
        flash("Este chamado já está resolvido.")
    else:
        chamado.status = novo_status
        if chamado.responsavel_id is None:
            chamado.responsavel_id = session["usuario_id"]
        db.session.commit()
        flash(
            "Chamado iniciado e atribuído a você."
            if novo_status == "Em andamento"
            else "Chamado marcado como resolvido."
        )
    return redirect(f"/chamados/{id}")


@app.route("/chamados/<int:id>/comentarios", methods=["POST"])
@tecnico_required
def adicionar_comentario(id):
    chamado = Chamado.query.get_or_404(id)
    mensagem = request.form.get("mensagem", "").strip()
    if not mensagem:
        flash("Escreva uma atualização antes de enviar.")
        return redirect(f"/chamados/{id}")

    if chamado.responsavel_id is None:
        chamado.responsavel_id = session["usuario_id"]
    chamado.atualizado_em = datetime.utcnow()
    db.session.add(
        Comentario(chamado_id=chamado.id, autor_id=session["usuario_id"], mensagem=mensagem)
    )
    db.session.commit()
    flash("Atualização adicionada ao chamado.")
    return redirect(f"/chamados/{id}")


def preparar_banco():
    db.create_all()
    colunas = {linha[1] for linha in db.session.execute(text("PRAGMA table_info(chamado)"))}
    if "criado_em" not in colunas:
        db.session.execute(text("ALTER TABLE chamado ADD COLUMN criado_em DATETIME"))
    if "atualizado_em" not in colunas:
        db.session.execute(text("ALTER TABLE chamado ADD COLUMN atualizado_em DATETIME"))
    if "responsavel_id" not in colunas:
        db.session.execute(text("ALTER TABLE chamado ADD COLUMN responsavel_id INTEGER"))

    agora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db.session.execute(text("UPDATE chamado SET criado_em = :agora WHERE criado_em IS NULL"), {"agora": agora})
    db.session.execute(text("UPDATE chamado SET atualizado_em = :agora WHERE atualizado_em IS NULL"), {"agora": agora})
    db.session.commit()


with app.app_context():
    preparar_banco()


if __name__ == "__main__":
    app.run(debug=True)
