#!/bin/bash

# Скрипт для обновления Docker образа из GitHub Container Registry

echo "🔄 Обновление Playlist Checker..."

# Остановить текущие контейнеры
echo "⏹️  Остановка контейнеров..."
docker-compose down

# Удалить старый образ
echo "🗑️  Удаление старого образа..."
docker rmi ghcr.io/u71536/playlistchecker:latest 2>/dev/null || true

# Загрузить новый образ
echo "⬇️  Загрузка нового образа..."
docker pull ghcr.io/u71536/playlistchecker:latest

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
