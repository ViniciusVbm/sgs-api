// Formatação de datas no fuso de Recife e de campos (spec 012, R6.2).
const FUSO = 'America/Recife';

const DATA_HORA = new Intl.DateTimeFormat('pt-BR', {
  timeZone: FUSO, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
});
const DATA = new Intl.DateTimeFormat('pt-BR', { timeZone: FUSO, day: '2-digit', month: '2-digit', year: 'numeric' });

export const digitos = (s) => String(s ?? '').replace(/\D/g, '');
export const fmtDataHora = (iso) => (iso ? DATA_HORA.format(new Date(iso)) : '');
export const fmtData = (iso) => (iso ? DATA.format(new Date(iso)) : '');
export const fmtCep = (v) => { const d = digitos(v); return d.length === 8 ? `${d.slice(0, 5)}-${d.slice(5)}` : String(v ?? ''); };
