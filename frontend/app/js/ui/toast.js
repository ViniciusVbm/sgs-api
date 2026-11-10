import { html, montar } from '../html.js';
import { ic } from './icone.js';

// Avisos curtos; o contêiner #toasts tem aria-live (spec 012, R1.5).
export function toast(tipo, titulo, mensagem = '') {
  const el = document.createElement('div');
  el.className = `toast ${tipo}`;
  el.setAttribute('role', tipo === 'err' ? 'alert' : 'status');
  const icone = tipo === 'err' ? 'alert' : tipo === 'wait' ? 'send' : 'check';
  montar(el, html`${ic(icone)}<div><b>${titulo}</b>${mensagem ? html`<span>${mensagem}</span>` : ''}</div>`);
  document.getElementById('toasts').appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity .3s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 300);
  }, 4600);
  return el;
}
