#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import db, app, User
from werkzeug.security import generate_password_hash

def init_database():
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        print("✅ Таблицы созданы")
        
        # Проверяем, есть ли уже пользователи
        if User.query.count() == 0:
            # Создаем администратора
            admin = User(
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            
            # Создаем тестового пользователя
            user = User(
                username='user',
                email='user@example.com',
                password=generate_password_hash('password'),
                role='user'
            )
            db.session.add(user)
            
            db.session.commit()
            print("✅ Тестовые пользователи созданы")
        
        total = User.query.count()
        admins = User.query.filter_by(role='admin').count()
        print(f"📊 Всего пользователей: {total}")
        print(f"👑 Администраторов: {admins}")
        print("✅ База данных готова к работе!")

if __name__ == '__main__':
    init_database()