import os
from flask import Flask, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

# --- Инициализация всего дерьма ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_you_should_change')

# Фикс для Render
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='eventlet')
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Куда кидать анонимов

# --- Модели Базы Данных ---

# UserMixin дает нам готовые поля типа is_authenticated
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    messages = db.relationship('Message', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Загрузчик пользователя для Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Создаем таблицы ---
with app.app_context():
    db.create_all()

# --- ЕБАНЫЙ HTML-ШАБЛОН. ОН СТАЛ ЕЩЕ БОЛЬШЕ ---
HTML_TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Авторизованный чат</title>
    <style>
        body { margin: 0; padding-bottom: 3rem; font-family: sans-serif; background: #2c2f33; color: #ffffff; }
        .message-container { display: flex; flex-direction: column; }
        .message { background: #40444b; margin: 5px; padding: 10px; border-radius: 10px; max-width: 70%; }
        .message .author { font-weight: bold; color: #7289da; }
        .message.mine { align-self: flex-end; background: #7289da; }
        .message.mine .author { color: #ffffff; }
        #messages { list-style-type: none; margin: 0; padding: 10px; }
        #form { background: rgba(0,0,0,0.15); padding: 0.25rem; position: fixed; bottom: 0; left: 0; right: 0; display: flex; height: 3rem; }
        #input { border: none; padding: 0 1rem; flex-grow: 1; border-radius: 2rem; margin: 0.25rem; background: #40444b; color: #fff; }
        #input:focus { outline: none; }
        #form button { background: #7289da; border: none; padding: 0 1rem; margin: 0.25rem; border-radius: 2rem; color: #fff; }
        .auth-form { padding: 20px; max-width: 300px; margin: 50px auto; background: #23272a; border-radius: 5px; }
        .auth-form input { width: 100%; padding: 10px; margin-bottom: 10px; box-sizing: border-box; }
    </style>
</head>
<body>
    {% if current_user.is_authenticated %}
        <div style="padding:10px; background: #23272a;">
            Привет, {{ current_user.username }}! <a href="/logout">Выйти</a>
        </div>
        <ul id="messages">
        {% for message in messages %}
            <li class="message-container">
                <div class="message {% if message.author.id == current_user.id %}mine{% endif %}">
                    <div class="author">{{ message.author.username }}</div>
                    <div>{{ message.text }}</div>
                </div>
            </li>
        {% endfor %}
        </ul>
        <form id="form" action="">
            <input id="input" autocomplete="off" /><button>Отправить</button>
        </form>
    {% else %}
        <div class="auth-form">
            <h2>{{ form_title }}</h2>
            <form method="post">
                <input type="text" name="username" placeholder="Имя пользователя" required>
                <input type="password" name="password" placeholder="Пароль" required>
                <button type="submit">{{ button_text }}</button>
            </form>
            <p>{{ switch_text }} <a href="{{ switch_url }}">{{ switch_link_text }}</a></p>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <ul class=flashes>
                    {% for message in messages %}
                        <li>{{ message }}</li>
                    {% endfor %}
                    </ul>
                {% endif %}
            {% endwith %}
        </div>
    {% endif %}

    {% if current_user.is_authenticated %}
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', (event) => {
            const socket = io();
            const messages = document.getElementById('messages');
            const form = document.getElementById('form');
            const input = document.getElementById('input');
            const currentUserId = {{ current_user.id }};

            window.scrollTo(0, document.body.scrollHeight);

            form.addEventListener('submit', function(e) {
                e.preventDefault();
                if (input.value) {
                    socket.emit('send_message', { 'text': input.value });
                    input.value = '';
                }
            });

            socket.on('new_message', function(msg) {
                const li = document.createElement('li');
                li.classList.add('message-container');
                
                const div = document.createElement('div');
                div.classList.add('message');
                if (msg.user_id === currentUserId) {
                    div.classList.add('mine');
                }

                const authorDiv = document.createElement('div');
                authorDiv.classList.add('author');
                authorDiv.textContent = msg.username;

                const textDiv = document.createElement('div');
                textDiv.textContent = msg.text;

                div.appendChild(authorDiv);
                div.appendChild(textDiv);
                li.appendChild(div);
                messages.appendChild(li);
                window.scrollTo(0, document.body.scrollHeight);
            });
        });
    </script>
    {% endif %}
</body>
</html>
"""

# --- Роуты для чата, логина, регистрации ---

@app.route('/')
@login_required
def home():
    messages = Message.query.order_by(Message.id.asc()).limit(100).all()
    return render_template_string(HTML_TEMPLATE, messages=messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user is None or not user.check_password(request.form['password']):
            return redirect(url_for('login')) # Тут надо бы сообщение об ошибке, но похуй
        login_user(user, remember=True)
        return redirect(url_for('home'))
    return render_template_string(HTML_TEMPLATE, form_title="Вход", button_text="Войти", switch_text="Нет аккаунта?", switch_url=url_for('register'), switch_link_text="Регистрация")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            return redirect(url_for('register')) # Юзер уже есть, но мы ему не скажем
        user = User(username=request.form['username'])
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        return redirect(url_for('home'))
    return render_template_string(HTML_TEMPLATE, form_title="Регистрация", button_text="Зарегистрироваться", switch_text="Уже есть аккаунт?", switch_url=url_for('login'), switch_link_text="Войти")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Обработчики сокетов ---

@socketio.on('send_message')
@login_required # Только залогиненные могут слать сообщения
def handle_send_message_event(data):
    if 'text' in data and data['text'].strip() != '':
        msg = Message(text=data['text'], author=current_user)
        db.session.add(msg)
        db.session.commit()
        emit('new_message', {
            'text': msg.text, 
            'username': current_user.username,
            'user_id': current_user.id
            }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)
