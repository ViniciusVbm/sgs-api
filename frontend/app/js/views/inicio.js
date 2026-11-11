import { html, montar } from '../html.js';
import { chamar } from '../api.js';
import { ic } from '../ui/icone.js';
import { carregando, erro, vazio, emDesenvolvimento } from '../ui/estado.js';
import { fmtDataHora } from '../ui/format.js';
import { ROTULO_DO_STATUS } from '../referencias.js';

// Início com os indicadores de GET /dashboard/resumo, no escopo de dashboard:read (spec 012, R4.1).

const saudacao = () => { const h = new Date().getHours(); return h < 12 ? 'Bom dia' : h < 18 ? 'Boa tarde' : 'Boa noite'; };

const barras = (itens, filtro) => {
  if (!itens.length) return vazio('Nenhuma unidade no seu escopo.');
  const maximo = Math.max(1, ...itens.map((i) => i.quantidade));
  return html`<div class="dist">${itens.map((i) => html`<a href="#/unidades?${filtro}=${encodeURIComponent(i.chave)}" data-ref="barra"><span>${i.rotulo}</span><span class="track" aria-hidden="true"><span style="width:${(i.quantidade / maximo) * 100}%"></span></span><b>${i.quantidade}</b></a>`)}</div>`;
};

const painel = (titulo, conteudo, extra = '') =>
  html`<section class="panel"><div class="panel-h"><div><h2>${titulo}</h2></div>${extra}</div><div class="panel-b">${conteudo}</div></section>`;

export async function telaInicio(alvo, perfil) {
  document.title = 'Início — SGS Recife';
  const cabecalho = html`<div class="page-head"><div><h1>${saudacao()}, ${String(perfil.me.nome).split(' ')[0]}.</h1>
    <p>Indicadores calculados pela API no seu escopo de acesso.</p></div>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      <a class="btn btn-line" href="#/qualidade" data-ref="painel-completo">${ic('shield')}Painel completo: gráficos e consultas</a>
      ${perfil.global('unidade:create') ? html`<a class="btn btn-primary" href="#/nova">${ic('plus')}Cadastrar unidade</a>` : ''}</div></div>`;
  montar(alvo, html`${cabecalho}${carregando()}`);
  let resumo;
  try {
    ({ dados: resumo } = await chamar('GET', '/dashboard/resumo'));
  } catch (falha) {
    montar(alvo, html`${cabecalho}${erro(falha)}`);
    return;
  }
  const u = resumo.unidades;
  const q = resumo.qualidade;
  const a = resumo.alteracoes;
  const porStatus = Object.entries(u.por_status).map(([chave, quantidade]) => ({ chave, rotulo: ROTULO_DO_STATUS[chave] || chave, quantidade }));
  montar(alvo, html`${cabecalho}
    <div class="figures" data-ref="indicadores">
      <a class="fig" href="#/unidades" data-ref="total"><div class="v">${u.total}</div><div class="l">Unidades cadastradas</div><div class="s">no seu escopo</div></a>
      <a class="fig warn" href="#/unidades?com_pendencias=true" data-ref="pendencias"><div class="v">${q.unidades_com_pendencias}</div><div class="l">Fichas com pendência</div><div class="s">${q.total_pendencias} pendências registradas</div></a>
      <div class="fig wait" data-ref="sem-cnes"><div class="v">${q.sem_cnes}</div><div class="l">Sem CNES</div><div class="s">${q.servicos_fora_cnes} serviços fora do CNES</div></div>
      <div class="fig ok" data-ref="alteracoes"><div class="v">${a.ultimos_7_dias}</div><div class="l">Alterações em 7 dias</div><div class="s">${a.ultimos_30_dias} em 30 dias</div></div>
    </div>
    <div class="cols">
      <div class="stack">
        ${painel('Atividade recente', a.recentes.length ? html`<div class="rows">${a.recentes.map((r) => html`
          <a class="row" href="#/unidade/${encodeURIComponent(r.unit_id)}" style="color:inherit;text-decoration:none"><span class="act-ic">${ic('history')}</span>
            <div class="grow"><div class="t">${r.unit_name}</div><div class="d">${r.action} — ${r.actor_name || 'sistema'}, ${fmtDataHora(r.occurred_at)}${r.district_name ? html` · ${r.district_name}` : ''}</div></div></a>`)}</div>`
          : vazio('Nenhuma alteração recente.'))}
        ${emDesenvolvimento('Solicitações pendentes e fichas com mais pendências', 'Dependem da API de solicitações e das regras da spec 007 (R4.2).')}
      </div>
      <div class="stack">
        ${painel('Unidades por distrito', barras(u.por_distrito, 'distrito'))}
        ${painel('Unidades por tipo', barras(u.por_tipo, 'tipo'))}
        ${painel('Unidades por área técnica', barras(u.por_area, 'area'))}
        ${painel('Unidades por situação', barras(porStatus, 'status'))}
      </div>
    </div>`);
}
