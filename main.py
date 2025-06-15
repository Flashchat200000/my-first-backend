import os
from flask import Flask, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit # ДОБАВИЛИ

app = Flask(__name__)
# Настройки как и были
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("://", "ql://", 1) # ВАЖНЫЙ ФИКС ДЛЯ RENDER
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app) # ДОБАВИЛИ

# Модель как и была
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)

# Таблицу создаем так же
with app.app_context():
    db.create_all()

# HTML-шаблон. ВНИМАНИЕ: МЫ ЕГО СЕЙЧАС СИЛЬНО ИЗМЕНИМ
HTML_TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Флеш-чат 200000</title>
    <style>
        body { font-family: sans-serif; background: #222; color: #eee; }
        #messages { list-style-type: none; margin: 0; padding: 0; }
        #messages li { padding: 5px 10px; }
        #messages li:nth-child(odd) { background: #333; }
        #form { background: #444; padding: 10px; position: fixed; bottom: 0; width: 100%; }
        #input { border: 1px solid #555; background: #222; color: #eee; padding: 10px; width: 80%; }
        #form button { width: 18%; background: #0a0; border: none; padding: 10px; }
    </style>
</head>
<body>
    <ul id="messages">
    {% for message in messages %}
        <li>{{ message.text }}</li>
    {% endfor %}
    </ul>

    <form id="form" action="">
        <input id="input" autocomplete="off" /><button>Отправить</button>
    </form>

    <!-- Подключаем клиент Socket.IO -->
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <script>
        // Устанавливаем соединение
        const socket = io();

        const messages = document.getElementById('messages');
        const form = document.getElementById('form');
        const input = document.getElementById('input');

        // Отправляем сообщение на сервер
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // чтобы страница не перезагружалась
            if (input.value) {
                socket.emit('send_message', { 'text': input.value });
                input.value = '';
            }
        });

        // Получаем сообщение от сервера и добавляем его в список
        socket.on('new_message', function(msg) {
            const item = document.createElement('li');
            item.textContent = msg.text;
            messages.appendChild(item);
            window.scrollTo(0, document.body.scrollHeight);
        });
    </script>
</body>
</html>
"""

# Главная страница теперь просто отдает HTML с уже имеющимися сообщениями
@app.route('/')
def home():
    messages = Message.query.order_by(Message.id).all()
    return render_template_string(HTML_TEMPLATE, messages=messages)

# Слушаем событие 'send_message' от клиента
@socketio.on('send_message')
def handle_send_message_event(data):
    # Сохраняем сообщение в базу
    new_msg = Message(text=data['text'])
    db.session.add(new_msg)
    db.session.commit()
    # Отправляем НОВОЕ сообщение ВСЕМ подключенным клиентам
    emit('new_message', {'text': new_msg.text}, broadcast=True)

# Этот код больше не нужен, удаляем его нахуй:
# @app.route('/add', methods=['POST']) ...
# @app.route('/api/messages') ...

# ЗАПУСКАТЬ ТЕПЕРЬ НУЖНО ТАК, ЧЕРЕЗ SOCKETIO
if __name__ == '__main__':
    socketio.run(app)
