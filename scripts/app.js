/* ============================================================
   Shared clipboard logic for index + view pages
   Works on HTTP (LAN) with fallback for blocked clipboard APIs
   ============================================================ */

function copyFromElementRemovingButtons(element, button) {
  if (!element) return;

  // Clone so we don’t mutate the DOM
  const clone = element.cloneNode(true);

  // Remove any buttons (copy buttons, action buttons, etc.)
  clone.querySelectorAll("button").forEach(btn => btn.remove());

  const text = (clone.innerText || clone.textContent || "").trim();
  if (!text) return;

  // const showCopied = () => {
  //   const original = button.innerHTML;
  //   button.innerHTML = "✅ Copied!";
  //   setTimeout(() => {
  //     button.innerHTML = original;
  //   }, 1600);
  // };

  const icon = button.querySelector("img");
if (!icon) return;

const originalSrc = icon.src;
icon.src = "/static/resources/copy-success.svg";

setTimeout(() => {
  icon.src = originalSrc;
}, 1200);


  // Modern clipboard API (HTTPS / localhost)
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard
      .writeText(text)
      .then(showCopied)
      .catch(() => fallbackCopy(text, showCopied));
  } else {
    fallbackCopy(text, showCopied);
  }
}

function fallbackCopy(text, onSuccess) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";

  document.body.appendChild(textarea);
  textarea.select();

  try {
    const ok = document.execCommand("copy");
    if (ok) {
      onSuccess();
    } else {
      alert("Copy failed (browser blocked it).");
    }
  } catch (err) {
    alert("Copy failed (browser blocked it).");
  } finally {
    document.body.removeChild(textarea);
  }
}

/* ============================================================
   Index page: copy preview snippet
   HTML usage:
   onclick="copyToClipboard('{{ paste.id }}', this)"
   ============================================================ */

function copyToClipboard(pasteId, button) {
  const contentNode = document.getElementById("content-" + pasteId);
  if (!contentNode) return;

  copyFromElementRemovingButtons(contentNode, button);
}

/* ============================================================
   View page: copy full paste
   HTML usage:
   onclick="copyPaste(this)"
   ============================================================ */

function copyPaste(button) {
  const contentNode = document.getElementById("paste-content");
  if (!contentNode) return;

  copyFromElementRemovingButtons(contentNode, button);
}
