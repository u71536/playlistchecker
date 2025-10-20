#!/bin/bash

# Скрипт для обновления Playlist Checker

echo "🔄 Обновление Playlist Checker..."

# Остановить текущие контейнеры
echo "⏹️  Остановка контейнеров..."
docker-compose down

# Очистить старые образы
echo "🗑️  Очистка старых образов..."
docker system prune -f

# Обновить код из Git и собрать образ
echo "📥 Обновление кода из Git..."
git pull origin main || echo "⚠️  Git pull не удался, используем текущий код"

echo "🔨 Сборка нового образа..."
docker-compose build --no-cache web

# Запустить контейнеры
echo "🚀 Запуск контейнеров..."
docker-compose up -d

# Показать статус
echo "📊 Статус контейнеров:"
docker-compose ps

# Показать логи
echo "📋 Последние логи:"
docker logs playlistchecker-web --tail 10

echo "✅ Обновление завершено!"
