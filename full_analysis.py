import json
import os
from pathlib import Path
import numpy as np
from collections import defaultdict
import scipy.stats as st

class ThesisAnalyzer:
    def __init__(self, experiments_dir='data/experiments'):
        self.experiments_dir = Path(experiments_dir)
        self.sessions = []
        # Валентность убрана, вместо нее считаем Frustration и Positive


    def load_sessions(self):
        json_files = list(self.experiments_dir.glob('*.json'))
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions.append(data)
            except: pass
        return len(self.sessions)

    def calculate_emotions(self, expressions):
        if not expressions: return 0.0
        # Фрустрация/Негатив = Гнев + Отвращение + Страх + Грусть
        frustration = sum(expressions.get(e, 0.0) for e in ['angry', 'disgusted', 'fearful', 'sad'])
        return frustration

    def get_mean_ci(self, data, confidence=0.95):
        if not data: return 0.0, 0.0
        a = 1.0 * np.array(data)
        n = len(a)
        if n < 2:
            return np.mean(a), 0.0
        m, se = np.mean(a), st.sem(a)
        if se == 0:
            return m, 0.0
        h = se * st.t.ppf((1 + confidence) / 2., n-1)
        return m, h

    def run_analysis(self):
        task_mapping = {
            'pretty_modal_validation': 'Val-Pretty',
            'modal_v1_validation': 'Val-Pretty',
            'trash_modal_validation': 'Val-Trash',
            'modal_v2_validation': 'Val-Trash',
            'inline_validation': 'Val-Inline',
            'modal_window_1': 'Task-1',
            'modal_plashka_1': 'Task-2',
            'modal_window_2': 'Task-3',
            'modal_plashka_2': 'Task-4',
            'modal_window_3': 'Task-5'
        }

        task_data = defaultdict(lambda: {'frustration': [], 'reaction_time': [], 'spread': []})

        for session in self.sessions:
            # Эмоции
            for emo in session.get('emotionData', []):
                tid = emo.get('taskId')
                mapped_tid = task_mapping.get(tid, tid)
                expr = emo.get('expressions', {})
                if expr:
                    frust = self.calculate_emotions(expr)
                    task_data[mapped_tid]['frustration'].append(frust)

            # Время закрытия / реакции (модалки + инлайн)
            modal_instances = {}
            inline_error_at = None 
            
            for event in session.get('interactionEvents', []):
                ev_type = event.get('type')
                if ev_type == 'experiment_event':
                    ev_type = event.get('eventName')
                
                tid = event.get('taskId', 'Task-Unknown')
                mapped_tid = task_mapping.get(tid, tid)
                ts = event.get('timestamp')

                # 1. Логика для модальных окон
                if ev_type in ['modal_shown', 'modal_closed']:
                    inst_id = event.get('modal_instance', 0)
                    key = f"{mapped_tid}_{inst_id}"

                    if key not in modal_instances:
                        modal_instances[key] = {'shown_at': None, 'closed_at': None, 'version': mapped_tid}

                    if ev_type == 'modal_shown':
                        modal_instances[key]['shown_at'] = ts
                    elif ev_type == 'modal_closed':
                        modal_instances[key]['closed_at'] = ts

                # 2. Логика для инлайн-валидации (реакция на появление ошибок)
                if mapped_tid == 'Val-Inline':
                    if ev_type == 'inline_error_shown' and inline_error_at is None:
                        inline_error_at = ts
                    elif ev_type in ['click', 'inline_error_hidden'] and inline_error_at is not None:
                        # Считаем время от появления первой ошибки до первого действия (клик или исправление)
                        dt = (ts - inline_error_at) / 1000
                        if dt > 0.1: # Игнорируем мгновенные перекрывающиеся события
                            task_data['Val-Inline']['reaction_time'].append(dt)
                            inline_error_at = None

            # Собираем результаты по модалкам
            for key, data in modal_instances.items():
                if data['shown_at'] and data['closed_at']:
                    dt = (data['closed_at'] - data['shown_at']) / 1000
                    task_data[data['version']]['reaction_time'].append(dt)

            # Дисперсия
            gaze_by_task = defaultdict(list)
            for gaze in session.get('gazeData', []):
                tid = gaze.get('taskId')
                mapped_tid = task_mapping.get(tid, tid)
                gaze_by_task[mapped_tid].append((gaze.get('x', 0), gaze.get('y', 0)))
            
            for tid, points in gaze_by_task.items():
                if len(points) > 1:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    disp = np.sqrt(np.std(xs)**2 + np.std(ys)**2)
                    # Исключаем явные ошибки (выбросы) ай-трекинга
                    if disp < 3000:
                        task_data[tid]['spread'].append(disp)

        print(f"Results for {len(self.sessions)} participants:\n")
        print(f"{'Task':<12} | {'Frust (±CI)':<12} | {'Close (±CI)':<12} | {'Spread (±CI)':<14}")
        print("-" * 59)
        
        # Выводим только те таски, которые есть в нашем маппинге (8 штук)
        target_tasks = ['Val-Pretty', 'Val-Trash', 'Val-Inline', 'Task-1', 'Task-2', 'Task-3', 'Task-4', 'Task-5']
        
        for tid in target_tasks:
            d = task_data[tid]
            f_m, f_ci = self.get_mean_ci(d['frustration'])
            rt_data = d['reaction_time']
            rt_m, rt_ci = self.get_mean_ci(rt_data)
            sp_m, sp_ci = self.get_mean_ci(d['spread'])
            
            print(f"{tid:<12} | {f_m:4.2f} ±{f_ci:4.2f} | {rt_m:4.2f} ±{rt_ci:4.2f} | {sp_m:6.1f} ±{sp_ci:4.1f}")
        
        print("-" * 59)
        print(f"\nВсего обработано файлов: {len(self.sessions)}")

if __name__ == '__main__':
    analyzer = ThesisAnalyzer()
    analyzer.load_sessions()
    analyzer.run_analysis()
