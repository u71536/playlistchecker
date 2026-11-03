import hashlib
import hmac
import os
import time

START_TOKEN_TTL_SECONDS = 24 * 60 * 60


def webhook_authorized(provided):
    """Проверить секрет, который Telegram присылает в заголовке webhook."""
    secret = os.environ.get('TELEGRAM_WEBHOOK_SECRET') or ''
    if not secret or not provided or len(provided) != len(secret):
        return False
    return hmac.compare_digest(provided, secret)


def make_start_token(user_id, secret_key, ttl_seconds=START_TOKEN_TTL_SECONDS):
    """Подписанный параметр /start. Влезает в лимит Telegram (64 символа, [A-Za-z0-9_-])."""
    expires_at = int(time.time()) + ttl_seconds
    signature = _sign(user_id, expires_at, secret_key)
    return f'{user_id}-{expires_at}-{signature}'


def parse_start_token(token, secret_key):
    """Вернуть user id или None, если токен подделан или просрочен."""
    if not token or not secret_key:
        return None
    parts = token.split('-')
    if len(parts) != 3:
        return None
    user_id_raw, expires_raw, signature = parts
    if len(signature) != 32:
        return None
    try:
        user_id = int(user_id_raw)
        expires_at = int(expires_raw)
    except ValueError:
        return None
    if user_id < 1 or expires_at < int(time.time()):
        return None
    expected = _sign(user_id, expires_at, secret_key)
    if not hmac.compare_digest(signature, expected):
        return None
    return user_id


def _sign(user_id, expires_at, secret_key):
    payload = f'{user_id}:{expires_at}'.encode()
    return hmac.new(secret_key.encode(), payload, hashlib.sha256).hexdigest()[:32]
