import requests
import os
from datetime import datetime, timedelta
import json
import re
from flask_babel import gettext

class DeezerService:
    def __init__(self, app_id=None, app_secret=None, redirect_uri=None):
        self.app_id = app_id or os.environ.get('DEEZER_APP_ID')
        self.app_secret = app_secret or os.environ.get('DEEZER_APP_SECRET')
        self.redirect_uri = redirect_uri or os.environ.get('DEEZER_REDIRECT_URI')
        self.base_url = "https://api.deezer.com"
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY')
        self.rapidapi_host = "deezerdevs-deezer.p.rapidapi.com"
    
    def get_auth_url(self):
        """Получить URL для авторизации"""
        params = {
            'app_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'perms': 'basic_access,email,manage_library'
        }
        return f"https://connect.deezer.com/oauth/auth.php?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    def get_access_token(self, code):
        """Получить токен доступа по коду авторизации"""
        url = "https://connect.deezer.com/oauth/access_token.php"
        params = {
            'app_id': self.app_id,
            'secret': self.app_secret,
            'code': code
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            # Deezer возвращает токен в формате "access_token=TOKEN&expires=SECONDS"
            token_data = response.text
            if 'access_token=' in token_data:
                token = token_data.split('access_token=')[1].split('&')[0]
                expires_in = int(token_data.split('expires=')[1]) if 'expires=' in token_data else 3600
                return {
                    'access_token': token,
                    'expires_in': expires_in,
                    'expires_at': datetime.utcnow() + timedelta(seconds=expires_in)
                }
        
        raise Exception(gettext('service.deezer.access_token_error'))
    
    def get_playlist_info(self, access_token, playlist_url):
        """Получить информацию о плейлисте"""
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.deezer.invalid_playlist_url'))
        
        url = f"{self.base_url}/playlist/{playlist_id}"
        params = {'access_token': access_token}
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                'id': str(data['id']),
                'name': data['title'],
                'description': data.get('description', ''),
                'tracks_count': data['nb_tracks'],
                'owner': data['creator']['name'],
                'public': data.get('public', True)
            }
        else:
            raise Exception(gettext('service.deezer.playlist_info_error', status_code=response.status_code))
    
    def get_playlist_tracks(self, access_token, playlist_id):
        """Получить треки плейлиста"""
        tracks = []
        url = f"{self.base_url}/playlist/{playlist_id}/tracks"
        params = {'access_token': access_token, 'limit': 100}
        index = 0
        
        while True:
            params['index'] = index
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                break
            
            data = response.json()
            if not data.get('data'):
                break
            
            for track_data in data['data']:
                tracks.append({
                    'id': str(track_data['id']),
                    'name': track_data['title'],
                    'artist': track_data['artist']['name'],
                    'album': track_data['album']['title'],
                    'duration': track_data['duration'],
                    'added_at': datetime.utcnow().isoformat()  # Deezer не предоставляет время добавления
                })
            
            index += 100
            if index >= data.get('total', 0):
                break
        
        return tracks
    
    def _extract_playlist_id(self, url):
        """Извлечь ID плейлиста из URL"""
        # Паттерны для различных форматов URL Deezer
        patterns = [
            r'deezer\.com/playlist/(\d+)',
            r'playlist/(\d+)',
            r'playlist:(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _get_rapidapi_headers(self):
        """Получить заголовки для RapidAPI"""
        if not self.rapidapi_key:
            raise ValueError("RAPIDAPI_KEY не установлен в переменных окружения")
        
        return {
            'x-rapidapi-key': self.rapidapi_key,
            'x-rapidapi-host': self.rapidapi_host
        }
    
    def get_public_playlist_info(self, playlist_url):
        """Получить информацию о плейлисте через RapidAPI (без авторизации)"""
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.deezer.invalid_playlist_url'))
        
        try:
            url = f"https://{self.rapidapi_host}/playlist/{playlist_id}"
            headers = self._get_rapidapi_headers()
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'id': str(data['id']),
                    'name': data['title'],
                    'description': data.get('description', ''),
                    'tracks_count': data.get('nb_tracks', 0),
                    'owner': data.get('creator', {}).get('name', 'Unknown'),
                    'public': data.get('public', True)
                }
            else:
                raise Exception(gettext('service.deezer.playlist_info_error', status_code=response.status_code))
        except Exception as e:
            raise Exception(gettext('service.deezer.playlist_info_error', status_code=str(e)))
    
    def get_public_playlist_tracks(self, playlist_url):
        """Получить треки плейлиста через RapidAPI (без авторизации)"""
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.deezer.invalid_playlist_url'))
        
        try:
            tracks = []
            url = f"https://{self.rapidapi_host}/playlist/{playlist_id}"
            headers = self._get_rapidapi_headers()
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Получаем треки из плейлиста
                tracks_data = data.get('tracks', {}).get('data', [])
                
                for track_data in tracks_data:
                    # Проверяем, что трек не None (может быть удален)
                    if track_data:
                        tracks.append({
                            'id': str(track_data['id']),
                            'name': track_data['title'],
                            'artist': track_data.get('artist', {}).get('name', 'Unknown'),
                            'album': track_data.get('album', {}).get('title', ''),
                            'duration': track_data.get('duration', 0),
                            'added_at': datetime.utcnow().isoformat()
                        })
                
                # Обрабатываем пагинацию, если есть
                tracks_obj = data.get('tracks', {})
                next_url = tracks_obj.get('next')
                index = len(tracks_data)
                
                while next_url:
                    # Для RapidAPI используем параметр index для пагинации
                    pagination_url = f"https://{self.rapidapi_host}/playlist/{playlist_id}/tracks"
                    params = {'index': index, 'limit': 100}
                    
                    pagination_response = requests.get(pagination_url, headers=headers, params=params)
                    
                    if pagination_response.status_code == 200:
                        pagination_data = pagination_response.json()
                        pagination_tracks = pagination_data.get('data', [])
                        
                        if not pagination_tracks:
                            break
                        
                        for track_data in pagination_tracks:
                            if track_data:
                                tracks.append({
                                    'id': str(track_data['id']),
                                    'name': track_data['title'],
                                    'artist': track_data.get('artist', {}).get('name', 'Unknown'),
                                    'album': track_data.get('album', {}).get('title', ''),
                                    'duration': track_data.get('duration', 0),
                                    'added_at': datetime.utcnow().isoformat()
                                })
                        
                        index += len(pagination_tracks)
                        next_url = pagination_data.get('next')
                    else:
                        break
                
                return tracks
            else:
                raise Exception(gettext('service.deezer.playlist_tracks_error', error=f"Status code: {response.status_code}"))
        except Exception as e:
            raise Exception(gettext('service.deezer.playlist_tracks_error', error=str(e)))
    
    def is_token_valid(self, access_token):
        """Проверить валидность токена"""
        url = f"{self.base_url}/user/me"
        params = {'access_token': access_token}
        
        response = requests.get(url, params=params)
        return response.status_code == 200
