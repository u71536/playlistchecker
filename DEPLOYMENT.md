# Развертывание PlaylistChecker на сервере с несколькими сервисами

Это руководство поможет вам развернуть PlaylistChecker на сервере с использованием Docker в среде с несколькими сервисами.

## Требования к серверу

- **ОС**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: минимум 2GB (рекомендуется 4GB+ для нескольких сервисов)
- **CPU**: 2 ядра (рекомендуется 4+)
- **Диск**: 20GB+ свободного места
- **Docker**: версия 20.10+
- **Docker Compose**: версия 2.0+

## Архитектура мультисервисного развертывания

В данной конфигурации предполагается:
- **Traefik** как основной reverse proxy для всех сервисов
- **Общая Docker сеть** для взаимодействия между сервисами
- **Изолированные порты** для каждого сервиса
- **Централизованное управление SSL** через Traefik

## Установка Docker

### Ubuntu/Debian:
```bash
# Обновляем пакеты
sudo apt update

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавляем пользователя в группу docker (замените $USER на ваше имя пользователя)
sudo usermod -aG docker ubuntu

# Обновляем группы текущей сессии
newgrp docker

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

```

**Примечание**: После добавления в группу docker выполните `newgrp docker` или перезайдите в систему.

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

## Настройка общей инфраструктуры

### 1. Создание общей Docker сети

```bash
# Создаем сеть для всех сервисов
docker network create traefik-network
```

### 2. Установка и настройка Traefik

Создайте директорию для Traefik:
```bash
mkdir -p /opt/traefik
cd /opt/traefik
```

Создайте `docker-compose.yml` для Traefik:
```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard (опционально)
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/traefik.yml:ro
      - ./acme.json:/acme.json
      - ./logs:/logs
    networks:
      - traefik-network
    environment:
      - TRAEFIK_API_DASHBOARD=true
      - TRAEFIK_API_INSECURE=true

networks:
  traefik-network:
    external: true
```

Создайте `traefik.yml`:
```yaml
api:
  dashboard: true
  insecure: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entrypoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: traefik-network

certificatesResolvers:
  letsencrypt:
    acme:
      email: your-email@example.com
      storage: acme.json
      httpChallenge:
        entryPoint: web

log:
  filePath: "/logs/traefik.log"
  level: INFO

accessLog:
  filePath: "/logs/access.log"
```

Запустите Traefik:
```bash
# Создаем файл для SSL сертификатов
touch acme.json
chmod 600 acme.json

# Создаем директорию для логов
mkdir -p logs

# Запускаем Traefik
docker-compose up -d
```

## Развертывание PlaylistChecker

### 1. Подготовка директории проекта

```bash
# Создаем структуру для сервисов
mkdir -p /opt/services/playlistchecker
cd /opt/services/playlistchecker

# Клонируем проект (замените на ваш репозиторий)
# Вариант 1: Публичный репозиторий
git clone https://github.com/u71536/playlistchecker.git .

# Вариант 2: С Personal Access Token
# git clone https://username:TOKEN@github.com/username/playlistchecker.git .

# Вариант 3: SSH (рекомендуется)
# git clone git@github.com:username/playlistchecker.git .
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
- URL для redirect_uri (замените `yourdomain.com` на ваш поддомен)

### 3. Генерация SECRET_KEY

```bash
# Генерируем безопасный SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Обновление docker-compose.yml

Обновите `docker-compose.yml` для работы с Traefik:

```yaml
version: '3.8'

services:
  web:
    build: .
    container_name: playlistchecker-web
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./instance:/app/instance
    networks:
      - traefik-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.playlistchecker.rule=Host(`playlist.yourdomain.com`)"
      - "traefik.http.routers.playlistchecker.entrypoints=websecure"
      - "traefik.http.routers.playlistchecker.tls.certresolver=letsencrypt"
      - "traefik.http.services.playlistchecker.loadbalancer.server.port=5000"
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    container_name: playlistchecker-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: playlistchecker
      POSTGRES_USER: playlistchecker
      POSTGRES_PASSWORD: playlistcheckerQp9)3ni~
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - traefik-network

volumes:
  postgres_data:

networks:
  traefik-network:
    external: true
```

