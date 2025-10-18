# Развертывание PlaylistChecker на сервере

Это руководство поможет вам развернуть PlaylistChecker на сервере с использованием Docker.

## Требования к серверу

- **ОС**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: минимум 1GB (рекомендуется 2GB+)
- **CPU**: 1 ядро (рекомендуется 2+)
- **Диск**: 10GB+ свободного места
- **Docker**: версия 20.10+
- **Docker Compose**: версия 2.0+

## Установка Docker

### Ubuntu/Debian:
```bash
# Обновляем пакеты
sudo apt update

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезагружаемся или выходим/входим в систему
```

### CentOS/RHEL:
```bash
# Устанавливаем Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io

# Запускаем Docker
sudo systemctl start docker
sudo systemctl enable docker

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Развертывание приложения

### 1. Клонирование репозитория

```bash
# Клонируем проект
git clone https://github.com/yourusername/PlaylistChecker.git
cd PlaylistChecker
```

### 2. Настройка переменных окружения

```bash
# Копируем пример конфигурации
cp env.production .env

# Редактируем конфигурацию
nano .env
```

**Важно**: Заполните все необходимые переменные:
- `SECRET_KEY` - сгенерируйте случайную строку
- API ключи для музыкальных сервисов
- URL для redirect_uri (замените `yourdomain.com` на ваш домен)

### 3. Генерация SECRET_KEY

```bash
# Генерируем безопасный SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Запуск приложения

```bash
# Собираем и запускаем контейнеры
docker-compose up -d --build

# Проверяем статус
docker-compose ps

# Смотрим логи
docker-compose logs -f
```

### 5. Инициализация базы данных

```bash
# Выполняем миграции (если нужно)
docker-compose exec web flask db upgrade

# Или создаем таблицы напрямую
docker-compose exec web python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Настройка домена и SSL

### 1. Настройка DNS

Настройте A-запись вашего домена на IP адрес сервера:
```
yourdomain.com -> YOUR_SERVER_IP
```

### 2. Получение SSL сертификата (Let's Encrypt)

```bash
# Устанавливаем Certbot
sudo apt install certbot

# Получаем сертификат
sudo certbot certonly --standalone -d yourdomain.com

# Копируем сертификаты в проект
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/key.pem
sudo chown $USER:$USER ./ssl/*.pem
```

### 3. Обновление конфигурации

```bash
# Создаем директорию для SSL
mkdir -p ssl

# Обновляем nginx.conf (раскомментируйте HTTPS секцию)
# Обновляем .env (измените redirect_uri на https://)
```

### 4. Перезапуск с SSL

```bash
docker-compose down
docker-compose up -d
```

## Мониторинг и обслуживание

### Просмотр логов

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи только веб-приложения
docker-compose logs -f web

# Логи Nginx
docker-compose logs -f nginx
```

### Обновление приложения

```bash
# Останавливаем контейнеры
docker-compose down

# Получаем обновления
git pull

# Пересобираем и запускаем
docker-compose up -d --build
```

### Резервное копирование

```bash
# Создаем бэкап базы данных
docker-compose exec web cp /app/instance/playlistchecker.db /app/backup_$(date +%Y%m%d_%H%M%S).db

# Или через docker cp
docker cp $(docker-compose ps -q web):/app/instance/playlistchecker.db ./backup_$(date +%Y%m%d_%H%M%S).db
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Использование диска
df -h

# Использование памяти
free -h
```

## Автоматическое обновление SSL

Создайте cron задачу для автоматического обновления сертификатов:

```bash
# Редактируем crontab
crontab -e

# Добавляем задачу (каждый месяц)
0 3 1 * * /usr/bin/certbot renew --quiet && docker-compose restart nginx
```

## Troubleshooting

### Проблемы с портами

```bash
# Проверяем какие порты заняты
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443

# Останавливаем конфликтующие сервисы
sudo systemctl stop apache2  # если установлен Apache
sudo systemctl stop nginx    # если установлен системный Nginx
```

### Проблемы с правами доступа

```bash
# Исправляем права на директории
sudo chown -R $USER:$USER .
chmod -R 755 .
```

### Проблемы с базой данных

```bash
# Проверяем файл базы данных
ls -la instance/

# Пересоздаем базу данных
rm instance/playlistchecker.db
docker-compose exec web python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Безопасность

### Firewall

```bash
# Настраиваем UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Обновления системы

```bash
# Регулярно обновляйте систему
sudo apt update && sudo apt upgrade -y
```

## Производительность

### Оптимизация для высоких нагрузок

1. **Увеличьте количество воркеров Gunicorn** в Dockerfile:
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "8", "--timeout", "120", "app:app"]
   ```

2. **Используйте PostgreSQL** вместо SQLite для продакшена

3. **Настройте кэширование** в Nginx

4. **Используйте CDN** для статических файлов

## Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь что все переменные окружения заполнены
3. Проверьте доступность портов
4. Создайте issue в GitHub репозитории
