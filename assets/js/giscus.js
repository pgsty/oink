(() => {
  'use strict';
  if (typeof window !== 'undefined' && window.OinkComparePane) return;

  const origin = 'https://giscus.app';
  const frameTimeoutMs = 15000;
  const colorScheme = window.matchMedia('(prefers-color-scheme: dark)');
  const sections = document.querySelectorAll('[data-td-giscus]');
  if (!sections.length) return;

  const resolveTheme = theme => theme && theme.startsWith('/')
    ? new URL(theme, window.location.origin).href
    : theme;

  const getTheme = section => {
    const configuredTheme = section.dataset.theme;
    if (configuredTheme && configuredTheme !== 'auto') return resolveTheme(configuredTheme);

    const siteTheme = document.documentElement.getAttribute('data-bs-theme');
    const colorMode = siteTheme === 'light' || siteTheme === 'dark'
      ? siteTheme
      : document.documentElement.getAttribute('data-td-preset') ? 'light'
        : colorScheme.matches ? 'dark' : 'light';
    try {
      const presets = JSON.parse(section.dataset.tdPresetThemes || '{}');
      const palette = presets[document.documentElement.getAttribute('data-td-preset')];
      if (palette && palette[colorMode]) return resolveTheme(palette[colorMode]);
    } catch (_) {
      // Older/custom markup can keep the original light/dark pair.
    }
    return colorMode === 'dark'
      ? resolveTheme(section.dataset.tdThemeDark)
      : resolveTheme(section.dataset.tdThemeLight);
  };

  const setTheme = section => {
    const frame = section.querySelector('iframe.giscus-frame');
    if (!frame) return;
    frame.contentWindow.postMessage({
      giscus: { setConfig: { theme: getTheme(section) } },
    }, origin);
  };

  const setReady = section => {
    section.setAttribute('aria-busy', 'false');
    const status = section.querySelector('[data-td-giscus-status]');
    if (!status) return;
    status.textContent = '';
    status.classList.add('d-none');
  };

  const setError = section => {
    section.setAttribute('aria-busy', 'false');
    const status = section.querySelector('[data-td-giscus-status]');
    if (!status) return;
    status.textContent = section.dataset.tdErrorMessage || 'Comments could not be loaded.';
    status.classList.remove('d-none');
  };

  const load = section => {
    if (section.dataset.loaded === 'true') return;
    const container = section.querySelector('[data-td-giscus-container]');
    if (!container) return;

    const attributes = {
      src: `${origin}/client.js`,
      'data-repo': section.dataset.repo,
      'data-repo-id': section.dataset.repoId,
      'data-category': section.dataset.category,
      'data-category-id': section.dataset.categoryId,
      'data-mapping': section.dataset.mapping,
      'data-strict': section.dataset.strict,
      'data-reactions-enabled': section.dataset.reactionsEnabled,
      'data-emit-metadata': section.dataset.emitMetadata,
      'data-input-position': section.dataset.inputPosition,
      'data-theme': getTheme(section),
      'data-lang': section.dataset.lang,
      'data-loading': section.dataset.loading,
      crossorigin: 'anonymous',
      async: '',
    };
    if (section.dataset.term) attributes['data-term'] = section.dataset.term;

    let frameFound = false;
    let frameTimeout;
    const frameObserver = new MutationObserver(() => {
      const frame = section.querySelector('iframe.giscus-frame');
      if (!frame) return;
      frameFound = true;
      window.clearTimeout(frameTimeout);
      frame.addEventListener('load', () => {
        setTheme(section);
        setReady(section);
      }, { once: true });
      frameObserver.disconnect();
    });
    frameObserver.observe(container, { childList: true, subtree: true });

    const script = document.createElement('script');
    Object.entries(attributes).forEach(([name, value]) => script.setAttribute(name, value));
    script.addEventListener('load', () => {
      if (frameFound) return;
      frameTimeout = window.setTimeout(() => {
        if (!frameFound) setError(section);
      }, frameTimeoutMs);
    }, { once: true });
    script.addEventListener('error', () => {
      window.clearTimeout(frameTimeout);
      frameObserver.disconnect();
      setError(section);
    }, { once: true });
    section.dataset.loaded = 'true';
    container.appendChild(script);
  };

  sections.forEach(load);

  new MutationObserver(() => sections.forEach(setTheme)).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-bs-theme', 'data-td-preset'],
  });
  const handleColorScheme = () => sections.forEach(setTheme);
  if (colorScheme.addEventListener) {
    colorScheme.addEventListener('change', handleColorScheme);
  } else {
    colorScheme.addListener(handleColorScheme);
  }
})();
