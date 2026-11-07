import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

_FERNET_PREFIX = 'gAAAAA'


def _fernet():
    secret = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


class EncryptedText(TypeDecorator):
    """Encrypt token columns. Values saved before encryption stay readable."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if not value or not isinstance(value, str):
            return value
        if value.startswith(_FERNET_PREFIX):
            return value
        return _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if not value or not isinstance(value, str):
            return value
        if not value.startswith(_FERNET_PREFIX):
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            return value
