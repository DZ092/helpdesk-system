"""adiciona resolvido_em ao chamado

Revision ID: e7a1c4d9b2f0
Revises: d835773a6a22
Create Date: 2026-09-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7a1c4d9b2f0'
down_revision = 'd835773a6a22'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chamado', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resolvido_em', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_chamado_resolvido_em'), ['resolvido_em'], unique=False)

    # Backfill: chamados já resolvidos não têm registro de quando isso
    # aconteceu. atualizado_em é o melhor dado disponível — pode ter mudado
    # depois da resolução, mas é o limite superior mais próximo.
    op.execute("UPDATE chamado SET resolvido_em = atualizado_em WHERE status = 'Resolvido'")


def downgrade():
    with op.batch_alter_table('chamado', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chamado_resolvido_em'))
        batch_op.drop_column('resolvido_em')
