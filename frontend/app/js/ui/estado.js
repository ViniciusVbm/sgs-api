import { html } from '../html.js';
import { ic } from './icone.js';

// Estados de carregamento, vazio e erro (spec 012, R1.6).
export const carregando = (texto = 'Carregando…') =>
  html`<div class="empty" role="status" aria-busy="true" data-estado="carregando"><b>${texto}</b></div>`;

export const vazio = (titulo, detalhe = '') =>
  html`<div class="empty" data-estado="vazio"><b>${titulo}</b>${detalhe ? html`<span>${detalhe}</span>` : ''}</div>`;

export const erro = (falha) => {
  const status = falha && typeof falha.status === 'number' ? falha.status : 0;
  const detalhe = (falha && falha.detail) || 'Não foi possível concluir a operação.';
  const pedido = falha && falha.requestId ? `Código do pedido: ${falha.requestId}` : '';
  return html`<div class="err-summary" role="alert" data-estado="erro" data-status="${status}">
    <b>${ic('alert')}${detalhe}</b>${pedido ? html`<p>${pedido}</p>` : ''}</div>`;
};

// Indicação padrão de funcionalidade sem backend (spec 012, R13.1).
export const emDesenvolvimento = (titulo, motivo) =>
  html`<div class="banner info" data-estado="em-desenvolvimento">${ic('info')}
    <p><b>${titulo}: em desenvolvimento.</b> ${motivo}</p></div>`;
