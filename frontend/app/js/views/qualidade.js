import { html, montar } from '../html.js';
import { chamar } from '../api.js';
import { ic } from '../ui/icone.js';
import { carregando, erro, vazio } from '../ui/estado.js';
import { fmtDataHora } from '../ui/format.js';
import { carregarReferencia } from '../referencias.js';
import { buscarTodas } from '../paginas.js';
import { PERIODOS, intervaloDoPeriodo, contarPorIntervalo, hojeEmRecife } from '../periodo.js';
import { barras, barrasAgrupadas, barrasEmpilhadas, rosca, linha, numero, CORES, COR_OUTROS } from '../ui/grafico.js';

// Painel de qualidade e consultas (spec 012, R12.1 sem as 8 verificações, R12.6; design § Qualidade).
// Todo número vem da API ou de uma conta declarada sobre a resposta dela; nada é fixo nem simulado.
// Os filtros de distrito, tipo e área vão para a API (que também aplica o escopo de leitura) e
// ficam na URL; o período vale só para a linha das alterações, a partir do log do banco.

const FILTROS = ['distrito', 'tipo', 'area'];
const TAMANHO = 20;

export const SITUACOES = [
  { chave: 'regular', rotulo: 'Regular', cor: 'var(--viz-ok)' },
  { chave: 'sem_cnes', rotulo: 'Sem CNES', cor: 'var(--viz-espera)' },
  { chave: 'com_pendencias', rotulo: 'Com pendências', cor: 'var(--viz-alerta)' },
  { chave: 'inativa', rotulo: 'Inativa', cor: 'var(--viz-neutro)' },
];
const ROTULO_DA_SITUACAO = Object.fromEntries(SITUACOES.map((s) => [s.chave, s.rotulo]));
const CONCILIACAO = { par: 'Unidade e equipamento', unidade_sem_equipamento: 'Unidade sem equipamento', equipamento_sem_unidade: 'Equipamento sem unidade' };

// Um id da URL que não está nas referências continua selecionado e vai para a API, que responde
// 422; a tela mostra o erro dela em vez de descartar o filtro em silêncio.
const opcoes = (mapa, atual, rotuloTodos) => html`<option value="">${rotuloTodos}</option>${[...mapa.values()]
  .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  .map((r) => html`<option value="${r.id}" ${String(r.id) === atual ? html`selected` : ''}>${r.nome}</option>`)}${
  atual && !mapa.has(atual) ? html`<option value="${atual}" selected>${atual} (não encontrado)</option>` : ''}`;

const caminhoDaApi = (rota) => rota.replace(/^\/api\/v1/, '');
const semValor = (v) => (v === null || v === undefined || v === '' ? '—' : v);
const ficha = (id, nome) => html`<a href="#/unidade/${encodeURIComponent(id)}">${nome}</a>`;

const figura = (ref, valor, rotulo, sub, extra = '') =>
  html`<div class="fig" data-ref="${ref}" ${extra}><div class="v">${valor}</div><div class="l">${rotulo}</div><div class="s">${sub}</div></div>`;

