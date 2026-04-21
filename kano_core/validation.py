from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from .models import KanoSurvey, SurveyResponse


@dataclass
class KanoValidationError(ValueError):
    message: str
    details: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        if not self.details:
            return self.message
        return f"{self.message}: {'; '.join(self.details)}"


def validate_survey(survey: KanoSurvey) -> None:
    errors: List[str] = []
    if not survey.features:
        errors.append("опросник не содержит ни одного свойства")

    seen_ids: set[str] = set()
    for index, feature in enumerate(survey.features, start=1):
        feature_id = feature.feature_id.strip()
        name = feature.name.strip()
        if not feature_id:
            errors.append(f"свойство #{index} не содержит feature_id")
        if not name:
            errors.append(f"свойство {feature_id or f'#{index}'} не содержит name")
        if feature_id in seen_ids and feature_id:
            errors.append(f"feature_id '{feature_id}' используется более одного раза")
        seen_ids.add(feature_id)

    if errors:
        raise KanoValidationError("Ошибка валидации опросника", errors)


def validate_responses(survey: KanoSurvey, responses: Iterable[SurveyResponse]) -> List[str]:
    warnings: List[str] = []
    feature_ids = {feature.feature_id for feature in survey.features}

    for index, response in enumerate(list(responses), start=1):
        unknown_ids = set(response) - feature_ids
        if unknown_ids:
            warnings.append(
                f"респондент #{index} содержит неизвестные свойства: {', '.join(sorted(unknown_ids))}"
            )

        missing_ids = feature_ids - set(response)
        if missing_ids:
            warnings.append(
                f"респондент #{index} не ответил на свойства: {', '.join(sorted(missing_ids))}"
            )

        for feature_id, pair in response.items():
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                warnings.append(
                    f"респондент #{index}, свойство '{feature_id}': ответ должен быть парой из двух значений"
                )

    return warnings
