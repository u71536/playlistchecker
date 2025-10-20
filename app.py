from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import logging
from playlist_monitor import PlaylistMonitor

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'dev-secret-key-change-in-production'
)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///playlistchecker.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация расширений
db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Настройки уведомлений
    email_notifications_enabled = db.Column(db.Boolean, default=True)
    telegram_notifications_enabled = db.Column(db.Boolean, default=False)
    browser_notifications_enabled = db.Column(db.Boolean, default=True)
    
    # Telegram интеграция
    telegram_chat_id = db.Column(db.String(50))
    telegram_username = db.Column(db.String(100))
    
    # Связи с музыкальными сервисами
    spotify_tokens = db.relationship('SpotifyToken', backref='user', lazy=True)
    deezer_tokens = db.relationship('DeezerToken', backref='user', lazy=True)
    apple_music_tokens = db.relationship('AppleMusicToken', backref='user', lazy=True)
    yandex_music_tokens = db.relationship('YandexMusicToken', backref='user', lazy=True)
    
    # Плейлисты пользователя
    playlists = db.relationship('Playlist', backref='user', lazy=True)
    
    # Push-подписки для браузерных уведомлений
    push_subscriptions = db.relationship('PushSubscription', backref='user', lazy=True, cascade='all, delete-orphan')

class SpotifyToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DeezerToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AppleMusicToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class YandexMusicToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service = db.Column(db.String(20), nullable=False)  # spotify, deezer, apple_music, yandex_music
    service_playlist_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime)
    
    # Связь с треками
    tracks = db.relationship('Track', backref='playlist', lazy=True, cascade='all, delete-orphan')

