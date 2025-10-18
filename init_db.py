#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных PlaylistChecker
"""

from app import app, db, User, monitor
from werkzeug.security import generate_password_hash


def init_database():
    """Инициализация базы данных"""
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        print("Таблицы базы данных созданы")
        
        # Создаем администратора по умолчанию
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@playlistchecker.com',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
            print("Создан пользователь-администратор: admin / admin123")
        else:
            print("Пользователь-администратор уже существует")
        
        print("База данных инициализирована успешно!")

if __name__ == '__main__':
    init_database()
