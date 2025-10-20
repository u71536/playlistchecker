# Автоматическое обновление через Docker

## Как это работает

1. **GitHub Actions** автоматически собирает Docker образ при каждом push в `main` ветку
2. Образ публикуется в GitHub Container Registry: `ghcr.io/u71536/playlistchecker:latest`
3. На сервере можно обновиться одной командой

## Настройка на сервере

### Первоначальная настройка

1. Убедитесь, что в `docker-compose.yml` используется образ из registry:
```yaml
image: ghcr.io/u71536/playlistchecker:latest
```

2. Сделайте скрипт обновления исполняемым:
```bash
chmod +x update.sh
```

### Обновление приложения

Для обновления до последней версии выполните:

```bash
./update.sh
```

Или вручную:

```bash
# Остановить контейнеры
docker-compose down

# Загрузить новый образ
docker pull ghcr.io/u71536/playlistchecker:latest

# Запустить контейнеры
docker-compose up -d
```

## Автоматическое обновление

Можно настроить автоматическое обновление через cron:

```bash
# Добавить в crontab (обновление каждый час)
crontab -e

# Добавить строку:
0 * * * * cd /opt/services/playlistchecker && ./update.sh >> update.log 2>&1
```

## Проверка статуса

```bash
# Статус контейнеров
docker-compose ps

# Логи приложения
docker logs playlistchecker-web --tail 50

# Версия образа
docker images | grep playlistchecker
```

## Откат к предыдущей версии

Если нужно откатиться:

```bash
# Посмотреть доступные теги
docker images ghcr.io/u71536/playlistchecker

# Изменить тег в docker-compose.yml на нужную версию
# Например: ghcr.io/u71536/playlistchecker:sha-abc123

# Перезапустить
docker-compose up -d
```
