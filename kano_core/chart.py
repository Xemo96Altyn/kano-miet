from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .models import KanoCategory, KanoFeatureResult


def create_matrix_chart(
    feature_results: List[KanoFeatureResult],
    output_path: str | Path = "kano_matrix.png",
) -> Path | None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    cell_width = 150
    cell_height = 120
    margin_left = 180
    margin_top = 100
    margin_right = 40
    margin_bottom = 40
    img_width = cell_width * 5 + margin_left + margin_right
    img_height = cell_height * 5 + margin_top + margin_bottom

    img = Image.new("RGB", (img_width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf", 22)
        font_cell = ImageFont.truetype("/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf", 16)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf", 18)
    except Exception:
        font_header = font_cell = font_label = ImageFont.load_default()

    category_matrix: Dict[int, Dict[int, KanoCategory]] = {
        1: {1: KanoCategory.QUESTIONABLE, 2: KanoCategory.ATTRACTIVE, 3: KanoCategory.ATTRACTIVE, 4: KanoCategory.ATTRACTIVE, 5: KanoCategory.ONE_DIMENSIONAL},
        2: {1: KanoCategory.REVERSE, 2: KanoCategory.QUESTIONABLE, 3: KanoCategory.INDIFFERENT, 4: KanoCategory.INDIFFERENT, 5: KanoCategory.MUST_BE},
        3: {1: KanoCategory.REVERSE, 2: KanoCategory.INDIFFERENT, 3: KanoCategory.INDIFFERENT, 4: KanoCategory.INDIFFERENT, 5: KanoCategory.MUST_BE},
        4: {1: KanoCategory.REVERSE, 2: KanoCategory.INDIFFERENT, 3: KanoCategory.INDIFFERENT, 4: KanoCategory.INDIFFERENT, 5: KanoCategory.MUST_BE},
        5: {1: KanoCategory.REVERSE, 2: KanoCategory.REVERSE, 3: KanoCategory.REVERSE, 4: KanoCategory.REVERSE, 5: KanoCategory.QUESTIONABLE},
    }

    color_map = {
        KanoCategory.ATTRACTIVE: (50, 168, 82),
        KanoCategory.ONE_DIMENSIONAL: (255, 179, 0),
        KanoCategory.MUST_BE: (214, 40, 40),
        KanoCategory.INDIFFERENT: (158, 161, 166),
        KanoCategory.REVERSE: (138, 43, 226),
        KanoCategory.QUESTIONABLE: (85, 85, 85),
    }

    matrix: Dict[Tuple[int, int], List[str]] = {(i, j): [] for i in range(1, 6) for j in range(1, 6)}
    for result in feature_results:
        for f_ans, d_ans in result.pairs:
            if 1 <= f_ans <= 5 and 1 <= d_ans <= 5:
                matrix[(f_ans, d_ans)].append(result.feature.feature_id)

    for d in range(1, 6):
        for f in range(1, 6):
            x0 = margin_left + (f - 1) * cell_width
            y0 = margin_top + (d - 1) * cell_height
            x1 = x0 + cell_width
            y1 = y0 + cell_height

            category = category_matrix[d][f]
            draw.rectangle((x0, y0, x1, y1), fill=color_map[category], outline=(0, 0, 0), width=2)

            for idx, feature_id in enumerate(matrix[(d, f)][:6]):
                row = idx // 2
                col = idx % 2
                dot_x = x0 + 20 + col * 65
                dot_y = y0 + 25 + row * 30
                draw.ellipse((dot_x - 5, dot_y - 5, dot_x + 5, dot_y + 5), fill=(0, 0, 0), outline=(255, 255, 255), width=1)
                draw.text((dot_x + 8, dot_y - 8), feature_id, fill=(0, 0, 0), font=font_cell)

            draw.text((x0 + 5, y1 - 22), category.short(), fill=(255, 255, 255), font=font_label)

    answer_labels = ["1\nМне нравится", "2\nОжидаю", "3\nНейтрально", "4\nМогу терпеть", "5\nМне не нравится"]
    for i, label in enumerate(answer_labels):
        x = margin_left + i * cell_width + cell_width // 2
        draw.text((x - 65, margin_top - 45), label, fill=(0, 0, 0), font=font_cell)

    for i, label in enumerate(answer_labels):
        y = margin_top + i * cell_height + cell_height // 2
        draw.text((47, y - 20), label, fill=(0, 0, 0), font=font_cell)

    draw.text((margin_left + cell_width * 2 - 50, margin_top - 80), "Свойство отсутствует", fill=(0, 0, 0), font=font_header)

    from PIL import Image as PILImage

    left_text_img = PILImage.new("RGBA", (200, 50), (255, 255, 255, 0))
    left_text_draw = ImageDraw.Draw(left_text_img)
    left_text_draw.text((5, 5), "Свойство есть", fill=(0, 0, 0), font=font_header)
    left_text_rotated = left_text_img.rotate(90, expand=True)
    img.paste(left_text_rotated, (5, margin_top + cell_height * 2 - 80), left_text_rotated)

    destination = Path(output_path)
    img.save(destination)
    return destination
