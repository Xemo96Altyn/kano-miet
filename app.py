import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import abort

# Импорты твоего существующего ядра (оставляем как было)
from kano_core.io import load_survey, save_survey
from kano_core.models import KanoSurvey
from kano_core.service import analyze_kano_payload
from kano_core.validation import KanoValidationError

# Импорт моделей БД
from kano_automatization.models import db, User, SurveyMeta

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "webui"
SURVEYS_DIR = BASE_DIR / "surveys"
RESPONSES_DIR = BASE_DIR / "responses"

# Инициализация Flask (указываем webui как папку со статикой)
app = Flask(__name__, static_folder=str(WEB_DIR))
app.config['SECRET_KEY'] = 'super-secret-key-kano-123' # Секретный ключ для сессий
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kano.db' # Файл БД появится в корне
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация плагинов
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'serve_login' # Куда кидать неавторизованных

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Декоратор для защиты админских маршрутов
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({"error": "Доступ запрещен. Вы не администратор."}), 403
        return f(*args, **kwargs)
    return decorated_function
# Создаем таблицы при первом запуске
with app.app_context():
    db.create_all()

# ==========================================
# 1. МАРШРУТЫ HTML СТРАНИЦ (Отдача файлов)
# ==========================================

@app.route('/')
def serve_index():
    return send_from_directory(WEB_DIR, 'index.html') # Теперь это будет login.html

@app.route('/home')
@login_required # Защита! Без логина сюда не попасть
def serve_home():
    return send_from_directory(WEB_DIR, 'home.html')

@app.route('/builder')
@login_required
def serve_builder():
    return send_from_directory(WEB_DIR, 'builder.html')

@app.route('/dashboard')
@app.route('/dashboard/<survey_id>')
@login_required
def serve_dashboard(survey_id=None):
    return send_from_directory(WEB_DIR, 'dashboard.html')

@app.route('/survey/<survey_id>')
def serve_survey(survey_id):
    # Публичный доступ для респондентов!
    return send_from_directory(WEB_DIR, 'survey.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(WEB_DIR, filename)

@app.route('/register')
def serve_register():
    return send_from_directory(WEB_DIR, 'register.html')

@app.route('/admin')
@login_required
@admin_required
def serve_admin():
    return send_from_directory(WEB_DIR, 'admin_panel.html')
# ==========================================
# 2. МАРШРУТЫ АВТОРИЗАЦИИ (API)
# ==========================================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if user and check_password_hash(user.password_hash, data.get('password')):
        login_user(user)
        return jsonify({"status": "ok", "role": user.role})
    return jsonify({"error": "Неверный логин или пароль"}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({"error": "Пользователь уже существует"}), 400
    
    new_user = User(
        username=data.get('username'),
        password_hash=generate_password_hash(data.get('password')),
        full_name=data.get('full_name'),
        role='organizer' # По умолчанию все организаторы
    )
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return jsonify({"status": "created"}), 201

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({"status": "ok"})

@app.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def api_get_users():
    users = User.query.all()
    # Считаем, сколько опросов у каждого
    result = []
    for u in users:
        surveys_count = SurveyMeta.query.filter_by(user_id=u.id).count()
        result.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "surveys_count": surveys_count
        })
    return jsonify(result)

@app.route('/api/admin/role', methods=['POST'])
@login_required
@admin_required
def api_change_role():
    data = request.json
    user = User.query.get(data.get('user_id'))
    if user:
        user.role = data.get('role')
        db.session.commit()
        return jsonify({"status": "ok"})
    return jsonify({"error": "Пользователь не найден"}), 404

@app.route('/api/admin/delete_user', methods=['POST'])
@login_required
@admin_required
def api_delete_user():
    user_id = request.json.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404
    
    if user.id == current_user.id:
        return jsonify({"error": "Нельзя удалить самого себя"}), 400

    # Удаляем все опросы этого пользователя из БД
    user_surveys = SurveyMeta.query.filter_by(user_id=user.id).all()
    for meta in user_surveys:
        # Физически удаляем JSON файлы
        try:
            if survey_file_path(meta.survey_uuid).exists():
                os.remove(survey_file_path(meta.survey_uuid))
            if response_file_path(meta.survey_uuid).exists():
                os.remove(response_file_path(meta.survey_uuid))
        except Exception:
            pass
        db.session.delete(meta)

    # Удаляем самого пользователя
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "deleted"})
# ==========================================
# 3. ПЕРЕНОС ТВОЕЙ СТАРОЙ ЛОГИКИ (JSON API)
# ==========================================
import os
import secrets
import re
import json
from datetime import datetime

