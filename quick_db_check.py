#!/usr/bin/env python3
"""
Быстрая проверка базы данных без сложных импортов
"""

import sqlite3
import os
from datetime import datetime

def check_db_quick():
    """Быстрая проверка базы данных через SQLite"""
    db_path = os.path.join('instance', 'playlistchecker.db')
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=" * 50)
        print("БЫСТРАЯ ПРОВЕРКА БАЗЫ ДАННЫХ")
        print("=" * 50)
        
        # Пользователи
        cursor.execute("SELECT COUNT(*) FROM user")
        users_count = cursor.fetchone()[0]
        print(f"👥 Пользователей: {users_count}")
        
        if users_count > 0:
            cursor.execute("SELECT username, email, created_at FROM user ORDER BY created_at DESC LIMIT 5")
            users = cursor.fetchall()
            print("   Последние пользователи:")
            for user in users:
                print(f"   - {user[0]} ({user[1]}) - {user[2]}")
        
        print()
        
        # Плейлисты
        cursor.execute("SELECT COUNT(*) FROM playlist")
        playlists_count = cursor.fetchone()[0]
        print(f"🎵 Плейлистов: {playlists_count}")
        
        if playlists_count > 0:
            # По сервисам
            cursor.execute("SELECT service, COUNT(*) FROM playlist GROUP BY service")
            services = cursor.fetchall()
            for service, count in services:
                print(f"   - {service}: {count}")
            
            cursor.execute("SELECT name, service, created_at FROM playlist ORDER BY created_at DESC LIMIT 5")
            playlists = cursor.fetchall()
            print("   Последние плейлисты:")
            for playlist in playlists:
                print(f"   - {playlist[0]} ({playlist[1]}) - {playlist[2]}")
        
        print()
        
        # Треки
        cursor.execute("SELECT COUNT(*) FROM track")
        tracks_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM track WHERE is_removed = 0")
        active_tracks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM track WHERE is_removed = 1")
        removed_tracks = cursor.fetchone()[0]
        
        print(f"🎶 Треков: {tracks_count}")
        print(f"   - Активных: {active_tracks}")
        print(f"   - Удаленных: {removed_tracks}")
        
        if tracks_count > 0:
            cursor.execute("SELECT name, artist, added_at, is_removed FROM track ORDER BY added_at DESC LIMIT 5")
            tracks = cursor.fetchall()
            print("   Последние треки:")
            for track in tracks:
                status = "❌" if track[3] else "✅"
                print(f"   {status} {track[0]} - {track[1]} ({track[2]})")
        
        print()
        
        # Уведомления
        cursor.execute("SELECT COUNT(*) FROM notification")
        notifications_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM notification WHERE is_read = 0")
        unread_notifications = cursor.fetchone()[0]
        
        print(f"🔔 Уведомлений: {notifications_count}")
        print(f"   - Непрочитанных: {unread_notifications}")
        
        if notifications_count > 0:
            cursor.execute("SELECT message, created_at, is_read FROM notification ORDER BY created_at DESC LIMIT 5")
            notifications = cursor.fetchall()
            print("   Последние уведомления:")
            for notif in notifications:
                status = "🔴" if not notif[2] else "🟢"
                print(f"   {status} {notif[0][:50]}... ({notif[1]})")
        
        print()
        
        # Токены
        cursor.execute("SELECT COUNT(*) FROM spotify_token")
        spotify_tokens = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM deezer_token")
        deezer_tokens = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM apple_music_token")
        apple_tokens = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM yandex_music_token")
        yandex_tokens = cursor.fetchone()[0]
        
        print(f"🔑 Токены доступа:")
        print(f"   - Spotify: {spotify_tokens}")
        print(f"   - Deezer: {deezer_tokens}")
        print(f"   - Apple Music: {apple_tokens}")
        print(f"   - Yandex Music: {yandex_tokens}")
        
        print()
        print("=" * 50)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")

if __name__ == '__main__':
    check_db_quick()
