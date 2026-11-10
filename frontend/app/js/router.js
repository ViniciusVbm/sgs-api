// Roteador por hash, como o protótipo (#/rota/parametro?filtro=valor).
const rotas = [];
let aoNaoEncontrar = () => {};

export function rota(padrao, tratador) {
  const partes = padrao.split('/').filter(Boolean);
  rotas.push({ partes, tratador });
}

export const naoEncontrada = (tratador) => { aoNaoEncontrar = tratador; };

export function lerHash(hash = location.hash) {
  const [caminho, busca = ''] = hash.replace(/^#/, '').split('?');
  const segmentos = caminho.split('/').filter(Boolean).map(decodeURIComponent);
  return { segmentos, consulta: new URLSearchParams(busca) };
}

export function resolver() {
  const { segmentos, consulta } = lerHash();
  for (const { partes, tratador } of rotas) {
    if (partes.length !== segmentos.length) continue;
    const params = {};
    const casa = partes.every((p, i) => {
      if (p.startsWith(':')) { params[p.slice(1)] = segmentos[i]; return true; }
      return p === segmentos[i];
    });
    if (casa) return tratador(params, consulta);
  }
  return aoNaoEncontrar(segmentos, consulta);
}

export const ir = (hash) => { if (location.hash === hash) resolver(); else location.hash = hash; };
export const iniciarRoteador = () => window.addEventListener('hashchange', resolver);
