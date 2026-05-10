import os
import json
import random
from analysis import ITEAnalyzer

SYNTH_DIR = 'data/experiments/synth'
N = 100  # всего объектов
N_PER_GROUP = N // 2

def generate_synthetic_session(session_id, browser_name):
    base = {
        'Chrome': {'tasks': 10, 'gaze': 100, 'emotions': 50, 'duration': 300000},
        'Firefox': {'tasks': 7, 'gaze': 80, 'emotions': 40, 'duration': 350000}
    }[browser_name]
    tasks = max(1, int(random.gauss(base['tasks'], 2)))
    gaze = max(10, int(random.gauss(base['gaze'], 15)))
    emotions = max(5, int(random.gauss(base['emotions'], 8)))
    duration = max(60000, int(random.gauss(base['duration'], 40000)))
    return {
        "sessionId": session_id,
        "timestamp": random.randint(1700000000000, 1800000000000),
        "browser": {"name": browser_name, "version": "test", "userAgent": "synthetic", "platform": "test", "language": "ru"},
        "screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1040, "pixelRatio": 1, "viewport": {"width": 1200, "height": 800}},
        "tasks": [{"id": f"task_{i+1}", "description": "test", "startTime": 0, "endTime": 0, "duration": duration//tasks, "completed": True} for i in range(tasks)],
        "currentTaskId": None,
        "gazeData": [{"timestamp": 0, "taskId": None, "x": random.randint(0, 1200), "y": random.randint(0, 800), "relativeTime": 0} for _ in range(gaze)],
        "emotionData": [{"timestamp": 0, "taskId": None, "expressions": {"happy": random.random(), "sad": random.random()}, "relativeTime": 0, "dominantEmotion": "happy"} for _ in range(emotions)],
        "interactionEvents": [{"timestamp": 0, "type": "click", "taskId": None, "data": {}} for _ in range(random.randint(5, 20))],
        "errors": [],
        "startTime": 0,
        "endTime": duration,
        "duration": duration
    }

def generate_synthetic_dataset():
    os.makedirs(SYNTH_DIR, exist_ok=True)
    for i in range(N):
        browser = 'Chrome' if i < N_PER_GROUP else 'Firefox'
        session_id = f'synth_{browser.lower()}_{i+1}'
        session = generate_synthetic_session(session_id, browser)
        with open(os.path.join(SYNTH_DIR, f'{session_id}.json'), 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
    print(f'Сгенерировано {N} синтетических сессий в {SYNTH_DIR}')

def run_analysis():
    analyzer = ITEAnalyzer()
    files = [os.path.join(SYNTH_DIR, f) for f in os.listdir(SYNTH_DIR) if f.endswith('.json')]
    data = []
    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            data.append(json.load(f))
    print(f'загружено {len(data)} сессий для анализа')
    results = analyzer.analyze_experiment_list(data)
    print('рез-ты анализа:')
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    generate_synthetic_dataset()
    run_analysis()