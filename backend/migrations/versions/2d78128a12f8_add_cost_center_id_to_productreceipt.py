"""Add cost_center_id to ProductReceipt

Revision ID: 2d78128a12f8
Revises: 6e822fdf5191
Create Date: 2026-02-06 10:43:30.855364

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d78128a12f8'
down_revision = '6e822fdf5191'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('product_receipts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cost_center_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_product_receipts_cost_center_id_cost_centers'), 'cost_centers', ['cost_center_id'], ['id'])


def downgrade():
    with op.batch_alter_table('product_receipts', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_product_receipts_cost_center_id_cost_centers'), type_='foreignkey')
        batch_op.drop_column('cost_center_id')