// Como cada consulta do catálogo é mostrada (as colunas são as do esquema de resposta da API).
const TABELAS = {
  'unidades-sem-servico': {
    cabecalho: ['Unidade', 'CNES', 'Tipo', 'Distrito'],
    linha: (u) => [ficha(u.id, u.nome), semValor(u.cnes), u.tipo, u.distrito],
  },
  'conciliacao-unidade-equipamento': {
    cabecalho: ['Unidade', 'Distrito', 'Equipamento', 'Tipo do equipamento', 'Situação'],
    linha: (l) => [l.unidade_id ? ficha(l.unidade_id, l.unidade_nome) : '—', semValor(l.distrito), semValor(l.equipamento_nome),
      semValor(l.equipamento_tipo), html`<span class="chip ${l.situacao === 'par' ? 'ok' : 'warn'}">${CONCILIACAO[l.situacao] || l.situacao}</span>`],
  },
  'distritos-sem-cnes-acima-da-rede': {
    cabecalho: ['Distrito', 'Unidades', 'Sem CNES', '% sem CNES', '% da rede'],
    linha: (d) => [d.district_name, d.total_units, d.units_without_cnes, `${numero(d.percent_without_cnes, 2)}%`, `${numero(d.network_percent_without_cnes, 2)}%`],
  },
  'unidades-com-servico-fora-do-cnes': {
    cabecalho: ['Unidade', 'CNES', 'Tipo', 'Distrito', 'Serviços fora do CNES'],
    linha: (u) => [ficha(u.unit_id, u.name), semValor(u.cnes), u.unit_type_name, u.district_name, u.services_outside_cnes_count],
  },
  inventario: {
    cabecalho: ['Unidade', 'Tipo', 'Área técnica', 'Distrito', 'Situação cadastral', 'Equipamentos', 'Serviços', 'Fora do CNES'],
    linha: (u) => [ficha(u.unit_id, u.name), u.unit_type_name, u.technical_area_name, u.district_name,
      html`<span class="chip">${ROTULO_DA_SITUACAO[u.registration_status] || u.registration_status}</span>`,
      u.equipment_count, u.service_count, u.services_outside_cnes_count],
  },
  'unidades-por-categoria': {
    cabecalho: ['Categoria', 'Item', 'Unidades'],
    linha: (c) => [c.categoria, c.rotulo, c.quantidade],
  },
  'equipamentos-por-tipo-e-distrito': {
    cabecalho: ['Tipo de equipamento', 'Distrito', 'Cadastros', 'Quantidade total'],
    linha: (e) => [e.equipment_type_name, e.district_name, e.equipment_count, e.total_quantity],
  },
  'alteracoes-por-periodo': {
    cabecalho: ['Distrito', 'Últimos 7 dias', 'Últimos 30 dias'],
    linha: (a) => [a.district_name, a.last_7_days, a.last_30_days],
  },
  'alteracoes-recentes': {
    cabecalho: ['Quando', 'Ação', 'Unidade', 'Distrito', 'Autor'],
    linha: (a) => [fmtDataHora(a.occurred_at), a.action, ficha(a.unit_id, a.unit_name), semValor(a.district_name), a.actor_name || 'sistema'],
  },
};

function tabelaGenerica(itens) {
  const chaves = Object.keys(itens[0] || {});
  return { cabecalho: chaves, linha: (i) => chaves.map((k) => (typeof i[k] === 'object' && i[k] !== null ? JSON.stringify(i[k]) : semValor(i[k]))) };
}