### 5. Запуск приложения

```bash
# Собираем и запускаем контейнеры
docker-compose up -d --build

# Проверяем статус
docker-compose ps

# Смотрим логи
docker-compose logs -f
```

### 6. Инициализация базы данных

```bash
# Выполняем миграции (если нужно)
docker-compose exec web flask db upgrade

# Или создаем таблицы напрямую
docker-compose exec web python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Настройка доменов и поддоменов

### 1. Настройка DNS

Настройте DNS записи для всех ваших сервисов:
```
# Основной домен
yourdomain.com -> YOUR_SERVER_IP

# Поддомены для сервисов
playlist.yourdomain.com -> YOUR_SERVER_IP
api.yourdomain.com -> YOUR_SERVER_IP
admin.yourdomain.com -> YOUR_SERVER_IP
monitor.yourdomain.com -> YOUR_SERVER_IP

# Wildcard запись (опционально)
*.yourdomain.com -> YOUR_SERVER_IP
```

#### Настройка в популярных DNS провайдерах

##### Porkbun
1. Войдите в панель управления Porkbun (https://porkbun.com/account)
2. Перейдите в "DNS Records" для вашего домена
3. Добавьте записи:

```
Type: A    Name: @         Answer: YOUR_SERVER_IP    TTL: 600
Type: A    Name: playlist  Answer: YOUR_SERVER_IP    TTL: 600
Type: A    Name: api       Answer: YOUR_SERVER_IP    TTL: 600
Type: A    Name: admin     Answer: YOUR_SERVER_IP    TTL: 600
Type: A    Name: monitor   Answer: YOUR_SERVER_IP    TTL: 600
Type: A    Name: traefik   Answer: YOUR_SERVER_IP    TTL: 600
```

**Особенности Porkbun:**
- TTL рекомендуется устанавливать 600 секунд (10 минут) для быстрого обновления
- Поддерживает wildcard записи: `Type: A, Name: *, Answer: YOUR_SERVER_IP`
- Автоматически добавляет точку в конце FQDN записей
- Поддерживает API для автоматизации управления DNS
- Бесплатные SSL сертификаты (но мы используем Let's Encrypt через Traefik)

##### Cloudflare
1. Войдите в панель Cloudflare
2. Выберите ваш домен
3. Перейдите в раздел "DNS"
4. Добавьте записи:

```
Type: A    Name: @         Content: YOUR_SERVER_IP    Proxy: Off
Type: A    Name: playlist  Content: YOUR_SERVER_IP    Proxy: Off  
Type: A    Name: api       Content: YOUR_SERVER_IP    Proxy: Off
Type: A    Name: admin     Content: YOUR_SERVER_IP    Proxy: Off
```

**Важно**: Отключите Cloudflare Proxy (серая тучка) для корректной работы Let's Encrypt.

##### Namecheap
1. Войдите в Namecheap панель
2. Перейдите в "Domain List" → "Manage"
3. Выберите "Advanced DNS"
4. Добавьте записи:

```
Type: A Record    Host: @         Value: YOUR_SERVER_IP    TTL: 30 min
Type: A Record    Host: playlist  Value: YOUR_SERVER_IP    TTL: 30 min
Type: A Record    Host: api       Value: YOUR_SERVER_IP    TTL: 30 min
Type: A Record    Host: admin     Value: YOUR_SERVER_IP    TTL: 30 min
```

##### Reg.ru
1. Войдите в панель управления
2. Выберите домен → "Управление DNS"
3. Добавьте записи:

```
Тип: A    Субдомен: @         IP: YOUR_SERVER_IP
Тип: A    Субдомен: playlist  IP: YOUR_SERVER_IP  
Тип: A    Субдомен: api       IP: YOUR_SERVER_IP
Тип: A    Субдомен: admin     IP: YOUR_SERVER_IP
```

#### Проверка DNS записей

После настройки DNS записей, проверьте их:

```bash
# Узнайте IP адрес вашего сервера
curl ifconfig.me

# Проверка основного домена
nslookup yourdomain.com

