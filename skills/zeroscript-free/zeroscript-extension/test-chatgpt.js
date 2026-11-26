// Quick Node smoke test for providers/chatgpt.js (run: node test-chatgpt.js).
// Not shipped.
//
// Why this exists: every ChatGPT bug fixed in 1.5.1 was a READING bug, not a
// parsing one - the parser was fine, the text handed to it was wrong. ChatGPT
// renders code blocks with CodeMirror, which emits one element per line and NO
// newline characters at all, so a naive read glued a whole script onto one line
// ("your code block was empty"), and past a few thousand characters CodeMirror
// stops rendering the rest of a long line, so commands ran truncated. Those are
// exactly the regressions this file guards.
//
// The provider is a browser IIFE, so it is evaluated here against a minimal
// stub DOM (below) - just enough of the Node/Element surface that textWithout
// walks. No jsdom, no npm install: the repo has no dependencies and this test
// keeps it that way.
const fs = require("fs");

// ── Stub DOM ────────────────────────────────────────────────────────────────
// el("div", {class, attrs}, children) / txt("…"). Only the members tested
// here are implemented; anything else stays undefined on purpose so a future
// change that needs more DOM fails loudly here instead of silently passing.
function txt(v) {
  return { nodeType: 3, nodeValue: v, childNodes: [] };
}
function matchSimple(node, sel) {
  const parts = sel.split(",").map((s) => s.trim()).filter(Boolean);
  return parts.some((part) => {
    let rest = part;
    const tagM = rest.match(/^[a-z0-9_-]+/i);
    if (tagM) {
      if (node.tagName !== tagM[0].toUpperCase()) return false;
      rest = rest.slice(tagM[0].length);
    }
    const attrRe = /\[([a-z0-9_-]+)(?:=(?:'([^']*)'|"([^"]*)"|([^\]]*)))?\]/gi;
    let m;
    while ((m = attrRe.exec(rest))) {
      const val = node.getAttribute(m[1]);
      if (val === null) return false;
      const want = m[2] !== undefined ? m[2] : (m[3] !== undefined ? m[3] : m[4]);
      if (want !== undefined && val !== want) return false;
    }
    rest = rest.replace(attrRe, "");
    const clsRe = /\.([a-z0-9_-]+)/gi;
    while ((m = clsRe.exec(rest))) {
      if (!node.classList.contains(m[1])) return false;
    }
    rest = rest.replace(clsRe, "");
    return rest.trim() === "";
  });
}
function el(tag, opts, children) {
  const o = opts || {};
  const classes = new Set((o.class || "").split(/\s+/).filter(Boolean));
  const attrs = o.attrs || {};
  const kids = (children || []).map((c) => (typeof c === "string" ? txt(c) : c));
  const node = {
    nodeType: 1,
    tagName: tag.toUpperCase(),
    parentElement: null,
    childNodes: kids,
    get children() { return this.childNodes.filter((c) => c.nodeType === 1); },
    get textContent() {
      return this.childNodes.map((c) => (c.nodeType === 3 ? c.nodeValue : c.textContent)).join("");
    },
    classList: {
      contains: (c) => classes.has(c),
      add: (...cs) => cs.forEach((c) => classes.add(c)),
      remove: (...cs) => cs.forEach((c) => classes.delete(c)),
    },
    getAttribute: (n) => (n in attrs ? attrs[n] : null),
    matches: (sel) => matchSimple(node, sel),
    closest: (sel) => {
      for (let cur = node; cur; cur = cur.parentElement) {
        if (cur.nodeType === 1 && cur.matches(sel)) return cur;
      }
      return null;
    },
  };
  kids.forEach((c) => { if (c.nodeType === 1) c.parentElement = node; });
  node.querySelectorAll = (sel) => {
    const out = [];
    const walk = (n) => {
      for (const c of n.childNodes) {
        if (c.nodeType !== 1) continue;
        if (c.matches(sel)) out.push(c);
        walk(c);
      }
    };
    walk(node);
    return out;
  };
  node.querySelector = (sel) => node.querySelectorAll(sel)[0] || null;
  return node;
}

// ── Load the provider against the stub globals ──────────────────────────────
const dispatchedEvents = [];
const docListeners = {};
let stubQuerySelector = () => null;
let stubQuerySelectorAll = () => [];
global.document = {
  querySelector: (s) => stubQuerySelector(s),
  querySelectorAll: (s) => stubQuerySelectorAll(s),
  addEventListener: (type, fn) => { (docListeners[type] = docListeners[type] || []).push(fn); },
  dispatchEvent: (ev) => { dispatchedEvents.push(ev && ev.type); },
  documentElement: { classList: { contains: () => false }, setAttribute: () => {} },
  body: null,
};
global.window = { location: { pathname: "/" }, addEventListener: () => {} };
global.location = global.window.location;
global.CustomEvent = class { constructor(t) { this.type = t; } };
global.MutationObserver = class { observe() {} disconnect() {} };
global.getComputedStyle = () => ({});
const P = new Function(
  fs.readFileSync(__dirname + "/providers/chatgpt.js", "utf8") + "; return ZSProvider;"
)();

const ok = (name, cond) => { console.log((cond ? "PASS" : "FAIL") + "  " + name); if (!cond) process.exitCode = 1; };

// ── The CodeMirror line collapse (the 1.5.1 headline bug) ───────────────────
// A code block is <div class="cm-content"> with one <div class="cm-line"> per
// source line and no newline text nodes anywhere. Reading it with textContent
// returns `###LUA###return 1+1###END_LUA###` - one line, unparseable. Every
// cm-line must terminate.
const cmBlock = (lines, attrs) =>
  el("div", { class: "cm-content", attrs: attrs || {} },
     lines.map((l) => el("div", { class: "cm-line" }, l === "" ? [] : [l])));

dispatchedEvents.length = 0;
const collapsed = P.textWithout(cmBlock(["###LUA###", "return 1+1", "###END_LUA###"]));
ok("cm-lines are newline-terminated", collapsed.includes("###LUA###\nreturn 1+1\n###END_LUA###"));
ok("syncCM dispatches zs-cm-sync when called directly on .cm-content", dispatchedEvents.includes("zs-cm-sync"));

// A blank source line is an EMPTY cm-line. Swallowing it shifts every Luau
// error line number reported afterwards, so it must survive as "\n".
const blanks = P.textWithout(cmBlock(["local a = 1", "", "return a"]));
ok("empty cm-line survives as a blank line", /local a = 1\n\nreturn a/.test(blanks));

// ── The MAIN-world tap wins over the rendered lines ─────────────────────────
// Past ~2000-4000 chars CodeMirror renders only PART of a long line, so the
// visible lines are a truncated copy. providers/chatgpt-cm.js publishes the
// editor's true document on data-zs-cm; when present it must be used verbatim
// and the (short) rendered subtree ignored - this is what made a 21k-character
// command stop executing cut off.
const full = '{"command":"multi_edit","params":{"edits":[{"old_string":"a","new_string":"' + "x".repeat(5000) + '"}]}}';
const tapped = P.textWithout(cmBlock(['{"command":"multi_edit","params":{"edits":[{"old_str'], { "data-zs-cm": full }));
ok("data-zs-cm tap is preferred over rendered lines", tapped.includes(full));
ok("tapped block parses as JSON", (() => {
  const s = tapped.slice(tapped.indexOf("{"), tapped.lastIndexOf("}") + 1);
  try { return JSON.parse(s).params.edits[0].new_string.length === 5000; } catch { return false; }
})());
// An EMPTY tap value is still a real document (an empty editor), not a missing
// attribute: getAttribute must be checked against null, never falsiness.
const emptyTap = P.textWithout(cmBlock(["stale rendered text"], { "data-zs-cm": "" }));
ok("empty tap value is honoured, not treated as absent", !emptyTap.includes("stale"));

// ── Ordinary prose is untouched ─────────────────────────────────────────────
// Block elements break lines; inline text must not gain stray newlines, or the
// core's marker matching sees a shape the model never wrote.
const prose = P.textWithout(
  el("div", {}, [
    el("p", {}, ["Running the command now:"]),
    el("p", {}, ["Done ", el("strong", {}, ["with"]), " no gaps."]),
  ])
);
ok("blocks separate, inline text stays joined", /Running the command now:\nDone with no gaps\./.test(prose));
// (A block closes with a trailing newline of its own - hence the optional \n.)
ok("a <br> is a newline", /^a\nb\n?$/.test(P.textWithout(el("p", {}, ["a", el("br", {}), "b"]))));

// ── excludeSel ──────────────────────────────────────────────────────────────
// The core passes ".zs-chip" so its own injected chip never counts as model
// output (a chip echoing a tool name would otherwise re-trigger the call).
const withChip = P.textWithout(
  el("div", {}, [el("p", {}, ["real reply"]), el("div", { class: "zs-chip" }, ["execute_luau · 2s"])]),
  ".zs-chip"
);
ok("excluded subtree is skipped", withChip.includes("real reply") && !withChip.includes("execute_luau"));

// ── conversationKey() routes ────────────────────────────────────────────────
global.location.pathname = "/";
ok("conversationKey returns empty string on /", P.conversationKey() === "");
global.location.pathname = "/g/g-proj123";
ok("conversationKey returns empty string on /g/<id>", P.conversationKey() === "");
global.location.pathname = "/c/abc-123";
ok("conversationKey captures /c/<id>", P.conversationKey() === "/c/abc-123");
global.location.pathname = "/g/g-proj123/c/abc-123";
ok("conversationKey captures /g/<id>/c/<conv-id>", P.conversationKey() === "/g/g-proj123/c/abc-123");
global.location.pathname = "/";

// ── findToolBlockSpot() unfenced ranges & large JSON blocks ─────────────────
const pOpen = el("p", {}, ["###LUA:Server###"]);
const pBody = el("p", {}, ["return game.PlaceId"]);
const pClose = el("p", {}, ["###END-LUA###"]);
const pProse = el("p", {}, ["Trailing explanation for the user."]);
const mdUnfenced = el("div", { class: "markdown" }, [pOpen, pBody, pClose, pProse]);
const itemUnfenced = el("div", { attrs: { "data-message-author-role": "assistant" } }, [mdUnfenced]);
P.findToolBlockSpot(itemUnfenced);
ok(
  "findToolBlockSpot hides ###LUA:Server### ... ###END-LUA### range without hiding trailing prose",
  pOpen.classList.contains("zs-tool-hide") &&
  pBody.classList.contains("zs-tool-hide") &&
  pClose.classList.contains("zs-tool-hide") &&
  !pProse.classList.contains("zs-tool-hide") &&
  !mdUnfenced.classList.contains("zs-cmd-mask-all")
);

const bigJsonP = el("p", {}, ['{"command":"multi_edit","params":{"data":"' + "a".repeat(700) + '"}}']);
const itemBigJson = el("div", { attrs: { "data-message-author-role": "assistant" } }, [el("div", { class: "markdown" }, [bigJsonP])]);
P.findToolBlockSpot(itemBigJson);
ok("findToolBlockSpot hides large (>600 char) unfenced JSON command paragraph", bigJsonP.classList.contains("zs-tool-hide"));

// ── installSendHooks() ignores untrusted clicks ─────────────────────────────
const editorStub = el("div", { attrs: { id: "prompt-textarea" } }, ["hello"]);
const stopBtnStub = el("button", { attrs: { "data-testid": "stop-button" } }, ["Stop"]);
stopBtnStub.offsetParent = {};
stubQuerySelector = (s) => (s.includes("#prompt-textarea") ? editorStub : null);
stubQuerySelectorAll = (s) => (s.includes("stop-button") ? [stopBtnStub] : []);
let nativeStops = 0;
P.installSendHooks({
  isBlocked: () => false,
  isStarted: () => true,
  onBlockedAttempt: () => {},
  onUserMessage: () => {},
  onNativeStop: () => { nativeStops++; },
  onNativeContinue: () => {},
});
const clickHook = docListeners.click[docListeners.click.length - 1];
clickHook({ isTrusted: false, target: stopBtnStub });
ok("installSendHooks ignores untrusted (isTrusted: false) stop clicks", nativeStops === 0);
clickHook({ isTrusted: true, target: stopBtnStub });
ok("installSendHooks handles trusted (isTrusted: true) stop clicks", nativeStops === 1);
stubQuerySelector = () => null;
stubQuerySelectorAll = () => [];
