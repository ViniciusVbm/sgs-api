import { html, montar } from '../html.js';
import { chamar } from '../api.js';
import { ic } from '../ui/icone.js';
import { carregando, erro, vazio, emDesenvolvimento } from '../ui/estado.js';
import { fmtDataHora, fmtDataHoraSegundos, fmtAuditoria, fmtCep, resultadoDoEvento } from '../ui/format.js';
import { carregarReferencia, ROTULO_DO_STATUS } from '../referencias.js';
import { inicioDoDia, fimDoDia, mudanca, paginacao } from './historico.js';
import { abrirModal, fecharModal } from '../ui/modal.js';
import { toast } from '../ui/toast.js';
import { campo, lerFormulario, alterados, mostrarErros, limparErros, marcarErro } from '../ui/form.js';
import { camposDaUnidade, lerUnidade, conferirObrigatorios, alteracoesDaUnidade, valorLegivel, marcarCamposEstruturais, ROTULOS } from '../formUnidade.js';

// Ficha da unidade (spec 012, T8 parte A: R6.1, R6.2; design § Ficha mínima).
// Dados de GET /unidades/{id} (guarda o ETag), serviços com inclusão, alteração e remoção (T10), histórico da
// view vw_unit_history (GET /unidades/{id}/historico) só quando algum escopo de auditoria:read
// cobre a unidade, e a aba de aparelhos "em desenvolvimento" (R9.1, DF1).

const ABAS = { dados: 'Dados', servicos: 'Serviços', historico: 'Histórico', equipamentos: 'Equipamentos' };
const TAMANHO = 20;
const ACOES = {
  'unidade.criada': 'Unidade cadastrada',
  'unidade.atualizada': 'Dados alterados',
  'unidade.desativada': 'Unidade desativada',
  'unidade.servico_adicionado': 'Serviço incluído',
  'unidade.servico_alterado': 'Serviço alterado',
  'unidade.servico_removido': 'Serviço removido',
  'unidade.equipamento_adicionado': 'Equipamento incluído',
  'unidade.equipamento_alterado': 'Equipamento alterado',
  'unidade.equipamento_removido': 'Equipamento removido',
  'operacao.falhou': 'Tentativa sem sucesso',
};

// Resultado do evento no histórico (spec 013, R8.4); os anteriores à 013 saem "não registrado".
const chipDeResultado = (e) => {
  const r = resultadoDoEvento(e.resultado, e.resultado_categoria);
  return html`<span class="chip ${r.classe}" data-ref="resultado" data-resultado="${r.valor}">${r.rotulo}</span>`;
};

// Campos de referência da auditoria (nomes do banco) e a tabela que traduz o id para o nome.
const REFERENCIA_DO_CAMPO = { unit_type_id: 'tipos-unidade', district_id: 'distritos', service_type_id: 'tipos-servico' };
const vazioNosDois = (m) => (m.de === null || m.de === undefined) && (m.para === null || m.para === undefined);
const comNome = (m, referencias) => {
  const mapa = referencias[REFERENCIA_DO_CAMPO[m.campo]];
  const nome = (v) => (mapa && v !== null && v !== undefined && mapa.has(String(v)) ? `${mapa.get(String(v)).nome} (${v})` : v);
  return { ...m, de: nome(m.de), para: nome(m.para) };
};

const semValor = (v) => (v === null || v === undefined || v === '' ? html`<span class="muted">—</span>` : v);
const item = (rotulo, valor, ref = '') => html`<div ${ref ? html`data-ref="${ref}"` : ''}><dt>${rotulo}</dt><dd>${semValor(valor)}</dd></div>`;

function horario(valor) {
  if (!valor || typeof valor !== 'object' || !Object.keys(valor).length) return '';
  return Object.entries(valor).map(([dia, faixa]) => `${dia}: ${typeof faixa === 'object' ? JSON.stringify(faixa) : faixa}`).join(' · ');
}

