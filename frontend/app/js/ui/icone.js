import { esc, raw } from '../html.js';

// Ícone do sprite local (assets/icons.svg), como `ic()` do protótipo.
export const ic = (nome, cls = '') =>
  raw(`<svg class="icon ${esc(cls)}" aria-hidden="true"><use href="/assets/icons.svg#i-${esc(nome)}"/></svg>`);
