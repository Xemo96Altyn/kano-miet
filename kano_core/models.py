from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple, Union

AnswerValue = Union[int, str]
SurveyResponse = Dict[str, Tuple[AnswerValue, AnswerValue]]

DEFAULT_ANSWER_SCALE: Tuple[str, ...] = (
    "1. Мне нравится",
    "2. Ожидаю",
    "3. Нейтрально",
    "4. Могу терпеть",
    "5. Мне не нравится",
)


class KanoCategory(str, Enum):
    ATTRACTIVE = "Привлекательная"
    ONE_DIMENSIONAL = "Одномерная"
    MUST_BE = "Обязательная"
    INDIFFERENT = "Безразличная"
    REVERSE = "Обратная"
    QUESTIONABLE = "Сомнительная"

    def short(self) -> str:
        return {
            KanoCategory.ATTRACTIVE: "A",
            KanoCategory.ONE_DIMENSIONAL: "O",
            KanoCategory.MUST_BE: "M",
            KanoCategory.INDIFFERENT: "I",
            KanoCategory.REVERSE: "R",
            KanoCategory.QUESTIONABLE: "Q",
        }[self]

    def description(self) -> str:
        return {
            KanoCategory.ATTRACTIVE: "Свойство вызывает положительные эмоции при наличии и не вызывает неудовлетворения при отсутствии.",
            KanoCategory.ONE_DIMENSIONAL: "Свойство влияет на удовлетворенность пропорционально: чем лучше, тем выше удовлетворение.",
            KanoCategory.MUST_BE: "Свойство обязательно. Его отсутствие вызывает неудовлетворение, а наличие воспринимается как должное.",
            KanoCategory.INDIFFERENT: "Свойство не имеет существенного влияния на удовлетворенность пользователей.",
            KanoCategory.REVERSE: "Свойство воспринимается негативно: его наличие снижает удовлетворение.",
            KanoCategory.QUESTIONABLE: "Результаты неоднозначны; необходимо пересмотреть опрос или данные.",
        }[self]


class KanoQuestionType(str, Enum):
    FUNCTIONAL = "Функциональный"
    DYSFUNCTIONAL = "Дисфункциональный"


@dataclass
class KanoFeature:
    feature_id: str
    name: str
    description: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "description": self.description,
        }


@dataclass
class KanoQuestion:
    feature_id: str
    feature_name: str
    type: KanoQuestionType
    text: str
    answer_scale: Tuple[str, ...] = field(default_factory=lambda: DEFAULT_ANSWER_SCALE)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "feature_name": self.feature_name,
            "question_type": self.type.value,
            "question_text": self.text,
            "scale": list(self.answer_scale),
        }


@dataclass
class KanoFeatureResult:
    feature: KanoFeature
    counts: Dict[KanoCategory, int]
    total_answers: int
    final_category: KanoCategory
    satisfaction_coefficient: float
    dissatisfaction_coefficient: float
    interpretation: str
    recommendation: str
    pairs: List[Tuple[int, int]] = field(default_factory=list)

    def as_dict(self, include_pairs: bool = False) -> Dict[str, Any]:
        payload = {
            "feature_id": self.feature.feature_id,
            "feature_name": self.feature.name,
            "feature_description": self.feature.description,
            "counts": {cat.short(): self.counts.get(cat, 0) for cat in KanoCategory},
            "count_labels": {cat.value: self.counts.get(cat, 0) for cat in KanoCategory},
            "total_answers": self.total_answers,
            "final_category": self.final_category.value,
            "final_category_code": self.final_category.short(),
            "satisfaction_coefficient": round(self.satisfaction_coefficient, 3),
            "dissatisfaction_coefficient": round(self.dissatisfaction_coefficient, 3),
            "interpretation": self.interpretation,
            "recommendation": self.recommendation,
        }
        if include_pairs:
            payload["pairs"] = list(self.pairs)
        return payload


@dataclass
class KanoAnalysisResult:
    survey: "KanoSurvey"
    feature_results: List[KanoFeatureResult]
    summary: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)

    def as_dict(self, include_pairs: bool = False) -> Dict[str, Any]:
        return {
            "survey": self.survey.as_dict(),
            "questionnaire": [question.as_dict() for question in self.survey.create_questionnaire()],
            "feature_results": [result.as_dict(include_pairs=include_pairs) for result in self.feature_results],
            "summary": self.summary,
            "warnings": list(self.warnings),
        }


class KanoSurvey:
    def __init__(self, features: List[KanoFeature] | None = None, title: str = "") -> None:
        self.features: List[KanoFeature] = list(features or [])
        self.title = title

    def add_feature(self, feature_id: str, name: str, description: str = "") -> KanoFeature:
        feature = KanoFeature(feature_id=feature_id, name=name, description=description)
        self.features.append(feature)
        return feature

    def create_questionnaire(self) -> List[KanoQuestion]:
        questions: List[KanoQuestion] = []
        for feature in self.features:
            questions.append(
                KanoQuestion(
                    feature_id=feature.feature_id,
                    feature_name=feature.name,
                    type=KanoQuestionType.FUNCTIONAL,
                    text=f"Если в продукте реализовано свойство '{feature.name}', как вы к этому отнесетесь?",
                )
            )
            questions.append(
                KanoQuestion(
                    feature_id=feature.feature_id,
                    feature_name=feature.name,
                    type=KanoQuestionType.DYSFUNCTIONAL,
                    text=f"Если в продукте отсутствует свойство '{feature.name}', как вы к этому отнесетесь?",
                )
            )
        return questions

    def questionnaire_table(self) -> List[Dict[str, Any]]:
        return [question.as_dict() for question in self.create_questionnaire()]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "features": [feature.as_dict() for feature in self.features],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KanoSurvey":
        survey = cls(title=str(data.get("title", "")).strip())
        for feature_data in data.get("features", []):
            survey.add_feature(
                feature_id=str(feature_data.get("feature_id", "")).strip(),
                name=str(feature_data.get("name", "")).strip(),
                description=str(feature_data.get("description", "")).strip(),
            )
        return survey
