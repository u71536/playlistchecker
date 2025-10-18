import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os


class TokenExpiredError(Exception):
    """Исключение для истекших токенов"""
    def __init__(self, message, new_token_info=None):
        super().__init__(message)
        self.new_token_info = new_token_info


class SpotifyService:
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        self.client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        self.client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI')
        
        self.scope = "playlist-read-private playlist-read-collaborative user-library-read"
        
    def get_auth_url(self):
        """Получить URL для авторизации"""
        sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        return sp_oauth.get_authorize_url()
    
    def get_access_token(self, code):
        """Получить токен доступа по коду авторизации"""
        sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        token_info = sp_oauth.get_access_token(code)
        return token_info
    
    def refresh_access_token(self, refresh_token):
        """Обновить токен доступа"""
        sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        token_info = sp_oauth.refresh_access_token(refresh_token)
        return token_info
    
    def get_client(self, access_token):
        """Получить клиент Spotify с токеном"""
        return spotipy.Spotify(auth=access_token)
    
    def get_playlist_info(self, access_token, playlist_url, refresh_token=None):
        """Получить информацию о плейлисте"""
        sp = self.get_client(access_token)
        
        # Извлекаем ID плейлиста из URL
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError("Неверный URL плейлиста Spotify")
        
        try:
            playlist = sp.playlist(playlist_id)
            return {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist['description'],
                'tracks_count': playlist['tracks']['total'],
                'owner': playlist['owner']['display_name'],
                'public': playlist['public']
            }
        except Exception as e:
            # Проверяем, является ли ошибка связанной с истекшим токеном
            if "401" in str(e) and "access token expired" in str(e).lower() and refresh_token:
                # Пытаемся обновить токен
                try:
                    new_token_info = self.refresh_access_token(refresh_token)
                    # Возвращаем информацию о новом токене вместе с ошибкой
                    raise TokenExpiredError("Токен истек", new_token_info)
                except Exception as refresh_error:
                    raise Exception(f"Ошибка обновления токена: {str(refresh_error)}")
            raise Exception(f"Ошибка получения информации о плейлисте: {str(e)}")
    
    def get_playlist_tracks(self, access_token, playlist_id, refresh_token=None):
        """Получить треки плейлиста"""
        sp = self.get_client(access_token)
        
        tracks = []
        offset = 0
        limit = 100
        
        while True:
            try:
                results = sp.playlist_tracks(playlist_id, offset=offset, limit=limit)
                if not results['items']:
                    break
                
                for item in results['items']:
                    if item['track']:  # Проверяем, что трек не удален
                        track = item['track']
                        tracks.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artist': ', '.join([artist['name'] for artist in track['artists']]),
                            'album': track['album']['name'],
                            'duration': track['duration_ms'] // 1000,  # Конвертируем в секунды
                            'added_at': item['added_at']
                        })
                
                offset += limit
                if offset >= results['total']:
                    break
                    
            except Exception as e:
                # Проверяем, является ли ошибка связанной с истекшим токеном
                if "401" in str(e) and "access token expired" in str(e).lower() and refresh_token:
                    # Пытаемся обновить токен
                    try:
                        new_token_info = self.refresh_access_token(refresh_token)
                        # Возвращаем информацию о новом токене вместе с ошибкой
                        raise TokenExpiredError("Токен истек", new_token_info)
                    except Exception as refresh_error:
                        raise Exception(f"Ошибка обновления токена: {str(refresh_error)}")
                raise Exception(f"Ошибка получения треков плейлиста: {str(e)}")
        
        return tracks
    
    def _extract_playlist_id(self, url):
        """Извлечь ID плейлиста из URL"""
        import re
        
        # Паттерны для различных форматов URL Spotify
        patterns = [
            r'open\.spotify\.com/playlist/([a-zA-Z0-9]+)',
            r'spotify:playlist:([a-zA-Z0-9]+)',
            r'playlist/([a-zA-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_user_playlists(self, access_token, refresh_token=None):
        """Получить все плейлисты пользователя"""
        sp = self.get_client(access_token)
        
        playlists = []
        offset = 0
        limit = 50
        
        while True:
            try:
                results = sp.current_user_playlists(limit=limit, offset=offset)
                if not results['items']:
                    break
                
                for playlist in results['items']:
                    playlists.append({
                        'id': playlist['id'],
                        'name': playlist['name'],
                        'description': playlist.get('description', ''),
                        'tracks_count': playlist['tracks']['total'],
                        'public': playlist['public'],
                        'owner': playlist['owner']['display_name'],
                        'url': playlist['external_urls']['spotify']
                    })
                
                offset += limit
                if offset >= results['total']:
                    break
                    
            except Exception as e:
                # Проверяем, является ли ошибка связанной с истекшим токеном
                if "401" in str(e) and "access token expired" in str(e).lower() and refresh_token:
                    # Пытаемся обновить токен
                    try:
                        new_token_info = self.refresh_access_token(refresh_token)
                        # Возвращаем информацию о новом токене вместе с ошибкой
                        raise TokenExpiredError("Токен истек", new_token_info)
                    except Exception as refresh_error:
                        raise Exception(f"Ошибка обновления токена: {str(refresh_error)}")
                raise Exception(f"Ошибка получения плейлистов пользователя: {str(e)}")
        
        return playlists
    
    def is_token_valid(self, access_token):
        """Проверить валидность токена"""
        try:
            sp = self.get_client(access_token)
            sp.current_user()  # Простой запрос для проверки токена
            return True
        except Exception:
            return False
