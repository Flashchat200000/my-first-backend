import os
from flask import Flask, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit

# --- Инициализация ---
app = Flask(__name__)
# ВАЖНЫЙ ФИКС ДЛЯ RENDER. ОН ЛОМАЕТСЯ БЕЗ ЭТОГО.
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
    
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)
# async_mode='eventlet' важен для gunicorn
socketio = SocketIO(app, async_mode='eventlet')

# --- Модель базы данных ---
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)

# --- Создаем таблицы, если их нет ---
with app.app_context():
    db.create_all()

# --- HTML-шаблон с JavaScript ---
HTML_TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Флеш-чат 200000</title>
    <style>
        body { margin: 0; padding-bottom: 3rem; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #2c2f33; color: #ffffff; }
        #messages { list-style-type: none; margin: 0; padding: 0; }
        #messages li { padding: 0.5rem 1rem; }
        #messages li:nth-child(odd) { background: #23272a; }
        #form { background: rgba(0, 0, 0, 0.15); padding: 0.25rem; position: fixed; bottom: 0; left: 0; right: 0; display: flex; height: 3rem; box-sizing: border-box; backdrop-filter: blur(10px); }
        #input { border: none; padding: 0 1rem; flex-grow: 1; border-radius: 2rem; margin: 0.25rem; background: #40444b; color: #ffffff; }
        #input:focus { outline: none; }
        #form button { background: #7289da; border: none; padding: 0 1rem; margin: 0.25rem; border-radius: 2rem; outline: none; color: #ffffff; }
    </style>
</head>
<body>
    <ul id="messages">
    {% for message in messages %}
        <li>{{ message.text }}</li>
    {% endfor %}
    </ul>

    <form id="form" action="">
        <input id="input" autocomplete="off" placeholder="Введите сообщение..." /><button>Отправить</button>
    </form>

    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', (event) => {
            const socket = io();

            const messages = document.getElementById('messages');
            const form = document.getElementById('form');
            const input = document.getElementById('input');

            // Скролл вниз при загрузке
            window.scrollTo(0, document.body.scrollHeight);

            form.addEventListener('submit', function(e) {
                e.preventDefault();
                if (input.value) {
                    socket.emit('send_message', { 'text': input.value });
                    input.value = '';
                }
            });

            socket.on('new_message', function(msg) {
                const item = document.createElement('li');
                item.textContent = msg.text;
                messages.appendChild(item);
                window.scrollTo(0, document.body.scrollHeight);
            });
        });
    </script>
</body>
</html>
"""

# --- Роуты и обработчики ---

@app.route('/')
def home():
    # Просто отдаем страницу с последними 50 сообщениями
    messages = Message.query.order_by(Message.id.desc()).limit(50).all()
    messages.reverse() # чтобы новые были внизу
    return render_template_string(HTML_TEMPLATE, messages=messages)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('send_message')
def handle_send_message_event(data):
    if 'text' in data and data['text'].strip() != '':
        print(f"Received message: {data['text']}")
        # Сохраняем в базу
        new_msg = Message(text=data['text'])
        db.session.add(new_msg)
        db.session.commit()
        # Отправляем всем, включая отправителя
        emit('new_message', {'text': new_msg.text}, broadcast=True)

# Этот блок для локального запуска, на Render он не используется
if __name__ == '__main__':
    socketio.run(app, debug=True)
