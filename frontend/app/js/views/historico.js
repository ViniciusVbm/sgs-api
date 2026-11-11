import { html, montar } from '../html.js';
import { chamar } from '../api.js';
import { ic } from '../ui/icone.js';
import { carregando, erro, vazio } from '../ui/estado.js';
import { fmtAuditoria, fmtInstante, resultadoDoEvento, NAO_REGISTRADO } from '../ui/format.js';
import { abrirModal, fecharModal } from '../ui/modal.js';
import { numero } from '../ui/grafico.js';

// Histórico geral para quem tem auditoria:read global (spec 012, R12.2, R12.4, R12.5;
// design § Histórico geral): a trilha da aplicação, o log do banco preenchido pelo trigger
// trg_registry_change_log e as partições criadas pelo procedimento sp_ensure_monthly_partitions.

const TAMANHO = 20;
const ABAS = { trilha: 'Trilha de auditoria', banco: 'Log do banco', particoes: 'Partições do log' };
const TABELAS = { health_units: 'Unidades', equipments: 'Equipamentos', services: 'Serviços' };
const OPERACOES = { INSERT: 'Inclusão', UPDATE: 'Alteração', DELETE: 'Exclusão' };
const ENTIDADES = { unidade: 'Unidade', equipamento: 'Equipamento', servico: 'Serviço', referencia: 'Referência', usuario: 'Usuário' };
const TIPOS_DE_ATOR = { usuario: 'usuário', anonimo: 'anônimo', sistema: 'sistema', servico: 'serviço', seed: 'seed', cli_admin: 'comando administrativo' };
const RESTRITO = 'restrito ao Auditor';

// Resultado do evento (spec 013, R8.4).
export const chipDeResultado = (e) => {
  const r = resultadoDoEvento(e.resultado, e.resultado_categoria);
  return html`<span class="chip ${r.classe}" data-ref="resultado" data-resultado="${r.valor}">${r.rotulo}</span>`;
};
const ouNaoRegistrado = (v) => (v === null || v === undefined || v === '' ? html`<span class="muted">${NAO_REGISTRADO}</span>` : v);

// Datas do filtro em dias de Recife (UTC−3 o ano todo): `de` inclusivo, `ate` exclusivo (dia seguinte).
export const inicioDoDia = (dia) => (dia ? new Date(`${dia}T00:00:00-03:00`).toISOString() : '');
export const fimDoDia = (dia) => (dia ? new Date(new Date(`${dia}T00:00:00-03:00`).getTime() + 86400000).toISOString() : '');

const valorLegivel = (v) => {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'boolean') return v ? 'sim' : 'não';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
};
export const mudanca = (rotulo, de, para) => html`<li><b>${rotulo}</b>: <span class="from">${valorLegivel(de)}</span> → <span class="to">${valorLegivel(para)}</span></li>`;

export const paginacao = (pagina, total) => {
  const ultima = Math.max(1, Math.ceil(total / TAMANHO));
  return html`<nav class="list-meta" aria-label="Paginação"><span data-ref="total" data-total="${total}">${total} registros</span>
    <span>Página ${pagina} de ${ultima}</span><span>
    <button class="btn btn-line btn-sm" type="button" data-pagina="${pagina - 1}" ${pagina <= 1 ? html`disabled` : ''}>${ic('back')}Anterior</button>
    <button class="btn btn-line btn-sm" type="button" data-pagina="${pagina + 1}" ${pagina >= ultima ? html`disabled` : ''}>Próxima${ic('chev')}</button></span></nav>`;
};

export async function telaHistorico(alvo, perfil, consulta) {
  const aba = ABAS[consulta.get('aba')] ? consulta.get('aba') : 'trilha';
  document.title = `${ABAS[aba]} — SGS Recife`;
  montar(alvo, html`
    <div class="page-head"><div><h1>Histórico geral</h1>
      <p>Quem alterou o quê e quando: a trilha da aplicação e o log gravado pelo próprio banco.</p></div></div>
    <section class="panel">
      <nav class="tabs" aria-label="Visões do histórico">${Object.entries(ABAS).map(([k, r]) => html`<a href="#/historico?aba=${k}" class="${k === aba ? 'on' : ''}" ${k === aba ? html`aria-current="page"` : ''} data-aba="${k}">${r}</a>`)}</nav>
      <div id="h-corpo"></div>
    </section>`);
  const corpo = document.getElementById('h-corpo');
  if (aba === 'trilha') await abaTrilha(corpo, consulta);
  else if (aba === 'banco') await abaBanco(corpo, consulta);
  else await abaParticoes(corpo);
}

