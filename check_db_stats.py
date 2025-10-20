#!/usr/bin/env python3
"""
Скрипт для просмотра статистики базы данных PlaylistChecker
"""

import os
import sys
from datetime import datetime

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем после добавления пути
from app import app, db, User, Playlist, Track, Notification, SpotifyToken, DeezerToken, AppleMusicToken, YandexMusicToken

def show_database_stats():
    """Показать статистику базы данных"""
    with app.app_context():
        print("=" * 50)
        print("СТАТИСТИКА БАЗЫ ДАННЫХ PLAYLISTCHECKER")
        print("=" * 50)
        
        # Пользователи
        users_count = User.query.count()
        telegram_connected = User.query.filter(User.telegram_chat_id.isnot(None)).count()
        telegram_enabled = User.query.filter_by(telegram_notifications_enabled=True).count()
        
        print(f"👥 Пользователей: {users_count}")
        print(f"   📱 Telegram подключен: {telegram_connected}")
        print(f"   🔔 Telegram уведомления включены: {telegram_enabled}")
        
        if users_count > 0:
            print("   Последние пользователи:")
            recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
            for user in recent_users:
                tg_status = "📱" if user.telegram_chat_id else "❌"
                print(f"   - {user.username} ({user.email}) {tg_status} - {user.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        print()
        
        # Плейлисты
        playlists_count = Playlist.query.count()
        print(f"🎵 Плейлистов: {playlists_count}")
        
        if playlists_count > 0:
            # По сервисам
            spotify_playlists = Playlist.query.filter_by(service='spotify').count()
            deezer_playlists = Playlist.query.filter_by(service='deezer').count()
            apple_playlists = Playlist.query.filter_by(service='apple_music').count()
            yandex_playlists = Playlist.query.filter_by(service='yandex_music').count()
            
            print(f"   - Spotify: {spotify_playlists}")
            print(f"   - Deezer: {deezer_playlists}")
            print(f"   - Apple Music: {apple_playlists}")
            print(f"   - Yandex Music: {yandex_playlists}")
            
            print("   Последние плейлисты:")
            recent_playlists = Playlist.query.order_by(Playlist.created_at.desc()).limit(5).all()
            for playlist in recent_playlists:
                print(f"   - {playlist.name} ({playlist.service}) - {playlist.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        print()
        
        # Треки
        tracks_count = Track.query.count()
        active_tracks = Track.query.filter_by(is_removed=False).count()
        removed_tracks = Track.query.filter_by(is_removed=True).count()
        
        print(f"🎶 Треков: {tracks_count}")
        print(f"   - Активных: {active_tracks}")
        print(f"   - Удаленных: {removed_tracks}")
        
        if tracks_count > 0:
            print("   Последние треки:")
            recent_tracks = Track.query.order_by(Track.added_at.desc()).limit(5).all()
            for track in recent_tracks:
                status = "❌" if track.is_removed else "✅"
                print(f"   {status} {track.name} - {track.artist} ({track.added_at.strftime('%Y-%m-%d %H:%M')})")
        
        print()
        
        # Уведомления
        notifications_count = Notification.query.count()
        unread_notifications = Notification.query.filter_by(is_read=False).count()
        
        print(f"🔔 Уведомлений: {notifications_count}")
        print(f"   - Непрочитанных: {unread_notifications}")
        
        if notifications_count > 0:
            print("   Последние уведомления:")
            recent_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(5).all()
            for notif in recent_notifications:
                status = "🔴" if not notif.is_read else "🟢"
                print(f"   {status} {notif.message[:50]}... ({notif.created_at.strftime('%Y-%m-%d %H:%M')})")
        
        print()
        
        # Токены доступа
        spotify_tokens = SpotifyToken.query.count()
        deezer_tokens = DeezerToken.query.count()
        apple_tokens = AppleMusicToken.query.count()
        yandex_tokens = YandexMusicToken.query.count()
        
        print(f"🔑 Токены доступа:")
        print(f"   - Spotify: {spotify_tokens}")
        print(f"   - Deezer: {deezer_tokens}")
        print(f"   - Apple Music: {apple_tokens}")
        print(f"   - Yandex Music: {yandex_tokens}")
        
        print()
        print("=" * 50)

def show_user_details(user_id=None):
    """Показать детальную информацию о пользователе"""
    with app.app_context():
        if user_id:
            user = User.query.get(user_id)
            if not user:
                print(f"Пользователь с ID {user_id} не найден")
                return
            users = [user]
        else:
            users = User.query.all()
        
        for user in users:
            print(f"\n👤 ПОЛЬЗОВАТЕЛЬ: {user.username} (ID: {user.id})")
            print(f"   Email: {user.email}")
            print(f"   Зарегистрирован: {user.created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # Telegram интеграция
            print(f"   📱 Telegram:")
            if user.telegram_chat_id:
                print(f"      Chat ID: {user.telegram_chat_id}")
                print(f"      Username: {user.telegram_username or 'Не указан'}")
                print(f"      Уведомления: {'✅ Включены' if user.telegram_notifications_enabled else '❌ Отключены'}")
            else:
                print(f"      ❌ Не подключен")
            
            # Настройки уведомлений
            print(f"   🔔 Уведомления:")
            print(f"      Email: {'✅' if user.email_notifications_enabled else '❌'}")
            print(f"      Telegram: {'✅' if user.telegram_notifications_enabled else '❌'}")
            print(f"      Браузер: {'✅' if user.browser_notifications_enabled else '❌'}")
            
            # Плейлисты пользователя
            playlists = Playlist.query.filter_by(user_id=user.id).all()
            print(f"   Плейлистов: {len(playlists)}")
            
            for playlist in playlists:
                tracks_count = Track.query.filter_by(playlist_id=playlist.id).count()
                active_tracks = Track.query.filter_by(playlist_id=playlist.id, is_removed=False).count()
                print(f"     - {playlist.name} ({playlist.service}) - {active_tracks}/{tracks_count} треков")
            
            # Уведомления
            notifications = Notification.query.filter_by(user_id=user.id).all()
            unread = Notification.query.filter_by(user_id=user.id, is_read=False).count()
            print(f"   Уведомлений: {len(notifications)} (непрочитанных: {unread})")
            
            print("-" * 40)

if __name__ == '__main__':
    print("Выберите действие:")
    print("1. Показать общую статистику")
    print("2. Показать детали всех пользователей")
    print("3. Показать детали конкретного пользователя")
    
    choice = input("\nВведите номер (1-3): ").strip()
    
    if choice == '1':
        show_database_stats()
    elif choice == '2':
        show_user_details()
    elif choice == '3':
        user_id = input("Введите ID пользователя: ").strip()
        try:
            show_user_details(int(user_id))
        except ValueError:
            print("Неверный ID пользователя")
    else:
        print("Неверный выбор")
