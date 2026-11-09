import os

from dotenv import load_dotenv
from flask import Flask, request, session
from flask_babel import Babel, gettext, lazy_gettext
from flask_login import current_user

from extensions import db, limiter, login_manager, migrate
from forms import CsrfForm
from models import (
    AppleMusicToken,
    DeezerToken,
    Notification,
    NotificationHistory,
    Playlist,
    PushSubscription,
    SpotifyToken,
    Track,
    User,
    YandexMusicToken,
)
from playlist_monitor import PlaylistMonitor

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'dev-secret-key-change-in-production'
)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///playlistchecker.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['LANGUAGES'] = {
    'ru': 'Русский',
    'en': 'English',
    'uk': 'Українська',
    'es': 'Español',
    'pt': 'Português',
    'de': 'Deutsch',
    'fr': 'Français',
    'it': 'Italiano',
    'pl': 'Polski',
    'tr': 'Türkçe',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
    'ar': 'العربية',
}
app.config['HREFLANG'] = {
    'ru': 'ru',
    'en': 'en',
    'uk': 'uk',
    'es': 'es',
    'pt': 'pt',
    'de': 'de',
    'fr': 'fr',
    'it': 'it',
    'pl': 'pl',
    'tr': 'tr',
    'zh': 'zh-Hans',
    'ja': 'ja',
    'ko': 'ko',
    'ar': 'ar',
}
app.config['OG_LOCALES'] = {
    'ru': 'ru_RU',
    'en': 'en_US',
    'uk': 'uk_UA',
    'es': 'es_ES',
    'pt': 'pt_BR',
    'de': 'de_DE',
    'fr': 'fr_FR',
    'it': 'it_IT',
    'pl': 'pl_PL',
    'tr': 'tr_TR',
    'zh': 'zh_CN',
    'ja': 'ja_JP',
    'ko': 'ko_KR',
    'ar': 'ar_AR',
}
app.config['HTML_LANG'] = {'zh': 'zh-Hans'}
app.config['RTL_LANGUAGES'] = ('ar',)
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['BABEL_DEFAULT_LOCALE'] = 'ru'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['RATELIMIT_ENABLED'] = os.environ.get('RATELIMIT_ENABLED', '1') != '0'

db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
limiter.init_app(app)


def get_locale():
    languages = app.config['LANGUAGES']
    requested = request.args.get('lang')
    if requested in languages:
        session['language'] = requested
        return requested
    selected = session.get('language')
    if selected in languages:
        return selected
    if current_user.is_authenticated and getattr(current_user, 'language', None) in languages:
        return current_user.language
    # Адрес без параметра языка всегда русский, чтобы / и /?lang=en не меняли
    # текст в зависимости от Accept-Language поискового робота.
    return 'ru'


babel = Babel(app, locale_selector=get_locale)


@app.context_processor
def inject_conf_vars():
    return {
        'LANGUAGES': app.config['LANGUAGES'],
        'HREFLANG': app.config['HREFLANG'],
        'OG_LOCALES': app.config['OG_LOCALES'],
        'HTML_LANG': app.config['HTML_LANG'],
        'RTL_LANGUAGES': app.config['RTL_LANGUAGES'],
        'CURRENT_LANGUAGE': session.get('language', get_locale()),
        '_': gettext,
        '_l': lazy_gettext,
        'csrf_form': CsrfForm(),
    }


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


monitor = PlaylistMonitor(app)
# Маршруты импортируются после монитора: routes.playlists берёт его из extensions.
import extensions as _extensions  # noqa: E402

_extensions.monitor = monitor

from routes import register_routes  # noqa: E402

register_routes(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