export async function telaQualidade(alvo, perfil, consulta) {
  document.title = 'Qualidade dos dados — SGS Recife';
  const filtros = Object.fromEntries(FILTROS.map((f) => [f, consulta.get(f) || '']));
  const periodo = { tipo: PERIODOS[consulta.get('periodo')] ? consulta.get('periodo') : '7', de: consulta.get('de') || '', ate: consulta.get('ate') || '' };
  const veLog = perfil.global('auditoria:read'); // a linha do período usa o log do banco (escopo global)
  montar(alvo, carregando());
  let distritos; let tipos; let areas; let tiposDeEquipamento; let catalogo;
  try {
    [distritos, tipos, areas, tiposDeEquipamento, { dados: catalogo }] = await Promise.all([
      ...['distritos', 'tipos-unidade', 'areas-tecnicas', 'tipos-equipamento'].map(carregarReferencia),
      chamar('GET', '/dashboard/consultas'),
    ]);
  } catch (falha) {
    montar(alvo, erro(falha));
    return;
  }

  montar(alvo, html`
    <div class="page-head"><div><h1>Qualidade dos dados</h1>
      <p>Indicadores, gráficos e as consultas do banco, calculados pela API no seu escopo de acesso.</p></div></div>
    <section class="panel">
      <form class="filters" id="fq" role="search" aria-label="Filtros do painel">
        <div class="fld"><label for="fq-distrito">Distrito</label><select id="fq-distrito" name="distrito">${opcoes(distritos, filtros.distrito, 'Todos os distritos')}</select></div>
        <div class="fld"><label for="fq-tipo">Tipo de unidade</label><select id="fq-tipo" name="tipo">${opcoes(tipos, filtros.tipo, 'Todos os tipos')}</select></div>
        <div class="fld"><label for="fq-area">Área técnica</label><select id="fq-area" name="area">${opcoes(areas, filtros.area, 'Todas as áreas')}</select></div>
        <button class="btn btn-quiet btn-sm" type="button" id="fq-limpar">${ic('x')}Limpar filtros</button>
      </form>
      <div class="panel-b">
        <div id="q-indicadores" aria-live="polite"></div>
        <div class="viz-grade" id="q-graficos"></div>
      </div>
    </section>
    ${veLog ? html`<section class="panel" id="q-periodo">
      <div class="panel-h"><div><h2>Alterações no período</h2><p>Registros do log do banco (trigger <code>trg_registry_change_log</code>), somados em todas as páginas. Os filtros de distrito, tipo e área não se aplicam a este gráfico.</p></div></div>
      <form class="filters" id="fp" aria-label="Período">
        <div class="seg-tabs" role="group" aria-label="Período">${Object.entries(PERIODOS).map(([v, r]) => html`<a href="#" role="button" data-periodo="${v}" class="${periodo.tipo === v ? 'on' : ''}" aria-pressed="${periodo.tipo === v}">${r}</a>`)}</div>
        <div class="fld" data-personalizado ${periodo.tipo === 'personalizado' ? '' : html`hidden`}><label for="fp-de">De</label><input id="fp-de" type="date" value="${periodo.de}" max="${hojeEmRecife()}"></div>
        <div class="fld" data-personalizado ${periodo.tipo === 'personalizado' ? '' : html`hidden`}><label for="fp-ate">Até (inclusive)</label><input id="fp-ate" type="date" value="${periodo.ate}" max="${hojeEmRecife()}"></div>
        <button class="btn btn-line btn-sm" type="submit" data-personalizado ${periodo.tipo === 'personalizado' ? '' : html`hidden`}>Aplicar</button>
      </form>
      <div class="panel-b" id="q-linha"></div>
    </section>` : ''}
    <section class="panel">
      <div class="panel-h"><div><h2>Consultas e views do banco</h2><p>Cada consulta mostra a técnica SQL e a justificativa como vêm da API. Abra uma para ver o resultado com os filtros acima.</p></div></div>
      <div class="consultas" id="q-consultas">${catalogo.map((e) => html`
        <details class="consulta" data-consulta="${e.nome}">
          <summary><span class="t-name">${e.titulo}</span><span class="chip" data-ref="tecnica">${e.tecnica_sql}</span></summary>
          <div class="consulta-b"><p class="muted" data-ref="justificativa">${e.justificativa}</p><div data-ref="resultado"></div></div>
        </details>`)}</div>
    </section>`);

  const elementos = {
    indicadores: document.getElementById('q-indicadores'),
    graficos: document.getElementById('q-graficos'),
    linha: document.getElementById('q-linha'),
  };
  const lerFiltros = () => Object.fromEntries(FILTROS.map((f) => [f, document.getElementById(`fq-${f}`).value]));
  const guardarNaUrl = () => {
    const url = new URLSearchParams(Object.entries(lerFiltros()).filter(([, v]) => v));
    if (veLog && periodo.tipo !== '7') url.set('periodo', periodo.tipo);
    if (veLog && periodo.tipo === 'personalizado') { url.set('de', periodo.de); url.set('ate', periodo.ate); }
    const qs = url.toString();
    history.replaceState(null, '', `#/qualidade${qs ? `?${qs}` : ''}`); // filtros na URL (R12.6)
  };

  let geracao = 0;
  let resumoAtual = null;
  const atualizarPainel = async () => {
    guardarNaUrl();
    const meu = ++geracao;
    const f = lerFiltros();
    montar(elementos.indicadores, carregando('Calculando indicadores…'));
    montar(elementos.graficos, html``);
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
    const sufixo = qs ? `?${qs}` : '';
    const [resumo, inventario, cnes, equipamentos, alteracoes] = await Promise.allSettled([
      chamar('GET', `/dashboard/resumo${sufixo}`).then((r) => r.dados),
      buscarTodas('/dashboard/inventario', f),
      buscarTodas('/dashboard/consultas/distritos-sem-cnes-acima-da-rede', f),
      chamar('GET', `/dashboard/consultas/equipamentos-por-tipo-e-distrito${sufixo}`).then((r) => r.dados),
      chamar('GET', `/dashboard/consultas/alteracoes-por-periodo${sufixo}`).then((r) => r.dados),
    ]);
    if (meu !== geracao) return; // resposta de um filtro antigo
    resumoAtual = resumo.status === 'fulfilled' ? resumo.value : null;
    desenharIndicadores(elementos.indicadores, resumo, inventario, alteracoes);
    desenharGraficos(elementos.graficos, { inventario, cnes, equipamentos, alteracoes, tiposDeEquipamento });
    document.querySelectorAll('#q-consultas details[open]').forEach((d) => carregarConsulta(d, 1));
  };

  const atualizarLinha = async () => {
    if (!veLog) return;
    guardarNaUrl();
    const intervalo = intervaloDoPeriodo(periodo.tipo, periodo.de, periodo.ate);
    if (intervalo.erro) {
      montar(elementos.linha, html`<p class="fld-err" role="alert" data-ref="erro-periodo">${intervalo.erro}</p>`);
      return;
    }
    montar(elementos.linha, carregando('Somando os registros do período…'));
    let resultado;
    try {
      resultado = await buscarTodas('/auditoria/banco', { de: intervalo.de.toISOString(), ate: intervalo.ate.toISOString() });
    } catch (falha) {
      montar(elementos.linha, erro(falha));
      return;
    }
    const pontos = contarPorIntervalo(resultado.itens, intervalo);
    const comRegistro = pontos.filter((p) => p.valor > 0).length;
    const aviso = comRegistro < 2
      ? html`<div class="banner info" data-ref="historico-insuficiente">${ic('info')}<p>Ainda não há histórico suficiente para mostrar tendência neste período: ${comRegistro ? 'todos os registros caem num único intervalo' : 'não há registros'}.</p></div>`
      : '';
    montar(elementos.linha, html`${aviso}${linha({
      ref: 'grafico-linha',
      titulo: `Registros do log por ${intervalo.porHora ? 'hora' : 'dia'}`,
      subtitulo: `${resultado.total} registros de ${intervalo.deIso.split('-').reverse().join('/')} a ${intervalo.ateIso.split('-').reverse().join('/')}`,
      pontos,
    })}`);
    elementos.linha.querySelector('[data-ref=grafico-linha]').dataset.total = String(resultado.total);
  };

  const carregarConsulta = async (detalhe, pagina) => {
    const entrada = catalogo.find((e) => e.nome === detalhe.dataset.consulta);
    const destino = detalhe.querySelector('[data-ref=resultado]');
    if (entrada.nome === 'resumo') {
      montar(destino, resumoAtual ? html`<p>Os indicadores do topo desta página e do Início vêm desta consulta: ${resumoAtual.unidades.total} unidades, ${resumoAtual.qualidade.sem_cnes} sem CNES, ${resumoAtual.qualidade.unidades_com_pendencias} com pendências e ${resumoAtual.alteracoes.ultimos_7_dias} alterações em 7 dias.</p>` : vazio('Resumo indisponível.'));
      return;
    }
    if (entrada.rota.includes('{')) {
      montar(destino, html`<p>Esta consulta é de uma unidade: abra uma ficha pela <a href="#/unidades">lista de unidades</a> e veja a aba Histórico.</p>`);
      return;
    }
    if (entrada.rota.startsWith('/api/v1/auditoria/')) {
      const aba = entrada.rota.endsWith('/particoes') ? 'particoes' : 'banco';
      montar(destino, html`<p>Disponível no <a href="#/historico?aba=${aba}" data-ref="link-historico">Histórico, aba ${aba === 'banco' ? 'Log do banco' : 'Partições'}</a>, com os filtros próprios dela.</p>`);
      return;
    }
    const f = lerFiltros();
    const params = new URLSearchParams(FILTROS.filter((k) => entrada.parametros.includes(k) && f[k]).map((k) => [k, f[k]]));
    const situacao = detalhe.querySelector('[data-ref=situacao]');
    if (entrada.parametros.includes('situacao') && situacao && situacao.value) params.set('situacao', situacao.value);
    if (entrada.paginada) { params.set('pagina', String(pagina)); params.set('tamanho', String(TAMANHO)); }
    const filtroDeSituacao = entrada.parametros.includes('situacao')
      ? html`<div class="fld consulta-filtro"><label for="fs-${entrada.nome}">Situação cadastral</label><select id="fs-${entrada.nome}" data-ref="situacao"><option value="">Todas</option>${SITUACOES.map((s) => html`<option value="${s.chave}" ${situacao && situacao.value === s.chave ? html`selected` : ''}>${s.rotulo}</option>`)}</select></div>`
      : '';
    montar(destino, html`${filtroDeSituacao}${carregando()}`);
    let dados;
    try {
      ({ dados } = await chamar('GET', `${caminhoDaApi(entrada.rota)}?${params}`));
    } catch (falha) {
      montar(destino, html`${filtroDeSituacao}${erro(falha)}`);
      ligarSituacao(detalhe);
      return;
    }
    const itens = entrada.paginada ? dados.itens : dados;
    const total = entrada.paginada ? dados.total : dados.length;
    const formato = TABELAS[entrada.nome] || tabelaGenerica(itens);
    const ultima = Math.max(1, Math.ceil(total / TAMANHO));
    montar(destino, html`${filtroDeSituacao}
      <p class="list-meta consulta-meta"><span>Total: <b data-ref="total" data-total="${total}">${total}</b></span>${entrada.paginada ? html`<span>Página ${pagina} de ${ultima}</span>` : ''}</p>
      ${itens.length ? html`<div class="tbl-wrap"><table><thead><tr>${formato.cabecalho.map((c) => html`<th>${c}</th>`)}</tr></thead>
        <tbody>${itens.map((i) => html`<tr>${formato.linha(i).map((c) => html`<td>${c}</td>`)}</tr>`)}</tbody></table></div>` : vazio('Nenhuma linha com estes filtros.')}
      ${entrada.paginada && ultima > 1 ? html`<nav class="list-meta" aria-label="Paginação">
        <button class="btn btn-line btn-sm" type="button" data-pagina="${pagina - 1}" ${pagina <= 1 ? html`disabled` : ''}>${ic('back')}Anterior</button>
        <button class="btn btn-line btn-sm" type="button" data-pagina="${pagina + 1}" ${pagina >= ultima ? html`disabled` : ''}>Próxima${ic('chev')}</button></nav>` : ''}`);
    destino.querySelectorAll('[data-pagina]').forEach((b) => b.addEventListener('click', () => carregarConsulta(detalhe, Number(b.dataset.pagina))));
    ligarSituacao(detalhe);
  };
  const ligarSituacao = (detalhe) => {
    const s = detalhe.querySelector('[data-ref=situacao]');
    if (s) s.addEventListener('change', () => carregarConsulta(detalhe, 1));
  };

  document.querySelectorAll('#fq select').forEach((s) => s.addEventListener('change', atualizarPainel));
  document.getElementById('fq').addEventListener('submit', (e) => { e.preventDefault(); atualizarPainel(); });
  document.getElementById('fq-limpar').addEventListener('click', () => {
    document.querySelectorAll('#fq select').forEach((s) => { s.value = ''; });
    atualizarPainel();
  });
  document.querySelectorAll('#q-consultas details').forEach((d) => d.addEventListener('toggle', () => { if (d.open) carregarConsulta(d, 1); }));
  if (veLog) {
    document.querySelectorAll('#fp [data-periodo]').forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault();
      periodo.tipo = a.dataset.periodo;
      document.querySelectorAll('#fp [data-periodo]').forEach((b) => { b.classList.toggle('on', b === a); b.setAttribute('aria-pressed', String(b === a)); });
      document.querySelectorAll('#fp [data-personalizado]').forEach((el) => { el.hidden = periodo.tipo !== 'personalizado'; });
      if (periodo.tipo !== 'personalizado') atualizarLinha();
    }));
    document.getElementById('fp').addEventListener('submit', (e) => {
      e.preventDefault();
      periodo.de = document.getElementById('fp-de').value;
      periodo.ate = document.getElementById('fp-ate').value;
      atualizarLinha();
    });
  }
  await Promise.all([atualizarPainel(), atualizarLinha()]);
}

