import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from werkzeug.security import generate_password_hash

import app as app_module
from app import (
    Notification,
    NotificationHistory,
    Playlist,
    SpotifyToken,
    Track,
    User,
    app,
    db,
    monitor,
)
from services.spotify_service import SpotifyService
from services.telegram_link import make_start_token


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.context = app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()
        self.spotify = monitor.services['spotify']
        self.original_playlist_info = self.spotify.get_playlist_info
        self.original_playlist_tracks = self.spotify.get_playlist_tracks

    def tearDown(self):
        self.spotify.get_playlist_info = self.original_playlist_info
        self.spotify.get_playlist_tracks = self.original_playlist_tracks
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_scheduler_is_not_started_by_the_web_app(self):
        self.assertFalse(hasattr(app_module, 'scheduler'))

    def test_password_hash_fits_column(self):
        hashed = generate_password_hash(
            'correct-horse-battery-staple',
            method='scrypt',
        )
        column = User.__table__.columns['password_hash']
        self.assertGreater(len(hashed), 120)
        self.assertGreaterEqual(column.type.length, len(hashed))
        user = self._make_user()
        user.password_hash = hashed
        db.session.commit()
        stored = db.session.get(User, user.id).password_hash
        self.assertEqual(stored, hashed)

    def test_add_playlist_stores_tracks(self):
        user = self._make_user()
        self._attach_spotify(user)
        self.spotify.get_playlist_info = lambda *args, **kwargs: {
            'id': 'pl1',
            'name': 'Night Drive',
            'description': 'late',
        }
        self.spotify.get_playlist_tracks = lambda *args, **kwargs: [
            {
                'id': 't1',
                'name': 'Song A',
                'artist': 'Artist',
                'album': 'Album',
                'duration': 180,
            },
            {
                'id': 't2',
                'name': 'Song B',
                'artist': 'Artist',
                'album': 'Album',
                'duration': 200,
            },
        ]

        playlist = monitor.add_playlist(
            user,
            'spotify',
            'https://open.spotify.com/playlist/pl1',
        )

        self.assertEqual(playlist.name, 'Night Drive')
        stored = Track.query.filter_by(playlist_id=playlist.id).all()
        self.assertEqual(
            sorted(track.service_track_id for track in stored),
            ['t1', 't2'],
        )

    def test_removed_track_is_marked_and_notified(self):
        user = self._make_user()
        self._attach_spotify(user)
        playlist = Playlist(
            user_id=user.id,
            service='spotify',
            service_playlist_id='pl1',
            name='Night Drive',
            description='',
        )
        db.session.add(playlist)
        db.session.flush()
        db.session.add(Track(
            playlist_id=playlist.id,
            service_track_id='t1',
            name='Song A',
            artist='Artist',
        ))
        removed = Track(
            playlist_id=playlist.id,
            service_track_id='t2',
            name='Song B',
            artist='Artist',
        )
        db.session.add(removed)
        db.session.commit()

        self.spotify.get_playlist_tracks = lambda *args, **kwargs: [
            {
                'id': 't1',
                'name': 'Song A',
                'artist': 'Artist',
                'album': 'Album',
                'duration': 180,
            },
        ]

        monitor.check_playlist(playlist)
        db.session.expire_all()

        gone = Track.query.filter_by(service_track_id='t2').one()
        kept = Track.query.filter_by(service_track_id='t1').one()
        self.assertTrue(gone.is_removed)
        self.assertIsNotNone(gone.removed_at)
        self.assertFalse(kept.is_removed)
        note = Notification.query.filter_by(track_id=gone.id).one()
        self.assertIn('Song B', note.message)

    def test_delete_playlist_removes_only_the_owned_one(self):
        owner = self._make_user()
        other = self._make_user('bob', 'bob@example.com')
        owned = self._playlist(owner, 'pl-owned', 'Mine')
        foreign = self._playlist(other, 'pl-foreign', 'Theirs')
        track = Track(
            playlist_id=owned.id,
            service_track_id='t',
            name='Song',
            artist='Artist',
        )
        db.session.add(track)
        db.session.flush()
        db.session.add(Notification(
            user_id=owner.id,
            playlist_id=owned.id,
            track_id=track.id,
            message='gone',
        ))
        db.session.add(NotificationHistory(
            user_id=owner.id,
            playlist_id=owned.id,
            notification_type='track_removed',
            track_service_id='t',
            message='gone',
        ))
        db.session.commit()
        owned_id = owned.id
        foreign_id = foreign.id
        track_id = track.id

        self._login(owner)
        deleted = self.client.post(f'/playlist/{owned_id}/delete')
        self.assertEqual(deleted.status_code, 302)
        self.assertIsNone(db.session.get(Playlist, owned_id))
        self.assertIsNone(db.session.get(Track, track_id))
        self.assertEqual(Notification.query.filter_by(playlist_id=owned_id).count(), 0)
        self.assertEqual(
            NotificationHistory.query.filter_by(playlist_id=owned_id).count(),
            0,
        )

        rejected = self.client.post(f'/playlist/{foreign_id}/delete')
        self.assertEqual(rejected.status_code, 302)
        self.assertEqual(db.session.get(Playlist, foreign_id).name, 'Theirs')

    def test_playlists_page_renders_delete_form(self):
        user = self._make_user()
        playlist = self._playlist(user, 'pl1', 'Mine')
        self._login(user)
        response = self.client.get('/playlists')
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'/playlist/{playlist.id}/delete'.encode(), response.data)

    def test_spotify_callback_rejects_missing_state(self):
        user = self._make_user()
        self._login(user)
        with patch.object(
            SpotifyService,
            'get_access_token',
            side_effect=AssertionError('code must not be exchanged'),
        ):
            response = self.client.get('/auth/spotify/callback?code=abc')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SpotifyToken.query.count(), 0)

    def test_spotify_auth_keeps_state_through_callback(self):
        user = self._make_user()
        self._login(user)
        started = self.client.get('/auth/spotify')
        self.assertEqual(started.status_code, 302)
        state = parse_qs(urlparse(started.headers['Location']).query)['state'][0]
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['spotify_oauth_state'], state)

        with patch.object(
            SpotifyService,
            'get_access_token',
            return_value={
                'access_token': 'access',
                'refresh_token': 'refresh',
                'expires_in': 3600,
            },
        ):
            finished = self.client.get(
                f'/auth/spotify/callback?code=abc&state={state}'
            )
        self.assertEqual(finished.status_code, 302)
        stored = SpotifyToken.query.filter_by(user_id=user.id).one()
        self.assertEqual(stored.access_token, 'access')

    def test_telegram_webhook_rejects_missing_secret(self):
        response = self.client.post(
            '/api/telegram/webhook',
            json={
                'message': {
                    'text': '/start 1',
                    'chat': {'id': 5},
                }
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_telegram_webhook_ignores_raw_user_id(self):
        user = self._make_user()
        with patch(
            'services.notification_service.notification_service.send_telegram_notification',
            return_value=True,
        ):
            response = self.client.post(
                '/api/telegram/webhook',
                json={
                    'message': {
                        'text': f'/start {user.id}',
                        'chat': {'id': 99, 'username': 'eve'},
                    }
                },
                headers={'X-Telegram-Bot-Api-Secret-Token': 'hook-secret'},
            )
        self.assertEqual(response.status_code, 200)
        db.session.refresh(user)
        self.assertIsNone(user.telegram_chat_id)

    def test_telegram_webhook_accepts_signed_start(self):
        user = self._make_user()
        token = make_start_token(user.id, app.config['SECRET_KEY'])
        with patch(
            'services.notification_service.notification_service.send_telegram_notification',
            return_value=True,
        ):
            response = self.client.post(
                '/api/telegram/webhook',
                json={
                    'message': {
                        'text': f'/start {token}',
                        'chat': {'id': 99, 'username': 'alice'},
                    }
                },
                headers={'X-Telegram-Bot-Api-Secret-Token': 'hook-secret'},
            )
        self.assertEqual(response.status_code, 200)
        db.session.refresh(user)
        self.assertEqual(user.telegram_chat_id, '99')
        self.assertEqual(user.telegram_username, 'alice')

    def _make_user(self, username='alice', email='alice@example.com'):
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash('secret-password'),
            email_notifications_enabled=False,
            browser_notifications_enabled=False,
            telegram_notifications_enabled=False,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def _attach_spotify(self, user):
        db.session.add(SpotifyToken(
            user_id=user.id,
            access_token='access',
            refresh_token='refresh',
            expires_at=datetime.utcnow() + timedelta(hours=2),
        ))
        db.session.commit()

    def _playlist(self, user, service_playlist_id, name):
        playlist = Playlist(
            user_id=user.id,
            service='spotify',
            service_playlist_id=service_playlist_id,
            name=name,
            description='',
        )
        db.session.add(playlist)
        db.session.commit()
        return playlist

    def _login(self, user):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True


if __name__ == '__main__':
    unittest.main()
