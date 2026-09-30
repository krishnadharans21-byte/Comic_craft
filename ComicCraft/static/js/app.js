"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const prompt = document.getElementById("story_prompt");
  const count = document.getElementById("prompt-count");
  const form = document.getElementById("comic-form");
  const overlay = document.getElementById("loading-overlay");
  const button = form?.querySelector("button[type='submit']");

  const updateCount = () => {
    if (prompt && count) count.textContent = `${prompt.value.length} / ${prompt.maxLength}`;
  };
  prompt?.addEventListener("input", updateCount);
  updateCount();

  form?.addEventListener("submit", () => {
    if (overlay) {
      overlay.classList.add("is-active");
      overlay.setAttribute("aria-hidden", "false");
    }
    if (button) {
      button.disabled = true;
      const label = button.querySelector(".button-label");
      if (label) label.textContent = "Making your comic…";
    }
  });
});
