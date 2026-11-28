/*!
 * This is a Docsy-adapted version of https://github.com/twbs/examples/blob/main/color-modes/js/color-modes.js.
 *
 * Original header:
 *
 * Color mode toggler for Bootstrap's docs (https://getbootstrap.com/)
 * Copyright 2011-2024 The Bootstrap Authors
 * Licensed under the Creative Commons Attribution 3.0 Unported License.
 */

(() => {
  'use strict'

  const themeKey = 'td-color-theme'
  const valid = theme => ['auto', 'light', 'dark'].includes(theme)
  const getStoredTheme = () => {
    try {
      const value = localStorage.getItem(themeKey)
      if (value !== null && !valid(value)) localStorage.removeItem(themeKey)
      return valid(value) ? value : 'auto'
    } catch (_) {
      return 'auto'
    }
  }
  // Keep the in-page preference even if storage is blocked.
  let preference = getStoredTheme()
  const setStoredTheme = theme => {
    let saved = true
    try {
      localStorage.setItem(themeKey, theme)
    } catch (_) {
      saved = false
    }
    document.documentElement.toggleAttribute('data-td-mode-unsaved', !saved)
    document.querySelectorAll('[data-td-appearance-note]').forEach(note => {
      note.hidden = saved && !document.documentElement.hasAttribute('data-td-preset-unsaved')
    })
  }

  const getPreferredTheme = () => {
    return preference
  }

  // Vendored runtimes ship their own dark palettes but key them on their own
  // switch rather than on `data-bs-theme`: Swagger UI on `html.dark-mode` and
  // Algolia DocSearch on `html[data-theme='dark']`, which is where DocSearch
  // redefines its whole `--docsearch-*` token set. Mirroring the resolved
  // theme onto both is what makes those palettes reachable at all; the names
  // are the runtimes' API, in the same family as asciinema's `--term-*`
  // properties. Neither runtime is loaded on a page that does not use it.
  const mirrorVendorTheme = theme => {
    const root = document.documentElement
    root.classList.toggle('dark-mode', theme === 'dark')
    root.setAttribute('data-theme', theme)
  }

  const setTheme = theme => {
    const resolved = theme === 'auto'
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : theme
    document.documentElement.setAttribute('data-td-color-mode', preference)
    document.documentElement.setAttribute('data-bs-theme', resolved)
    mirrorVendorTheme(resolved)
    document.querySelectorAll('meta[name="theme-color"]').forEach(meta => {
      const color = meta.getAttribute('data-td-canvas-' + resolved)
      if (color) meta.setAttribute('content', color)
    })
    try {
      window.dispatchEvent(new CustomEvent('td-theme-change', {
        detail: { theme: document.documentElement.getAttribute('data-bs-theme') },
      }))
    } catch (_) {
      // The attribute remains the source of truth; observers still update.
    }
  }

  const syncDirectThemeButtons = () => {
    const dark = document.documentElement.getAttribute('data-bs-theme') === 'dark'
    // The Appearance trigger's icon slot needs nothing here: it shows the
    // reader's choice through `data-td-color-mode`, which setTheme writes.
    document.querySelectorAll('[data-td-theme-toggle]').forEach(toggle => {
      toggle.setAttribute('aria-pressed', dark ? 'true' : 'false')
      const moon = toggle.querySelector('.td-shell-icon--moon')
      const sun = toggle.querySelector('.td-shell-icon--sun')
      if (moon) moon.toggleAttribute('hidden', !dark)
      if (sun) sun.toggleAttribute('hidden', dark)
      // Consumer legacy toggles can use a single glyph instead of paired
      // shell icons. Never rewrite the glyph of one of those paired icons.
      const icon = !moon && !sun && toggle.querySelector('i.fa-solid')
      if (icon) {
        icon.classList.toggle('fa-sun', !dark)
        icon.classList.toggle('fa-moon', dark)
      }
    })

    // The explicit auto/light/dark controls reflect the stored *preference*,
    // not the theme it currently resolves to: "auto" stays selected after the
    // system flips to dark.
    // The Appearance menu's Mode group uses native radios, whose checked
    // state is the selection; legacy button pickers keep aria-pressed.
    document.querySelectorAll('[data-bs-theme-value]').forEach(button => {
      const selected = button.getAttribute('data-bs-theme-value') === preference
      if (button.type === 'radio') {
        button.checked = selected
        return
      }
      button.setAttribute('aria-pressed', selected ? 'true' : 'false')
      button.classList.toggle('td-is-active', selected)
    })
  }

  try {
    setTheme(getPreferredTheme())
  } finally {
    // Never leave the transition-suppression attribute behind, even when a
    // browser API or consumer override throws during initialisation.
    document.documentElement.removeAttribute('data-td-theme-init')
  }

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (preference === 'auto') {
      setTheme(getPreferredTheme())
      syncDirectThemeButtons()
    }
  })

  const apply = theme => {
    if (!valid(theme)) return
    preference = theme
    if (theme === 'auto') {
      // Storing "auto" rather than clearing the key keeps the choice explicit,
      // and getPreferredTheme resolves it against the media query.
      setStoredTheme('auto')
    } else {
      setStoredTheme(theme)
    }
    setTheme(theme)
    syncDirectThemeButtons()
  }

  window.addEventListener('storage', event => {
    if (event.key !== themeKey && event.key !== null) return
    preference = getStoredTheme()
    setTheme(preference)
    syncDirectThemeButtons()
  })

  if (window.OinkActions && window.OinkActions.get('switch_theme')) {
    window.OinkActions.registerExecutor('switch_theme', context => {
      const value = context && context.value
      const theme = typeof value === 'string' ? value : value && value.value
      if (!['auto', 'light', 'dark'].includes(theme)) {
        return Promise.reject(new Error('Unsupported theme'))
      }
      apply(theme)
      return { theme }
    })
  }

  const initControls = () => {
    syncDirectThemeButtons()

    // A radio reports a choice through `change` (arrow keys included); a
    // button through `click`. Either way the same apply() runs.
    document.querySelectorAll('[data-bs-theme-value]')
      .forEach(button => {
        button.addEventListener(button.type === 'radio' ? 'change' : 'click', () => {
          apply(button.getAttribute('data-bs-theme-value'))
        })
      })

    document.querySelectorAll('[data-td-theme-toggle]')
      .forEach(toggle => {
        toggle.addEventListener('click', () => {
          apply(document.documentElement.getAttribute('data-bs-theme') === 'dark'
            ? 'light'
            : 'dark')
        })
      })
  }

  if (!document.readyState || document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', initControls)
  } else {
    initControls()
  }
})()
