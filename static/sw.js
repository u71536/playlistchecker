// Service Worker для обработки push-уведомлений PlaylistChecker

const CACHE_NAME = 'playlistchecker-v1';
const urlsToCache = [
    '/',
    '/static/css/bootstrap.min.css',
    '/static/js/bootstrap.bundle.min.js',
    '/static/favicon.ico'
];

// Установка Service Worker
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('Кэш открыт');
                return cache.addAll(urlsToCache);
            })
    );
});

// Активация Service Worker
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Удаляем старый кэш:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Обработка fetch запросов
self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                // Возвращаем кэшированную версию или загружаем из сети
                return response || fetch(event.request);
            }
        )
    );
});

// Обработка push-уведомлений
self.addEventListener('push', function(event) {
    console.log('Получено push-уведомление:', event);
    
    let notificationData = {
        title: 'PlaylistChecker',
        body: 'У вас есть новые уведомления',
        icon: '/static/icon-192x192.png',
        badge: '/static/badge-72x72.png',
        data: {
            url: '/'
        },
        actions: [
            {
                action: 'view',
                title: 'Посмотреть',
                icon: '/static/view-icon.png'
            },
            {
                action: 'close',
                title: 'Закрыть',
                icon: '/static/close-icon.png'
            }
        ],
        requireInteraction: true,
        tag: 'playlistchecker-notification'
    };
    
    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = { ...notificationData, ...data };
        } catch (e) {
            console.error('Ошибка парсинга данных push-уведомления:', e);
            notificationData.body = event.data.text();
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(notificationData.title, notificationData)
    );
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', function(event) {
    console.log('Клик по уведомлению:', event);
    
    event.notification.close();
    
    if (event.action === 'view' || !event.action) {
        // Открываем или фокусируем окно приложения
        event.waitUntil(
            clients.matchAll({ type: 'window' }).then(function(clientList) {
                const url = event.notification.data?.url || '/';
                
                // Ищем уже открытое окно
                for (let i = 0; i < clientList.length; i++) {
                    const client = clientList[i];
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // Открываем новое окно
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
        );
    } else if (event.action === 'close') {
        // Просто закрываем уведомление (уже закрыто выше)
        console.log('Уведомление закрыто пользователем');
    }
});

// Обработка закрытия уведомлений
self.addEventListener('notificationclose', function(event) {
    console.log('Уведомление закрыто:', event);
    
    // Здесь можно отправить аналитику о закрытии уведомления
    // fetch('/api/analytics/notification-closed', {
    //     method: 'POST',
    //     body: JSON.stringify({
    //         tag: event.notification.tag,
    //         timestamp: Date.now()
    //     })
    // });
});

// Обработка фоновой синхронизации (если потребуется в будущем)
self.addEventListener('sync', function(event) {
    if (event.tag === 'background-sync') {
        event.waitUntil(
            // Здесь можно добавить логику фоновой синхронизации
            console.log('Фоновая синхронизация:', event.tag)
        );
    }
});

// Обработка ошибок
self.addEventListener('error', function(event) {
    console.error('Ошибка в Service Worker:', event.error);
});

self.addEventListener('unhandledrejection', function(event) {
    console.error('Необработанное отклонение промиса в Service Worker:', event.reason);
});
