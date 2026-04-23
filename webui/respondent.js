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
const statusKinds = ["status-error", "status-success", "status-busy"];

loadSurveyButton.addEventListener("click", () => loadSurvey());
submitResponseButton.addEventListener("click", () => submitResponse());
resetFormButton.addEventListener("click", () => surveyForm.reset());

window.addEventListener("DOMContentLoaded", () => loadSurvey());

function setSurveyStatus(message, kind = "") {
  surveyStatus.textContent = message;
  surveyStatus.classList.remove(...statusKinds);
  if (kind) {
    surveyStatus.classList.add(kind);
  }
}

function currentSurveyId() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  const surveyIndex = parts.findIndex((part) => part === "survey");
  if (surveyIndex !== -1 && parts[surveyIndex + 1]) {
    return decodeURIComponent(parts[surveyIndex + 1]);
  }
  return surveyIdInput.value.trim() || "telega";
}

async function loadSurvey() {
  const surveyId = currentSurveyId();
  surveyIdInput.value = surveyId;
  setSurveyStatus("Загрузка опросника...", "status-busy");
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
    setSurveyStatus(`Опросник ${state.survey.title || state.surveyId} загружен. Можно отвечать.`, "status-success");
  } catch (error) {
    setSurveyStatus(error.message, "status-error");
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
    setSurveyStatus("Сначала загрузите опросник.", "status-error");
    return;
  }

  const responsePayload = {};
  for (const feature of state.survey.features) {
    const functional = surveyForm.querySelector(`input[name="${feature.feature_id}-functional"]:checked`);
    const dysfunctional = surveyForm.querySelector(`input[name="${feature.feature_id}-dysfunctional"]:checked`);

    if (!functional || !dysfunctional) {
      showError(`Для свойства "${feature.name}" нужно заполнить оба ответа, иначе отправка невозможна.`);
      setSurveyStatus("Опрос заполнен не полностью.", "status-error");
      return;
    }

    responsePayload[feature.feature_id] = [Number(functional.value), Number(dysfunctional.value)];
  }

  setSurveyStatus("Отправка ответов...", "status-busy");
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
    setSurveyStatus(`Спасибо! Ваши ответы сохранены. Всего респондентов: ${payload.respondent_count}.`, "status-success");
  } catch (error) {
    showError(error.message);
    setSurveyStatus(error.message, "status-error");
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
