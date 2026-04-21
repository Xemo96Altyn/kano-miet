from __future__ import annotations

from kano_analysis import KanoSurvey, load_survey, save_survey


def create_new_survey() -> KanoSurvey:
    survey = KanoSurvey()
    print("Создание нового опросника по модели Кано")
    print("=========================================")

    while True:
        print("\nДобавьте свойство продукта:")
        feature_id = input("Идентификатор свойства (например, F1): ").strip()
        if not feature_id:
            break

        name = input("Название свойства: ").strip()
        if not name:
            print("Название обязательно. Попробуйте снова.")
            continue

        description = input("Описание свойства (опционально): ").strip()
        survey.add_feature(feature_id=feature_id, name=name, description=description)
        print(f"Свойство '{name}' добавлено.")

        more = input("Добавить еще свойство? (y/n): ").strip().lower()
        if more not in ("y", "yes", "да"):
            break

    return survey


def display_questionnaire(survey: KanoSurvey) -> None:
    print("\nСгенерированный опросник по модели Кано:")
    print("========================================")

    for index, question in enumerate(survey.create_questionnaire(), start=1):
        print(f"{index}. [{question.type.value}] {question.text}")
        print(f"   Шкала: {', '.join(question.answer_scale)}")
        print()


def main() -> None:
    print("Инструмент создания опросников по модели Кано")
    print("=============================================")
    print("Выберите действие:")
    print("1. Создать новый опросник")
    print("2. Загрузить существующий опросник")
    print("3. Выход")

    choice = input("Ваш выбор (1-3): ").strip()

    if choice == "1":
        survey = create_new_survey()
        if not survey.features:
            print("Опросник пустой. Выход.")
            return

        display_questionnaire(survey)
        filename = input("Введите имя файла для сохранения (например, survey.json): ").strip()
        if not filename:
            filename = "survey.json"
        if not filename.endswith(".json"):
            filename += ".json"

        try:
            path = save_survey(survey, filename)
            print(f"Опросник сохранен в файл: {path}")
        except Exception as exc:
            print(f"Не удалось сохранить опросник: {exc}")

    elif choice == "2":
        filename = input("Введите имя файла для загрузки (например, survey.json): ").strip()
        if not filename:
            filename = "survey.json"
        if not filename.endswith(".json"):
            filename += ".json"

        try:
            survey = load_survey(filename)
        except Exception as exc:
            print(f"Не удалось загрузить опросник: {exc}")
            return

        display_questionnaire(survey)
        edit = input("Хотите отредактировать опросник? (y/n): ").strip().lower()
        if edit in ("y", "yes", "да"):
            print("Добавление новых свойств:")
            while True:
                feature_id = input("Идентификатор свойства (или пусто для завершения): ").strip()
                if not feature_id:
                    break

                name = input("Название свойства: ").strip()
                if not name:
                    continue

                description = input("Описание свойства (опционально): ").strip()
                survey.add_feature(feature_id=feature_id, name=name, description=description)
                print(f"Свойство '{name}' добавлено.")

            display_questionnaire(survey)
            save = input("Сохранить изменения? (y/n): ").strip().lower()
            if save in ("y", "yes", "да"):
                try:
                    path = save_survey(survey, filename)
                    print(f"Опросник сохранен в файл: {path}")
                except Exception as exc:
                    print(f"Не удалось сохранить изменения: {exc}")

    elif choice == "3":
        print("Выход.")
    else:
        print("Неверный выбор.")


if __name__ == "__main__":
    main()
