"""Настраивает окружение до импорта приложения.

app.py читает DATABASE_URL в момент импорта, поэтому эти значения
должны быть заданы при загрузке пакета tests, раньше тестовых модулей.
"""
import os
import tempfile
from pathlib import Path

_db_path = Path(tempfile.gettempdir()) / 'playlistchecker_unit.db'
if _db_path.exists():
    try:
        _db_path.unlink()
    except OSError:
        pass

os.environ['DATABASE_URL'] = 'sqlite:///' + _db_path.as_posix()
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['TELEGRAM_WEBHOOK_SECRET'] = 'hook-secret'
os.environ['SPOTIFY_CLIENT_ID'] = 'cid'
os.environ['SPOTIFY_CLIENT_SECRET'] = 'csecret'
os.environ['SPOTIFY_REDIRECT_URI'] = 'http://localhost:5000/auth/spotify/callback'
os.environ['MAIL_USERNAME'] = ''
os.environ['MAIL_PASSWORD'] = ''
