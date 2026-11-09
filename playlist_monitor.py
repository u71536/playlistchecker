from datetime import datetime, timedelta
from services.notification_service import notification_service
from services.check_schedule import is_due
from services.spotify_service import SpotifyService, TokenExpiredError, SpotifyReauthorizationRequired
from services.deezer_service import DeezerService
from services.apple_music_service import AppleMusicService
from services.yandex_music_service import YandexMusicService
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные для моделей базы данных (будут инициализированы позже)
db = None
User = None
Playlist = None
Track = None
Notification = None
SpotifyToken = None
DeezerToken = None
AppleMusicToken = None
YandexMusicToken = None


class PlaylistMonitor:
    def __init__(self, app=None):
        self.app = None
        self.services = {
            'spotify': SpotifyService(),
            'deezer': DeezerService(),
            'apple_music': AppleMusicService(),
            'yandex_music': YandexMusicService()
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Инициализация с Flask приложением"""
        self.app = app
        self._init_models()
    
    def _init_models(self):
        """Инициализация моделей базы данных"""
        global db, User, Playlist, Track, Notification
        global SpotifyToken, DeezerToken, AppleMusicToken, YandexMusicToken
        
        if self.app:
            with self.app.app_context():
                from app import (db as app_db, User as app_User,
                                Playlist as app_Playlist, Track as app_Track,
                                Notification as app_Notification,
                                SpotifyToken as app_SpotifyToken,
                                DeezerToken as app_DeezerToken,
                                AppleMusicToken as app_AppleMusicToken,
                                YandexMusicToken as app_YandexMusicToken)
                
                db = app_db
                User = app_User
                Playlist = app_Playlist
                Track = app_Track
                Notification = app_Notification
                SpotifyToken = app_SpotifyToken
                DeezerToken = app_DeezerToken
                AppleMusicToken = app_AppleMusicToken
                YandexMusicToken = app_YandexMusicToken
    
    def check_all_playlists(self):
        """Проверить все плейлисты всех пользователей"""
        logger.info("Начинаем проверку всех плейлистов")
        
        if self.app:
            with self.app.app_context():
                self._check_all_playlists_impl()
        else:
            self._check_all_playlists_impl()
    
    def _check_all_playlists_impl(self):
        """Внутренняя реализация проверки всех плейлистов"""
        users = User.query.all()
        for user in users:
            try:
                self.check_user_playlists(user)
            except SpotifyReauthorizationRequired:
                logger.warning(
                    f"Spotify reauthorization required for {user.username}; "
                    "stored token discarded, skipping remaining Spotify checks"
                )
            except Exception as e:
                logger.error(f"Ошибка при проверке плейлистов пользователя {user.username}: {str(e)}")
        
        logger.info("Проверка всех плейлистов завершена")

    def check_due_playlists(self, moment=None):
        """Проверить плейлисты пользователей, у которых сейчас выбранный час."""
        if self.app:
            with self.app.app_context():
                self._check_due_playlists_impl(moment)
        else:
            self._check_due_playlists_impl(moment)

    def _check_due_playlists_impl(self, moment):
        for user in User.query.all():
            if not is_due(user.check_hour, user.timezone, moment):
                continue
            try:
                self.check_user_playlists(user)
            except SpotifyReauthorizationRequired:
                logger.warning(
                    "Spotify reauthorization required for %s; stored token discarded",
                    user.username,
                )
            except Exception:
                logger.exception(
                    "Ошибка при проверке плейлистов пользователя %s", user.username,
                )
    
    def check_user_playlists(self, user):
        """Проверить плейлисты конкретного пользователя"""
        logger.info(f"Проверяем плейлисты пользователя {user.username}")
        
        if self.app:
            with self.app.app_context():
                self._check_user_playlists_impl(user)
        else:
            self._check_user_playlists_impl(user)
    
    def _check_user_playlists_impl(self, user):
        """Внутренняя реализация проверки плейлистов пользователя"""
        playlists = Playlist.query.filter_by(user_id=user.id).all()
        reauthorization_required = None
        for playlist in playlists:
            try:
                self.check_playlist(playlist)
            except SpotifyReauthorizationRequired as error:
                self._record_check_failure(playlist.id, error)
                reauthorization_required = error
                logger.warning(
                    f"Spotify refresh token expired for {user.username}; "
                    "will not retry refresh"
                )
            except Exception as error:
                logger.error(f"Ошибка при проверке плейлиста {playlist.name}: {str(error)}")
                self._record_check_failure(playlist.id, error)
        if reauthorization_required:
            raise reauthorization_required
    
    def check_playlist(self, playlist):
        """Проверить конкретный плейлист на изменения"""
        logger.info(f"Проверяем плейлист: {playlist.name} ({playlist.service})")
        
        if self.app:
            with self.app.app_context():
                self._check_playlist_impl(playlist)
        else:
            self._check_playlist_impl(playlist)
    
    def _check_playlist_impl(self, playlist):
        """Внутренняя реализация проверки плейлиста"""
        service = self.services.get(playlist.service)
        if not service:
            logger.error(f"Сервис {playlist.service} не найден")
            return
        
        # Для публичных плейлистов Яндекс.Музыки, Deezer и Apple Music не нужен токен
        if playlist.service == 'deezer':
            try:
                # Получаем треки плейлиста Deezer через RapidAPI
                playlist_url = f"https://www.deezer.com/playlist/{playlist.service_playlist_id}"
                current_tracks = service.get_public_playlist_tracks(playlist_url)
                self._sync_playlist_tracks(playlist, current_tracks)
                logger.info("Плейлист Deezer %s проверен", playlist.name)
                
            except Exception as e:
                logger.error(f"Ошибка при проверке плейлиста Deezer {playlist.name}: {str(e)}")
                raise
        elif playlist.service == 'apple_music':
            try:
                # Проверяем, есть ли User Token (для приватных плейлистов)
                user_token = self._get_user_token(playlist.user, 'apple_music')
                storefront, playlist_id = service.split_storage_id(playlist.service_playlist_id)
                current_tracks = service.get_playlist_tracks(
                    playlist_id,
                    user_token=user_token,
                    storefront=storefront,
                )
                self._sync_playlist_tracks(playlist, current_tracks)
                logger.info("Плейлист Apple Music %s проверен", playlist.name)
                
            except Exception as e:
                logger.error(f"Ошибка при проверке плейлиста Apple Music {playlist.name}: {str(e)}")
                raise
        elif playlist.service == 'yandex_music':
            try:
                current_tracks = service.get_playlist_tracks_by_id(
                    playlist.service_playlist_id
                )
                self._sync_playlist_tracks(playlist, current_tracks)
                logger.info("Публичный плейлист %s проверен", playlist.name)
                
            except Exception as e:
                logger.error(f"Ошибка при проверке публичного плейлиста {playlist.name}: {str(e)}")
                raise
        else:
            # Получаем токен доступа для сервиса
            access_token = self._get_user_token(playlist.user, playlist.service)
            if not access_token:
                logger.warning(f"Нет токена доступа для {playlist.service} у пользователя {playlist.user.username}")
                self._record_check_failure(playlist.id, "Нет токена доступа")
                return
            
            # Получаем refresh_token для Spotify
            refresh_token = None
            if playlist.service == 'spotify':
                token_record = playlist.user.spotify_tokens[0] if playlist.user.spotify_tokens else None
                if token_record:
                    refresh_token = token_record.refresh_token
            
            try:
                # Получаем текущие треки из плейлиста
                if playlist.service == 'spotify':
                    current_tracks = service.get_playlist_tracks(access_token, playlist.service_playlist_id, refresh_token)
                else:
                    current_tracks = service.get_playlist_tracks(access_token, playlist.service_playlist_id)
                self._sync_playlist_tracks(playlist, current_tracks)
                logger.info("Плейлист %s проверен", playlist.name)
                
            except SpotifyReauthorizationRequired:
                self._discard_spotify_token(playlist.user)
                raise
            except TokenExpiredError as e:
                if e.new_token_info and playlist.service == 'spotify':
                    token_record = playlist.user.spotify_tokens[0] if playlist.user.spotify_tokens else None
                    if token_record:
                        token_record.access_token = e.new_token_info['access_token']
                        if 'refresh_token' in e.new_token_info:
                            token_record.refresh_token = e.new_token_info['refresh_token']
                        token_record.expires_at = datetime.utcnow() + timedelta(seconds=e.new_token_info['expires_in'])
                        db.session.commit()
                        
                        logger.info(f"Токен обновлен для пользователя {playlist.user.username}, повторяем проверку плейлиста")
                        
                        try:
                            current_tracks = service.get_playlist_tracks(e.new_token_info['access_token'], playlist.service_playlist_id)
                            self._sync_playlist_tracks(playlist, current_tracks)
                            logger.info("Плейлист %s проверен после обновления токена", playlist.name)
                            return
                        except SpotifyReauthorizationRequired:
                            self._discard_spotify_token(playlist.user)
                            raise
                        except Exception as retry_e:
                            logger.error(f"Ошибка при повторной проверке плейлиста {playlist.name} после обновления токена: {str(retry_e)}")
                            raise
                
                logger.error(f"Ошибка при проверке плейлиста {playlist.name}: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Ошибка при проверке плейлиста {playlist.name}: {str(e)}")
                raise
    
    def _discard_spotify_token(self, user):
        """Delete stored Spotify tokens. Do not retry a failed refresh."""
        token_records = list(user.spotify_tokens) if user.spotify_tokens else []
        if not token_records:
            return
        
        for token_record in token_records:
            db.session.delete(token_record)
        db.session.commit()
        db.session.expire(user, ['spotify_tokens'])
        user._spotify_reauth_required = True
        logger.warning(
            f"Discarded Spotify token for {user.username} "
            "(invalid_grant / expired refresh token); will not retry"
        )
        try:
            from services.notification_service import notification_service
            notification_service.send_reconnect_notification(user, 'Spotify')
        except Exception as notify_error:
            logger.error(
                f"Failed to notify {user.username} about Spotify reauthorization: {notify_error}"
            )
    
    def _apply_spotify_token_refresh(self, user, error):
        """Persist a successfully refreshed Spotify token and return the new pair."""
        if not error.new_token_info:
            raise error
        token_record = user.spotify_tokens[0] if user.spotify_tokens else None
        if not token_record:
            raise error
        token_record.access_token = error.new_token_info['access_token']
        if 'refresh_token' in error.new_token_info:
            token_record.refresh_token = error.new_token_info['refresh_token']
        token_record.expires_at = datetime.utcnow() + timedelta(
            seconds=error.new_token_info['expires_in']
        )
        db.session.commit()
        logger.info(f"Токен Spotify для пользователя {user.username} успешно обновлен")
        return token_record.access_token, token_record.refresh_token
    
    def _get_user_token(self, user, service_name):
        """Получить токен доступа пользователя для сервиса"""
        if service_name == 'spotify':
            if getattr(user, '_spotify_reauth_required', False) is True:
                raise SpotifyReauthorizationRequired(
                    'Spotify refresh token expired. Please sign in again.'
                )
            token_record = user.spotify_tokens[0] if user.spotify_tokens else None
            if token_record:
                # Проверяем, не истек ли токен
                if token_record.expires_at > datetime.utcnow():
                    return token_record.access_token
                else:
                    # Токен истек, пытаемся обновить
                    try:
                        service = self.services['spotify']
                        new_token_info = service.refresh_access_token(token_record.refresh_token)
                        
                        # Обновляем токен в базе данных
                        token_record.access_token = new_token_info['access_token']
                        if 'refresh_token' in new_token_info:
                            token_record.refresh_token = new_token_info['refresh_token']
                        token_record.expires_at = datetime.utcnow() + timedelta(seconds=new_token_info['expires_in'])
                        db.session.commit()
                        
                        logger.info(f"Токен Spotify для пользователя {user.username} успешно обновлен")
                        return token_record.access_token
                    except SpotifyReauthorizationRequired:
                        self._discard_spotify_token(user)
                        raise
                    except Exception as e:
                        logger.error(f"Ошибка обновления токена Spotify для пользователя {user.username}: {str(e)}")
                        return None
        elif service_name == 'deezer':
            token_record = user.deezer_tokens[0] if user.deezer_tokens else None
            if token_record and token_record.expires_at > datetime.utcnow():
                return token_record.access_token
        elif service_name == 'apple_music':
            token_record = user.apple_music_tokens[0] if user.apple_music_tokens else None
            if token_record:
                # Проверяем, не истек ли токен
                if token_record.expires_at > datetime.utcnow():
                    return token_record.access_token
                else:
                    # Токен истек - удаляем его
                    logger.warning(
                        f"Токен Apple Music для пользователя {user.username} истек"
                    )
                    db.session.delete(token_record)
                    db.session.commit()
                    return None
        elif service_name == 'yandex_music':
            token_record = user.yandex_music_tokens[0] if user.yandex_music_tokens else None
            if token_record and token_record.expires_at > datetime.utcnow():
                return token_record.access_token
        
        return None
    
    def _record_check_failure(self, playlist_id, error):
        detail = ' '.join(str(error).split())[:240]
        try:
            db.session.rollback()
        except Exception:
            logger.exception('Не удалось откатить сессию после ошибки проверки')
        playlist = db.session.get(Playlist, playlist_id)
        if playlist is None:
            return
        playlist.last_check_error = detail or 'Ошибка проверки'
        playlist.last_check_failed_at = datetime.utcnow()
        db.session.commit()

    def _sync_playlist_tracks(self, playlist, current_tracks):
        if self.app:
            with self.app.app_context():
                self._sync_playlist_tracks_impl(playlist, current_tracks)
        else:
            self._sync_playlist_tracks_impl(playlist, current_tracks)

    def _sync_playlist_tracks_impl(self, playlist, current_tracks):
        current_by_id = {}
        for track in current_tracks:
            track_id = track.get('id')
            if track_id is None or track_id == '':
                continue
            current_by_id[str(track_id)] = track

        stored = Track.query.filter_by(playlist_id=playlist.id).all()
        by_service_id = {}
        for track in stored:
            by_service_id.setdefault(str(track.service_track_id), track)

        removed_payloads = []
        added_payloads = []
        for service_id, track_data in current_by_id.items():
            existing = by_service_id.get(service_id)
            if existing is None:
                existing = Track(
                    playlist_id=playlist.id,
                    service_track_id=service_id,
                    name=track_data.get('name') or '',
                    artist=track_data.get('artist') or '',
                    album=track_data.get('album') or '',
                    duration=track_data.get('duration') or 0,
                    added_at=datetime.utcnow(),
                    is_removed=False,
                )
                db.session.add(existing)
                db.session.flush()
                added_payloads.append(self._change_payload(existing, playlist, added=True))
                continue
            if existing.is_removed:
                existing.is_removed = False
                existing.removed_at = None
                existing.name = track_data.get('name') or existing.name
                existing.artist = track_data.get('artist') or existing.artist
                existing.album = track_data.get('album') or existing.album
                if track_data.get('duration'):
                    existing.duration = track_data.get('duration')
                existing.added_at = datetime.utcnow()
                added_payloads.append(self._change_payload(existing, playlist, added=True))

        for service_id, existing in by_service_id.items():
            if existing.is_removed or service_id in current_by_id:
                continue
            existing.is_removed = True
            existing.removed_at = datetime.utcnow()
            removed_payloads.append(self._change_payload(existing, playlist, added=False))

        for payload in removed_payloads + added_payloads:
            db.session.add(Notification(
                user_id=playlist.user_id,
                playlist_id=playlist.id,
                track_id=payload['track_db_id'],
                message=payload['message'],
            ))

        playlist.last_checked = datetime.utcnow()
        playlist.last_check_error = None
        playlist.last_check_failed_at = None
        owner_id = playlist.user_id
        playlist_name = playlist.name
        playlist_id = playlist.id
        db.session.commit()

        owner = db.session.get(User, owner_id)
        if owner is None:
            return
        self._send_change_batch(owner, removed_payloads, playlist_name, playlist_id, 'track_removed')
        self._send_change_batch(owner, added_payloads, playlist_name, playlist_id, 'track_added')

    def _change_payload(self, track, playlist, added):
        if added:
            message = (
                f"Трек '{track.name}' от {track.artist} добавлен в плейлист '{playlist.name}'"
            )
        else:
            message = (
                f"Трек '{track.name}' от {track.artist} был удален из плейлиста '{playlist.name}'"
            )
        return {
            'track_db_id': track.id,
            'track_service_id': track.service_track_id,
            'track_name': track.name,
            'artist_name': track.artist,
            'message': message,
        }

    def _send_change_batch(self, owner, payloads, playlist_name, playlist_id, notification_type):
        if not payloads:
            return
        try:
            notification_service.send_batch_notifications(
                user=owner,
                tracks_data=payloads,
                playlist_name=playlist_name,
                playlist_id=playlist_id,
                notification_type=notification_type,
            )
        except Exception:
            logger.exception('Ошибка отправки сводного уведомления')

    def add_playlist(self, user, service, playlist_url):
        """Добавить новый плейлист для мониторинга"""
        # Убеждаемся, что работаем в контексте приложения
        if self.app:
            with self.app.app_context():
                return self._add_playlist_impl(user, service, playlist_url)
        else:
            return self._add_playlist_impl(user, service, playlist_url)
    
    def _add_playlist_impl(self, user, service, playlist_url):
        """Внутренняя реализация добавления плейлиста"""
        service_obj = self.services.get(service)
        if not service_obj:
            raise ValueError(f"Неподдерживаемый сервис: {service}")
        
        # Для публичных плейлистов Яндекс.Музыки, Deezer и Apple Music не нужен токен
        if service == 'deezer':
            try:
                # Получаем информацию о плейлисте Deezer через RapidAPI
                playlist_info = service_obj.get_public_playlist_info(playlist_url)
                
                # Проверяем, не добавлен ли уже этот плейлист
                existing_playlist = Playlist.query.filter_by(
                    user_id=user.id,
                    service=service,
                    service_playlist_id=playlist_info['id']
                ).first()
                
                if existing_playlist:
                    raise ValueError("Этот плейлист уже добавлен для мониторинга")
                
                # Создаем плейлист в базе данных
                playlist = Playlist(
                    user_id=user.id,
                    service=service,
                    service_playlist_id=playlist_info['id'],
                    name=playlist_info['name'],
                    description=playlist_info.get('description', ''),
                    last_checked=datetime.utcnow()
                )
                db.session.add(playlist)
                db.session.flush()  # Получаем ID плейлиста
                
                # Получаем и сохраняем треки плейлиста Deezer
                tracks_data = service_obj.get_public_playlist_tracks(playlist_url)
                for track_data in tracks_data:
                    track = Track(
                        playlist_id=playlist.id,
                        service_track_id=track_data['id'],
                        name=track_data['name'],
                        artist=track_data['artist'],
                        album=track_data.get('album', ''),
                        duration=track_data.get('duration', 0),
                        added_at=datetime.utcnow()
                    )
                    db.session.add(track)
                
                db.session.commit()
                logger.info(f"Плейлист Deezer {playlist.name} добавлен для пользователя {user.username}")
                
                return playlist
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении плейлиста Deezer: {str(e)}")
                raise
        elif service == 'apple_music' and ('music.apple.com' in playlist_url or 'playlist' in playlist_url):
            try:
                # Проверяем, есть ли User Token (для приватных плейлистов)
                user_token = self._get_user_token(user, 'apple_music')
                
                # Получаем информацию о плейлисте (публичном или приватном)
                if user_token:
                    playlist_info = service_obj.get_playlist_info(
                        playlist_url,
                        user_token=user_token
                    )
                else:
                    playlist_info = service_obj.get_public_playlist_info(playlist_url)
                
                # Проверяем, не добавлен ли уже этот плейлист
                existing_playlist = Playlist.query.filter_by(
                    user_id=user.id,
                    service=service,
                    service_playlist_id=playlist_info['id']
                ).first()
                
                if existing_playlist:
                    raise ValueError("Этот плейлист уже добавлен для мониторинга")
                
                # Создаем плейлист в базе данных
                playlist = Playlist(
                    user_id=user.id,
                    service=service,
                    service_playlist_id=playlist_info['id'],
                    name=playlist_info['name'],
                    description=playlist_info.get('description', ''),
                    last_checked=datetime.utcnow()
                )
                db.session.add(playlist)
                db.session.flush()  # Получаем ID плейлиста
                
                # Получаем и сохраняем треки плейлиста
                if user_token:
                    tracks_data = service_obj.get_playlist_tracks(
                        playlist_info['id'],
                        user_token=user_token
                    )
                else:
                    tracks_data = service_obj.get_public_playlist_tracks(playlist_url)
                for track_data in tracks_data:
                    track = Track(
                        playlist_id=playlist.id,
                        service_track_id=track_data['id'],
                        name=track_data['name'],
                        artist=track_data['artist'],
                        album=track_data.get('album', ''),
                        duration=track_data.get('duration', 0),
                        added_at=datetime.utcnow()
                    )
                    db.session.add(track)
                
                db.session.commit()
                logger.info(f"Плейлист Apple Music {playlist.name} добавлен для пользователя {user.username}")
                
                return playlist
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении плейлиста Apple Music: {str(e)}")
                raise
        elif service == 'yandex_music':
            try:
                # Получаем информацию о публичном плейлисте
                playlist_info = service_obj.get_public_playlist_info(playlist_url)
                
                # Проверяем, не добавлен ли уже этот плейлист
                existing_playlist = Playlist.query.filter_by(
                    user_id=user.id,
                    service=service,
                    service_playlist_id=playlist_info['id']
                ).first()
                
                if existing_playlist:
                    raise ValueError("Этот плейлист уже добавлен для мониторинга")
                
                # Создаем плейлист в базе данных
                playlist = Playlist(
                    user_id=user.id,
                    service=service,
                    service_playlist_id=playlist_info['id'],
                    name=playlist_info['name'],
                    description=playlist_info.get('description', ''),
                    last_checked=datetime.utcnow()
                )
                db.session.add(playlist)
                db.session.flush()  # Получаем ID плейлиста
                
                tracks_data = service_obj.get_playlist_tracks_by_id(playlist_info['id'])
                for track_data in tracks_data:
                    track = Track(
                        playlist_id=playlist.id,
                        service_track_id=track_data['id'],
                        name=track_data['name'],
                        artist=track_data['artist'],
                        album=track_data.get('album', ''),
                        duration=track_data.get('duration', 0),
                        added_at=datetime.utcnow()
                    )
                    db.session.add(track)
                
                db.session.commit()
                logger.info(f"Публичный плейлист {playlist.name} добавлен для пользователя {user.username}")
                
                return playlist
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении публичного плейлиста: {str(e)}")
                raise
        else:
            # Получаем токен доступа
            access_token = self._get_user_token(user, service)
            if not access_token:
                raise ValueError(f"Нет токена доступа для {service}")
            
            # Получаем refresh_token для Spotify
            refresh_token = None
            if service == 'spotify':
                token_record = user.spotify_tokens[0] if user.spotify_tokens else None
                if token_record:
                    refresh_token = token_record.refresh_token
            
            try:
                if service == 'spotify':
                    playlist_info = service_obj.get_playlist_info(
                        access_token, playlist_url, refresh_token
                    )
                else:
                    playlist_info = service_obj.get_playlist_info(
                        access_token, playlist_url
                    )
            except TokenExpiredError as e:
                access_token, refresh_token = self._apply_spotify_token_refresh(user, e)
                playlist_info = service_obj.get_playlist_info(access_token, playlist_url)
            except SpotifyReauthorizationRequired:
                self._discard_spotify_token(user)
                raise
            
            # Проверяем, не добавлен ли уже этот плейлист
            existing_playlist = Playlist.query.filter_by(
                user_id=user.id,
                service=service,
                service_playlist_id=playlist_info['id']
            ).first()
            
            if existing_playlist:
                raise ValueError("Этот плейлист уже добавлен для мониторинга")
            
            # Создаем плейлист в базе данных
            playlist = Playlist(
                user_id=user.id,
                service=service,
                service_playlist_id=playlist_info['id'],
                name=playlist_info['name'],
                description=playlist_info.get('description', ''),
                last_checked=datetime.utcnow()
            )
            db.session.add(playlist)
            db.session.flush()  # Получаем ID плейлиста
            
            try:
                if service == 'spotify':
                    tracks_data = service_obj.get_playlist_tracks(
                        access_token, playlist_info['id'], refresh_token
                    )
                else:
                    tracks_data = service_obj.get_playlist_tracks(
                        access_token, playlist_info['id']
                    )
            except TokenExpiredError as e:
                access_token, refresh_token = self._apply_spotify_token_refresh(user, e)
                tracks_data = service_obj.get_playlist_tracks(
                    access_token, playlist_info['id']
                )
            except SpotifyReauthorizationRequired:
                db.session.rollback()
                self._discard_spotify_token(user)
                raise
            for track_data in tracks_data:
                track = Track(
                    playlist_id=playlist.id,
                    service_track_id=track_data['id'],
                    name=track_data['name'],
                    artist=track_data['artist'],
                    album=track_data.get('album', ''),
                    duration=track_data.get('duration', 0),
                    added_at=datetime.utcnow()
                )
                db.session.add(track)
            
            db.session.commit()
            logger.info(f"Плейлист {playlist.name} добавлен для пользователя {user.username}")
            
            return playlist
