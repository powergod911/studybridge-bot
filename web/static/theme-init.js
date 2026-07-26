(() => {
  "use strict";

  try {
    const savedTheme = localStorage.getItem("shadow-mentor-theme");
    const preferredTheme = matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
    document.documentElement.dataset.theme = savedTheme || preferredTheme;
  } catch {
    document.documentElement.dataset.theme = "light";
  }
})();
