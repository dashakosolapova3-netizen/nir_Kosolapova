import json
import os
from pathlib import Path
import numpy as np
from collections import defaultdict

class SmartThesisAnalyzer:
    def __init__(self, experiments_dir='data/experiments'):
        self.experiments_dir = Path(experiments_dir)
        self.sessions = []
        self.valence_map = {
            'happy': 0.8, 'surprised': 0.2, 'neutral': 0.0,
            'sad': -0.4, 'fearful': -0.6, 'angry': -0.8, 'disgusted': -0.9
        }

    def load_sessions(self):
        json_files = list(self.experiments_dir.glob('*.json'))
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions.append(data)
            except: pass
        return len(self.sessions)

    def calculate_valence(self, expressions):
        if not expressions: return 0.0
        return sum(prob * self.valence_map.get(emotion, 0.0) for emotion, prob in expressions.items())

    def run_analysis(self):
        task_mapping = {
            'pretty_modal_validation': 'Task-1',
            'trash_modal_validation': 'Task-2',
            'inline_validation': 'Task-3',
            'modal_window_1': 'Task-4',
            'modal_plashka_1': 'Task-5',
            'modal_window_2': 'Task-6',
            'modal_plashka_2': 'Task-7',
            'modal_window_3': 'Task-8'
        }

        # Данные по задачам
        task_results = defaultdict(lambda: {'valence': [], 'total_duration': [], 'reaction_time': [], 'dispersion': []})

        for session in self.sessions:
            # 1. Карта временных интервалов задач в этой сессии
            task_intervals = []
            for t in session.get('tasks', []):
                tid = t.get('id')
                mapped_tid = task_mapping.get(tid, tid)
                if t.get('startTime') and t.get('endTime'):
                    task_intervals.append({
                        'id': mapped_tid,
                        'start': t['startTime'],
                        'end': t['endTime']
                    })
                    # Сохраняем общую длительность
                    task_results[mapped_tid]['total_duration'].append((t['endTime'] - t['startTime']) / 1000)

            # 2. Обработка событий взаимодействия
            modal_appearances = [] # Список всех моментов появления
            # Группируем клики по задачам
            for event in session.get('interactionEvents', []):
                ts = event.get('timestamp')
                ev_type = event.get('type')
                if ev_type == 'experiment_event': ev_type = event.get('eventName')
                
                # Находим, в какой задаче произошло событие (игнорируем event.taskId)
                current_task = next((t['id'] for t in task_intervals if t['start'] <= ts <= t['end']), None)
                if not current_task: continue

                if ev_type == 'modal_shown':
                    modal_appearances.append({'task': current_task, 'ts': ts})
                
                if ev_type == 'modal_closed':
                    # Ищем последнее появление в этой задаче
                    last_shown = next((m for m in reversed(modal_appearances) if m['task'] == current_task), None)
                    if last_shown:
                        rt = (ts - last_shown['ts']) / 1000
                        task_results[current_task]['reaction_time'].append(rt)
                
                # Обработка клика по [ЗАКРЫТЬ] как события закрытия
                if ev_type == 'click':
                    text = str(event.get('data', {}).get('text', '')).upper()
                    if '[ЗАКРЫТЬ]' in text or 'CLOSE' in text:
                        last_shown = next((m for m in reversed(modal_appearances) if m['task'] == current_task), None)
                        if last_shown:
                            rt = (ts - last_shown['ts']) / 1000
                            # Предотвращаем двойной учет если есть и click и modal_closed
                            if not task_results[current_task]['reaction_time'] or abs(task_results[current_task]['reaction_time'][-1] - rt) > 0.5:
                                task_results[current_task]['reaction_time'].append(rt)

            # 3. Эмоции и Взгляд
            for emo in session.get('emotionData', []):
                ts = emo.get('timestamp')
                cur_task = next((t['id'] for t in task_intervals if t['start'] <= ts <= t['end']), None)
                if cur_task and emo.get('expressions'):
                    task_results[cur_task]['valence'].append(self.calculate_valence(emo['expressions']))

            gaze_points = defaultdict(list)
            for gaze in session.get('gazeData', []):
                ts = gaze.get('timestamp')
                cur_task = next((t['id'] for t in task_intervals if t['start'] <= ts <= t['end']), None)
                if cur_task:
                    gaze_points[cur_task].append((gaze.get('x', 0), gaze.get('y', 0)))
            
            for tid, pts in gaze_points.items():
                if len(pts) > 5:
                    disp = np.sqrt(np.std([p[0] for p in pts])**2 + np.std([p[1] for p in pts])**2)
                    task_results[tid]['dispersion'].append(disp)

        print(f"CLEANED Results for {len(self.sessions)} participants:\n")
        print(f"{'Task':<10} | {'Val':<5} | {'Close':<6} | {'Total':<6} | {'Disp':<8}")
        print("-" * 50)
        
        for tid in sorted(task_results.keys()):
            d = task_results[tid]
            v = np.mean(d['valence']) if d['valence'] else 0
            rt = np.mean(d['reaction_time']) if d['reaction_time'] else 0
            td = np.mean(d['total_duration']) if d['total_duration'] else 0
            disp = np.mean(d['dispersion']) if d['dispersion'] else 0
            print(f"{tid:<10} | {v:5.2f} | {rt:6.2f} | {td:6.2f} | {disp:8.2f}")

if __name__ == '__main__':
    analyzer = SmartThesisAnalyzer()
    analyzer.load_sessions()
    analyzer.run_analysis()
