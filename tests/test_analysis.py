import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import numpy as np
from analysis import CustomForest, ITEAnalyzer

class TestCustomForest(unittest.TestCase):
    def setUp(self):
        """Подготовка данных для тестов"""
        self.X = np.random.rand(100, 5)  # 100 samples, 5 features
        self.y = np.random.rand(100)
        self.forest = CustomForest(n_estimators=10, max_depth=5)

    def test_fit_predict(self):
        """Тест базового функционала обучения и предсказания"""
        self.forest.fit(self.X, self.y)
        predictions = self.forest.predict(self.X)
        self.assertEqual(len(predictions), len(self.y))
        self.assertTrue(all(isinstance(pred, (np.floating, float)) for pred in predictions))

    def test_feature_selection(self):
        """Тест выбора признаков"""
        self.forest.max_features = 'sqrt'
        self.forest.fit(self.X, self.y)
        self.assertEqual(len(self.forest.trees), self.forest.n_estimators)

class TestITEAnalyzer(unittest.TestCase):
    def setUp(self):
        """Подготовка тестовых данных"""
        self.analyzer = ITEAnalyzer()

    def test_analyze_experiment_empty_data(self):
        """Тест анализа пустых данных эксперимента"""
        results = self.analyzer.analyze_experiment()
        self.assertIn('session_count', results)
        self.assertIn('ite_mean', results)
        self.assertIn('ite_std', results)
        self.assertIn('visualizations', results)
        self.assertIn('note', results)

    def test_analyze_experiment_with_data(self):
        """Тест анализа с реальными данными"""
        test_data = {
            'sessionId': 'test_session',
            'browser': {'name': 'Chrome'},
            'tasks': [{'completed': True, 'duration': 1000}],
            'gazeData': [{'x': 100, 'y': 100}],
            'emotionData': [{'expressions': {'happy': 0.8}}]
        }
        results = self.analyzer.analyze_experiment(test_data)
        self.assertIn('session_count', results)
        self.assertGreater(results['session_count'], 0)

if __name__ == '__main__':
    unittest.main() 