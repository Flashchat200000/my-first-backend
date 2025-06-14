import os
from flask import Flask, jsonify, request, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Настройки базы данных (ничего не меняется) ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)

# --- Модель для сообщений (ничего не меняется) ---
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)

    def to_dict(self):
        return {'id': self.id, 'text': self.text}

# --- Создание таблицы (ничего не меняется) ---
with app.app_context():
    db.create_all()

# --- HTML-шаблон для нашей уродливой формы ---
# Мы вставляем его прямо сюда, чтобы не создавать лишние файлы
HTML_TEMPLATE = """
<!doctype html>
<title>Мой первый CRUD</title>
<h1>Добавить новое сообщение:</h1>
<form method=post action="/add">
  <input type=text name=text size=50>
  <input type=submit value="Добавить">
</form>
<hr>
<h1>Все сообщения в базе:</h1>
<ul>
{% for message in messages %}
  <li>{{ message.text }} (id: {{ message.id }})</li>
{% endfor %}
</ul>
"""

# --- ГЛАВНАЯ СТРАНИЦА: теперь она показывает форму и сообщения ---
@app.route('/', methods=['GET'])
def home():
    # Получаем все сообщения из базы
    messages = Message.query.all()
    # Показываем нашу HTML-страницу, передавая в нее список сообщений
    return render_template_string(HTML_TEMPLATE, messages=messages)

# --- РОУТ ДЛЯ ДОБАВЛЕНИЯ: теперь он принимает данные из формы ---
@app.route('/add', methods=['POST'])
def add_message():
    # Получаем текст из поля 'text' нашей HTML-формы
    text_from_form = request.form.get('text')
    if not text_from_form:
        return "Ошибка: текст не может быть пустым", 400

    new_msg = Message(text=text_from_form)
    db.session.add(new_msg)
    db.session.commit()
    # После добавления, перенаправляем пользователя обратно на главную страницу
    return redirect(url_for('home'))

# --- API РОУТЫ (оставляем их, вдруг пригодятся) ---
@app.route('/api/messages')
def get_messages_api():
    messages = Message.query.all()
    return jsonify([msg.to_dict() for msg in messages])
