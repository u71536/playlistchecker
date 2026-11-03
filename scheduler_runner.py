"""Ежедневная проверка плейлистов отдельным процессом, не внутри Gunicorn."""
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

from app import app, monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_playlists():
    """Проверить все сохранённые плейлисты на удалённые треки."""
    logger.info('Запуск проверки плейлистов')
    try:
        with app.app_context():
            monitor.check_all_playlists()
        logger.info('Проверка плейлистов завершена')
    except Exception:
        logger.exception('Ошибка при проверке плейлистов')


def main():
    hour = int(os.environ.get('CHECK_HOUR', '9'))
    minute = int(os.environ.get('CHECK_MINUTE', '0'))
    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=check_playlists,
        trigger='cron',
        hour=hour,
        minute=minute,
        id='playlist_checker',
    )
    logger.info(
        'Планировщик запущен: проверка каждый день в %02d:%02d (локальное время процесса)',
        hour,
        minute,
    )
    scheduler.start()


if __name__ == '__main__':
    main()