function desenharIndicadores(alvo, resumo, inventario, alteracoes) {
  if (resumo.status === 'rejected') { montar(alvo, erro(resumo.reason)); return; }
  const r = resumo.value;
  const total = r.unidades.total;
  const semCnes = r.qualidade.sem_cnes;
  const pctSemCnes = total ? (semCnes / total) * 100 : 0;
  let medias = figura('medias', '—', 'Média por unidade', 'Inventário indisponível.');
  if (inventario.status === 'fulfilled') {
    const linhas = inventario.value.itens;
    const n = linhas.length;
    const servicos = n ? linhas.reduce((s, u) => s + u.service_count, 0) / n : 0;
    const equipamentos = n ? linhas.reduce((s, u) => s + u.equipment_count, 0) / n : 0;
    medias = figura('medias', n ? numero(servicos, 2) : '—', 'Serviços por unidade (média)',
      n ? `${numero(equipamentos, 2)} equipamentos por unidade · média sobre ${n} unidades` : 'Nenhuma unidade no filtro.',
      html`data-media-servicos="${servicos}" data-media-equipamentos="${equipamentos}" data-n="${n}"`);
  }
  let ritmo = figura('ritmo', '—', 'Ritmo de alterações', 'Consulta indisponível.');
  if (alteracoes.status === 'fulfilled') {
    const s7 = alteracoes.value.reduce((s, a) => s + a.last_7_days, 0);
    const s30 = alteracoes.value.reduce((s, a) => s + a.last_30_days, 0);
    const r7 = s7 / 7;
    const r30 = s30 / 30;
    const comparacao = Math.abs(r7 - r30) < 1e-9 ? 'igual ao' : r7 > r30 ? 'acima do' : 'abaixo do';
    ritmo = figura('ritmo', `${numero(r7, 2)}/dia`, 'Alterações por dia (7 dias)',
      `${numero(r30, 2)}/dia em 30 dias: ritmo ${comparacao} mês (${s7} e ${s30} alterações)`,
      html`data-r7="${r7}" data-r30="${r30}"`);
  }
  montar(alvo, html`<div class="figures" data-ref="indicadores">
    ${figura('total', total, 'Unidades no filtro', 'no seu escopo de acesso', html`data-valor="${total}"`)}
    ${figura('sem-cnes', semCnes, 'Unidades sem CNES', `${numero(pctSemCnes, 1)}% das ${total} unidades`, html`data-valor="${semCnes}"`)}
    ${medias}${ritmo}</div>`);
}

