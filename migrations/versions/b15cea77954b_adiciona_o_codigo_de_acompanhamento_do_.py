"""adiciona o codigo de acompanhamento do chamado

Revision ID: b15cea77954b
Revises: b3ea6a92ffd9
Create Date: 2026-09-03 22:18:50.537581

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b15cea77954b'
down_revision = 'b3ea6a92ffd9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chamado', schema=None) as batch_op:
        batch_op.add_column(sa.Column('codigo_acompanhamento_hash', sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f('ix_chamado_codigo_acompanhamento_hash'), ['codigo_acompanhamento_hash'], unique=True)


def downgrade():
    with op.batch_alter_table('chamado', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chamado_codigo_acompanhamento_hash'))
        batch_op.drop_column('codigo_acompanhamento_hash')
