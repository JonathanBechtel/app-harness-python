// Global script. Keep page scripts small, page-scoped, and initialised on
// DOMContentLoaded from their own kebab-case file via {% block extra_js %}.
document.addEventListener("DOMContentLoaded", () => {
  document.documentElement.dataset.jsReady = "true";
});
