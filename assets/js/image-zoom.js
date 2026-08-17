/* OINK image zoom: progressive enhancement around one native dialog. */
(() => {
  'use strict';

  const dialog = document.querySelector('[data-td-image-zoom-dialog]');
  if (
    !dialog ||
    typeof window.HTMLDialogElement === 'undefined' ||
    typeof dialog.showModal !== 'function'
  ) {
    return;
  }

  const dialogImage = dialog.querySelector('[data-td-image-zoom-image]');
  const dialogCaption = dialog.querySelector('[data-td-image-zoom-caption]');
  const closeButton = dialog.querySelector('[data-td-image-zoom-close]');
  if (!dialogImage || !dialogCaption || !closeButton) return;

  let origin = null;
  let backdropPressed = false;

  const directCaption = (image) => {
    const figure = image.closest('figure');
    if (!figure) return '';
    const caption = Array.from(figure.children).find(
      (child) => child.tagName === 'FIGCAPTION'
    );
    return caption?.textContent?.trim() || '';
  };

  const isEligible = (image) => {
    if (!(image instanceof HTMLImageElement)) return false;
    const ariaHidden = image.getAttribute('aria-hidden')?.trim().toLowerCase();
    const roles = image
      .getAttribute('role')
      ?.trim()
      .toLowerCase()
      .split(/\s+/);
    if (
      image.closest('a, button, [data-no-zoom]') ||
      ariaHidden === 'true' ||
      roles?.some((role) => role === 'presentation' || role === 'none') ||
      image.hasAttribute('data-td-image-zoom-ready')
    ) {
      return false;
    }

    const alt = image.getAttribute('alt');
    const source = image.dataset.zoomSrc?.trim() || image.currentSrc || image.src;
    if (!alt?.trim() || !source) return false;

    // The theme marks everything it renders itself, Gallery fence items
    // included; the structural checks below only cover images a site wrote as
    // raw HTML.
    if (image.hasAttribute('data-td-image-zoom')) return true;
    const parent = image.parentElement;
    if (!parent) return false;
    if (parent.tagName === 'FIGURE') return true;
    return (
      parent.tagName === 'P' &&
      parent.childElementCount === 1 &&
      !parent.textContent.trim()
    );
  };

  const open = (button, image) => {
    const alt = image.getAttribute('alt') || '';
    const source = image.dataset.zoomSrc?.trim() || image.currentSrc || image.src;
    const caption = directCaption(image);

    origin = button;
    dialogImage.src = source;
    dialogImage.alt = alt;
    dialogCaption.textContent = caption;
    dialogCaption.hidden = !caption;
    dialog.showModal();
    closeButton.focus({ preventScroll: true });
  };

  const openLabel = dialog.dataset.openLabel?.trim();
  if (!openLabel) return;
  const contentImages = [
    '#td-main-content .td-content img',
    '#td-main-content > img',
    '#td-main-content > p > img',
    '#td-main-content > figure > img',
  ].join(', ');
  document.querySelectorAll(contentImages).forEach((image) => {
    if (!isEligible(image)) return;

    const button = document.createElement('button');
    const action = document.createElement('span');
    button.type = 'button';
    button.className = 'td-image-zoom__trigger';
    button.setAttribute('aria-haspopup', 'dialog');
    action.className = 'visually-hidden';
    action.textContent = openLabel;
    image.setAttribute('data-td-image-zoom-ready', '');
    image.before(button);
    button.append(image);
    button.append(action);
    button.addEventListener('click', () => open(button, image));
  });

  closeButton.addEventListener('click', () => dialog.close());
  dialog.addEventListener('pointerdown', (event) => {
    backdropPressed = event.target === dialog;
  });
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog && backdropPressed) dialog.close();
    backdropPressed = false;
  });
  dialog.addEventListener('close', () => {
    // A queued close event can arrive after another trigger has reopened the dialog.
    if (dialog.open) return;
    dialogImage.removeAttribute('src');
    dialogImage.alt = '';
    dialogCaption.textContent = '';
    dialogCaption.hidden = true;
    const active = document.activeElement;
    const mayRestore =
      !active ||
      active === document.body ||
      active === document.documentElement ||
      active === dialog ||
      dialog.contains(active);
    if (origin?.isConnected && mayRestore) origin.focus({ preventScroll: true });
    origin = null;
  });
})();