# Твои старые вспомогательные функции оставляем!
def slugify_title(title: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", title.strip().lower(), flags=re.UNICODE)
    cleaned = cleaned.strip("-")
    return cleaned or "survey"

def generate_survey_id(title: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    token = secrets.token_hex(2)
    return f"{slugify_title(title)}-{stamp}-{token}"


# --- РОУТ СОЗДАНИЯ ОПРОСА ---
@app.route('/api/surveys', methods=['POST'])
@login_required # Только авторизованные могут создавать опросы!
def create_survey():
    payload = request.json # Flask сам парсит JSON
    title = str(payload.get("title", "")).strip()
    raw_features = payload.get("features", [])
    
    if not title:
        return jsonify({"error": "Название опроса обязательно."}), 400
    if not raw_features or not isinstance(raw_features, list):
        return jsonify({"error": "Нужно добавить хотя бы одно свойство."}), 400
        
    features = []
    for index, feature in enumerate(raw_features, start=1):
        name = str(feature.get("name", "")).strip()
        description = str(feature.get("description", "")).strip()
        if not name:
            return jsonify({"error": f"Свойство #{index} не содержит название."}), 400
        features.append({
            "feature_id": f"А{index}",
            "name": name,
            "description": description,
        })

    survey_id = generate_survey_id(title)
    
    try:
        # 1. Создаем папку, если вдруг её нет, и сохраняем JSON
        os.makedirs(SURVEYS_DIR, exist_ok=True)
        survey = KanoSurvey.from_dict({"title": title, "features": features})
        save_survey(survey, SURVEYS_DIR / f"{survey_id}.json")
        
        # 2. Сохраняем "ярлык" в Базу Данных
        new_meta = SurveyMeta(
            user_id=current_user.id, # Берем ID текущего залогиненного юзера
            survey_uuid=survey_id,
            title=title
        )
        db.session.add(new_meta)
        db.session.commit()
        
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "status": "created",
        "survey_id": survey_id,
        "title": title,
        "survey_url": f"/survey/{survey_id}",
        "dashboard_url": f"/dashboard/{survey_id}",
    }), 201


# --- РОУТ ПОЛУЧЕНИЯ СПИСКА МОИХ ОПРОСОВ ---
@app.route('/api/surveys', methods=['GET'])
@login_required
def list_my_surveys():
    # Если запрашивает админ - берем все опросы и склеиваем с таблицей User
    if current_user.role == 'admin':
        query_result = db.session.query(SurveyMeta, User).join(User, SurveyMeta.user_id == User.id).all()
    else:
        query_result = db.session.query(SurveyMeta, User).join(User, SurveyMeta.user_id == User.id).filter(SurveyMeta.user_id == current_user.id).all()
    
    items = []
    for meta, user in query_result:
        # 1. Считаем количество ответов респондентов
        response_path = RESPONSES_DIR / f"{meta.survey_uuid}.json"
        resp_count = 0
        if response_path.exists():
            import json
            try:
                resp_count = len(json.loads(response_path.read_text(encoding="utf-8")))
            except:
                pass

        # 2. Считаем количество свойств из файла опроса (ИСПРАВЛЕНИЕ БАГА)
        survey_path = SURVEYS_DIR / f"{meta.survey_uuid}.json"
        feature_count = 0
        if survey_path.exists():
            import json
            try:
                survey_data = json.loads(survey_path.read_text(encoding="utf-8"))
                feature_count = len(survey_data.get("features", []))
            except:
                pass

        item = {
            "survey_id": meta.survey_uuid,
            "title": meta.title,
            "feature_count": feature_count, # Теперь сюда подставляется реальная цифра
            "respondent_count": resp_count,
            "survey_url": f"/survey/{meta.survey_uuid}",
            "dashboard_url": f"/dashboard/{meta.survey_uuid}",
        }

        # Если запрашивает админ, добавляем информацию об авторе
        if current_user.role == 'admin':
            item["creator_name"] = user.full_name
            item["creator_username"] = user.username

        items.append(item)
        
    return jsonify({"items": items})
# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФАЙЛОВ ---
def survey_file_path(survey_id: str):
    return SURVEYS_DIR / f"{survey_id}.json"

def response_file_path(survey_id: str):
    return RESPONSES_DIR / f"{survey_id}.json"

