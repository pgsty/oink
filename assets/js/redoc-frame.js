import { init } from {{ .engine | jsonify | safeJS }};

// The shortcode validates the authored URL. Validate again because the local
// frame is directly addressable, restrict cross-origin specs to same-origin
// authored embeds, and never enable upstream's default telemetry.
function allowsSpec(url, rawSpec) {
  if (url.origin === location.origin) return true;
  try {
    const frame = window.frameElement;
    if (!frame || !frame.classList?.contains('td-redoc__frame')) return false;
    const authored = new URL(frame.getAttribute('src') || '', frame.ownerDocument.baseURI);
    return authored.searchParams.get('spec') === rawSpec;
  } catch (_) {
    return false;
  }
}

const spec = new URLSearchParams(location.search).get('spec');
if (spec) {
  try {
    const url = new URL(spec, location.href);
    if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password && allowsSpec(url, spec)) {
      init(url.href, { disableTelemetry: true, sanitize: true, router: 'hash' }, document.getElementById('api'));
    }
  } catch (error) {
    console.error('ReDoc:', error);
  }
}