// `aviso`: resultado da desativação que acabou de acontecer (T25), mostrado depois da recarga.
export async function telaUnidade(alvo, perfil, params, aviso = null) {
  const id = params.id;
  montar(alvo, carregando('Abrindo a ficha…'));
  let unidade; let etag; let tipos; let distritos; let areas;
  try {
    [{ dados: unidade, etag }, tipos, distritos, areas] = await Promise.all([
      chamar('GET', `/unidades/${encodeURIComponent(id)}`),
      ...['tipos-unidade', 'distritos', 'areas-tecnicas'].map(carregarReferencia),
    ]);
  } catch (falha) {
    document.title = 'Unidade — SGS Recife';
    montar(alvo, falha.status === 404
      ? html`<a class="crumb" href="#/unidades">${ic('back')}Unidades</a>
        <div class="empty" data-estado="nao-encontrada" data-status="404"><b>Unidade não encontrada.</b><span>${falha.detail}</span></div>`
      : html`<a class="crumb" href="#/unidades">${ic('back')}Unidades</a>${erro(falha)}`);
    return;
  }
  document.title = `${unidade.nome} — SGS Recife`;
  const tipo = tipos.get(String(unidade.tipo_unidade_id));
  const areaId = tipo ? tipo.area_tecnica_id : null;
  const area = areaId ? areas.get(String(areaId)) : null;
  const distrito = distritos.get(String(unidade.distrito_id));
  const veHistorico = perfil.cobreUnidade('auditoria:read', { unidadeId: unidade.id, distritoId: unidade.distrito_id, areaId });
  const abas = Object.keys(ABAS).filter((a) => a !== 'historico' || veHistorico);
  const aba = abas.includes(params.aba) ? params.aba : 'dados';
  if (params.aba && params.aba !== aba) history.replaceState(null, '', `#/unidade/${encodeURIComponent(unidade.id)}`);
  const base = `#/unidade/${encodeURIComponent(unidade.id)}`;
  // R7.7: só o escopo global de unidade:deactivate (o Gestor de Dados) e só se a unidade não está inativa.
  const podeDesativar = perfil.global('unidade:deactivate') && unidade.status !== 'inativa';
  // R7.1, R7.4: só o escopo global de unidade:update edita; quem só propõe vê o botão desabilitado.
  const podeEditar = perfil.global('unidade:update');
  const soPropoe = !podeEditar && perfil.tem('alteracao:propor');

  montar(alvo, html`
    <div data-ref="ficha" data-unidade="${unidade.id}" data-etag="${etag || ''}" data-versao="${unidade.versao}">
    ${perfil.deUnidade ? '' : html`<a class="crumb" href="#/unidades">${ic('back')}Unidades</a>`}
    <div class="unit-head"><div>
      <h1 data-ref="nome-unidade">${unidade.nome}</h1>
      <div class="chips">
        <span class="chip ${unidade.status === 'ativa' ? 'ok' : 'warn'}" data-ref="status">${ROTULO_DO_STATUS[unidade.status] || unidade.status}</span>
        <span class="chip" data-ref="cnes">${unidade.cnes ? `CNES ${unidade.cnes}` : 'Sem CNES'}</span>
        ${unidade.pendencias ? html`<span class="chip warn" data-ref="pendencias">${unidade.pendencias} pendência${unidade.pendencias > 1 ? 's' : ''}</span>` : ''}
      </div></div>
      <div class="versao" data-ref="versao-bloco">
        <div><span class="muted">Versão</span> <b data-ref="versao">${unidade.versao}</b></div>
        <div><span class="muted">Atualizado em</span> <b data-ref="atualizado-em" data-iso="${unidade.atualizado_em}">${comSegundos(unidade.atualizado_em)}</b></div>
        ${podeEditar || soPropoe || podeDesativar ? html`<div class="acoes-ficha">
          ${podeEditar ? html`<button class="btn btn-primary btn-sm" type="button" id="editar" data-ref="editar">${ic('edit')}Editar ficha</button>` : ''}
          ${soPropoe ? html`<button class="btn btn-line btn-sm" type="button" disabled aria-disabled="true" data-ref="propor" data-estado="em-desenvolvimento" title="A proposta de alteração depende da spec de solicitações (DF2, PF-01).">${ic('send')}Propor alteração (em desenvolvimento)</button>` : ''}
          ${podeDesativar ? html`<button class="btn btn-danger btn-sm" type="button" id="desativar" data-ref="desativar">${ic('x')}Desativar unidade</button>` : ''}
        </div>` : ''}
      </div></div>
    ${aviso ? (aviso.tipo === 'editada' || aviso.tipo === 'conflito' ? avisoDaEdicao(aviso) : avisoDaDesativacao(aviso, unidade, perfil)) : ''}
    <section class="panel">
      <nav class="tabs" aria-label="Seções da ficha">${abas.map((a) => html`<a href="${a === 'dados' ? base : `${base}/${a}`}" class="${a === aba ? 'on' : ''}" ${a === aba ? html`aria-current="page"` : ''} data-aba="${a}">${ABAS[a]}</a>`)}</nav>
      <div class="panel-b" id="u-corpo"></div>
    </section></div>`);

  if (podeDesativar) document.getElementById('desativar').addEventListener('click', () => abrirDesativacao(alvo, perfil, params, unidade));
  if (podeEditar) document.getElementById('editar').addEventListener('click', () => abrirEdicao(alvo, perfil, params, unidade, etag, { tipos, distritos }));
  const corpo = document.getElementById('u-corpo');
  if (aba === 'dados') abaDados(corpo, unidade, { tipo, area, distrito });
  else if (aba === 'servicos') await abaServicos(corpo, unidade, perfil);
  else if (aba === 'historico') await abaHistorico(corpo, unidade);
  else montar(corpo, emDesenvolvimento('Equipamentos (aparelhos)', 'O inventário de aparelhos depende da decisão DF1 e da spec de infraestrutura; equipamentos de saúde não são mostrados aqui (R9.1).'));
}

