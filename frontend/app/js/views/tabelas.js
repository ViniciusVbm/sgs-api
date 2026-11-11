import { html, montar } from '../html.js';
import { chamar } from '../api.js';
import { ic } from '../ui/icone.js';
import { carregando, erro, vazio } from '../ui/estado.js';
import { abrirModal, fecharModal } from '../ui/modal.js';
import { toast } from '../ui/toast.js';
import { campo, lerFormulario, alterados, mostrarErros, limparErros } from '../ui/form.js';
import { carregarReferencia, limparReferencias } from '../referencias.js';

// Tabelas de referência (spec 012, R16.1; design § Tabelas de referência). Só o Gestor de Dados
// (regra_validacao:manage global) chega aqui; a API confere a permissão de novo em cada escrita.
// "Excluir" é desativar: as FKs para os tipos não têm cascata na exclusão, e a API não apaga
// referência. A troca do código de um tipo de equipamento chega aos equipamentos pela FK
// ON UPDATE CASCADE, e a tela confere o efeito nos próprios registros.

const TABELAS = {
  'tipos-unidade': { titulo: 'Tipos de unidade', singular: 'tipo de unidade', tabela: 'unit_types', editavel: true, area: true },
  'tipos-equipamento': { titulo: 'Tipos de equipamento', singular: 'tipo de equipamento', tabela: 'equipment_types', editavel: true },
  'tipos-servico': { titulo: 'Tipos de serviço', singular: 'tipo de serviço', tabela: 'service_types', editavel: true },
  distritos: { titulo: 'Distritos sanitários', singular: 'distrito', tabela: 'districts', editavel: false },
  'areas-tecnicas': { titulo: 'Áreas técnicas', singular: 'área técnica', tabela: 'technical_areas', editavel: false },
};

const ordenar = (itens) => [...itens].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));

