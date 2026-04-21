const builderStatus = document.getElementById("builder-status");
const surveyTitleInput = document.getElementById("survey-title");
const featureList = document.getElementById("feature-list");
const addFeatureButton = document.getElementById("add-feature");
const createSurveyButton = document.getElementById("create-survey");
const createdLinks = document.getElementById("created-links");

addFeatureButton.addEventListener("click", () => addFeaturePair());
createSurveyButton.addEventListener("click", () => createSurvey());

window.addEventListener("DOMContentLoaded", async () => {
  addFeaturePair();
});

function addFeatureRow(name = "", description = "") {
  const row = document.createElement("section");
  row.className = "question-card";
  row.innerHTML = `
    <div class="field-stack">
      <label class="field-label">Название свойства</label>
      <input type="text" class="feature-name" value="${escapeHtml(name)}" placeholder="Например, Безопасность">
    </div>
    <div class="field-stack">
      <label class="field-label">Описание свойства</label>
      <input type="text" class="feature-description" value="${escapeHtml(description)}" placeholder="Необязательно">
    </div>
    <button class="btn btn-ghost remove-feature" type="button">Удалить</button>
  `;

  row.querySelector(".remove-feature").addEventListener("click", () => {
    row.remove();
  });

  featureList.appendChild(row);
}

function addFeaturePair() {
  addFeatureRow();
  addFeatureRow();
}

async function createSurvey() {
  const title = surveyTitleInput.value.trim();
  const features = Array.from(featureList.querySelectorAll(".question-card"))
    .map((card) => ({
      name: card.querySelector(".feature-name").value.trim(),
      description: card.querySelector(".feature-description").value.trim(),
    }))
    .filter((item) => item.name);

  if (!title) {
    builderStatus.textContent = "Название опроса обязательно.";
    return;
  }
  if (!features.length) {
    builderStatus.textContent = "Добавьте хотя бы одно свойство.";
    return;
  }

  builderStatus.textContent = "Создаем опрос...";
  try {
    const response = await fetch("/api/surveys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, features }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось создать опрос.");
    }

    createdLinks.classList.remove("empty-state");
    createdLinks.innerHTML = `
      <h3>${title}</h3>
      <div class="actions">
        <a class="btn btn-secondary btn-link" href="${payload.survey_url}" target="_blank">Открыть опрос респондента</a>
        <a class="btn btn-ghost btn-link" href="${payload.dashboard_url}" target="_blank">Открыть панель анализа</a>
      </div>
      <p><strong>ID опроса:</strong> ${payload.survey_id}</p>
    `;
    builderStatus.textContent = "Опрос создан и сохранен на сервере.";
    surveyTitleInput.value = "";
    featureList.innerHTML = "";
    addFeaturePair();
  } catch (error) {
    builderStatus.textContent = error.message;
  }
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
