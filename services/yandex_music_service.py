import requests
from datetime import datetime
from flask_babel import gettext


class YandexMusicService:
    def __init__(self):
        pass
    
    def _extract_playlist_id(self, url):
        """Извлечь ID плейлиста из URL"""
        import re
        
        # Паттерны для различных форматов URL Yandex Music
        patterns = [
            r'music\.yandex\.ru/users/([^/]+)/playlists/(\d+)',
            r'music\.yandex\.ru/playlists/([a-f0-9-]+)',  # UUID формат для публичных плейлистов
            r'music\.yandex\.ru/playlists/ya\.music/playlists/ya\.music/(\d+)',  # Новый формат
            r'playlists/(\d+)',
            r'playlist/(\d+)',
            r'playlist/([a-f0-9-]+)'  # UUID формат
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1) if len(match.groups()) == 1 else match.group(2)
        
        return None
    
    def get_public_playlist_info(self, playlist_url):
        """Получить информацию о публичном плейлисте без авторизации"""
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.yandex_music.invalid_playlist_url'))
        
        try:
            # Используем прямой API endpoint для публичных плейлистов
            url = f"https://api.music.yandex.net/playlist/{playlist_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                result = data['result']
                return {
                    'id': str(result['kind']),
                    'name': result['title'],
                    'description': result.get('description', ''),
                    'tracks_count': result['trackCount'],
                    'owner': result['owner']['name'],
                    'public': result.get('visibility') == 'public'
                }
            else:
                raise Exception(gettext('service.yandex_music.api_error', status_code=response.status_code, response_text=response.text))
                
        except Exception as e:
            raise Exception(gettext('service.yandex_music.playlist_info_error', error=str(e)))
    
    def get_public_playlist_tracks(self, playlist_url):
        """Получить треки публичного плейлиста без авторизации"""
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(gettext('service.yandex_music.invalid_playlist_url'))
        
        try:
            # Используем прямой API endpoint для публичных плейлистов
            url = f"https://api.music.yandex.net/playlist/{playlist_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                result = data['result']
                tracks = []
                
                for track_data in result['tracks']:
                    track = track_data['track']
                    tracks.append({
                        'id': str(track['id']),
                        'name': track['title'],
                        'artist': ', '.join([artist['name'] for artist in track['artists']]),
                        'album': track['albums'][0]['title'] if track['albums'] else '',
                        'duration': track['durationMs'] // 1000,  # Конвертируем в секунды
                        'added_at': datetime.utcnow().isoformat()  # Yandex Music не предоставляет время добавления
                    })
                
                return tracks
            else:
                raise Exception(gettext('service.yandex_music.api_error', status_code=response.status_code, response_text=response.text))
                
        except Exception as e:
            raise Exception(gettext('service.yandex_music.playlist_tracks_error', error=str(e)))
    
