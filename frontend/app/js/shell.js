import { html, montar } from './html.js';
import { ic } from './ui/icone.js';
import { aplicarTema, temaAtual, alternarTema } from './ui/tema.js';
import { toast } from './ui/toast.js';
import { itensDoMenu, rotuloDoPapel } from './perms.js';

// Estrutura do protótipo: menu lateral, barra superior, sino e área de conteúdo (spec 012, R1.2, R3).

const iniciais = (nome) => String(nome || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();

function descricaoDoPerfil(p) {
  const primeira = [...(p.me.papeis || [])].sort((a, b) => a.papel.localeCompare(b.papel))[0];
  if (!primeira) return 'Sem papel atribuído';
  return rotuloDoPapel[primeira.papel] || primeira.papel;
}

export function desenharShell(perfil, chaveAtiva, { aoSair }) {
  const itens = itensDoMenu(perfil);
  const menu = itens.map((i) => (i[0] === 'sep' ? html`<div class="nav-sep"></div>` : html`<a href="${i[0]}" class="${i[3] === chaveAtiva ? 'on' : ''}" ${i[3] === chaveAtiva ? html`aria-current="page"` : ''} data-menu="${i[3]}" ${i[4] ? html`data-em-desenvolvimento` : ''}>${ic(i[1])}${i[2]}</a>`));
  const comBusca = perfil.tem('unidade:read') && !perfil.deUnidade;
  montar(document.getElementById('app'), html`
  <div class="shell">
    <aside class="side" id="side" aria-label="Menu principal">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true"><i style="background:var(--pref-blue)"></i><i style="background:var(--pref-green)"></i><i style="background:var(--pref-orange)"></i></div>
        <div><b>SGS Recife</b><small>Governança de dados da rede de saúde</small></div>
      </div>
      <nav class="nav">${menu}</nav>
      <div class="side-foot"><p style="margin:0 0 6px">${descricaoDoPerfil(perfil)}</p></div>
    </aside>
    <div class="main">
      <header class="top">
        <button class="icon-btn menu-btn" id="menuBtn" aria-label="Abrir menu">${ic('menu')}</button>
        ${comBusca ? html`<form class="top-search" id="topSearch" role="search">${ic('search')}<input id="topQ" type="search" placeholder="Buscar por nome ou CNES" aria-label="Buscar unidade"></form>` : html`<div></div>`}
        <div class="top-sp"></div>
        <button class="icon-btn" id="themeBtn"></button>
        <div style="position:relative">
          <button class="icon-btn" id="bellBtn" aria-label="Notificações (em desenvolvimento)" aria-haspopup="true">${ic('bell')}</button>
          <div id="bellPop"></div>
        </div>
        <div class="me">
          <span class="avatar" style="background:var(--brand)">${iniciais(perfil.me.nome)}</span>
          <div><b data-ref="nome">${perfil.me.nome}</b><small>${descricaoDoPerfil(perfil)}</small></div>
          <button class="icon-btn" id="logoutBtn" title="Sair" aria-label="Sair">${ic('logout')}</button>
        </div>
      </header>
      <main class="content" id="view"></main>
    </div>
  </div>`);
  aplicarTema(temaAtual());
  document.getElementById('themeBtn').addEventListener('click', alternarTema);
  document.getElementById('logoutBtn').addEventListener('click', aoSair);
  document.getElementById('menuBtn').addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('side').classList.toggle('open'); });
  // Sino visível para todos, sem contagem, até existir a API de notificações (R11.1).
  document.getElementById('bellBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    const caixa = document.getElementById('bellPop');
    if (caixa.firstChild) { montar(caixa, html``); return; }
    montar(caixa, html`<div class="pop" role="dialog" aria-label="Notificações"><div class="pop-h"><b>Notificações</b></div>
      <div class="pop-empty" data-estado="em-desenvolvimento">Notificações: em desenvolvimento. Ainda não há API de notificações.</div></div>`);
  });
  const busca = document.getElementById('topSearch');
  if (busca) {
    busca.addEventListener('submit', (e) => {
      e.preventDefault();
      location.hash = `#/unidades?q=${encodeURIComponent(document.getElementById('topQ').value.trim())}`;
    });
  }
  return document.getElementById('view');
}

export function fecharPopups() {
  const caixa = document.getElementById('bellPop');
  if (caixa && caixa.firstChild) montar(caixa, html``);
  document.getElementById('side')?.classList.remove('open');
}

export { toast };
