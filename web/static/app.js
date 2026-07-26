(() => {
  "use strict";

  const telegram = window.Telegram?.WebApp;
  telegram?.ready();
  telegram?.expand();

  const elements = {
    messages: document.getElementById("messages"),
    composer: document.getElementById("composer"),
    input: document.getElementById("messageInput"),
    send: document.getElementById("sendButton"),
    attach: document.getElementById("attachButton"),
    imageInput: document.getElementById("imageInput"),
    attachmentPreview: document.getElementById("attachmentPreview"),
    attachmentImage: document.getElementById("attachmentImage"),
    attachmentName: document.getElementById("attachmentName"),
    attachmentSize: document.getElementById("attachmentSize"),
    removeAttachment: document.getElementById("removeAttachmentButton"),
    newChat: document.getElementById("newChatButton"),
    theme: document.getElementById("themeButton"),
    themeColor: document.getElementById("themeColor"),
    statusDot: document.getElementById("statusDot"),
    statusText: document.getElementById("statusText"),
    previewNotice: document.getElementById("previewNotice"),
    engineTabs: [...document.querySelectorAll(".engine-tab")],
  };

  const user = telegram?.initDataUnsafe?.user;
  const storageKey = `shadow-mentor-chat:${user?.id || "preview"}`;
  const themeStorageKey = "shadow-mentor-theme";
  const state = {
    engine: "auto",
    messages: loadMessages(),
    image: null,
    imageUrl: null,
    busy: false,
  };

  if (!telegram?.initData) {
    elements.previewNotice.hidden = false;
  }

  function savedTheme() {
    try {
      return localStorage.getItem(themeStorageKey);
    } catch {
      return null;
    }
  }

  function setTheme(theme, persist = false) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    const isDark = nextTheme === "dark";
    document.documentElement.dataset.theme = nextTheme;
    elements.themeColor.content = isDark ? "#0d1210" : "#f4f7f6";
    elements.theme.title = isDark ? "Light theme" : "Dark theme";
    elements.theme.setAttribute(
      "aria-label",
      isDark ? "Switch to light theme" : "Switch to dark theme",
    );
    elements.theme.innerHTML = isDark
      ? '<i data-lucide="sun" data-fallback="☀"></i>'
      : '<i data-lucide="moon" data-fallback="◐"></i>';

    if (persist) {
      try {
        localStorage.setItem(themeStorageKey, nextTheme);
      } catch {
        // Telegram may deny storage in restrictive privacy modes.
      }
    }

    const colors = getComputedStyle(document.documentElement);
    telegram?.setHeaderColor?.(colors.getPropertyValue("--page").trim());
    telegram?.setBackgroundColor?.(colors.getPropertyValue("--page").trim());
    refreshIcons();
  }

  function loadMessages() {
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey) || "[]");
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter(
          (item) =>
            item &&
            (item.role === "user" || item.role === "assistant") &&
            typeof item.content === "string",
        )
        .slice(-30);
    } catch {
      return [];
    }
  }

  function saveMessages() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state.messages.slice(-30)));
    } catch {
      // Telegram may deny storage in restrictive privacy modes.
    }
  }

  function setStatus(label, kind = "ready") {
    elements.statusText.textContent = label;
    elements.statusDot.classList.toggle("is-busy", kind === "busy");
    elements.statusDot.classList.toggle("is-error", kind === "error");
  }

  function greeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  function renderWelcome() {
    const welcome = document.createElement("section");
    welcome.className = "welcome";

    const mark = document.createElement("div");
    mark.className = "welcome-mark";
    mark.innerHTML = '<img src="/static/shadow-mentor.png" alt="">';

    const title = document.createElement("h2");
    title.textContent = `${greeting()}${user?.first_name ? `, ${user.first_name}` : ""}.`;

    const prompt = document.createElement("p");
    prompt.textContent = "What are we solving today?";

    const subjects = document.createElement("div");
    subjects.className = "subject-prompts";
    [
      ["Combined Maths", "Help me solve this Combined Maths problem: "],
      ["Physics", "Explain this Physics question step-by-step: "],
      ["Chemistry", "Help me understand this Chemistry topic: "],
      ["Biology", "Explain this Biology concept clearly: "],
    ].forEach(([label, value]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "subject-prompt";
      button.textContent = label;
      button.addEventListener("click", () => {
        elements.input.value = value;
        resizeInput();
        elements.input.focus();
      });
      subjects.appendChild(button);
    });

    welcome.append(mark, title, prompt, subjects);
    elements.messages.appendChild(welcome);
  }

  function protectMath(source) {
    const math = [];
    const text = source.replace(
      /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$[^$\n]+?\$)/g,
      (match) => {
        const token = `SHADOWMATHTOKEN${math.length}END`;
        math.push(match);
        return token;
      },
    );
    return { text, math };
  }

  function restoreMath(container, math) {
    if (!math.length) return;
    const nodes = [];
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) nodes.push(walker.currentNode);

    const tokenPattern = /SHADOWMATHTOKEN(\d+)END/g;
    nodes.forEach((node) => {
      if (!node.nodeValue?.includes("SHADOWMATHTOKEN")) return;
      const fragment = document.createDocumentFragment();
      let lastIndex = 0;
      let match;
      tokenPattern.lastIndex = 0;
      while ((match = tokenPattern.exec(node.nodeValue)) !== null) {
        fragment.append(node.nodeValue.slice(lastIndex, match.index));
        fragment.append(document.createTextNode(math[Number(match[1])] || ""));
        lastIndex = match.index + match[0].length;
      }
      fragment.append(node.nodeValue.slice(lastIndex));
      node.replaceWith(fragment);
    });
  }

  function escapeHtml(value) {
    const node = document.createElement("div");
    node.textContent = value;
    return node.innerHTML;
  }

  function fallbackMarkup(value) {
    const lines = value.split("\n");
    const output = [];
    let paragraph = [];

    const flushParagraph = () => {
      if (!paragraph.length) return;
      output.push(`<p>${paragraph.join("<br>")}</p>`);
      paragraph = [];
    };

    lines.forEach((line) => {
      const heading = line.match(/^\s{0,3}#{1,6}\s+(.+)$/);
      if (heading) {
        flushParagraph();
        output.push(`<h3>${escapeHtml(heading[1]).replace(/\*\*/g, "")}</h3>`);
      } else if (!line.trim()) {
        flushParagraph();
      } else {
        paragraph.push(escapeHtml(line).replace(/\*\*/g, ""));
      }
    });
    flushParagraph();
    return output.join("");
  }

  function renderPlainMathFallback(container) {
    const replacements = [
      [/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, "($1/$2)"],
      [/\\rho/g, "ρ"],
      [/\\Delta/g, "Δ"],
      [/\\theta/g, "θ"],
      [/\\pi/g, "π"],
      [/\\cdot/g, "·"],
      [/\\times/g, "×"],
      [/\\left|\\right/g, ""],
      [/\^2/g, "²"],
      [/\^3/g, "³"],
      [/\\\(|\\\)|\\\[|\\\]|\$\$/g, ""],
      [/\$/g, ""],
    ];
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      let value = node.nodeValue || "";
      replacements.forEach(([pattern, replacement]) => {
        value = value.replace(pattern, replacement);
      });
      node.nodeValue = value;
    });
  }

  function renderRichText(value, container) {
    const protectedMath = protectMath(value);
    const parsed = window.marked
      ? window.marked.parse(protectedMath.text, { breaks: true, gfm: true })
      : fallbackMarkup(protectedMath.text);
    const clean = window.DOMPurify
      ? window.DOMPurify.sanitize(parsed, { USE_PROFILES: { html: true } })
      : window.marked
        ? fallbackMarkup(protectedMath.text)
        : parsed;

    container.innerHTML = clean;
    restoreMath(container, protectedMath.math);
    container.querySelectorAll("a").forEach((link) => {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    });

    if (window.renderMathInElement) {
      window.renderMathInElement(container, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\[", right: "\\]", display: true },
          { left: "\\(", right: "\\)", display: false },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    } else {
      renderPlainMathFallback(container);
    }
  }

  function messageElement(message, options = {}) {
    const row = document.createElement("article");
    row.className = `message ${message.role}${options.error ? " error" : ""}`;

    if (message.role === "assistant") {
      const avatar = document.createElement("div");
      avatar.className = "assistant-avatar";
      avatar.setAttribute("aria-hidden", "true");
      avatar.innerHTML = '<img src="/static/shadow-mentor.png" alt="">';
      row.appendChild(avatar);
    }

    const body = document.createElement("div");
    body.className = "message-body";
    const content = document.createElement("div");
    content.className = "message-content";

    if (message.role === "assistant") {
      renderRichText(message.content, content);
    } else {
      content.textContent = message.content;
    }
    body.appendChild(content);

    if (message.role === "assistant" && !options.error) {
      const actions = document.createElement("div");
      actions.className = "message-actions";
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "message-action";
      copy.title = "Copy answer";
      copy.setAttribute("aria-label", "Copy answer");
      copy.innerHTML = '<i data-lucide="copy" data-fallback="⧉"></i>';
      copy.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(message.content);
          copy.innerHTML = '<i data-lucide="check" data-fallback="✓"></i>';
          refreshIcons();
          setTimeout(() => {
            copy.innerHTML = '<i data-lucide="copy" data-fallback="⧉"></i>';
            refreshIcons();
          }, 1400);
        } catch {
          setStatus("Copy failed", "error");
        }
      });
      actions.appendChild(copy);
      body.appendChild(actions);
    }

    row.appendChild(body);
    return row;
  }

  function renderMessages() {
    elements.messages.replaceChildren();
    if (!state.messages.length) {
      renderWelcome();
    } else {
      state.messages.forEach((message) => {
        elements.messages.appendChild(messageElement(message));
      });
    }
    refreshIcons();
    scrollToBottom(false);
  }

  function showTyping() {
    const row = document.createElement("article");
    row.id = "typingMessage";
    row.className = "message assistant";
    row.innerHTML = `
      <div class="assistant-avatar" aria-hidden="true"><img src="/static/shadow-mentor.png" alt=""></div>
      <div class="message-body">
        <div class="typing" aria-label="Shadow Mentor is thinking">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
    elements.messages.appendChild(row);
    refreshIcons();
    scrollToBottom(true);
  }

  function removeTyping() {
    document.getElementById("typingMessage")?.remove();
  }

  function refreshIcons() {
    window.lucide?.createIcons({ attrs: { "stroke-width": 1.9 } });
  }

  function scrollToBottom(smooth = true) {
    elements.messages.scrollTo({
      top: elements.messages.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  }

  function resizeInput() {
    elements.input.style.height = "auto";
    elements.input.style.height = `${Math.min(elements.input.scrollHeight, 132)}px`;
  }

  function setBusy(value) {
    state.busy = value;
    elements.send.disabled = value;
    elements.attach.disabled = value;
    elements.engineTabs.forEach((button) => {
      button.disabled = value;
    });
    setStatus(value ? "Thinking" : "Ready", value ? "busy" : "ready");
  }

  function clearAttachment() {
    if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
    state.image = null;
    state.imageUrl = null;
    elements.imageInput.value = "";
    elements.attachmentPreview.hidden = true;
    elements.attachmentImage.removeAttribute("src");
  }

  function formatBytes(bytes) {
    if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function apiError(response) {
    try {
      const data = await response.json();
      return data.detail || "Shadow Mentor could not answer.";
    } catch {
      return "Shadow Mentor could not answer.";
    }
  }

  async function sendQuestion() {
    const message = elements.input.value.trim();
    if ((!message && !state.image) || state.busy) return;
    let requestFailed = false;

    const history = state.messages.slice(-10);
    const displayMessage = message || "Explain this image step-by-step.";
    state.messages.push({ role: "user", content: displayMessage });
    saveMessages();
    renderMessages();
    showTyping();
    setBusy(true);

    const attachedImage = state.image;
    elements.input.value = "";
    resizeInput();
    clearAttachment();
    telegram?.HapticFeedback?.impactOccurred("light");

    try {
      let response;
      if (attachedImage) {
        const form = new FormData();
        form.append("image", attachedImage);
        form.append("prompt", displayMessage);
        response = await fetch("/api/image", {
          method: "POST",
          headers: { "X-Telegram-Init-Data": telegram?.initData || "" },
          body: form,
        });
      } else {
        response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Telegram-Init-Data": telegram?.initData || "",
          },
          body: JSON.stringify({
            message,
            engine: state.engine,
            history,
          }),
        });
      }

      if (!response.ok) throw new Error(await apiError(response));
      const data = await response.json();
      state.messages.push({ role: "assistant", content: data.answer });
      saveMessages();
      removeTyping();
      elements.messages.appendChild(
        messageElement({ role: "assistant", content: data.answer }),
      );
      refreshIcons();
      scrollToBottom(true);
      telegram?.HapticFeedback?.notificationOccurred("success");
    } catch (error) {
      requestFailed = true;
      removeTyping();
      const messageText = error instanceof Error ? error.message : "Please try again.";
      elements.messages.appendChild(
        messageElement(
          { role: "assistant", content: messageText },
          { error: true },
        ),
      );
      setStatus("Could not answer", "error");
      telegram?.HapticFeedback?.notificationOccurred("error");
      scrollToBottom(true);
    } finally {
      setBusy(false);
      if (requestFailed) setStatus("Could not answer", "error");
      elements.input.focus();
    }
  }

  elements.composer.addEventListener("submit", (event) => {
    event.preventDefault();
    sendQuestion();
  });

  elements.input.addEventListener("input", resizeInput);
  elements.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      sendQuestion();
    }
  });

  elements.attach.addEventListener("click", () => elements.imageInput.click());
  elements.imageInput.addEventListener("change", () => {
    const image = elements.imageInput.files?.[0];
    if (!image) return;
    if (image.size > 10 * 1024 * 1024) {
      setStatus("Image is over 10 MB", "error");
      elements.imageInput.value = "";
      return;
    }

    clearAttachment();
    state.image = image;
    state.imageUrl = URL.createObjectURL(image);
    elements.attachmentImage.src = state.imageUrl;
    elements.attachmentName.textContent = image.name;
    elements.attachmentSize.textContent = formatBytes(image.size);
    elements.attachmentPreview.hidden = false;
  });
  elements.removeAttachment.addEventListener("click", clearAttachment);

  elements.engineTabs.forEach((button) => {
    button.addEventListener("click", () => {
      state.engine = button.dataset.engine || "auto";
      elements.engineTabs.forEach((tab) => {
        tab.classList.toggle("is-active", tab === button);
      });
      telegram?.HapticFeedback?.selectionChanged();
    });
  });

  elements.newChat.addEventListener("click", () => {
    state.messages = [];
    saveMessages();
    clearAttachment();
    renderMessages();
    elements.input.focus();
    telegram?.HapticFeedback?.impactOccurred("light");
  });

  elements.theme.addEventListener("click", () => {
    const nextTheme =
      document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(nextTheme, true);
    telegram?.HapticFeedback?.selectionChanged();
  });

  window.addEventListener("online", () => setStatus("Ready"));
  window.addEventListener("offline", () => setStatus("Offline", "error"));
  telegram?.onEvent?.("themeChanged", () => {
    if (!savedTheme()) setTheme(telegram.colorScheme);
  });

  setTheme(savedTheme() || telegram?.colorScheme || document.documentElement.dataset.theme);
  renderMessages();
  resizeInput();
  refreshIcons();
})();
