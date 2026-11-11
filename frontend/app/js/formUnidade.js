import { html } from './html.js';
import { campo, marcarErro } from './ui/form.js';
import { ROTULO_DO_STATUS } from './referencias.js';

// Campos da unidade para o cadastro e a edição (spec 012, T9: R7.1 a R7.3), com os nomes e os
// limites do contrato (UnidadeCreate e UnidadeUpdate). Os formatos (CNES, CEP, telefone,
// coordenadas) são validados pela API, que responde 422 no campo; aqui só se conferem os
// obrigatórios do schema antes de enviar.

export const OBRIGATORIOS = ['nome', 'tipo_unidade_id', 'distrito_id', 'cep', 'endereco', 'status'];
const OPCIONAIS = ['cnes', 'bairro', 'telefone', 'nome_gestor', 'latitude', 'longitude'];
export const ROTULOS = {
  nome: 'Nome', cnes: 'CNES', tipo_unidade_id: 'Tipo de unidade', distrito_id: 'Distrito sanitário',
  cep: 'CEP', endereco: 'Endereço', bairro: 'Bairro', telefone: 'Telefone', nome_gestor: 'Gestor(a) da unidade',
  latitude: 'Latitude', longitude: 'Longitude', status: 'Situação',
};

// Itens ativos; na edição, também o valor atual, mesmo inativo, para não parecer alterado.
const opcoesDe = (mapa, atual = '') => [...mapa.values()]
  .filter((r) => r.ativo !== false || String(r.id) === String(atual))
  .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  .map((r) => ({ valor: r.id, rotulo: r.ativo === false ? `${r.nome} (inativo)` : r.nome }));

// `atual`: valores da API (edição) ou vazio (cadastro). Na edição, a situação "inativa" não é
// editável: a desativação é pela procedure (T25) e a interface não reativa (R7.7).
export function camposDaUnidade(atual, { tipos, distritos }, { edicao = false } = {}) {
  const v = (k) => (atual && atual[k] !== null && atual[k] !== undefined ? atual[k] : '');
  const inativa = edicao && atual.status === 'inativa';
  const situacoes = Object.entries(ROTULO_DO_STATUS)
    .filter(([chave]) => !edicao || chave !== 'inativa')
    .map(([valor, rotulo]) => ({ valor, rotulo }));
  return html`
    <div class="grid g2">
      <div class="span2">${campo({ nome: 'nome', rotulo: ROTULOS.nome, valor: v('nome'), obrigatorio: true, max: 200 })}</div>
      ${campo({ nome: 'cnes', rotulo: ROTULOS.cnes, valor: v('cnes'), max: 7, ajuda: 'Sete dígitos. Sem CNES, a unidade fica pendente.' })}
      ${inativa
    ? html`<div class="fld" data-campo="status"><label for="fld-status">${ROTULOS.status}</label><input id="fld-status" type="text" value="Inativa" disabled data-ref="status-inativa"><p class="hint">Unidade desativada pelo procedimento; a edição não muda a situação.</p></div>`
    : campo({ nome: 'status', rotulo: ROTULOS.status, valor: v('status') || 'ativa', obrigatorio: true, opcoes: situacoes, ajuda: edicao ? 'Para desativar, use "Desativar unidade".' : '' })}
      ${campo({ nome: 'tipo_unidade_id', rotulo: ROTULOS.tipo_unidade_id, valor: v('tipo_unidade_id'), obrigatorio: true, opcoes: opcoesDe(tipos, v('tipo_unidade_id')) })}
      ${campo({ nome: 'distrito_id', rotulo: ROTULOS.distrito_id, valor: v('distrito_id'), obrigatorio: true, opcoes: opcoesDe(distritos, v('distrito_id')) })}
      <div class="span2">${campo({ nome: 'endereco', rotulo: ROTULOS.endereco, valor: v('endereco'), obrigatorio: true, max: 200 })}</div>
      ${campo({ nome: 'bairro', rotulo: ROTULOS.bairro, valor: v('bairro'), max: 100 })}
      ${campo({ nome: 'cep', rotulo: ROTULOS.cep, valor: v('cep'), obrigatorio: true, max: 9, ajuda: 'Oito dígitos, com ou sem hífen.' })}
      ${campo({ nome: 'telefone', rotulo: ROTULOS.telefone, valor: v('telefone'), max: 20 })}
      ${campo({ nome: 'nome_gestor', rotulo: ROTULOS.nome_gestor, valor: v('nome_gestor'), max: 150 })}
      ${campo({ nome: 'latitude', rotulo: ROTULOS.latitude, valor: v('latitude'), max: 12, ajuda: 'Entre -90 e 90, até 6 casas.' })}
      ${campo({ nome: 'longitude', rotulo: ROTULOS.longitude, valor: v('longitude'), max: 12, ajuda: 'Entre -180 e 180, até 6 casas.' })}
    </div>`;
}

