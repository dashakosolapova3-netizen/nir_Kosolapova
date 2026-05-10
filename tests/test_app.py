import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import json
from app import app

class TestFlaskApp(unittest.TestCase):
    def setUp(self):
        """Подготовка тестового клиента"""
        self.app = app.test_client()
        self.app.testing = True
        
    def test_home_status_code(self):
        """Тест доступности главной страницы"""
        result = self.app.get('/')
        self.assertEqual(result.status_code, 200)
        
    def test_api_upload(self):
        """Тест загрузки данных эксперимента"""
        test_data = {
            'experimentData': {
                'sessionId': 'test_session',
                'browser': {'name': 'Chrome'},
                'tasks': [{'completed': True, 'duration': 1000}],
                'gazeData': [{'x': 100, 'y': 100}],
                'emotionData': [{'dominantEmotion': 'happy', 'expressions': {'happy': 0.8}}]
            }
        }
        result = self.app.post('/api/upload',
                               data=json.dumps(test_data),
                               content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertIn('success', result.get_data(as_text=True))
        
    def test_api_analyze_empty_data(self):
        """Тест анализа без данных (ожидаем ошибку 400)"""
        result = self.app.post('/api/analyze', data=json.dumps({}), content_type='application/json')
        self.assertEqual(result.status_code, 400)
        self.assertIn('sessionIds', result.get_data(as_text=True))
        
    def test_api_analyze_with_sessions(self):
        """Тест анализа с двумя сессиями (Chrome и Firefox)"""
        # Создаем две тестовые сессии
        chrome_id = 'test_session_chrome'
        firefox_id = 'test_session_firefox'
        chrome_data = {
            'experimentData': {
                'sessionId': chrome_id,
                'browser': {'name': 'Chrome'},
                'tasks': [{'completed': True, 'duration': 1000}],
                'gazeData': [{'x': 100, 'y': 100}],
                'emotionData': [{'dominantEmotion': 'happy', 'expressions': {'happy': 0.8}}]
            }
        }
        firefox_data = {
            'experimentData': {
                'sessionId': firefox_id,
                'browser': {'name': 'Firefox'},
                'tasks': [{'completed': True, 'duration': 2000}],
                'gazeData': [{'x': 120, 'y': 120}],
                'emotionData': [{'dominantEmotion': 'neutral', 'expressions': {'neutral': 0.9}}]
            }
        }
        self.app.post('/api/upload', data=json.dumps(chrome_data), content_type='application/json')
        self.app.post('/api/upload', data=json.dumps(firefox_data), content_type='application/json')
        # Теперь анализируем эти две сессии
        analyze_body = {'sessionIds': [chrome_id, firefox_id]}
        result = self.app.post('/api/analyze', data=json.dumps(analyze_body), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertIn('individual_effect', result.get_data(as_text=True))
        
if __name__ == '__main__':
    unittest.main() 