// Desativação pela procedure sp_deactivate_unit (R7.7; 006/R4, 011/R6.2 a R6.4). A regra é do
// backend: a API recusa motivo inválido (422), quem não tem a permissão (403) e unidade inexistente
// (404), e é idempotente para unidade já inativa. A tela só confirma, pede o motivo e, antes de
// enviar, relê a unidade para avisar se outra pessoa acabou de desativá-la.
function abrirDesativacao(alvo, perfil, params, unidade) {
  const caixa = abrirModal(html`<form id="fd" novalidate>
    <div class="modal-h"><h2>Desativar unidade</h2><p>${unidade.nome}</p></div>
    <div class="modal-b">
      <div class="banner info" data-ref="nao-e-exclusao">${ic('info')}<p><b>Desativar não é excluir.</b> A unidade continua no cadastro, no histórico e nos relatórios, com a situação "Inativa". O banco executa o procedimento <code>sp_deactivate_unit</code>, que trava a ficha durante a operação; a versão sobe pelo trigger de versão.</p></div>
      ${campo({ nome: 'motivo', rotulo: 'Motivo da desativação', obrigatorio: true, max: 500, ajuda: 'De 3 a 500 caracteres. Fica registrado na trilha de auditoria.' })}
      <p class="fld-err" id="fd-geral" role="alert"></p></div>
    <div class="modal-f"><button class="btn btn-line" type="button" id="fd-cancelar">Cancelar</button>
      <button class="btn btn-danger" type="submit">Desativar unidade</button></div></form>`, { rotulo: 'Desativar unidade' });
  const form = caixa.querySelector('#fd');
  caixa.querySelector('#fd-cancelar').addEventListener('click', fecharModal);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    limparErros(form);
    const geral = caixa.querySelector('#fd-geral');
    geral.textContent = '';
    const { motivo } = lerFormulario(form);
    if (motivo.length < 3) { marcarErro(form, 'motivo', 'Informe o motivo, com pelo menos 3 caracteres.'); return; }
    const botao = form.querySelector('button[type=submit]');
    botao.disabled = true;
    const caminho = `/unidades/${encodeURIComponent(unidade.id)}`;
    let atual;
    let resposta;
    try {
      ({ dados: atual } = await chamar('GET', caminho));
      if (atual.status !== 'inativa') resposta = await chamar('POST', `${caminho}/desativar`, { corpo: { motivo } });
    } catch (falha) {
      botao.disabled = false;
      if (!mostrarErros(form, falha)) geral.textContent = falha.status === 403 ? 'Você não tem permissão para desativar esta unidade.' : falha.detail;
      return;
    }
    fecharModal();
    if (!resposta) {
      toast('ok', 'A unidade já estava inativa.', 'Nada foi enviado.');
      await telaUnidade(alvo, perfil, params, { tipo: 'ja-inativa' });
      return;
    }
    toast('ok', 'Unidade desativada.');
    await telaUnidade(alvo, perfil, params, {
      tipo: 'desativada', motivo, antes: atual, depois: resposta.dados,
    });
  });
}

