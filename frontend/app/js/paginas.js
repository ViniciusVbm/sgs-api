import { chamar, ErroDaApi } from './api.js';

// Busca todas as páginas de uma rota paginada (PaginaOut: itens, total). Usado onde a conta
// precisa do conjunto inteiro, sem amostragem: médias e situação do inventário, linha do
// período (spec 012, R12.6). Para quando os itens recebidos alcançam o `total` da API.

const MAX_PAGINAS = 100;

export async function buscarTodas(caminho, parametros = {}, tamanho = 100) {
  const filtros = Object.entries(parametros).filter(([, v]) => v !== '' && v !== null && v !== undefined);
  const itens = [];
  let total = 0;
  for (let pagina = 1; ; pagina += 1) {
    if (pagina > MAX_PAGINAS) {
      throw new ErroDaApi(0, { detail: 'Há registros demais para somar nesta tela; reduza o período ou os filtros.' });
    }
    const qs = new URLSearchParams([...filtros, ['pagina', String(pagina)], ['tamanho', String(tamanho)]]);
    const { dados } = await chamar('GET', `${caminho}?${qs}`);
    total = dados.total;
    itens.push(...dados.itens);
    if (itens.length >= total || !dados.itens.length) break;
  }
  return { itens, total };
}
