const dashboardState = {
  surveyId: "",
};

const surveyIdInput = document.getElementById("survey-id");
const loadDashboardButton = document.getElementById("load-dashboard");
const dashboardStatus = document.getElementById("dashboard-status");
const respondentCount = document.getElementById("respondent-count");
const dashboardMeta = document.getElementById("dashboard-meta");
const runAnalysisButton = document.getElementById("run-analysis");
const clearResponsesButton = document.getElementById("clear-responses");
const deleteSurveyButton = document.getElementById("delete-survey");
const surveyList = document.getElementById("survey-list");
const results = document.getElementById("results");
const resultsPlaceholder = document.getElementById("results-placeholder");
const summaryCards = document.getElementById("summary-cards");
const priorityBlock = document.getElementById("priority-block");
const warningBlock = document.getElementById("warning-block");
const featureResults = document.getElementById("feature-results");
const chartBlock = document.getElementById("chart-block");
const chartImage = document.getElementById("chart-image");

loadDashboardButton.addEventListener("click", () => refreshDashboard());
runAnalysisButton.addEventListener("click", () => runAnalysis());
clearResponsesButton.addEventListener("click", () => clearResponses());
deleteSurveyButton.addEventListener("click", () => deleteSurvey());

window.addEventListener("DOMContentLoaded", () => {
  const initialSurveyId = currentSurveyId();
  refreshSurveyList();
  if (initialSurveyId) {
    refreshDashboard();
  } else {
    resetDashboardView();
  }
});

function currentSurveyId() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  if (parts[0] === "dashboard" && parts[1]) {
    return decodeURIComponent(parts[1]);
  }
  return surveyIdInput.value.trim();
}

async function refreshDashboard() {
  dashboardState.surveyId = currentSurveyId();
  if (!dashboardState.surveyId) {
    dashboardStatus.textContent = "Введите идентификатор опроса, чтобы открыть аналитику.";
    resetDashboardView();
    return;
  }
  surveyIdInput.value = dashboardState.surveyId;
  dashboardStatus.textContent = "Обновление панели...";

  try {
    const surveyResponse = await fetch(`/api/survey?id=${encodeURIComponent(dashboardState.surveyId)}`);
    const surveyPayload = await surveyResponse.json();
    if (!surveyResponse.ok) {
      throw new Error(surveyPayload.error || "Не удалось загрузить опросник.");
    }

    const countResponse = await fetch(`/api/responses?id=${encodeURIComponent(dashboardState.surveyId)}`);
    const countPayload = await countResponse.json();
    if (!countResponse.ok) {
      throw new Error(countPayload.error || "Не удалось получить число респондентов.");
    }

    respondentCount.textContent = `Респондентов: ${countPayload.respondent_count}`;
    dashboardMeta.innerHTML = `
      <h3>${surveyPayload.survey.title || dashboardState.surveyId}</h3>
      <p>Идентификатор опроса: ${dashboardState.surveyId}</p>
      <p>Свойств в опроснике: ${surveyPayload.survey.features.length}</p>
      <p>Собрано ответов: ${countPayload.respondent_count}</p>
      <p>Страница опроса: <strong>/survey/${dashboardState.surveyId}</strong></p>
    `;
    dashboardStatus.textContent = "Панель обновлена.";
    await refreshSurveyList();
  } catch (error) {
    dashboardStatus.textContent = error.message;
  }
}

async function runAnalysis() {
  dashboardStatus.textContent = "Проводим анализ...";
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        survey_id: dashboardState.surveyId,
        create_chart: true,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось провести анализ.");
    }

    renderResults(payload);
    respondentCount.textContent = `Респондентов: ${payload.summary.respondent_count}`;
    dashboardStatus.textContent = "Анализ завершен.";
  } catch (error) {
    dashboardStatus.textContent = error.message;
  }
}

async function clearResponses() {
  if (!dashboardState.surveyId) {
    dashboardStatus.textContent = "Сначала укажите survey_id.";
    return;
  }
  const confirmed = window.confirm(
    `Очистить все ответы респондентов для опроса "${dashboardState.surveyId}"? Это действие нельзя отменить.`,
  );
  if (!confirmed) {
    return;
  }

  dashboardStatus.textContent = "Очищаем ответы...";
  try {
    const response = await fetch("/api/responses/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ survey_id: dashboardState.surveyId }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось очистить ответы.");
    }

    respondentCount.textContent = "Респондентов: 0";
    resetResults();
    dashboardStatus.textContent = "Ответы очищены.";
    await refreshDashboard();
  } catch (error) {
    dashboardStatus.textContent = error.message;
  }
}

async function deleteSurvey() {
  if (!dashboardState.surveyId) {
    dashboardStatus.textContent = "Сначала укажите survey_id.";
    return;
  }
  const confirmed = window.confirm(
    `Удалить опрос "${dashboardState.surveyId}" полностью вместе с ответами? Это действие нельзя отменить.`,
  );
  if (!confirmed) {
    return;
  }

  dashboardStatus.textContent = "Удаляем опрос...";
  try {
    const response = await fetch("/api/survey/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ survey_id: dashboardState.surveyId }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось удалить опрос.");
    }

    surveyIdInput.value = "";
    dashboardState.surveyId = "";
    resetDashboardView();
    await refreshSurveyList();
    dashboardStatus.textContent = `Опрос "${payload.survey_id}" удален.`;
  } catch (error) {
    dashboardStatus.textContent = error.message;
  }
}

function renderResults(result) {
  resultsPlaceholder.classList.add("hidden");
  results.classList.remove("hidden");

  summaryCards.innerHTML = [
    summaryCard("Свойств", result.summary.total_features),
    summaryCard("Респондентов", result.summary.respondent_count),
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

function resetResults() {
  results.classList.add("hidden");
  resultsPlaceholder.classList.remove("hidden");
  chartImage.removeAttribute("src");
}

function resetDashboardView() {
  respondentCount.textContent = "Респондентов: 0";
  dashboardMeta.innerHTML = "Введите `survey_id` и нажмите «Обновить».";
  resetResults();
}

async function refreshSurveyList() {
  try {
    const response = await fetch("/api/surveys");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось получить список опросов.");
    }

    surveyList.innerHTML = payload.items
      .map(
        (item) => {
          // Если бэкенд прислал данные автора (значит мы админ), формируем строчку
          const creatorHtml = item.creator_name 
            ? `<p class="muted" style="margin: 0 0 10px 0; font-size: 13px;">👤 Автор: <strong>${item.creator_name}</strong> (@${item.creator_username})</p>` 
            : '';

          return `
          <article class="feature-card">
            <div class="feature-top">
              <div>
                <div class="feature-code">${item.survey_id}</div>
                <h3>${item.title}</h3>
              </div>
              <span class="pill">${item.respondent_count} ответов</span>
            </div>
            ${creatorHtml} <!-- Вставляем строчку с автором сюда -->
            <p>Свойств: ${item.feature_count}</p>
            <div class="actions">
              <a class="btn btn-secondary btn-link" href="${item.survey_url}" target="_blank">Страница опроса</a>
              <a class="btn btn-ghost btn-link" href="${item.dashboard_url}" target="_blank">Панель анализа</a>
            </div>
          </article>
        `}
      )
      .join("");
  } catch (error) {
    surveyList.innerHTML = `<div class="empty-state">${error.message}</div>`;
  }
}
