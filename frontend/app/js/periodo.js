// Períodos e intervalos no fuso de Recife (spec 012, R12.6: linha das alterações no período).
// America/Recife é UTC−3 o ano todo (sem horário de verão desde 2019), então o deslocamento
// é fixo: um dia tem sempre 24 h e os limites dos intervalos caem à meia-noite de Recife.

const FUSO = 'America/Recife';
const DESLOCAMENTO = '-03:00';
const HORA = 3600 * 1000;
const DIA = 24 * HORA;

const DIA_ISO = new Intl.DateTimeFormat('en-CA', { timeZone: FUSO, year: 'numeric', month: '2-digit', day: '2-digit' });
const DIA_MES = new Intl.DateTimeFormat('pt-BR', { timeZone: FUSO, day: '2-digit', month: '2-digit' });
const HORA_DO_DIA = new Intl.DateTimeFormat('pt-BR', { timeZone: FUSO, hour: '2-digit', hourCycle: 'h23' });

export const PERIODOS = { 7: '7 dias', 30: '30 dias', personalizado: 'Personalizado' };

export const hojeEmRecife = (agora = new Date()) => DIA_ISO.format(agora);
const meiaNoite = (diaIso) => new Date(`${diaIso}T00:00:00${DESLOCAMENTO}`);
const somarDias = (diaIso, n) => DIA_ISO.format(new Date(meiaNoite(diaIso).getTime() + n * DIA + 12 * HORA));
const valido = (diaIso) => /^\d{4}-\d{2}-\d{2}$/.test(diaIso || '') && !Number.isNaN(meiaNoite(diaIso).getTime());

// {de, ate} como datas absolutas (`ate` exclusivo) e a granularidade: por hora até 2 dias.
export function intervaloDoPeriodo(periodo, deIso, ateIso, agora = new Date()) {
  const hoje = hojeEmRecife(agora);
  let inicio;
  let fimInclusivo;
  if (periodo === 'personalizado') {
    if (!valido(deIso) || !valido(ateIso)) return { erro: 'Informe a data inicial e a final.' };
    if (deIso > ateIso) return { erro: 'A data inicial deve ser anterior ou igual à final.' };
    inicio = deIso;
    fimInclusivo = ateIso;
  } else {
    const dias = periodo === '30' ? 30 : 7;
    inicio = somarDias(hoje, -(dias - 1));
    fimInclusivo = hoje;
  }
  const de = meiaNoite(inicio);
  const ate = meiaNoite(somarDias(fimInclusivo, 1));
  return { de, ate, deIso: inicio, ateIso: fimInclusivo, porHora: ate - de <= 2 * DIA };
}

// Todos os intervalos do período, com zero onde não há registro (nada é inventado).
export function contarPorIntervalo(registros, { de, ate, porHora }, campo = 'quando') {
  const passo = porHora ? HORA : DIA;
  const quantidade = Math.round((ate - de) / passo);
  const contagens = new Array(quantidade).fill(0);
  for (const r of registros) {
    const n = Math.floor((new Date(r[campo]).getTime() - de.getTime()) / passo);
    if (n >= 0 && n < quantidade) contagens[n] += 1;
  }
  return contagens.map((valor, n) => {
    const inicio = new Date(de.getTime() + n * passo);
    const dia = DIA_MES.format(inicio);
    const rotuloCurto = porHora ? `${dia} ${HORA_DO_DIA.format(inicio)}h` : dia;
    return { inicio, valor, rotulo: porHora ? `${rotuloCurto} (1 hora)` : dia, rotuloCurto };
  });
}
