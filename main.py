import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Подключаемся к базе данных по ссылке из настроек окружения
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False # Чтобы кириллица была кириллицей

db = SQLAlchemy(app)

# Описываем, как будет выглядеть таблица для сообщений
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text
        }

# Эта команда создает таблицу в базе, если ее еще нет
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return 'Сервер с базой данных работает. Теперь есть /add и /messages'

# Новый роут для добавления сообщения
@app.route('/add', methods=['POST'])
def add_message():
    # Получаем JSON из тела запроса
    data = request.get_json()
    if not data or not 'text' in data:
        return jsonify({'error': 'Нет текста в запросе'}), 400

    new_msg = Message(text=data['text'])
    db.session.add(new_msg)
    db.session.commit()
    return jsonify({'message': 'Сообщение добавлено!', 'id': new_msg.id}), 201

# Новый роут для получения всех сообщений
@app.route('/messages')
def get_messages():
    messages = Message.query.all()
    return jsonify([msg.to_dict() for msg in messages])
