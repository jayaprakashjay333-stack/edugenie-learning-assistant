const form = document.querySelector("#assistant-form");
const taskSelect = document.querySelector("#task");
const levelField = document.querySelector("#level-field");
const levelSelect = document.querySelector("#level");
const input = document.querySelector("#user-input");
const inputLabel = document.querySelector("#input-label");
const inputHint = document.querySelector("#input-hint");
const submitButton = document.querySelector("#submit-button");
const buttonLabel = document.querySelector("#button-label");
const resultPanel = document.querySelector("#result-panel");
const resultTitle = document.querySelector("#result-title");
const statusMessage = document.querySelector("#status-message");
const resultContent = document.querySelector("#result-content");
const logoutButton = document.querySelector("#logout-button");

const taskDetails = {
  explain: {
    endpoint: "/explain",
    label: "What would you like to understand?",
    placeholder: "For example: How does photosynthesis work?",
    hint: "A specific topic works best.",
    button: "Explain it",
    title: "A clearer explanation",
    field: "topic",
  },
  qa: {
    endpoint: "/qa",
    label: "What is your question?",
    placeholder: "For example: Which is the largest ocean?",
    hint: "Ask one question at a time.",
    button: "Get an answer",
    title: "Your answer",
    field: "question",
  },
  quiz: {
    endpoint: "/quiz",
    label: "Paste a topic or passage for your quiz",
    placeholder: "Add a topic, your notes, or a short passage (at least 20 characters).",
    hint: "You'll get three questions with four choices each.",
    button: "Generate quiz",
    title: "Check your understanding",
    field: "text",
  },
  summarize: {
    endpoint: "/summarize",
    label: "What would you like summarized?",
    placeholder: "Paste the passage you'd like to review (at least 20 characters).",
    hint: "A focused passage makes a clearer summary.",
    button: "Summarize it",
    title: "The key points",
    field: "text",
  },
  learn: {
    endpoint: "/learn/recommendations",
    label: "What would you like to learn?",
    placeholder: "For example: SQL, from the basics to query optimization.",
    hint: "We'll organize a path from your current level.",
    button: "Build my path",
    title: "Your learning path",
    field: "topic",
  },
};

function updateTaskFields() {
  const details = taskDetails[taskSelect.value];
  inputLabel.textContent = details.label;
  input.placeholder = details.placeholder;
  inputHint.textContent = details.hint;
  buttonLabel.textContent = details.button;
  levelField.hidden = taskSelect.value !== "learn";
  input.maxLength = details.field === "text" ? "30000" : "4000";
  input.rows = details.field === "text" ? 8 : 5;
}

function showStatus(message, isError = false) {
  statusMessage.hidden = !message;
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

function showTextResult(text) {
  const paragraph = document.createElement("p");
  paragraph.className = "answer-text";
  paragraph.textContent = text;
  resultContent.replaceChildren(paragraph);
}

function showQuiz(questions) {
  if (!Array.isArray(questions) || questions.length !== 3) {
    throw new Error("The quiz response was incomplete. Please try again.");
  }
  const fragment = document.createDocumentFragment();

  questions.forEach((question, questionIndex) => {
    if (
      typeof question.question !== "string" ||
      !Array.isArray(question.options) ||
      question.options.length !== 4 ||
      typeof question.correct_answer !== "string"
    ) {
      throw new Error("The quiz response was incomplete. Please try again.");
    }

    const fieldset = document.createElement("fieldset");
    fieldset.className = "quiz-question";
    const legend = document.createElement("legend");
    legend.textContent = `${questionIndex + 1}. ${question.question}`;
    fieldset.append(legend);

    const feedback = document.createElement("p");
    feedback.className = "quiz-feedback";
    feedback.hidden = true;

    question.options.forEach((option, optionIndex) => {
      const label = document.createElement("label");
      label.className = "quiz-option";
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = `question-${questionIndex}`;
      radio.value = option;
      radio.addEventListener("change", () => {
        const isCorrect = option === question.correct_answer;
        fieldset.querySelectorAll("input").forEach((choice) => {
          choice.disabled = true;
        });
        feedback.classList.toggle("correct", isCorrect);
        feedback.classList.toggle("incorrect", !isCorrect);
        feedback.textContent = isCorrect
          ? `Correct. ${question.explanation}`
          : `Not quite. The correct answer is: ${question.correct_answer}. ${question.explanation}`;
        feedback.hidden = false;
      });
      label.append(radio, document.createTextNode(` ${option}`));
      fieldset.append(label);
    });

    fieldset.append(feedback);
    fragment.append(fieldset);
  });

  resultContent.replaceChildren(fragment);
}

taskSelect.addEventListener("change", updateTaskFields);
updateTaskFields();

logoutButton.addEventListener("click", async () => {
  logoutButton.disabled = true;
  try {
    const response = await fetch("/auth/logout", {
      method: "POST",
      credentials: "same-origin",
    });
    if (!response.ok) {
      throw new Error("Could not sign out. Please try again.");
    }
    window.location.assign("/login");
  } catch (error) {
    logoutButton.disabled = false;
    window.alert(
      error instanceof Error ? error.message : "Could not sign out. Please try again."
    );
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const details = taskDetails[taskSelect.value];
  const value = input.value.trim();
  if (value.length < 2) {
    input.focus();
    return;
  }

  resultPanel.hidden = false;
  resultTitle.textContent = details.title;
  resultContent.replaceChildren();
  showStatus("Putting together a thoughtful response…");
  submitButton.disabled = true;
  buttonLabel.textContent = "Working…";

  const payload = { [details.field]: value };
  if (taskSelect.value === "learn") {
    payload.level = levelSelect.value;
  }

  try {
    const response = await fetch(details.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = data?.detail;
      const message = Array.isArray(detail)
        ? detail
            .map((issue) => {
              const field = Array.isArray(issue.loc) ? issue.loc.at(-1) : null;
              return field && issue.msg ? `${field}: ${issue.msg}` : issue.msg;
            })
            .filter(Boolean)
            .join(" ")
        : detail;
      throw new Error(
        typeof message === "string" && message
          ? message
          : "The request could not be completed."
      );
    }

    if (taskSelect.value === "quiz") {
      showQuiz(data.questions);
    } else if (typeof data.result === "string" && data.result.trim()) {
      showTextResult(data.result);
    } else {
      throw new Error("The assistant returned an empty response. Please try again.");
    }
    showStatus("");
  } catch (error) {
    showStatus(
      error instanceof Error ? error.message : "Something went wrong. Please try again.",
      true
    );
  } finally {
    submitButton.disabled = false;
    buttonLabel.textContent = details.button;
  }
});
