#!/usr/bin/env python3
"""
Скрипт для заполнения переводов страницы About
"""

import re

def fill_about_translations():
    """Заполнить переводы для страницы About"""
    
    # Словарь переводов для about.html
    about_translations = {
        # Основные тексты
        'PlaylistChecker — это инновационный веб-сервис, созданный для решения проблемы исчезающих песен из музыкальных плейлистов. Мы понимаем, как важно сохранить целостность ваших музыкальных коллекций, и предлагаем автоматизированное решение для мониторинга изменений.': 'PlaylistChecker is an innovative web service created to solve the problem of disappearing songs from music playlists. We understand how important it is to preserve the integrity of your music collections, and we offer an automated solution for monitoring changes.',
        
        'Наш сервис работает 24/7, отслеживая ваши плейлисты на популярных музыкальных платформах и уведомляя вас о любых изменениях в режиме реального времени. Больше не нужно вручную проверять каждый плейлист — мы сделаем это за вас!': 'Our service works 24/7, tracking your playlists on popular music platforms and notifying you of any changes in real time. No more need to manually check each playlist - we will do it for you!',
        
        # Причины исчезновения песен
        'Истечение лицензионных соглашений': 'License agreement expiration',
        'Изменения в политике платформ': 'Platform policy changes',
        'Проблемы с авторскими правами': 'Copyright issues',
        'Технические сбои сервисов': 'Service technical failures',
        'Региональные ограничения': 'Regional restrictions',
        
        # Последствия для пользователей
        'Последствия для пользователей': 'Consequences for users',
        'Потеря любимых композиций': 'Loss of favorite songs',
        'Нарушение целостности плейлистов': 'Playlist integrity violation',
        'Необходимость ручной проверки': 'Need for manual checking',
        'Потеря времени на восстановление': 'Time loss for restoration',
        
        # Возможности сервиса
        'Возможности PlaylistChecker': 'PlaylistChecker Features',
        'Мгновенные уведомления': 'Instant Notifications',
        'Получайте уведомления о любых изменениях в ваших плейлистах в реальном времени': 'Get notifications about any changes in your playlists in real time',
        'Множество платформ': 'Multiple Platforms',
        'Поддержка Spotify, Apple Music, Yandex Music и других популярных сервисов': 'Support for Spotify, Apple Music, Yandex Music and other popular services',
        'Постоянная проверка ваших плейлистов каждые 10 минут без вашего участия': 'Continuous checking of your playlists every 10 minutes without your involvement',
    }
    
    # Заполняем русские переводы (остаются на русском)
    ru_file = 'translations/ru/LC_MESSAGES/messages.po'
    with open(ru_file, 'r', encoding='utf-8') as f:
        ru_content = f.read()
    
    # Заполняем пустые русские переводы
    pattern = r'msgid "(.*?)"\nmsgstr ""'
    def replace_ru(match):
        msgid = match.group(1)
        return f'msgid "{msgid}"\nmsgstr "{msgid}"'
    
    ru_content = re.sub(pattern, replace_ru, ru_content, flags=re.MULTILINE)
    
    with open(ru_file, 'w', encoding='utf-8') as f:
        f.write(ru_content)
    
    # Заполняем английские переводы
    en_file = 'translations/en/LC_MESSAGES/messages.po'
    with open(en_file, 'r', encoding='utf-8') as f:
        en_content = f.read()
    
    # Применяем переводы из словаря
    for russian, english in about_translations.items():
        pattern = f'msgid "{re.escape(russian)}"\nmsgstr ""'
        replacement = f'msgid "{russian}"\nmsgstr "{english}"'
        en_content = re.sub(pattern, replacement, en_content, flags=re.MULTILINE)
    
    # Заполняем оставшиеся пустые переводы
    pattern = r'msgid "(.*?)"\nmsgstr ""'
    def replace_en(match):
        msgid = match.group(1)
        # Для коротких строк оставляем как есть
        if len(msgid) < 30:
            return f'msgid "{msgid}"\nmsgstr "{msgid}"'
        else:
            # Для длинных текстов оставляем пустыми
            return match.group(0)
    
    en_content = re.sub(pattern, replace_en, en_content, flags=re.MULTILINE)
    
    with open(en_file, 'w', encoding='utf-8') as f:
        f.write(en_content)
    
    print("✅ Переводы для about.html обновлены!")

if __name__ == '__main__':
    fill_about_translations()