function desenharGraficos(alvo, { inventario, cnes, equipamentos, alteracoes, tiposDeEquipamento }) {
  const falhou = (resultado) => html`<figure class="viz">${erro(resultado.reason)}</figure>`;
  const partes = [];

  if (inventario.status === 'fulfilled') {
    const linhas = inventario.value.itens;
    const fatias = SITUACOES.map((s) => ({ ...s, valor: linhas.filter((u) => u.registration_status === s.chave).length }));
    partes.push(linhas.length
      ? rosca({ ref: 'grafico-situacao', titulo: 'Situação cadastral das unidades', subtitulo: 'Calculada no banco por fn_registration_status (vw_unit_inventory)', fatias, rotuloTotal: 'unidades' })
      : html`<figure class="viz" data-ref="grafico-situacao"><figcaption><b>Situação cadastral das unidades</b></figcaption>${vazio('Nenhuma unidade no filtro.')}</figure>`);
  } else partes.push(falhou(inventario));

  if (cnes.status === 'fulfilled') {
    const linhas = cnes.value.itens;
    partes.push(linhas.length
      ? barras({
        ref: 'grafico-cnes', titulo: 'Distritos com mais unidades sem CNES que a rede',
        subtitulo: 'Percentual de unidades sem CNES (subconsulta no HAVING)',
        itens: linhas.map((d) => ({ rotulo: d.district_name, valor: d.percent_without_cnes })),
        referencia: { rotulo: 'Percentual da rede', valor: linhas[0].network_percent_without_cnes },
        formato: (v) => `${numero(v, 2)}%`, rotuloValor: '% sem CNES',
      })
      : html`<figure class="viz" data-ref="grafico-cnes"><figcaption><b>Distritos com mais unidades sem CNES que a rede</b></figcaption>${vazio('Nenhum distrito acima do percentual da rede neste filtro.')}</figure>`);
  } else partes.push(falhou(cnes));

  if (alteracoes.status === 'fulfilled') {
    const linhas = alteracoes.value;
    partes.push(linhas.length
      ? barrasAgrupadas({
        ref: 'grafico-alteracoes', titulo: 'Alterações por distrito', subtitulo: 'Últimos 7 e 30 dias (vw_unit_history)',
        categorias: linhas.map((a) => a.district_name),
        series: [
          { nome: 'Últimos 7 dias', cor: CORES[0], valores: linhas.map((a) => a.last_7_days) },
          { nome: 'Últimos 30 dias', cor: CORES[1], valores: linhas.map((a) => a.last_30_days) },
        ],
      })
      : html`<figure class="viz" data-ref="grafico-alteracoes"><figcaption><b>Alterações por distrito</b></figcaption>${vazio('Nenhuma alteração nos últimos 30 dias.')}</figure>`);
  } else partes.push(falhou(alteracoes));

  if (equipamentos.status === 'fulfilled') {
    const linhas = equipamentos.value;
    // A cor segue o tipo (ordem fixa da tabela de referência), não a posição no resultado.
    const ordem = [...tiposDeEquipamento.values()].sort((a, b) => a.id - b.id).map((t) => t.codigo);
    // Os 5 primeiros tipos têm cor própria e fixa; os demais somam em "Outros tipos" (sem repetir cor).
    const presentes = [...new Set(linhas.map((l) => l.equipment_type_code))];
    const proprios = ordem.slice(0, CORES.length).filter((c) => presentes.includes(c));
    const outros = presentes.filter((c) => !proprios.includes(c));
    const distritos = [...new Set(linhas.map((l) => l.district_name))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
    const soma = (codigos, distrito) => linhas.filter((l) => codigos.includes(l.equipment_type_code) && l.district_name === distrito).reduce((s, l) => s + l.equipment_count, 0);
    const series = proprios.map((c) => ({
      nome: linhas.find((l) => l.equipment_type_code === c).equipment_type_name,
      cor: CORES[ordem.indexOf(c)],
      valores: distritos.map((d) => soma([c], d)),
    }));
    if (outros.length) series.push({ nome: 'Outros tipos', cor: COR_OUTROS, valores: distritos.map((d) => soma(outros, d)) });
    partes.push(linhas.length
      ? barrasEmpilhadas({ ref: 'grafico-equipamentos', titulo: 'Equipamentos por tipo e distrito', subtitulo: 'Cadastros de equipamento (JOIN de cinco tabelas)', categorias: distritos, series })
      : html`<figure class="viz" data-ref="grafico-equipamentos"><figcaption><b>Equipamentos por tipo e distrito</b></figcaption>${vazio('Nenhum equipamento no filtro.')}</figure>`);
  } else partes.push(falhou(equipamentos));

  montar(alvo, html`${partes}`);
}
