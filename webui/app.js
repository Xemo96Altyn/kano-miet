const scaleLabels = {
  1: "Нравится",
  2: "Ожидаю",
  3: "Нейтрально",
  4: "Терпимо",
  5: "Не нравится",
};

const state = {
  surveyFile: "telega.json",
  survey: null,
  questionnaire: [],
  responses: [],
};

const surveyFileInput = document.getElementById("survey-file");
const loadSurveyButton = document.getElementById("load-survey");
const surveyStatus = document.getElementById("survey-status");
const emptyState = document.getElementById("empty-state");
const surveyForm = document.getElementById("survey-form");
const formActions = document.getElementById("form-actions");
const respondentCount = document.getElementById("respondent-count");
const addRespondentButton = document.getElementById("add-respondent");
const runAnalysisButton = document.getElementById("run-analysis");
const resetRespondentsButton = document.getElementById("reset-respondents");
const results = document.getElementById("results");
const resultsPlaceholder = document.getElementById("results-placeholder");
const summaryCards = document.getElementById("summary-cards");
const priorityBlock = document.getElementById("priority-block");
const warningBlock = document.getElementById("warning-block");
const featureResults = document.getElementById("feature-results");
const chartBlock = document.getElementById("chart-block");
const chartImage = document.getElementById("chart-image");

loadSurveyButton.addEventListener("click", () => loadSurvey());
addRespondentButton.addEventListener("click", () => addRespondent());
runAnalysisButton.addEventListener("click", () => runAnalysis());
resetRespondentsButton.addEventListener("click", () => resetResponses());

window.addEventListener("DOMContentLoaded", () => {
  loadSurvey();
});

async function loadSurvey() {
  const file = surveyFileInput.value.trim() || "telega.json";
  surveyStatus.textContent = "Загрузка опросника...";

  try {
    const response = await fetch(`/api/survey?file=${encodeURIComponent(file)}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось загрузить опросник.");
    }

    state.surveyFile = payload.survey_file;
    state.survey = payload.survey;
    state.questionnaire = payload.questionnaire;
    state.responses = [];

    renderSurvey();
    resetResults();
    surveyStatus.textContent = `Загружен опросник: ${state.surveyFile}`;
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
      <p class="question-desc">${feature.description || "Описание не задано. Для анализа используется название свойства."}</p>
      <div class="question-grid">
        ${buildAnswerBlock(feature.feature_id, "functional", functionalQuestion?.question_text || "")}
        ${buildAnswerBlock(feature.feature_id, "dysfunctional", dysfunctionalQuestion?.question_text || "")}
      </div>
    `;
    surveyForm.appendChild(card);
  });

  emptyState.classList.add("hidden");
  surveyForm.classList.remove("hidden");
  formActions.classList.remove("hidden");
  updateRespondentCounter();
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

function addRespondent() {
  if (!state.survey) {
    surveyStatus.textContent = "Сначала загрузите опросник.";
    return;
  }

  const response = {};
  for (const feature of state.survey.features) {
    const functional = surveyForm.querySelector(`input[name="${feature.feature_id}-functional"]:checked`);
    const dysfunctional = surveyForm.querySelector(`input[name="${feature.feature_id}-dysfunctional"]:checked`);

    if (!functional || !dysfunctional) {
      surveyStatus.textContent = `Для свойства "${feature.name}" нужно заполнить оба ответа.`;
      return;
    }

    response[feature.feature_id] = [Number(functional.value), Number(dysfunctional.value)];
  }

  state.responses.push(response);
  surveyStatus.textContent = `Респондент #${state.responses.length} добавлен в выборку.`;
  updateRespondentCounter();
  surveyForm.reset();
}

async function runAnalysis() {
  if (!state.survey) {
    surveyStatus.textContent = "Сначала загрузите опросник.";
    return;
  }
  if (!state.responses.length) {
    surveyStatus.textContent = "Добавьте хотя бы одного респондента перед анализом.";
    return;
  }

  surveyStatus.textContent = "Проводим анализ...";

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        survey: state.survey,
        responses: state.responses,
        create_chart: true,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось провести анализ.");
    }

    renderResults(payload);
    surveyStatus.textContent = "Анализ завершен.";
  } catch (error) {
    surveyStatus.textContent = error.message;
  }
}

