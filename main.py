import os
from flask import Flask, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

# --- Инициализация ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_you_should_change')

db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='eventlet')
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Глобальный словарь для отслеживания онлайн-пользователей { sid: username } ---
online_users = {}

# --- Модели Базы Данных ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    messages = db.relationship('Message', backref='author', lazy=True)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- HTML-ШАБЛОН ---
HTML_TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чат с юзерами</title>
    <style>
        body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; height: 100vh; background: #23272a; color: #fff; }
        .sidebar { width: 200px; background: #2c2f33; padding: 10px; border-right: 1px solid #23272a; display: flex; flex-direction: column; }
        .sidebar h3 { margin-top: 0; font-size: 1.1em; }
        #user-list { list-style-type: none; padding: 0; margin: 0; }
        #user-list li { padding: 5px; color: #99aab5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .sidebar-footer { margin-top: auto; font-size: 0.9em; }
        .sidebar-footer a { color: #7289da; text-decoration: none; }
        .main-content { flex-grow: 1; display: flex; flex-direction: column; }
        .chat-window { flex-grow: 1; padding: 10px; overflow-y: auto; }
        #messages { list-style-type: none; margin: 0; padding: 0; }
        .message-container { margin-bottom: 10px; }
        .message { display: inline-block; padding: 10px; border-radius: 15px; max-width: 70%; word-wrap: break-word; }
        .message .author { font-weight: bold; margin-bottom: 5px; }
        .message.other { background: #40444b; }
        .message.other .author { color: #58f286; }
        .message.mine { background: #7289da; }
        .message.mine .author { display: none; }
        .message-container.mine { text-align: right; }
        .notification { text-align: center; color: #99aab5; font-style: italic; font-size: 0.9em; padding: 5px; }
        #form { padding: 10px; background: #2c2f33; display: flex; }
        #input { flex-grow: 1; padding: 10px; border: none; border-radius: 20px; background: #40444b; color: #fff; }
        #input:focus { outline: none; }
        #form button { background: #7289da; border: none; padding: 10px 15px; margin-left: 10px; border-radius: 20px; color: #fff; }
        .auth-container { width: 100%; display: flex; align-items: center; justify-content: center; }
        .auth-form { padding: 20px; max-width: 300px; background: #2c2f33; border-radius: 5px; }
        .auth-form input { width: 100%; padding: 10px; margin-bottom: 10px; box-sizing: border-box; border-radius: 3px; border: 1px solid #23272a; background: #40444b; color: #fff; }
        .auth-form button { width: 100%; padding: 10px; border: none; border-radius: 3px; background: #7289da; color: #fff; }
        .auth-form p { font-size: 0.9em; text-align: center; }
        .auth-form a { color: #7289da; }
    </style>
</head>
<body>
    {% if current_user.is_authenticated %}
    <div class="sidebar">
        <h3>Онлайн (<span id="user-count">0</span>):</h3>
        <ul id="user-list"></ul>
        <div class="sidebar-footer">
            <p>{{ current_user.username }}<br><a href="/logout">Выйти</a></p>
        </div>
    </div>
    <div class="main-content">
        <div class="chat-window" id="chat-window">
            <ul id="messages">
            {% for message in messages %}
                <li class="message-container {% if message.author.id == current_user.id %}mine{% endif %}">
                    <div class="message {% if message.author.id == current_user.id %}mine{% else %}other{% endif %}">
                        <div class="author">{{ message.author.username }}</div>
                        <div>{{ message.text }}</div>
                    </div>
                </li>
            {% endfor %}
            </ul>
        </div>
        <form id="form" action=""><input id="input" autocomplete="off" placeholder="Сообщение..." /><button type="submit">Send</button></form>
    </div>
    {% else %}
        <div class="auth-container">
            <div class="auth-form">
                <h2>{{ form_title }}</h2>
                <form method="post">
                    <input type="text" name="username" placeholder="Имя пользователя" required>
                    <input type="password" name="password" placeholder="Пароль" required>
                    <button type="submit">{{ button_text }}</button>
                </form>
                <p>{{ switch_text }} <a href="{{ switch_url }}">{{ switch_link_text }}</a></p>
            </div>
        </div>
    {% endif %}

    {% if current_user.is_authenticated %}
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const socket = io();
            const messages = document.getElementById('messages');
            const userList = document.getElementById('user-list');
            const userCount = document.getElementById('user-count');
            const chatWindow = document.getElementById('chat-window');
            const currentUserId = {{ current_user.id }};
            const currentUsername = "{{ current_user.username }}";
            
            const scrollToBottom = () => { chatWindow.scrollTop = chatWindow.scrollHeight; };
            scrollToBottom();

            socket.on('connect', () => { socket.emit('user_joined', { username: currentUsername }); });

            socket.on('update_user_list', (users) => {
                userList.innerHTML = '';
                userCount.textContent = users.length;
                users.forEach(user => {
                    const item = document.createElement('li');
                    item.textContent = user;
                    userList.appendChild(item);
                });
            });

            socket.on('user_status', (data) => {
                const item = document.createElement('li');
                item.className = 'notification';
                item.textContent = `${data.username} ${data.status}`;
                messages.appendChild(item);
                scrollToBottom();
            });

            socket.on('new_message', (msg) => {
                const li = document.createElement('li');
                li.className = 'message-container' + (msg.user_id === currentUserId ? ' mine' : '');
                
                const div = document.createElement('div');
                div.className = 'message' + (msg.user_id === currentUserId ? ' mine' : ' other');
                
                const authorDiv = document.createElement('div');
                authorDiv.className = 'author';
                authorDiv.textContent = msg.username;
                
                const textDiv = document.createElement('div');
                textDiv.textContent = msg.text;
                
                div.appendChild(authorDiv);
                div.appendChild(textDiv);
                li.appendChild(div);
                messages.appendChild(li);
                scrollToBottom();
            });
            
            document.getElementById('form').addEventListener('submit', (e) => {
                e.preventDefault();
                const input = document.getElementById('input');
                if (input.value.trim()) {
                    socket.emit('send_message', { 'text': input.value });
                    input.value = '';
                }
            });
        });
    </script>
    {% endif %}
</body>
</html>
"""

# --- Роуты ---

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
            return redirect(url_for('login'))
        login_user(user, remember=True)
        return redirect(url_for('home'))
    return render_template_string(HTML_TEMPLATE, form_title="Вход", button_text="Войти", switch_text="Нет аккаунта?", switch_url=url_for('register'), switch_link_text="Регистрация")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            return redirect(url_for('register'))
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

@socketio.on('user_joined')
@login_required
def handle_user_joined(data):
    sid = request.sid
    username = current_user.username
    online_users[sid] = username
    emit('update_user_list', list(online_users.values()), broadcast=True)
    emit('user_status', {'username': username, 'status': 'присоединился'}, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in online_users:
        username = online_users.pop(sid)
        emit('update_user_list', list(online_users.values()), broadcast=True)
        emit('user_status', {'username': username, 'status': 'отключился'}, broadcast=True)

@socketio.on('send_message')
@login_required
def handle_send_message_event(data):
    if 'text' in data and data['text'].strip():
        msg = Message(text=data['text'], author=current_user)
        db.session.add(msg)
        db.session.commit()
        emit('new_message', {
            'text': msg.text, 
            'username': current_user.username,
            'user_id': current_user.id
            }, broadcast=True)

# --- Запуск ---
if __name__ == '__main__':
    socketio.run(app)
