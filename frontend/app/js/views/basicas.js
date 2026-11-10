import { html, montar } from '../html.js';
import { ic } from '../ui/icone.js';
import { emDesenvolvimento } from '../ui/estado.js';

// Telas simples: sem acesso (R3.3), não encontrada, em desenvolvimento (R13.1) e em implantação.

const cabecalho = (titulo, subtitulo = '') =>
  html`<div class="page-head"><div><h1>${titulo}</h1>${subtitulo ? html`<p>${subtitulo}</p>` : ''}</div></div>`;

export function semAcesso(alvo) {
  document.title = 'Sem acesso — SGS Recife';
  montar(alvo, html`${cabecalho('Sem acesso')}
    <div class="empty" data-estado="sem-acesso">${ic('lock')}<b>Você não tem permissão para esta tela.</b>
    <span>As permissões vêm dos seus papéis. Se precisar de acesso, procure o Administrador de TI.</span></div>`);
}

export function naoEncontrada(alvo) {
  document.title = 'Página não encontrada — SGS Recife';
  montar(alvo, html`${cabecalho('Página não encontrada')}<div class="empty" data-estado="nao-encontrada"><b>O endereço não corresponde a nenhuma tela.</b></div>`);
}

export function telaEmDesenvolvimento(alvo, titulo, motivo) {
  document.title = `${titulo} — SGS Recife`;
  montar(alvo, html`${cabecalho(titulo)}${emDesenvolvimento(titulo, motivo)}`);
}

// Tela [M] cuja tarefa da spec 012 ainda não foi entregue: não simula dados.
export function telaEmImplantacao(alvo, titulo, tarefa) {
  document.title = `${titulo} — SGS Recife`;
  montar(alvo, html`${cabecalho(titulo)}<div class="empty" data-estado="em-implantacao"><b>Tela em implantação.</b>
    <span>Será entregue na tarefa ${tarefa} da spec 012. Nenhum dado é mostrado até lá.</span></div>`);
}
