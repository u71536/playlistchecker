#!/usr/bin/env python3
"""
Скрипт для тестирования API сервисов
"""

import os
from dotenv import load_dotenv
from services.spotify_service import SpotifyService
from services.deezer_service import DeezerService
from services.apple_music_service import AppleMusicService
from services.yandex_music_service import YandexMusicService

# Загружаем переменные окружения
load_dotenv()

def test_spotify():
    """Тестирование Spotify API"""
    print("=== Тестирование Spotify API ===")
    
    service = SpotifyService()
    
    # Проверяем настройки
    if not service.client_id or not service.client_secret:
        print("❌ Spotify API не настроен (отсутствуют CLIENT_ID или CLIENT_SECRET)")
        return
    
    print("✅ Spotify API настроен")
    print(f"Auth URL: {service.get_auth_url()}")
    print()

def test_deezer():
    """Тестирование Deezer API"""
    print("=== Тестирование Deezer API ===")
    
    service = DeezerService()
    
    # Проверяем настройки
    if not service.app_id or not service.app_secret:
        print("❌ Deezer API не настроен (отсутствуют APP_ID или APP_SECRET)")
        return
    
    print("✅ Deezer API настроен")
    print(f"Auth URL: {service.get_auth_url()}")
    print()

def test_apple_music():
    """Тестирование Apple Music API"""
    print("=== Тестирование Apple Music API ===")
    
    service = AppleMusicService()
    
    # Проверяем настройки
    if not all([service.team_id, service.key_id, service.private_key]):
        print("❌ Apple Music API не настроен (отсутствуют учетные данные)")
        return
    
    try:
        token = service.get_developer_token()
        print("✅ Apple Music API настроен")
        print(f"Developer Token: {token[:20]}...")
    except Exception as e:
        print(f"❌ Ошибка получения developer token: {e}")
    print()

def test_yandex_music():
    """Тестирование Yandex Music API"""
    print("=== Тестирование Yandex Music API ===")
    
    service = YandexMusicService()
    
    # Проверяем настройки
    if not service.client_id or not service.client_secret:
        print("❌ Yandex Music API не настроен (отсутствуют CLIENT_ID или CLIENT_SECRET)")
        return
    
    print("✅ Yandex Music API настроен")
    print(f"Auth URL: {service.get_auth_url()}")
    print()

def main():
    """Основная функция тестирования"""
    print("Тестирование API сервисов PlaylistChecker")
    print("=" * 50)
    print()
    
    test_spotify()
    test_deezer()
    test_apple_music()
    test_yandex_music()
    
    print("Тестирование завершено!")
    print()
    print("Для полного тестирования необходимо:")
    print("1. Настроить все API ключи в .env файле")
    print("2. Запустить приложение: python run.py")
    print("3. Открыть http://localhost:5000 в браузере")

if __name__ == '__main__':
    main()
