// Trusted offline converter. Input is math data, never an HTML document or code.
import {mathjax} from '@mathjax/src/js/mathjax.js';
import {TeX} from '@mathjax/src/js/input/tex.js';
import {SVG} from '@mathjax/src/js/output/svg.js';
import {liteAdaptor} from '@mathjax/src/js/adaptors/liteAdaptor.js';
import {RegisterHTMLHandler} from '@mathjax/src/js/handlers/html.js';
import {MathJaxNewcmFont} from '@mathjax/mathjax-newcm-font/js/svg.js';
import '@mathjax/src/js/util/asyncLoad/esm.js';
import '@mathjax/src/js/input/tex/base/BaseConfiguration.js';
import '@mathjax/src/js/input/tex/ams/AmsConfiguration.js';
import {readFileSync, writeFileSync} from 'node:fs';

const policy = JSON.parse(readFileSync(new URL('../../../backend/tldr_backend/study/rendering/math-policy.json', import.meta.url), 'utf8'));
function validate(tex) {
  if (typeof tex !== 'string' || !tex.trim() || tex.length > policy.max_length || /[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(tex)) throw new Error('Invalid equation');
  let depth = 0, rows = 0;
  for (let i = 0; i < tex.length; i++) {
    if (tex[i] === '\\') {
      const match = /^\\([A-Za-z]+|[\s\S])/.exec(tex.slice(i));
      if (!match || ![...policy.commands, ...policy.escaped].includes(match[1])) throw new Error('Unsupported command');
      if (match[1] === '\\') rows++;
      i += match[0].length - 1; continue;
    }
    if (tex[i] === '{') depth++;
    if (tex[i] === '}') depth--;
    if (depth < 0 || depth > policy.max_depth) throw new Error('Invalid braces');
  }
  if (depth || rows > policy.max_rows || (tex.match(/&/g) || []).length > 120) throw new Error('Invalid equation size');
  for (const match of tex.matchAll(/\\(?:begin|end)\s*\{([^{}]+)\}/g)) if (!policy.environments.includes(match[1])) throw new Error('Unsupported environment');
}

globalThis.fetch = () => { throw new Error('Network access is disabled for math conversion'); };
const adaptor = liteAdaptor({fontSize: 16});
RegisterHTMLHandler(adaptor);
const input = new TeX({packages: ['base', 'ams'], maxBuffer: 4096,
  formatError() { throw new Error('Invalid or unsupported math expression'); }});
const output = new SVG({fontCache: 'none', fontData: MathJaxNewcmFont});
const document = mathjax.document('', {InputJax: input, OutputJax: output});

try {
  // Paths are fixed by trusted Python code, never included in lesson JSON.
  let source = process.argv[2] ? readFileSync(process.argv[2], 'utf8') : '';
  if (!process.argv[2]) for await (const chunk of process.stdin) { source += chunk; if (source.length > 16384) throw new Error('Math request too large'); }
  if (source.length > 16384) throw new Error('Math request too large');
  const request = JSON.parse(source);
  if (!Array.isArray(request) || request.length > 6 || request.some(tex => typeof tex !== 'string' || tex.length > 600)) throw new Error('Invalid math request');
  const results = [];
  for (const tex of request) {
    validate(tex);
    const node = await document.convertPromise(tex, {display: true, em: 16, ex: 8, containerWidth: 1280});
    const svg = adaptor.tags(node, 'svg')[0];
    if (!svg) throw new Error('Math conversion did not produce SVG');
    results.push(adaptor.outerHTML(svg));
  }
  if (process.argv[3]) writeFileSync(process.argv[3], JSON.stringify(results));
  else process.stdout.write(JSON.stringify(results));
} catch {
  process.stderr.write('Local equation typesetting failed. Check the supported LaTeX syntax.\n');
  process.exitCode = 1;
}