export async function telaTabelas(alvo, consulta) {
  const tipo = TABELAS[consulta.get('tabela')] ? consulta.get('tabela') : 'tipos-unidade';
  const conf = TABELAS[tipo];
  document.title = `${conf.titulo} — SGS Recife`;
  montar(alvo, html`
    <div class="page-head"><div><h1>Tabelas de referência</h1>
      <p>Catálogos usados no cadastro. Inclua, corrija ou desative itens; o banco mantém a integridade das referências.</p></div>
      ${conf.editavel ? html`<button class="btn btn-primary" type="button" id="incluir">${ic('plus')}Incluir ${conf.singular}</button>` : ''}</div>
    <nav class="seg-tabs tabelas-sel" aria-label="Tabela">${Object.entries(TABELAS).map(([k, c]) => html`<a href="#/referencias?tabela=${k}" class="${k === tipo ? 'on' : ''}" ${k === tipo ? html`aria-current="page"` : ''} data-tabela="${k}">${c.titulo}</a>`)}</nav>
    ${conf.editavel
    ? html`<div class="banner info" data-ref="regra-exclusao">${ic('info')}<p><b>Excluir é desativar.</b> Unidades, equipamentos e serviços apontam para estes tipos por chave estrangeira sem exclusão em cascata; por isso um tipo não é apagado do banco, só desativado (e pode ser reativado). Um tipo inativo deixa de aparecer nos formulários.${tipo === 'tipos-equipamento' ? html` <b>Corrigir o código</b> de um tipo de equipamento atualiza todos os equipamentos dele pela chave estrangeira <code>ON UPDATE CASCADE</code>.` : ''}</p></div>`
    : html`<div class="banner info" data-ref="somente-leitura">${ic('lock')}<p><b>Somente leitura.</b> Esta é uma tabela de domínio fechado (${tipo === 'distritos' ? 'os 8 distritos sanitários do Recife' : 'as áreas técnicas da Secretaria'}); não se incluem nem se alteram itens pela interface.</p></div>`}
    <div id="cascata" aria-live="polite"></div>
    <section class="panel"><div id="lista"></div></section>`);

  const lista = document.getElementById('lista');
  let itens = [];
  let areas = new Map();

  const carregar = async () => {
    montar(lista, carregando());
    try {
      const pedidos = [chamar('GET', `/referencias/${encodeURIComponent(tipo)}`)];
      if (conf.area) pedidos.push(carregarReferencia('areas-tecnicas'));
      const [{ dados }, mapaDeAreas] = await Promise.all(pedidos);
      itens = ordenar(dados);
      if (mapaDeAreas) areas = mapaDeAreas;
    } catch (falha) {
      montar(lista, erro(falha));
      return;
    }
    const ativos = itens.filter((i) => i.ativo).length;
    montar(lista, html`<p class="list-meta"><span data-ref="contagem" data-total="${itens.length}">${itens.length} itens · ${ativos} ativos · ${itens.length - ativos} inativos</span><span class="muted">tabela <code>${conf.tabela}</code></span></p>
      ${itens.length ? html`<div class="tbl-wrap"><table><thead><tr><th>Código</th><th>Nome</th>${conf.area ? html`<th>Área técnica</th>` : ''}<th>Situação</th>${conf.editavel ? html`<th class="acoes">Ações</th>` : ''}</tr></thead>
        <tbody>${itens.map((r) => html`<tr data-item="${r.id}" data-codigo="${r.codigo}">
          <td><code>${r.codigo}</code></td><td>${r.nome}</td>
          ${conf.area ? html`<td>${areas.get(String(r.area_tecnica_id))?.nome || '—'}</td>` : ''}
          <td><span class="chip ${r.ativo ? 'ok' : ''}" data-ref="situacao">${r.ativo ? 'Ativo' : 'Inativo'}</span></td>
          ${conf.editavel ? html`<td class="acoes"><button class="btn btn-quiet btn-sm" type="button" data-editar="${r.id}">${ic('edit')}Editar</button>
            <button class="btn btn-line btn-sm" type="button" data-ativo="${r.id}">${r.ativo ? html`${ic('x')}Desativar` : html`${ic('refresh')}Reativar`}</button></td>` : ''}</tr>`)}</tbody></table></div>`
    : vazio('Nenhum item cadastrado.')}`);
    lista.querySelectorAll('[data-editar]').forEach((b) => b.addEventListener('click', () => abrirFormulario(itens.find((i) => String(i.id) === b.dataset.editar))));
    lista.querySelectorAll('[data-ativo]').forEach((b) => b.addEventListener('click', () => confirmarSituacao(itens.find((i) => String(i.id) === b.dataset.ativo))));
  };

  const depoisDeGravar = async (mensagem) => {
    fecharModal();
    limparReferencias(); // a lista e os filtros das outras telas não podem mostrar o nome antigo
    toast('ok', mensagem);
    await carregar();
  };

  const abrirFormulario = (original = null) => {
    const opcoesDeArea = [...areas.values()].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map((a) => ({ valor: a.id, rotulo: a.nome }));
    const caixa = abrirModal(html`<form id="fr" novalidate>
      <div class="modal-h"><h2>${original ? `Editar ${conf.singular}` : `Incluir ${conf.singular}`}</h2>
        <p>${original ? html`Item <code>${original.codigo}</code>. Só os campos alterados são enviados.` : 'O código é único na tabela.'}</p></div>
      <div class="modal-b"><div class="grid">
        ${campo({ nome: 'codigo', rotulo: 'Código', valor: original?.codigo, obrigatorio: true, max: 50, ajuda: 'Letras, números, hífen e sublinhado.' })}
        ${campo({ nome: 'nome', rotulo: 'Nome', valor: original?.nome, obrigatorio: true, max: 100 })}
        ${conf.area ? campo({ nome: 'area_tecnica_id', rotulo: 'Área técnica', valor: original?.area_tecnica_id, obrigatorio: true, opcoes: opcoesDeArea }) : ''}
      </div>${tipo === 'tipos-equipamento' && original ? html`<p class="hint" data-ref="aviso-cascata">Mudar o código atualiza, pela cascata da chave estrangeira, todos os equipamentos com o código <code>${original.codigo}</code>.</p>` : ''}
      <p class="fld-err" id="fr-geral" role="alert"></p></div>
      <div class="modal-f"><button class="btn btn-line" type="button" id="fr-cancelar">Cancelar</button>
        <button class="btn btn-primary" type="submit">${original ? 'Salvar alterações' : 'Incluir'}</button></div></form>`, { rotulo: original ? `Editar ${conf.singular}` : `Incluir ${conf.singular}` });
    const formulario = caixa.querySelector('#fr');
    caixa.querySelector('#fr-cancelar').addEventListener('click', fecharModal);
    formulario.addEventListener('submit', async (e) => {
      e.preventDefault();
      limparErros(formulario);
      const geral = caixa.querySelector('#fr-geral');
      geral.textContent = '';
      const dados = lerFormulario(formulario);
      const corpo = original ? alterados({ codigo: original.codigo, nome: original.nome, area_tecnica_id: original.area_tecnica_id }, dados) : { ...dados };
      if ('area_tecnica_id' in corpo) corpo.area_tecnica_id = corpo.area_tecnica_id === '' ? null : Number(corpo.area_tecnica_id);
      if (!conf.area) delete corpo.area_tecnica_id;
      if (original && !Object.keys(corpo).length) { fecharModal(); toast('ok', 'Nada a alterar.'); return; }
      const botao = formulario.querySelector('button[type=submit]');
      botao.disabled = true;
      try {
        if (original) await chamar('PATCH', `/referencias/${encodeURIComponent(tipo)}/${encodeURIComponent(original.id)}`, { corpo });
        else await chamar('POST', `/referencias/${encodeURIComponent(tipo)}`, { corpo });
      } catch (falha) {
        botao.disabled = false;
        if (!mostrarErros(formulario, falha, 'codigo')) geral.textContent = falha.status === 403 ? 'Você não tem permissão para esta ação.' : falha.detail;
        return;
      }
      if (original && tipo === 'tipos-equipamento' && 'codigo' in corpo) {
        await depoisDeGravar('Código alterado.');
        await mostrarCascata(original, corpo.codigo);
        return;
      }
      await depoisDeGravar(original ? 'Alterações salvas.' : `${conf.singular[0].toUpperCase()}${conf.singular.slice(1)} incluído.`);
    });
  };

  const confirmarSituacao = (item) => {
    const desativar = item.ativo;
    const caixa = abrirModal(html`<div class="modal-h"><h2>${desativar ? 'Desativar' : 'Reativar'} ${conf.singular}</h2>
        <p><code>${item.codigo}</code> · ${item.nome}</p></div>
      <div class="modal-b"><p>${desativar
    ? 'O item continua no banco e nos registros que já o usam, mas deixa de aparecer nos formulários. A desativação pode ser desfeita.'
    : 'O item volta a aparecer nos formulários.'}</p><p class="fld-err" id="sit-erro" role="alert"></p></div>
      <div class="modal-f"><button class="btn btn-line" type="button" id="sit-cancelar">Cancelar</button>
        <button class="btn ${desativar ? 'btn-danger' : 'btn-primary'}" type="button" id="sit-confirmar">${desativar ? 'Desativar' : 'Reativar'}</button></div>`,
    { rotulo: `${desativar ? 'Desativar' : 'Reativar'} ${conf.singular}` });
    caixa.querySelector('#sit-cancelar').addEventListener('click', fecharModal);
    caixa.querySelector('#sit-confirmar').addEventListener('click', async (e) => {
      e.currentTarget.disabled = true;
      try {
        await chamar('PATCH', `/referencias/${encodeURIComponent(tipo)}/${encodeURIComponent(item.id)}`, { corpo: { ativo: !desativar } });
      } catch (falha) {
        caixa.querySelector('#sit-erro').textContent = falha.status === 403 ? 'Você não tem permissão para esta ação.' : falha.detail;
        return;
      }
      await depoisDeGravar(desativar ? 'Item desativado.' : 'Item reativado.');
    });
  };

  // Efeito do ON UPDATE CASCADE: o número da auditoria (equipamentos com o código antigo, contado
  // antes da troca) e a conferência nos registros, que já devem ter o código novo.
  const mostrarCascata = async (original, novo) => {
    const destino = document.getElementById('cascata');
    montar(destino, carregando('Conferindo os equipamentos afetados…'));
    const entidade = encodeURIComponent(`tipos-equipamento:${original.id}`);
    try {
      const [{ dados: eventos }, { dados: emUnidades }, { dados: soltos }] = await Promise.all([
        chamar('GET', `/auditoria/eventos?entidade_tipo=referencia&entidade_id=${entidade}&acao=referencia.atualizada&tamanho=1`),
        chamar('GET', '/dashboard/consultas/equipamentos-por-tipo-e-distrito'),
        chamar('GET', '/equipamentos'),
      ]);
      const afetados = eventos.itens[0]?.metadados?.equipamentos_afetados;
      const soma = (lista, chave, codigo, campoDaSoma) => lista.filter((l) => l[chave] === codigo).reduce((s, l) => s + (campoDaSoma ? l[campoDaSoma] : 1), 0);
      const novosEmUnidades = soma(emUnidades, 'equipment_type_code', novo, 'equipment_count');
      const novosSoltos = soma(soltos, 'tipo_codigo', novo);
      const antigos = soma(emUnidades, 'equipment_type_code', original.codigo, 'equipment_count') + soma(soltos, 'tipo_codigo', original.codigo);
      const confere = afetados === novosEmUnidades + novosSoltos && antigos === 0;
      montar(destino, html`<div class="banner ${confere ? 'ok' : 'wait'}" data-ref="resultado-cascata" data-afetados="${afetados ?? ''}" data-em-unidades="${novosEmUnidades}" data-soltos="${novosSoltos}" data-antigos="${antigos}" data-confere="${confere}">
        ${ic(confere ? 'check' : 'alert')}<p><b>ON UPDATE CASCADE: ${afetados ?? '?'} equipamentos afetados</b> pela troca de <code>${original.codigo}</code> para <code>${novo}</code> (número registrado na auditoria, evento <code>referencia.atualizada</code>).<br>
        Conferência nos registros: ${novosEmUnidades} em unidades + ${novosSoltos} sem unidade já têm o código <code>${novo}</code>; ${antigos} ainda com <code>${original.codigo}</code>.${confere ? '' : ' Os números não batem; confira o histórico.'}</p></div>`);
    } catch (falha) {
      montar(destino, html`<div data-ref="resultado-cascata">${erro(falha)}</div>`);
    }
  };

  if (conf.editavel) document.getElementById('incluir').addEventListener('click', () => abrirFormulario());
  await carregar();
}
