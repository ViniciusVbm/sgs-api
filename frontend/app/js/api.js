// Cliente HTTP da API (spec 012, R2.5, R1.6, R3.4). Erros viram ErroDaApi com o problem+json.

export class ErroDaApi extends Error {
  constructor(status, problema = {}, requestId = null) {
    const detalhe = problema.detail || problema.title || 'Não foi possível concluir a operação.';
    super(detalhe);
    this.status = status;
    this.detail = detalhe;
    this.errors = Array.isArray(problema.errors) ? problema.errors : [];
    this.problema = problema;
    this.requestId = requestId;
  }
}

const ganchos = { token: () => null, renovar: async () => false, expirou: () => {} };

export function configurarApi({ token, renovar, expirou }) {
  Object.assign(ganchos, { token, renovar, expirou });
}

const ROTAS_DE_SESSAO = '/auth/';

export async function chamar(metodo, caminho, opcoes = {}) {
  const { corpo, cabecalhos = {}, autenticar = true, repetir = true } = opcoes;
  const headers = { Accept: 'application/json, application/problem+json', ...cabecalhos };
  if (corpo !== undefined) headers['Content-Type'] = 'application/json';
  const token = autenticar ? ganchos.token() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let resposta;
  try {
    resposta = await fetch(`/api/v1${caminho}`, {
      method: metodo,
      headers,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      credentials: 'same-origin',
    });
  } catch {
    throw new ErroDaApi(0, { detail: 'Sem conexão com o servidor. Verifique a rede e tente de novo.' });
  }

  // 401 numa rota de negócio: um refresh e uma nova tentativa (R2.5); /auth/* fica de fora.
  if (resposta.status === 401 && autenticar && repetir && !caminho.startsWith(ROTAS_DE_SESSAO)) {
    if (await ganchos.renovar()) return chamar(metodo, caminho, { ...opcoes, repetir: false });
    ganchos.expirou();
  }

  const tipo = resposta.headers.get('Content-Type') || '';
  let dados = null;
  if (resposta.status !== 204) {
    dados = tipo.includes('json') ? await resposta.json().catch(() => null) : await resposta.text();
  }
  if (!resposta.ok) {
    const problema = dados && typeof dados === 'object' ? dados : {};
    throw new ErroDaApi(resposta.status, problema, resposta.headers.get('X-Request-ID'));
  }
  return { dados, etag: resposta.headers.get('ETag'), status: resposta.status };
}
