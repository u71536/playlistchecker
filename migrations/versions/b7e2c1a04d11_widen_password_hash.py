"""Widen password_hash so Werkzeug scrypt hashes fit

Revision ID: b7e2c1a04d11
Revises: ad0c584cc8c9
Create Date: 2026-11-01 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e2c1a04d11'
down_revision = 'ad0c584cc8c9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=120),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=255),
            type_=sa.String(length=120),
            existing_nullable=False,
        )
