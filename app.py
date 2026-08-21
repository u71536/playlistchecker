from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_babel import Babel, gettext, lazy_gettext
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import jwt
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

# Конфигурация для переводов
app.config['LANGUAGES'] = {
    'ru': 'Русский',
    'en': 'English'
}

# Конфигурация Babel
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['BABEL_DEFAULT_LOCALE'] = 'ru'

# Настройки для разработки
if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    # Перезагружаем переводы в режиме разработки
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# Принудительно отключаем кэширование для разработки
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Инициализация расширений
db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Инициализация Babel
def get_locale():
    # 1. Если язык выбран пользователем, используем его
    if 'language' in session:
        return session['language']
    
    # 2. Если пользователь авторизован и у него есть предпочтения языка
    if current_user.is_authenticated and hasattr(current_user, 'language'):
        return current_user.language
    
    # 3. Используем язык браузера, если он поддерживается
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'ru'

babel = Babel(app, locale_selector=get_locale)

# Добавляем функции перевода в контекст шаблонов
@app.context_processor
def inject_conf_vars():
    return {
        'LANGUAGES': app.config['LANGUAGES'],
        'CURRENT_LANGUAGE': session.get('language', get_locale()),
        '_': gettext,
        '_l': lazy_gettext
    }


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
    
    # Настройки языка
    language = db.Column(db.String(5), default='ru')
    
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

