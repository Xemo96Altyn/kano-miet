from __future__ import annotations

from typing import List

from kano_core import (
    AnswerValue,
    KanoAnalysisResult,
    KanoAnalyzer as CoreKanoAnalyzer,
    KanoCategory,
    KanoFeature,
    KanoFeatureResult,
    KanoQuestion,
    KanoQuestionType,
    KanoSurvey,
    SurveyResponse,
    analyze_kano,
    analyze_kano_payload,
    build_questionnaire_payload,
    generate_report,
    load_responses_from_csv,
    load_survey,
    save_survey,
    survey_from_payload,
)


class KanoAnalyzer(CoreKanoAnalyzer):
    def generate_report(self, feature_results: List[KanoFeatureResult]) -> str:
        result = KanoAnalysisResult(
            survey=KanoSurvey([item.feature for item in feature_results]),
            feature_results=feature_results,
            summary={
                "total_features": len(feature_results),
                "by_category": {
                    "must_be": [item.feature.feature_id for item in feature_results if item.final_category == KanoCategory.MUST_BE],
                    "one_dimensional": [item.feature.feature_id for item in feature_results if item.final_category == KanoCategory.ONE_DIMENSIONAL],
                    "attractive": [item.feature.feature_id for item in feature_results if item.final_category == KanoCategory.ATTRACTIVE],
                    "indifferent": [item.feature.feature_id for item in feature_results if item.final_category == KanoCategory.INDIFFERENT],
                    "reverse": [item.feature.feature_id for item in feature_results if item.final_category == KanoCategory.REVERSE],
                    "questionable": [item.feature.feature_id for item in feature_results if item.final_category == KanoCategory.QUESTIONABLE],
                },
            },
            warnings=[],
        )
        return generate_report(result)

    def load_responses_from_csv(
        self,
        path: str,
        feature_id_column: str = "feature_id",
        functional_column: str = "functional",
        dysfunctional_column: str = "dysfunctional",
        respondent_column: str | None = None,
    ) -> List[SurveyResponse]:
        return load_responses_from_csv(
            path=path,
            feature_id_column=feature_id_column,
            functional_column=functional_column,
            dysfunctional_column=dysfunctional_column,
            respondent_column=respondent_column,
        )


def prompt_answer(question: str) -> int:
    valid_values = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "нравится": 1,
        "ожидаю": 2,
        "нейтрально": 3,
        "терплю": 4,
        "не нравится": 5,
    }
    scale = "1 - Мне нравится, 2 - Ожидаю, 3 - Нейтрально, 4 - Могу терпеть, 5 - Мне не нравится"
    while True:
        answer = input(f"{question} ({scale}): ").strip().lower()
        if answer in valid_values:
            return valid_values[answer]
        if answer.isdigit() and answer in valid_values:
            return valid_values[answer]
        print("Неверный ввод. Введите число от 1 до 5 или соответствующее слово.")


def collect_console_responses(survey: KanoSurvey, respondent_count: int) -> List[SurveyResponse]:
    responses: List[SurveyResponse] = []
    for respondent_index in range(1, respondent_count + 1):
        print(f"\n=== Респондент {respondent_index} ===")
        respondent: SurveyResponse = {}
        for feature in survey.features:
            functional = prompt_answer(
                f"Если в продукте реализовано свойство '{feature.name}', как вы к этому отнесетесь?"
            )
            dysfunctional = prompt_answer(
                f"Если в продукте отсутствует свойство '{feature.name}', как вы к этому отнесетесь?"
            )
            respondent[feature.feature_id] = (functional, dysfunctional)
        responses.append(respondent)
    return responses


def example_usage() -> None:
    print("Анализ требований по модели Кано")
    print("===============================")

    filename = input("Введите имя файла опросника (например, survey.json): ").strip()
    if not filename:
        filename = "survey.json"
    if not filename.endswith(".json"):
        filename += ".json"

    try:
        survey = load_survey(filename)
    except Exception as exc:
        print(f"Не удалось загрузить опросник: {exc}")
        return

    print("Сгенерированная структура опроса по шаблону модели Кано:")
    for question in survey.create_questionnaire():
        print(f"- [{question.type.value}] {question.text}")
        print(f"  Шкала: {', '.join(question.answer_scale)}")

    try:
        respondent_count = int(input("\nСколько респондентов вы хотите опросить? ").strip())
        if respondent_count < 1:
            raise ValueError
    except ValueError:
        print("Введите целое положительное число респондентов.")
        return

    responses = collect_console_responses(survey, respondent_count)
    result = analyze_kano(survey, responses, create_chart=True)
    print("\nОтчет по результатам анализа:\n")
    print(generate_report(result))


def load_survey_from_file(filename: str) -> KanoSurvey:
    return load_survey(filename)


if __name__ == "__main__":
    example_usage()