def read_response_store(survey_id: str) -> list:
    path = response_file_path(survey_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return []

def write_response_store(survey_id: str, responses: list) -> None:
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    response_file_path(survey_id).write_text(json.dumps(responses, ensure_ascii=False, indent=2), encoding="utf-8")


# --- РОУТ ПОЛУЧЕНИЯ ОПРОСА (ДЛЯ РЕСПОНДЕНТОВ И ДАШБОРДА) ---
# Заметь: здесь НЕТ @login_required. Респонденты могут заходить свободно!
@app.route('/api/survey', methods=['GET'])
def get_survey():
    survey_id = request.args.get("id")
    if not survey_id:
        return jsonify({"error": "Не указан ID опроса."}), 400
    
    path = survey_file_path(survey_id)
    if not path.exists():
        return jsonify({"error": f"Опросник '{survey_id}' не найден."}), 404
        
    try:
        survey = load_survey(path)
        return jsonify({
            "survey_id": survey_id,
            "survey": survey.as_dict(),
            "questionnaire": survey.questionnaire_table(),
            "survey_url": f"/survey/{survey_id}",
            "dashboard_url": f"/dashboard/{survey_id}",
        })
    except KanoValidationError as exc:
        return jsonify({"error": str(exc)}), 400


# --- РОУТ ОТПРАВКИ ОТВЕТОВ РЕСПОНДЕНТОМ ---
@app.route('/api/respond', methods=['POST'])
def respond_survey():
    payload = request.json
    survey_id = payload.get("survey_id")
    response_data = payload.get("response")
    
    if not survey_id or not response_data:
        return jsonify({"error": "Некорректные данные"}), 400
        
    if not survey_file_path(survey_id).exists():
        return jsonify({"error": "Опрос не найден"}), 404
        
    responses = read_response_store(survey_id)
    responses.append(response_data)
    write_response_store(survey_id, responses)
    
    return jsonify({
        "status": "accepted",
        "survey_id": survey_id,
        "respondent_count": len(responses),
    }), 201


# --- РОУТ ПОЛУЧЕНИЯ КОЛИЧЕСТВА ОТВЕТОВ (ДЛЯ ДАШБОРДА) ---
@app.route('/api/responses', methods=['GET'])
@login_required
def get_responses_count():
    survey_id = request.args.get("id")
    responses = read_response_store(survey_id)
    return jsonify({"survey_id": survey_id, "respondent_count": len(responses)})


# --- РОУТ АНАЛИЗА ---
@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_survey():
    payload = request.json
    survey_id = payload.get("survey_id")
    create_chart = bool(payload.get("create_chart", True))

    path = survey_file_path(survey_id)
    if not path.exists():
        return jsonify({"error": f"Опросник '{survey_id}' не найден."}), 404

    responses = read_response_store(survey_id)
    if not responses:
        return jsonify({"error": "Нет ответов для анализа."}), 400

    try:
        survey = load_survey(path)
        chart_name = f"kano_matrix_{survey_id}.png"
        
        # Вызываем твой старый модуль анализа
        result = analyze_kano_payload(
            survey_payload=survey.as_dict(),
            responses=responses,
            create_chart=create_chart,
            chart_path=str(BASE_DIR / chart_name), # сохраняем картинку в корень
        )
        
        # Привязываем URL картинки
        if result.get("summary", {}).get("chart_path"):
            result["summary"]["chart_url"] = f"/generated/{chart_name}"
            
        result["summary"]["respondent_count"] = len(responses)
        return jsonify(result)
        
    except Exception as exc:
        return jsonify({"error": f"Ошибка анализа: {exc}"}), 500


# --- РОУТ ОТДАЧИ КАРТИНОК АНАЛИЗА ---
@app.route('/generated/<path:filename>')
def serve_generated(filename):
    return send_from_directory(BASE_DIR, filename)


# --- РОУТ УДАЛЕНИЯ ОПРОСА ---
@app.route('/api/survey/delete', methods=['POST'])
@login_required
def delete_survey():
    survey_id = request.json.get("survey_id")
    
    # 1. Ищем опрос в БД
    if current_user.role == 'admin':
        # Админ может найти и удалить любой опрос
        meta = SurveyMeta.query.filter_by(survey_uuid=survey_id).first()
    else:
        # Организатор может найти только свой опрос
        meta = SurveyMeta.query.filter_by(survey_uuid=survey_id, user_id=current_user.id).first()
        
    if meta:
        db.session.delete(meta)
        db.session.commit()
    else:
        return jsonify({"error": "Опрос не найден или у вас нет прав на его удаление"}), 403

    # 2. Физически удаляем файлы
    try:
        if survey_file_path(survey_id).exists():
            os.remove(survey_file_path(survey_id))
        if response_file_path(survey_id).exists():
            os.remove(response_file_path(survey_id))
    except Exception as e:
        pass # Игнорируем ошибки файлов, главное что из БД удалили

    return jsonify({"status": "deleted", "survey_id": survey_id})


# --- РОУТ ОЧИСТКИ ОТВЕТОВ ---
@app.route('/api/responses/clear', methods=['POST'])
@login_required
def clear_responses():
    survey_id = request.json.get("survey_id")
    
    # Проверка прав (как при удалении)
    if current_user.role == 'admin':
        meta = SurveyMeta.query.filter_by(survey_uuid=survey_id).first()
    else:
        meta = SurveyMeta.query.filter_by(survey_uuid=survey_id, user_id=current_user.id).first()
        
    if not meta:
        return jsonify({"error": "Нет прав для очистки ответов этого опроса"}), 403
        
    write_response_store(survey_id, [])
    return jsonify({"status": "cleared", "survey_id": survey_id, "respondent_count": 0})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)