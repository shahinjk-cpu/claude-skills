// SPDX-License-Identifier: GPL-3.0-or-later
// providers/aistudio.js - Google AI Studio (aistudio.google.com) provider.
// Exports the ZSProvider interface consumed by core/main.js.
// eslint-disable-next-line no-unused-vars
const ZSProvider = (() => {
  "use strict";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let diag = () => {};
  let _locked = false, _lockedEl = null;

  const S = {
    turnSel: "ms-chat-turn",
    replyContainerSel: ".model-prompt-container, .chat-turn-container.model, .turn-content",
    thinking: 'ms-thought-chunk, .thought-container, [class*="thought-panel"], [class*="thinking"]',
    chromeExclude:
      'ms-thought-chunk, .thought-container, [class*="thought-panel"], [class*="thinking"], ' +
      "ms-chat-turn-options, .turn-footer, .author-label, .role-label, button, mat-icon, " +
      '.actions-container, ms-code-block header, ms-code-block .header, .code-block-header, ' +
      '.copy-button, [aria-hidden="true"], .zs-chip',
    editorSels: [
      'ms-prompt-input-wrapper textarea:not([aria-hidden="true"])',
      'ms-autosize-textarea textarea:not([aria-hidden="true"])',
      'textarea[aria-label*="Type something" i]',
      'textarea[aria-label*="Start typing" i]',
      'textarea[aria-label*="prompt" i]',
      'footer textarea:not([aria-hidden="true"])',
      'main textarea:not([aria-hidden="true"])',
    ],
    editorFallbackSels: [
      'textarea:not([aria-hidden="true"])',
      'main [contenteditable]:not([contenteditable="false"])',
      '[contenteditable]:not([contenteditable="false"])',
    ],
    runSels: [
      "ms-run-button button",
      "run-button button",
      "button.run-button",
      'button[aria-label="Run"]',
      'button[aria-label="Run prompt" i]',
      'button[aria-label="Send"]',
      'button[aria-label="Send message" i]',
    ],
    stopSels: [
      "run-button.stoppable button",
      "button.stoppable",
      'button[aria-label*="Stop" i]',
      'button[aria-label*="Cancel" i]',
      'button[aria-label*="Arrêt" i]',
    ],
    codeWrap: "pre, ms-code-block, .code-block-container",
    errorSurfaces: '[role="alert"], .mat-mdc-snack-bar-container, [class*="toast"], [class*="error"]',
  };

  const RE = {
    contextLimit: /context.{0,25}(limit|length|exceeded)|token limit|prompt.{0,20}too long|too many tokens/i,
    tooLong: /conversation.{0,25}(too long|getting long)|token limit/i,
    busy: /an internal error has occurred|internal error|rate limit|too many requests|quota|resource exhausted|service unavailable|overloaded|something went wrong|try again later/i,
  };

  const timings = {
    GEN_IDLE_MS: 1500,
    REASON_IDLE_MS: 18000,
    WARMUP_MS: 45000,
    REASON_NOREPLY_MS: 120000,
    STABLE_MS: 9000,
    RESPONSE_TIMEOUT_MS: 300000,
  };

  function isSysInstruction(el) {
    if (!el) return false;
    if (el.closest && el.closest('ms-system-instructions, [class*="system-instruction"]')) return true;
    const aria = (el.getAttribute && el.getAttribute("aria-label")) || "";
    const ph = (el.getAttribute && el.getAttribute("placeholder")) || "";
    return /system\s+instruction/i.test(aria) || /system\s+instruction/i.test(ph);
  }

  function isVisibleBox(el, minW = 0, minH = 0) {
    if (!el || (el.closest && el.closest("#zs-root")) || isSysInstruction(el)) return false;
    if (el.getAttribute && el.getAttribute("aria-hidden") === "true") return false;
    if (!el.getBoundingClientRect) return true;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    if (minW && r.width < minW) return false;
    if (minH && r.height < minH) return false;
    try {
      const st = getComputedStyle(el);
      if (st.display === "none" || st.visibility === "hidden" || st.opacity === "0") return false;
    } catch {}
    return true;
  }

  function findInShadowRoots(root, minW, minH) {
    if (!root || !root.querySelectorAll) return null;
    const stack = [root];
    let visited = 0;
    while (stack.length && visited < 60) {
      const cur = stack.pop();
      visited++;
      if (!cur || !cur.querySelectorAll) continue;
      if (cur !== root) {
        for (const sel of S.editorSels) {
          for (const el of cur.querySelectorAll(sel)) {
            if (isVisibleBox(el)) return el;
          }
        }
        for (const el of cur.querySelectorAll('textarea:not([aria-hidden="true"]), [contenteditable]:not([contenteditable="false"])')) {
          if (isVisibleBox(el, minW, minH)) return el;
        }
      }
      for (const el of cur.querySelectorAll("*")) {
        if (el.shadowRoot && !(el.closest && el.closest("#zs-root"))) stack.push(el.shadowRoot);
      }
    }
    return null;
  }

  function getEditor() {
    if (_locked && _lockedEl && _lockedEl.isConnected && isVisibleBox(_lockedEl)) return _lockedEl;
    const locked = document.querySelector('[data-zs-locked="1"]');
    if (locked && isVisibleBox(locked)) return locked;
    for (const sel of S.editorSels) {
      for (const el of document.querySelectorAll(sel)) {
        if (isVisibleBox(el)) return el;
      }
    }
    for (const sel of S.editorFallbackSels) {
      for (const el of document.querySelectorAll(sel)) {
        if (isVisibleBox(el, 100, 16)) return el;
      }
    }
    return findInShadowRoots(document.querySelector("main") || document.body, 100, 16);
  }

  const editorText = () => {
    const e = getEditor();
    if (!e) return "";
    return e.tagName === "TEXTAREA" ? (e.value || "") : (e.textContent || "");
  };

  function allItems() {
    const turnSels = [
      S.turnSel,
      '[data-turn-role="User"], [data-turn-role="Model"], [data-turn-role="user"], [data-turn-role="model"]',
      "[data-message-author-role]",
      "user-query, model-response",
      ".chat-turn-container",
    ];
    for (const sel of turnSels) {
      const seen = new Set();
      const out = [];
      for (const n of document.querySelectorAll(sel)) {
        if (n.closest("#zs-root")) continue;
        const host = sel === S.turnSel ? n : (n.closest(S.turnSel) || n);
        if (!seen.has(host)) { seen.add(host); out.push(host); }
      }
      if (out.length) {
        out.sort((a, b) => (a === b ? 0 : (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1)));
        return out;
      }
    }
    return [];
  }

  function isUserItem(item) {
    if (!item) return false;
    const directRole = item.getAttribute && item.getAttribute("data-turn-role");
    if (directRole) return directRole.toLowerCase() === "user";
    const roleNode = item.querySelector && item.querySelector("[data-turn-role]");
    if (roleNode) return (roleNode.getAttribute("data-turn-role") || "").toLowerCase() === "user";
    const msgRole = item.getAttribute && item.getAttribute("data-message-author-role");
    if (msgRole) return msgRole.toLowerCase() === "user";
    if (item.tagName === "USER-QUERY") return true;
    if (item.tagName === "MODEL-RESPONSE") return false;
    if (item.matches && item.matches(".chat-turn-container.user, .user-prompt-container")) return true;
    if (item.querySelector && item.querySelector(".chat-turn-container.user, .user-prompt-container")) return true;
    if (item.querySelector && item.querySelector(".chat-turn-container.model, .model-prompt-container")) return false;
    const cl = (item.className || "").toString();
    return /\bjustify-end\b|\bself-end\b|\bitems-end\b/.test(cl);
  }
  const isAssistantItem = (item) => !!item && !isUserItem(item);

  const BLOCK_TAGS = /^(?:P|DIV|PRE|LI|UL|OL|BLOCKQUOTE|H[1-6]|TABLE|TR|SECTION|ARTICLE|HR)$/;
  function textWithout(root, excludeSel) {
    if (!root) return "";
    const skip = S.chromeExclude + (excludeSel ? ", " + excludeSel : "");
    let t = "";
    const breakLine = () => { if (t && !t.endsWith("\n")) t += "\n"; };
    const walk = (n) => {
      if (n.nodeType === 3) { t += n.nodeValue; return; }
      if (n.nodeType !== 1) return;
      if (n.matches && n.matches(skip)) return;
      if (n.tagName === "BR") { t += "\n"; return; }
      if (n.classList && n.classList.contains("cm-line")) {
        for (const c of n.childNodes) walk(c);
        t += "\n";
        return;
      }
      const isBlock = BLOCK_TAGS.test(n.tagName);
      if (isBlock) breakLine();
      for (const c of n.childNodes) walk(c);
      if (isBlock) breakLine();
    };
    walk(root);
    return t;
  }

  const replyContainer = (item) => {
    if (!item) return null;
    if (isAssistantItem(item)) return item.querySelector(S.replyContainerSel) || item;
    return item.querySelector(".user-prompt-container, .chat-turn-container.user, .turn-content") || item;
  };
  const itemText = (item) => {
    const rc = replyContainer(item);
    return rc ? textWithout(rc) : "";
  };
  const classifyText = (item, excludeSel) => {
    const rc = replyContainer(item);
    if (!rc || (excludeSel && rc.closest(excludeSel))) return "";
    return textWithout(rc, excludeSel);
  };

  const assistantItems = () => allItems().filter(isAssistantItem);
  const assistantCount = () => assistantItems().length;
  const userCount = () => allItems().filter(isUserItem).length;
  const lastAssistant = () => {
    const it = assistantItems();
    return it.length ? it[it.length - 1] : null;
  };

  const _idMap = new WeakMap();
  let _idSeq = 0;
  function lastAssistantId() {
    const it = lastAssistant();
    if (!it) return null;
    let id = _idMap.get(it);
    if (!id) { id = ++_idSeq; _idMap.set(it, id); }
    return id;
  }

  const chatIsEmpty = () => allItems().length === 0;
  const conversationKey = () =>
    (/\/prompts\/(?!new_chat\b)[^/?#]+/.test(location.pathname) ? location.pathname : "");
  const isFreshChat = () => chatIsEmpty() && !conversationKey() && !!getEditor();

  function composerFrame() {
    const ed = getEditor();
    if (!ed) return null;
    return ed.closest("ms-prompt-input-wrapper") || ed.closest("form") || ed.closest("footer") || ed.parentElement;
  }

  function isAnchorCandidate(el) {
    if (!el || (el.closest && el.closest("#zs-root"))) return false;
    if (!el.getBoundingClientRect) return false;
    const r = el.getBoundingClientRect();
    const maxW = Math.min(window.innerWidth - 16, 1100);
    if (r.width < 260 || r.width > maxW || r.height < 44 || r.height > 320) return false;
    if (r.top < 4 || r.bottom > window.innerHeight + 20) return false;
    try {
      const st = getComputedStyle(el);
      if (st.display.includes("flex") && st.flexDirection === "row" && r.height < 64) return false;
    } catch {}
    return true;
  }

  function barAnchor() {
    const ed = getEditor();
    if (!ed) return null;
    const wrap = ed.closest("ms-prompt-input-wrapper");
    if (wrap && isAnchorCandidate(wrap)) return wrap;
    let n = ed.parentElement;
    for (let i = 0; i < 8 && n && n !== document.body && n.tagName !== "MAIN"; i++) {
      if (n.closest && n.closest("#zs-root")) break;
      const cl = [...(n.classList || [])];
      if ((cl.some((c) => c.startsWith("rounded") || c.includes("prompt-input") || c.includes("composer"))) && isAnchorCandidate(n)) {
        return n;
      }
      n = n.parentElement;
    }
    const f = composerFrame();
    if (isAnchorCandidate(f)) return f;
    return null;
  }

  function setInputLock(on) {
    _locked = on;
    const ed = getEditor();
    if (on) {
      if (!ed) return;
      _lockedEl = ed;
      if (ed.tagName === "TEXTAREA") {
        ed.setAttribute("readonly", "");
      } else {
        if (!ed.dataset.zsPrevCe) ed.dataset.zsPrevCe = ed.getAttribute("contenteditable") || "true";
        ed.setAttribute("contenteditable", "false");
      }
      ed.setAttribute("data-zs-locked", "1");
      return;
    }
    const targets = [];
    if (ed) targets.push(ed);
    if (_lockedEl && _lockedEl !== ed && _lockedEl.isConnected) targets.push(_lockedEl);
    _lockedEl = null;
    for (const t of targets) {
      if (t.tagName === "TEXTAREA") {
        t.removeAttribute("readonly");
      } else {
        t.setAttribute("contenteditable", t.dataset.zsPrevCe || "true");
        delete t.dataset.zsPrevCe;
      }
      t.removeAttribute("data-zs-locked");
    }
  }

  const isInTurn = (b) => !!(b && b.closest && b.closest("ms-chat-turn, [data-turn-role]"));

  const BAD_RUN_RE = /setting|panel|toggle|rerun/i;
  const EXPLICIT_RUN_RE = /^\s*(?:run|send)(?:\s+ctrl|\s*⌘|\s*↵|\s+prompt|\s*$)/i;

  function isStopBtn(b) {
    if (!b || isInTurn(b) || (b.closest && b.closest("#zs-root"))) return false;
    const rawTxt = (b.textContent || "").replace(/\s+/g, " ").trim();
    const sig = `${b.getAttribute("aria-label") || ""} ${rawTxt}`;
    if (EXPLICIT_RUN_RE.test(rawTxt) && !/\b(?:stop|cancel|abort|interrupt|arr[êe]t)\b/i.test(sig)) return false;
    if (b.classList && b.classList.contains("stoppable")) return true;
    if (b.closest && b.closest("run-button.stoppable, ms-run-button.stoppable, .stoppable")) return true;
    if (b.matches && b.matches('[data-testid*="stop" i]')) return true;
    if (/\b(?:stop|cancel|abort|interrupt|arr[êe]t)\b/i.test(sig)) return true;
    const icon = b.querySelector && b.querySelector("mat-icon");
    if (icon) {
      const name = (icon.getAttribute("fonticon") || icon.getAttribute("data-mat-icon-name") || icon.textContent || "").trim().toLowerCase();
      if (name === "stop" || name === "stop_circle" || name === "stop_circle_outline") return true;
    }
    const comp = barAnchor() || composerFrame();
    const inComposer = (comp && comp.contains(b)) || !!(b.closest && b.closest("run-button, ms-run-button, ms-prompt-input-wrapper"));
    if (inComposer && !NON_SEND_BTN_RE.test(sig) && b.querySelector && b.querySelector("svg rect")) return true;
    return false;
  }

  const NON_SEND_BTN_RE = /stop|cancel|abort|interrupt|arr[êe]t|mic|voice|audio|record|dictat|attach|upload|file|image|add|plus|tune|setting|panel|toggle|rerun|history|tool|grounding|search|credit|claim|share|edit|structured|function|clear|compare|system|token|code|menu|close|dismiss|default|model/i;
  function sendButton() {
    for (const sel of S.runSels) {
      for (const b of document.querySelectorAll(sel)) {
        const sig = `${b.getAttribute("aria-label") || ""} ${b.textContent || ""}`;
        if (BAD_RUN_RE.test(sig)) continue;
        if (!isInTurn(b) && !isStopBtn(b) && isVisibleBox(b)) return b;
      }
    }
    const ed = getEditor();
    const composerScope = barAnchor() || composerFrame() || (ed && ed.closest && ed.closest("ms-prompt-input-wrapper, footer, main")) || document;
    if (composerScope && composerScope.querySelectorAll) {
      for (const b of composerScope.querySelectorAll("button")) {
        if (isInTurn(b) || !isVisibleBox(b) || isStopBtn(b)) continue;
        const normAria = (b.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim();
        const normTxt = (b.innerText || b.textContent || "").replace(/\s+/g, " ").trim();
        if (BAD_RUN_RE.test(`${normAria} ${normTxt}`)) continue;
        if (EXPLICIT_RUN_RE.test(normTxt) || EXPLICIT_RUN_RE.test(normAria)) return b;
      }
    }
    const tightScope = barAnchor() || composerFrame() || (ed && ed.parentElement);
    if (!tightScope || !tightScope.querySelectorAll) return null;
    let best = null;
    let bestRight = -Infinity;
    for (const b of tightScope.querySelectorAll("button")) {
      if (isInTurn(b) || !isVisibleBox(b) || isStopBtn(b)) continue;
      const sig = `${b.getAttribute("aria-label") || ""} ${b.textContent || ""}`.trim();
      if (NON_SEND_BTN_RE.test(sig)) continue;
      if (!b.querySelector("svg, mat-icon")) continue;
      const r = b.getBoundingClientRect ? b.getBoundingClientRect() : null;
      const right = r ? r.right : 0;
      if (right >= bestRight) { bestRight = right; best = b; }
    }
    return best;
  }

  function stopButton() {
    for (const sel of [...S.stopSels, ...S.runSels]) {
      for (const b of document.querySelectorAll(sel)) {
        if (!isInTurn(b) && isVisibleBox(b) && isStopBtn(b)) return b;
      }
    }
    const scope = barAnchor() || composerFrame();
    if (scope && scope.querySelectorAll) {
      for (const b of scope.querySelectorAll("button")) {
        if (!isInTurn(b) && isVisibleBox(b) && isStopBtn(b)) return b;
      }
    }
    return null;
  }

  function thinkingText(item) {
    if (!item || !item.querySelectorAll) return "";
    const parts = [];
    for (const el of item.querySelectorAll(S.thinking)) {
      if (el.closest && el.closest(".zs-chip")) continue;
      if (el.parentElement && el.parentElement.closest(S.thinking)) continue;
      const t = (el.innerText || el.textContent || "").trim();
      if (t) parts.push(t);
    }
    return parts.join("\n");
  }

  function streamText(item) {
    if (!item) return "";
    const th = thinkingText(item);
    const body = textWithout(replyContainer(item) || item, ".zs-chip");
    return th ? (th + "\n" + body) : body;
  }
  const streamLen = (item) => streamText(item === undefined ? lastAssistant() : item).length;

  let _streamMax = -1, _streamAt = 0, _streamItem = null;
  function sampleStream() {
    const item = lastAssistant();
    const len = streamText(item).length;
    const now = Date.now();
    if (item !== _streamItem || len < _streamMax - 400) {
      _streamItem = item; _streamMax = len; _streamAt = now; return;
    }
    if (len > _streamMax) { _streamMax = len; _streamAt = now; }
  }
  const grewWithin = (ms) => _streamMax > 1 && Date.now() - _streamAt < ms;

  const WEDGE_MS = 60000;
  let _stopSince = 0;
  function genActive() {
    sampleStream();
    const stop = !!stopButton();
    const now = Date.now();
    if (stop) {
      if (!_stopSince) _stopSince = now;
      return (now - _streamAt < WEDGE_MS) || (now - _stopSince < 2500);
    }
    _stopSince = 0;
    return grewWithin(timings.GEN_IDLE_MS);
  }
  const isGenerating = genActive;
  const isBusyNow = genActive;
  const isHardGenerating = () => !!stopButton();

  const turnHalted = () => false;
  const findContinueBtn = () => null;
  const clickContinueBtn = () => false;

  function snapshot() {
    try {
      const it = lastAssistant();
      return it ? { th: thinkingText(it).trim().length, rp: itemText(it).length } : { th: 0, rp: 0 };
    } catch { return {}; }
  }

  function readAssistant() {
    const item = lastAssistant();
    if (!item) return { present: false, reply: "", thinking: "", item: null };
    return {
      present: true,
      reply: classifyText(item, ".zs-chip").trim(),
      thinking: thinkingText(item).trim(),
      item,
    };
  }

  async function waitFor(pred, timeout) {
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) {
      if (pred()) return true;
      await sleep(120);
    }
    return false;
  }

  const SEND_MAX_CHARS = 116000;
  const SEND_MAX_LINES = 800;
  const INSERT_CHUNK_LINES = 40;
  function truncateForSend(text) {
    if (!text) return text;
    const lines = String(text).split("\n");
    if (text.length <= SEND_MAX_CHARS && lines.length <= SEND_MAX_LINES) return text;
    const marker = (what) => `\n\n[…ZeroScript: result truncated (${what}) for Google AI Studio composer…]\n\n`;
    let out = text;
    if (lines.length > SEND_MAX_LINES) {
      const head = Math.floor(SEND_MAX_LINES * 0.85);
      out = lines.slice(0, head).join("\n") + marker(`${lines.length - SEND_MAX_LINES} lines omitted`) + lines.slice(lines.length - (SEND_MAX_LINES - head)).join("\n");
    }
    if (out.length > SEND_MAX_CHARS) {
      const budget = SEND_MAX_CHARS - 300;
      const head = Math.floor(budget * 0.85);
      out = out.slice(0, head) + marker(`${out.length - budget} chars omitted`) + out.slice(out.length - (budget - head));
    }
    return out;
  }

  const sameText = (a, b) => String(a || "").replace(/\s+/g, "") === String(b || "").replace(/\s+/g, "");

  function setTextareaValue(el, v) {
    const proto = window.HTMLTextAreaElement && window.HTMLTextAreaElement.prototype;
    const setter = proto && Object.getOwnPropertyDescriptor(proto, "value");
    if (setter && setter.set) setter.set.call(el, v);
    else el.value = v;
    try { el.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText" })); }
    catch { el.dispatchEvent(new Event("input", { bubbles: true })); }
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function setEditorText(ed, text) {
    ed.focus();
    if (document.activeElement !== ed) {
      await sleep(20);
      ed.focus();
    }
    if (ed.tagName === "TEXTAREA") {
      setTextareaValue(ed, text);
      return;
    }
    const sel = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(ed);
    sel.removeAllRanges();
    sel.addRange(range);
    const lines = String(text).split("\n");
    for (let i = 0; i < lines.length; i++) {
      if (lines[i]) document.execCommand("insertText", false, lines[i]);
      if (i < lines.length - 1) document.execCommand("insertLineBreak");
      if (i && i % INSERT_CHUNK_LINES === 0) await sleep(0);
    }
    try { ed.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText" })); }
    catch { ed.dispatchEvent(new Event("input", { bubbles: true })); }
    if ((ed.textContent || "").trim() === "" && String(text).trim() !== "") {
      try {
        const dt = new DataTransfer();
        dt.setData("text/plain", String(text));
        ed.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
      } catch {}
    }
    if ((ed.textContent || "").trim() === "" && String(text).trim() !== "") {
      ed.textContent = String(text);
      try { ed.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText" })); }
      catch { ed.dispatchEvent(new Event("input", { bubbles: true })); }
    }
  }

  async function typeAndSend(text, images) {
    const ed = getEditor();
    if (!ed) throw new Error("Google AI Studio input box not found");
    text = truncateForSend(text);
    const relock = _locked;
    if (relock) {
      if (ed.tagName === "TEXTAREA") ed.removeAttribute("readonly");
      else ed.setAttribute("contenteditable", ed.dataset.zsPrevCe || "true");
    }
    const isBtnReady = (b) => !!b && !b.disabled && b.getAttribute("aria-disabled") !== "true";
    const wasSent = () => editorText().trim() === "" || !!stopButton();
    try {
      if (!sameText(editorText(), text)) await setEditorText(ed, text);
      if (images && images.length) {
        try { await attachImages(images); } catch {}
      }
      await waitFor(() => isBtnReady(sendButton()), 3500);
      const btn = sendButton();
      diag("aistudio.send", {
        len: text.length,
        btnText: (btn && (btn.innerText || btn.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40)) || "",
        aria: (btn && btn.getAttribute("aria-label")) || "",
        disabled: btn ? !!btn.disabled : null,
        ariaDisabled: btn ? btn.getAttribute("aria-disabled") : null,
      });
      if (isBtnReady(btn)) {
        try { btn.focus(); } catch {}
        btn.click();
        if (await waitFor(wasSent, 450)) return;
      }
      const ctrlEnter = { key: "Enter", code: "Enter", keyCode: 13, which: 13, ctrlKey: true, bubbles: true, cancelable: true };
      ed.focus();
      ed.dispatchEvent(new KeyboardEvent("keydown", ctrlEnter));
      ed.dispatchEvent(new KeyboardEvent("keyup", ctrlEnter));
      document.dispatchEvent(new KeyboardEvent("keydown", ctrlEnter));
      document.dispatchEvent(new KeyboardEvent("keyup", ctrlEnter));
      if (await waitFor(wasSent, 250)) return;
      const btn2 = sendButton();
      if (isBtnReady(btn2)) {
        for (const ev of ["pointerdown", "mousedown", "mouseup", "click"]) {
          btn2.dispatchEvent(new MouseEvent(ev, { bubbles: true, cancelable: true, view: window }));
        }
        if (await waitFor(wasSent, 300)) return;
      }
      const plainEnter = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true };
      ed.dispatchEvent(new KeyboardEvent("keydown", plainEnter));
      ed.dispatchEvent(new KeyboardEvent("keyup", plainEnter));
    } finally {
      if (relock) setInputLock(true);
    }
  }

  function stopGeneration() {
    const b = stopButton();
    if (b) try { b.click(); } catch {}
  }

  function isBuildMode() {
    if (/^\/(?:u\/\d+\/)?(?:apps|build)(?:\/|$)/i.test(location.pathname)) return true;
    const ed = getEditor();
    if (ed) {
      const sig = `${ed.getAttribute("placeholder") || ""} ${ed.getAttribute("aria-label") || ""}`;
      if (/make changes,\s*add new features/i.test(sig)) return true;
    }
    return false;
  }

  function modeWarning() {
    if (isBuildMode()) {
      return "<b>Build mode</b> (web preview) · switch to <b>Chat</b> for Studio.";
    }
    return "";
  }

  async function switchToSupportedMode() {
    for (const sel of ['a[href*="/prompts/new_chat"]', 'a[href*="/prompts"]']) {
      for (const el of document.querySelectorAll(sel)) {
        if (isVisibleBox(el)) {
          try { el.click(); } catch {}
          await waitFor(() => !isBuildMode() && !!getEditor(), 4000);
          return true;
        }
      }
    }
    location.assign("https://aistudio.google.com/prompts/new_chat");
    return true;
  }

  const INTERFERING_TOOL_RE = /grounding with google search|url context/i;

  function activeInterferingTools() {
    const found = [];
    const scope = barAnchor() || composerFrame();
    if (scope && scope.querySelectorAll) {
      for (const el of scope.querySelectorAll("button, [role='listitem'], [class*='chip'], [class*='tool']")) {
        if (el.closest("#zs-root") || isInTurn(el)) continue;
        const txt = (el.textContent || "").replace(/\s+/g, " ").trim();
        if (!txt || txt.length > 80 || !INTERFERING_TOOL_RE.test(txt)) continue;
        const closeBtn = el.tagName === "BUTTON"
          ? el
          : (el.querySelector("button[aria-label*='remove' i], button[aria-label*='close' i], button[aria-label*='disable' i], button:last-of-type") || null);
        if (closeBtn && !found.some((f) => f.el === closeBtn)) {
          found.push({ label: txt, el: closeBtn, kind: "chip" });
        }
      }
    }
    for (const sw of document.querySelectorAll('[role="switch"][aria-checked="true"], mat-slide-toggle button[aria-checked="true"], mat-slide-toggle input[type="checkbox"]:checked')) {
      if (sw.closest("#zs-root") || isInTurn(sw)) continue;
      const row = sw.closest("div, section, li, mat-slide-toggle") || sw.parentElement;
      const label = ((row && row.textContent) || sw.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim();
      if (INTERFERING_TOOL_RE.test(label) && !found.some((f) => f.el === sw)) {
        found.push({ label: label.slice(0, 60), el: sw, kind: "toggle" });
      }
    }
    return found;
  }

  async function disableInterferingTools() {
    const items = activeInterferingTools();
    if (!items.length) return 0;
    let cleared = 0;
    for (const it of items) {
      try {
        it.el.click();
        cleared++;
      } catch {}
    }
    if (cleared) {
      diag("aistudio.toolsCleared", { count: cleared, labels: items.map((x) => x.label) });
      await sleep(150);
    }
    return cleared;
  }

  function bootErrorHint(text) {
    if (/internal error|resource exhausted|quota/i.test(text || "")) {
      return "Tip: In Google AI Studio, turn off Grounding with Google Search & URL context in the composer/Tools sidebar, or switch models (e.g. Gemini 2.5 Pro/Flash), then click Start again.";
    }
    return "";
  }

  function enforceComposer() { return { ready: !isBuildMode() }; }
  async function ensureComposerReady(reason) {
    if (isBuildMode()) {
      diag("mode_ready", { reason, provider: "aistudio", buildMode: true });
      return {
        ready: false,
        detail: "Google AI Studio is in Build (web-app preview) mode. Click Chat in the left sidebar or open aistudio.google.com/prompts/new_chat, then click Start Roblox agent.",
      };
    }
    if (!getEditor()) await waitFor(() => !!getEditor(), 1500);
    await disableInterferingTools();
    const ed = getEditor();
    diag("mode_ready", { reason, provider: "aistudio", hasEditor: !!ed });
    return {
      ready: !!ed,
      detail: ed ? "" : "Google AI Studio input box not found on this page. Open a New Chat or reload the page, then try again.",
    };
  }

  function scanError() {
    try {
      for (const el of document.querySelectorAll(S.errorSurfaces)) {
        if (el.offsetParent === null) continue;
        if (el.closest(S.turnSel)) continue;
        const t = (el.innerText || "").trim();
        if (t.length > 8 && t.length < 600 && RE.contextLimit.test(t)) return t.slice(0, 240);
      }
    } catch {}
    if (!getEditor()) return "The input box disappeared (session ended?).";
    return null;
  }
  const isTooLongMsg = (text) => RE.tooLong.test(text);
  const isBusyMsg = (text) => RE.busy.test(text);

  function fileFromImage(img, i) {
    const mime = img.mimeType || "image/jpeg";
    const bin = atob(img.data);
    const arr = new Uint8Array(bin.length);
    for (let j = 0; j < bin.length; j++) arr[j] = bin.charCodeAt(j);
    const ext = mime.includes("png") ? "png" : "jpg";
    return new File([arr], `zeroscript_${Date.now()}_${i}.${ext}`, { type: mime });
  }
  async function attachImages(images) {
    if (!images || !images.length) return false;
    const scope = barAnchor() || composerFrame();
    const inp = (scope && scope.querySelector('input[type="file"]')) || document.querySelector('input[type="file"]');
    const dt = new DataTransfer();
    images.forEach((img, i) => { try { dt.items.add(fileFromImage(img, i)); } catch {} });
    if (!dt.items.length) return false;
    if (inp) {
      try { inp.files = dt.files; inp.dispatchEvent(new Event("change", { bubbles: true })); } catch {}
    } else {
      const ed = getEditor();
      if (ed) {
        ed.focus();
        ed.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
      }
    }
    return await waitFor(() => !!document.querySelector('ms-image-chunk, img[src^="blob:"], [class*="preview"], [class*="thumbnail"], [class*="attachment"]'), 12000);
  }
  function clearAttachments() {
    try {
      const scope = barAnchor() || composerFrame() || document;
      scope.querySelectorAll('button[aria-label*="Remove" i], button[aria-label*="Delete" i]')
        .forEach((b) => { try { if (!isInTurn(b)) b.click(); } catch {} });
    } catch {}
  }

  async function openNewChat() {
    if (isBuildMode()) {
      location.assign("https://aistudio.google.com/prompts/new_chat");
      return true;
    }
    for (const sel of ['a[href*="/prompts/new_chat"]', 'button[aria-label*="Create new prompt" i]', 'button[aria-label*="New chat" i]', 'a[aria-label*="New chat" i]']) {
      for (const el of document.querySelectorAll(sel)) {
        if (isVisibleBox(el)) {
          try { el.click(); } catch {}
          await waitFor(() => chatIsEmpty() && !!getEditor(), 5000);
          return true;
        }
      }
    }
    location.assign("https://aistudio.google.com/prompts/new_chat");
    return true;
  }

  const PROMPT_EXTRA = `- NEVER CLAIM ZEROSCRIPT IS INACTIVE OR TELL THE USER TO PASTE CODE: the ZeroScript browser extension is live in this tab for the entire session. Always emit a fenced ZeroScript command block directly (multi_edit or ###LUA### ... ###END_LUA###) instead of asking the user to paste code into Roblox Studio.`;

  function installSendHooks(handlers) {
    document.addEventListener("keydown", (e) => {
      if (!e.isTrusted) return;
      if (e.key !== "Enter" || e.shiftKey || e.isComposing) return;
      const ed = getEditor();
      if (!ed || !ed.contains(e.target)) return;
      if (editorText().trim() === "") return;
      if (handlers.isBlocked()) return;
      if (e.ctrlKey || e.metaKey) {
        if (!handlers.isStarted()) {
          if (!chatIsEmpty()) return;
          handlers.onBlockedAttempt();
          return;
        }
        handlers.onUserMessage(assistantCount());
        return;
      }
      // AI Studio defaults to Ctrl+Enter, with an optional plain-Enter preference;
      // defer briefly so a newline keypress never falsely triggers turn tracking.
      const u0 = userCount();
      const a0 = assistantCount();
      setTimeout(() => {
        if (editorText().trim() === "" || userCount() > u0 || isGenerating()) {
          if (!handlers.isStarted()) {
            if (chatIsEmpty()) handlers.onBlockedAttempt();
          } else {
            handlers.onUserMessage(a0);
          }
        }
      }, 250);
    }, true);

    document.addEventListener("click", (e) => {
      if (!e.isTrusted) return;
      if (!getEditor()) return;
      const b = e.target && e.target.closest && e.target.closest("button");
      if (!b || isInTurn(b)) return;
      if (isStopBtn(b)) { handlers.onNativeStop(); return; }
      if (b !== sendButton() && !S.runSels.some((sel) => b.matches(sel))) return;
      if (b.disabled) return;
      if (handlers.isBlocked()) return;
      if (!handlers.isStarted()) {
        if (!chatIsEmpty()) return;
        handlers.onBlockedAttempt();
        return;
      }
      handlers.onUserMessage(assistantCount());
    }, true);
  }

  const CMD_SHAPE = /"(?:command|tool)"\s*:\s*"|###\s*lua|###mcp_tool###/i;
  function findToolBlockSpot(item) {
    const rc = replyContainer(item);
    if (!rc) return null;
    let hidAny = null;
    rc.querySelectorAll(S.codeWrap).forEach((cw) => {
      if (cw.closest(".zs-chip")) return;
      if (CMD_SHAPE.test(cw.textContent || "")) {
        cw.classList.add("zs-tool-hide");
        rc.classList.add("zs-cmd-mask");
        hidAny = hidAny || { parent: cw.parentElement, ref: cw };
      }
    });
    [...rc.children].forEach((el) => {
      if (el.classList.contains("zs-chip") || el.querySelector(S.codeWrap)) return;
      const t = el.textContent || "";
      if ((/^\{\s*"(?:command|tool)"\s*:/.test(t.trim()) || t.length < 600) && CMD_SHAPE.test(t)) {
        el.classList.add("zs-tool-hide");
        rc.classList.add("zs-cmd-mask");
        hidAny = hidAny || { parent: el.parentElement, ref: el };
      }
    });
    return hidAny;
  }

  return {
    id: "aistudio",
    displayName: "Google AI Studio",
    supportsVision: true,
    timings,
    thinkingSel: S.thinking,
    chipAtItemLevel: true,
    reliableCounts: true,
    init({ diag: d } = {}) {
      if (d) diag = d;
      try { document.documentElement.setAttribute("data-zs-aistudio-ver", "2026-11-25_v1.9.1"); } catch {}
    },
    allItems, isUserItem, isAssistantItem, itemText, classifyText,
    assistantCount, userCount, lastAssistant, lastAssistantId, readAssistant,
    streamLen, snapshot,
    getEditor, editorText, chatIsEmpty, isFreshChat, composerFrame, barAnchor,
    setInputLock, typeAndSend, stopGeneration,
    isGenerating, isBusyNow, isHardGenerating,
    enforceComposer, ensureComposerReady, modeWarning,
    modeSwitchLabel: "↗ Open Chat", switchToSupportedMode,
    activeInterferingTools, disableInterferingTools, bootErrorHint,
    turnHalted, findContinueBtn, clickContinueBtn,
    scanError, isTooLongMsg, isBusyMsg,
    attachImages, clearAttachments, openNewChat, conversationKey,
    installSendHooks, findToolBlockSpot,
    promptExtra: PROMPT_EXTRA,
    resendSystemEvery: 5,
    sendCharBudget: SEND_MAX_CHARS - 4000,
  };
})();

