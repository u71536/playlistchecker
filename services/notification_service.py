import smtplib
import requests
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import os

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений по email, Telegram и браузерных push-уведомлений"""
    
    def __init__(self):
        self.email_config = {
            'server': os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
            'port': int(os.environ.get('MAIL_PORT', 587)),
            'use_tls': os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true',
            'username': os.environ.get('MAIL_USERNAME'),
            'password': os.environ.get('MAIL_PASSWORD'),
            'default_sender': os.environ.get('MAIL_DEFAULT_SENDER')
        }
        
        self.telegram_config = {
            'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN'),
            'api_url': 'https://api.telegram.org/bot'
        }
        
        self.webpush_config = {
            'vapid_public_key': os.environ.get('VAPID_PUBLIC_KEY'),
            'vapid_private_key': os.environ.get('VAPID_PRIVATE_KEY'),
            'vapid_email': os.environ.get('VAPID_EMAIL')
        }
    
    def send_email_notification(self, user_email, subject, message,
                                track_name=None, playlist_name=None):
        """Отправить email уведомление"""
        if not all([self.email_config['username'], self.email_config['password']]):
            logger.warning("Email настройки не настроены, "
                           "пропускаем отправку email")
            return False
        
        try:
            # Определяем адрес отправителя
            from_address = self.email_config.get('default_sender') or self.email_config.get('username')
            if not from_address or '@' not in from_address:
                logger.error("Некорректный адрес отправителя. Задайте MAIL_DEFAULT_SENDER или MAIL_USERNAME в виде полной почты (example@domain.com)")
                return False

            # Создаем сообщение
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_address
            msg['To'] = user_email
            
            # Текстовая версия
            text_content = f"""
PlaylistChecker - Уведомление

{message}

Плейлист: {playlist_name or 'Неизвестно'}
Трек: {track_name or 'Неизвестно'}

Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

