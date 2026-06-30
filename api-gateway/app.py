from flask import Flask, request, jsonify, Response
import requests
import os
from functools import wraps

app = Flask(__name__)

AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8001')

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return '', 200

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Требуется авторизация'}), 401
        try:
            response = requests.get(
                f"{AUTH_SERVICE_URL}/api/auth/verify",
                headers={'Authorization': token}
            )
            if response.status_code != 200:
                return jsonify({'error': 'Неверный токен!'}), 401
            user_data = response.json()
            request.user = user_data['user']
        except Exception as e:
            return jsonify({'error': f'Ошибка авторизации: {str(e)}'}), 500
        return f(*args, **kwargs)
    return decorated

@app.route('/api/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy_auth(path):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = f"{AUTH_SERVICE_URL}/api/auth/{path}"
        response = requests.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers if k.lower() != 'host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        return jsonify({'error': f'Ошибка прокси: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'api-gateway'})

@app.route('/api/grades', methods=['GET'])
@require_auth
def get_grades():
    user = request.user
    if user['role'] == 'student':
        grades = [
            {'subject': 'Математика', 'grade': 5, 'date': '2026-01-15'},
            {'subject': 'Физика', 'grade': 4, 'date': '2026-01-20'},
            {'subject': 'Программирование', 'grade': 5, 'date': '2026-01-25'}
        ]
    else:
        grades = [
            {'student': 'Паша Техник', 'subject': 'Математика', 'grade': 5},
            {'student': 'Паша Техник', 'subject': 'Физика', 'grade': 4},
            {'student': 'Марат Скоропортов', 'subject': 'Математика', 'grade': 4}
        ]
    return jsonify({'grades': grades, 'user': user})

@app.route('/api/schedule', methods=['GET'])
@require_auth
def get_schedule():
    schedule = [
        {'day': 'Понедельник', 'time': '10:00', 'subject': 'Математика', 'room': 101},
        {'day': 'Понедельник', 'time': '12:00', 'subject': 'Физика', 'room': 203},
        {'day': 'Вторник', 'time': '10:00', 'subject': 'Программирование', 'room': 305},
        {'day': 'Вторник', 'time': '14:00', 'subject': 'Английский', 'room': 107},
    ]
    return jsonify({'schedule': schedule})

@app.route('/api/news', methods=['GET'])
def get_news():
    news = [
        {'title': 'День открытых дверей', 'date': '2026-03-15', 'content': 'Приглашаем всех желающих!'},
        {'title': 'Олимпиада по программированию', 'date': '2026-03-20', 'content': 'Регистрация открыта'},
        {'title': 'Каникулы', 'date': '2026-03-25', 'content': 'Весенние каникулы с 25 марта по 1 апреля'}
    ]
    return jsonify({'news': news})
    
@app.route('/metrics', methods=['GET'])
def metrics():
    # Простые текстовые метрики для Prometheus
    import psutil
    import time
    metrics_text = ""
    
    # CPU
    metrics_text += f"# HELP api_gateway_cpu_usage CPU usage in percent\n"
    metrics_text += f"# TYPE api_gateway_cpu_usage gauge\n"
    metrics_text += f"api_gateway_cpu_usage {psutil.cpu_percent()}\n"
    
    # Memory
    mem = psutil.virtual_memory()
    metrics_text += f"# HELP api_gateway_memory_usage Memory usage in bytes\n"
    metrics_text += f"# TYPE api_gateway_memory_usage gauge\n"
    metrics_text += f"api_gateway_memory_usage {mem.used}\n"
    
    # Uptime (можно добавить)
    if not hasattr(metrics, 'start_time'):
        metrics.start_time = time.time()
    uptime = time.time() - metrics.start_time
    metrics_text += f"# HELP api_gateway_uptime_seconds Uptime in seconds\n"
    metrics_text += f"# TYPE api_gateway_uptime_seconds counter\n"
    metrics_text += f"api_gateway_uptime_seconds {uptime}\n"
    
    return Response(metrics_text, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

