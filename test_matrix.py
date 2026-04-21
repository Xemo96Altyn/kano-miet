#!/usr/bin/env python3
"""Тестовый скрипт для быстрой генерации матрицы Кано с случайными данными."""

import random
from kano_analysis import KanoSurvey, KanoAnalyzer

def generate_test_matrix():
    """Генерирует тестовую матрицу с случайными ответами."""
    
    # Создаём опросник с тестовыми свойствами
    survey = KanoSurvey()
    survey.add_feature("F1", "Быстрая загрузка")
    survey.add_feature("F2", "Удобный интерфейс")
    survey.add_feature("F3", "Надёжность")
    survey.add_feature("F4", "Красивый дизайн")
    survey.add_feature("F5", "Техподдержка")
    
    # Генерируем случайные ответы от 10 респондентов
    respondent_count = 10
    responses = []
    
    for respondent_id in range(respondent_count):
        respondent_answers = {}
        for feature in survey.features:
            # Случайные ответы: пара (функциональный, дисфункциональный) от 1 до 5
            functional_answer = random.randint(1, 5)
            dysfunctional_answer = random.randint(1, 5)
            respondent_answers[feature.feature_id] = (functional_answer, dysfunctional_answer)
        responses.append(respondent_answers)
    
    # Запускаем анализ
    analyzer = KanoAnalyzer()
    results = analyzer.analyze(survey, responses)
    
    # Выводим отчет
    print(analyzer.generate_report(results))
    print(f"\nМатрица сохранена в файл: kano_matrix.png")

if __name__ == "__main__":
    random.seed(42)  # Для воспроизводимости результатов
    generate_test_matrix()
