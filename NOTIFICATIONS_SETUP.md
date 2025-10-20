# Настройка системы уведомлений PlaylistChecker

Этот документ описывает, как настроить все типы уведомлений в PlaylistChecker.

## 🔧 Обзор системы уведомлений

PlaylistChecker поддерживает три типа уведомлений:
- 📧 **Email уведомления** - отправка на почту
- 📱 **Telegram уведомления** - через Telegram бота
- 🌐 **Браузерные push-уведомления** - нативные уведомления браузера

## 📧 Настройка Email уведомлений

### 1. Настройка SMTP сервера

Добавьте в ваш `.env` файл:

```env
# Email настройки
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
```

### 2. Для Gmail

1. Включите двухфакторную аутентификацию
2. Создайте пароль приложения:
   - Перейдите в Google Account → Security
   - В разделе "Signing in to Google" выберите "App passwords"
   - Создайте новый пароль для приложения
   - Используйте этот пароль в `MAIL_PASSWORD`

### 3. Для других почтовых сервисов

**Yandex:**
```env
MAIL_SERVER=smtp.yandex.ru
MAIL_PORT=587
MAIL_USE_TLS=True
```

**Mail.ru:**
```env
MAIL_SERVER=smtp.mail.ru
MAIL_PORT=587
MAIL_USE_TLS=True
```

**Outlook/Hotmail:**
```env
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
```

## 📱 Настройка Telegram уведомлений

### 1. Создание Telegram бота

1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните токен бота

### 2. Настройка webhook (для продакшена)

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://yourdomain.com/api/telegram/webhook"}'
```

### 3. Переменные окружения

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
```

### 4. Подключение пользователей

Пользователи подключают Telegram через:
1. Настройки уведомлений → "Подключить Telegram"
2. Переход по ссылке на бота
3. Отправка команды `/start` с уникальным кодом

## 🌐 Настройка браузерных push-уведомлений

### 1. Генерация VAPID ключей

Запустите скрипт генерации ключей:

```bash
python generate_vapid_keys.py
```

### 2. Добавление ключей в .env

```env
VAPID_PUBLIC_KEY=your_generated_public_key
VAPID_PRIVATE_KEY=your_generated_private_key
VAPID_EMAIL=mailto:your_email@example.com
```

### 3. Настройка Service Worker

Service Worker уже настроен в `static/sw.js`. Убедитесь, что:
- Файл доступен по пути `/static/sw.js`
- HTTPS включен (обязательно для push-уведомлений)

### 4. Иконки уведомлений (опционально)

Добавьте иконки в папку `static/`:
- `icon-192x192.png` - основная иконка
- `badge-72x72.png` - значок уведомления
- `view-icon.png` - иконка действия "Посмотреть"
- `close-icon.png` - иконка действия "Закрыть"

## 🚀 Развертывание

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Миграция базы данных

```bash
flask db upgrade
```

### 3. Проверка настроек

Убедитесь, что все переменные окружения настроены:

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Проверка email
print('Email:', 'OK' if os.getenv('MAIL_USERNAME') else 'НЕ НАСТРОЕН')

# Проверка Telegram
print('Telegram:', 'OK' if os.getenv('TELEGRAM_BOT_TOKEN') else 'НЕ НАСТРОЕН')

# Проверка VAPID
print('VAPID:', 'OK' if os.getenv('VAPID_PUBLIC_KEY') else 'НЕ НАСТРОЕН')
"
```

## 🔧 Настройка пользователей

### Для пользователей

1. Войдите в аккаунт PlaylistChecker
2. Перейдите в меню пользователя → "Уведомления"
3. Включите нужные типы уведомлений:
   - ✅ Email уведомления (включены по умолчанию)
   - 📱 Telegram уведомления (требует подключения бота)
   - 🌐 Браузерные уведомления (требует разрешения браузера)

### Подключение Telegram

1. В настройках уведомлений нажмите "Подключить Telegram"
2. Перейдите по ссылке на бота
3. Отправьте команду `/start`
4. Вернитесь в настройки и включите Telegram уведомления

### Разрешение браузерных уведомлений

1. В настройках уведомлений нажмите "Разрешить уведомления"
2. Подтвердите разрешение в браузере
3. Включите браузерные уведомления

## 🐛 Устранение неполадок

### Email не отправляются

1. Проверьте настройки SMTP
2. Убедитесь, что пароль приложения правильный
3. Проверьте логи приложения
4. Тестируйте подключение:

```python
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your_email@gmail.com', 'your_app_password')
server.quit()
print("SMTP подключение успешно!")
```

### Telegram бот не отвечает

1. Проверьте токен бота
2. Убедитесь, что webhook настроен правильно
3. Проверьте логи сервера
4. Тестируйте бота вручную

### Push-уведомления не работают

1. Убедитесь, что сайт работает по HTTPS
2. Проверьте VAPID ключи
3. Убедитесь, что Service Worker зарегистрирован
4. Проверьте разрешения браузера

## 📊 Мониторинг

### Логи уведомлений

Все уведомления логируются. Проверьте логи для диагностики:

```bash
tail -f app.log | grep -i notification
```

### Статистика отправки

В будущих версиях будет добавлена статистика:
- Количество отправленных уведомлений
- Успешность доставки
- Предпочтения пользователей

## 🔒 Безопасность

1. **Никогда не публикуйте** приватные ключи и токены
2. Используйте переменные окружения для всех секретов
3. Регулярно обновляйте токены и пароли
4. Мониторьте использование API

## 📈 Производительность

- Email уведомления: ~1-2 секунды на отправку
- Telegram уведомления: ~0.5-1 секунда на отправку  
- Push-уведомления: ~0.1-0.3 секунды на отправку

Рекомендуется отправлять уведомления асинхронно для больших объемов.

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи приложения
2. Убедитесь в правильности настроек
3. Протестируйте каждый тип уведомлений отдельно
4. Обратитесь к документации сервисов (Gmail, Telegram, Web Push API)
