{{ with .Site.Params.plantuml }}
{{ if and (reflect.IsMap .) (partial "config-enabled.html" (dict "value" . "key" "params.plantuml")) }}
(function () {
    'use strict';

    function encode6bit(value) {
        if (value < 10) return String.fromCharCode(48 + value);
        value -= 10;
        if (value < 26) return String.fromCharCode(65 + value);
        value -= 26;
        if (value < 26) return String.fromCharCode(97 + value);
        value -= 26;
        if (value === 0) return '-';
        if (value === 1) return '_';
        return '?';
    }

    function append3bytes(b1, b2, b3) {
        const c1 = b1 >> 2;
        const c2 = ((b1 & 0x3) << 4) | (b2 >> 4);
        const c3 = ((b2 & 0xf) << 2) | (b3 >> 6);
        const c4 = b3 & 0x3f;
        return encode6bit(c1 & 0x3f) + encode6bit(c2 & 0x3f)
            + encode6bit(c3 & 0x3f) + encode6bit(c4 & 0x3f);
    }

    function encode64(data) {
        let result = '';
        for (let i = 0; i < data.length; i += 3) {
            if (i + 2 === data.length) {
                result += append3bytes(data[i], data[i + 1], 0);
            } else if (i + 1 === data.length) {
                result += append3bytes(data[i], 0, 0);
            } else {
                result += append3bytes(data[i], data[i + 1], data[i + 2]);
            }
        }
        return result;
    }

    const imageURL = {{ .svg_image_url | jsonify | safeJS }};
    Array.prototype.forEach.call(
        document.querySelectorAll('.language-plantuml'),
        function (code) {
            const pre = code.parentNode;
            if (!pre || !pre.parentNode) return;
            const source = new TextEncoder().encode(pre.textContent);
            const encoded = encode64(pako.deflateRaw(source, { level: 9 }));
            {{ if .svg }}
            // Matches the element the vendored SVG loader looks for.
            const rendered = document.createElement('svg');
            rendered.setAttribute('data-src', imageURL + encoded);
            {{ else }}
            const rendered = document.createElement('img');
            rendered.setAttribute('src', imageURL + encoded);
            rendered.setAttribute('alt', 'PlantUML diagram');
            {{ end }}
            pre.parentNode.replaceChild(rendered, pre);
        },
    );
})();
{{ end }}
{{ end }}
