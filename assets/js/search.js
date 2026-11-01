/*
Copyright 2018 Google LLC

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

(function () {
  'use strict';
  if (typeof window !== 'undefined' && window.OinkComparePane) return;

  var searchPage = '{{ "search/" | absURL }}';

  // Delegated so the handler also covers search inputs added after load.
  document.addEventListener('keypress', function (event) {
    if (event.key !== 'Enter') return;
    var input = event.target;
    if (!input || typeof input.matches !== 'function') return;
    if (!input.matches('.td-search input')) return;
    event.preventDefault();
    document.location = searchPage + '?q=' + encodeURIComponent(input.value);
  });
})();