# Проверка поддоменов
nslookup playlist.yourdomain.com
nslookup api.yourdomain.com
nslookup admin.yourdomain.com

# Альтернативная проверка с dig
dig yourdomain.com
dig playlist.yourdomain.com

# Проверка с конкретного DNS сервера
nslookup playlist.yourdomain.com 8.8.8.8
nslookup playlist.yourdomain.com 1.1.1.1

# Онлайн проверка
# Используйте сайты: whatsmydns.net или dnschecker.org
```

#### Время распространения DNS

- **TTL (Time To Live)**: Устанавливайте 300-1800 секунд (5-30 минут)
- **Полное распространение**: 24-48 часов по всему миру
- **Локальная проверка**: 5-30 минут

**Важно**: Подождите 5-30 минут после настройки DNS перед запуском сервисов с SSL.

### 2. SSL сертификаты

SSL сертификаты автоматически управляются Traefik через Let's Encrypt. Убедитесь что:
- В `traefik.yml` указан правильный email
- Домены доступны извне (порты 80 и 443 открыты)
- DNS записи настроены корректно

### 3. Проверка SSL

```bash
# Проверяем статус сертификатов
docker exec traefik cat /acme.json | jq '.letsencrypt.Certificates[].domain'

# Проверяем доступность
curl -I https://playlist.yourdomain.com
```

## Управление несколькими сервисами

### Структура директорий

Рекомендуемая структура для нескольких сервисов:
```
/opt/
├── traefik/                    # Reverse proxy
│   ├── docker-compose.yml
│   ├── traefik.yml
│   └── acme.json
├── services/
│   ├── playlistchecker/        # PlaylistChecker
│   │   ├── docker-compose.yml
│   │   ├── .env
│   │   └── ...
│   ├── another-service/        # Другой сервис
│   │   ├── docker-compose.yml
│   │   ├── .env
│   │   └── ...
│   └── monitoring/             # Мониторинг (опционально)
│       ├── docker-compose.yml
│       └── ...
└── scripts/                    # Скрипты управления
    ├── deploy-all.sh
    ├── backup-all.sh
    └── update-all.sh
```

### Добавление нового сервиса

Для добавления нового сервиса:

1. **Создайте директорию сервиса:**
```bash
mkdir -p /opt/services/new-service
cd /opt/services/new-service
```

2. **Создайте docker-compose.yml с Traefik labels:**
```yaml
version: '3.8'

services:
  app:
    image: your-service:latest
    container_name: new-service-app
    restart: unless-stopped
    networks:
      - traefik-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.new-service.rule=Host(`service.yourdomain.com`)"
      - "traefik.http.routers.new-service.entrypoints=websecure"
      - "traefik.http.routers.new-service.tls.certresolver=letsencrypt"
      - "traefik.http.services.new-service.loadbalancer.server.port=8080"

networks:
  traefik-network:
    external: true
```

3. **Запустите сервис:**
```bash
docker-compose up -d
```

## Мониторинг и обслуживание

### Просмотр логов

```bash
# Логи Traefik
cd /opt/traefik && docker-compose logs -f

# Логи PlaylistChecker
cd /opt/services/playlistchecker && docker-compose logs -f

# Логи конкретного сервиса
cd /opt/services/playlistchecker && docker-compose logs -f web

# Все контейнеры
docker logs -f container_name
```

### Обновление сервисов

```bash
# Обновление PlaylistChecker
cd /opt/services/playlistchecker
git pull
docker-compose up -d --build

# Обновление всех сервисов (скрипт)
/opt/scripts/update-all.sh
```

### Резервное копирование

```bash
# Бэкап базы данных PlaylistChecker (PostgreSQL)
docker exec playlistchecker-db pg_dump -U playlistchecker playlistchecker > backup_$(date +%Y%m%d_%H%M%S).sql

# Бэкап всех volumes
docker run --rm -v playlistchecker_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Скрипт для бэкапа всех сервисов
/opt/scripts/backup-all.sh
```

### Мониторинг ресурсов

```bash
# Использование ресурсов всеми контейнерами
docker stats