async function abaTrilha(corpo, consulta) {
  const f = { de: consulta.get('de') || '', ate: consulta.get('ate') || '', acao: consulta.get('acao') || '', entidade_tipo: consulta.get('entidade_tipo') || '', autor: consulta.get('autor') || '', autor_nome: consulta.get('autor_nome') || '' };
  montar(corpo, html`
    <form class="filters" id="ft" aria-label="Filtros da trilha">
      <div class="fld"><label for="ft-de">De</label><input id="ft-de" type="date" value="${f.de}"></div>
      <div class="fld"><label for="ft-ate">Até (inclusive)</label><input id="ft-ate" type="date" value="${f.ate}"></div>
      <div class="fld"><label for="ft-acao">Ação (início)</label><input id="ft-acao" type="search" maxlength="100" placeholder="Ex.: unidade." value="${f.acao}"></div>
      <div class="fld"><label for="ft-entidade">Entidade</label><select id="ft-entidade"><option value="">Todas</option>
        ${Object.entries(ENTIDADES).map(([k, r]) => html`<option value="${k}" ${k === f.entidade_tipo ? html`selected` : ''}>${r}</option>`)}</select></div>
      <button class="btn btn-line btn-sm" type="submit">Filtrar</button>
    </form>
    <div class="list-meta" id="ft-autor" ${f.autor ? '' : html`hidden`}></div>
    <div id="ft-resultado"></div>`);
  const resultado = document.getElementById('ft-resultado');
  const caixaAutor = document.getElementById('ft-autor');
  const desenharAutor = () => {
    caixaAutor.hidden = !f.autor;
    montar(caixaAutor, f.autor ? html`<span>Autor: <b>${f.autor_nome || f.autor}</b></span><button class="btn btn-quiet btn-sm" type="button" id="ft-sem-autor">${ic('x')}Todos os autores</button>` : html``);
    const limpar = document.getElementById('ft-sem-autor');
    if (limpar) limpar.addEventListener('click', () => { f.autor = ''; f.autor_nome = ''; carregar(1); });
  };
  const carregar = async (pagina) => {
    f.de = document.getElementById('ft-de').value;
    f.ate = document.getElementById('ft-ate').value;
    f.acao = document.getElementById('ft-acao').value.trim();
    f.entidade_tipo = document.getElementById('ft-entidade').value;
    // A trilha é a aba padrão: sem filtros, a URL continua `#/historico` (início do Auditor, R3.5).
    const url = new URLSearchParams(Object.entries(f).filter(([, v]) => v));
    history.replaceState(null, '', `#/historico${url.toString() ? `?${url}` : ''}`);
    desenharAutor();
    const api = new URLSearchParams([['pagina', String(pagina)], ['tamanho', String(TAMANHO)]]);
    if (f.de) api.set('de', inicioDoDia(f.de));
    if (f.ate) api.set('ate', fimDoDia(f.ate));
    for (const k of ['acao', 'entidade_tipo', 'autor']) if (f[k]) api.set(k, f[k]);
    montar(resultado, carregando('Buscando eventos…'));
    let dados;
    try {
      ({ dados } = await chamar('GET', `/auditoria/eventos?${api}`));
    } catch (falha) {
      montar(resultado, erro(falha));
      return;
    }
    montar(resultado, dados.itens.length ? html`<div class="tbl-wrap"><table>
      <thead><tr><th>Quando</th><th>Ação</th><th>Resultado</th><th>Entidade</th><th>Autor</th><th>Mudanças</th><th>Detalhe</th></tr></thead>
      <tbody>${dados.itens.map((e) => html`<tr data-evento="${e.id}">
        <td>${fmtAuditoria(e.quando)}</td><td><code>${e.acao}</code></td><td>${chipDeResultado(e)}</td>
        <td>${ENTIDADES[e.entidade_tipo] || e.entidade_tipo || '—'}${e.entidade_id ? html`<div class="t-sub">${e.entidade_id}</div>` : ''}</td>
        <td>${e.autor.id ? html`<button class="btn btn-quiet btn-sm" type="button" data-autor="${e.autor.id}" data-autor-nome="${e.autor.nome || ''}" title="Filtrar por este autor">${e.autor.nome || e.autor.id}</button>` : 'sistema'}
          ${e.autor.papeis.length ? html`<div class="t-sub">${e.autor.papeis.join(', ')}</div>` : ''}</td>
        <td>${e.mudancas.length ? html`<ul class="changes">${e.mudancas.map((m) => mudanca(m.rotulo || m.campo, m.de, m.para))}</ul>` : '—'}</td>
        <td><button class="btn btn-line btn-sm" type="button" data-detalhe="${e.id}">Detalhe</button></td></tr>`)}</tbody></table></div>
      ${paginacao(pagina, dados.total)}` : html`${vazio('Nenhum evento com estes filtros.')}${paginacao(pagina, dados.total)}`);
    resultado.querySelectorAll('[data-pagina]').forEach((b) => b.addEventListener('click', () => carregar(Number(b.dataset.pagina))));
    resultado.querySelectorAll('[data-autor]').forEach((b) => b.addEventListener('click', () => { f.autor = b.dataset.autor; f.autor_nome = b.dataset.autorNome; carregar(1); }));
    resultado.querySelectorAll('[data-detalhe]').forEach((b) => b.addEventListener('click', () => detalharEvento(b.dataset.detalhe)));
  };
  document.getElementById('ft').addEventListener('submit', (e) => { e.preventDefault(); carregar(1); });
  document.getElementById('ft-entidade').addEventListener('change', () => carregar(1));
  await carregar(1);
}

