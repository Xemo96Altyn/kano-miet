(function () {
  const basePath = window.KANO_BASE_PATH || "/";
  const baseUrl = new URL(basePath, window.location.origin);

  function normalizePath(path) {
    return String(path || "").replace(/^\/+/, "");
  }

  function buildUrl(path) {
    return new URL(normalizePath(path), baseUrl).toString();
  }

  function buildPath(path) {
    const url = new URL(normalizePath(path), baseUrl);
    return `${url.pathname}${url.search}${url.hash}`;
  }

  window.kanoBasePath = basePath;
  window.kanoUrl = buildUrl;
  window.kanoPath = buildPath;
  window.kanoApiUrl = function kanoApiUrl(path) {
    return buildUrl(`api/${normalizePath(path)}`);
  };
  window.kanoApiPath = function kanoApiPath(path) {
    return buildPath(`api/${normalizePath(path)}`);
  };

  const originalFetch = window.fetch.bind(window);
  window.fetch = function patchedFetch(input, init) {
    if (typeof input === "string" && input.startsWith("/")) {
      return originalFetch(buildUrl(input), init);
    }
    if (input instanceof Request && input.url.startsWith(window.location.origin + "/")) {
      const relativePath = input.url.slice(window.location.origin.length);
      if (relativePath.startsWith("/")) {
        return originalFetch(new Request(buildUrl(relativePath), input), init);
      }
    }
    return originalFetch(input, init);
  };

  function rewriteRootRelativeAttribute(selector, attribute) {
    document.querySelectorAll(selector).forEach((element) => {
      const value = element.getAttribute(attribute);
      if (value && value.startsWith("/")) {
        element.setAttribute(attribute, buildPath(value));
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function rewriteRootRelativePaths() {
    rewriteRootRelativeAttribute("[href]", "href");
    rewriteRootRelativeAttribute("[src]", "src");
  });
})();
