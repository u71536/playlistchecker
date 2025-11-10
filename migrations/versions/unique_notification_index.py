"""Make notification history index unique to prevent duplicate notifications

Revision ID: ad0c584cc8c9
Revises: 82848fa0ea05
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad0c584cc8c9'
down_revision = '82848fa0ea05'
branch_labels = None
depends_on = None


def upgrade():
    # Удаляем старый не-уникальный индекс
    with op.batch_alter_table('notification_history', schema=None) as batch_op:
        batch_op.drop_index('idx_unique_notification')
        # Создаем уникальный индекс
        batch_op.create_index('idx_unique_notification', 
                            ['user_id', 'playlist_id', 'track_service_id', 'notification_type'], 
                            unique=True)


def downgrade():
    # Возвращаем не-уникальный индекс
    with op.batch_alter_table('notification_history', schema=None) as batch_op:
        batch_op.drop_index('idx_unique_notification')
        batch_op.create_index('idx_unique_notification', 
                            ['user_id', 'playlist_id', 'track_service_id', 'notification_type'], 
                            unique=False)

