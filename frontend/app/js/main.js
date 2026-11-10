import { html, montar } from './html.js';
import { configurarApi, chamar } from './api.js';
import { tokenAtual, renovar, sair } from './auth.js';
import { rota, naoEncontrada as quandoNaoEncontrada, resolver, iniciarRoteador } from './router.js';
import { criarPerfil, inicioDoPerfil } from './perms.js';
import { desenharShell, fecharPopups } from './shell.js';
import { iniciarTema } from './ui/tema.js';
import { toast } from './ui/toast.js';
import { fecharModal } from './ui/modal.js';
import { carregando, erro } from './ui/estado.js';
import { mostrarLogin } from './views/login.js';
import { semAcesso, naoEncontrada, telaEmDesenvolvimento, telaEmImplantacao } from './views/basicas.js';

// Abertura (spec 012, design § Fluxo): refresh silencioso → /me → menu → rota.
let perfil = null;

configurarApi({
  token: tokenAtual,
  renovar,
  expirou: () => voltarAoLogin('Sua sessão expirou. Entre de novo.'),
});

function voltarAoLogin(aviso = '') {
  perfil = null;
  fecharModal();
  history.replaceState(null, '', location.pathname);
  mostrarLogin(abrirApp, aviso ? { erro: aviso } : {});
}

async function encerrar() {
  try { await sair(); } catch { /* a sessão local é descartada de qualquer forma (R2.6) */ }
  document.getElementById('toasts').replaceChildren();
  voltarAoLogin();
}

// Cada tela declara a chave do menu e a condição de acesso; sem permissão, "sem acesso" (R3.3).
function tela(chave, permitido, desenhar) {
  return (params, consulta) => {
    if (!perfil) return; // sem sessão, o login já está na tela
    fecharModal();
    fecharPopups();
    const alvo = desenharShell(perfil, chave, { aoSair: encerrar });
    if (!permitido(perfil, params)) { semAcesso(alvo); return; }
    desenhar(alvo, params, consulta);
    window.scrollTo(0, 0);
  };
}

const sempre = () => true;

function registrarRotas() {
  rota('inicio', tela('inicio', (p) => p.tem('dashboard:read'), (a) => telaEmImplantacao(a, 'Início', 'T6')));
  rota('unidades', tela('unidades', (p) => p.tem('unidade:read'), (a) => telaEmImplantacao(a, 'Unidades', 'T7')));
  rota('unidade/:id', tela('unidade', (p) => p.tem('unidade:read'), (a) => telaEmImplantacao(a, 'Ficha da unidade', 'T8')));
  rota('unidade/:id/:aba', tela('historico-unidade', (p) => p.tem('unidade:read'), (a) => telaEmImplantacao(a, 'Ficha da unidade', 'T8')));
  rota('nova', tela('nova', (p) => p.global('unidade:create') || p.tem('alteracao:propor'), (a) => {
    if (perfil.global('unidade:create')) telaEmImplantacao(a, 'Cadastrar unidade', 'T9');
    else telaEmDesenvolvimento(a, 'Solicitar cadastro', 'O cadastro por solicitação depende da spec de solicitações e da ratificação das premissas pelo cliente (PF-01, PF-07).');
  }));
  rota('solicitacoes', tela('solicitacoes', (p) => p.tem('alteracao:propor') || p.tem('alteracao:validar'), (a) =>
    telaEmDesenvolvimento(a, perfil.tem('alteracao:validar') ? 'Validações' : 'Solicitações', 'Ainda não há API de solicitações; propor, aprovar e devolver dependem da spec de solicitações (PF-01, PF-02).')));
  rota('qualidade', tela('qualidade', (p) => p.tem('dashboard:read'), (a) => telaEmImplantacao(a, 'Qualidade dos dados', 'T11')));
  rota('historico', tela('historico', (p) => p.tem('auditoria:read'), (a) => {
    if (perfil.global('auditoria:read')) telaEmImplantacao(a, 'Histórico', 'T11');
    else telaEmDesenvolvimento(a, 'Histórico de alterações', 'A trilha geral no escopo do distrito ou da área ainda não existe na API (emenda da 008). O histórico de cada unidade continua na ficha.');
  }));
  rota('cadeia', tela('cadeia', (p) => p.global('auditoria:read'), (a) => telaEmImplantacao(a, 'Verificação da cadeia', 'T11')));
  rota('importar', tela('importar', (p) => p.global('unidade:create'), (a) =>
    telaEmDesenvolvimento(a, 'Importar planilha', 'Ainda não há API de importação (spec de CSV do backend).')));
  rota('papeis', tela('papeis', (p) => p.tem('papel:assign'), (a) => telaEmImplantacao(a, 'Papéis e atribuições', 'T5 (complemento)')));
  rota('usuarios', tela('usuarios', (p) => p.tem('usuario:manage'), (a) =>
    telaEmDesenvolvimento(a, 'Usuários', 'Ainda não há API de usuários (spec da 003 para /admin/usuarios).')));
  rota('sem-acesso', tela('', sempre, (a) => semAcesso(a)));
  quandoNaoEncontrada((segmentos) => {
    if (!segmentos.length) { location.replace(inicioDoPerfil(perfil)); return; }
    tela('', sempre, (a) => naoEncontrada(a))();
  });
}

async function abrirApp() {
  const app = document.getElementById('app');
  montar(app, carregando('Abrindo sua sessão…'));
  try {
    const { dados } = await chamar('GET', '/me');
    perfil = criarPerfil(dados);
  } catch (falha) {
    if (falha.status === 401) { voltarAoLogin('Sua sessão expirou. Entre de novo.'); return; }
    montar(app, html`<main class="content">${erro(falha)}</main>`);
    return;
  }
  toast('ok', `Olá, ${String(perfil.me.nome).split(' ')[0]}.`);
  if (!location.hash || location.hash === '#' || location.hash === '#/') location.replace(inicioDoPerfil(perfil));
  else resolver();
}

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') fecharPopups(); });
document.addEventListener('click', (e) => {
  if (!e.target.closest('#bellPop') && !e.target.closest('#bellBtn')) {
    const caixa = document.getElementById('bellPop');
    if (caixa && caixa.firstChild) montar(caixa, html``);
  }
  const lado = document.getElementById('side');
  if (lado && lado.classList.contains('open') && !e.target.closest('#side')) lado.classList.remove('open');
});

async function iniciar() {
  iniciarTema();
  registrarRotas();
  iniciarRoteador();
  // A rota só é resolvida com sessão; sem ela, o login (R2.4).
  window.addEventListener('hashchange', () => { if (!perfil) mostrarLogin(abrirApp); }, { capture: true });
  if (await renovar()) await abrirApp();
  else mostrarLogin(abrirApp);
}

iniciar();
