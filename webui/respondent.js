const scaleLabels = {
  1: "Нравится",
  2: "Ожидаю",
  3: "Нейтрально",
  4: "Терпимо",
  5: "Не нравится",
};

const state = {
  surveyId: "telega",
  survey: null,
  questionnaire: [],
};

const surveyIdInput = document.getElementById("survey-id");
const loadSurveyButton = document.getElementById("load-survey");
const surveyStatus = document.getElementById("survey-status");
const emptyState = document.getElementById("empty-state");
const errorState = document.getElementById("error-state");
const surveyForm = document.getElementById("survey-form");
const formActions = document.getElementById("form-actions");
const submitResponseButton = document.getElementById("submit-response");
const resetFormButton = document.getElementById("reset-form");
const thankYouState = document.getElementById("thank-you-state");

loadSurveyButton.addEventListener("click", () => loadSurvey());
submitResponseButton.addEventListener("click", () => submitResponse());
resetFormButton.addEventListener("click", () => surveyForm.reset());

window.addEventListener("DOMContentLoaded", () => loadSurvey());

function currentSurveyId() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  if (parts[0] === "survey" && parts[1]) {
    return decodeURIComponent(parts[1]);
  }
  return surveyIdInput.value.trim() || "telega";
}

async function loadSurvey() {
  const surveyId = currentSurveyId();
  surveyIdInput.value = surveyId;
  surveyStatus.textContent = "Загрузка опросника...";
  hideError();
  thankYouState.classList.add("hidden");

  try {
    const response = await fetch(`/api/survey?id=${encodeURIComponent(surveyId)}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось загрузить опросник.");
    }

    state.surveyId = payload.survey_id;
    state.survey = payload.survey;
    state.questionnaire = payload.questionnaire;
    renderSurvey();
    surveyStatus.textContent = `Опросник ${state.survey.title || state.surveyId} загружен. Можно отвечать.`;
  } catch (error) {
    surveyStatus.textContent = error.message;
  }
}

function renderSurvey() {
  const features = state.survey?.features || [];
  surveyForm.innerHTML = "";

  features.forEach((feature) => {
    const functionalQuestion = state.questionnaire.find(
      (item) => item.feature_id === feature.feature_id && item.question_type === "Функциональный",
    );
    const dysfunctionalQuestion = state.questionnaire.find(
      (item) => item.feature_id === feature.feature_id && item.question_type === "Дисфункциональный",
    );

    const card = document.createElement("section");
    card.className = "question-card";
    card.innerHTML = `
      <div class="question-title">${feature.name}</div>
      <p class="question-desc">${feature.description || "Описание не задано. Ориентируйтесь на название свойства."}</p>
      <div class="question-grid">
        ${buildAnswerBlock(feature.feature_id, "functional", functionalQuestion?.question_text || "")}
        ${buildAnswerBlock(feature.feature_id, "dysfunctional", dysfunctionalQuestion?.question_text || "")}
      </div>
    `;
    surveyForm.appendChild(card);
  });

  emptyState.classList.add("hidden");
  thankYouState.classList.add("hidden");
  surveyForm.classList.remove("hidden");
  formActions.classList.remove("hidden");
}

function buildAnswerBlock(featureId, kind, questionText) {
  const options = [1, 2, 3, 4, 5]
    .map(
      (value) => `
        <label class="scale-option">
          <input type="radio" name="${featureId}-${kind}" value="${value}">
          <span>${value}<br>${scaleLabels[value]}</span>
        </label>
      `,
    )
    .join("");

  return `
    <div class="answer-block">
      <span class="answer-label">${questionText}</span>
      <div class="scale-grid">${options}</div>
    </div>
  `;
}

async function submitResponse() {
  if (!state.survey) {
    surveyStatus.textContent = "Сначала загрузите опросник.";
    return;
  }

  const responsePayload = {};
  for (const feature of state.survey.features) {
    const functional = surveyForm.querySelector(`input[name="${feature.feature_id}-functional"]:checked`);
    const dysfunctional = surveyForm.querySelector(`input[name="${feature.feature_id}-dysfunctional"]:checked`);

    if (!functional || !dysfunctional) {
      showError(`Для свойства "${feature.name}" нужно заполнить оба ответа, иначе отправка невозможна.`);
      surveyStatus.textContent = "Опрос заполнен не полностью.";
      return;
    }

    responsePayload[feature.feature_id] = [Number(functional.value), Number(dysfunctional.value)];
  }

  surveyStatus.textContent = "Отправка ответов...";
  hideError();
  try {
    const response = await fetch("/api/respond", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        survey_id: state.surveyId,
        response: responsePayload,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось отправить ответы.");
    }

    surveyForm.reset();
    surveyForm.classList.add("hidden");
    formActions.classList.add("hidden");
    thankYouState.classList.remove("hidden");
    surveyStatus.textContent = `Спасибо! Ваши ответы сохранены. Всего респондентов: ${payload.respondent_count}.`;
  } catch (error) {
    showError(error.message);
    surveyStatus.textContent = error.message;
  }
}

function showError(message) {
  errorState.textContent = message;
  errorState.classList.remove("hidden");
}

function hideError() {
  errorState.textContent = "";
  errorState.classList.add("hidden");
}
