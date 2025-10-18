#!/usr/bin/env python3
"""
Скрипт для запуска приложения PlaylistChecker
"""

import os
from app import app, db, monitor

if __name__ == '__main__':
    # Создаем таблицы базы данных
    with app.app_context():
        db.create_all()
        print("База данных инициализирована")
    
    # Запускаем приложение
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"Запускаем PlaylistChecker на порту {port}")
    print("Откройте http://localhost:5000 в браузере")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
