# Быстрый старт PlaylistChecker

## 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 2. Настройка переменных окружения

```bash
# Скопируйте пример файла
cp env_example.txt .env

# Отредактируйте .env файл, добавив ваши API ключи
# Минимально необходимые настройки:
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///playlistchecker.db
```

## 3. Инициализация базы данных

```bash
python init_db.py
```

## 4. Запуск приложения

```bash
python run.py
```

**Альтернативные способы запуска:**
```bash
# Через Flask CLI
flask run

# Или напрямую через Python
python app.py
```

## 5. Открытие в браузере

Перейдите по адресу: http://localhost:5000

## 6. Первые шаги

1. **Регистрация**: Создайте аккаунт или войдите как admin/admin123
2. **Подключение сервисов**: Настройте API ключи в .env и подключите музыкальные сервисы
3. **Добавление плейлистов**: Добавьте плейлисты для мониторинга
4. **Ожидание уведомлений**: Приложение будет проверять плейлисты каждый день в 9:00

## Тестирование API

```bash
python test_services.py
```

## Структура проекта

- `app.py` - основное приложение Flask
- `run.py` - скрипт запуска
- `playlist_monitor.py` - система мониторинга
- `services/` - модули для работы с API музыкальных сервисов
- `templates/` - HTML шаблоны
- `init_db.py` - инициализация базы данных
- `test_services.py` - тестирование API

## Получение API ключей

### Spotify
1. https://developer.spotify.com/
2. Создайте приложение
3. Получите Client ID и Client Secret

### Deezer  
1. https://developers.deezer.com/
2. Создайте приложение
3. Получите App ID и App Secret

### Apple Music
1. https://developer.apple.com/
2. Создайте MusicKit сертификат
3. Получите Team ID, Key ID и приватный ключ

### Yandex Music
1. https://yandex.ru/dev/
2. Создайте приложение
3. Получите Client ID и Client Secret

## Устранение неполадок

- Убедитесь, что все зависимости установлены
- Проверьте правильность API ключей в .env файле
- Проверьте логи приложения на наличие ошибок
- Убедитесь, что порт 5000 свободен

## Структура веб-проекта

```
PlaylistChecker/
├── app.py                 # Основное Flask приложение
├── run.py                 # Скрипт запуска (опционально)
├── playlist_monitor.py    # Система мониторинга
├── init_db.py            # Инициализация БД
├── requirements.txt      # Python зависимости
├── env_example.txt      # Пример переменных окружения
├── services/            # API сервисы для музыкальных платформ
└── templates/           # HTML шаблоны веб-интерфейса
```
