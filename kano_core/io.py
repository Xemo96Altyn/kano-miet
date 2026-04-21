from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Union

from .models import KanoSurvey, SurveyResponse
from .validation import validate_survey


def save_survey(survey: KanoSurvey, filename: Union[str, Path]) -> Path:
    validate_survey(survey)
    path = Path(filename)
    path.write_text(json.dumps(survey.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_survey(filename: Union[str, Path]) -> KanoSurvey:
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    survey = KanoSurvey.from_dict(data)
    validate_survey(survey)
    return survey


def load_responses_from_csv(
    path: Union[str, Path],
    feature_id_column: str = "feature_id",
    functional_column: str = "functional",
    dysfunctional_column: str = "dysfunctional",
    respondent_column: Optional[str] = None,
) -> List[SurveyResponse]:
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        if respondent_column is None:
            responses: List[SurveyResponse] = []
            for row in reader:
                feature_id = row[feature_id_column]
                functional = row[functional_column]
                dysfunctional = row[dysfunctional_column]
                responses.append({feature_id: (functional, dysfunctional)})
            return responses

        respondents: Dict[str, SurveyResponse] = {}
        for row in reader:
            respondent_id = row[respondent_column]
            feature_id = row[feature_id_column]
            functional = row[functional_column]
            dysfunctional = row[dysfunctional_column]
            respondent = respondents.setdefault(respondent_id, {})
            respondent[feature_id] = (functional, dysfunctional)
        return list(respondents.values())
