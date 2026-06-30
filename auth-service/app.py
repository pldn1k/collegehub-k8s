from flask import Flask, request, jsonify, Response
import jwt
import datetime
import os
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import wraps
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time

app = Flask(__name__)

# Метрики
REQUEST_COUNT = Counter('auth_http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('auth_http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])

# Middleware для метрик
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if request.path != '/metrics':
        if hasattr(request, 'start_time'):
            latency = time.time() - request.start_time
            REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(latency)
        REQUEST_COUNT.labels(method=request.method, endpoint=request.path, status=response.status_code).inc()
    return response

# Конфигурация
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET', 'dev-secret-key-change-me')

# Подключение к Redis
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6382)),
    db=0,
    decode_responses=True
)

# Подключение к PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', 'postgres'),
        port=int(os.environ.get('POSTGRES_PORT', 5432)),
        database=os.environ.get('POSTGRES_DB', 'collegehub'),
        user=os.environ.get('POSTGRES_USER', 'postgres'),
        password=os.environ.get('POSTGRES_PASSWORD', 'postgres123')
    )

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Токен отсутствует!'}), 401
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id, username, name, role FROM users WHERE username = %s", (data['username'],))
            current_user = cur.fetchone()
            cur.close()
            conn.close()
            
            if not current_user:
                return jsonify({'message': 'Пользователь не найден!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Токен истёк!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Неверный токен!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'auth-service'})

@app.route('/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, username, password, name, role FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or user['password'] != password:
        return jsonify({'message': 'Неверные учетные данные'}), 401

    token = jwt.encode({
        'username': user['username'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    redis_client.setex(f"session:{username}", 86400, token)

    return jsonify({
        'token': token,
        'user': {
            'username': user['username'],
            'name': user['name'],
            'role': user['role']
        }
    })

@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify(current_user):
    return jsonify({
        'valid': True,
        'user': {
            'username': current_user['username'],
            'name': current_user['name'],
            'role': current_user['role']
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout(current_user):
    redis_client.delete(f"session:{current_user['username']}")
    return jsonify({'message': 'Выход выполнен успешно'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
