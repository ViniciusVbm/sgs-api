import { chamar } from './api.js';

// Nomes das referências (a API devolve ids na lista e na ficha; spec 012, R5.1, R6.1).
const cache = new Map();

export function carregarReferencia(tipo) {
  if (!cache.has(tipo)) {
    const pedido = chamar('GET', `/referencias/${encodeURIComponent(tipo)}`)
      .then(({ dados }) => new Map(dados.map((r) => [String(r.id), r])))
      .catch((falha) => { cache.delete(tipo); throw falha; });
    cache.set(tipo, pedido);
  }
  return cache.get(tipo);
}

export const limparReferencias = () => cache.clear();

export const ROTULO_DO_STATUS = { ativa: 'Ativa', inativa: 'Inativa', em_implantacao: 'Em implantação' };
