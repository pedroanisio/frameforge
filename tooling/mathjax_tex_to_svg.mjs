#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { mathjax } from '../viewer/node_modules/mathjax-full/js/mathjax.js';
import { TeX } from '../viewer/node_modules/mathjax-full/js/input/tex.js';
import { MathML } from '../viewer/node_modules/mathjax-full/js/input/mathml.js';
import { SVG } from '../viewer/node_modules/mathjax-full/js/output/svg.js';
import { liteAdaptor } from '../viewer/node_modules/mathjax-full/js/adaptors/liteAdaptor.js';
import { RegisterHTMLHandler } from '../viewer/node_modules/mathjax-full/js/handlers/html.js';
import { AllPackages } from '../viewer/node_modules/mathjax-full/js/input/tex/AllPackages.js';

const EX_TO_PX = 8;

function unitToPx(value, fallback) {
  const match = String(value || '').trim().match(/^([0-9.]+)([a-z%]*)$/i);
  if (!match) return fallback;
  const amount = Number.parseFloat(match[1]);
  if (!Number.isFinite(amount)) return fallback;
  const unit = match[2].toLowerCase();
  if (unit === 'ex') return amount * EX_TO_PX;
  if (unit === 'em') return amount * EX_TO_PX * 2;
  if (unit === 'px' || unit === '') return amount;
  return fallback;
}

function convertAll(expressions) {
  const adaptor = liteAdaptor();
  RegisterHTMLHandler(adaptor);
  const tex = new TeX({ packages: AllPackages });
  const mathml = new MathML();
  const svg = new SVG({ fontCache: 'none' });
  const documents = {
    tex: mathjax.document('', { InputJax: tex, OutputJax: svg }),
    mathml: mathjax.document('', { InputJax: mathml, OutputJax: svg }),
  };

  return expressions.map((expr) => {
    const item = typeof expr === 'object' && expr !== null
      ? expr
      : { input: 'tex', source: expr };
    const input = item.input === 'mathml' ? 'mathml' : 'tex';
    const source = String(item.source ?? item.tex ?? item.mathml ?? '');
    const node = documents[input].convert(source, { display: true });
    const outer = adaptor.outerHTML(node);
    const svgMatch = outer.match(/<svg\b([^>]*)>([\s\S]*)<\/svg>/);
    if (!svgMatch) {
      throw new Error(`MathJax did not return SVG for ${input} input`);
    }
    const attrs = svgMatch[1];
    const viewBox = (attrs.match(/\bviewBox="([^"]+)"/) || [])[1];
    const widthAttr = (attrs.match(/\bwidth="([^"]+)"/) || [])[1];
    const heightAttr = (attrs.match(/\bheight="([^"]+)"/) || [])[1];
    const vb = (viewBox || '').split(/\s+/).map(Number);
    const width = unitToPx(widthAttr, Number.isFinite(vb[2]) ? vb[2] / 50 : 120);
    const height = unitToPx(heightAttr, Number.isFinite(vb[3]) ? vb[3] / 50 : 24);

    return {
      input,
      source,
      viewBox,
      width,
      height,
      body: svgMatch[2],
    };
  });
}

try {
  const input = JSON.parse(readFileSync(0, 'utf8') || '[]');
  const expressions = Array.isArray(input) ? input : [input];
  process.stdout.write(JSON.stringify(convertAll(expressions)));
} catch (error) {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
}