// Detalhe do evento (spec 013, R8.1, R8.2, R2.2): tudo o que a API devolve. IP, User-Agent e
// sessão só chegam a quem tem `auditoria:read_acessos`; para os demais a API os manda nulos com
// `origem_restrita`, e a tela diz que são restritos (a regra é do backend, não daqui).
async function detalharEvento(id) {
  const caixa = abrirModal(html`<div class="modal-h"><h2>Evento ${id}</h2></div><div class="modal-b" id="ev-corpo">${carregando('Lendo o evento…')}</div>
    <div class="modal-f"><button class="btn btn-line" type="button" id="ev-fechar">Fechar</button></div>`, { rotulo: `Detalhe do evento ${id}` });
  caixa.querySelector('#ev-fechar').addEventListener('click', fecharModal);
  const destino = caixa.querySelector('#ev-corpo');
  let e;
  try {
    ({ dados: e } = await chamar('GET', `/auditoria/eventos/${encodeURIComponent(id)}`));
  } catch (falha) {
    montar(destino, erro(falha));
    return;
  }
  const origem = (v) => (e.origem_restrita ? html`<span class="muted" data-ref="restrito">${RESTRITO}</span>` : ouNaoRegistrado(v));
  const campo = (rotulo, valor, ref) => html`<div><dt>${rotulo}</dt><dd data-ref="${ref}">${valor}</dd></div>`;
  montar(destino, html`<dl class="kv" data-ref="detalhe-evento" data-origem-restrita="${e.origem_restrita ? 'true' : 'false'}">
    ${campo('Ação', html`<code>${e.acao}</code>`, 'acao')}
    ${campo('Instante', html`<code>${fmtInstante(e.quando)}</code>`, 'instante')}
    ${campo('Resultado', chipDeResultado(e), 'resultado')}
    ${campo('Autor', e.autor.nome || e.autor.id || '—', 'autor')}
    ${campo('Tipo de ator', ouNaoRegistrado(TIPOS_DE_ATOR[e.autor.tipo] || e.autor.tipo), 'tipo-ator')}
    ${campo('Origem', ouNaoRegistrado(e.origem), 'origem')}
    ${campo('Entidade', e.entidade_tipo ? `${ENTIDADES[e.entidade_tipo] || e.entidade_tipo} ${e.entidade_id || ''}` : '—', 'entidade')}
    ${campo('IP', origem(e.ip), 'ip')}
    ${campo('User-Agent', origem(e.user_agent), 'user-agent')}
    ${campo('Sessão', origem(e.sessao_id), 'sessao')}
    ${campo('Request id', ouNaoRegistrado(e.request_id), 'request-id')}
    ${campo('Hash anterior', html`<code class="hash">${e.prev_hash || '—'}</code>`, 'prev-hash')}
    ${campo('Hash', html`<code class="hash">${e.hash || '—'}</code>`, 'hash')}
  </dl>
  ${e.mudancas.length ? html`<table><thead><tr><th>Campo</th><th>De</th><th>Para</th></tr></thead><tbody>${e.mudancas.map((m) => html`<tr><td>${m.rotulo || m.campo}</td><td>${valorLegivel(m.de)}</td><td>${valorLegivel(m.para)}</td></tr>`)}</tbody></table>` : ''}
  ${Object.keys(e.metadados || {}).length ? html`<p class="hint">Metadados</p><pre class="metadados">${JSON.stringify(e.metadados, null, 2)}</pre>` : ''}`);
}

