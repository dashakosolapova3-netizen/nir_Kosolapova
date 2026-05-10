from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import uuid
from datetime import datetime
from analysis import ITEAnalyzer
from werkzeug.utils import secure_filename
import base64
import csv

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для фронтенда

# Конфигур.
UPLOAD_FOLDER = 'data/experiments'
RESULTS_FOLDER = 'data/results'
ALLOWED_EXTENSIONS = {'json'}

# Создаем папки если их нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

# Инициализируем анализатор
analyzer = ITEAnalyzer()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.getcwd(), filename)

@app.route('/')
def index():
    return jsonify({
        "message": "UX Experiment Backend API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/upload",
            "analyze": "/api/analyze",
            "results": "/api/results/<session_id>"
        }
    })

@app.route('/api/upload', methods=['POST'])
def upload_experiment_data():
    """Принимает JSON данные эксперимента от фронтенда"""
    try:
        # Прверяем наличие данных
        if 'experimentData' not in request.json:
            return jsonify({'error': 'No experiment data provided'}), 400
        
        data = request.json['experimentData']
        session_id = data.get('sessionId', str(uuid.uuid4()))
        
        # Сохраняем данные
        filename = f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'filename': filename,
            'message': f'Experiment data saved successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_experiment():
    try:
        data = request.get_json()
        if not data or 'sessionIds' not in data:
            return jsonify({
                'error': 'Необходимо указать sessionIds',
                'note': 'Укажите ID сессий для анализа'
            }), 400

        session_ids = data['sessionIds']
        if len(session_ids) != 2:
            return jsonify({
                'error': 'Необходимо указать ровно 2 ID сессий',
                'note': 'Для анализа требуется ровно 2 сессии (Chrome и Firefox)'
            }), 400

        # Загружаем данные сессий
        sessions_data = []
        for session_id in session_ids:
            session_file = None
            for file in os.listdir('data/experiments'):
                if session_id in file:
                    session_file = file
                    break
            
            if not session_file:
                return jsonify({
                    'error': f'Сессия {session_id} не найдена',
                    'note': 'Убедитесь, что указаны корректные ID сессий'
                }), 404

            with open(os.path.join('data/experiments', session_file), 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                sessions_data.append(session_data)

        # Определяем, какая сессия Chrome, а какая Firefox
        chrome_data = None
        firefox_data = None
        for session in sessions_data:
            browser = session.get('browser', {}).get('name', '').lower()
            if 'chrome' in browser:
                chrome_data = session
            elif 'firefox' in browser:
                firefox_data = session

        if not chrome_data or not firefox_data:
            return jsonify({
                'error': 'Не удалось определить браузеры',
                'note': 'Убедитесь, что одна сессия проведена в Chrome, а другая в Firefox'
            }), 400

        # Анализируем данные
        analyzer = ITEAnalyzer()
        result = analyzer.analyze_two_sessions(chrome_data, firefox_data)

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'error': str(e),
            'note': 'Произошла ошибка при анализе данных'
        }), 500

def analyze_all_sessions():
    """Анализирует все доступные сессии и возвращает результаты"""
    try:
        experiment_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                          if f.endswith('.json')]
        
        if not experiment_files:
            return {
                'status': 'no_data',
                'message': 'Нет данных для анализа'
            }
        
        # Группируем сессии по браузерам
        browser_sessions = {}
        for file in experiment_files:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                browser = data.get('browser', {}).get('name', 'Unknown')
                if browser not in browser_sessions:
                    browser_sessions[browser] = []
                browser_sessions[browser].append(data)
        
        # Анализируем результаты
        results = {
            'browser_comparison': {},
            'emotion_stats': {},
            'task_stats': {}
        }
        
        # Сравнение браузеров
        for browser, sessions in browser_sessions.items():
            avg_task_time = sum(
                sum(task.get('duration', 0) for task in session.get('tasks', []))
                for session in sessions
            ) / len(sessions) if sessions else 0
            
            emotion_counts = {}
            total_emotions = 0
            for session in sessions:
                for emotion_data in session.get('emotionData', []):
                    dominant = emotion_data.get('dominantEmotion')
                    if dominant:
                        emotion_counts[dominant] = emotion_counts.get(dominant, 0) + 1
                        total_emotions += 1
            
            results['browser_comparison'][browser] = {
                'avg_task_time': avg_task_time / 1000,  # конвертируем в секунды
                'emotion_distribution': {
                    emotion: (count / total_emotions * 100) if total_emotions > 0 else 0
                    for emotion, count in emotion_counts.items()
                }
            }
        
        # Общая статистика по эмоциям
        all_emotions = {}
        total_emotions = 0
        for sessions in browser_sessions.values():
            for session in sessions:
                for emotion_data in session.get('emotionData', []):
                    dominant = emotion_data.get('dominantEmotion')
                    if dominant:
                        all_emotions[dominant] = all_emotions.get(dominant, 0) + 1
                        total_emotions += 1
        
        results['emotion_stats'] = {
            emotion: (count / total_emotions * 100) if total_emotions > 0 else 0
            for emotion, count in all_emotions.items()
        }
        
        # Статистика по задачам
        total_tasks = 0
        completed_tasks = 0
        total_time = 0
        for sessions in browser_sessions.values():
            for session in sessions:
                tasks = session.get('tasks', [])
                total_tasks += len(tasks)
                completed_tasks += sum(1 for task in tasks if task.get('completed'))
                total_time += sum(task.get('duration', 0) for task in tasks)
        
        results['task_stats'] = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'avg_task_time': (total_time / completed_tasks / 1000) if completed_tasks > 0 else 0
        }
        
        return results
        
    except Exception as e:
        print(f"Ошибка при анализе сессий: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

@app.route('/api/results/<session_id>')
def get_results(session_id):
    """Получает результаты анализа для сессии"""
    try:
        # Ищем файл с результатами
        results_files = [f for f in os.listdir(app.config['RESULTS_FOLDER']) 
                        if f.startswith(f'results_')]
        
        if not results_files:
            return jsonify({'error': 'Results not found'}), 404
        
        # берем самый свежий файл
        latest_file = sorted(results_files)[-1]
        filepath = os.path.join(app.config['RESULTS_FOLDER'], latest_file)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            results = json.load(f)
            
        # Добавляем статистику из эксперимента
        experiment_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                          if f.startswith(session_id)]
        if experiment_files:
            exp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], experiment_files[0])
            with open(exp_filepath, 'r', encoding='utf-8') as f:
                exp_data = json.load(f)
                results.update({
                    'statistics': exp_data.get('statistics', {}),
                    'calibrationAccuracy': exp_data.get('calibrationAccuracy'),
                    'browser': exp_data.get('browser', {}),
                    'emotionData': exp_data.get('emotionData', [])
                })
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/experiments')
def list_experiments():
    """Список всех экспериментов"""
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        experiments = []
        
        for file in files:
            if file.endswith('.json'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    experiments.append({
                        'filename': file,
                        'session_id': data.get('sessionId'),
                        'timestamp': data.get('timestamp'),
                        'browser': data.get('browser', {}).get('name'),
                        'tasks_count': len(data.get('tasks', []))
                    })
        
        return jsonify({
            'status': 'success',
            'experiments': experiments
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 