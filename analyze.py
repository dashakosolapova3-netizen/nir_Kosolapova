import json
import os
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
import warnings

warnings.filterwarnings('ignore')

class RegistrationFormAnalyzer:
    """
    Анализатор данных для исследования форм регистрации.
    Сравнивает модальную (задание 3) и inline (задание 4) валидацию.
    Включает метрики: валентность, негатив, тревожность, когнитивная нагрузка, время реакции.
    """
    
    def __init__(self, data_folder='data/experiments'):
        self.data_folder = data_folder
        self.sessions_data = []
        self.results_df = None
        self.comparison_results = {}
        
    def load_all_sessions(self):
        """Загрузка всех JSON-сессий из папки"""
        print(f"Загрузка данных из {self.data_folder}...")
        if not os.path.exists(self.data_folder):
            print(f"Папка {self.data_folder} не найдена. Создаю...")
            os.makedirs(self.data_folder, exist_ok=True)
            return 0
            
        files = [f for f in os.listdir(self.data_folder) if f.endswith('.json')]
        for filename in files:
            filepath = os.path.join(self.data_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['_filename'] = filename
                    self.sessions_data.append(data)
            except Exception as e:
                print(f"Ошибка загрузки {filename}: {e}")
                
        print(f"Загружено  {len(self.sessions_data)}  сессий")
        return len(self.sessions_data)
    
    def classify_session(self, session):
        """
        Определяет тип сессии (Modal или Inline).
        Логика: Четный ID -> Modal, Нечетный ID -> Inline.
        """
        # --- Метод 1: По номеру участника (Самый надежный) ---
        p_id = session.get('participantNumber')
        if p_id is not None:
            try:
                # Приводим к строке, затем к числу, чтобы избежать ошибок типов
                num = int(str(p_id))
                if num % 2 == 0:
                    return 'modal'
                else:
                    return 'inline'
            except (ValueError, TypeError):
                pass 

        tasks = session.get('tasks', [])
        for task in tasks:
            # Берем ID задачи и приводим к нижнему регистру
            tid = str(task.get('id', '')).lower()
            
            # Ключевые слова для модальной валидации
            if any(k in tid for k in ['modal', 'modalka', 'pretty']):
                return 'modal'
            
            # Ключевые слова для инлайн валидации
            if any(k in tid for k in ['inline', 'unmodal', 'form_inline']):
                return 'inline'
                
        return 'unknown'
    
    def calculate_anxiety_index(self, expressions):
        """
        Индекс тревожности. Учитывает эффект внезапности (surprise) при появлении модалки,
        а также стресс (fearful, angry) и фрустрацию (sad).
        Формула: 0.5*Surprise + 1.0*Fear + 0.8*Angry + 0.4*Sad
        """
        return (expressions.get('surprised', 0) * 0.5 +
                expressions.get('fearful', 0) * 1.0 +
                expressions.get('angry', 0) * 0.8 +
                expressions.get('sad', 0) * 0.4)

    def calculate_emotion_metrics(self, emotion_data):
        """Расчёт базовых и продвинутых эмоциональных метрик"""
        if not emotion_data:
            return {k: 0.0 for k in ['avg_valence', 'std_valence', 'avg_negative_prob', 
                                     'avg_anxiety', 'peak_anxiety', 'total_samples', 'negative_ratio']}
            
        df = pd.DataFrame(emotion_data)
        valence_map = {'happy': 0.8, 'surprised': 0.2, 'neutral': 0.0, 
                       'sad': -0.4, 'fearful': -0.6, 'angry': -0.8, 'disgusted': -0.9}
        
        def calc_valence(expr): return sum(expr.get(e, 0) * v for e, v in valence_map.items())
        def calc_neg(expr): return sum(expr.get(e, 0) for e in ['angry', 'disgusted', 'sad', 'fearful'])
        def calc_anx(expr): return self.calculate_anxiety_index(expr)
        def dominant(expr): return max(expr.items(), key=lambda x: x[1])[0]
        
        df['valence'] = df['expressions'].apply(calc_valence)
        df['negative_prob'] = df['expressions'].apply(calc_neg)
        df['anxiety'] = df['expressions'].apply(calc_anx)
        df['dominant'] = df['expressions'].apply(dominant)
        
        return {
            'avg_valence': df['valence'].mean(),
            'std_valence': df['valence'].std() if len(df) > 1 else 0.0,
            'avg_negative_prob': df['negative_prob'].mean(),
            'avg_anxiety': df['anxiety'].mean(),
            'peak_anxiety': df['anxiety'].max(),
            'total_samples': len(df),
            'negative_ratio': (df['dominant'].isin(['angry', 'sad', 'fearful', 'disgusted'])).mean()
        }
    
    def calculate_interaction_metrics(self, events):
        """Анализ кликов, закрытий и времени реакции на модалки"""
        if not events:
            return {'modal_shown_count': 0, 'total_clicks': 0, 'error_corrections': 0, 'avg_modal_reaction_time': 0.0}
            
        df = pd.DataFrame(events)
        modals = df[df['type'] == 'modal_shown']
        clicks = df[df['type'] == 'click']
        corrections = 0
        
        for _, row in clicks.iterrows():
            if isinstance(row.get('data'), dict):
                text = str(row['data'].get('text', '')).lower()
                if any(w in text for w in ['нет', 'спасибо', 'закрыть', 'ок', 'исправить']):
                    corrections += 1
                    
        # Время реакции: от modal_shown до следующего click или modal_closed
        reaction_times = []
        for _, m in modals.iterrows():
            m_time = m['timestamp']
            subsequent = df[(df['timestamp'] > m_time) & ((df['type'] == 'click') | (df['type'] == 'modal_closed'))]
            if not subsequent.empty:
                delta = (subsequent.iloc[0]['timestamp'] - m_time) / 1000.0
                reaction_times.append(delta)
                
        return {
            'modal_shown_count': len(modals),
            'total_clicks': len(clicks),
            'error_corrections': corrections,
            'avg_modal_reaction_time': np.mean(reaction_times) if reaction_times else 0.0
        }
    
    def calculate_gaze_metrics(self, gaze_data):
        """Анализ айтрекинга: скорость, дисперсия, частота фиксаций"""
        if not gaze_data or len(gaze_data) < 2:
            return {'avg_gaze_speed': 0.0, 'gaze_variance': 0.0, 'fixations_per_sec': 0.0}
            
        df = pd.DataFrame(gaze_data).sort_values('timestamp')
        df['dx'] = df['x'].diff()
        df['dy'] = df['y'].diff()
        df['dist'] = np.sqrt(df['dx']**2 + df['dy']**2)
        df['dt'] = df['timestamp'].diff() / 1000.0
        
        # Фильтр выбросов (слишком быстрые скачки = потеря трекинга)
        valid = df[(df['dt'] > 0) & (df['dist'] < 5000)]
        speeds = valid['dist'] / valid['dt']
        
        duration = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]) / 1000.0
        
        return {
            'avg_gaze_speed': speeds.mean() if len(speeds) > 0 else 0.0,
            'gaze_variance': df['x'].var() + df['y'].var(),
            'fixations_per_sec': len(df) / duration if duration > 0 else 0.0
        }
    
    def analyze_session(self, session):
        """Сбор всех метрик для одной сессии"""
        v_type = self.classify_session(session)
        
        # Фильтруем только задания по формам регистрации (3 и 4)
        reg_keywords = ['modal', 'inline', 'modalka', 'pretty', 'validation']
        reg_tasks = [t for t in session.get('tasks', []) 
                     if any(k in t.get('id', '').lower() for k in reg_keywords)]
        if not reg_tasks: reg_tasks = session.get('tasks', []) # fallback
        
        task_ids = [t['id'] for t in reg_tasks]
        emotions = [e for e in session.get('emotionData', []) if e.get('taskId') in task_ids]
        gazes = [g for g in session.get('gazeData', []) if g.get('taskId') in task_ids]
        events = session.get('interactionEvents', [])
        
        metrics = {
            'session_id': session.get('sessionId'),
            'participant_id': session.get('participantNumber'),
            'validation_type': v_type,
            'total_duration_sec': sum(t.get('duration', 0) for t in reg_tasks) / 1000.0,
            'completed_tasks': sum(1 for t in reg_tasks if t.get('completed'))
        }
        metrics.update(self.calculate_emotion_metrics(emotions))
        metrics.update(self.calculate_interaction_metrics(events))
        metrics.update(self.calculate_gaze_metrics(gazes))
        
        # Композитный индекс когнитивной нагрузки (нормализованный)
        # Чем выше скорость взгляда, дисперсия и время реакции -> тем выше нагрузка
        load_parts = [
            metrics['avg_gaze_speed'] / 2000.0,      # нормализация скорости
            metrics['gaze_variance'] / 500000.0,     # нормализация разброса
            metrics['avg_modal_reaction_time'] / 8.0 # нормализация реакции
        ]
        metrics['cognitive_load_index'] = np.mean([p for p in load_parts if p >= 0])
        
        return metrics
    
    def analyze_all_sessions(self):
        """Пакетный анализ всех сессий"""
        print("Анализ сессий...")
        all_metrics = []
        for session in self.sessions_data:
            try:
                all_metrics.append(self.analyze_session(session))
            except Exception as e:
                print(f"Ошибка анализа {session.get('sessionId')}: {e}")
                
        self.results_df = pd.DataFrame(all_metrics)
        print(f"Проанализировано {len(self.results_df)} сессий")
        return self.results_df
    
    def compare_validation_types(self):
        """Статистическое сравнение Modal vs Inline"""
        if self.results_df is None or self.results_df.empty:
            print("Сначала выполните analyze_all_sessions()")
            return
            
        modal = self.results_df[self.results_df['validation_type'] == 'modal']
        inline = self.results_df[self.results_df['validation_type'] == 'inline']
        
        print("\n" + "="*70)
        print("СРАВНЕНИЕ: МОДАЛЬНАЯ vs INLINE ВАЛИДАЦИЯ")
        print("="*70)
        print(f"👥 Modal: {len(modal)} участников | Inline: {len(inline)} участников\n")
        
        metrics_to_check = [
            ('avg_anxiety', ' Индекс Тревожности', False),
            ('peak_anxiety', 'Пиковая Тревожность', False),
            ('cognitive_load_index', ' Индекс Когнитивной Нагрузки', False),
            ('avg_gaze_speed', 'Скорость движения взгляда (px/ms)', False),
            ('avg_modal_reaction_time', 'Время реакции на модалку (сек)', False),
            ('total_duration_sec', 'Общее время заполнения (сек)', False),
            ('avg_negative_prob', 'Средняя вероятность негатива', False),
            ('error_corrections', 'Исправлений ошибок', False),
            ('total_clicks', 'Всего кликов', False)
        ]
        
        for metric, name, higher_better in metrics_to_check:
            if metric not in self.results_df.columns: continue
            
            m_val, m_std = modal[metric].mean(), modal[metric].std()
            i_val, i_std = inline[metric].mean(), inline[metric].std()
            
            t_stat, p_val = stats.ttest_ind(modal[metric].dropna(), inline[metric].dropna(), nan_policy='omit')
            sig = "Значимо" if p_val < 0.05 else "Не значимо"
            diff = m_val - i_val
            direction = "↑ выше" if diff > 0 else "↓ ниже"
            
            self.comparison_results[metric] = {'modal': m_val, 'inline': i_val, 'p': p_val, 'sig': p_val < 0.05}
            
            print(f" {name}:")
            print(f"   Modal: {m_val:.4f} ± {m_std:.4f}")
            print(f"   Inline: {i_val:.4f} ± {i_std:.4f}")
            print(f"   Разница: {abs(diff):.4f} ({direction}) | p={p_val:.4f} {sig}\n")
            
        return self.comparison_results
    
    def generate_report(self):
        """Генерация текстового отчёта с выводами"""
        if not self.comparison_results:
            print("Сначала выполните compare_validation_types()")
            return
            
        report = []
        report.append("="*70)
        report.append("ОТЧЁТ: Исследование форм регистрации (Modal vs Inline)")
        report.append("="*70)
        report.append(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"Всего сессий: {len(self.results_df)}")
       
                
        # Итоговые рекомендации
        report.append("\n" + "="*70)
        report.append(" ИТОГОВЫЕ РЕКОМЕНДАЦИИ ДЛЯ UX/UI")
        report.append("="*70)
        if anx.get('sig') and anx['modal'] > anx['inline']:
            report.append(" Для форм регистрации РЕКОМЕНДУЕТСЯ использовать INLINE-валидацию.")
            report.append("   - Снижает тревожность и когнитивную нагрузку")
            report.append("   - Ускоряет процесс заполнения")
            report.append("   - Уменьшает количество лишних кликов/закрытий окон")
        else:
            report.append("Различия незначительны. Выбор зависит от бизнес-логики и дизайна.")
            
        text = "\n".join(report)
        print(text)
        
        # Сохранение
        os.makedirs('data/results', exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'data/results/report_{ts}.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\n💾 Отчёт сохранён: data/results/report_{ts}.txt")
        return text

def main():
    print(" Запуск анализа НИР: Формы регистрации (Modal vs Inline)\n")
    analyzer = RegistrationFormAnalyzer()
    
    if analyzer.load_all_sessions() == 0:
        print(" Нет данных для анализа. Проверьте папку data/experiments")
        return
        
    analyzer.analyze_all_sessions()
    analyzer.compare_validation_types()
    analyzer.generate_report()
    
    print("\n Анализ завершён успешно!")

if __name__ == '__main__':
    main()