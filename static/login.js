const authForm = document.querySelector("#auth-form");
const modeTabs = [...document.querySelectorAll(".auth-tab")];
const nameField = document.querySelector("#name-field");
const displayName = document.querySelector("#display-name");
const emailInput = document.querySelector("#email");
const passwordInput = document.querySelector("#password");
const authTitle = document.querySelector("#auth-title");
const authSubtitle = document.querySelector("#auth-subtitle");
const submitButton = document.querySelector("#auth-submit");
const submitLabel = document.querySelector("#auth-submit-label");
const authMessage = document.querySelector("#auth-message");

let mode = "signin";

function setMode(nextMode) {
  mode = nextMode;
  const isSignup = mode === "signup";
  nameField.hidden = !isSignup;
  displayName.disabled = !isSignup;
  displayName.required = isSignup;
  passwordInput.autocomplete = isSignup ? "new-password" : "current-password";
  authTitle.textContent = isSignup ? "Create your account" : "Welcome back";
  authSubtitle.textContent = isSignup
    ? "A little space for everything you're ready to learn."
    : "Sign in to pick up where curiosity left off.";
  submitLabel.textContent = isSignup ? "Create account" : "Sign in";
  authMessage.hidden = true;
  authMessage.textContent = "";

  modeTabs.forEach((tab) => {
    const isActive = tab.dataset.mode === mode;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
  });
}

function showMessage(message, isError = true) {
  authMessage.textContent = message;
  authMessage.classList.toggle("error", isError);
  authMessage.hidden = !message;
}

modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!authForm.reportValidity()) {
    return;
  }

  const isSignup = mode === "signup";
  const body = {
    email: emailInput.value.trim(),
    password: passwordInput.value,
  };
  if (isSignup) {
    body.display_name = displayName.value.trim();
  }

  submitButton.disabled = true;
  submitLabel.textContent = isSignup ? "Creating account…" : "Signing in…";
  showMessage("One moment…", false);

  try {
    const response = await fetch(isSignup ? "/auth/register" : "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const detail = data?.detail;
      const message = Array.isArray(detail)
        ? detail
            .map((issue) => issue.msg)
            .filter(Boolean)
            .join(" ")
        : detail;
      throw new Error(
        typeof message === "string" && message
          ? message
          : "We couldn't complete that request. Please try again."
      );
    }

    window.location.assign("/");
  } catch (error) {
    showMessage(
      error instanceof Error ? error.message : "Something went wrong. Please try again."
    );
  } finally {
    submitButton.disabled = false;
    submitLabel.textContent = mode === "signup" ? "Create account" : "Sign in";
  }
});

document.querySelector("#signin-tab").focus({ preventScroll: true });
