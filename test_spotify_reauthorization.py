#!/usr/bin/env python3
"""Tests for Spotify invalid_grant handling (6-month refresh token expiry)."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from spotipy.oauth2 import SpotifyOauthError

from services.spotify_service import (
    SpotifyReauthorizationRequired,
    SpotifyService,
    TokenExpiredError,
)


def _invalid_grant_error(description='Refresh token expired'):
    return SpotifyOauthError(
        'error: 400, Bad Request: invalid_grant',
        error='invalid_grant',
        error_description=description,
    )


class InvalidGrantDetectionTests(unittest.TestCase):
    def test_detects_oauth_error_code(self):
        self.assertTrue(SpotifyService.is_invalid_grant(_invalid_grant_error()))

    def test_detects_invalid_grant_in_message(self):
        self.assertTrue(SpotifyService.is_invalid_grant(Exception('invalid_grant')))

    def test_ignores_unrelated_errors(self):
        self.assertFalse(SpotifyService.is_invalid_grant(Exception('401 access token expired')))
        self.assertFalse(SpotifyService.is_invalid_grant(None))


class RefreshAccessTokenTests(unittest.TestCase):
    def setUp(self):
        self.gettext_patcher = patch(
            'services.spotify_service.gettext',
            side_effect=lambda msgid, **kwargs: msgid
        )
        self.gettext_patcher.start()
        self.service = SpotifyService()

    def tearDown(self):
        self.gettext_patcher.stop()

    @patch.object(SpotifyService, '_oauth')
    def test_invalid_grant_raises_reauthorization_required_without_retry(self, mock_oauth):
        oauth = mock_oauth.return_value
        oauth.refresh_access_token.side_effect = _invalid_grant_error()

        with self.assertRaises(SpotifyReauthorizationRequired):
            self.service.refresh_access_token('dead-refresh-token')

        oauth.refresh_access_token.assert_called_once_with('dead-refresh-token')

    @patch.object(SpotifyService, '_oauth')
    def test_other_refresh_errors_are_not_treated_as_reauthorization(self, mock_oauth):
        oauth = mock_oauth.return_value
        oauth.refresh_access_token.side_effect = SpotifyOauthError(
            'error: 500',
            error='server_error',
        )

        with self.assertRaises(SpotifyOauthError):
            self.service.refresh_access_token('refresh-token')

        oauth.refresh_access_token.assert_called_once()

    @patch.object(SpotifyService, '_oauth')
    def test_successful_refresh_returns_token_info(self, mock_oauth):
        token_info = {'access_token': 'new-access', 'expires_in': 3600}
        mock_oauth.return_value.refresh_access_token.return_value = token_info

        result = self.service.refresh_access_token('refresh-token')

        self.assertEqual(result, token_info)


class ApiRefreshPropagationTests(unittest.TestCase):
    def setUp(self):
        self.gettext_patcher = patch(
            'services.spotify_service.gettext',
            side_effect=lambda msgid, **kwargs: msgid
        )
        self.gettext_patcher.start()
        self.service = SpotifyService()

    def tearDown(self):
        self.gettext_patcher.stop()

    def test_401_with_successful_refresh_raises_token_expired_error(self):
        sp = MagicMock()
        sp.current_user_playlists.side_effect = Exception('401 - The access token expired')
        self.service.get_client = MagicMock(return_value=sp)
        new_token = {'access_token': 'new-access', 'expires_in': 3600}
        self.service.refresh_access_token = MagicMock(return_value=new_token)

        with self.assertRaises(TokenExpiredError) as ctx:
            self.service.get_user_playlists('old-access', 'refresh-token')

        self.assertEqual(ctx.exception.new_token_info, new_token)
        self.service.refresh_access_token.assert_called_once_with('refresh-token')

    def test_401_with_invalid_grant_raises_reauthorization_required(self):
        sp = MagicMock()
        sp.current_user_playlists.side_effect = Exception('401 - The access token expired')
        self.service.get_client = MagicMock(return_value=sp)
        self.service.refresh_access_token = MagicMock(
            side_effect=SpotifyReauthorizationRequired('reauth')
        )

        with self.assertRaises(SpotifyReauthorizationRequired):
            self.service.get_user_playlists('old-access', 'refresh-token')

        self.service.refresh_access_token.assert_called_once_with('refresh-token')

    def test_check_and_refresh_does_not_retry_invalid_grant(self):
        self.service.is_token_valid = MagicMock(return_value=False)
        self.service.refresh_access_token = MagicMock(
            side_effect=SpotifyReauthorizationRequired('reauth')
        )

        with self.assertRaises(SpotifyReauthorizationRequired):
            self.service.check_and_refresh_token(
                'old-access',
                'dead-refresh',
                datetime.utcnow() - timedelta(minutes=1),
            )

        self.service.refresh_access_token.assert_called_once_with('dead-refresh')


class DiscardTokenTests(unittest.TestCase):
    def test_monitor_discards_token_on_invalid_grant_and_does_not_retry(self):
        from playlist_monitor import PlaylistMonitor

        monitor = PlaylistMonitor()
        user = MagicMock()
        token = MagicMock()
        token.refresh_token = 'dead-refresh'
        token.expires_at = datetime.utcnow() - timedelta(minutes=1)
        user.spotify_tokens = [token]
        user.username = 'alice'

        monitor.services['spotify'].refresh_access_token = MagicMock(
            side_effect=SpotifyReauthorizationRequired('reauth')
        )
        monitor._discard_spotify_token = MagicMock()

        with self.assertRaises(SpotifyReauthorizationRequired):
            monitor._get_user_token(user, 'spotify')

        monitor.services['spotify'].refresh_access_token.assert_called_once_with('dead-refresh')
        monitor._discard_spotify_token.assert_called_once_with(user)

    def test_monitor_does_not_refresh_again_after_reauth_flag(self):
        from playlist_monitor import PlaylistMonitor

        monitor = PlaylistMonitor()
        user = MagicMock()
        user._spotify_reauth_required = True
        user.spotify_tokens = [MagicMock()]
        monitor.services['spotify'].refresh_access_token = MagicMock()

        with self.assertRaises(SpotifyReauthorizationRequired):
            monitor._get_user_token(user, 'spotify')

        monitor.services['spotify'].refresh_access_token.assert_not_called()


if __name__ == '__main__':
    unittest.main()
