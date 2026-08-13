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
        const header = document.querySelector('.landing-header');
        if (!header) return;

        const update = function() {
            header.classList.toggle('scrolled', window.pageYOffset > 60);
        };

        window.addEventListener('scroll', update, {passive: true});
        update();
    }

    function initLanguageMenus() {
        document.querySelectorAll('.td-language-selector--menu').forEach(function(menu, index) {
            const trigger = menu.querySelector('.td-language-selector__trigger');
            const surfaceName = 'language-menu-' + index;
            let closeTimer = 0;

            function open() {
                if (window.OinkSurfaceCoordinator) {
                    const keep = menu.closest('#td-shell-sidebar') ? ['drawer'] : [];
                    window.OinkSurfaceCoordinator.closeOthers(surfaceName, keep);
                }
                window.clearTimeout(closeTimer);
                menu.classList.add('is-open');
                if (trigger) trigger.setAttribute('aria-expanded', 'true');
            }
            if (window.OinkSurfaceCoordinator) {
                window.OinkSurfaceCoordinator.register(surfaceName, close);
            }

            function close() {
                menu.classList.remove('is-open');
                if (trigger) trigger.setAttribute('aria-expanded', 'false');
            }

            function closeSoon() {
                window.clearTimeout(closeTimer);
                closeTimer = window.setTimeout(close, 140);
            }

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
        });
    }

    function initVersionMenus() {
        document.querySelectorAll('[data-td-version-menu]').forEach(function(menu, index) {
            const trigger = menu.querySelector('[data-bs-toggle="dropdown"]');
            const surfaceName = 'version-menu-' + index;
            if (!trigger || !window.bootstrap || !bootstrap.Dropdown) return;
            const dropdown = bootstrap.Dropdown.getOrCreateInstance(trigger);

            menu.addEventListener('show.bs.dropdown', function() {
                if (window.OinkSurfaceCoordinator) {
                    const keep = menu.closest('#td-shell-sidebar') ? ['drawer'] : [];
                    window.OinkSurfaceCoordinator.closeOthers(surfaceName, keep);
                }
            });
            if (window.OinkSurfaceCoordinator) {
                window.OinkSurfaceCoordinator.register(surfaceName, function() {
                    dropdown.hide();
                });
            }
        });
    }

    // Hover popovers (theme, version): hover or focus reveals the options
    // while the trigger keeps its own click action (dark-mode.js binds the
    // theme toggle; the version trigger toggles the popover for touch).
    function initThemeMenus() {
        document.querySelectorAll('[data-td-nav-hover]').forEach(function(menu, index) {
            const trigger = menu.querySelector('.nav-util');
            const surfaceName = 'theme-menu-' + index;
            let closeTimer = 0;

            function open() {
                if (window.OinkSurfaceCoordinator) {
                    window.OinkSurfaceCoordinator.closeOthers(surfaceName);
                }
                window.clearTimeout(closeTimer);
                menu.classList.add('is-open');
                if (trigger) trigger.setAttribute('aria-expanded', 'true');
            }

            function close() {
                menu.classList.remove('is-open');
                if (trigger) trigger.setAttribute('aria-expanded', 'false');
            }

            function closeSoon() {
                window.clearTimeout(closeTimer);
                closeTimer = window.setTimeout(close, 140);
            }

            if (window.OinkSurfaceCoordinator) {
                window.OinkSurfaceCoordinator.register(surfaceName, close);
            }

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
            // Triggers without their own click action (the version menu)
            // toggle on tap, so touch reaches the options too.
            if (trigger && trigger.hasAttribute('data-td-nav-hover-open')) {
                trigger.addEventListener('click', function() {
                    if (menu.classList.contains('is-open')) close(); else open();
                });
            }
        });
    }

    initHeaderScroll();
    initLanguageMenus();
    initVersionMenus();
    initThemeMenus();

}());
