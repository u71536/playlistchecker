# Переводы PlaylistChecker

Этот проект поддерживает многоязычность с помощью Flask-Babel.

## Поддерживаемые языки

- 🇷🇺 Русский (ru) - основной язык
- 🇺🇸 Английский (en)

## Управление переводами

### Быстрые команды

```bash
# Полный цикл обновления переводов
python manage_translations.py full

# Извлечь новые строки для перевода
python manage_translations.py extract

# Обновить существующие переводы
python manage_translations.py update

# Скомпилировать переводы
python manage_translations.py compile

# Добавить новый язык (например, французский)
python manage_translations.py init fr
```

### Ручное управление

```bash
# Извлечь строки для перевода
pybabel extract -F babel.cfg -k _l -o messages.pot .

# Инициализировать новый язык
pybabel init -i messages.pot -d translations -l <код_языка>

# Обновить переводы
pybabel update -i messages.pot -d translations

# Скомпилировать переводы
pybabel compile -d translations
```

## Добавление переводов в код

### В Python коде

```python
from flask_babel import gettext, lazy_gettext

# Для обычных строк
flash(gettext('Сообщение для пользователя'))

# Для форм и других случаев, где нужна ленивая загрузка
class MyForm(FlaskForm):
    field = StringField(lazy_gettext('Название поля'))
```

### В шаблонах Jinja2

```html
<!-- Простой перевод -->
<h1>{{ _('Заголовок страницы') }}</h1>

<!-- Перевод с переменными -->
<p>{{ _('Привет, %(username)s!', username=current_user.username) }}</p>

<!-- Множественные формы -->
<p>{{ ngettext('%(num)d файл', '%(num)d файла', '%(num)d файлов', num=count) }}</p>
```

## Структура файлов переводов

```
translations/
├── en/
│   └── LC_MESSAGES/
│       ├── messages.po  # Исходный файл переводов
│       └── messages.mo  # Скомпилированный файл
└── ru/
    └── LC_MESSAGES/
        ├── messages.po
        └── messages.mo
```

## Переключение языков

Пользователи могут переключать язык через:
1. Переключатель в навигационном меню
2. URL: `/set_language/<код_языка>`

Выбранный язык сохраняется в:
- Сессии пользователя
- Профиле пользователя (для авторизованных)

## Добавление нового языка

1. Инициализируйте новый язык:
   ```bash
   python manage_translations.py init <код_языка>
   ```

2. Добавьте язык в конфигурацию приложения (`app.py`):
   ```python
   app.config['LANGUAGES'] = {
       'ru': 'Русский',
       'en': 'English',
       'fr': 'Français'  # новый язык
   }
   ```

3. Переведите строки в файле `translations/<код_языка>/LC_MESSAGES/messages.po`

4. Скомпилируйте переводы:
   ```bash
   python manage_translations.py compile
   ```

## Рекомендации

1. **Всегда используйте функции перевода** для пользовательских строк
2. **Регулярно обновляйте переводы** при добавлении нового текста
3. **Тестируйте на разных языках** перед релизом
4. **Используйте контекст** для неоднозначных переводов

## Автоматизация

Для автоматического обновления переводов при разработке можно добавить в CI/CD:

```bash
# В скрипте деплоя
python manage_translations.py full
```
