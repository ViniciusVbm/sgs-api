import { html, montar } from '../html.js';
import { chamar } from '../api.js';
import { ic } from '../ui/icone.js';
import { carregando, erro } from '../ui/estado.js';
import { toast } from '../ui/toast.js';
import { limparErros, mostrarErros } from '../ui/form.js';
import { carregarReferencia } from '../referencias.js';
import { camposDaUnidade, lerUnidade, conferirObrigatorios, marcarCamposEstruturais } from '../formUnidade.js';

// Cadastro de unidade pelo escopo global de unidade:create (spec 012, T9: R7.3, R7.2).
// POST /unidades; a API valida formatos, unicidade (409 com a unidade existente) e o escopo.
// Gravada, a ficha nova abre na aba de serviços.

export async function telaNovaUnidade(alvo) {
  document.title = 'Cadastrar unidade — SGS Recife';
  montar(alvo, carregando());
  let tipos; let distritos;
  try {
    [tipos, distritos] = await Promise.all(['tipos-unidade', 'distritos'].map(carregarReferencia));
  } catch (falha) {
    montar(alvo, erro(falha));
    return;
  }
  montar(alvo, html`
    <a class="crumb" href="#/unidades">${ic('back')}Unidades</a>
    <div class="page-head"><div><h1>Cadastrar unidade</h1>
      <p>Os campos marcados como opcionais podem ficar em branco. A unidade nasce na versão 1.</p></div></div>
    <section class="panel"><form id="fn" novalidate class="panel-b">
      ${camposDaUnidade(null, { tipos, distritos })}
      <div class="err-summary" id="fn-geral" role="alert" hidden></div>
      <div class="form-actions"><a class="btn btn-line" href="#/unidades">Cancelar</a>
        <button class="btn btn-primary" type="submit">${ic('plus')}Cadastrar unidade</button></div>
    </form></section>`);
  const form = document.getElementById('fn');
  const geral = document.getElementById('fn-geral');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    limparErros(form);
    geral.hidden = true;
    const dados = lerUnidade(form);
    if (!conferirObrigatorios(form, dados)) return;
    const botao = form.querySelector('button[type=submit]');
    botao.disabled = true;
    let criada;
    try {
      ({ dados: criada } = await chamar('POST', '/unidades', { corpo: dados }));
    } catch (falha) {
      botao.disabled = false;
      const nosCampos = mostrarErros(form, falha) || marcarCamposEstruturais(form, falha);
      const existente = falha.status === 409 && falha.problema ? falha.problema.unidade_existente_id : null;
      if (!nosCampos || existente) {
        geral.hidden = false;
        montar(geral, html`<b>${ic('alert')}${falha.status === 403 ? 'Você não tem permissão para cadastrar esta unidade.' : falha.detail}</b>
          ${existente ? html`<p><a href="#/unidade/${encodeURIComponent(existente)}" data-ref="unidade-existente">Abrir a unidade que já existe</a></p>` : ''}`);
      }
      return;
    }
    toast('ok', 'Unidade cadastrada.', 'Inclua os serviços da unidade.');
    location.hash = `#/unidade/${encodeURIComponent(criada.id)}/servicos`;
  });
}
