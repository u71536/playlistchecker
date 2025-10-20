#!/usr/bin/env python3
"""
Скрипт для управления переводами PlaylistChecker
"""

import os
import sys
import subprocess

def extract_messages():
    """Извлечь строки для перевода из кода и шаблонов"""
    print("Извлекаем строки для перевода...")
    result = subprocess.run([
        'pybabel', 'extract', '-F', 'babel.cfg', '-k', '_l', '-o', 'messages.pot', '.'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Строки успешно извлечены в messages.pot")
    else:
        print(f"✗ Ошибка извлечения: {result.stderr}")
        return False
    return True

def init_language(lang):
    """Инициализировать новый язык"""
    print(f"Инициализируем язык {lang}...")
    result = subprocess.run([
        'pybabel', 'init', '-i', 'messages.pot', '-d', 'translations', '-l', lang
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Язык {lang} успешно инициализирован")
    else:
        print(f"✗ Ошибка инициализации: {result.stderr}")
        return False
    return True

def update_translations():
    """Обновить существующие переводы"""
    print("Обновляем переводы...")
    result = subprocess.run([
        'pybabel', 'update', '-i', 'messages.pot', '-d', 'translations'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Переводы успешно обновлены")
    else:
        print(f"✗ Ошибка обновления: {result.stderr}")
        return False
    return True

def compile_translations():
    """Скомпилировать переводы"""
    print("Компилируем переводы...")
    result = subprocess.run([
        'pybabel', 'compile', '-d', 'translations'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Переводы успешно скомпилированы")
    else:
        print(f"✗ Ошибка компиляции: {result.stderr}")
        return False
    return True

def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python manage_translations.py extract    - извлечь строки для перевода")
        print("  python manage_translations.py init <lang> - инициализировать новый язык")
        print("  python manage_translations.py update     - обновить переводы")
        print("  python manage_translations.py compile    - скомпилировать переводы")
        print("  python manage_translations.py full       - полный цикл (extract + update + compile)")
        return
    
    command = sys.argv[1]
    
    if command == 'extract':
        extract_messages()
    elif command == 'init':
        if len(sys.argv) < 3:
            print("Укажите код языка (например: en, fr, de)")
            return
        lang = sys.argv[2]
        if extract_messages():
            init_language(lang)
    elif command == 'update':
        if extract_messages():
            update_translations()
    elif command == 'compile':
        compile_translations()
    elif command == 'full':
        if extract_messages():
            if update_translations():
                compile_translations()
    else:
        print(f"Неизвестная команда: {command}")

if __name__ == '__main__':
    main()
