import { montar } from '../html.js';
import { ic } from './icone.js';

// O tema é o único dado guardado no navegador (spec 012, R15.3).
const CHAVE = 'sgs-theme';

export function temaAtual() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

export function aplicarTema(tema) {
  document.documentElement.setAttribute('data-theme', tema);
  try { localStorage.setItem(CHAVE, tema); } catch { /* armazenamento indisponível */ }
  const botao = document.getElementById('themeBtn');
  if (botao) {
    montar(botao, ic(tema === 'dark' ? 'sun' : 'moon'));
    botao.title = tema === 'dark' ? 'Usar tema claro' : 'Usar tema escuro';
    botao.setAttribute('aria-label', botao.title);
  }
}

export function iniciarTema() {
  let tema = 'light';
  try { tema = localStorage.getItem(CHAVE) === 'dark' ? 'dark' : 'light'; } catch { /* idem */ }
  document.documentElement.setAttribute('data-theme', tema);
}

export const alternarTema = () => aplicarTema(temaAtual() === 'dark' ? 'light' : 'dark');
