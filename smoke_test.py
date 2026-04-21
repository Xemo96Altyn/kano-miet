from __future__ import annotations

import json
from pathlib import Path

from kano_core.service import analyze_kano_payload


def main() -> None:
    survey_path = Path("telega.json")
    survey = json.loads(survey_path.read_text(encoding="utf-8"))

    responses = [
        {
            "А1": (5, 1),
            "А2": (2, 4),
            "А3": (1, 5),
            "А4": (2, 5),
            "А5": (3, 3),
        },
    ]

    result = analyze_kano_payload(survey, responses, create_chart=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
