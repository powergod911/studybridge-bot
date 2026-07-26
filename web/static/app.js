(() => {
  "use strict";

  const telegram = window.Telegram?.WebApp;
  telegram?.ready();
  telegram?.expand();

  const elements = {
    workspace: document.querySelector(".workspace"),
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
    historyNewChat: document.getElementById("historyNewChatButton"),
    theme: document.getElementById("themeButton"),
    themeColor: document.getElementById("themeColor"),
    statusDot: document.getElementById("statusDot"),
    statusText: document.getElementById("statusText"),
    previewNotice: document.getElementById("previewNotice"),
    historyButton: document.getElementById("historyButton"),
    homeButton: document.getElementById("homeButton"),
    closeHistory: document.getElementById("closeHistoryButton"),
    historyPanel: document.getElementById("historyPanel"),
    historyScrim: document.getElementById("historyScrim"),
    historyCount: document.getElementById("historyCount"),
    historyEmpty: document.getElementById("historyEmpty"),
    conversationList: document.getElementById("conversationList"),
    modelButton: document.getElementById("modelButton"),
    modelMenu: document.getElementById("modelMenu"),
    modelOptions: [...document.querySelectorAll(".model-option")],
  };

  const user = telegram?.initDataUnsafe?.user;
  const themeStorageKey = "shadow-mentor-theme";
  const engineStorageKey = `shadow-mentor-engine:${user?.id || "preview"}`;
  const validImageTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
  const state = {
    engine: loadEngine(),
    conversations: [],
    activeConversationId: null,
    messages: [],
    image: null,
    imageUrl: null,
    busy: false,
    requestId: 0,
    abortController: null,
  };

  if (!telegram?.initData) {
    elements.previewNotice.hidden = false;
  }

  function storageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // Telegram can deny storage in restrictive privacy modes.
    }
  }

  function loadEngine() {
    const value = storageGet(engineStorageKey);
    return ["auto", "deepseek", "gemini"].includes(value) ? value : "auto";
  }

  function savedTheme() {
    return storageGet(themeStorageKey);
  }

  function setTheme(theme, persist = false) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    const isDark = nextTheme === "dark";
    document.documentElement.dataset.theme = nextTheme;
    elements.themeColor.content = isDark ? "#060a12" : "#ffffff";
    elements.theme.title = isDark ? "Light theme" : "Dark theme";
    elements.theme.setAttribute(
      "aria-label",
      isDark ? "Switch to light theme" : "Switch to dark theme",
    );
    elements.theme.innerHTML = isDark
      ? '<i data-lucide="sun" data-fallback="L"></i>'
      : '<i data-lucide="moon" data-fallback="D"></i>';

    if (persist) storageSet(themeStorageKey, nextTheme);

    const colors = getComputedStyle(document.documentElement);
    telegram?.setHeaderColor?.(colors.getPropertyValue("--page").trim());
    telegram?.setBackgroundColor?.(colors.getPropertyValue("--page").trim());
    refreshIcons();
  }

  function authHeaders(extra = {}) {
    return {
      "X-Telegram-Init-Data": telegram?.initData || "",
      ...extra,
    };
  }

  async function apiError(response) {
    try {
      const data = await response.json();
      return data.detail || "Shadow Mentor could not complete that request.";
    } catch {
      return "Shadow Mentor could not complete that request.";
    }
  }

  async function requestJson(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: authHeaders(options.headers || {}),
    });
    if (!response.ok) throw new Error(await apiError(response));
    if (response.status === 204) return null;
    return response.json();
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
    welcome.innerHTML = `
      <div class="mentor-core" aria-hidden="true">
        <div class="core-frame">
          <span class="core-corner core-corner-a"></span>
          <span class="core-corner core-corner-b"></span>
          <span class="core-corner core-corner-c"></span>
          <span class="core-corner core-corner-d"></span>
          <img src="/static/shadow-mentor.png" alt="">
          <span class="core-scan"></span>
        </div>
        <div class="core-readout">
          <span>SHADOW CORE</span>
          <strong>ONLINE</strong>
        </div>
      </div>
      <div class="welcome-console">
        <div class="welcome-signal" aria-hidden="true">
          <span>01</span><span>MENTOR ONLINE</span>
        </div>
        <div class="welcome-copy">
          <h2>${greeting()}${user?.first_name ? `, ${escapeHtml(user.first_name)}` : ""}.</h2>
          <p>Bring one problem at a time. Shadow Mentor will keep the thread as you work through it.</p>
        </div>
        <div class="subject-picker">
          <button class="subject-launch" type="button" aria-label="Choose a subject" aria-expanded="false" title="Choose a subject">
            <i data-lucide="library-big" data-fallback="S"></i>
          </button>
          <div>
            <strong>Choose a subject</strong>
            <span>Open focused A/L starters</span>
          </div>
        </div>
        <div class="subject-prompts" aria-label="Subject starters" hidden></div>
      </div>
    `;

    const subjects = welcome.querySelector(".subject-prompts");
    [
      ["Combined Maths", "sigma", "Help me solve this Combined Maths problem: "],
      ["Physics", "atom", "Explain this Physics question step-by-step: "],
      ["Chemistry", "flask-conical", "Help me understand this Chemistry topic: "],
      ["Biology", "dna", "Explain this Biology concept clearly: "],
      ["ICT", "binary", "Help me with this A/L ICT question: "],
      ["General", "book-open", "Help me study this A/L topic: "],
    ].forEach(([label, icon, value]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "subject-prompt";
      button.innerHTML = `<i data-lucide="${icon}" data-fallback="S"></i><span>${label}</span>`;
      button.addEventListener("click", () => {
        elements.input.value = value;
        resizeInput();
        elements.input.focus();
      });
      subjects.appendChild(button);
    });

    const subjectLaunch = welcome.querySelector(".subject-launch");
    subjectLaunch.addEventListener("click", () => {
      const willOpen = subjects.hidden;
      subjects.hidden = !willOpen;
      subjectLaunch.setAttribute("aria-expanded", String(willOpen));
      subjectLaunch.classList.toggle("is-active", willOpen);
      if (willOpen) subjects.querySelector("button")?.focus();
      refreshIcons();
    });
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
      [/\\rho/g, "rho"],
      [/\\Delta/g, "Delta"],
      [/\\theta/g, "theta"],
      [/\\pi/g, "pi"],
      [/\\cdot|\\times/g, " x "],
      [/\\left|\\right/g, ""],
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
      : fallbackMarkup(protectedMath.text);

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

  async function copyText(value, button) {
    try {
      await navigator.clipboard.writeText(value);
      button.innerHTML = '<i data-lucide="check" data-fallback="v"></i>';
      refreshIcons();
      setTimeout(() => {
        button.innerHTML = '<i data-lucide="copy" data-fallback="C"></i>';
        refreshIcons();
      }, 1400);
    } catch {
      setStatus("Copy failed", "error");
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
    if (message.hasImage) {
      const imageBadge = document.createElement("div");
      imageBadge.className = "message-image-badge";
      imageBadge.innerHTML = '<i data-lucide="image" data-fallback="IMG"></i><span>Study image attached</span>';
      body.appendChild(imageBadge);
    }

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
      if (message.engine) {
        const engine = document.createElement("span");
        engine.className = "answer-engine";
        engine.textContent = message.engine;
        actions.appendChild(engine);
      }
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "message-action";
      copy.title = "Copy answer";
      copy.setAttribute("aria-label", "Copy answer");
      copy.innerHTML = '<i data-lucide="copy" data-fallback="C"></i>';
      copy.addEventListener("click", () => copyText(message.content, copy));
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
    updateNavigation();
    refreshIcons();
    scrollToBottom(false);
  }

  function updateNavigation() {
    const hasConversationView = state.messages.length > 0;
    elements.workspace.classList.toggle("is-conversation", hasConversationView);
    elements.homeButton.hidden = !hasConversationView;
    elements.input.placeholder = hasConversationView
      ? "Ask a follow-up..."
      : "Ask a new problem...";
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
    scrollToBottom(true);
  }

  function removeTyping() {
    document.getElementById("typingMessage")?.remove();
  }

  function refreshIcons() {
    window.lucide?.createIcons({ attrs: { "stroke-width": 1.8 } });
  }

  function scrollToBottom(smooth = true) {
    elements.messages.scrollTo({
      top: elements.messages.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  }

  function resizeInput() {
    elements.input.style.height = "auto";
    elements.input.style.height = `${Math.min(elements.input.scrollHeight, 144)}px`;
  }

  function setBusy(value) {
    state.busy = value;
    elements.send.disabled = value;
    elements.attach.disabled = value;
    elements.modelOptions.forEach((button) => {
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
    elements.composer.classList.remove("has-attachment");
  }

  function formatBytes(bytes) {
    if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function attachImage(image, displayName = null) {
    if (!validImageTypes.has(image.type)) {
      setStatus("Use a JPEG, PNG or WebP image", "error");
      return false;
    }
    if (image.size > 10 * 1024 * 1024) {
      setStatus("Image is over 10 MB", "error");
      return false;
    }

    clearAttachment();
    state.image = image;
    state.imageUrl = URL.createObjectURL(image);
    elements.attachmentImage.src = state.imageUrl;
    elements.attachmentName.textContent = displayName || image.name || "Pasted image";
    elements.attachmentSize.textContent = formatBytes(image.size);
    elements.attachmentPreview.hidden = false;
    elements.composer.classList.add("has-attachment");
    setStatus("Image attached");
    return true;
  }

  function formatHistoryTime(value) {
    const date = new Date(value);
    const today = new Date();
    if (date.toDateString() === today.toDateString()) {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    return date.toLocaleDateString([], { month: "short", day: "numeric" });
  }

  function renderConversationList() {
    elements.conversationList.replaceChildren();
    elements.historyCount.textContent = String(state.conversations.length);
    elements.historyEmpty.hidden = state.conversations.length > 0;

    state.conversations.forEach((conversation) => {
      const row = document.createElement("div");
      row.className = "conversation-row";
      row.classList.toggle("is-active", conversation.id === state.activeConversationId);

      const open = document.createElement("button");
      open.type = "button";
      open.className = "conversation-open";
      open.innerHTML = `
        <span>${escapeHtml(conversation.title)}</span>
        <small>${formatHistoryTime(conversation.updated_at)}</small>
      `;
      open.addEventListener("click", () => openConversation(conversation.id));

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "conversation-delete";
      remove.title = "Delete conversation";
      remove.setAttribute("aria-label", `Delete ${conversation.title}`);
      remove.innerHTML = '<i data-lucide="trash-2" data-fallback="x"></i>';
      remove.addEventListener("click", () => removeConversation(conversation));
      row.append(open, remove);
      elements.conversationList.appendChild(row);
    });
    refreshIcons();
  }

  async function loadConversations() {
    try {
      state.conversations = await requestJson("/api/conversations");
      elements.historyEmpty.textContent = "Your solved problems will appear here.";
      renderConversationList();
    } catch (error) {
      elements.historyEmpty.hidden = false;
      elements.historyEmpty.textContent =
        error instanceof Error ? error.message : "History is unavailable.";
      throw error;
    }
  }

  async function openConversation(conversationId) {
    if (state.busy || conversationId === state.activeConversationId) {
      closeHistory();
      return;
    }
    closeHistory();
    setStatus("Loading", "busy");
    try {
      const conversation = await requestJson(`/api/conversations/${conversationId}`);
      state.activeConversationId = conversation.id;
      state.messages = conversation.messages.map((message) => ({
        role: message.role,
        content: message.content,
        engine: message.engine,
        hasImage: message.has_image,
      }));
      renderConversationList();
      renderMessages();
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load chat", "error");
    }
  }

  function confirmAction(message) {
    if (telegram?.showConfirm) {
      return new Promise((resolve) => telegram.showConfirm(message, resolve));
    }
    return Promise.resolve(window.confirm(message));
  }

  async function removeConversation(conversation) {
    if (!(await confirmAction(`Delete "${conversation.title}"?`))) return;
    try {
      await requestJson(`/api/conversations/${conversation.id}`, { method: "DELETE" });
      if (state.activeConversationId === conversation.id) startNewConversation();
      await loadConversations();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Delete failed", "error");
    }
  }

  function startNewConversation() {
    state.requestId += 1;
    state.abortController?.abort();
    state.abortController = null;
    state.activeConversationId = null;
    state.messages = [];
    setBusy(false);
    clearAttachment();
    closeModelMenu();
    renderConversationList();
    renderMessages();
    closeHistory();
    elements.input.focus();
    telegram?.HapticFeedback?.impactOccurred("light");
  }

  function goHome() {
    state.requestId += 1;
    state.abortController?.abort();
    state.abortController = null;
    state.activeConversationId = null;
    state.messages = [];
    setBusy(false);
    clearAttachment();
    closeModelMenu();
    renderConversationList();
    renderMessages();
    closeHistory();
    elements.input.focus();
    telegram?.HapticFeedback?.selectionChanged();
  }

  function openHistory() {
    elements.historyScrim.hidden = false;
    elements.historyPanel.classList.add("is-open");
    elements.historyScrim.classList.add("is-visible");
  }

  function closeHistory() {
    elements.historyPanel.classList.remove("is-open");
    elements.historyScrim.classList.remove("is-visible");
    setTimeout(() => {
      if (!elements.historyScrim.classList.contains("is-visible")) {
        elements.historyScrim.hidden = true;
      }
    }, 180);
  }

  function updateModelControl() {
    const labels = { auto: "Auto", deepseek: "DeepSeek", gemini: "Gemini" };
    elements.modelButton.title = `Model: ${labels[state.engine]}`;
    elements.modelButton.setAttribute("aria-label", `Choose AI model. Current: ${labels[state.engine]}`);
    elements.modelButton.dataset.engine = state.engine;
    elements.modelOptions.forEach((option) => {
      const selected = option.dataset.engine === state.engine;
      option.classList.toggle("is-active", selected);
      option.setAttribute("aria-checked", String(selected));
    });
    refreshIcons();
  }

  function openModelMenu() {
    elements.modelMenu.hidden = false;
    elements.modelButton.setAttribute("aria-expanded", "true");
  }

  function closeModelMenu() {
    elements.modelMenu.hidden = true;
    elements.modelButton.setAttribute("aria-expanded", "false");
  }

  async function sendQuestion() {
    const message = elements.input.value.trim();
    if ((!message && !state.image) || state.busy) return;
    let requestFailed = false;
    const requestId = ++state.requestId;
    const abortController = new AbortController();
    state.abortController = abortController;
    const attachedImage = state.image;
    const displayMessage = message || "Explain this image step-by-step.";
    const fallbackHistory = state.messages.slice(-10).map((turn) => ({
      role: turn.role,
      content: turn.content.slice(0, 6000),
    }));

    state.messages.push({
      role: "user",
      content: displayMessage,
      hasImage: Boolean(attachedImage),
    });
    renderMessages();
    showTyping();
    setBusy(true);
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
        if (state.activeConversationId) {
          form.append("conversation_id", state.activeConversationId);
        }
        response = await fetch("/api/image", {
          method: "POST",
          headers: authHeaders(),
          body: form,
          signal: abortController.signal,
        });
      } else {
        response = await fetch("/api/chat", {
          method: "POST",
          headers: authHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({
            message,
            engine: state.engine,
            conversation_id: state.activeConversationId,
            history: fallbackHistory,
          }),
          signal: abortController.signal,
        });
      }

      if (!response.ok) throw new Error(await apiError(response));
      const data = await response.json();
      if (requestId !== state.requestId) return;
      state.activeConversationId = data.conversation_id;
      state.messages.push({
        role: "assistant",
        content: data.answer,
        engine: data.engine,
      });
      removeTyping();
      renderMessages();
      await loadConversations();
      telegram?.HapticFeedback?.notificationOccurred("success");
    } catch (error) {
      if (requestId !== state.requestId || error?.name === "AbortError") return;
      requestFailed = true;
      removeTyping();
      const messageText = error instanceof Error ? error.message : "Please try again.";
      elements.messages.appendChild(
        messageElement({ role: "assistant", content: messageText }, { error: true }),
      );
      setStatus("Could not answer", "error");
      telegram?.HapticFeedback?.notificationOccurred("error");
      scrollToBottom(true);
    } finally {
      if (requestId === state.requestId) {
        state.abortController = null;
        setBusy(false);
        if (requestFailed) setStatus("Could not answer", "error");
        elements.input.focus();
      }
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
  elements.input.addEventListener("paste", (event) => {
    const imageItem = [...(event.clipboardData?.items || [])].find((item) =>
      item.type.startsWith("image/"),
    );
    const image = imageItem?.getAsFile();
    if (!image) return;
    event.preventDefault();
    attachImage(image, `Pasted image.${image.type.split("/")[1] || "png"}`);
  });

  ["dragenter", "dragover"].forEach((name) => {
    elements.composer.addEventListener(name, (event) => {
      event.preventDefault();
      elements.composer.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    elements.composer.addEventListener(name, (event) => {
      event.preventDefault();
      elements.composer.classList.remove("is-dragging");
    });
  });
  elements.composer.addEventListener("drop", (event) => {
    const image = [...(event.dataTransfer?.files || [])].find((file) =>
      file.type.startsWith("image/"),
    );
    if (image) attachImage(image);
  });

  elements.attach.addEventListener("click", () => elements.imageInput.click());
  elements.imageInput.addEventListener("change", () => {
    const image = elements.imageInput.files?.[0];
    if (image) attachImage(image);
  });
  elements.removeAttachment.addEventListener("click", clearAttachment);
  elements.newChat.addEventListener("click", startNewConversation);
  elements.historyNewChat.addEventListener("click", startNewConversation);
  elements.homeButton.addEventListener("click", goHome);
  elements.historyButton.addEventListener("click", openHistory);
  elements.closeHistory.addEventListener("click", closeHistory);
  elements.historyScrim.addEventListener("click", closeHistory);

  elements.modelButton.addEventListener("click", () => {
    if (elements.modelMenu.hidden) openModelMenu();
    else closeModelMenu();
    telegram?.HapticFeedback?.selectionChanged();
  });
  elements.modelOptions.forEach((option) => {
    option.addEventListener("click", () => {
      state.engine = option.dataset.engine || "auto";
      storageSet(engineStorageKey, state.engine);
      updateModelControl();
      closeModelMenu();
      telegram?.HapticFeedback?.selectionChanged();
    });
  });
  document.addEventListener("click", (event) => {
    if (!elements.modelMenu.hidden && !event.target.closest(".model-control")) {
      closeModelMenu();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeModelMenu();
      closeHistory();
    }
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

  async function initialize() {
    setTheme(savedTheme() || telegram?.colorScheme || document.documentElement.dataset.theme);
    updateModelControl();
    renderMessages();
    resizeInput();
    refreshIcons();
    try {
      await loadConversations();
      if (state.conversations.length) {
        await openConversation(state.conversations[0].id);
      }
    } catch (error) {
      if (telegram?.initData) {
        setStatus(error instanceof Error ? error.message : "History unavailable", "error");
      }
    }
  }

  initialize();
})();
