import { html, montar } from '../html.js';
import { chamar } from '../api.js';
import { ic } from '../ui/icone.js';
import { carregando, erro, vazio } from '../ui/estado.js';
import { carregarReferencia, ROTULO_DO_STATUS } from '../referencias.js';

// Lista de unidades: busca, filtros e ordenação da API, paginação e filtros na URL
// (spec 012, R5.1, R5.2; recorte do distrito por navegação, R3.5; exportação: R5.4 [C]).

const FILTROS = ['q', 'tipo', 'area', 'distrito', 'status', 'com_pendencias', 'ordem', 'pagina', 'tamanho'];
const TODOS = 'todos'; // distrito escolhido explicitamente como "todos" (o recorte é só navegação)

const opcoes = (mapa, atual, rotuloTodos) => html`<option value="">${rotuloTodos}</option>${[...mapa.values()]
  .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  .map((r) => html`<option value="${r.id}" ${String(r.id) === atual ? html`selected` : ''}>${r.nome}</option>`)}`;

const selecionado = (valor, atual) => (valor === atual ? html`selected` : '');

export async function telaUnidades(alvo, perfil, consulta) {
  document.title = 'Unidades — SGS Recife';
  // R3.5: o Técnico Distrital abre a lista no próprio DS; pode escolher "Todos os distritos".
  const recorte = perfil.recorte('distrito');
  if (recorte && ![...consulta.keys()].length) {
    location.replace(`#/unidades?distrito=${encodeURIComponent(recorte.escopo_id)}`);
    return;
  }
  const filtros = Object.fromEntries(FILTROS.map((f) => [f, consulta.get(f) || '']));
  montar(alvo, carregando());
  let distritos; let tipos; let areas;
  try {
    [distritos, tipos, areas] = await Promise.all(
      ['distritos', 'tipos-unidade', 'areas-tecnicas'].map(carregarReferencia),
    );
  } catch (falha) {
    montar(alvo, erro(falha));
    return;
  }
  const doDistrito = filtros.distrito && filtros.distrito !== TODOS ? distritos.get(filtros.distrito) : null;
  montar(alvo, html`
    <div class="page-head"><div><h1>${doDistrito && recorte && String(recorte.escopo_id) === filtros.distrito ? html`Unidades do ${doDistrito.nome}` : 'Unidades da rede'}</h1>
      <p>Encontre uma unidade pelo nome ou CNES. Clique na linha para abrir a ficha.</p></div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn btn-line" type="button" disabled aria-disabled="true" title="Exportar: em desenvolvimento (gerada pelo backend, DF10)" data-estado="em-desenvolvimento">${ic('download')}Exportar lista (em desenvolvimento)</button>
        ${perfil.global('unidade:create') ? html`<a class="btn btn-primary" href="#/nova">${ic('plus')}Cadastrar unidade</a>` : ''}
      </div></div>
    <section class="panel">
      <form class="filters" id="filters" role="search">
        <div class="fld grow"><label for="q">Buscar</label><input id="q" type="search" maxlength="100" placeholder="Ex.: CAPS ou 2427370" value="${filtros.q}"></div>
        <div class="fld"><label for="ftipo">Tipo</label><select id="ftipo" name="tipo">${opcoes(tipos, filtros.tipo, 'Todos os tipos')}</select></div>
        <div class="fld"><label for="farea">Área técnica</label><select id="farea" name="area">${opcoes(areas, filtros.area, 'Todas as áreas')}</select></div>
        <div class="fld"><label for="fds">Distrito</label><select id="fds" name="distrito">${opcoes(distritos, filtros.distrito === TODOS ? '' : filtros.distrito, 'Todos os distritos')}</select></div>
        <div class="fld"><label for="fstatus">Situação</label><select id="fstatus" name="status"><option value="">Todas</option>
          ${Object.entries(ROTULO_DO_STATUS).map(([v, r]) => html`<option value="${v}" ${selecionado(v, filtros.status)}>${r}</option>`)}</select></div>
        <div class="fld"><label for="fpend">Pendências</label><select id="fpend" name="com_pendencias"><option value="">Todas</option>
          <option value="true" ${selecionado('true', filtros.com_pendencias)}>Com pendência</option><option value="false" ${selecionado('false', filtros.com_pendencias)}>Sem pendência</option></select></div>
        <div class="fld"><label for="ford">Ordenar por</label><select id="ford" name="ordem">
          <option value="nome" ${selecionado('nome', filtros.ordem)}>Nome (A a Z)</option>
          <option value="distrito" ${selecionado('distrito', filtros.ordem)}>Distrito</option>
          <option value="atualizacao" ${selecionado('atualizacao', filtros.ordem)}>Atualizadas por último</option></select></div>
      </form>
      <div class="list-meta"><span id="count" aria-live="polite"></span><button class="btn btn-quiet btn-sm" type="button" id="clearBtn" hidden>${ic('x')}Limpar filtros</button></div>
      <div id="resultado"></div>
    </section>`);

  const ler = () => {
    const f = {
      q: document.getElementById('q').value.trim(),
      tipo: document.getElementById('ftipo').value,
      area: document.getElementById('farea').value,
      distrito: document.getElementById('fds').value || (recorte ? TODOS : ''),
      status: document.getElementById('fstatus').value,
      com_pendencias: document.getElementById('fpend').value,
      ordem: document.getElementById('ford').value,
    };
    return f;
  };

  const resultado = document.getElementById('resultado');
  let pedido = 0;
  const atualizar = async (pagina = Number(filtros.pagina) || 1, tamanho = Number(filtros.tamanho) || 20) => {
    const f = ler();
    const url = new URLSearchParams();
    const api = new URLSearchParams();
    for (const [k, v] of Object.entries(f)) {
      if (!v || (k === 'ordem' && v === 'nome')) continue;
      url.set(k, v);
      if (!(k === 'distrito' && v === TODOS)) api.set(k, v);
    }
    if (pagina > 1) url.set('pagina', String(pagina));
    if (tamanho !== 20) url.set('tamanho', String(tamanho));
    api.set('pagina', String(pagina));
    api.set('tamanho', String(tamanho));
    if (f.ordem) api.set('ordem', f.ordem);
    const qs = url.toString();
    history.replaceState(null, '', `#/unidades${qs ? `?${qs}` : ''}`); // filtros na URL (R5.1)
    document.getElementById('clearBtn').hidden = !qs || (recorte && qs === `distrito=${recorte.escopo_id}`);
    const meu = ++pedido;
    montar(resultado, carregando('Buscando unidades…'));
    let pagina_;
    try {
      ({ dados: pagina_ } = await chamar('GET', `/unidades?${api}`));
    } catch (falha) {
      if (meu === pedido) montar(resultado, erro(falha));
      return;
    }
    if (meu !== pedido) return; // resposta de um filtro antigo
    const { itens, total } = pagina_;
    const ultima = Math.max(1, Math.ceil(total / tamanho));
    const inicio = total ? (pagina - 1) * tamanho + 1 : 0;
    document.getElementById('count').textContent = total
      ? `${inicio}–${inicio + itens.length - 1} de ${total} unidades` : '0 unidades';
    if (!itens.length) {
      montar(resultado, html`${vazio('Nenhuma unidade encontrada.', pagina > ultima ? 'Esta página está além da última.' : 'Revise a busca ou limpe os filtros.')}
        ${pagina > 1 ? html`<div class="list-meta"><button class="btn btn-line btn-sm" type="button" data-pagina="1">Voltar à primeira página</button></div>` : ''}`);
    } else {
      montar(resultado, html`<div class="tbl-wrap"><table>
        <thead><tr><th>Unidade</th><th>Tipo</th><th>Distrito</th><th>Bairro</th><th>Pendências</th><th>Situação</th></tr></thead>
        <tbody>${itens.map((u) => html`<tr class="link" data-id="${u.id}" tabindex="0">
          <td><div class="t-name">${u.nome}</div><div class="t-sub">${u.cnes ? `CNES ${u.cnes}` : 'Sem CNES'}</div></td>
          <td>${tipos.get(String(u.tipo_unidade_id))?.nome || '—'}</td>
          <td>${distritos.get(String(u.distrito_id))?.nome || '—'}</td>
          <td>${u.bairro || '—'}</td>
          <td>${u.pendencias ? html`<span class="chip warn">${u.pendencias}</span>` : html`<span class="chip">0</span>`}</td>
          <td><span class="chip ${u.status === 'ativa' ? '' : 'warn'}">${ROTULO_DO_STATUS[u.status] || u.status}</span></td></tr>`)}</tbody></table></div>
        <nav class="list-meta" aria-label="Paginação">
          <button class="btn btn-line btn-sm" type="button" data-pagina="${pagina - 1}" ${pagina <= 1 ? html`disabled` : ''}>${ic('back')}Anterior</button>
          <span>Página ${pagina} de ${ultima}</span>
          <button class="btn btn-line btn-sm" type="button" data-pagina="${pagina + 1}" ${pagina >= ultima ? html`disabled` : ''}>Próxima${ic('chev')}</button>
          <label>Por página <select id="ftam">${[20, 50, 100].map((n) => html`<option value="${n}" ${n === tamanho ? html`selected` : ''}>${n}</option>`)}</select></label>
        </nav>`);
      document.getElementById('ftam').addEventListener('change', (e) => atualizar(1, Number(e.target.value)));
    }
    resultado.querySelectorAll('[data-pagina]').forEach((b) => b.addEventListener('click', () => atualizar(Number(b.dataset.pagina), tamanho)));
    filtros.pagina = String(pagina);
    filtros.tamanho = String(tamanho);
  };

  let espera;
  document.getElementById('q').addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(() => atualizar(1), 300); });
  document.getElementById('filters').addEventListener('submit', (e) => { e.preventDefault(); atualizar(1); });
  document.querySelectorAll('#filters select').forEach((s) => s.addEventListener('change', () => atualizar(1)));
  resultado.addEventListener('click', (e) => { const tr = e.target.closest('tr[data-id]'); if (tr) location.hash = `#/unidade/${encodeURIComponent(tr.dataset.id)}`; });
  resultado.addEventListener('keydown', (e) => { const tr = e.target.closest('tr[data-id]'); if (tr && e.key === 'Enter') location.hash = `#/unidade/${encodeURIComponent(tr.dataset.id)}`; });
  document.getElementById('clearBtn').addEventListener('click', () => {
    document.getElementById('filters').reset();
    document.querySelectorAll('#filters select').forEach((s) => { s.value = ''; });
    document.getElementById('ford').value = 'nome';
    document.getElementById('q').value = '';
    if (recorte) document.getElementById('fds').value = String(recorte.escopo_id);
    atualizar(1);
  });
  await atualizar();
}