# Использование диска
df -h

# Использование памяти
free -h

# Статус всех сервисов
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Автоматизация и скрипты управления

### Создание скриптов управления

Создайте полезные скрипты в `/opt/scripts/`:

**1. Скрипт обновления всех сервисов (`update-all.sh`):**
```bash
#!/bin/bash
set -e

echo "Обновление всех сервисов..."

# Обновление PlaylistChecker
echo "Обновление PlaylistChecker..."
cd /opt/services/playlistchecker
git pull
docker-compose up -d --build

# Добавьте другие сервисы по мере необходимости
# cd /opt/services/another-service
# git pull
# docker-compose up -d --build

echo "Все сервисы обновлены!"
```

**2. Скрипт резервного копирования (`backup-all.sh`):**
```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Создание резервных копий в $BACKUP_DIR..."

# Бэкап PlaylistChecker
echo "Бэкап PlaylistChecker..."
docker exec playlistchecker-db pg_dump -U playlistchecker playlistchecker > "$BACKUP_DIR/playlistchecker.sql"

# Бэкап volumes
docker run --rm -v playlistchecker_postgres_data:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/playlistchecker_volumes.tar.gz -C /data .

# Бэкап конфигураций
cp -r /opt/services "$BACKUP_DIR/services_config"
cp -r /opt/traefik "$BACKUP_DIR/traefik_config"

echo "Резервное копирование завершено: $BACKUP_DIR"
```

**3. Скрипт мониторинга (`health-check.sh`):**
```bash
#!/bin/bash

echo "=== Статус сервисов ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n=== Использование ресурсов ==="
docker stats --no-stream

echo -e "\n=== Использование диска ==="
df -h

echo -e "\n=== Проверка доступности сервисов ==="
curl -s -o /dev/null -w "PlaylistChecker: %{http_code}\n" https://playlist.yourdomain.com
curl -s -o /dev/null -w "Traefik Dashboard: %{http_code}\n" http://yourdomain.com:8080
```

Сделайте скрипты исполняемыми:
```bash
chmod +x /opt/scripts/*.sh
```

### Автоматические задачи (Cron)

```bash
# Редактируем crontab
crontab -e

# Добавляем задачи
# Ежедневный health check в 6:00
0 6 * * * /opt/scripts/health-check.sh >> /var/log/health-check.log 2>&1

# Еженедельный бэкап в воскресенье в 3:00
0 3 * * 0 /opt/scripts/backup-all.sh >> /var/log/backup.log 2>&1

# Очистка старых бэкапов (старше 30 дней)
0 4 * * 0 find /opt/backups -type d -mtime +30 -exec rm -rf {} +

# Очистка Docker (каждый месяц)
0 2 1 * * docker system prune -af --volumes >> /var/log/docker-cleanup.log 2>&1
```

## Troubleshooting

### Проблемы с Traefik

```bash
# Проверяем статус Traefik
docker logs traefik

# Проверяем конфигурацию
docker exec traefik cat /traefik.yml

# Проверяем сертификаты
docker exec traefik cat /acme.json | jq '.'

# Перезапуск Traefik
cd /opt/traefik && docker-compose restart
```

### Проблемы с сетью Docker

```bash
# Проверяем сети
docker network ls

# Пересоздаем сеть
docker network rm traefik-network
docker network create traefik-network

# Проверяем подключения к сети
docker network inspect traefik-network
```

### Проблемы с портами

```bash
# Проверяем какие порты заняты
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
sudo netstat -tlnp | grep :8080

# Останавливаем конфликтующие сервисы
sudo systemctl stop apache2  # если установлен Apache
sudo systemctl stop nginx    # если установлен системный Nginx
```

### Проблемы с правами доступа

```bash
# Исправляем права на директории
sudo chown -R $USER:$USER /opt/services/
sudo chown -R $USER:$USER /opt/traefik/
chmod -R 755 /opt/services/
chmod 600 /opt/traefik/acme.json
```

### Проблемы с базой данных