async function abaBanco(corpo, consulta) {
  const f = { de: consulta.get('de') || '', ate: consulta.get('ate') || '', tabela: consulta.get('tabela') || '', fora_da_api: consulta.get('fora_da_api') === 'true' };
  montar(corpo, html`
    <div class="panel-b"><div class="banner info" data-ref="origem-log">${ic('info')}<p>Registrado pelo trigger <code>trg_registry_change_log</code> em toda escrita em unidades, equipamentos e serviços, <b>inclusive fora da aplicação</b>. O nome do gestor chega mascarado pelo próprio banco.</p></div></div>
    <form class="filters" id="fb" aria-label="Filtros do log do banco">
      <div class="fld"><label for="fb-tabela">Tabela</label><select id="fb-tabela"><option value="">Todas</option>
        ${Object.entries(TABELAS).map(([k, r]) => html`<option value="${k}" ${k === f.tabela ? html`selected` : ''}>${r}</option>`)}</select></div>
      <div class="fld"><label for="fb-de">De</label><input id="fb-de" type="date" value="${f.de}"></div>
      <div class="fld"><label for="fb-ate">Até (inclusive)</label><input id="fb-ate" type="date" value="${f.ate}"></div>
      <label class="check"><input id="fb-fora" type="checkbox" ${f.fora_da_api ? html`checked` : ''}> Só alterações feitas fora da API</label>
      <button class="btn btn-line btn-sm" type="submit">Filtrar</button>
    </form>
    <div id="fb-resultado"></div>`);
  const resultado = document.getElementById('fb-resultado');
  const carregar = async (pagina) => {
    f.tabela = document.getElementById('fb-tabela').value;
    f.de = document.getElementById('fb-de').value;
    f.ate = document.getElementById('fb-ate').value;
    f.fora_da_api = document.getElementById('fb-fora').checked;
    const url = new URLSearchParams([['aba', 'banco']]);
    for (const k of ['tabela', 'de', 'ate']) if (f[k]) url.set(k, f[k]);
    if (f.fora_da_api) url.set('fora_da_api', 'true');
    history.replaceState(null, '', `#/historico?${url}`);
    const api = new URLSearchParams([['pagina', String(pagina)], ['tamanho', String(TAMANHO)], ['fora_da_api', String(f.fora_da_api)]]);
    if (f.tabela) api.set('tabela', f.tabela);
    if (f.de) api.set('de', inicioDoDia(f.de));
    if (f.ate) api.set('ate', fimDoDia(f.ate));
    montar(resultado, carregando('Buscando registros do banco…'));
    let dados;
    try {
      ({ dados } = await chamar('GET', `/auditoria/banco?${api}`));
    } catch (falha) {
      montar(resultado, erro(falha));
      return;
    }
    montar(resultado, dados.itens.length ? html`<div class="tbl-wrap"><table>
      <thead><tr><th>Quando</th><th>Tabela</th><th>Operação</th><th>Linha</th><th>Colunas alteradas</th><th>Usuário do banco</th><th>Origem</th></tr></thead>
      <tbody>${dados.itens.map((r) => html`<tr data-registro="${r.id}" data-linha="${r.linha_id}">
        <td>${fmtAuditoria(r.quando)}</td><td>${TABELAS[r.tabela] || r.tabela}</td><td>${OPERACOES[r.operacao] || r.operacao}</td>
        <td>${r.tabela === 'health_units' ? html`<a href="#/unidade/${encodeURIComponent(r.linha_id)}"><code>${r.linha_id.slice(0, 8)}</code></a>` : html`<code title="${r.linha_id}">${r.linha_id.slice(0, 8)}</code>`}</td>
        <td><ul class="changes">${Object.entries(r.colunas).map(([c, v]) => mudanca(c, v && v.de, v && v.para))}</ul></td>
        <td><code>${r.usuario_do_banco}</code></td>
        <td><span class="chip ${r.pela_api ? 'ok' : 'warn'}" data-ref="origem">${r.pela_api ? 'pela API' : 'fora da API'}</span></td></tr>`)}</tbody></table></div>
      ${paginacao(pagina, dados.total)}` : html`${vazio(f.fora_da_api ? 'Nenhuma alteração feita fora da API neste filtro.' : 'Nenhum registro com estes filtros.')}${paginacao(pagina, dados.total)}`);
    resultado.querySelectorAll('[data-pagina]').forEach((b) => b.addEventListener('click', () => carregar(Number(b.dataset.pagina))));
  };
  document.getElementById('fb').addEventListener('submit', (e) => { e.preventDefault(); carregar(1); });
  document.getElementById('fb-tabela').addEventListener('change', () => carregar(1));
  document.getElementById('fb-fora').addEventListener('change', () => carregar(1));
  await carregar(1);
}

