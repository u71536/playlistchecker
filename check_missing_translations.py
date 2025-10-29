#!/usr/bin/env python3
"""
Подробная проверка недостающих переводов
"""

import re
import os

def check_missing_translations():
    """Проверить что именно осталось непереведенным"""
    
    files = [
        ('translations/ru/LC_MESSAGES/messages.po', 'Русский'),
        ('translations/en/LC_MESSAGES/messages.po', 'Английский')
    ]
    
    for file_path, lang_name in files:
        print(f"\n{'='*60}")
        print(f"🔍 ПРОВЕРКА {lang_name.upper()} ПЕРЕВОДОВ")
        print(f"{'='*60}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Найти все пустые переводы
        pattern = r'#: ([^\n]+)\nmsgid "(.*?)"\nmsgstr ""'
        matches = re.findall(pattern, content, re.MULTILINE)
        
        if matches:
            print(f"\n❌ Найдено {len(matches)} пустых переводов:")
            print("-" * 60)
            
            # Группируем по файлам
            by_file = {}
            for location, text in matches:
                file_name = location.split(':')[0].split('/')[-1]
                if file_name not in by_file:
                    by_file[file_name] = []
                by_file[file_name].append((location, text))
            
            for file_name, items in by_file.items():
                print(f"\n📄 {file_name} ({len(items)} строк):")
                for location, text in items[:5]:  # Показываем первые 5
                    # Обрезаем длинные тексты
                    display_text = text[:80] + "..." if len(text) > 80 else text
                    print(f"  • {location}: '{display_text}'")
                
                if len(items) > 5:
                    print(f"  ... и еще {len(items) - 5} строк")
        else:
            print(f"\n✅ Все переводы заполнены!")
        
        # Подсчитать общую статистику
        total_translations = len(re.findall(r'msgstr "', content))
        empty_translations = len(matches)
        filled_translations = total_translations - empty_translations
        percentage = (filled_translations / total_translations * 100) if total_translations > 0 else 0
        
        print(f"\n📊 Статистика {lang_name}:")
        print(f"  Всего переводов: {total_translations}")
        print(f"  Заполнено: {filled_translations} ({percentage:.1f}%)")
        print(f"  Пустых: {empty_translations} ({100-percentage:.1f}%)")

def check_template_coverage():
    """Проверить покрытие переводами в шаблонах"""
    
    print(f"\n{'='*60}")
    print("🔍 ПРОВЕРКА ПОКРЫТИЯ ШАБЛОНОВ")
    print(f"{'='*60}")
    
    template_dir = 'templates'
    
    # Паттерны для поиска непереведенного текста
    patterns = [
        (r'<h[1-6][^>]*>([^<{]+)</h[1-6]>', 'Заголовки'),
        (r'<p[^>]*>([^<{]+)</p>', 'Параграфы'),
        (r'<li[^>]*>([^<{]+)</li>', 'Списки'),
        (r'<button[^>]*>([^<{]+)</button>', 'Кнопки'),
        (r'placeholder="([^"]+)"', 'Плейсхолдеры'),
        (r'title="([^"]+)"', 'Подсказки'),
    ]
    
    for filename in sorted(os.listdir(template_dir)):
        if filename.endswith('.html'):
            filepath = os.path.join(template_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"\n📄 {filename}:")
            
            total_found = 0
            for pattern, pattern_name in patterns:
                matches = re.findall(pattern, content)
                untranslated = []
                
                for match in matches:
                    text = match.strip()
                    # Пропускаем переменные, пустые строки и уже переведенные
                    if (text and 
                        not text.startswith('{{') and 
                        not text.startswith('{%') and
                        not text.startswith('_') and
                        len(text) > 2 and
                        any(char.isalpha() and char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' for char in text)):
                        
                        untranslated.append(text)
                
                if untranslated:
                    print(f"  {pattern_name}: {len(untranslated)} непереведенных")
                    for text in untranslated[:3]:  # Показываем первые 3
                        display_text = text[:50] + "..." if len(text) > 50 else text
                        print(f"    • '{display_text}'")
                    if len(untranslated) > 3:
                        print(f"    ... и еще {len(untranslated) - 3}")
                    total_found += len(untranslated)
            
            if total_found == 0:
                print("  ✅ Все тексты переведены!")

def show_next_steps():
    """Показать следующие шаги"""
    
    print(f"\n{'='*60}")
    print("📋 СЛЕДУЮЩИЕ ШАГИ")
    print(f"{'='*60}")
    
    print("\n1. 🔧 Для добавления недостающих переводов:")
    print("   • Найдите непереведенный текст в шаблонах")
    print("   • Оберните его в {{ _('...') }}")
    print("   • Запустите: python manage_translations.py full")
    print("   • Заполните переводы в .po файлах")
    
    print("\n2. 📝 Для ручного заполнения переводов:")
    print("   • Откройте translations/en/LC_MESSAGES/messages.po")
    print("   • Найдите строки с msgstr \"\"")
    print("   • Заполните английские переводы")
    print("   • Запустите: python manage_translations.py compile")
    
    print("\n3. 🧪 Для тестирования:")
    print("   • Запустите приложение: python app.py")
    print("   • Переключите язык через глобус в навигации")
    print("   • Проверьте все страницы на обоих языках")
    
    print("\n4. 📊 Для мониторинга прогресса:")
    print("   • python check_translations.py - общая статистика")
    print("   • python check_missing_translations.py - детальный анализ")

if __name__ == '__main__':
    check_missing_translations()
    check_template_coverage()
    show_next_steps()
    print(f"\n{'='*60}")
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА!")
    print(f"{'='*60}")