// Corpo no formato do contrato: opcional vazio vira null (no PATCH, null limpa o campo); ids
// numéricos; coordenadas como texto, para a API (Decimal) receber exatamente o que foi digitado.
export function lerUnidade(formulario) {
  const dados = {};
  formulario.querySelectorAll('[name]').forEach((el) => {
    if (el.disabled) return;
    const texto = String(el.value).trim();
    if (el.name === 'tipo_unidade_id' || el.name === 'distrito_id') dados[el.name] = texto === '' ? null : Number(texto);
    else if (OPCIONAIS.includes(el.name)) dados[el.name] = texto === '' ? null : texto;
    else dados[el.name] = texto;
  });
  return dados;
}

// Os obrigatórios do schema, antes de enviar; o resto (formatos, unicidade) é da API.
export function conferirObrigatorios(formulario, dados) {
  let ok = true;
  for (const nome of OBRIGATORIOS) {
    if (nome in dados && (dados[nome] === '' || dados[nome] === null)) {
      marcarErro(formulario, nome, 'Campo obrigatório.');
      ok = false;
    }
  }
  return ok;
}

// Igualdade sem diferença só de formato: CEP com ou sem hífen, números de coordenada.
const normal = (nome, valor) => {
  if (valor === null || valor === undefined || valor === '') return null;
  if (nome === 'cep') return String(valor).replace(/\D/g, '');
  if (nome === 'latitude' || nome === 'longitude') return Number(valor);
  if (nome === 'tipo_unidade_id' || nome === 'distrito_id') return Number(valor);
  return String(valor);
};

// Só os campos alterados, para o PATCH (R7.1).
export function alteracoesDaUnidade(original, dados) {
  const saida = {};
  for (const [nome, valor] of Object.entries(dados)) {
    if (normal(nome, valor) !== normal(nome, original[nome])) saida[nome] = valor;
  }
  return saida;
}

// Texto legível de um valor para o diff de confirmação.
export function valorLegivel(nome, valor, { tipos, distritos }) {
  if (valor === null || valor === undefined || valor === '') return '—';
  if (nome === 'tipo_unidade_id') return tipos.get(String(valor))?.nome || String(valor);
  if (nome === 'distrito_id') return distritos.get(String(valor))?.nome || String(valor);
  if (nome === 'status') return ROTULO_DO_STATUS[valor] || valor;
  return String(valor);
}

// 403 com `campos_estruturais` (ex.: "distrito_id, cnes"): aponta os campos (R7.2).
export function marcarCamposEstruturais(formulario, falha) {
  const lista = falha.problema && falha.problema.campos_estruturais;
  if (falha.status !== 403 || !lista) return false;
  let algum = false;
  for (const nome of String(lista).split(',').map((s) => s.trim()).filter(Boolean)) {
    algum = marcarErro(formulario, nome, 'Seu escopo não permite alterar este campo.') || algum;
  }
  return algum;
}