---
Это автоматическое уведомление от PlaylistChecker
            """
            
            # HTML версия
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
        .track-info {{ background: white; padding: 15px; border-radius: 5px; margin: 15px 0; 
                       border-left: 4px solid #667eea; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #667eea; 
                color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 PlaylistChecker</h1>
            <p>Уведомление об изменении плейлиста</p>
        </div>
        <div class="content">
            <h2>Обнаружены изменения!</h2>
            <p>{message}</p>
            
            <div class="track-info">
                <strong>📋 Плейлист:</strong> {playlist_name or 'Неизвестно'}<br>
                <strong>🎵 Трек:</strong> {track_name or 'Неизвестно'}<br>
                <strong>🕒 Время:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}
            </div>
            
            <p>Зайдите в свой аккаунт PlaylistChecker, чтобы увидеть подробности.</p>
        </div>
        <div class="footer">
            <p>Это автоматическое уведомление от PlaylistChecker</p>
        </div>
    </div>
</body>
</html>
            """
            
            # Прикрепляем части сообщения
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Отправляем email
            server = smtplib.SMTP(self.email_config['server'], self.email_config['port'])
            if self.email_config['use_tls']:
                server.starttls()
            
            server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email уведомление отправлено на {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки email уведомления: {str(e)}")
            return False
    
    def send_telegram_notification(self, chat_id, message, track_name=None, playlist_name=None):
        """Отправить Telegram уведомление"""
        if not self.telegram_config['bot_token']:
            logger.warning("Telegram bot token не настроен, пропускаем отправку в Telegram")
            return False
        
        try:
            # Форматируем сообщение для Telegram
            telegram_message = f"""
🎵 *PlaylistChecker - Уведомление*

{message}

📋 *Плейлист:* {playlist_name or 'Неизвестно'}
🎵 *Трек:* {track_name or 'Неизвестно'}
🕒 *Время:* {datetime.now().strftime('%d.%m.%Y %H:%M')}
            """
            
            url = f"{self.telegram_config['api_url']}{self.telegram_config['bot_token']}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': telegram_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Telegram уведомление отправлено в чат {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram уведомления: {str(e)}")
            return False
    
    def send_browser_notification(self, user_id, title, message, track_name=None, playlist_name=None):
        """Отправить браузерное push-уведомление"""
        try:
            # Импортируем модели в функции, чтобы избежать циклических импортов
            from app import db, User, PushSubscription
            
            # Получаем все подписки пользователя
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"Пользователь с ID {user_id} не найден")
                return False
            
            subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
            if not subscriptions:
                logger.info(f"У пользователя {user.username} нет активных push-подписок")
                return False
            
            # Проверяем настройки WebPush
            if not all([self.webpush_config['vapid_public_key'], 
                       self.webpush_config['vapid_private_key'],
                       self.webpush_config['vapid_email']]):
                logger.warning("WebPush настройки не настроены, пропускаем отправку push-уведомлений")
                return False
            
            try:
                from pywebpush import webpush
            except ImportError:
                logger.error("Библиотека pywebpush не установлена. Установите: pip install pywebpush")
                return False
            
            # Формируем payload для push-уведомления
            notification_payload = {
                'title': title,
                'body': message,
                'icon': '/static/icon-192x192.png',  # Добавим иконку позже
                'badge': '/static/badge-72x72.png',
                'data': {
                    'playlist_name': playlist_name,
                    'track_name': track_name,
                    'timestamp': datetime.now().isoformat(),
                    'url': '/'  # URL для открытия при клике на уведомление
                },
                'actions': [
                    {
                        'action': 'view',
                        'title': 'Посмотреть',
                        'icon': '/static/view-icon.png'
                    }
                ],
                'requireInteraction': True,
                'tag': f'playlist-{playlist_name}'  # Группировка уведомлений
            }
            
            import json
            payload_json = json.dumps(notification_payload)
            
            success_count = 0
            for subscription in subscriptions:
                try:
                    subscription_info = {
                        'endpoint': subscription.endpoint,
                        'keys': {
                            'p256dh': subscription.p256dh_key,
                            'auth': subscription.auth_key
                        }
                    }
                    
                    webpush(
                        subscription_info=subscription_info,
                        data=payload_json,
                        vapid_private_key=self.webpush_config['vapid_private_key'],
                        vapid_claims={
                            'sub': f"mailto:{self.webpush_config['vapid_email']}"
                        }
                    )
                    
                    success_count += 1
                    logger.info(f"Push-уведомление отправлено на устройство пользователя {user.username}")
                    
                except Exception as push_error:
                    logger.error(f"Ошибка отправки push-уведомления на устройство: {str(push_error)}")
                    
                    # Если подписка недействительна, удаляем её
                    if "410" in str(push_error) or "invalid" in str(push_error).lower():
                        logger.info(f"Удаляем недействительную push-подписку")
                        db.session.delete(subscription)
                        db.session.commit()
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Ошибка отправки браузерного уведомления: {str(e)}")
            return False
    
    def check_notification_already_sent(self, user_id, playlist_id, track_service_id, notification_type):
        """Проверить, было ли уже отправлено уведомление для этого конкретного изменения"""
        from app import NotificationHistory
        
        existing_notification = NotificationHistory.query.filter_by(
            user_id=user_id,
            playlist_id=playlist_id,
            track_service_id=track_service_id,
            notification_type=notification_type
        ).first()
        
        return existing_notification is not None
    
    def save_notification_history(self, user_id, playlist_id, notification_data, sent_via):
        """Сохранить историю отправленного уведомления"""
        from app import NotificationHistory, db
        
        history = NotificationHistory(
            user_id=user_id,
            playlist_id=playlist_id,
            notification_type=notification_data.get('type', 'track_changed'),
            track_service_id=notification_data.get('track_service_id'),
            track_name=notification_data.get('track_name'),
            artist_name=notification_data.get('artist_name'),
            playlist_name=notification_data.get('playlist_name'),
            message=notification_data.get('message', ''),
            sent_via=sent_via
        )
        
        try:
            db.session.add(history)
            db.session.commit()
            logger.info(f"Сохранена история уведомления для пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения истории уведомления: {str(e)}")
            db.session.rollback()
            return False

    def send_all_notifications(self, user, notification_data):
        """Отправить уведомления по всем каналам с проверкой уникальности"""
        # Проверяем, было ли уже отправлено уведомление для этого конкретного изменения
        playlist_id = notification_data.get('playlist_id')
        track_service_id = notification_data.get('track_service_id')
        notification_type = notification_data.get('type')
        
        if self.check_notification_already_sent(user.id, playlist_id, track_service_id, notification_type):
            logger.info(f"Уведомление для пользователя {user.username} о треке {track_service_id} уже было отправлено")
            return {
                'email': False,
                'telegram': False,
                'browser': False,
                'skipped': True,
                'reason': 'already_notified'
            }
        
        # Сохраняем запись в истории ДО отправки, чтобы предотвратить параллельные отправки
        # Используем временный статус "sending" для отслеживания процесса
        try:
            from app import NotificationHistory, db
            from sqlalchemy.exc import IntegrityError
            # Пытаемся создать запись в истории с временным статусом
            history = NotificationHistory(
                user_id=user.id,
                playlist_id=playlist_id,
                notification_type=notification_type,
                track_service_id=track_service_id,
                track_name=notification_data.get('track_name'),
                artist_name=notification_data.get('artist_name'),
                playlist_name=notification_data.get('playlist_name'),
                message=notification_data.get('message', ''),
                sent_via='sending'  # Временный статус
            )
            db.session.add(history)
            db.session.commit()  # Коммитим сразу, чтобы зафиксировать в БД
            logger.info(f"Создана запись в истории уведомлений для пользователя {user.username}, трек {track_service_id}")
        except IntegrityError as e:
            # Если запись уже существует (race condition или уникальный индекс), пропускаем отправку
            db.session.rollback()
            logger.info(f"Уведомление для пользователя {user.username} о треке {track_service_id} уже обрабатывается или отправлено (IntegrityError)")
            return {
                'email': False,
                'telegram': False,
                'browser': False,
                'skipped': True,
                'reason': 'already_processing'
            }
        except Exception as e:
            # Другие ошибки - логируем и пропускаем отправку
            db.session.rollback()
            logger.error(f"Ошибка при создании записи в истории уведомлений: {str(e)}")
            return {
                'email': False,
                'telegram': False,
                'browser': False,
                'skipped': True,
                'reason': 'error_creating_history'
            }
        
        results = {
            'email': False,
            'telegram': False,
            'browser': False,
            'skipped': False
        }
        
        title = f"Изменение в плейлисте {notification_data.get('playlist_name', '')}"
        message = notification_data.get('message', '')
        track_name = notification_data.get('track_name')
        playlist_name = notification_data.get('playlist_name')
        
        sent_channels = []
        
        # Email уведомление
        if user.email and user.email_notifications_enabled:
            if self.send_email_notification(user.email, title, message, track_name, playlist_name):
                results['email'] = True
                sent_channels.append('email')
        
        # Telegram уведомление
        if hasattr(user, 'telegram_chat_id') and user.telegram_chat_id and user.telegram_notifications_enabled:
            if self.send_telegram_notification(user.telegram_chat_id, message, track_name, playlist_name):
                results['telegram'] = True
                sent_channels.append('telegram')
        
        # Браузерное уведомление
        if user.browser_notifications_enabled:
            if self.send_browser_notification(user.id, title, message, track_name, playlist_name):
                results['browser'] = True
                sent_channels.append('browser')
        
        # Обновляем историю с реальными каналами отправки
        try:
            from app import db
            if sent_channels:
                sent_via = ', '.join(sent_channels)
            else:
                sent_via = 'none'  # Если ни одно уведомление не было отправлено
            
            history.sent_via = sent_via
            db.session.commit()
            logger.info(f"Обновлена история уведомления для пользователя {user.username}, отправлено через: {sent_via}")
        except Exception as e:
            logger.error(f"Ошибка обновления истории уведомления: {str(e)}")
            db.session.rollback()
        
        logger.info(f"Уведомления для пользователя {user.username}: {results}")
        return results

    def send_batch_notifications(self, user, tracks_data, playlist_name, playlist_id):
        """Отправить одно сводное уведомление о нескольких удалённых треках.
        
        Вместо отдельного письма/сообщения на каждый трек, группирует все удалённые
        треки из одного плейлиста в одно уведомление.
        """
        if not tracks_data:
            return
        
        count = len(tracks_data)
        
        # Сохраняем историю для каждого трека (для дедупликации)
        from app import NotificationHistory, db
        from sqlalchemy.exc import IntegrityError
        
        new_tracks = []
        for td in tracks_data:
            if self.check_notification_already_sent(user.id, playlist_id, td['track_service_id'], 'track_removed'):
                logger.info(f"Уведомление для трека {td['track_service_id']} уже было отправлено, пропускаем")
                continue
            try:
                history = NotificationHistory(
                    user_id=user.id,
                    playlist_id=playlist_id,
                    notification_type='track_removed',
                    track_service_id=td['track_service_id'],
                    track_name=td['track_name'],
                    artist_name=td['artist_name'],
                    playlist_name=playlist_name,
                    message=td['message'],
                    sent_via='sending'
                )
                db.session.add(history)
                db.session.flush()
                new_tracks.append({'data': td, 'history': history})
            except IntegrityError:
                db.session.rollback()
                logger.info(f"Уведомление для трека {td['track_service_id']} уже обрабатывается")
                continue
        
        if not new_tracks:
            logger.info(f"Все уведомления для плейлиста {playlist_name} уже были отправлены ранее")
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            return
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка сохранения истории batch уведомлений: {str(e)}")
            return
        
        actual_count = len(new_tracks)
        
        # Формируем сводное сообщение
        if actual_count == 1:
            td = new_tracks[0]['data']
            summary_message = f"Трек '{td['track_name']}' от {td['artist_name']} был удалён из плейлиста '{playlist_name}'"
            track_list_text = f"  - {td['track_name']} — {td['artist_name']}"
            track_list_html = f"<li><strong>{td['track_name']}</strong> — {td['artist_name']}</li>"
        else:
            word = self._pluralize_tracks(actual_count)
            summary_message = f"Из плейлиста '{playlist_name}' удалено {actual_count} {word}"
            lines_text = []
            lines_html = []
            display_limit = 20
            for i, nt in enumerate(new_tracks):
                td = nt['data']
                if i < display_limit:
                    lines_text.append(f"  - {td['track_name']} — {td['artist_name']}")
                    lines_html.append(f"<li><strong>{td['track_name']}</strong> — {td['artist_name']}</li>")
            if actual_count > display_limit:
                remaining = actual_count - display_limit
                lines_text.append(f"  ... и ещё {remaining}")
                lines_html.append(f"<li><em>... и ещё {remaining}</em></li>")
            track_list_text = "\n".join(lines_text)
            track_list_html = "\n".join(lines_html)
        
        title = f"Изменения в плейлисте {playlist_name}"
        
        sent_channels = []
        
        # Email
        if user.email and user.email_notifications_enabled:
            if self._send_batch_email(user.email, title, summary_message, track_list_text, track_list_html, playlist_name, actual_count):
                sent_channels.append('email')
        
        # Telegram
        if hasattr(user, 'telegram_chat_id') and user.telegram_chat_id and user.telegram_notifications_enabled:
            if self._send_batch_telegram(user.telegram_chat_id, summary_message, track_list_text, playlist_name, actual_count):
                sent_channels.append('telegram')
        
        # Browser push
        if user.browser_notifications_enabled:
            if self.send_browser_notification(user.id, title, summary_message):
                sent_channels.append('browser')
        
        # Обновляем историю
        try:
            sent_via = ', '.join(sent_channels) if sent_channels else 'none'
            for nt in new_tracks:
                nt['history'].sent_via = sent_via
            db.session.commit()
            logger.info(f"Batch уведомление для {user.username}: {actual_count} треков, каналы: {sent_via}")
        except Exception as e:
            logger.error(f"Ошибка обновления batch истории: {str(e)}")
            db.session.rollback()
    
    @staticmethod
    def _pluralize_tracks(n):
        """Склонение слова 'трек' по числу"""
        if 11 <= n % 100 <= 19:
            return "треков"
        remainder = n % 10
        if remainder == 1:
            return "трек"
        elif 2 <= remainder <= 4:
            return "трека"
        else:
            return "треков"
    
    def _send_batch_email(self, user_email, subject, summary, track_list_text, track_list_html, playlist_name, count):
        """Отправить одно сводное email-уведомление о нескольких удалённых треках"""
        if not all([self.email_config['username'], self.email_config['password']]):
            logger.warning("Email настройки не настроены, пропускаем отправку email")
            return False
        
        try:
            from_address = self.email_config.get('default_sender') or self.email_config.get('username')
            if not from_address or '@' not in from_address:
                logger.error("Некорректный адрес отправителя")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_address
            msg['To'] = user_email
            
            text_content = f"""
PlaylistChecker - Сводное уведомление

{summary}

Удалённые треки:
{track_list_text}

Плейлист: {playlist_name}
Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

---
Это автоматическое уведомление от PlaylistChecker
            """
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
        .track-list {{ background: white; padding: 15px; border-radius: 5px; margin: 15px 0; 
                       border-left: 4px solid #667eea; }}
        .track-list ul {{ margin: 5px 0; padding-left: 20px; }}
        .track-list li {{ margin: 4px 0; }}
        .count-badge {{ display: inline-block; background: #e74c3c; color: white; 
                        padding: 3px 10px; border-radius: 12px; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 PlaylistChecker</h1>
            <p>Сводное уведомление об изменениях</p>
        </div>
        <div class="content">
            <h2>{summary}</h2>
            
            <div class="track-list">
                <strong>📋 Плейлист:</strong> {playlist_name}<br>
                <strong>🎵 Удалено треков:</strong> <span class="count-badge">{count}</span><br>
                <strong>🕒 Время:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}
                <hr>
                <ul>
                    {track_list_html}
                </ul>
            </div>
            
            <p>Зайдите в свой аккаунт PlaylistChecker, чтобы увидеть подробности.</p>
        </div>
        <div class="footer">
            <p>Это автоматическое уведомление от PlaylistChecker</p>
        </div>
    </div>
</body>
</html>
            """
            
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(text_part)
            msg.attach(html_part)
            
            server = smtplib.SMTP(self.email_config['server'], self.email_config['port'])
            if self.email_config['use_tls']:
                server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Сводное email уведомление отправлено на {user_email} ({count} треков)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сводного email уведомления: {str(e)}")
            return False
    
    def _send_batch_telegram(self, chat_id, summary, track_list_text, playlist_name, count):
        """Отправить одно сводное Telegram-уведомление о нескольких удалённых треках"""
        if not self.telegram_config['bot_token']:
            logger.warning("Telegram bot token не настроен, пропускаем отправку в Telegram")
            return False
        
        try:
            telegram_message = f"""
🎵 *PlaylistChecker — Сводное уведомление*

{summary}

📋 *Плейлист:* {playlist_name}
🔢 *Удалено треков:* {count}
🕒 *Время:* {datetime.now().strftime('%d.%m.%Y %H:%M')}

*Удалённые треки:*
{track_list_text}
            """
            
            # Telegram ограничивает сообщения 4096 символами
            if len(telegram_message) > 4000:
                word = self._pluralize_tracks(count)
                telegram_message = f"""
🎵 *PlaylistChecker — Сводное уведомление*

Из плейлиста *{playlist_name}* удалено *{count}* {word}.

🕒 *Время:* {datetime.now().strftime('%d.%m.%Y %H:%M')}

Полный список доступен в вашем аккаунте PlaylistChecker.
                """
            
            url = f"{self.telegram_config['api_url']}{self.telegram_config['bot_token']}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': telegram_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Сводное Telegram уведомление отправлено в чат {chat_id} ({count} треков)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сводного Telegram уведомления: {str(e)}")
            return False


# Глобальный экземпляр сервиса уведомлений
notification_service = NotificationService()
