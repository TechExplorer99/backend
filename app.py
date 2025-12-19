from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import text
from flasgger import Swagger, swag_from
import os

# Инициализация Flask приложения
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Конфигурация базы данных
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Конфигурация Swagger
app.config['SWAGGER'] = {
    'title': 'My Login App API',
    'uiversion': 3
}
swagger = Swagger(app)

# Инициализация SQLAlchemy
db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

# Создание таблиц (инициализация БД)
def create_tables():
    try:
        db.create_all()
        print("✅ Таблицы базы данных созданы")
        
        # Создаем тестового админа, если его нет
        admin_exists = User.query.filter_by(username='admin').first()
        if not admin_exists:
            admin = User(
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            
            # Создаем тестового пользователя
            test_user = User(
                username='user',
                email='user@example.com',
                password=generate_password_hash('password'),
                role='user'
            )
            db.session.add(test_user)
            
            db.session.commit()
            print("✅ Тестовые пользователи созданы")
            
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        db.session.rollback()

# Главная страница
@app.route('/')
def home():
    return jsonify({
        "message": "Backend для приложения входа работает! 🚀",
        "status": "online",
        "database": "SQLite",
        "endpoints": [
            "/api/health",
            "/api/register",
            "/api/login",
            "/api/users",
            "/api/users/<id>"
        ]
    })

# Проверка здоровья
@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Проверка состояния сервера и подключения к базе данных.
    ---
    tags:
      - Health
    responses:
      200:
        description: Статус сервера и базы данных
        schema:
          type: object
          properties:
            status:
              type: string
            message:
              type: string
            database:
              type: string
            timestamp:
              type: string
              format: date-time
    """
    try:
        # В SQLAlchemy 2.x нужно оборачивать сырой SQL в text()
        db.session.execute(text('SELECT 1'))
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return jsonify({
        "status": "ok",
        "message": "Backend работает",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    })

# Регистрация
@app.route('/api/register', methods=['POST'])
@swag_from({
    'tags': ['Auth'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'email', 'password'],
                'properties': {
                    'username': {'type': 'string'},
                    'email': {'type': 'string'},
                    'password': {'type': 'string', 'minLength': 6}
                }
            }
        }
    ],
    'responses': {
        201: {'description': 'Пользователь создан'},
        400: {'description': 'Ошибка валидации'}
    }
})
def register():
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        if len(password) < 6:
            return jsonify({'error': 'Пароль должен быть не менее 6 символов'}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Пользователь с таким именем уже существует'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Пользователь с таким email уже существует'}), 400
        
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role='user'
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Регистрация успешна!',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

# Вход
@app.route('/api/login', methods=['POST'])
@swag_from({
    'tags': ['Auth'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'password'],
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': 'Успешный вход'},
        401: {'description': 'Неверные учетные данные'}
    }
})
def login():
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        identifier = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not identifier or not password:
            return jsonify({'error': 'Введите логин и пароль'}), 400
        
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        if not check_password_hash(user.password, password):
            return jsonify({'error': 'Неверный пароль'}), 401
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Вход выполнен успешно',
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

# Получить всех пользователей
@swag_from({
    'tags': ['Users'],
    'responses': {
        200: {
            'description': 'Успешное получение списка пользователей',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'count': {'type': 'integer'},
                    'users': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'username': {'type': 'string'},
                                'email': {'type': 'string'},
                                'role': {'type': 'string'},
                                'created_at': {'type': 'string'},
                                'updated_at': {'type': 'string'},
                            },
                        },
                    },
                },
            },
        },
        500: {
            'description': 'Ошибка сервера',
        },
    },
})
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        users_list = [user.to_dict() for user in users]
        
        return jsonify({
            'success': True,
            'count': len(users_list),
            'users': users_list
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

# Получить одного пользователя
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Получить пользователя по ID
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Данные пользователя
      404:
        description: Пользователь не найден
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

# Обновить пользователя
@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Нет данных для обновления'}), 400
        
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        updated = False
        
        if 'username' in data and data['username']:
            new_username = data['username'].strip()
            if new_username != user.username:
                existing = User.query.filter_by(username=new_username).first()
                if existing and existing.id != user_id:
                    return jsonify({'error': 'Имя пользователя уже занято'}), 400
                user.username = new_username
                updated = True
        
        if 'email' in data and data['email']:
            new_email = data['email'].strip().lower()
            if new_email != user.email:
                existing = User.query.filter_by(email=new_email).first()
                if existing and existing.id != user_id:
                    return jsonify({'error': 'Email уже используется'}), 400
                user.email = new_email
                updated = True
        
        if 'password' in data and data['password']:
            new_password = data['password']
            if len(new_password) < 6:
                return jsonify({'error': 'Пароль должен быть не менее 6 символов'}), 400
            user.password = generate_password_hash(new_password)
            updated = True
        
        if 'role' in data and data['role'] in ['user', 'admin']:
            user.role = data['role']
            updated = True
        
        if updated:
            user.updated_at = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Данные пользователя обновлены',
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

# Удалить пользователя
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({'error': 'Нельзя удалить последнего администратора'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Пользователь удален',
            'deleted_user_id': user_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

# Поиск пользователей
@app.route('/api/users/search', methods=['GET'])
def search_users():
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({'error': 'Пустой поисковый запрос'}), 400
        
        users = User.query.filter(
            (User.username.ilike(f'%{query}%')) | 
            (User.email.ilike(f'%{query}%'))
        ).limit(20).all()
        
        users_list = [user.to_dict() for user in users]
        
        return jsonify({
            'success': True,
            'count': len(users_list),
            'users': users_list
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

# Статистика
@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_users = User.query.count()
        admin_users = User.query.filter_by(role='admin').count()
        regular_users = User.query.filter_by(role='user').count()
        
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'admin_users': admin_users,
                'regular_users': regular_users,
                'recent_users': [user.to_dict() for user in recent_users]
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

# Обработчики ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ресурс не найден'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    # Инициализируем базу данных и создаем тестовые записи
    with app.app_context():
        create_tables()
    
    print("\n" + "="*50)
    print("🚀 Запуск backend сервера с SQLite базой данных")
    print("="*50)
    print("📊 База данных: SQLite (users.db)")
    print("🔗 URL: http://localhost:3001")
    print("📖 Swagger Docs: http://localhost:3001/apidocs/")
    print("🔧 API доступно по: http://localhost:3001/api/")
    print("👥 Тестовые аккаунты:")
    print("   • admin / admin123 (администратор)")
    print("   • user / password (обычный пользователь)")
    print("="*50 + "\n")
    
    app.run(debug=True, port=3001, use_reloader=False)