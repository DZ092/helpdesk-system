"""adiciona o autor do chamado

Revision ID: f3b8d2a7c1e5
Revises: e7a1c4d9b2f0
Create Date: 2026-10-18 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3b8d2a7c1e5'
down_revision = 'e7a1c4d9b2f0'
branch_labels = None
depends_on = None


def upgrade():
    # Sem backfill: os chamados existentes guardam o nome de quem abriu como
    # texto livre (coluna `usuario`), que não identifica uma conta com
    # segurança. Eles ficam com autor None e continuam visíveis à equipe
    # técnica, como antes.
    with op.batch_alter_table('chamado', schema=None) as batch_op:
        batch_op.add_column(sa.Column('autor_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_chamado_autor_id'), ['autor_id'], unique=False)
        batch_op.create_foreign_key('fk_chamado_autor_id_usuario', 'usuario', ['autor_id'], ['id'])


def downgrade():
    with op.batch_alter_table('chamado', schema=None) as batch_op:
        batch_op.drop_constraint('fk_chamado_autor_id_usuario', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_chamado_autor_id'))
        batch_op.drop_column('autor_id')
