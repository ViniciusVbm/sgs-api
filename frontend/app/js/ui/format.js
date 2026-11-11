// Formatação de datas no fuso de Recife e de campos (spec 012, R6.2).
const FUSO = 'America/Recife';

const DATA_HORA = new Intl.DateTimeFormat('pt-BR', {
  timeZone: FUSO, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
});
const DATA = new Intl.DateTimeFormat('pt-BR', { timeZone: FUSO, day: '2-digit', month: '2-digit', year: 'numeric' });
const DATA_HORA_SEGUNDOS = new Intl.DateTimeFormat('pt-BR', {
  timeZone: FUSO, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
});
// Recife não tem horário de verão desde 2019: o deslocamento é fixo (o mesmo de src/core/fuso.py).
export const ROTULO_DO_FUSO = 'UTC−03:00';

export const digitos = (s) => String(s ?? '').replace(/\D/g, '');
export const fmtDataHora = (iso) => (iso ? DATA_HORA.format(new Date(iso)) : '');
export const fmtData = (iso) => (iso ? DATA.format(new Date(iso)) : '');
export const fmtDataHoraSegundos = (iso) => (iso ? DATA_HORA_SEGUNDOS.format(new Date(iso)) : '');
// Trilha, log do banco e histórico da unidade (spec 013, R2.1): segundos e o fuso explícito.
export const fmtAuditoria = (iso) => (iso ? `${DATA_HORA_SEGUNDOS.format(new Date(iso))} (${ROTULO_DO_FUSO})` : '');
// Detalhe do evento (spec 013, R2.2): o instante como a API devolve, com microssegundos e
// deslocamento, sem conversão nenhuma.
export const fmtInstante = (iso) => (iso ? String(iso) : '');

// Resultado do evento (spec 013, R4.1, R8.4); eventos anteriores à 013 vêm sem resultado.
const RESULTADOS = { success: ['ok', 'sucesso'], failure: ['err', 'falha'], denied: ['warn', 'negado'] };
export const CATEGORIAS = {
  autenticacao: 'autenticação', autorizacao: 'autorização', validacao: 'validação',
  conflito: 'conflito', precondicao: 'precondição', erro_interno: 'erro interno',
};
export const NAO_REGISTRADO = 'não registrado';
export const resultadoDoEvento = (resultado, categoria) => {
  const [classe, rotulo] = RESULTADOS[resultado] || ['wait', NAO_REGISTRADO];
  return { classe, rotulo: categoria ? `${rotulo} (${CATEGORIAS[categoria] || categoria})` : rotulo, valor: resultado || '' };
};
export const fmtCep = (v) => { const d = digitos(v); return d.length === 8 ? `${d.slice(0, 5)}-${d.slice(5)}` : String(v ?? ''); };
