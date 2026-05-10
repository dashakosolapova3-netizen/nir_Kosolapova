import json
import os
import glob
import numpy as np
import pandas as pd
from pathlib import Path

class ModernExperimentAnalyzer:
    def __init__(self, data_dir='data/experiments'):
        self.data_dir = data_dir
        self.sessions = []
        self.summary_data = []

    def load_data(self):
        """Загрузка всех JSON файлов из директории."""
        files = glob.glob(os.path.join(self.data_dir, '*.json'))
        print(f"Найдено файлов: {len(files)}")
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    # Фильтрация по минимальному качеству данных (например, есть хоть какие-то gaze points)
                    if data.get('statistics', {}).get('totalGazePoints', 0) > 10:
                        self.sessions.append(data)
            except Exception as e:
                print(f"Ошибка при чтении {f}: {e}")
        return len(self.sessions)

    def analyze(self):
        """Основной цикл анализа сессий."""
        all_results = []
        
        for session in self.sessions:
            participant = session.get('participantNumber', 'Unknown')
            accuracy = session.get('calibrationAccuracy', 0)
            
            # Группируем события по таскам
            events = session.get('interactionEvents', [])
            tasks_found = set(e.get('taskId') for e in events if e.get('taskId'))
            
            for task_id in tasks_found:
                task_events = [e for e in events if e.get('taskId') == task_id]
                
                # Метрики модальных окон / плашек
                shown_count = len([e for e in task_events if e.get('type') == 'modal_shown'])
                closed_count = len([e for e in task_events if e.get('type') == 'modal_closed'])
                registered_count = len([e for e in task_events if e.get('type') == 'modal_registered']) or \
                                   len([e for e in task_events if e.get('type') == 'click' and 'регистр' in e.get('data', {}).get('text', '').lower()])
                
                # Расчет времени реакции
                reaction_times = []
                last_shown = None
                for e in task_events:
                    if e.get('type') == 'modal_shown':
                        last_shown = e.get('timestamp')
                    elif e.get('type') in ['modal_closed', 'modal_registered', 'click'] and last_shown:
                        if e.get('type') == 'click' and e.get('data', {}).get('tag') != 'BUTTON':
                            continue
                        dt = (e.get('timestamp') - last_shown) / 1000
                        if 0.1 < dt < 60: # Отсекаем шум
                            reaction_times.append(dt)
                        last_shown = None

                # Эмоции для этого таска
                # (В текущей структуре emotionStats может быть общим или по v2)
                # Попробуем найти образцы эмоций в gazeData или emotionData если они есть
                task_frustration = 0
                emo_samples = [e for e in session.get('emotionData', []) if e.get('taskId') == task_id]
                if emo_samples:
                    neg_emotions = []
                    for s in emo_samples:
                        expr = s.get('expressions', {})
                        # Фрустрация = Angry + Sad + Disgusted
                        f_score = expr.get('angry', 0) + expr.get('sad', 0) + expr.get('disgusted', 0)
                        neg_emotions.append(f_score)
                    task_frustration = np.mean(neg_emotions) if neg_emotions else 0

                all_results.append({
                    'participant': participant,
                    'task_id': task_id,
                    'accuracy': accuracy,
                    'shown': shown_count,
                    'closed': closed_count,
                    'registered': registered_count,
                    'conv_rate': (registered_count / shown_count * 100) if shown_count > 0 else 0,
                    'avg_reaction': np.mean(reaction_times) if reaction_times else 0,
                    'frustration': task_frustration
                })
        
        self.summary_data = pd.DataFrame(all_results)
        return self.summary_data

    def print_report(self):
        if self.summary_data.empty:
            print("Нет данных для анализа.")
            return

        print("\n" + "="*80)
        print(f"{'СВОДНЫЙ ОТЧЕТ ПО ЭКСПЕРИМЕНТАМ':^80}")
        print("="*80)
        
        # Сводка по типам тасков
        report = self.summary_data.groupby('task_id').agg({
            'participant': 'count',
            'accuracy': 'mean',
            'conv_rate': 'mean',
            'shown': 'mean',
            'avg_reaction': 'mean',
            'frustration': 'mean'
        }).round(2)
        
        report.columns = ['Участников', 'Точность %', 'Конверсия %', 'Показов (ср)', 'Реакция (сек)', 'Фрустрация']
        print(report.to_string())
        print("="*80)
        
        # Сохранение в JSON
        output_path = 'data/analysis_summary.json'
        report.to_json(output_path, orient='index', force_ascii=False)
        print(f"Отчет сохранен в {output_path}")

if __name__ == '__main__':
    analyzer = ModernExperimentAnalyzer()
    if analyzer.load_data() > 0:
        analyzer.analyze()
        analyzer.print_report()
    else:
        print("Папка с экспериментами пуста или файлы не найдены.")
