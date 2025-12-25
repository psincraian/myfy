/**
 * Copy to Markdown feature for documentation pages
 * Fetches the original markdown source and copies it to clipboard
 */
(function () {
  "use strict";

  // GitHub repository information
  const REPO_OWNER = "psincraian";
  const REPO_NAME = "myfy";
  const BRANCH = "main";
  const DOCS_DIR = "docs";

  /**
   * Get the markdown file path from the current page URL
   * @returns {string|null} The markdown file path or null if not determinable
   */
  function getMarkdownPath() {
    const path = window.location.pathname;

    // Handle root path
    if (path === "/" || path === "/index.html") {
      return `${DOCS_DIR}/index.md`;
    }

    // Remove trailing slash and /index.html if present
    let cleanPath = path.replace(/\/$/, "").replace(/\/index\.html$/, "");

    // Remove leading slash
    cleanPath = cleanPath.replace(/^\//, "");

    // If empty after cleaning, it's the index
    if (!cleanPath) {
      return `${DOCS_DIR}/index.md`;
    }

    // Construct the markdown path
    return `${DOCS_DIR}/${cleanPath}.md`;
  }

  /**
   * Fetch the raw markdown content from GitHub
   * @param {string} markdownPath - The path to the markdown file
   * @returns {Promise<string>} The markdown content
   */
  async function fetchMarkdown(markdownPath) {
    const url = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${BRANCH}/${markdownPath}`;

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch markdown: ${response.status}`);
    }

    return response.text();
  }

  /**
   * Copy text to clipboard using the fallback method
   * This works in Safari and older browsers
   * @param {string} text - The text to copy
   * @returns {boolean} Whether the copy succeeded
   */
  function copyToClipboardFallback(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.top = "0";
    textarea.style.left = "0";
    textarea.style.width = "2em";
    textarea.style.height = "2em";
    textarea.style.padding = "0";
    textarea.style.border = "none";
    textarea.style.outline = "none";
    textarea.style.boxShadow = "none";
    textarea.style.background = "transparent";
    textarea.setAttribute("readonly", "");
    document.body.appendChild(textarea);

    let success = false;
    try {
      textarea.select();
      textarea.setSelectionRange(0, textarea.value.length);
      success = document.execCommand("copy");
    } catch (err) {
      console.error("Fallback copy failed:", err);
    }

    document.body.removeChild(textarea);
    return success;
  }

  /**
   * Copy text to clipboard
   * Uses ClipboardItem API for Safari compatibility with async content
   * @param {string} text - The text to copy
   * @returns {Promise<void>}
   */
  async function copyToClipboard(text) {
    // Try the modern Clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return;
      } catch (err) {
        // If Clipboard API fails, try fallback
        console.warn("Clipboard API failed, trying fallback:", err);
      }
    }

    // Use fallback for older browsers or if Clipboard API failed
    if (!copyToClipboardFallback(text)) {
      throw new Error("Failed to copy to clipboard");
    }
  }

  /**
   * Copy content to clipboard using ClipboardItem with a Promise
   * This is the Safari-compatible way to handle async clipboard operations
   * @param {Promise<string>} textPromise - A promise that resolves to the text to copy
   * @returns {Promise<void>}
   */
  async function copyToClipboardAsync(textPromise) {
    // Safari supports ClipboardItem with a Promise for the blob
    // This allows us to start the clipboard operation synchronously
    // while the content is still being fetched
    if (
      navigator.clipboard &&
      navigator.clipboard.write &&
      typeof ClipboardItem !== "undefined"
    ) {
      try {
        // Create a ClipboardItem with a Promise that resolves to a Blob
        // This is the key for Safari compatibility - the write() call happens
        // synchronously during the user gesture, but the content is provided async
        const item = new ClipboardItem({
          "text/plain": textPromise.then(
            (text) => new Blob([text], { type: "text/plain" })
          ),
        });
        await navigator.clipboard.write([item]);
        return true;
      } catch (err) {
        console.warn("ClipboardItem with Promise failed:", err);
        return false;
      }
    }
    return false;
  }

  /**
   * Show a temporary tooltip/notification
   * @param {HTMLElement} button - The button element
   * @param {string} message - The message to show
   * @param {boolean} isError - Whether this is an error message
   */
  function showTooltip(button, message, isError = false) {
    const tooltip = document.createElement("span");
    tooltip.className = `copy-markdown-tooltip ${isError ? "error" : "success"}`;
    tooltip.textContent = message;

    button.appendChild(tooltip);

    setTimeout(() => {
      tooltip.remove();
    }, 2000);
  }

  /**
   * Create the copy button element
   * @returns {HTMLButtonElement} The button element
   */
  function createCopyButton() {
    const button = document.createElement("button");
    button.className = "copy-markdown-button";
    button.type = "button";
    button.title = "Copy page as Markdown";
    button.setAttribute("aria-label", "Copy page as Markdown");

    // Lucide copy icon (matches the theme's icon set)
    button.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="copy-icon">
        <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
      </svg>
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="check-icon" style="display: none;">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      <span class="copy-markdown-label">Copy Markdown</span>
    `;

    return button;
  }

  /**
   * Handle the copy button click
   * @param {HTMLButtonElement} button - The button element
   */
  async function handleCopyClick(button) {
    const copyIcon = button.querySelector(".copy-icon");
    const checkIcon = button.querySelector(".check-icon");

    try {
      button.disabled = true;
      button.classList.add("loading");

      const markdownPath = getMarkdownPath();
      if (!markdownPath) {
        throw new Error("Could not determine markdown path");
      }

      // Create the fetch promise
      const markdownPromise = fetchMarkdown(markdownPath);

      // Try Safari-compatible async clipboard first
      // This must be called synchronously during the click event
      const asyncCopySucceeded = await copyToClipboardAsync(markdownPromise);

      if (!asyncCopySucceeded) {
        // Fall back to traditional method - wait for fetch then copy
        const markdown = await markdownPromise;
        await copyToClipboard(markdown);
      }

      // Show success state
      copyIcon.style.display = "none";
      checkIcon.style.display = "inline";
      button.classList.remove("loading");
      button.classList.add("copied");

      showTooltip(button, "Copied!");

      // Reset after delay
      setTimeout(() => {
        copyIcon.style.display = "inline";
        checkIcon.style.display = "none";
        button.classList.remove("copied");
      }, 2000);
    } catch (error) {
      console.error("Failed to copy markdown:", error);
      button.classList.remove("loading");
      showTooltip(button, "Failed to copy", true);
    } finally {
      button.disabled = false;
    }
  }

  /**
   * Initialize the copy button on the page
   */
  function initCopyButton() {
    // Find the content area
    const contentArea = document.querySelector(".md-content__inner");
    if (!contentArea) {
      return;
    }

    // Check if button already exists (for instant navigation)
    if (contentArea.querySelector(".copy-markdown-button")) {
      return;
    }

    // Find the first h1 heading
    const h1 = contentArea.querySelector("h1");
    if (!h1) {
      return;
    }

    // Create a wrapper for the heading and button
    const wrapper = document.createElement("div");
    wrapper.className = "copy-markdown-header";

    // Create the button
    const button = createCopyButton();
    button.addEventListener("click", () => handleCopyClick(button));

    // Insert wrapper before h1
    h1.parentNode.insertBefore(wrapper, h1);
    wrapper.appendChild(h1);
    wrapper.appendChild(button);
  }

  // Initialize on page load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCopyButton);
  } else {
    initCopyButton();
  }

  // Re-initialize on instant navigation (Material theme uses this)
  if (typeof document$ !== "undefined") {
    document$.subscribe(initCopyButton);
  } else {
    // Fallback: listen for popstate and custom navigation events
    window.addEventListener("popstate", () => {
      setTimeout(initCopyButton, 100);
    });
  }
})();
