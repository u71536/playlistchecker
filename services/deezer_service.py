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
    
    def _fetch_public_json(self, url, params=None):
        response = requests.get(url, params=params, timeout=20)
        if response.status_code != 200:
            raise Exception(gettext(
                'service.deezer.playlist_info_error',
                status_code=response.status_code,
            ))
        data = response.json()
        if data.get('error'):
            raise Exception(gettext(
                'service.deezer.playlist_info_error',
                status_code=data['error'].get('type', response.status_code),
            ))
        return data

    def get_public_playlist_info(self, playlist_url):
        """Информация о публичном плейлисте через API Deezer, без RapidAPI."""
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.deezer.invalid_playlist_url'))
        try:
            data = self._fetch_public_json(f'{self.base_url}/playlist/{playlist_id}')
            creator = data.get('creator') or {}
            return {
                'id': str(data['id']),
                'name': data['title'],
                'description': data.get('description') or '',
                'tracks_count': data.get('nb_tracks', 0),
                'owner': creator.get('name', 'Unknown'),
                'public': data.get('public', True),
            }
        except ValueError:
            raise
        except Exception as error:
            raise Exception(gettext(
                'service.deezer.playlist_info_error',
                status_code=str(error),
            ))

    def get_public_playlist_tracks(self, playlist_url):
        """Треки публичного плейлиста через API Deezer, без RapidAPI."""
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.deezer.invalid_playlist_url'))
        try:
            tracks = []
            seen = 0
            total = None
            url = f'{self.base_url}/playlist/{playlist_id}/tracks'
            params = {'limit': 100}
            while url:
                data = self._fetch_public_json(url, params=params)
                page = data.get('data') or []
                if total is None:
                    total = data.get('total')
                seen += len(page)
                for track_data in page:
                    if not track_data or not track_data.get('id'):
                        continue
                    artist = track_data.get('artist') or {}
                    album = track_data.get('album') or {}
                    tracks.append({
                        'id': str(track_data['id']),
                        'name': track_data.get('title') or '',
                        'artist': artist.get('name', 'Unknown'),
                        'album': album.get('title', ''),
                        'duration': track_data.get('duration', 0),
                        'added_at': datetime.utcnow().isoformat(),
                    })
                url = data.get('next')
                params = None
            if total is not None and seen < total:
                raise Exception(gettext(
                    'service.deezer.playlist_tracks_error',
                    error='incomplete',
                ))
            return tracks
        except ValueError:
            raise
        except Exception as error:
            raise Exception(gettext(
                'service.deezer.playlist_tracks_error',
                error=str(error),
            ))
    
    def is_token_valid(self, access_token):
        """Проверить валидность токена"""
        url = f"{self.base_url}/user/me"
        params = {'access_token': access_token}
        
        response = requests.get(url, params=params)
        return response.status_code == 200
