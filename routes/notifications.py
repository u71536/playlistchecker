import logging
import os
from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_babel import gettext
from flask_login import current_user, login_required

from extensions import db
from forms import NotificationSettingsForm
from models import Notification, NotificationHistory, PushSubscription, User
from services.notification_service import notification_service
from services.telegram_link import make_start_token, parse_start_token, webhook_authorized

logger = logging.getLogger(__name__)


@login_required
def mark_notification_read(notification_id):
    """Пометить уведомление как прочитанное"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id,
    ).first()
    if not notification:
        return {'status': 'error'}, 404
    notification.is_read = True
    db.session.commit()
    return {'status': 'ok'}


@login_required
def mark_all_notifications_read():
    """Пометить все уведомления пользователя как прочитанные"""
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False,
    ).update({'is_read': True})
    db.session.commit()
    return {'status': 'ok'}


@login_required
def notification_settings():
    """Настройки уведомлений пользователя"""
    form = NotificationSettingsForm()
    if form.validate_on_submit():
        current_user.email_notifications_enabled = form.email_notifications_enabled.data
        current_user.telegram_notifications_enabled = form.telegram_notifications_enabled.data
        current_user.browser_notifications_enabled = form.browser_notifications_enabled.data
        db.session.commit()
        flash(gettext('flash.notification_settings_saved'))
        return redirect(url_for('notification_settings'))

    form.email_notifications_enabled.data = current_user.email_notifications_enabled
    form.telegram_notifications_enabled.data = current_user.telegram_notifications_enabled
    form.browser_notifications_enabled.data = current_user.browser_notifications_enabled
    return render_template('notification_settings.html', form=form)


@login_required
def notification_history():
    """История уведомлений пользователя"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    history_pagination = NotificationHistory.query.filter_by(user_id=current_user.id)\
        .order_by(NotificationHistory.sent_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('notification_history.html', history_pagination=history_pagination)


@login_required
def telegram_connect():
    """Подключение Telegram бота"""
    bot_username = os.environ.get('TELEGRAM_BOT_USERNAME', 'checkingplaylistbot')
    start_token = make_start_token(current_user.id, current_app.config['SECRET_KEY'])
    telegram_url = f'https://t.me/{bot_username}?start={start_token}'
    return redirect(telegram_url)


def telegram_webhook():
    """Webhook для обработки сообщений от Telegram бота"""
    if not webhook_authorized(request.headers.get('X-Telegram-Bot-Api-Secret-Token')):
        logger.warning('Rejected Telegram webhook: missing or invalid secret')
        return {'status': 'unauthorized'}, 401

    try:
        data = request.get_json(silent=True) or {}
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            if text.startswith('/start'):
                parts = text.split()
                user_id = (
                    parse_start_token(parts[1], current_app.config['SECRET_KEY'])
                    if len(parts) > 1 else None
                )
                user = db.session.get(User, user_id) if user_id is not None else None
                if user:
                    user.telegram_chat_id = str(chat_id)
                    if 'username' in message['chat']:
                        user.telegram_username = message['chat']['username']
                    db.session.commit()
                    notification_service.send_telegram_notification(
                        chat_id,
                        f'✅ Telegram успешно подключен к аккаунту {user.username}!\n\n'
                        'Теперь вы будете получать уведомления об изменениях в ваших плейлистах.',
                    )
                    return {'status': 'ok'}
            notification_service.send_telegram_notification(
                chat_id,
                "🤖 Привет! Я бот PlaylistChecker.\n\n"
                "Для подключения перейдите в настройки уведомлений на сайте "
                "и нажмите 'Подключить Telegram'.",
            )
        return {'status': 'ok'}
    except Exception as error:
        logger.error('Ошибка обработки Telegram webhook: %s', error)
        return {'status': 'error'}, 500


@login_required
def push_subscribe():
    """Подписка на push-уведомления"""
    try:
        data = request.get_json()
        existing = PushSubscription.query.filter_by(
            user_id=current_user.id,
            endpoint=data['endpoint'],
        ).first()
        if existing:
            existing.p256dh_key = data['keys']['p256dh']
            existing.auth_key = data['keys']['auth']
            existing.user_agent = request.headers.get('User-Agent', '')
            existing.last_used = datetime.utcnow()
        else:
            subscription = PushSubscription(
                user_id=current_user.id,
                endpoint=data['endpoint'],
                p256dh_key=data['keys']['p256dh'],
                auth_key=data['keys']['auth'],
                user_agent=request.headers.get('User-Agent', ''),
            )
            db.session.add(subscription)
        db.session.commit()
        return {'status': 'success'}
    except Exception as error:
        logger.error('Ошибка подписки на push-уведомления: %s', error)
        return {'status': 'error', 'message': str(error)}, 500


@login_required
def push_unsubscribe():
    """Отписка от push-уведомлений"""
    try:
        data = request.get_json()
        subscription = PushSubscription.query.filter_by(
            user_id=current_user.id,
            endpoint=data['endpoint'],
        ).first()
        if subscription:
            db.session.delete(subscription)
            db.session.commit()
        return {'status': 'success'}
    except Exception as error:
        logger.error('Ошибка отписки от push-уведомлений: %s', error)
        return {'status': 'error', 'message': str(error)}, 500


def get_vapid_public_key():
    """Получить публичный VAPID ключ для push-уведомлений"""
    public_key = os.environ.get('VAPID_PUBLIC_KEY')
    if not public_key:
        return {'error': 'VAPID ключ не настроен'}, 500
    return {'publicKey': public_key}


def register_notification_routes(app):
    app.add_url_rule(
        '/notifications/<int:notification_id>/read',
        view_func=mark_notification_read,
        methods=['POST'],
    )
    app.add_url_rule(
        '/notifications/read-all',
        view_func=mark_all_notifications_read,
        methods=['POST'],
    )
    app.add_url_rule(
        '/settings/notifications',
        view_func=notification_settings,
        methods=['GET', 'POST'],
    )
    app.add_url_rule('/notification_history', view_func=notification_history)
    app.add_url_rule('/telegram/connect', view_func=telegram_connect)
    app.add_url_rule('/api/telegram/webhook', view_func=telegram_webhook, methods=['POST'])
    app.add_url_rule('/api/push/subscribe', view_func=push_subscribe, methods=['POST'])
    app.add_url_rule('/api/push/unsubscribe', view_func=push_unsubscribe, methods=['POST'])
    app.add_url_rule('/api/push/vapid-public-key', view_func=get_vapid_public_key)