class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    service_track_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    album = db.Column(db.String(200))
    duration = db.Column(db.Integer)  # в секундах
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_removed = db.Column(db.Boolean, default=False)
    removed_at = db.Column(db.DateTime)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('track.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    playlist = db.relationship('Playlist', backref='notifications', lazy=True)
    track = db.relationship('Track', backref='notifications', lazy=True)

class PushSubscription(db.Model):
    """Модель для хранения push-подписок браузерных уведомлений"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh_key = db.Column(db.Text, nullable=False)
    auth_key = db.Column(db.Text, nullable=False)
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)

# Формы
class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

class PlaylistForm(FlaskForm):
    service = SelectField('Сервис', choices=[
        ('spotify', 'Spotify'),
        # ('deezer', 'Deezer'),  # Временно скрыт
        ('apple_music', 'Apple Music'),
        ('yandex_music', 'Yandex Music')
    ], validators=[DataRequired()])
    playlist_url = StringField('URL плейлиста', validators=[DataRequired()])
    submit = SubmitField('Добавить плейлист')

class NotificationSettingsForm(FlaskForm):
    """Форма настроек уведомлений"""
    email_notifications_enabled = BooleanField('Email уведомления')
    telegram_notifications_enabled = BooleanField('Telegram уведомления')
    browser_notifications_enabled = BooleanField('Браузерные уведомления')
    submit = SubmitField('Сохранить настройки')

@login_manager.user_loader
def load_user(user_id):
    try:
        # Пытаемся преобразовать в int (для SQLAlchemy)
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        # Если не удается преобразовать в int, возвращаем None
        # Это произойдет для старых Firestore ID в сессии
        return None

# Главная страница
@app.route('/')
def index():
    if current_user.is_authenticated:
        playlists = Playlist.query.filter_by(user_id=current_user.id).all()
        notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(10).all()
        return render_template('dashboard.html', playlists=playlists, notifications=notifications)
    return render_template('index.html')

# SEO страницы
@app.route('/about')
def about():
    """Страница о сервисе"""
    return render_template('about.html')


@app.route('/why-check')
def why_check():
    """Страница зачем проверять плейлисты"""
    return render_template('why_check.html')


@app.route('/sitemap.xml')
def sitemap():
    """Sitemap для поисковых систем"""
    from flask import Response
    from datetime import datetime
    
    sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{request.url_root}</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>{request.url_root}about</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>{request.url_root}why-check</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>{request.url_root}login</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>{request.url_root}register</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.6</priority>
    </url>
</urlset>'''
    
    return Response(sitemap_content, mimetype='application/xml')


@app.route('/robots.txt')
def robots_txt():
    """Robots.txt для поисковых систем"""
    from flask import Response
    
    robots_content = '''User-agent: *
Allow: /

# Sitemap
Sitemap: https://yourdomain.com/sitemap.xml

# Disallow private areas
Disallow: /instance/
Disallow: /migrations/
Disallow: /__pycache__/
Disallow: /services/__pycache__/

# Allow important pages
Allow: /
Allow: /about
Allow: /why-check
Allow: /login
Allow: /register'''
    
    return Response(robots_content, mimetype='text/plain')

# Авторизация
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверное имя пользователя или пароль')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Пользователь с таким именем уже существует')
            return render_template('register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Пользователь с таким email уже существует')
            return render_template('register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь вы можете войти в систему.')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/clear_session')
def clear_session():
    """Очистить сессию от старых Firestore данных"""
    from flask import session
    session.clear()
    return redirect(url_for('index'))

# Управление плейлистами
@app.route('/playlists')
@login_required
def playlists():
    playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return render_template('playlists.html', playlists=playlists)

@app.route('/add_playlist', methods=['GET', 'POST'])
@login_required
def add_playlist():
    form = PlaylistForm()
    if form.validate_on_submit():
        try:
            playlist = monitor.add_playlist(
                user=current_user,
                service=form.service.data,
                playlist_url=form.playlist_url.data
            )
            
            flash(f'Плейлист "{playlist.name}" успешно добавлен для мониторинга!')
            return redirect(url_for('playlists'))
        except ValueError as e:
            flash(f'Ошибка: {str(e)}', 'error')
        except Exception as e:
            flash(f'Произошла ошибка при добавлении плейлиста: {str(e)}', 'error')
    return render_template('add_playlist.html', form=form)

@app.route('/spotify_playlists')
@login_required
def spotify_playlists():
    """Получить все плейлисты пользователя из Spotify"""
    from services.spotify_service import SpotifyService
    
    # Проверяем, есть ли токен Spotify
    spotify_token = current_user.spotify_tokens[0] if current_user.spotify_tokens else None
    if not spotify_token:
        flash('Сначала подключите Spotify')
        return redirect(url_for('index'))
    
    try:
        service = SpotifyService()
        playlists = service.get_user_playlists(spotify_token.access_token, spotify_token.refresh_token)
        return render_template('spotify_playlists.html', playlists=playlists)
    except Exception as e:
        # Импортируем TokenExpiredError локально
        from services.spotify_service import TokenExpiredError
        
        if isinstance(e, TokenExpiredError) and e.new_token_info:
            # Обновляем токен в базе данных
            spotify_token.access_token = e.new_token_info['access_token']
            if 'refresh_token' in e.new_token_info:
                spotify_token.refresh_token = e.new_token_info['refresh_token']
            spotify_token.expires_at = datetime.utcnow() + timedelta(seconds=e.new_token_info['expires_in'])
            db.session.commit()
            
            # Повторяем запрос с новым токеном
            try:
                playlists = service.get_user_playlists(spotify_token.access_token)
                flash('Токен Spotify обновлен автоматически', 'info')
                return render_template('spotify_playlists.html', playlists=playlists)
            except Exception as retry_e:
                flash(f'Ошибка получения плейлистов после обновления токена: {str(retry_e)}')
                return redirect(url_for('index'))
        
        flash(f'Ошибка получения плейлистов: {str(e)}')
        return redirect(url_for('index'))

@app.route('/add_spotify_playlist/<playlist_id>')
@login_required
def add_spotify_playlist(playlist_id):
    """Добавить плейлист Spotify по ID"""
    from services.spotify_service import SpotifyService
    
    spotify_token = current_user.spotify_tokens[0] if current_user.spotify_tokens else None
    if not spotify_token:
        flash('Сначала подключите Spotify')
        return redirect(url_for('index'))
    
    try:
        playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
        
        playlist = monitor.add_playlist(
            user=current_user,
            service='spotify',
            playlist_url=playlist_url
        )
        flash(f'Плейлист "{playlist.name}" успешно добавлен для мониторинга!')
        return redirect(url_for('playlists'))
    except ValueError as e:
        flash(f'Ошибка: {str(e)}')
    except Exception as e:
        flash(f'Произошла ошибка: {str(e)}')
    
    return redirect(url_for('spotify_playlists'))

@app.route('/check_playlists_now')
@login_required
def check_playlists_now():
    """Принудительная проверка плейлистов"""
    try:
        monitor.check_user_playlists(current_user)
        flash('Плейлисты проверены! Проверьте уведомления.')
    except Exception as e:
        flash(f'Ошибка при проверке плейлистов: {str(e)}')
    return redirect(url_for('playlists'))

@app.route('/playlist/<int:playlist_id>/tracks')
@login_required
def playlist_tracks(playlist_id):
    """Показать треки плейлиста"""
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user.id).first()
    if not playlist:
        flash('Плейлист не найден')
        return redirect(url_for('playlists'))
    
    tracks = Track.query.filter_by(playlist_id=playlist_id).order_by(Track.added_at.desc()).all()
    return render_template('playlist_tracks.html', playlist=playlist, tracks=tracks)

# API для авторизации в сервисах
@app.route('/auth/spotify')
@login_required
def spotify_auth():
    """Начать авторизацию Spotify"""
    from services.spotify_service import SpotifyService
    
    service = SpotifyService()
    auth_url = service.get_auth_url()
    return redirect(auth_url)

@app.route('/auth/spotify/callback')
@login_required
def spotify_callback():
    """Обработка callback от Spotify"""
    from services.spotify_service import SpotifyService
    
    code = request.args.get('code')
    if not code:
        flash('Ошибка авторизации Spotify: код не получен')
        return redirect(url_for('index'))
    
    try:
        service = SpotifyService()
        token_info = service.get_access_token(code)
        
        # Сохраняем токен в базе данных
        expires_at = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
        
        # Удаляем старые токены
        SpotifyToken.query.filter_by(user_id=current_user.id).delete()
        
        # Сохраняем новый токен
        spotify_token = SpotifyToken(
            user_id=current_user.id,
            access_token=token_info['access_token'],
            refresh_token=token_info['refresh_token'],
            expires_at=expires_at
        )
        db.session.add(spotify_token)
        db.session.commit()
        
        flash('Spotify успешно подключен!')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Ошибка авторизации Spotify: {str(e)}')
        return redirect(url_for('index'))

@app.route('/auth/deezer')
@login_required
def deezer_auth():
    # Здесь будет логика авторизации Deezer
    flash('Авторизация Deezer будет реализована')
    return redirect(url_for('index'))

@app.route('/auth/apple_music')
@login_required
def apple_music_auth():
    # Здесь будет логика авторизации Apple Music
    flash('Авторизация Apple Music будет реализована в скором времени')
    return redirect(url_for('index'))

@app.route('/auth/yandex_music')
@login_required
def yandex_music_auth():
    # Здесь будет логика авторизации Yandex Music
    flash('Авторизация Yandex Music будет реализована в скором времени')
    return redirect(url_for('index'))

# Настройки уведомлений
@app.route('/settings/notifications', methods=['GET', 'POST'])
@login_required
def notification_settings():
    """Настройки уведомлений пользователя"""
    form = NotificationSettingsForm()
    
    if form.validate_on_submit():
        current_user.email_notifications_enabled = form.email_notifications_enabled.data
        current_user.telegram_notifications_enabled = form.telegram_notifications_enabled.data
        current_user.browser_notifications_enabled = form.browser_notifications_enabled.data
        
        db.session.commit()
        flash('Настройки уведомлений сохранены!')
        return redirect(url_for('notification_settings'))
    
    # Заполняем форму текущими настройками
    form.email_notifications_enabled.data = current_user.email_notifications_enabled
    form.telegram_notifications_enabled.data = current_user.telegram_notifications_enabled
    form.browser_notifications_enabled.data = current_user.browser_notifications_enabled
    
    return render_template('notification_settings.html', form=form)

# Telegram интеграция
@app.route('/telegram/connect')
@login_required
def telegram_connect():
    """Подключение Telegram бота"""
    bot_username = os.environ.get('TELEGRAM_BOT_USERNAME', 'checkingplaylistbot')
    telegram_url = f"https://t.me/{bot_username}?start={current_user.id}"
    return redirect(telegram_url)

@app.route('/api/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook для обработки сообщений от Telegram бота"""
    try:
        data = request.get_json()
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            # Обрабатываем команду /start с параметром user_id
            if text.startswith('/start'):
                parts = text.split()
                if len(parts) > 1:
                    try:
                        user_id = int(parts[1])
                        user = User.query.get(user_id)
                        
                        if user:
                            user.telegram_chat_id = str(chat_id)
                            if 'username' in message['chat']:
                                user.telegram_username = message['chat']['username']
                            
                            db.session.commit()
                            
                            # Отправляем подтверждение
                            from services.notification_service import notification_service
                            notification_service.send_telegram_notification(
                                chat_id,
                                f"✅ Telegram успешно подключен к аккаунту {user.username}!\n\nТеперь вы будете получать уведомления об изменениях в ваших плейлистах."
                            )
                            
                            return {'status': 'ok'}
                    except ValueError:
                        pass
            
            # Отправляем справку для неизвестных команд
            from services.notification_service import notification_service
            notification_service.send_telegram_notification(
                chat_id,
                "🤖 Привет! Я бот PlaylistChecker.\n\nДля подключения перейдите в настройки уведомлений на сайте и нажмите 'Подключить Telegram'."
            )
        
        return {'status': 'ok'}
        
    except Exception as e:
        logger.error(f"Ошибка обработки Telegram webhook: {str(e)}")
        return {'status': 'error'}, 500

# API для браузерных push-уведомлений
@app.route('/api/push/subscribe', methods=['POST'])
@login_required
def push_subscribe():
    """Подписка на push-уведомления"""
    try:
        data = request.get_json()
        
        # Проверяем, есть ли уже такая подписка
        existing = PushSubscription.query.filter_by(
            user_id=current_user.id,
            endpoint=data['endpoint']
        ).first()
        
        if existing:
            # Обновляем существующую подписку
            existing.p256dh_key = data['keys']['p256dh']
            existing.auth_key = data['keys']['auth']
            existing.user_agent = request.headers.get('User-Agent', '')
            existing.last_used = datetime.utcnow()
        else:
            # Создаем новую подписку
            subscription = PushSubscription(
                user_id=current_user.id,
                endpoint=data['endpoint'],
                p256dh_key=data['keys']['p256dh'],
                auth_key=data['keys']['auth'],
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.add(subscription)
        
        db.session.commit()
        return {'status': 'success'}
        
    except Exception as e:
        logger.error(f"Ошибка подписки на push-уведомления: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/api/push/unsubscribe', methods=['POST'])
@login_required
def push_unsubscribe():
    """Отписка от push-уведомлений"""
    try:
        data = request.get_json()
        
        subscription = PushSubscription.query.filter_by(
            user_id=current_user.id,
            endpoint=data['endpoint']
        ).first()
        
        if subscription:
            db.session.delete(subscription)
            db.session.commit()
        
        return {'status': 'success'}
        
    except Exception as e:
        logger.error(f"Ошибка отписки от push-уведомлений: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/api/push/vapid-public-key')
def get_vapid_public_key():
    """Получить публичный VAPID ключ для push-уведомлений"""
    public_key = os.environ.get('VAPID_PUBLIC_KEY')
    if not public_key:
        return {'error': 'VAPID ключ не настроен'}, 500
    
    return {'publicKey': public_key}

# Создаем глобальный экземпляр монитора
monitor = PlaylistMonitor(app)

# Планировщик задач
def check_playlists():
    """Функция для проверки всех плейлистов на изменения"""
    from datetime import datetime
    print(f"[{datetime.now()}] Запуск проверки плейлистов...")
    try:
        # Используем глобальную переменную app с контекстом
        with app.app_context():
            monitor.check_all_playlists()
        print(f"[{datetime.now()}] Проверка плейлистов завершена успешно")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при проверке плейлистов: {str(e)}")
        import traceback
        traceback.print_exc()

# Настройка планировщика
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=check_playlists,
    trigger="interval",
    minutes=10,  # Проверяем каждые 10 минут
    
    id='playlist_checker'
)
scheduler.start()

# Остановка планировщика при выходе
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