// Edição da ficha (R7.1, R7.2): formulário → diff de confirmação → PATCH com If-Match da versão
// lida, só com os campos alterados. A API decide: 412 (versão mudou), 422 (campos), 409 (CNES ou
// nome repetido, com a unidade existente) e 403 (campos estruturais fora do escopo).
function abrirEdicao(alvo, perfil, params, unidade, etag, refs) {
  const caixa = abrirModal(html`<form id="fe" novalidate>
    <div class="modal-h"><h2>Editar ficha</h2><p>Versão ${unidade.versao}. Só os campos alterados são enviados, com a versão lida (If-Match).</p></div>
    <div class="modal-b"><div id="fe-campos">${camposDaUnidade(unidade, refs, { edicao: true })}</div>
      <div id="fe-diff" hidden></div>
      <div class="err-summary" id="fe-geral" role="alert" hidden></div></div>
    <div class="modal-f"><button class="btn btn-line" type="button" id="fe-cancelar">Cancelar</button>
      <button class="btn btn-line" type="button" id="fe-voltar" hidden>${ic('back')}Voltar e corrigir</button>
      <button class="btn btn-primary" type="submit" id="fe-enviar">Revisar alterações</button></div></form>`, { rotulo: 'Editar ficha' });
  const form = caixa.querySelector('#fe');
  const camposEl = caixa.querySelector('#fe-campos');
  const diffEl = caixa.querySelector('#fe-diff');
  const geral = caixa.querySelector('#fe-geral');
  const enviar = caixa.querySelector('#fe-enviar');
  const voltar = caixa.querySelector('#fe-voltar');
  let corpo = null;
  const passoFormulario = () => {
    corpo = null;
    camposEl.hidden = false; diffEl.hidden = true; voltar.hidden = true;
    enviar.textContent = 'Revisar alterações';
    enviar.disabled = false;
  };
  const mostrarGeral = (conteudo) => { geral.hidden = false; montar(geral, conteudo); };
  caixa.querySelector('#fe-cancelar').addEventListener('click', fecharModal);
  voltar.addEventListener('click', passoFormulario);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    geral.hidden = true;
    if (!corpo) {
      limparErros(form);
      const dados = lerUnidade(form);
      if (!conferirObrigatorios(form, dados)) return;
      corpo = alteracoesDaUnidade(unidade, dados);
      if (!Object.keys(corpo).length) { fecharModal(); toast('ok', 'Nada a alterar.'); return; }
      montar(diffEl, html`<p class="sec-t">Confira as alterações antes de salvar</p><div class="tbl-wrap"><table data-ref="diff">
        <thead><tr><th>Campo</th><th>Antes</th><th>Depois</th></tr></thead>
        <tbody>${Object.entries(corpo).map(([nome, valor]) => html`<tr data-campo-diff="${nome}"><td>${ROTULOS[nome] || nome}</td>
          <td class="from">${valorLegivel(nome, unidade[nome], refs)}</td><td class="to">${valorLegivel(nome, valor, refs)}</td></tr>`)}</tbody></table></div>`);
      camposEl.hidden = true; diffEl.hidden = false; voltar.hidden = false;
      enviar.textContent = 'Confirmar e salvar';
      return;
    }
    enviar.disabled = true;
    let resposta;
    try {
      resposta = await chamar('PATCH', `/unidades/${encodeURIComponent(unidade.id)}`, { corpo, cabecalhos: { 'If-Match': etag } });
    } catch (falha) {
      if (falha.status === 412) {
        fecharModal();
        toast('err', 'A ficha mudou em outra sessão.', 'Nada foi gravado; confira os dados atuais.');
        await telaUnidade(alvo, perfil, params, { tipo: 'conflito', campos: Object.keys(corpo), versaoLida: unidade.versao, versaoAtual: falha.problema?.versao_atual });
        return;
      }
      passoFormulario();
      const nosCampos = mostrarErros(form, falha) || marcarCamposEstruturais(form, falha);
      const existente = falha.status === 409 ? falha.problema?.unidade_existente_id : null;
      if (!nosCampos || existente) {
        mostrarGeral(html`<b>${ic('alert')}${falha.status === 403 && !falha.problema?.campos_estruturais ? 'Você não tem permissão para esta alteração.' : falha.detail}</b>
          ${existente ? html`<p><a href="#/unidade/${encodeURIComponent(existente)}" data-ref="unidade-existente">Abrir a unidade que já tem estes dados</a></p>` : ''}`);
      }
      return;
    }
    fecharModal();
    toast('ok', 'Ficha atualizada.');
    await telaUnidade(alvo, perfil, params, { tipo: 'editada', antes: unidade, depois: resposta.dados, campos: Object.keys(corpo) });
  });
}

function avisoDaEdicao(aviso) {
  const nomes = aviso.campos.map((c) => ROTULOS[c] || c).join(', ');
  if (aviso.tipo === 'conflito') {
    return html`<div class="banner wait" data-ref="aviso-edicao" data-tipo="conflito" data-versao-lida="${aviso.versaoLida}" data-versao-atual="${aviso.versaoAtual ?? ''}">${ic('alert')}<p>
      <b>A ficha foi alterada em outra sessão</b> depois que você a abriu (você leu a versão ${aviso.versaoLida}${aviso.versaoAtual ? `; a atual é a ${aviso.versaoAtual}` : ''}).
      A API recusou a gravação (HTTP 412) e <b>nada foi sobrescrito</b>. A ficha abaixo já é a atual: confira e edite de novo os campos que você tinha alterado (${nomes}).</p></div>`;
  }
  const { antes, depois } = aviso;
  return html`<div class="banner ok" data-ref="aviso-edicao" data-tipo="editada"
      data-versao-antes="${antes.versao}" data-versao-depois="${depois.versao}"
      data-atualizado-antes="${antes.atualizado_em}" data-atualizado-depois="${depois.atualizado_em}">${ic('check')}<p>
    <b>Ficha atualizada.</b> Campos alterados: ${nomes}. Versão ${antes.versao} → ${depois.versao} e atualizado em
    ${comSegundos(antes.atualizado_em)} → ${comSegundos(depois.atualizado_em)}, gravados pelo banco (trigger <code>trg_health_units_version</code>, que sobe a versão e a data só quando algo muda de fato).</p></div>`;
}

