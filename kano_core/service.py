from __future__ import annotations

from typing import Any, Dict, List

from .analysis import KanoAnalyzer
from .chart import create_matrix_chart
from .models import KanoAnalysisResult, KanoSurvey, SurveyResponse
from .validation import validate_survey


def survey_from_payload(payload: Dict[str, Any]) -> KanoSurvey:
    survey = KanoSurvey.from_dict(payload)
    validate_survey(survey)
    return survey


def build_questionnaire_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    survey = survey_from_payload(payload)
    return {
        "survey": survey.as_dict(),
        "questionnaire": survey.questionnaire_table(),
    }


def analyze_kano(
    survey: KanoSurvey,
    responses: List[SurveyResponse],
    include_pairs: bool = False,
    create_chart: bool = False,
    chart_path: str = "kano_matrix.png",
) -> KanoAnalysisResult:
    analyzer = KanoAnalyzer()
    result = analyzer.analyze_to_result(survey, responses)
    if create_chart:
        chart = create_matrix_chart(result.feature_results, chart_path)
        if chart is None:
            result.warnings.append("График не создан: библиотека Pillow не установлена на сервере.")
        else:
            result.summary["chart_path"] = str(chart)
    return result


def analyze_kano_payload(
    survey_payload: Dict[str, Any],
    responses: List[SurveyResponse],
    include_pairs: bool = False,
    create_chart: bool = False,
    chart_path: str = "kano_matrix.png",
) -> Dict[str, Any]:
    survey = survey_from_payload(survey_payload)
    result = analyze_kano(
        survey=survey,
        responses=responses,
        include_pairs=include_pairs,
        create_chart=create_chart,
        chart_path=chart_path,
    )
    return result.as_dict(include_pairs=include_pairs)