```bash
# Проверяем статус PostgreSQL
docker logs playlistchecker-db

# Подключение к базе данных
docker exec -it playlistchecker-db psql -U playlistchecker -d playlistchecker

# Пересоздание базы данных
docker-compose exec web python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Проблемы с DNS и SSL

```bash
# Проверяем DNS
nslookup playlist.yourdomain.com

# Проверяем доступность портов извне
curl -I http://yourdomain.com
curl -I https://playlist.yourdomain.com

# Принудительное обновление сертификатов
docker exec traefik rm /acme.json
docker restart traefik
```

## Безопасность

### Firewall

```bash
# Настраиваем UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (для Traefik)
sudo ufw allow 443/tcp   # HTTPS (для Traefik)
sudo ufw allow 8080/tcp  # Traefik Dashboard (опционально, только для админов)
sudo ufw enable

# Для дополнительной безопасности, ограничьте доступ к Traefik Dashboard
sudo ufw allow from YOUR_ADMIN_IP to any port 8080
```

### Безопасность Traefik Dashboard

Добавьте базовую аутентификацию для Traefik Dashboard:

```bash
# Генерируем пароль
htpasswd -nb admin your_password

# Добавляем в traefik.yml:
# api:
#   dashboard: true
#   middlewares:
#     - auth
# 
# http:
#   middlewares:
#     auth:
#       basicAuth:
#         users:
#           - "admin:$2y$10$..."
```

### Обновления системы

```bash
# Регулярно обновляйте систему
sudo apt update && sudo apt upgrade -y

# Настройте автоматические обновления безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Мониторинг безопасности

```bash
# Установка fail2ban для защиты от брутфорса
sudo apt install fail2ban

# Мониторинг логов Docker
sudo journalctl -u docker.service -f
```

## Производительность

### Оптимизация для высоких нагрузок

1. **Увеличьте количество воркеров Gunicorn** в Dockerfile:
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "8", "--timeout", "120", "app:app"]
   ```

2. **Используйте PostgreSQL** вместо SQLite (уже настроено в новой конфигурации)

3. **Настройте ограничения ресурсов** в docker-compose.yml:
   ```yaml
   services:
     web:
       deploy:
         resources:
           limits:
             cpus: '2.0'
             memory: 1G
           reservations:
             cpus: '0.5'
             memory: 512M
   ```

4. **Используйте кэширование в Traefik**

5. **Настройте мониторинг производительности** с Prometheus + Grafana

### Масштабирование

Для горизонтального масштабирования:

```yaml
# В docker-compose.yml PlaylistChecker
services:
  web:
    deploy:
      replicas: 3
    # ... остальная конфигурация
```

## Мониторинг (опционально)

### Добавление Prometheus + Grafana

Создайте `/opt/services/monitoring/docker-compose.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - traefik-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.prometheus.rule=Host(`prometheus.yourdomain.com`)"
      - "traefik.http.routers.prometheus.entrypoints=websecure"
      - "traefik.http.routers.prometheus.tls.certresolver=letsencrypt"

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=your_secure_password
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - traefik-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.grafana.rule=Host(`grafana.yourdomain.com`)"
      - "traefik.http.routers.grafana.entrypoints=websecure"
      - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"

volumes:
  prometheus_data:
  grafana_data:

networks:
  traefik-network:
    external: true
```

## Поддержка

При возникновении проблем:
1. Проверьте логи Traefik: `docker logs traefik`
2. Проверьте логи сервисов: `cd /opt/services/playlistchecker && docker-compose logs -f`
3. Убедитесь что все переменные окружения заполнены
4. Проверьте статус сети: `docker network inspect traefik-network`
5. Проверьте DNS записи и доступность портов
6. Используйте скрипт health-check: `/opt/scripts/health-check.sh`
7. Создайте issue в GitHub репозитории

### Полезные команды для диагностики

```bash
# Общий статус системы
/opt/scripts/health-check.sh

# Проверка всех контейнеров
docker ps -a

# Проверка использования ресурсов
docker stats --no-stream

# Проверка логов всех сервисов
for service in /opt/services/*/; do
  echo "=== Логи $(basename "$service") ==="
  cd "$service" && docker-compose logs --tail=50
done
```