function avisoDaDesativacao(aviso, unidade, perfil) {
  if (aviso.tipo === 'ja-inativa') {
    return html`<div class="banner info" data-ref="aviso-desativacao" data-tipo="ja-inativa">${ic('info')}<p><b>A unidade já estava inativa</b> quando você confirmou (outra pessoa ou sessão a desativou). Nada foi enviado nem alterado.</p></div>`;
  }
  const { antes, depois } = aviso;
  const base = `#/unidade/${encodeURIComponent(unidade.id)}`;
  return html`<div class="banner ok" data-ref="aviso-desativacao" data-tipo="desativada"
      data-versao-antes="${antes.versao}" data-versao-depois="${depois.versao}"
      data-atualizado-antes="${antes.atualizado_em}" data-atualizado-depois="${depois.atualizado_em}">${ic('check')}<p>
    <b>Unidade desativada pelo procedimento <code>sp_deactivate_unit</code>.</b> Situação: ${ROTULO_DO_STATUS[antes.status] || antes.status} → Inativa;
    versão ${antes.versao} → ${depois.versao} (trigger de versão); atualizado em ${comSegundos(antes.atualizado_em)} → ${comSegundos(depois.atualizado_em)}.
    A unidade não foi apagada. Motivo registrado na auditoria: "${aviso.motivo}".
    <a href="${base}/historico" data-ref="ver-historico">Ver no histórico</a>${perfil.global('auditoria:read') ? html` · <a href="#/historico?aba=banco&amp;tabela=health_units" data-ref="ver-log">ver no log do banco</a>` : ''}</p></div>`;
}

function abaDados(corpo, u, { tipo, area, distrito }) {
  const coordenadas = u.latitude !== null && u.longitude !== null ? `${u.latitude}, ${u.longitude}` : '';
  montar(corpo, html`
    <div class="sec"><h2 class="sec-t">Identificação</h2><dl class="dl">
      ${item('Nome', u.nome)}
      ${item('CNES', u.cnes || (u.cnes_pendente ? 'pendente' : ''), 'dado-cnes')}
      ${item('Tipo de unidade', tipo ? tipo.nome : '', 'dado-tipo')}
      ${item('Área técnica', area ? area.nome : '', 'dado-area')}
      ${item('Distrito sanitário', distrito ? distrito.nome : '', 'dado-distrito')}
      ${item('Situação', ROTULO_DO_STATUS[u.status] || u.status, 'dado-status')}
    </dl></div>
    <div class="sec"><h2 class="sec-t">Endereço e contato</h2><dl class="dl">
      ${item('Endereço', u.endereco)}
      ${item('Bairro', u.bairro)}
      ${item('CEP', fmtCep(u.cep))}
      ${item('Telefone', u.telefone)}
      ${item('Gestor(a) da unidade', u.nome_gestor)}
      ${item('Coordenadas', coordenadas)}
      ${item('Horário de funcionamento', horario(u.horario_funcionamento))}
      ${item('Pendências de cadastro', String(u.pendencias))}
    </dl></div>
    <div class="sec"><h2 class="sec-t">Controle de versão</h2><dl class="dl">
      ${item('Versão', String(u.versao), 'dado-versao')}
      ${item('Atualizado em', fmtDataHora(u.atualizado_em))}
      ${item('Cadastrado em', fmtDataHora(u.criado_em))}
    </dl>
    <p class="hint" data-ref="origem-versao">A versão sobe a cada alteração real da ficha, inclusive feita fora da aplicação, pelo trigger <code>trg_health_units_version</code>; "Atualizado em" também é mantido pelo banco. A mesma versão vai no cabeçalho <code>ETag</code>, que protege a edição contra gravações simultâneas.</p></div>`);
}

// Data e hora com segundos: a mudança de `updated_at` pelo trigger fica visível mesmo no mesmo minuto.
const comSegundos = fmtDataHoraSegundos;
const SITUACAO_DO_SERVICO = { ativo: 'Ativo', inativo: 'Inativo' };

