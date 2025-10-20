#!/usr/bin/env python3
"""
Расширенный скрипт для заполнения всех переводов
"""

import re

def fill_all_translations():
    """Заполнить все переводы"""
    
    # Расширенный словарь переводов
    translations = {
        # Основные элементы интерфейса
        'О сервисе': 'About',
        'Зачем проверять плейлисты?': 'Why Check Playlists?',
        'Мониторинг плейлистов Spotify, Apple Music, Yandex Music': 'Monitoring Spotify, Apple Music, Yandex Music Playlists',
        'Важность мониторинга музыкальных коллекций': 'Importance of Music Collection Monitoring',
        'Профессиональное решение для мониторинга ваших музыкальных коллекций': 'Professional solution for monitoring your music collections',
        'Что такое PlaylistChecker?': 'What is PlaylistChecker?',
        'Понимание важности мониторинга ваших музыкальных коллекций': 'Understanding the importance of monitoring your music collections',
        'Реальная проблема цифровой музыки': 'The Real Problem of Digital Music',
        'Статистика проблемы': 'Problem Statistics',
        'Пользователей теряют песни': 'Users lose songs',
        'Почему песни исчезают?': 'Why do songs disappear?',
        
        # SEO и описания
        'Узнайте больше о PlaylistChecker - профессиональном сервисе для отслеживания изменений в плейлистах. Подробное описание функций, возможностей и преимуществ нашего сервиса мониторинга музыкальных коллекций.': 'Learn more about PlaylistChecker - a professional service for tracking playlist changes. Detailed description of features, capabilities and benefits of our music collection monitoring service.',
        'о сервисе, playlistchecker, мониторинг плейлистов, функции, возможности, spotify, apple music, yandex music, музыкальные сервисы': 'about service, playlistchecker, playlist monitoring, features, capabilities, spotify, apple music, yandex music, music services',
        'Узнайте, почему важно отслеживать изменения в плейлистах. Подробное объяснение проблем исчезающих песен, их влияния на музыкальные коллекции и способов защиты ваших плейлистов.': 'Learn why it is important to track playlist changes. Detailed explanation of disappearing song problems, their impact on music collections and ways to protect your playlists.',
        'зачем проверять плейлисты, исчезающие песни, мониторинг плейлистов, проблемы музыкальных сервисов, защита коллекций, spotify, apple music': 'why check playlists, disappearing songs, playlist monitoring, music service problems, collection protection, spotify, apple music',
        
        # Формы и элементы
        'Вход': 'Login',
        'Вход в систему': 'Sign In',
        'Регистрация': 'Registration',
        'Нет аккаунта?': 'No account?',
        'Имя пользователя': 'Username',
        'Пароль': 'Password',
        'Email': 'Email',
        'Войти': 'Login',
        'Зарегистрироваться': 'Register',
        
        # Остальные переводы из предыдущих файлов
        'Главная': 'Home',
        'Мои плейлисты': 'My Playlists',
        'Уведомления': 'Notifications',
        'Выйти': 'Logout',
        'Подключить': 'Connect',
        'Подключен': 'Connected',
        'Добавить плейлист': 'Add Playlist',
        'Панель управления': 'Dashboard',
        'Новые уведомления': 'New Notifications',
        'Плейлистов отслеживается': 'Playlists tracked',
        'Проверено сегодня': 'Checked today',
        'Новых уведомлений': 'New notifications',
        'Следующая проверка': 'Next check',
        'Подключенные сервисы': 'Connected Services',
        'Публичные плейлисты': 'Public Playlists',
        'Без авторизации': 'Without authorization',
        'Проверен': 'Checked',
        'Не проверялся': 'Not checked',
        'треков': 'tracks',
        'У вас пока нет плейлистов': 'You have no playlists yet',
        'Добавьте плейлисты для отслеживания изменений': 'Add playlists to track changes',
        'Добавить первый плейлист': 'Add first playlist',
        
        # Настройки уведомлений
        'Настройки уведомлений': 'Notification Settings',
        'Управление уведомлениями': 'Notification Management',
        'Email уведомления': 'Email notifications',
        'Telegram уведомления': 'Telegram notifications',
        'Браузерные уведомления': 'Browser notifications',
        'Сохранить настройки': 'Save settings',
    }
    
    # Заполняем русские переводы (остаются на русском)
    ru_file = 'translations/ru/LC_MESSAGES/messages.po'
    with open(ru_file, 'r', encoding='utf-8') as f:
        ru_content = f.read()
    
    # Заполняем пустые русские переводы
    ru_content = re.sub(r'msgstr ""(?=\n\n|\n#)', lambda m: f'msgstr "{m.group(0)[8:-1]}"', ru_content)
    
    # Простой способ - заполняем все пустые переводы тем же текстом
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
    for russian, english in translations.items():
        pattern = f'msgid "{re.escape(russian)}"\nmsgstr ""'
        replacement = f'msgid "{russian}"\nmsgstr "{english}"'
        en_content = re.sub(pattern, replacement, en_content, flags=re.MULTILINE)
    
    # Заполняем оставшиеся пустые переводы базовыми переводами или оригинальным текстом
    pattern = r'msgid "(.*?)"\nmsgstr ""'
    def replace_en(match):
        msgid = match.group(1)
        # Если это короткая строка без специальных символов, оставляем как есть
        if len(msgid) < 50 and not any(char in msgid for char in '.,!?'):
            return f'msgid "{msgid}"\nmsgstr "{msgid}"'
        else:
            # Для длинных текстов оставляем пустыми для ручного перевода
            return match.group(0)
    
    en_content = re.sub(pattern, replace_en, en_content, flags=re.MULTILINE)
    
    with open(en_file, 'w', encoding='utf-8') as f:
        f.write(en_content)
    
    print("✅ Все переводы обновлены!")

if __name__ == '__main__':
    fill_all_translations()
