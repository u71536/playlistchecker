import requests
import os
import jwt
import time
from datetime import datetime, timedelta
import json
from flask_babel import gettext

class AppleMusicService:
    def __init__(self, team_id=None, key_id=None, private_key=None):
        self.team_id = team_id or os.environ.get('APPLE_MUSIC_TEAM_ID')
        self.key_id = key_id or os.environ.get('APPLE_MUSIC_KEY_ID')
        self.private_key = private_key or os.environ.get('APPLE_MUSIC_PRIVATE_KEY')
        self.base_url = "https://api.music.apple.com"
    
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
    
    def get_playlist_info(self, user_token, playlist_url):
        """Получить информацию о плейлисте"""
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.apple_music.invalid_playlist_url'))
        
        developer_token = self.get_developer_token()
        headers = {
            'Authorization': f'Bearer {developer_token}',
            'Music-User-Token': user_token
        }
        
        url = f"{self.base_url}/v1/catalog/us/playlists/{playlist_id}"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            playlist = data['data'][0]
            return {
                'id': playlist['id'],
                'name': playlist['attributes']['name'],
                'description': playlist['attributes'].get('description', {}).get('standard', ''),
                'tracks_count': playlist['relationships']['tracks']['data'],
                'owner': playlist['attributes'].get('curatorName', 'Unknown'),
                'public': True
            }
        else:
            raise Exception(gettext('service.apple_music.playlist_info_error', status_code=response.status_code))
    
    def get_playlist_tracks(self, user_token, playlist_id):
        """Получить треки плейлиста"""
        developer_token = self.get_developer_token()
        headers = {
            'Authorization': f'Bearer {developer_token}',
            'Music-User-Token': user_token
        }
        
        tracks = []
        url = f"{self.base_url}/v1/catalog/us/playlists/{playlist_id}/tracks"
        limit = 100
        offset = 0
        
        while True:
            params = {
                'limit': limit,
                'offset': offset
            }
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                break
            
            data = response.json()
            if not data.get('data'):
                break
            
            for track_data in data['data']:
                if track_data['type'] == 'songs':
                    track = track_data['attributes']
                    tracks.append({
                        'id': track_data['id'],
                        'name': track['name'],
                        'artist': track['artistName'],
                        'album': track['albumName'],
                        'duration': int(track['durationInMillis'] / 1000),  # Конвертируем в секунды
                        'added_at': datetime.utcnow().isoformat()  # Apple Music не предоставляет время добавления
                    })
            
            offset += limit
            if offset >= data.get('meta', {}).get('total', 0):
                break
        
        return tracks
    
    def _extract_playlist_id(self, url):
        """Извлечь ID плейлиста из URL"""
        import re
        
        # Паттерны для различных форматов URL Apple Music
        patterns = [
            r'music\.apple\.com/.*?/playlist/[^/]+/([a-zA-Z0-9\.]+)',
            r'playlist/([a-zA-Z0-9\.]+)',
            r'pl\.([a-zA-Z0-9\.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def is_token_valid(self, user_token):
        """Проверить валидность пользовательского токена"""
        try:
            developer_token = self.get_developer_token()
            headers = {
                'Authorization': f'Bearer {developer_token}',
                'Music-User-Token': user_token
            }
            
            url = f"{self.base_url}/v1/me"
            response = requests.get(url, headers=headers)
            return response.status_code == 200
        except:
            return False
