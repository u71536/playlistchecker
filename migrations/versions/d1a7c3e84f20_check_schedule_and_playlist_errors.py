"""Per-user check hour and playlist check errors

Revision ID: d1a7c3e84f20
Revises: c8f4a91b2e10
Create Date: 2026-11-09 09:20:00.000000

"""
import os

from alembic import op
import sqlalchemy as sa


revision = 'd1a7c3e84f20'
down_revision = 'c8f4a91b2e10'
branch_labels = None
depends_on = None


def _default_hour():
    raw = os.environ.get('CHECK_HOUR', '9')
    try:
        hour = int(raw)
    except (TypeError, ValueError):
        return 9
    if 0 <= hour <= 23:
        return hour
    return 9


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'check_hour',
            sa.Integer(),
            nullable=False,
            server_default='9',
        ))
        batch_op.add_column(sa.Column(
            'timezone',
            sa.String(length=64),
            nullable=False,
            server_default='UTC',
        ))
    op.get_bind().execute(
        sa.text('UPDATE "user" SET check_hour = :hour'),
        {'hour': _default_hour()},
    )

    with op.batch_alter_table('playlist', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_check_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('last_check_failed_at', sa.DateTime(), nullable=True))

    op.drop_index('idx_unique_notification', table_name='notification_history')
    op.create_index(
        'idx_unique_notification',
        'notification_history',
        ['user_id', 'playlist_id', 'track_service_id', 'notification_type'],
        unique=False,
    )


def downgrade():
    op.drop_index('idx_unique_notification', table_name='notification_history')
    op.create_index(
        'idx_unique_notification',
        'notification_history',
        ['user_id', 'playlist_id', 'track_service_id', 'notification_type'],
        unique=True,
    )
    with op.batch_alter_table('playlist', schema=None) as batch_op:
        batch_op.drop_column('last_check_failed_at')
        batch_op.drop_column('last_check_error')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('timezone')
        batch_op.drop_column('check_hour')
