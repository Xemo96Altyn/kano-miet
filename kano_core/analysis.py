from __future__ import annotations

from typing import Dict, List, Optional

from .models import (
    AnswerValue,
    KanoAnalysisResult,
    KanoCategory,
    KanoFeatureResult,
    KanoSurvey,
    SurveyResponse,
)
from .reporting import summarize_feature_results
from .validation import validate_responses, validate_survey


class KanoAnalyzer:
    ANSWER_MAP: Dict[str, int] = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "нравится": 1,
        "приятно": 1,
        "лайк": 1,
        "ожидаю": 2,
        "ожидал": 2,
        "нейтрально": 3,
        "средне": 3,
        "терплю": 4,
        "могу терпеть": 4,
        "не нравится": 5,
        "негативно": 5,
        "не устраивает": 5,
    }

    CLASSIFICATION_MATRIX: Dict[int, Dict[int, KanoCategory]] = {
        1: {1: KanoCategory.QUESTIONABLE, 2: KanoCategory.ATTRACTIVE, 3: KanoCategory.ATTRACTIVE, 4: KanoCategory.ATTRACTIVE, 5: KanoCategory.ONE_DIMENSIONAL},
        2: {1: KanoCategory.REVERSE, 2: KanoCategory.QUESTIONABLE, 3: KanoCategory.INDIFFERENT, 4: KanoCategory.INDIFFERENT, 5: KanoCategory.MUST_BE},
        3: {1: KanoCategory.REVERSE, 2: KanoCategory.INDIFFERENT, 3: KanoCategory.INDIFFERENT, 4: KanoCategory.INDIFFERENT, 5: KanoCategory.MUST_BE},
        4: {1: KanoCategory.REVERSE, 2: KanoCategory.INDIFFERENT, 3: KanoCategory.INDIFFERENT, 4: KanoCategory.INDIFFERENT, 5: KanoCategory.MUST_BE},
        5: {1: KanoCategory.REVERSE, 2: KanoCategory.REVERSE, 3: KanoCategory.REVERSE, 4: KanoCategory.REVERSE, 5: KanoCategory.QUESTIONABLE},
    }

    def normalize_answer(self, answer: AnswerValue) -> Optional[int]:
        if isinstance(answer, int):
            return answer if 1 <= answer <= 5 else None

        if isinstance(answer, str):
            cleaned = answer.strip().lower()
            if cleaned in self.ANSWER_MAP:
                return self.ANSWER_MAP[cleaned]
            if cleaned.isdigit():
                numeric = int(cleaned)
                return numeric if 1 <= numeric <= 5 else None

        return None

    def classify_pair(self, functional: AnswerValue, dysfunctional: AnswerValue) -> KanoCategory:
        f_val = self.normalize_answer(functional)
        d_val = self.normalize_answer(dysfunctional)
        if f_val is None or d_val is None:
            return KanoCategory.QUESTIONABLE
        return self.CLASSIFICATION_MATRIX.get(f_val, {}).get(d_val, KanoCategory.QUESTIONABLE)

    def analyze(self, survey: KanoSurvey, respondent_answers: List[SurveyResponse]) -> List[KanoFeatureResult]:
        validate_survey(survey)

        feature_results: List[KanoFeatureResult] = []
        for feature in survey.features:
            counts: Dict[KanoCategory, int] = {category: 0 for category in KanoCategory}
            pairs: List[tuple[int, int]] = []

            for respondent in respondent_answers:
                pair = respondent.get(feature.feature_id)
                if pair is None or len(pair) != 2:
                    counts[KanoCategory.QUESTIONABLE] += 1
                    continue

                f_val = self.normalize_answer(pair[0])
                d_val = self.normalize_answer(pair[1])
                if f_val is None or d_val is None:
                    counts[KanoCategory.QUESTIONABLE] += 1
                    continue

                pairs.append((f_val, d_val))
                counts[self.CLASSIFICATION_MATRIX[f_val][d_val]] += 1

            total = sum(counts.values())
            final_category = self._determine_final_category(counts)
            satisfaction = self._satisfaction_coefficient(counts, total)
            dissatisfaction = self._dissatisfaction_coefficient(counts, total)

            feature_results.append(
                KanoFeatureResult(
                    feature=feature,
                    counts=counts,
                    total_answers=total,
                    final_category=final_category,
                    satisfaction_coefficient=satisfaction,
                    dissatisfaction_coefficient=dissatisfaction,
                    interpretation=self._interpret(final_category, satisfaction, dissatisfaction),
                    recommendation=self._recommendation(final_category),
                    pairs=pairs,
                )
            )

        return feature_results

    def analyze_to_result(self, survey: KanoSurvey, respondent_answers: List[SurveyResponse]) -> KanoAnalysisResult:
        warnings = validate_responses(survey, respondent_answers)
        feature_results = self.analyze(survey, respondent_answers)
        return KanoAnalysisResult(
            survey=survey,
            feature_results=feature_results,
            summary=summarize_feature_results(feature_results),
            warnings=warnings,
        )

    def _determine_final_category(self, counts: Dict[KanoCategory, int]) -> KanoCategory:
        primary_counts = {
            category: count
            for category, count in counts.items()
            if category != KanoCategory.QUESTIONABLE
        }
        winner = max(primary_counts.items(), key=lambda item: item[1], default=(KanoCategory.QUESTIONABLE, 0))
        if winner[1] == 0:
            return KanoCategory.QUESTIONABLE
        if counts[KanoCategory.QUESTIONABLE] >= winner[1]:
            return KanoCategory.QUESTIONABLE
        return winner[0]

    def _satisfaction_coefficient(self, counts: Dict[KanoCategory, int], total: int) -> float:
        if total == 0:
            return 0.0
        return (counts[KanoCategory.ATTRACTIVE] + counts[KanoCategory.ONE_DIMENSIONAL]) / total

    def _dissatisfaction_coefficient(self, counts: Dict[KanoCategory, int], total: int) -> float:
        if total == 0:
            return 0.0
        return -(counts[KanoCategory.MUST_BE] + counts[KanoCategory.ONE_DIMENSIONAL]) / total

    def _interpret(self, final_category: KanoCategory, satisfaction: float, dissatisfaction: float) -> str:
        dynamic: List[str] = []
        if satisfaction >= 0.7:
            dynamic.append("Высокий потенциал для роста удовлетворенности.")
        if dissatisfaction <= -0.4:
            dynamic.append("Отсутствие или плохая реализация вызывает заметное неудовлетворение.")
        if not dynamic:
            dynamic.append("Необходимо дополнительно посмотреть на распределение ответов.")
        return f"{final_category.description()} {' '.join(dynamic)}"

    def _recommendation(self, final_category: KanoCategory) -> str:
        if final_category == KanoCategory.MUST_BE:
            return "Обеспечить обязательное присутствие свойства, так как его отсутствие ухудшает качество продукта."
        if final_category == KanoCategory.ONE_DIMENSIONAL:
            return "Усилить и развивать свойство для повышения удовлетворенности."
        if final_category == KanoCategory.ATTRACTIVE:
            return "Сделать свойство заметной конкурентной особенностью."
        if final_category == KanoCategory.INDIFFERENT:
            return "Оценить целесообразность ресурсоемкой реализации."
        if final_category == KanoCategory.REVERSE:
            return "Пересмотреть необходимость свойства и возможные негативные эффекты."
        return "Пересмотреть методику опроса и формулировку вопросов."
