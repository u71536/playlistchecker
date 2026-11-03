# PlaylistChecker

Веб-приложение для мониторинга изменений в плейлистах на различных музыкальных платформах.

## Возможности

- 🔐 Авторизация в музыкальных сервисах (Spotify, Deezer, Apple Music, Yandex Music)
- 📋 Добавление плейлистов для мониторинга
- 🔍 Ежедневная проверка изменений в плейлистах
- 🔔 Уведомления о удаленных треках
- 📊 Статистика и история изменений
- 🌐 Современный веб-интерфейс

## Поддерживаемые сервисы

- **Spotify** - полная поддержка API ✅
- **Apple Music** - поддержка через Apple Music API (в разработке)
- **Yandex Music** - поддержка через Yandex Music API (в разработке)
- ~~**Deezer** - временно отключен~~

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd PlaylistChecker
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Скопируйте файл `env_example.txt` в `.env` и заполните необходимые параметры:

```bash
cp env_example.txt .env
```

Отредактируйте `.env` файл:

```env
# Основные настройки
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///playlistchecker.db

# Spotify API
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:5000/auth/spotify/callback

# Deezer API
DEEZER_APP_ID=your_deezer_app_id
DEEZER_APP_SECRET=your_deezer_app_secret
DEEZER_REDIRECT_URI=http://localhost:5000/auth/deezer/callback

# Apple Music API
APPLE_MUSIC_TEAM_ID=your_apple_music_team_id
APPLE_MUSIC_KEY_ID=your_apple_music_key_id
APPLE_MUSIC_PRIVATE_KEY=your_apple_music_private_key

# Yandex Music API
YANDEX_MUSIC_CLIENT_ID=your_yandex_music_client_id
YANDEX_MUSIC_CLIENT_SECRET=your_yandex_music_client_secret
YANDEX_MUSIC_REDIRECT_URI=http://localhost:5000/auth/yandex_music/callback
```

### 4. Получение API ключей

#### Spotify
1. Перейдите на [Spotify for Developers](https://developer.spotify.com/)
2. Создайте новое приложение
3. Получите Client ID и Client Secret

#### Deezer
1. Перейдите на [Deezer Developers](https://developers.deezer.com/)
2. Создайте новое приложение
3. Получите App ID и App Secret

#### Apple Music
1. Перейдите на [Apple Developer](https://developer.apple.com/)
2. Создайте MusicKit сертификат
3. Получите Team ID, Key ID и приватный ключ

#### Yandex Music
1. Перейдите на [Yandex Developer](https://yandex.ru/dev/)
2. Создайте новое приложение
3. Получите Client ID и Client Secret

### 5. Запуск приложения

```bash
python run.py
```

Приложение будет доступно по адресу: http://localhost:5000

**Альтернативные способы запуска:**

```bash
# Через Flask CLI
flask run

# Или напрямую через Python
python app.py
```

## Использование

### 1. Регистрация и вход
- Создайте аккаунт или войдите в существующий
- Заполните профиль пользователя

### 2. Подключение музыкальных сервисов
- Перейдите в панель управления
- Нажмите "Подключить" для нужного сервиса
- Авторизуйтесь через OAuth

### 3. Добавление плейлистов
- Нажмите "Добавить плейлист"
- Выберите сервис и вставьте ссылку на плейлист
- Плейлист будет добавлен для мониторинга

### 4. Мониторинг изменений
- Отдельный процесс проверяет плейлисты каждый день в 9:00 (`python scheduler_runner.py`)
- При удалении треков вы получите уведомления
- Вся статистика доступна в веб-интерфейсе

## Структура проекта

```
PlaylistChecker/
├── app.py                 # Основное приложение Flask
├── run.py                 # Скрипт запуска веб-сервера
├── scheduler_runner.py    # Ежедневная проверка плейлистов
├── playlist_monitor.py    # Модуль мониторинга плейлистов
├── requirements.txt       # Зависимости Python
├── env_example.txt       # Пример переменных окружения
├── services/             # Сервисы для работы с API
│   ├── __init__.py
│   ├── spotify_service.py
│   ├── deezer_service.py
│   ├── apple_music_service.py
│   └── yandex_music_service.py
└── templates/            # HTML шаблоны
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── playlists.html
    └── add_playlist.html
```

## Технологии

- **Backend**: Flask, SQLAlchemy, APScheduler
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **База данных**: SQLite (по умолчанию), PostgreSQL (для продакшена)
- **API**: Spotify Web API, Deezer API, Apple Music API, Yandex Music API

## Развертывание

### Локальная разработка
```bash
python run.py
python scheduler_runner.py
```

### Продакшен (с Gunicorn)
Веб и проверка запускаются отдельно, иначе каждый воркер Gunicorn ставит свою задачу.

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
python scheduler_runner.py
```

### Docker (опционально)
```bash
docker build -t playlistchecker .
docker run -p 5000:5000 playlistchecker
```

## Лицензия

MIT License

## Поддержка

Если у вас возникли вопросы или проблемы, создайте issue в репозитории проекта.
