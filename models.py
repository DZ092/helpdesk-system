"""Tabelas do banco de dados.

As datas são gravadas sempre em UTC "naive" (ver `obter_data_utc`); a conversão
para o horário de Brasília acontece só na exibição.
"""

from datetime import datetime, timezone

from constantes import PERFIS_TECNICOS
from extensions import db

def obter_data_utc():
    """Momento atual em UTC, sem fuso embutido.

    O SQLite não guarda o fuso horário, então gravar um datetime "aware" faria a
    informação de fuso ser silenciosamente descartada na escrita e reaparecer
    como naive na leitura. Padronizamos em UTC naive para que o que é gravado e
    o que é lido sejam sempre o mesmo valor; a conversão para o horário de
    Brasília acontece só na hora de exibir (ver filtro `data_local`).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100), nullable=False)
    setor = db.Column(db.String(100), nullable=False, index=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Aberto", index=True)
    prioridade = db.Column(db.String(20), default="Média", index=True)
    criado_em = db.Column(db.DateTime, default=obter_data_utc, nullable=False, index=True)
    atualizado_em = db.Column(
        db.DateTime, default=obter_data_utc, onupdate=obter_data_utc, nullable=False
    )
    responsavel_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=True, index=True
    )
    responsavel = db.relationship("Usuario", backref="chamados_responsaveis")


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    tipo_usuario = db.Column(db.String(20), nullable=False, default="Usuário")

    @property
    def eh_tecnico(self):
        return self.tipo_usuario in PERFIS_TECNICOS

    @property
    def eh_admin(self):
        return self.tipo_usuario == "Administrador"


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
