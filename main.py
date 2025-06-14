from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return 'Сервер работает. Иди на /api/test'

@app.route('/api/test')
def api_test():
    data = {
        'id': 1,
        'message': 'Это мой первый, сука, JSON ответ!',
        'status': 'success'
    }
    return jsonify(data)