class NotificationHistory(db.Model):
    """Модель для хранения истории отправленных уведомлений"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    notification_type = db.Column(db.String(20), nullable=False)  # 'track_added', 'track_removed'
    track_service_id = db.Column(db.String(255))  # ID трека в сервисе для уникальности
    track_name = db.Column(db.String(255))
    artist_name = db.Column(db.String(255))
    playlist_name = db.Column(db.String(255))
    message = db.Column(db.Text, nullable=False)
    sent_via = db.Column(db.String(50))  # 'email', 'telegram', 'browser', 'all'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    user = db.relationship('User', backref='notification_history', lazy=True)
    playlist = db.relationship('Playlist', backref='notification_history', lazy=True)
    
    # Индекс для быстрого поиска уникальных уведомлений
    __table_args__ = (
        db.Index('idx_unique_notification', 'user_id', 'playlist_id', 'track_service_id', 'notification_type'),
    )

# Формы
class LoginForm(FlaskForm):
    username = StringField(lazy_gettext('login.username'), validators=[DataRequired()])
    password = PasswordField(lazy_gettext('login.password'), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext('base.login'))

class RegisterForm(FlaskForm):
    username = StringField(lazy_gettext('login.username'), validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField(lazy_gettext('login.password'), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext('form.register'))

class PlaylistForm(FlaskForm):
    service = SelectField(lazy_gettext('form.service'), choices=[
        ('spotify', 'Spotify'),
        ('deezer', 'Deezer'),
        ('apple_music', 'Apple Music'),
        ('yandex_music', 'Yandex Music')
    ], validators=[DataRequired()])
    playlist_url = StringField(lazy_gettext('form.playlist_url'), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext('add_playlist.add_playlist'))

class NotificationSettingsForm(FlaskForm):
    """Форма настроек уведомлений"""
    email_notifications_enabled = BooleanField(lazy_gettext('notification_settings.email_notifications'))
    telegram_notifications_enabled = BooleanField(lazy_gettext('notification_settings.telegram_notifications'))
    browser_notifications_enabled = BooleanField(lazy_gettext('notification_settings.browser_notifications'))
    submit = SubmitField(lazy_gettext('form.save_settings'))

# Формы восстановления пароля
class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField(lazy_gettext('form.send'))

class ResetPasswordForm(FlaskForm):
    password = PasswordField(lazy_gettext('login.password'), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext('form.save'))

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
    """Перенаправление на страницу о сервисе"""
    return redirect(url_for('about'))


@app.route('/sitemap.xml')
def sitemap():
    """Sitemap для поисковых систем с поддержкой двух языков"""
    from flask import Response
    from datetime import datetime
    
    base_url = request.url_root.rstrip('/')
    lastmod = datetime.now().strftime('%Y-%m-%d')
    
    # Основные страницы с поддержкой языков
    pages = [
        {'path': '', 'changefreq': 'daily', 'priority': '1.0'},
        {'path': 'about', 'changefreq': 'weekly', 'priority': '0.8'},
        {'path': 'login', 'changefreq': 'monthly', 'priority': '0.6'},
        {'path': 'register', 'changefreq': 'monthly', 'priority': '0.6'},
    ]
    
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    sitemap_content += 'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    
    for page in pages:
        url_path = page['path']
        page_url = f'{base_url}/{url_path}' if url_path else base_url
        sitemap_content += '    <url>\n'
        sitemap_content += f'        <loc>{page_url}</loc>\n'
        sitemap_content += f'        <lastmod>{lastmod}</lastmod>\n'
        sitemap_content += f'        <changefreq>{page["changefreq"]}</changefreq>\n'
        sitemap_content += f'        <priority>{page["priority"]}</priority>\n'
        # Добавляем альтернативные языковые версии
        sitemap_content += f'        <xhtml:link rel="alternate" hreflang="ru" href="{page_url}?lang=ru" />\n'
        sitemap_content += f'        <xhtml:link rel="alternate" hreflang="en" href="{page_url}?lang=en" />\n'
        sitemap_content += f'        <xhtml:link rel="alternate" hreflang="x-default" href="{page_url}" />\n'
        sitemap_content += '    </url>\n'
    
    sitemap_content += '</urlset>'
    
    return Response(sitemap_content, mimetype='application/xml')


@app.route('/robots.txt')
def robots_txt():
    """Robots.txt для поисковых систем"""
    from flask import Response
    
    base_url = request.url_root.rstrip('/')
    
    robots_content = f'''User-agent: *
Allow: /

# Sitemap
Sitemap: {base_url}/sitemap.xml

# Disallow private areas
Disallow: /instance/
Disallow: /migrations/
Disallow: /__pycache__/
Disallow: /services/__pycache__/
Disallow: /api/

# Allow important pages
Allow: /
Allow: /about
Allow: /login
Allow: /register
Allow: /sitemap.xml
Allow: /robots.txt'''
    
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
        flash(gettext('login.invalid_username_or_password'))
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash(gettext('flash.user_exists_username'))
            return render_template('register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash(gettext('flash.user_exists_email'))
            return render_template('register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        
        flash(gettext('flash.registration_success'))
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Восстановление пароля
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip()).first()

        # Независимо от наличия пользователя показываем одинаковое сообщение
        try:
            if user:
                payload = {
                    'sub': user.id,
                    'exp': datetime.utcnow() + timedelta(hours=1),
                    'type': 'password_reset'
                }
                token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
                reset_url = url_for('reset_password', token=token, _external=True)

                # Отправляем письмо
                try:
                    from services.notification_service import notification_service
                    subject = 'Восстановление пароля'
                    message = f"Чтобы сбросить пароль, перейдите по ссылке: {reset_url}\n\nСсылка действительна 1 час."
                    sent = notification_service.send_email_notification(user.email, subject, message)
                    if not sent:
                        logger.info(f"[PasswordReset] Ссылка: {reset_url} (email не отправлен, проверьте SMTP настройки)")
                except Exception as e:
                    logger.error(f"[PasswordReset] Ошибка отправки письма: {str(e)}")
                    logger.info(f"[PasswordReset] Ссылка: {reset_url}")
        finally:
            flash(gettext('Если такой email существует, мы отправили письмо с инструкциями'))
            return redirect(url_for('login'))

    return render_template('forgot_password.html', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # Валидируем токен
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        if data.get('type') != 'password_reset':
            raise jwt.InvalidTokenError('invalid type')
        user_id = data.get('sub')
        user = User.query.get(user_id)
        if not user:
            raise jwt.InvalidTokenError('user not found')
    except Exception:
        flash(gettext('Ссылка для восстановления недействительна или устарела'))
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        flash(gettext('Пароль успешно обновлён. Войдите с новым паролем.'))
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)

@app.route('/clear_session')
def clear_session():
    """Очистить сессию от старых Firestore данных"""
    from flask import session
    session.clear()
    return redirect(url_for('index'))

@app.route('/set_language/<language>')
def set_language(language=None):
    """Установить язык интерфейса"""
    if language not in app.config['LANGUAGES']:
        return redirect(request.referrer or url_for('index'))
    
    session['language'] = language
    
    # Если пользователь авторизован, сохраняем его предпочтения
    if current_user.is_authenticated:
        current_user.language = language
        db.session.commit()
    
    return redirect(request.referrer or url_for('index'))

def _redirect_spotify_reauthorization():
    """Discard stored Spotify tokens and send the user through sign-in again."""
    SpotifyToken.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    db.session.expire(current_user, ['spotify_tokens'])
    flash(gettext('flash.spotify_reauthorization_required'))
    return redirect(url_for('spotify_auth'))


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
        from services.spotify_service import SpotifyReauthorizationRequired
        try:
            playlist = monitor.add_playlist(
                user=current_user,
                service=form.service.data,
                playlist_url=form.playlist_url.data
            )
            
            flash(gettext('flash.playlist_added_success', playlist_name=playlist.name))
            return redirect(url_for('playlists'))
        except SpotifyReauthorizationRequired:
            return _redirect_spotify_reauthorization()
        except ValueError as e:
            flash(gettext('flash.error_generic', error=str(e)), 'error')
        except Exception as e:
            flash(gettext('flash.error_adding_playlist', error=str(e)), 'error')
    return render_template('add_playlist.html', form=form)

@app.route('/spotify_playlists')
@login_required
def spotify_playlists():
    """Получить все плейлисты пользователя из Spotify"""
    from services.spotify_service import (
        SpotifyService, TokenExpiredError, SpotifyReauthorizationRequired
    )
    
    # Проверяем, есть ли токен Spotify
    spotify_token = current_user.spotify_tokens[0] if current_user.spotify_tokens else None
    if not spotify_token:
        flash(gettext('flash.connect_spotify_first'))
        return redirect(url_for('index'))
    
    try:
        service = SpotifyService()
        
        # Проверяем и обновляем токен при необходимости
        new_token_info = service.check_and_refresh_token(
            spotify_token.access_token, 
            spotify_token.refresh_token, 
            spotify_token.expires_at
        )
        
        if new_token_info:
            # Обновляем токен в базе данных
            spotify_token.access_token = new_token_info['access_token']
            if 'refresh_token' in new_token_info:
                spotify_token.refresh_token = new_token_info['refresh_token']
            spotify_token.expires_at = datetime.utcnow() + timedelta(seconds=new_token_info['expires_in'])
            db.session.commit()
            flash(gettext('flash.spotify_token_updated'), 'info')
        
        playlists = service.get_user_playlists(spotify_token.access_token, spotify_token.refresh_token)
        return render_template('spotify_playlists.html', playlists=playlists)
        
    except SpotifyReauthorizationRequired:
        return _redirect_spotify_reauthorization()
    except TokenExpiredError as e:
        if e.new_token_info:
            # Обновляем токен в базе данных
            spotify_token.access_token = e.new_token_info['access_token']
            if 'refresh_token' in e.new_token_info:
                spotify_token.refresh_token = e.new_token_info['refresh_token']
            spotify_token.expires_at = datetime.utcnow() + timedelta(seconds=e.new_token_info['expires_in'])
            db.session.commit()
            
            # Повторяем запрос с новым токеном
            try:
                playlists = service.get_user_playlists(spotify_token.access_token, spotify_token.refresh_token)
                flash(gettext('flash.spotify_token_updated'), 'info')
                return render_template('spotify_playlists.html', playlists=playlists)
            except SpotifyReauthorizationRequired:
                return _redirect_spotify_reauthorization()
            except Exception as retry_e:
                flash(gettext('flash.error_getting_playlists_after_token_update', error=str(retry_e)))
                return redirect(url_for('index'))
        
        flash(gettext('flash.error_getting_playlists', error=str(e)))
        return redirect(url_for('index'))
    except Exception as e:
        flash(gettext('flash.error_getting_playlists', error=str(e)))
        return redirect(url_for('index'))

@app.route('/add_spotify_playlist/<playlist_id>')
@login_required
def add_spotify_playlist(playlist_id):
    """Добавить плейлист Spotify по ID"""
    from services.spotify_service import SpotifyReauthorizationRequired
    
    spotify_token = current_user.spotify_tokens[0] if current_user.spotify_tokens else None
    if not spotify_token:
        flash(gettext('flash.connect_spotify_first'))
        return redirect(url_for('index'))
    
    try:
        playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
        
        playlist = monitor.add_playlist(
            user=current_user,
            service='spotify',
            playlist_url=playlist_url
        )
        flash(gettext('flash.playlist_added_success', playlist_name=playlist.name))
        return redirect(url_for('playlists'))
    except SpotifyReauthorizationRequired:
        return _redirect_spotify_reauthorization()
    except ValueError as e:
        flash(gettext('flash.error_generic', error=str(e)))
    except Exception as e:
        flash(gettext('flash.error_generic_short', error=str(e)))
    
    return redirect(url_for('spotify_playlists'))

@app.route('/check_playlists_now')
@login_required
def check_playlists_now():
    """Принудительная проверка плейлистов"""
    from services.spotify_service import SpotifyReauthorizationRequired
    try:
        monitor.check_user_playlists(current_user)
        flash(gettext('flash.playlists_checked'))
    except SpotifyReauthorizationRequired:
        return _redirect_spotify_reauthorization()
    except Exception as e:
        flash(gettext('flash.error_checking_playlists', error=str(e)))
    return redirect(url_for('playlists'))

@app.route('/playlist/<int:playlist_id>/tracks')
@login_required
def playlist_tracks(playlist_id):
    """Показать треки плейлиста"""
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user.id).first()
    if not playlist:
        flash(gettext('flash.playlist_not_found'))
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
        flash(gettext('flash.spotify_auth_error_no_code'))
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
        
        flash(gettext('flash.spotify_connected_success'))
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(gettext('flash.spotify_auth_error', error=str(e)))
        return redirect(url_for('index'))

@app.route('/auth/deezer')
@login_required
def deezer_auth():
    # Здесь будет логика авторизации Deezer
    flash(gettext('flash.deezer_auth_coming_soon'))
    return redirect(url_for('index'))

@app.route('/api/apple_music/developer_token')
@login_required
def get_apple_music_developer_token():
    """Получить Developer Token для Apple Music"""
    from services.apple_music_service import AppleMusicService
    try:
        service = AppleMusicService()
        token = service.get_developer_token()
        return jsonify({'token': token})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/apple_music/user_token', methods=['POST'])
@login_required
def save_apple_music_user_token():
    """Сохранить User Token для Apple Music"""
    from services.apple_music_service import AppleMusicService
    
    data = request.json
    user_token = data.get('user_token')
    expires_at_str = data.get('expires_at')
    
    if not user_token:
        return jsonify({'error': 'User token required'}), 400
    
    try:
        # Проверяем валидность токена
        service = AppleMusicService()
        if not service.is_token_valid(user_token):
            return jsonify({'error': 'Invalid user token'}), 400
        
        # Парсим дату истечения (обычно токен действителен ~6 месяцев)
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        else:
            # По умолчанию 6 месяцев
            expires_at = datetime.utcnow() + timedelta(days=180)
        
        # Удаляем старые токены
        AppleMusicToken.query.filter_by(user_id=current_user.id).delete()
        
        # Сохраняем новый токен
        apple_music_token = AppleMusicToken(
            user_id=current_user.id,
            access_token=user_token,
            expires_at=expires_at
        )
        db.session.add(apple_music_token)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/auth/apple_music')
@login_required
def apple_music_auth():
    """Авторизация Apple Music через MusicKit JS"""
    # Авторизация происходит на клиентской стороне через MusicKit JS
    # Просто рендерим страницу с JavaScript для авторизации
    return render_template('apple_music_auth.html')

@app.route('/auth/yandex_music')
@login_required
def yandex_music_auth():
    # Здесь будет логика авторизации Yandex Music
    flash(gettext('flash.yandex_music_auth_coming_soon'))
    return redirect(url_for('index'))

# Настройки уведомлений
@app.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Пометить уведомление как прочитанное"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first()
    if not notification:
        return jsonify({'status': 'error'}), 404
    notification.is_read = True
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Пометить все уведомления пользователя как прочитанные"""
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return jsonify({'status': 'ok'})


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
        flash(gettext('flash.notification_settings_saved'))
        return redirect(url_for('notification_settings'))
    
    # Заполняем форму текущими настройками
    form.email_notifications_enabled.data = current_user.email_notifications_enabled
    form.telegram_notifications_enabled.data = current_user.telegram_notifications_enabled
    form.browser_notifications_enabled.data = current_user.browser_notifications_enabled
    
    return render_template('notification_settings.html', form=form)

@app.route('/notification_history')
@login_required
def notification_history():
    """История уведомлений пользователя"""
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Количество уведомлений на страницу
    
    # Получаем историю уведомлений пользователя с пагинацией
    history_pagination = NotificationHistory.query.filter_by(user_id=current_user.id)\
        .order_by(NotificationHistory.sent_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('notification_history.html', 
                         history_pagination=history_pagination)

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
    trigger="cron",
    hour=9,  # Проверяем каждый день в 9:00 утра
    minute=0,
    id='playlist_checker'
)
scheduler.start()

# Остановка планировщика при выходе
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