// Serviços da unidade (R8.1, R8.2). Só o escopo global de servico:write vê os controles (R7.4,
// R8.1); a API confere de novo. "Desativar" é o PATCH de status; "Remover" é o DELETE do R8.1,
// que o modelo permite (nenhuma tabela aponta para services). O vínculo com equipamento não é
// editável (DF1). A API de serviços não usa If-Match: a última gravação vale.
async function abaServicos(corpo, u, perfil) {
  const podeEscrever = perfil.global('servico:write');
  const base = `/unidades/${encodeURIComponent(u.id)}/servicos`;
  let servicos = [];
  let tipos = new Map();
  let efeito = null; // {nome, antes, depois} do último PATCH, para mostrar o trigger trg_set_updated_at

  const carregar = async () => {
    montar(corpo, carregando('Buscando serviços…'));
    try {
      [{ dados: servicos }, tipos] = await Promise.all([chamar('GET', base), carregarReferencia('tipos-servico')]);
    } catch (falha) {
      montar(corpo, erro(falha));
      return;
    }
    const painelDoEfeito = efeito ? html`<div class="banner ok" data-ref="efeito-updated-at" data-antes="${efeito.antes}" data-depois="${efeito.depois}">${ic('check')}<p>
      <b>${efeito.nome}: alterado.</b> "Atualizado em" passou de <b>${comSegundos(efeito.antes)}</b> para <b>${comSegundos(efeito.depois)}</b>,
      gravado pelo próprio banco (trigger <code>trg_set_updated_at</code>), sem a aplicação enviar a data.</p></div>` : '';
    montar(corpo, html`${painelDoEfeito}
      <div class="list-meta consulta-meta"><span data-ref="total-servicos" data-total="${servicos.length}">${servicos.length} serviço${servicos.length === 1 ? '' : 's'}</span>
        ${podeEscrever ? html`<button class="btn btn-primary btn-sm" type="button" id="incluir-servico">${ic('plus')}Incluir serviço</button>` : ''}</div>
      ${servicos.length ? html`<div class="tbl-wrap"><table><thead><tr><th>Serviço</th><th>Tipo</th><th>No CNES</th><th>Situação</th><th>Equipamento</th><th>Atualizado em</th>${podeEscrever ? html`<th class="acoes">Ações</th>` : ''}</tr></thead>
        <tbody>${servicos.map((s) => html`<tr data-servico="${s.id}">
          <td data-ref="servico-nome">${s.nome}</td><td data-ref="servico-tipo">${tipos.get(String(s.tipo_servico_id))?.nome || '—'}</td>
          <td><span class="chip ${s.no_cnes ? 'ok' : 'warn'}" data-ref="servico-cnes">${s.no_cnes ? 'Sim' : 'Não'}</span></td>
          <td data-ref="servico-status">${SITUACAO_DO_SERVICO[s.status] || s.status}</td>
          <td>${s.equipamento_id ? 'vinculado' : '—'}</td>
          <td data-ref="servico-atualizado" data-iso="${s.atualizado_em}">${comSegundos(s.atualizado_em)}</td>
          ${podeEscrever ? html`<td class="acoes"><button class="btn btn-quiet btn-sm" type="button" data-editar-servico="${s.id}">${ic('edit')}Editar</button>
            <button class="btn btn-line btn-sm" type="button" data-situacao-servico="${s.id}">${s.status === 'ativo' ? html`${ic('x')}Desativar` : html`${ic('refresh')}Reativar`}</button>
            <button class="btn btn-quiet btn-sm" type="button" data-remover-servico="${s.id}">${ic('trash')}Remover</button></td>` : ''}</tr>`)}</tbody></table></div>`
    : vazio('Nenhum serviço cadastrado nesta unidade.')}`);
    if (!podeEscrever) return;
    const doId = (id) => servicos.find((s) => s.id === id);
    document.getElementById('incluir-servico').addEventListener('click', () => formulario());
    corpo.querySelectorAll('[data-editar-servico]').forEach((b) => b.addEventListener('click', () => formulario(doId(b.dataset.editarServico))));
    corpo.querySelectorAll('[data-situacao-servico]').forEach((b) => b.addEventListener('click', () => confirmar(doId(b.dataset.situacaoServico), 'situacao')));
    corpo.querySelectorAll('[data-remover-servico]').forEach((b) => b.addEventListener('click', () => confirmar(doId(b.dataset.removerServico), 'remover')));
  };

  // PATCH parcial: devolve o serviço gravado e registra o efeito do trigger em `updated_at`.
  const alterar = async (original, corpoDoPatch) => {
    const { dados } = await chamar('PATCH', `${base}/${encodeURIComponent(original.id)}`, { corpo: corpoDoPatch });
    efeito = { nome: dados.nome, antes: original.atualizado_em, depois: dados.atualizado_em };
    return dados;
  };

  const formulario = (original = null) => {
    const ativos = [...tipos.values()].filter((t) => t.ativo || (original && t.id === original.tipo_servico_id))
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
      .map((t) => ({ valor: t.id, rotulo: t.ativo ? t.nome : `${t.nome} (inativo)` }));
    const inicial = original
      ? { nome: original.nome, tipo_servico_id: String(original.tipo_servico_id), no_cnes: String(original.no_cnes), status: original.status }
      : { nome: '', tipo_servico_id: '', no_cnes: 'false', status: 'ativo' };
    const caixa = abrirModal(html`<form id="fs" novalidate>
      <div class="modal-h"><h2>${original ? 'Editar serviço' : 'Incluir serviço'}</h2><p>${u.nome}${original ? ' · só os campos alterados são enviados' : ''}</p></div>
      <div class="modal-b"><div class="grid">
        ${campo({ nome: 'nome', rotulo: 'Nome do serviço', valor: inicial.nome, obrigatorio: true, max: 200 })}
        ${campo({ nome: 'tipo_servico_id', rotulo: 'Tipo de serviço', valor: inicial.tipo_servico_id, obrigatorio: true, opcoes: ativos })}
        ${campo({ nome: 'no_cnes', rotulo: 'Consta no CNES?', valor: inicial.no_cnes, obrigatorio: true, opcoes: [{ valor: 'true', rotulo: 'Sim' }, { valor: 'false', rotulo: 'Não' }], vazio: '—' })}
        ${campo({ nome: 'status', rotulo: 'Situação', valor: inicial.status, obrigatorio: true, opcoes: [{ valor: 'ativo', rotulo: 'Ativo' }, { valor: 'inativo', rotulo: 'Inativo' }], vazio: '—' })}
      </div><p class="fld-err" id="fs-geral" role="alert"></p></div>
      <div class="modal-f"><button class="btn btn-line" type="button" id="fs-cancelar">Cancelar</button>
        <button class="btn btn-primary" type="submit">${original ? 'Salvar alterações' : 'Incluir'}</button></div></form>`, { rotulo: original ? 'Editar serviço' : 'Incluir serviço' });
    const form = caixa.querySelector('#fs');
    caixa.querySelector('#fs-cancelar').addEventListener('click', fecharModal);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      limparErros(form);
      const geral = caixa.querySelector('#fs-geral');
      geral.textContent = '';
      const dados = lerFormulario(form);
      const enviar = original ? alterados(inicial, dados) : { ...dados };
      if (original && !Object.keys(enviar).length) { fecharModal(); toast('ok', 'Nada a alterar.'); return; }
      // Tipos da API: id numérico e booleano; vazio vira null e a API responde 422 no campo.
      if ('tipo_servico_id' in enviar) enviar.tipo_servico_id = enviar.tipo_servico_id ? Number(enviar.tipo_servico_id) : null;
      if ('no_cnes' in enviar) enviar.no_cnes = enviar.no_cnes === '' ? null : enviar.no_cnes === 'true';
      if ('status' in enviar && enviar.status === '') enviar.status = null;
      const botao = form.querySelector('button[type=submit]');
      botao.disabled = true;
      try {
        if (original) await alterar(original, enviar);
        else await chamar('POST', base, { corpo: enviar });
      } catch (falha) {
        botao.disabled = false;
        if (!mostrarErros(form, falha)) geral.textContent = falha.status === 403 ? 'Você não tem permissão para esta ação.' : falha.detail;
        return;
      }
      fecharModal();
      toast('ok', original ? 'Serviço alterado.' : 'Serviço incluído.');
      if (!original) efeito = null;
      await carregar();
    });
  };

  const confirmar = (servico, acao) => {
    const remover = acao === 'remover';
    const desativar = servico.status === 'ativo';
    const titulo = remover ? 'Remover serviço' : desativar ? 'Desativar serviço' : 'Reativar serviço';
    const caixa = abrirModal(html`<div class="modal-h"><h2>${titulo}</h2><p>${servico.nome}</p></div>
      <div class="modal-b"><p>${remover
    ? 'O serviço é apagado do cadastro. Nenhum outro registro depende dele; a remoção fica na trilha de auditoria e no log do banco.'
    : desativar ? 'O serviço continua cadastrado, com a situação "Inativo".' : 'O serviço volta à situação "Ativo".'}</p>
        <p class="fld-err" id="cs-erro" role="alert"></p></div>
      <div class="modal-f"><button class="btn btn-line" type="button" id="cs-cancelar">Cancelar</button>
        <button class="btn ${remover || desativar ? 'btn-danger' : 'btn-primary'}" type="button" id="cs-confirmar">${remover ? 'Remover' : desativar ? 'Desativar' : 'Reativar'}</button></div>`, { rotulo: titulo });
    caixa.querySelector('#cs-cancelar').addEventListener('click', fecharModal);
    caixa.querySelector('#cs-confirmar').addEventListener('click', async (e) => {
      e.currentTarget.disabled = true;
      try {
        if (remover) {
          await chamar('DELETE', `${base}/${encodeURIComponent(servico.id)}`);
          efeito = null;
        } else {
          await alterar(servico, { status: desativar ? 'inativo' : 'ativo' });
        }
      } catch (falha) {
        caixa.querySelector('#cs-erro').textContent = falha.status === 403 ? 'Você não tem permissão para esta ação.' : falha.detail;
        caixa.querySelector('#cs-confirmar').disabled = false;
        return;
      }
      fecharModal();
      toast('ok', remover ? 'Serviço removido.' : desativar ? 'Serviço desativado.' : 'Serviço reativado.');
      await carregar();
    });
  };

  await carregar();
}

