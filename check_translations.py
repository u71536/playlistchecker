#!/usr/bin/env python3
"""
Скрипт для проверки переводов
"""

import re

def check_empty_translations():
    """Проверить пустые переводы"""
    
    files = [
        ('translations/ru/LC_MESSAGES/messages.po', 'Русский'),
        ('translations/en/LC_MESSAGES/messages.po', 'Английский')
    ]
    
    for file_path, lang_name in files:
        print(f"\n=== Проверка {lang_name} переводов ===")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Найти пустые переводы
        empty_patterns = [
            r'msgstr ""(?:\n\n|\n#)',  # Простые пустые переводы
            r'msgstr ""\n"',           # Многострочные пустые переводы
        ]
        
        empty_count = 0
        for pattern in empty_patterns:
            matches = re.findall(pattern, content)
            empty_count += len(matches)
        
        # Подсчитать общее количество переводов
        total_translations = len(re.findall(r'msgstr "', content))
        
        print(f"Всего переводов: {total_translations}")
        print(f"Пустых переводов: {empty_count}")
        print(f"Заполнено: {total_translations - empty_count} ({((total_translations - empty_count) / total_translations * 100):.1f}%)")
        
        if empty_count == 0:
            print("✅ Все переводы заполнены!")
        else:
            print(f"⚠️  Осталось заполнить {empty_count} переводов")

def check_translation_quality():
    """Проверить качество переводов"""
    
    print("\n=== Проверка качества переводов ===")
    
    # Проверим несколько ключевых переводов
    key_translations = [
        ('Главная', 'Home'),
        ('О сервисе', 'About'),
        ('Войти', 'Login'),
        ('Регистрация', 'Register'),
        ('Мои плейлисты', 'My Playlists'),
    ]
    
    with open('translations/en/LC_MESSAGES/messages.po', 'r', encoding='utf-8') as f:
        en_content = f.read()
    
    print("Проверка ключевых переводов:")
    for ru_text, expected_en in key_translations:
        pattern = f'msgid "{re.escape(ru_text)}"\nmsgstr "([^"]*)"'
        match = re.search(pattern, en_content)
        
        if match:
            actual_en = match.group(1)
            status = "✅" if actual_en == expected_en else "⚠️"
            print(f"{status} '{ru_text}' -> '{actual_en}'")
        else:
            print(f"❌ Перевод для '{ru_text}' не найден")

if __name__ == '__main__':
    check_empty_translations()
    check_translation_quality()
    print("\n✅ Проверка переводов завершена!")
