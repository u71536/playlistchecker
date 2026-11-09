"""Ежедневная проверка плейлистов отдельным процессом, не внутри Gunicorn."""
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

from app import app, monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_playlists():
    """Проверить плейлисты пользователей, у которых сейчас выбранный час."""
    logger.info('Запуск проверки плейлистов')
    try:
        with app.app_context():
            monitor.check_due_playlists()
        logger.info('Проверка плейлистов завершена')
    except Exception:
        logger.exception('Ошибка при проверке плейлистов')


def main():
    minute = int(os.environ.get('CHECK_MINUTE', '0'))
    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=check_playlists,
        trigger='cron',
        minute=minute,
        id='playlist_checker',
    )
    logger.info(
        'Планировщик запущен: каждый час в минуту %02d, по часу пользователя',
        minute,
    )
    scheduler.start()


if __name__ == '__main__':
    main()
