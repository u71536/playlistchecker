import re

import requests
from datetime import datetime
from flask_babel import gettext

_USER_PLAYLIST = re.compile(
    r'music\.yandex\.ru/users/([^/?#]+)/playlists/(\d+)'
)
_PUBLIC_PLAYLIST = re.compile(
    r'music\.yandex\.ru/playlists/([^/?#]+)'
)


class YandexMusicService:
    def __init__(self):
        self.base_url = 'https://api.music.yandex.net'

    def storage_id_from_url(self, url):
        """Ключ плейлиста: owner:kind для пользовательских, иначе id из ссылки."""
        if not url:
            return None
        user_match = _USER_PLAYLIST.search(url)
        if user_match:
            return f'{user_match.group(1)}:{user_match.group(2)}'
        public_match = _PUBLIC_PLAYLIST.search(url)
        if public_match and ':' not in public_match.group(1):
            return public_match.group(1)
        return None

    def _request_playlist(self, storage_id):
        if not storage_id:
            raise ValueError(gettext('service.yandex_music.invalid_playlist_url'))
        if ':' in storage_id:
            owner, kind = storage_id.split(':', 1)
            url = f'{self.base_url}/users/{owner}/playlists/{kind}'
        else:
            url = f'{self.base_url}/playlist/{storage_id}'
        response = requests.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json',
            },
            timeout=20,
        )
        if response.status_code != 200:
            raise Exception(gettext(
                'service.yandex_music.api_error',
                status_code=response.status_code,
                response_text=response.text,
            ))
        return response.json()['result']

    def _storage_id_from_result(self, result, fallback):
        owner = (result.get('owner') or {}).get('login')
        kind = result.get('kind')
        if owner and kind is not None:
            return f'{owner}:{kind}'
        return fallback

    def get_public_playlist_info(self, playlist_url):
        """Информация о публичном плейлисте без OAuth."""
        storage_id = self.storage_id_from_url(playlist_url)
        if not storage_id:
            raise ValueError(gettext('service.yandex_music.invalid_playlist_url'))
        try:
            result = self._request_playlist(storage_id)
            owner = result.get('owner') or {}
            return {
                'id': self._storage_id_from_result(result, storage_id),
                'name': result['title'],
                'description': result.get('description') or '',
                'tracks_count': result.get('trackCount', 0),
                'owner': owner.get('name') or owner.get('login') or '',
                'public': result.get('visibility') == 'public',
            }
        except ValueError:
            raise
        except Exception as error:
            raise Exception(gettext(
                'service.yandex_music.playlist_info_error',
                error=str(error),
            ))

    def get_playlist_tracks_by_id(self, storage_id):
        """Треки по сохранённому ключу owner:kind."""
        try:
            result = self._request_playlist(storage_id)
        except ValueError:
            raise
        except Exception as error:
            raise Exception(gettext(
                'service.yandex_music.playlist_tracks_error',
                error=str(error),
            ))
        tracks = []
        for track_data in result.get('tracks') or []:
            track = track_data.get('track') if isinstance(track_data, dict) else None
            if not track or not track.get('id'):
                continue
            albums = track.get('albums') or []
            artists = track.get('artists') or []
            duration_ms = track.get('durationMs') or 0
            tracks.append({
                'id': str(track['id']),
                'name': track.get('title') or '',
                'artist': ', '.join(
                    artist.get('name', '') for artist in artists if artist.get('name')
                ),
                'album': albums[0].get('title', '') if albums else '',
                'duration': duration_ms // 1000,
                'added_at': datetime.utcnow().isoformat(),
            })
        return tracks

    def get_public_playlist_tracks(self, playlist_url):
        """Треки публичного плейлиста без OAuth."""
        storage_id = self.storage_id_from_url(playlist_url)
        if not storage_id:
            raise ValueError(gettext('service.yandex_music.invalid_playlist_url'))
        info = self.get_public_playlist_info(playlist_url)
        return self.get_playlist_tracks_by_id(info['id'])
