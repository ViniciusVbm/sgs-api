// Escape de HTML (spec 012, R15.1 e R15.4). Toda interpolação em `html` é escapada,
// salvo o que vier de `raw()`, reservado ao HTML gerado pelo próprio código.

const MAPA = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => MAPA[c]);

class Confiavel {
  constructor(texto) { this.texto = texto; }
  toString() { return this.texto; }
}

export const raw = (texto) => new Confiavel(String(texto));

const valor = (v) => {
  if (v instanceof Confiavel) return v.texto;
  if (Array.isArray(v)) return v.map(valor).join('');
  if (v === false || v === null || v === undefined) return '';
  return esc(v);
};

export const html = (partes, ...valores) =>
  new Confiavel(partes.reduce((acc, p, i) => acc + p + (i < valores.length ? valor(valores[i]) : ''), ''));

// Único ponto que escreve innerHTML: recusa texto que não passou por `html`/`raw`.
export function montar(elemento, conteudo) {
  if (!(conteudo instanceof Confiavel)) throw new TypeError('HTML sem escape');
  elemento.innerHTML = conteudo.texto;
}
