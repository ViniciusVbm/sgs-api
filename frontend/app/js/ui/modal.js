import { montar } from '../html.js';

// Modal com foco preso e devolvido ao fechar (spec 012, R1.5).
let focoAnterior = null;

const focaveis = (raiz) => [...raiz.querySelectorAll(
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
)];

export function fecharModal() {
  const scrim = document.getElementById('scrim');
  if (!scrim) return;
  scrim.remove();
  if (focoAnterior && typeof focoAnterior.focus === 'function') focoAnterior.focus();
  focoAnterior = null;
}

export function abrirModal(conteudo, { rotulo = 'Diálogo' } = {}) {
  fecharModal();
  focoAnterior = document.activeElement;
  const scrim = document.createElement('div');
  scrim.className = 'scrim';
  scrim.id = 'scrim';
  const caixa = document.createElement('div');
  caixa.className = 'modal';
  caixa.setAttribute('role', 'dialog');
  caixa.setAttribute('aria-modal', 'true');
  caixa.setAttribute('aria-label', rotulo);
  montar(caixa, conteudo);
  scrim.appendChild(caixa);
  scrim.addEventListener('mousedown', (e) => { if (e.target === scrim) fecharModal(); });
  scrim.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.preventDefault(); fecharModal(); return; }
    if (e.key !== 'Tab') return;
    const lista = focaveis(caixa);
    if (!lista.length) return;
    const primeiro = lista[0];
    const ultimo = lista[lista.length - 1];
    if (e.shiftKey && document.activeElement === primeiro) { e.preventDefault(); ultimo.focus(); }
    else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primeiro.focus(); }
  });
  document.body.appendChild(scrim);
  (focaveis(caixa)[0] || caixa).focus();
  return caixa;
}
