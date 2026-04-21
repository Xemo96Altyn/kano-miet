from __future__ import annotations

from typing import Any, Dict, List

from .models import KanoAnalysisResult, KanoCategory, KanoFeatureResult


def summarize_feature_results(feature_results: List[KanoFeatureResult]) -> Dict[str, Any]:
    by_category = {
        "must_be": [result.feature.feature_id for result in feature_results if result.final_category == KanoCategory.MUST_BE],
        "one_dimensional": [result.feature.feature_id for result in feature_results if result.final_category == KanoCategory.ONE_DIMENSIONAL],
        "attractive": [result.feature.feature_id for result in feature_results if result.final_category == KanoCategory.ATTRACTIVE],
        "indifferent": [result.feature.feature_id for result in feature_results if result.final_category == KanoCategory.INDIFFERENT],
        "reverse": [result.feature.feature_id for result in feature_results if result.final_category == KanoCategory.REVERSE],
        "questionable": [result.feature.feature_id for result in feature_results if result.final_category == KanoCategory.QUESTIONABLE],
    }
    return {
        "total_features": len(feature_results),
        "by_category": by_category,
        "priority_order": by_category["must_be"] + by_category["one_dimensional"] + by_category["attractive"],
    }


def build_feature_results_payload(
    feature_results: List[KanoFeatureResult],
    include_pairs: bool = False,
) -> List[Dict[str, Any]]:
    return [result.as_dict(include_pairs=include_pairs) for result in feature_results]


def generate_report(analysis_result: KanoAnalysisResult) -> str:
    lines: List[str] = [
        "Отчет по анализу требований по модели Кано",
        "----------------------------------------",
    ]

    for result in analysis_result.feature_results:
        lines.append(f"Свойство: {result.feature.name} ({result.feature.feature_id})")
        lines.append(f"  Категория: {result.final_category.value} ({result.final_category.short()})")
        lines.append(
            f"  Ответы: {result.total_answers}, A={result.counts[KanoCategory.ATTRACTIVE]}, "
            f"O={result.counts[KanoCategory.ONE_DIMENSIONAL]}, M={result.counts[KanoCategory.MUST_BE]}, "
            f"I={result.counts[KanoCategory.INDIFFERENT]}, R={result.counts[KanoCategory.REVERSE]}, "
            f"Q={result.counts[KanoCategory.QUESTIONABLE]}"
        )
        lines.append(f"  Коэффициент удовлетворенности: {result.satisfaction_coefficient:.3f}")
        lines.append(f"  Коэффициент неудовлетворенности: {result.dissatisfaction_coefficient:.3f}")
        lines.append(f"  Интерпретация: {result.interpretation}")
        lines.append(f"  Рекомендация: {result.recommendation}")
        lines.append("")

    summary = analysis_result.summary["by_category"]
    lines.append("Стратегия по развитию продукта:")
    lines.append("")
    lines.append("1. Реализовать в первую очередь (обязательные): " + ", ".join(summary["must_be"]) if summary["must_be"] else "1. Реализовать в первую очередь (обязательные): нет")
    lines.append("2. Реализовать во вторую очередь (больше - лучше): " + ", ".join(summary["one_dimensional"]) if summary["one_dimensional"] else "2. Реализовать во вторую очередь (больше - лучше): нет")
    lines.append("3. Реализовать в третью очередь (для вау-эффекта): " + ", ".join(summary["attractive"]) if summary["attractive"] else "3. Реализовать в третью очередь (для вау-эффекта): нет")
    lines.append("4. Низкий приоритет: " + ", ".join(summary["indifferent"]) if summary["indifferent"] else "4. Низкий приоритет: нет")
    lines.append("5. Не реализовывать: " + ", ".join(summary["reverse"]) if summary["reverse"] else "5. Не реализовывать: нет")

    if analysis_result.warnings:
        lines.append("")
        lines.append("Предупреждения:")
        for warning in analysis_result.warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines)
