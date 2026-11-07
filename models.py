from datetime import datetime

from flask_login import UserMixin

from extensions import db
from services.token_crypto import EncryptedText


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    email_notifications_enabled = db.Column(db.Boolean, default=True)
    telegram_notifications_enabled = db.Column(db.Boolean, default=False)
    browser_notifications_enabled = db.Column(db.Boolean, default=True)

    telegram_chat_id = db.Column(db.String(50))
    telegram_username = db.Column(db.String(100))

    language = db.Column(db.String(5), default='ru')
    email_verified = db.Column(db.Boolean, nullable=False, default=True)
    email_verify_nonce = db.Column(db.String(64))
    password_reset_nonce = db.Column(db.String(64))

    spotify_tokens = db.relationship('SpotifyToken', backref='user', lazy=True)
    deezer_tokens = db.relationship('DeezerToken', backref='user', lazy=True)
    apple_music_tokens = db.relationship('AppleMusicToken', backref='user', lazy=True)
    yandex_music_tokens = db.relationship('YandexMusicToken', backref='user', lazy=True)
    playlists = db.relationship('Playlist', backref='user', lazy=True)
    push_subscriptions = db.relationship(
        'PushSubscription', backref='user', lazy=True, cascade='all, delete-orphan'
    )


class SpotifyToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(EncryptedText, nullable=False)
    refresh_token = db.Column(EncryptedText, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DeezerToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(EncryptedText, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AppleMusicToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(EncryptedText, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class YandexMusicToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(EncryptedText, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service = db.Column(db.String(20), nullable=False)
    service_playlist_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime)
    tracks = db.relationship('Track', backref='playlist', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'service', 'service_playlist_id',
            name='uq_user_service_playlist',
        ),
    )


class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    service_track_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    album = db.Column(db.String(200))
    duration = db.Column(db.Integer)
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
    playlist = db.relationship('Playlist', backref='notifications', lazy=True)
    track = db.relationship('Track', backref='notifications', lazy=True)


class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh_key = db.Column(db.Text, nullable=False)
    auth_key = db.Column(db.Text, nullable=False)
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)


class NotificationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    notification_type = db.Column(db.String(20), nullable=False)
    track_service_id = db.Column(db.String(255))
    track_name = db.Column(db.String(255))
    artist_name = db.Column(db.String(255))
    playlist_name = db.Column(db.String(255))
    message = db.Column(db.Text, nullable=False)
    sent_via = db.Column(db.String(50))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='notification_history', lazy=True)
    playlist = db.relationship('Playlist', backref='notification_history', lazy=True)

    __table_args__ = (
        db.Index(
            'idx_unique_notification',
            'user_id', 'playlist_id', 'track_service_id', 'notification_type',
            unique=True,
        ),
    )
