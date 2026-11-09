import os
import re
import time
from datetime import datetime

import jwt
import requests
from flask_babel import gettext


_STOREFRONT = re.compile(r'music\.apple\.com/([a-z]{2})/')
_PLAYLIST_ID = (
    re.compile(r'music\.apple\.com/.*?/playlist/[^/]+/([a-zA-Z0-9\.]+)'),
    re.compile(r'playlist/([a-zA-Z0-9\.]+)'),
    re.compile(r'pl\.([a-zA-Z0-9\.]+)'),
)


class AppleMusicService:
    def __init__(self, team_id=None, key_id=None, private_key=None):
        self.team_id = team_id or os.environ.get('APPLE_MUSIC_TEAM_ID')
        self.key_id = key_id or os.environ.get('APPLE_MUSIC_KEY_ID')
        private_key_env = (
            private_key or os.environ.get('APPLE_MUSIC_PRIVATE_KEY')
        )
        self.private_key = self._load_private_key(private_key_env)
        self.base_url = "https://api.music.apple.com"
    
    def _load_private_key(self, key_source):
        """Загрузить приватный ключ из файла или переменной окружения"""
        if not key_source:
            return None

        # Если ключ содержит BEGIN PRIVATE KEY, обрабатываем как строку
        if 'BEGIN PRIVATE KEY' in key_source:
            # Заменяем \n на реальные переносы строк
            return key_source.replace('\\n', '\n')

        # Проверяем, является ли это путем к файлу
        # Сначала проверяем указанный путь
        if os.path.isfile(key_source):
            try:
                with open(key_source, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                raise Exception(
                    f"Ошибка чтения файла ключа: {e}"
                )

        # Если файл не найден, пробуем найти относительно корня проекта
        # (где обычно находится app.py)
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        key_path = os.path.join(project_root, key_source)
        if os.path.isfile(key_path):
            try:
                with open(key_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                raise Exception(
                    f"Ошибка чтения файла ключа: {e}"
                )

        # Если это не файл и не ключ, возвращаем как есть
        # (может быть это уже сам ключ в неправильном формате)
        return key_source
    
    def get_developer_token(self):
        """Получить developer token для Apple Music API"""
        if not all([self.team_id, self.key_id, self.private_key]):
            raise Exception(gettext('service.apple_music.credentials_not_configured'))
        
        # Создаем JWT токен
        headers = {
            'alg': 'ES256',
            'kid': self.key_id
        }
        
        payload = {
            'iss': self.team_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600  # Токен действителен 1 час
        }
        
        try:
            token = jwt.encode(payload, self.private_key, algorithm='ES256', headers=headers)
            return token
        except Exception as e:
            raise Exception(gettext('service.apple_music.developer_token_error', error=str(e)))
    
    def get_playlist_info(self, playlist_url, user_token=None):
        """Получить информацию о плейлисте"""
        storefront, playlist_id = self.parse_playlist_ref(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.apple_music.invalid_playlist_url'))
        
        developer_token = self.get_developer_token()
        headers = {
            'Authorization': f'Bearer {developer_token}'
        }
        
        # User Token опционален - нужен только для приватных плейлистов
        if user_token:
            headers['Music-User-Token'] = user_token
        
        url = f"{self.base_url}/v1/catalog/{storefront}/playlists/{playlist_id}"

        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            playlist = data['data'][0]
            tracks_data = playlist['relationships'].get('tracks', {}).get('data', [])
            return {
                'id': self.storage_id(storefront, playlist['id']),
                'name': playlist['attributes']['name'],
                'description': playlist['attributes'].get('description', {}).get('standard', ''),
                'tracks_count': len(tracks_data),
                'owner': playlist['attributes'].get('curatorName', 'Unknown'),
                'public': True
            }
        else:
            raise Exception(
                gettext(
                    'service.apple_music.playlist_info_error',
                    status_code=response.status_code
                )
            )
    
    def get_public_playlist_info(self, playlist_url):
        """Получить информацию о публичном плейлисте (без user token)"""
        return self.get_playlist_info(playlist_url, user_token=None)
    
    def get_playlist_tracks(self, playlist_id, user_token=None, storefront=None):
        """Получить треки плейлиста. Неполный ответ считается ошибкой, а не пустым плейлистом."""
        if storefront is None:
            storefront, playlist_id = self.split_storage_id(playlist_id)
        developer_token = self.get_developer_token()
        headers = {
            'Authorization': f'Bearer {developer_token}'
        }
        if user_token:
            headers['Music-User-Token'] = user_token

        tracks = []
        url = f"{self.base_url}/v1/catalog/{storefront}/playlists/{playlist_id}/tracks"
        limit = 100
        offset = 0

        while True:
            response = requests.get(
                url,
                headers=headers,
                params={'limit': limit, 'offset': offset},
                timeout=20,
            )
            if response.status_code != 200:
                raise Exception(gettext(
                    'service.apple_music.playlist_info_error',
                    status_code=response.status_code,
                ))
            data = response.json()
            page = data.get('data') or []
            total = (data.get('meta') or {}).get('total')
            for track_data in page:
                if track_data.get('type') != 'songs':
                    continue
                track = track_data['attributes']
                tracks.append({
                    'id': track_data['id'],
                    'name': track['name'],
                    'artist': track['artistName'],
                    'album': track['albumName'],
                    'duration': int(track['durationInMillis'] / 1000),
                    'added_at': datetime.utcnow().isoformat(),
                })
            offset += limit
            if total is None:
                if len(page) < limit:
                    break
                continue
            if offset >= total:
                break
            if not page:
                raise Exception(gettext(
                    'service.apple_music.playlist_info_error',
                    status_code='incomplete',
                ))
        return tracks

    def get_public_playlist_tracks(self, playlist_url):
        """Получить треки публичного плейлиста (без user token)"""
        storefront, playlist_id = self.parse_playlist_ref(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.apple_music.invalid_playlist_url'))
        return self.get_playlist_tracks(playlist_id, user_token=None, storefront=storefront)

    def parse_playlist_ref(self, url):
        storefront_match = _STOREFRONT.search(url or '')
        storefront = storefront_match.group(1) if storefront_match else 'us'
        return storefront, self._extract_playlist_id(url)

    def storage_id(self, storefront, playlist_id):
        return f'{storefront}:{playlist_id}'

    def split_storage_id(self, storage_id):
        if storage_id and ':' in storage_id:
            storefront, playlist_id = storage_id.split(':', 1)
            if len(storefront) == 2 and storefront.isalpha():
                return storefront.lower(), playlist_id
        return 'us', storage_id

    def _extract_playlist_id(self, url):
        """Извлечь ID плейлиста из URL"""
        for pattern in _PLAYLIST_ID:
            match = pattern.search(url or '')
            if match:
                playlist_id = match.group(1)
                if pattern is _PLAYLIST_ID[2] and not playlist_id.startswith('pl.'):
                    return f'pl.{playlist_id}'
                return playlist_id
        return None
    
    def is_token_valid(self, user_token):
        """Проверить валидность пользовательского токена"""
        if not user_token:
            return False
        try:
            developer_token = self.get_developer_token()
            headers = {
                'Authorization': f'Bearer {developer_token}',
                'Music-User-Token': user_token
            }
            
            url = f"{self.base_url}/v1/me"
            response = requests.get(url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False
