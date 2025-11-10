from datetime import datetime, timedelta
from services.spotify_service import SpotifyService
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
            except Exception as e:
                logger.error(f"Ошибка при проверке плейлистов пользователя {user.username}: {str(e)}")
        
        logger.info("Проверка всех плейлистов завершена")
    
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
        for playlist in playlists:
            try:
                self.check_playlist(playlist)
            except Exception as e:
                logger.error(f"Ошибка при проверке плейлиста {playlist.name}: {str(e)}")
    
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
        
        # Для публичных плейлистов Яндекс.Музыки и Deezer не нужен токен
        if playlist.service == 'deezer':
            try:
                # Получаем треки плейлиста Deezer через RapidAPI
                playlist_url = f"https://www.deezer.com/playlist/{playlist.service_playlist_id}"
                current_tracks = service.get_public_playlist_tracks(playlist_url)
                current_track_ids = {track['id'] for track in current_tracks}
                
                # Получаем треки из базы данных
                db_tracks = Track.query.filter_by(playlist_id=playlist.id, is_removed=False).all()
                db_track_ids = {track.service_track_id for track in db_tracks}
                
                # Находим удаленные треки
                removed_track_ids = db_track_ids - current_track_ids
                if removed_track_ids:
                    self._handle_removed_tracks(playlist, removed_track_ids)
                
                # Находим новые треки
                new_track_ids = current_track_ids - db_track_ids
                if new_track_ids:
                    self._handle_new_tracks(playlist, current_tracks, new_track_ids)
                
                # Обновляем время последней проверки
                playlist.last_checked = datetime.utcnow()
                try:
                    db.session.commit()
                    logger.info(f"Время последней проверки плейлиста Deezer {playlist.name} обновлено")
                except Exception as e:
                    logger.error(f"Ошибка при обновлении времени проверки плейлиста Deezer {playlist.name}: {str(e)}")
                    db.session.rollback()
                    raise
                
                logger.info(f"Плейлист Deezer {playlist.name} проверен. Удалено: {len(removed_track_ids)}, добавлено: {len(new_track_ids)}")
                
            except Exception as e:
                logger.error(f"Ошибка при проверке плейлиста Deezer {playlist.name}: {str(e)}")
                raise
        elif playlist.service == 'yandex_music' and hasattr(playlist, 'is_public') and playlist.is_public:
            try:
                # Получаем треки публичного плейлиста
                playlist_url = f"https://music.yandex.ru/playlists/{playlist.service_playlist_id}"
                current_tracks = service.get_public_playlist_tracks(playlist_url)
                current_track_ids = {track['id'] for track in current_tracks}
                
                # Получаем треки из базы данных
                db_tracks = Track.query.filter_by(playlist_id=playlist.id, is_removed=False).all()
                db_track_ids = {track.service_track_id for track in db_tracks}
                
                # Находим удаленные треки
                removed_track_ids = db_track_ids - current_track_ids
                if removed_track_ids:
                    self._handle_removed_tracks(playlist, removed_track_ids)
                
                # Находим новые треки
                new_track_ids = current_track_ids - db_track_ids
                if new_track_ids:
                    self._handle_new_tracks(playlist, current_tracks, new_track_ids)
                
                # Обновляем время последней проверки
                playlist.last_checked = datetime.utcnow()
                try:
                    db.session.commit()
                    logger.info(f"Время последней проверки публичного плейлиста {playlist.name} обновлено")
                except Exception as e:
                    logger.error(f"Ошибка при обновлении времени проверки публичного плейлиста {playlist.name}: {str(e)}")
                    db.session.rollback()
                    raise
                
                logger.info(f"Публичный плейлист {playlist.name} проверен. Удалено: {len(removed_track_ids)}, добавлено: {len(new_track_ids)}")
                
            except Exception as e:
                logger.error(f"Ошибка при проверке публичного плейлиста {playlist.name}: {str(e)}")
                raise
        else:
            # Получаем токен доступа для сервиса
            access_token = self._get_user_token(playlist.user, playlist.service)
            if not access_token:
                logger.warning(f"Нет токена доступа для {playlist.service} у пользователя {playlist.user.username}")
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
                current_track_ids = {track['id'] for track in current_tracks}
                
                # Получаем треки из базы данных
                db_tracks = Track.query.filter_by(playlist_id=playlist.id, is_removed=False).all()
                db_track_ids = {track.service_track_id for track in db_tracks}
                
                # Находим удаленные треки
                removed_track_ids = db_track_ids - current_track_ids
                if removed_track_ids:
                    self._handle_removed_tracks(playlist, removed_track_ids)
                
                # Находим новые треки
                new_track_ids = current_track_ids - db_track_ids
                if new_track_ids:
                    self._handle_new_tracks(playlist, current_tracks, new_track_ids)
                
                # Обновляем время последней проверки
                playlist.last_checked = datetime.utcnow()
                try:
                    db.session.commit()
                    logger.info(f"Время последней проверки плейлиста {playlist.name} обновлено")
                except Exception as e:
                    logger.error(f"Ошибка при обновлении времени проверки плейлиста {playlist.name}: {str(e)}")
                    db.session.rollback()
                    raise
                
                logger.info(f"Плейлист {playlist.name} проверен. Удалено: {len(removed_track_ids)}, добавлено: {len(new_track_ids)}")
                
            except Exception as e:
                # Импортируем TokenExpiredError локально, чтобы избежать циклических импортов
                from services.spotify_service import TokenExpiredError
                
                if isinstance(e, TokenExpiredError) and e.new_token_info:
                    # Обновляем токен в базе данных
                    if playlist.service == 'spotify':
                        token_record = playlist.user.spotify_tokens[0] if playlist.user.spotify_tokens else None
                        if token_record:
                            token_record.access_token = e.new_token_info['access_token']
                            if 'refresh_token' in e.new_token_info:
                                token_record.refresh_token = e.new_token_info['refresh_token']
                            token_record.expires_at = datetime.utcnow() + timedelta(seconds=e.new_token_info['expires_in'])
                            db.session.commit()
                            
                            logger.info(f"Токен обновлен для пользователя {playlist.user.username}, повторяем проверку плейлиста")
                            
                            # Повторяем проверку с новым токеном
                            try:
                                current_tracks = service.get_playlist_tracks(e.new_token_info['access_token'], playlist.service_playlist_id)
                                current_track_ids = {track['id'] for track in current_tracks}
                                
                                # Получаем треки из базы данных
                                db_tracks = Track.query.filter_by(playlist_id=playlist.id, is_removed=False).all()
                                db_track_ids = {track.service_track_id for track in db_tracks}
                                
                                # Находим удаленные треки
                                removed_track_ids = db_track_ids - current_track_ids
                                if removed_track_ids:
                                    self._handle_removed_tracks(playlist, removed_track_ids)
                                
                                # Находим новые треки
                                new_track_ids = current_track_ids - db_track_ids
                                if new_track_ids:
                                    self._handle_new_tracks(playlist, current_tracks, new_track_ids)
                                
                                # Обновляем время последней проверки
                                playlist.last_checked = datetime.utcnow()
                                try:
                                    db.session.commit()
                                    logger.info(f"Время последней проверки плейлиста {playlist.name} обновлено после обновления токена")
                                except Exception as e:
                                    logger.error(f"Ошибка при обновлении времени проверки плейлиста {playlist.name} после обновления токена: {str(e)}")
                                    db.session.rollback()
                                    raise
                                
                                logger.info(f"Плейлист {playlist.name} проверен после обновления токена. Удалено: {len(removed_track_ids)}, добавлено: {len(new_track_ids)}")
                                return
                            except Exception as retry_e:
                                logger.error(f"Ошибка при повторной проверке плейлиста {playlist.name} после обновления токена: {str(retry_e)}")
                                raise
                
                logger.error(f"Ошибка при проверке плейлиста {playlist.name}: {str(e)}")
                raise
    
    def _get_user_token(self, user, service_name):
        """Получить токен доступа пользователя для сервиса"""
        if service_name == 'spotify':
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
                    except Exception as e:
                        logger.error(f"Ошибка обновления токена Spotify для пользователя {user.username}: {str(e)}")
                        return None
        elif service_name == 'deezer':
            token_record = user.deezer_tokens[0] if user.deezer_tokens else None
            if token_record and token_record.expires_at > datetime.utcnow():
                return token_record.access_token
        elif service_name == 'apple_music':
            token_record = user.apple_music_tokens[0] if user.apple_music_tokens else None
            if token_record and token_record.expires_at > datetime.utcnow():
                return token_record.access_token
        elif service_name == 'yandex_music':
            token_record = user.yandex_music_tokens[0] if user.yandex_music_tokens else None
            if token_record and token_record.expires_at > datetime.utcnow():
                return token_record.access_token
        
        return None
    
    def _handle_removed_tracks(self, playlist, removed_track_ids):
        """Обработать удаленные треки"""
        if self.app:
            with self.app.app_context():
                self._handle_removed_tracks_impl(playlist, removed_track_ids)
        else:
            self._handle_removed_tracks_impl(playlist, removed_track_ids)
    
    def _handle_removed_tracks_impl(self, playlist, removed_track_ids):
        """Внутренняя реализация обработки удаленных треков"""
        try:
            for track_id in removed_track_ids:
                track = Track.query.filter_by(
                    playlist_id=playlist.id,
                    service_track_id=track_id,
                    is_removed=False
                ).first()
                
                if track:
                    logger.info(f"Найден трек для удаления: {track.name} (ID: {track.id})")
                    
                    # Отмечаем трек как удаленный
                    track.is_removed = True
                    track.removed_at = datetime.utcnow()
                    
                    # Создаем уведомление
                    notification = Notification(
                        user_id=playlist.user_id,
                        playlist_id=playlist.id,
                        track_id=track.id,
                        message=f"Трек '{track.name}' от {track.artist} был удален из плейлиста '{playlist.name}'"
                    )
                    db.session.add(notification)
                    
                    # Отправляем уведомления по всем каналам
                    try:
                        from services.notification_service import notification_service
                        
                        notification_data = {
                            'type': 'track_removed',
                            'message': f"Трек '{track.name}' от {track.artist} был удален из плейлиста '{playlist.name}'",
                            'track_service_id': track.service_track_id,
                            'track_name': track.name,
                            'artist_name': track.artist,
                            'playlist_name': playlist.name,
                            'playlist_id': playlist.id
                        }
                        
                        notification_service.send_all_notifications(playlist.user, notification_data)
                        logger.info(f"Уведомления отправлены для пользователя {playlist.user.username}")
                        
                    except Exception as notification_error:
                        logger.error(f"Ошибка отправки уведомлений: {str(notification_error)}")
                    
                    logger.info(f"Трек {track.name} отмечен как удаленный из плейлиста {playlist.name}")
                    
                    # Принудительно сохраняем изменения для каждого трека
                    try:
                        db.session.commit()
                        logger.info(f"Изменения для трека {track.name} успешно сохранены в БД")
                    except Exception as commit_error:
                        logger.error(f"Ошибка при сохранении трека {track.name}: {str(commit_error)}")
                        db.session.rollback()
                        raise
                else:
                    logger.warning(f"Трек с ID {track_id} не найден в плейлисте {playlist.name}")
        except Exception as e:
            logger.error(f"Ошибка в _handle_removed_tracks_impl: {str(e)}")
            db.session.rollback()
            raise
    
    def _handle_new_tracks(self, playlist, current_tracks, new_track_ids):
        """Обработать новые треки"""
        if self.app:
            with self.app.app_context():
                self._handle_new_tracks_impl(playlist, current_tracks, new_track_ids)
        else:
            self._handle_new_tracks_impl(playlist, current_tracks, new_track_ids)
    
    def _handle_new_tracks_impl(self, playlist, current_tracks, new_track_ids):
        """Внутренняя реализация обработки новых треков"""
        try:
            for track_data in current_tracks:
                if track_data['id'] in new_track_ids:
                    # Проверяем, не существует ли уже трек с таким service_track_id
                    # (может быть добавлен при создании плейлиста или в другой транзакции)
                    existing_track = Track.query.filter_by(
                        playlist_id=playlist.id,
                        service_track_id=track_data['id'],
                        is_removed=False
                    ).first()
                    
                    if existing_track:
                        logger.info(f"Трек {track_data['name']} уже существует в плейлисте {playlist.name}, пропускаем")
                        continue
                    
                    # Проверяем, не было ли уже отправлено уведомление для этого трека
                    from services.notification_service import notification_service
                    if notification_service.check_notification_already_sent(
                        playlist.user_id, 
                        playlist.id, 
                        track_data['id'], 
                        'track_added'
                    ):
                        logger.info(f"Уведомление для трека {track_data['name']} уже было отправлено, пропускаем")
                        continue
                    
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
                    db.session.flush()  # Получаем ID трека
                    
                    # Создаем уведомление в базе данных
                    notification = Notification(
                        user_id=playlist.user_id,
                        playlist_id=playlist.id,
                        track_id=track.id,
                        message=f"Новый трек '{track.name}' от {track.artist} добавлен в плейлист '{playlist.name}'"
                    )
                    db.session.add(notification)
                    
                    # Отправляем уведомления по всем каналам
                    try:
                        notification_data = {
                            'type': 'track_added',
                            'message': f"Новый трек '{track.name}' от {track.artist} добавлен в плейлист '{playlist.name}'",
                            'track_service_id': track.service_track_id,
                            'track_name': track.name,
                            'artist_name': track.artist,
                            'playlist_name': playlist.name,
                            'playlist_id': playlist.id
                        }
                        
                        notification_service.send_all_notifications(playlist.user, notification_data)
                        logger.info(f"Уведомления о новом треке отправлены для пользователя {playlist.user.username}")
                        
                    except Exception as notification_error:
                        logger.error(f"Ошибка отправки уведомлений о новом треке: {str(notification_error)}")
                    
                    logger.info(f"Добавлен новый трек {track.name} в плейлист {playlist.name}")
                    
                    # Принудительно сохраняем изменения для каждого трека
                    try:
                        db.session.commit()
                        logger.info(f"Новый трек {track.name} успешно сохранен в БД")
                    except Exception as commit_error:
                        logger.error(f"Ошибка при сохранении нового трека {track.name}: {str(commit_error)}")
                        db.session.rollback()
                        raise
        except Exception as e:
            logger.error(f"Ошибка в _handle_new_tracks_impl: {str(e)}")
            db.session.rollback()
            raise
    
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
        
        # Для публичных плейлистов Яндекс.Музыки и Deezer не нужен токен
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
        elif service == 'yandex_music' and 'music.yandex.ru/playlists/' in playlist_url:
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
                
                # Получаем и сохраняем треки публичного плейлиста
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
            
            # Получаем информацию о плейлисте
            if service == 'spotify':
                playlist_info = service_obj.get_playlist_info(access_token, playlist_url, refresh_token)
            else:
                playlist_info = service_obj.get_playlist_info(access_token, playlist_url)
            
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
            
            # Получаем и сохраняем треки
            if service == 'spotify':
                tracks_data = service_obj.get_playlist_tracks(access_token, playlist_info['id'], refresh_token)
            else:
                tracks_data = service_obj.get_playlist_tracks(access_token, playlist_info['id'])
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