async function abaParticoes(corpo) {
  montar(corpo, carregando('Lendo as partições…'));
  let particoes;
  try {
    ({ dados: particoes } = await chamar('GET', '/auditoria/banco/particoes'));
  } catch (falha) {
    montar(corpo, erro(falha));
    return;
  }
  const linhas = particoes.reduce((s, p) => s + p.linhas, 0);
  montar(corpo, html`
    <div class="panel-b"><div class="banner info" data-ref="origem-particoes">${ic('info')}<p>Partições mensais do log do banco, criadas pelo procedimento com cursor <code>sp_ensure_monthly_partitions</code> (comando <code>sgs-admin banco particoes</code>). A interface só as consulta: o procedimento não é executado por aqui.</p></div></div>
    <p class="list-meta"><span><b data-ref="total" data-total="${particoes.length}">${particoes.length}</b> partições · ${numero(linhas, 0)} registros no total</span></p>
    ${particoes.length ? html`<div class="tbl-wrap"><table><thead><tr><th>Partição</th><th>Limite</th><th>Registros</th></tr></thead>
      <tbody>${particoes.map((p) => html`<tr data-particao="${p.nome}"><td><code>${p.nome}</code></td><td>${p.limite}</td><td>${p.linhas}</td></tr>`)}</tbody></table></div>` : vazio('Nenhuma partição encontrada.')}`);
}

