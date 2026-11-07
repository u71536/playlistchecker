"""Email verification, one-time reset nonce, unique playlist

Revision ID: c8f4a91b2e10
Revises: b7e2c1a04d11
Create Date: 2026-11-06 23:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c8f4a91b2e10'
down_revision = 'b7e2c1a04d11'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'email_verified',
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ))
        batch_op.add_column(sa.Column('email_verify_nonce', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('password_reset_nonce', sa.String(length=64), nullable=True))

    connection = op.get_bind()
    duplicate_ids = connection.execute(sa.text(
        """
        SELECT id FROM playlist
        WHERE id NOT IN (
            SELECT MIN(id) FROM playlist
            GROUP BY user_id, service, service_playlist_id
        )
        """
    )).fetchall()
    for (playlist_id,) in duplicate_ids:
        connection.execute(
            sa.text('DELETE FROM notification WHERE playlist_id = :playlist_id'),
            {'playlist_id': playlist_id},
        )
        connection.execute(
            sa.text('DELETE FROM notification_history WHERE playlist_id = :playlist_id'),
            {'playlist_id': playlist_id},
        )
        connection.execute(
            sa.text('DELETE FROM track WHERE playlist_id = :playlist_id'),
            {'playlist_id': playlist_id},
        )
        connection.execute(
            sa.text('DELETE FROM playlist WHERE id = :playlist_id'),
            {'playlist_id': playlist_id},
        )

    with op.batch_alter_table('playlist', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_user_service_playlist',
            ['user_id', 'service', 'service_playlist_id'],
        )


def downgrade():
    with op.batch_alter_table('playlist', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_service_playlist', type_='unique')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('password_reset_nonce')
        batch_op.drop_column('email_verify_nonce')
        batch_op.drop_column('email_verified')