function renderResults(result) {
  resultsPlaceholder.classList.add("hidden");
  results.classList.remove("hidden");

  summaryCards.innerHTML = [
    summaryCard("Свойств", result.summary.total_features),
    summaryCard("Респондентов", state.responses.length),
    summaryCard("Приоритетов", result.summary.priority_order.length),
  ].join("");

  const byCategory = result.summary.by_category;
  priorityBlock.innerHTML = `
    <h3>Порядок развития</h3>
    <p class="result-meta">Сформировано на основе итоговых категорий Кано.</p>
    <p><strong>1 очередь:</strong> ${formatList(byCategory.must_be)}</p>
    <p><strong>2 очередь:</strong> ${formatList(byCategory.one_dimensional)}</p>
    <p><strong>3 очередь:</strong> ${formatList(byCategory.attractive)}</p>
    <p><strong>Низкий приоритет:</strong> ${formatList(byCategory.indifferent)}</p>
    <p><strong>Не реализовывать:</strong> ${formatList(byCategory.reverse)}</p>
    <p><strong>Questionable:</strong> ${formatList(byCategory.questionable)}</p>
  `;

  if (result.warnings?.length) {
    warningBlock.classList.remove("hidden");
    warningBlock.innerHTML = `
      <h3>Предупреждения</h3>
      ${result.warnings.map((warning) => `<p>${warning}</p>`).join("")}
    `;
  } else {
    warningBlock.classList.add("hidden");
    warningBlock.innerHTML = "";
  }

  featureResults.innerHTML = result.feature_results.map(renderFeatureCard).join("");

  if (result.summary.chart_url) {
    chartBlock.classList.remove("hidden");
    chartImage.src = `${result.summary.chart_url}?t=${Date.now()}`;
  } else {
    chartBlock.classList.add("hidden");
    chartImage.removeAttribute("src");
  }
}

function renderFeatureCard(item) {
  const metrics = [
    `A: ${item.counts.A}`,
    `O: ${item.counts.O}`,
    `M: ${item.counts.M}`,
    `I: ${item.counts.I}`,
    `R: ${item.counts.R}`,
    `Q: ${item.counts.Q}`,
    `Удовл.: ${item.satisfaction_coefficient}`,
    `Неудовл.: ${item.dissatisfaction_coefficient}`,
  ]
    .map((metric) => `<span class="metric-chip">${metric}</span>`)
    .join("");

  return `
    <article class="feature-card">
      <div class="feature-top">
        <div>
          <div class="feature-code">${item.feature_id}</div>
          <h3>${item.feature_name}</h3>
        </div>
        <span class="pill">${item.final_category_code} · ${item.final_category}</span>
      </div>
      <div class="metrics">${metrics}</div>
      <p>${item.interpretation}</p>
      <p><strong>Рекомендация:</strong> ${item.recommendation}</p>
    </article>
  `;
}

function summaryCard(label, value) {
  return `
    <div class="summary-card">
      <div class="summary-label">${label}</div>
      <div class="summary-value">${value}</div>
    </div>
  `;
}

function formatList(items) {
  return items && items.length ? items.join(", ") : "нет";
}

function updateRespondentCounter() {
  respondentCount.textContent = `Респондентов: ${state.responses.length}`;
}

function resetResponses() {
  state.responses = [];
  surveyForm.reset();
  updateRespondentCounter();
  surveyStatus.textContent = "Ответы респондентов сброшены.";
  resetResults();
}

function resetResults() {
  results.classList.add("hidden");
  resultsPlaceholder.classList.remove("hidden");
  chartImage.removeAttribute("src");
}
