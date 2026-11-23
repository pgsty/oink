/*
 * Copyright 2018 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

(function() {

    'use strict';

    function initHeaderScroll() {
        const header = document.querySelector('.td-site-header');
        if (!header) return;

        const update = function() {
            header.classList.toggle('td-scrolled', window.pageYOffset > 60);
        };

        window.addEventListener('scroll', update, {passive: true});
        update();
    }

    // Reading containers can acquire focus from a click. A later unrelated
    // key must not turn that click into an article-sized focus decoration.
    // Tab and a new programmatic focus keep their normal keyboard indication.
    function initReadingFocus() {
        const selector = '#td-main-content, .td-table-scroll[tabindex], pre[tabindex]';
        let pointerTarget = null;
        function isContainer(el) {
            return el && typeof el.matches === 'function' && el.matches(selector);
        }
        document.addEventListener('pointerdown', function(event) {
            pointerTarget = event.target;
            const active = document.activeElement;
            if (isContainer(active) && active.contains(pointerTarget)) {
                active.setAttribute('data-td-pointer-focus', '');
            }
        }, true);
        document.addEventListener('pointerup', function() {
            pointerTarget = null;
        }, true);
        document.addEventListener('pointercancel', function() { pointerTarget = null; }, true);
        document.addEventListener('focusin', function(event) {
            if (isContainer(event.target)) {
                if (pointerTarget && event.target.contains(pointerTarget)) {
                    event.target.setAttribute('data-td-pointer-focus', '');
                } else event.target.removeAttribute('data-td-pointer-focus');
            }
            pointerTarget = null;
        }, true);
        document.addEventListener('focusout', function(event) {
            if (isContainer(event.target)) event.target.removeAttribute('data-td-pointer-focus');
        }, true);
        document.addEventListener('keydown', function(event) {
            pointerTarget = null;
            if (event.key === 'Tab' && isContainer(document.activeElement)) {
                document.activeElement.removeAttribute('data-td-pointer-focus');
            }
        }, true);
    }

    function initHoverMenu(menu, trigger, surfaceName) {
        if (!trigger) return;
        menu.setAttribute('data-td-menu-ready', '');
        let closeTimer = 0;
        let activatedOpen = false;
        // A floating list closes on the press: iOS sends no click for a tap
        // on plain content. The phone drawer's list sits in the flow, so it
        // waits for the click and the row under the finger stays in place.
        const inFlow = Boolean(menu.closest('.td-site-drawer'));
        const outsidePress = inFlow ? 'click' : 'pointerdown';

        function dismissOutside(event) {
            if (!menu.contains(event.target)) close();
        }

        function dismissOnEscape(event) {
            if (event.key !== 'Escape' || event.defaultPrevented) return;
            event.preventDefault();
            event.stopPropagation();
            if (document.activeElement === document.body || menu.contains(document.activeElement)) {
                trigger.focus({preventScroll: true});
            }
            close();
        }

        function open() {
            window.clearTimeout(closeTimer);
            if (menu.classList.contains('td-is-open')) return;
            if (window.OinkSurfaceCoordinator) {
                const keep = menu.closest('#td-shell-sidebar') ? ['drawer']
                    : menu.closest('[data-td-landing-menu]') ? ['mobile-menu'] : [];
                window.OinkSurfaceCoordinator.closeOthers(surfaceName, keep);
            }
            menu.classList.add('td-is-open');
            trigger.setAttribute('aria-expanded', 'true');
            document.addEventListener(outsidePress, dismissOutside, true);
            document.addEventListener('keydown', dismissOnEscape, true);
        }

        function close() {
            window.clearTimeout(closeTimer);
            menu.classList.remove('td-is-open');
            trigger.setAttribute('aria-expanded', 'false');
            activatedOpen = false;
            document.removeEventListener(outsidePress, dismissOutside, true);
            document.removeEventListener('keydown', dismissOnEscape, true);
        }

        function closeSoon() {
            window.clearTimeout(closeTimer);
            closeTimer = window.setTimeout(close, 140);
        }

        if (window.OinkSurfaceCoordinator) window.OinkSurfaceCoordinator.register(surfaceName, close);
        menu.addEventListener('pointerenter', function(event) {
            if (event.pointerType !== 'touch') open();
        });
        menu.addEventListener('pointerleave', function(event) {
            if (event.pointerType !== 'touch') closeSoon();
        });
        menu.addEventListener('focusin', open);
        menu.addEventListener('focusout', function(event) {
            if (!menu.contains(event.relatedTarget)) closeSoon();
        });
        if (!trigger.hasAttribute('data-td-nav-hover-open')) return;
        trigger.addEventListener('click', function() {
            if (activatedOpen) {
                close();
            } else {
                open();
                activatedOpen = true;
                if (inFlow) menu.scrollIntoView({block: 'nearest', inline: 'nearest'});
            }
        });
        menu.addEventListener('keydown', function(event) {
            if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
            const links = Array.from(menu.querySelectorAll('a[href]'));
            if (!links.length) return;
            event.preventDefault();
            open();
            const index = links.indexOf(document.activeElement);
            const next = event.key === 'ArrowDown' ? Math.min(index + 1, links.length - 1)
                : index < 0 ? links.length - 1 : Math.max(index - 1, 0);
            links[next].focus();
        });
    }

    initReadingFocus();
    if (!window.OinkComparePane) {
        initHeaderScroll();
        document.querySelectorAll('.td-language-selector--menu').forEach(function(menu, index) {
            initHoverMenu(menu, menu.querySelector('.td-language-selector__trigger'), 'language-menu-' + index);
        });
        document.querySelectorAll('[data-td-nav-hover]').forEach(function(menu, index) {
            initHoverMenu(menu, menu.querySelector('[data-td-nav-hover-trigger], .td-nav-util'), 'theme-menu-' + index);
        });
    }

}());