// Verificação da cadeia de hash da trilha (R12.4; spec 013, R8.3): só leitura no banco. Mostra o
// fim da cadeia conferido com a cabeça e, com uma âncora guardada fora do banco (gerada por
// `sgs-admin auditoria ancorar`), se a cadeia e o evento ancorado conferem.
const HEX = '^[0-9a-f]{64}$';
const confere = (valor) => (valor === null || valor === undefined ? '—' : valor ? 'sim' : html`<b>não</b>`);
export async function telaCadeia(alvo) {
  document.title = 'Verificação da cadeia — SGS Recife';
  montar(alvo, html`
    <div class="page-head"><div><h1>Verificação da cadeia</h1>
      <p>Recalcula o encadeamento por hash de toda a trilha e confere o fim com a cabeça da cadeia. Os registros não podem ser alterados nem apagados pela aplicação: triggers do banco bloqueiam UPDATE, DELETE e TRUNCATE.</p></div></div>
    <section class="panel"><form class="filters" id="cadeia-form" aria-label="Âncora externa (opcional)">
      <div class="fld"><label for="ancora-cadeia">Âncora: cadeia_id</label><input id="ancora-cadeia" pattern="${HEX}" maxlength="64" placeholder="opcional"></div>
      <div class="fld"><label for="ancora-id">Âncora: id</label><input id="ancora-id" type="number" min="1" placeholder="opcional"></div>
      <div class="fld"><label for="ancora-hash">Âncora: hash</label><input id="ancora-hash" pattern="${HEX}" maxlength="64" placeholder="opcional"></div>
      <button class="btn btn-primary" type="submit" id="verificar">${ic('shield')}Verificar agora</button>
    </form>
    <div class="panel-b" id="cadeia-resultado">${vazio('Clique em "Verificar agora". A âncora é opcional; informe os três campos ou nenhum.')}</div></section>`);
  const destino = document.getElementById('cadeia-resultado');
  document.getElementById('cadeia-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const ancora = {
      cadeia_id: document.getElementById('ancora-cadeia').value.trim(),
      id: document.getElementById('ancora-id').value.trim(),
      hash: document.getElementById('ancora-hash').value.trim(),
    };
    const preenchidos = Object.values(ancora).filter(Boolean).length;
    if (preenchidos !== 0 && preenchidos !== 3) {
      montar(destino, html`<div class="err-summary" role="alert" data-ref="ancora-incompleta"><b>${ic('alert')}Âncora incompleta.</b><p>Informe cadeia_id, id e hash, ou deixe os três em branco.</p></div>`);
      return;
    }
    const corpo = preenchidos ? { ancora: { ...ancora, id: Number(ancora.id) } } : {};
    montar(destino, carregando('Verificando a cadeia…'));
    let r;
    try {
      ({ dados: r } = await chamar('POST', '/auditoria/verificar', { corpo }));
    } catch (falha) {
      montar(destino, erro(falha));
      return;
    }
    const detalhes = html`<dl class="kv" data-ref="detalhes-cadeia">
      <div><dt>Eventos verificados</dt><dd data-ref="verificados">${r.verificados}</dd></div>
      <div><dt>Último evento</dt><dd data-ref="ultimo-id">${r.ultimo_id ?? '—'}</dd></div>
      <div><dt>Hash final</dt><dd><code class="hash" data-ref="hash-final">${r.hash_final || '—'}</code></dd></div>
      <div><dt>Cabeça confere</dt><dd data-ref="cabeca-confere" data-valor="${String(r.cabeca_confere)}">${confere(r.cabeca_confere)}</dd></div>
      <div><dt>Cadeia da âncora</dt><dd data-ref="cadeia-confere" data-valor="${String(r.cadeia_confere)}">${confere(r.cadeia_confere)}</dd></div>
      <div><dt>Âncora confere</dt><dd data-ref="ancora-confere" data-valor="${String(r.ancora_confere)}">${confere(r.ancora_confere)}</dd></div></dl>`;
    montar(destino, r.integra
      ? html`<div class="banner ok" data-ref="resultado-cadeia" data-integra="true">${ic('check')}<p><b>Cadeia íntegra.</b> ${r.verificados} eventos verificados.</p></div>${detalhes}`
      : html`<div class="err-summary" role="alert" data-ref="resultado-cadeia" data-integra="false"><b>${ic('alert')}${r.primeiro_evento_divergente ? `Cadeia divergente no evento ${r.primeiro_evento_divergente}.` : 'Cadeia divergente.'}</b><p>${r.motivo || ''} (${r.verificados} eventos verificados)</p></div>${detalhes}`);
  });
}
