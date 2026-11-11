import { html } from '../html.js';

// Campos de formulário com rótulo, ajuda e erro, e o envio só do que mudou (spec 012, T24;
// reaproveitado pela T10, T25 e T9). Os nomes dos campos são os da API, para que os erros
// 422 (`errors[{campo, mensagem}]`) caiam no campo certo (R7.2, R16.1).

// `opcoes`: lista de {valor, rotulo}; com ela o campo vira <select>.
export function campo({ nome, rotulo, valor = '', tipo = 'text', obrigatorio = false, max = null, opcoes = null, ajuda = '', vazio = 'Selecione…' }) {
  const id = `fld-${nome}`;
  const atual = valor === null || valor === undefined ? '' : String(valor);
  const controle = opcoes
    ? html`<select id="${id}" name="${nome}" ${obrigatorio ? html`required aria-required="true"` : ''} aria-describedby="${id}-err">
        <option value="">${vazio}</option>${opcoes.map((o) => html`<option value="${o.valor}" ${String(o.valor) === atual ? html`selected` : ''}>${o.rotulo}</option>`)}</select>`
    : html`<input id="${id}" name="${nome}" type="${tipo}" value="${atual}" ${max ? html`maxlength="${max}"` : ''} ${obrigatorio ? html`aria-required="true"` : ''} aria-describedby="${id}-err" autocomplete="off">`;
  return html`<div class="fld" data-campo="${nome}">
    <label for="${id}">${rotulo}${obrigatorio ? '' : html` <span class="opt">(opcional)</span>`}</label>
    ${controle}${ajuda ? html`<p class="hint">${ajuda}</p>` : ''}
    <p class="fld-err" id="${id}-err" role="alert"></p></div>`;
}

// Valores dos campos com `name`, sem espaços nas pontas.
export function lerFormulario(formulario) {
  const dados = {};
  formulario.querySelectorAll('[name]').forEach((el) => { dados[el.name] = String(el.value).trim(); });
  return dados;
}

// Só os campos cujo valor mudou em relação ao original (o PATCH não reenvia o resto).
export function alterados(original, atual) {
  const saida = {};
  for (const [chave, valor] of Object.entries(atual)) {
    const antes = original[chave] === null || original[chave] === undefined ? '' : String(original[chave]);
    if (valor !== antes) saida[chave] = valor;
  }
  return saida;
}

export function limparErros(formulario) {
  formulario.querySelectorAll('.fld.bad').forEach((f) => f.classList.remove('bad'));
  formulario.querySelectorAll('.fld-err').forEach((p) => { p.textContent = ''; });
}

export function marcarErro(formulario, nome, mensagem) {
  const caixa = formulario.querySelector(`[data-campo="${CSS.escape(nome)}"]`);
  if (!caixa) return false;
  caixa.classList.add('bad');
  caixa.querySelector('.fld-err').textContent = mensagem; // textContent: sem HTML
  return true;
}

// Erros da API nos campos: 422 (`errors`) e 409 de código repetido. Devolve se algum campo
// recebeu a mensagem; se nenhum, quem chamou mostra o `detail` geral.
export function mostrarErros(formulario, falha, campoDoConflito = null) {
  limparErros(formulario);
  let algum = false;
  for (const e of falha.errors || []) algum = marcarErro(formulario, e.campo, e.mensagem) || algum;
  if (!algum && falha.status === 409 && campoDoConflito) algum = marcarErro(formulario, campoDoConflito, falha.detail);
  const primeiro = formulario.querySelector('.fld.bad input, .fld.bad select');
  if (primeiro) primeiro.focus();
  return algum;
}