async function abaHistorico(corpo, u) {
  const f = { de: '', ate: '', autor: '', autorNome: '' };
  montar(corpo, html`
    <p class="hint" data-ref="origem-historico">Da view <code>vw_unit_history</code> (auditoria da unidade, de seus equipamentos e serviços), do mais recente para o mais antigo.</p>
    <form class="filters filtros-ficha" id="uh" aria-label="Filtros do histórico">
      <div class="fld"><label for="uh-de">De</label><input id="uh-de" type="date"></div>
      <div class="fld"><label for="uh-ate">Até (inclusive)</label><input id="uh-ate" type="date"></div>
      <button class="btn btn-line btn-sm" type="submit">Filtrar</button>
    </form>
    <div class="list-meta" id="uh-autor" hidden></div>
    <div id="uh-resultado"></div>`);
  const resultado = document.getElementById('uh-resultado');
  const caixaAutor = document.getElementById('uh-autor');
  const referencias = {};
  try {
    await Promise.all(Object.values(REFERENCIA_DO_CAMPO).map(async (t) => { referencias[t] = await carregarReferencia(t); }));
  } catch { /* sem os nomes, a tela mostra os ids, como a API devolve */ }
  const carregar = async (pagina) => {
    f.de = document.getElementById('uh-de').value;
    f.ate = document.getElementById('uh-ate').value;
    caixaAutor.hidden = !f.autor;
    montar(caixaAutor, f.autor ? html`<span>Autor: <b>${f.autorNome || f.autor}</b></span><button class="btn btn-quiet btn-sm" type="button" id="uh-sem-autor">${ic('x')}Todos os autores</button>` : html``);
    const limpar = document.getElementById('uh-sem-autor');
    if (limpar) limpar.addEventListener('click', () => { f.autor = ''; f.autorNome = ''; carregar(1); });
    const api = new URLSearchParams([['pagina', String(pagina)], ['tamanho', String(TAMANHO)]]);
    if (f.de) api.set('de', inicioDoDia(f.de));
    if (f.ate) api.set('ate', fimDoDia(f.ate));
    if (f.autor) api.set('autor', f.autor);
    montar(resultado, carregando('Buscando o histórico…'));
    let dados;
    try {
      ({ dados } = await chamar('GET', `/unidades/${encodeURIComponent(u.id)}/historico?${api}`));
    } catch (falha) {
      montar(resultado, erro(falha));
      return;
    }
    montar(resultado, dados.itens.length ? html`<ol class="timeline" data-ref="historico">${dados.itens.map((e) => html`<li data-evento="${e.id}">
        <span class="act-ic brand">${ic('history')}</span>
        <div><div class="what">${ACOES[e.acao] || e.acao}</div>
          <div class="when">${fmtAuditoria(e.quando)} · ${chipDeResultado(e)} · ${e.autor.id
    ? html`<button class="btn btn-quiet btn-sm" type="button" data-autor="${e.autor.id}" data-autor-nome="${e.autor.nome || ''}" title="Filtrar por este autor">${e.autor.nome || e.autor.id}</button>`
    : 'sistema'}${e.autor.papeis.length ? ` (${e.autor.papeis.join(', ')})` : ''}</div>
          ${e.metadados && e.metadados.motivo ? html`<p class="motivo" data-ref="motivo">Motivo: ${e.metadados.motivo}</p>` : ''}
          ${e.mudancas.some((m) => !vazioNosDois(m)) ? html`<ul class="changes">${e.mudancas.filter((m) => !vazioNosDois(m)).map((m) => comNome(m, referencias)).map((m) => mudanca(m.rotulo || m.campo, m.de, m.para))}</ul>` : ''}</div></li>`)}</ol>
      ${paginacao(pagina, dados.total)}`
    : html`${vazio(f.de || f.ate || f.autor ? 'Nenhuma alteração com estes filtros.' : 'Nenhuma alteração registrada para esta unidade.')}${paginacao(pagina, dados.total)}`);
    resultado.querySelectorAll('[data-pagina]').forEach((b) => b.addEventListener('click', () => carregar(Number(b.dataset.pagina))));
    resultado.querySelectorAll('[data-autor]').forEach((b) => b.addEventListener('click', () => { f.autor = b.dataset.autor; f.autorNome = b.dataset.autorNome; carregar(1); }));
  };
  document.getElementById('uh').addEventListener('submit', (e) => { e.preventDefault(); carregar(1); });
  await carregar(1);
}
