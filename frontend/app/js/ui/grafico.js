import { html } from '../html.js';

// Gráficos em SVG gerado no próprio front (spec 012, R12.6; design § Gráficos).
// Sem biblioteca nem recurso externo (R1.3, R15.2); todo valor entra pela tag `html`, com escape.
// Cada gráfico é um <svg role="img"> com aria-label que resume os dados, uma legenda quando há
// duas séries ou mais e uma tabela com os mesmos dados em "Ver dados" (R1.5).
// As coordenadas horizontais são porcentagens, sem viewBox: o texto mantém o tamanho real em
// qualquer largura (R1.4) e as barras não se deformam.

const FORMATOS = new Map();
export function numero(valor, casas = 1) {
  if (!FORMATOS.has(casas)) {
    FORMATOS.set(casas, new Intl.NumberFormat('pt-BR', { maximumFractionDigits: casas }));
  }
  return FORMATOS.get(casas).format(valor);
}

// Paleta categórica validada (scripts/validate_palette.js da skill de visualização) contra as
// superfícies do app.css nos dois temas; a cor segue a entidade, nunca a posição (app.css: --viz-*).
export const CORES = ['var(--viz-1)', 'var(--viz-2)', 'var(--viz-3)', 'var(--viz-4)', 'var(--viz-5)'];
export const COR_OUTROS = 'var(--viz-neutro)';

const ESCALA = 86; // a barra mais longa ocupa 86% da largura; o resto é do rótulo do valor
const proporcao = (valor, maximo) => (maximo > 0 ? Math.max(0, (valor / maximo) * ESCALA) : 0);
const fixo = (v) => Number(v.toFixed(3));

function legenda(series) {
  if (series.length < 2) return '';
  return html`<ul class="viz-leg">${series.map((s) => html`<li><i style="background:${s.cor}"></i>${s.nome}</li>`)}</ul>`;
}

function tabelaDeDados(cabecalho, linhas) {
  return html`<details class="viz-dados"><summary>Ver dados</summary><div class="tbl-wrap"><table>
    <thead><tr>${cabecalho.map((c) => html`<th>${c}</th>`)}</tr></thead>
    <tbody>${linhas.map((l) => html`<tr>${l.map((c) => html`<td>${c}</td>`)}</tr>`)}</tbody></table></div></details>`;
}

function quadro({ ref, titulo, subtitulo = '', series = [], corpo, cabecalho, linhas, nota = '' }) {
  return html`<figure class="viz" data-ref="${ref}">
    <figcaption><b>${titulo}</b>${subtitulo ? html`<span>${subtitulo}</span>` : ''}</figcaption>
    ${legenda(series)}${corpo}${nota}${tabelaDeDados(cabecalho, linhas)}</figure>`;
}

// Barras horizontais de uma série, com linha de referência opcional (ex.: o % da rede).
export function barras({ ref, titulo, subtitulo, itens, formato = (v) => numero(v), referencia = null, rotuloValor = 'Valor' }) {
  const maximo = Math.max(...itens.map((i) => i.valor), referencia ? referencia.valor : 0, 0);
  const linha = 34;
  const altura = itens.length * linha + 6;
  const resumo = `${titulo}: ${itens.map((i) => `${i.rotulo} ${formato(i.valor)}`).join('; ')}${referencia ? `; ${referencia.rotulo} ${formato(referencia.valor)}` : ''}`;
  const xRef = referencia ? fixo(proporcao(referencia.valor, maximo)) : 0;
  const corpo = html`<svg class="viz-svg" role="img" aria-label="${resumo}" width="100%" height="${altura}">
    ${itens.map((i, n) => {
      const y = n * linha;
      const largura = fixo(proporcao(i.valor, maximo));
      return html`<g><title>${i.rotulo}: ${formato(i.valor)}</title>
        <text class="viz-rot" x="0" y="${y + 11}">${i.rotulo}</text>
        <rect class="viz-trilho" x="0" y="${y + 16}" width="${ESCALA}%" height="12" rx="3"></rect>
        <rect x="0" y="${y + 16}" width="${largura}%" height="12" rx="3" style="fill:${i.cor || CORES[0]}"></rect>
        <text class="viz-val" x="${largura}%" dx="6" y="${y + 26}">${formato(i.valor)}</text>
        ${referencia ? html`<line class="viz-ref" x1="${xRef}%" x2="${xRef}%" y1="${y + 15}" y2="${y + 30}"><title>${referencia.rotulo}: ${formato(referencia.valor)}</title></line>` : ''}</g>`;
    })}
  </svg>`;
  const nota = referencia ? html`<p class="viz-nota"><i class="viz-tracejado"></i>${referencia.rotulo}: ${formato(referencia.valor)}</p>` : '';
  return quadro({
    ref, titulo, subtitulo, corpo, nota,
    cabecalho: ['Categoria', rotuloValor, ...(referencia ? [referencia.rotulo] : [])],
    linhas: itens.map((i) => [i.rotulo, formato(i.valor), ...(referencia ? [formato(referencia.valor)] : [])]),
  });
}

// Barras agrupadas: uma categoria por linha, uma barra por série (ex.: 7 e 30 dias por distrito).
export function barrasAgrupadas({ ref, titulo, subtitulo, categorias, series, formato = (v) => numero(v) }) {
  const maximo = Math.max(0, ...series.flatMap((s) => s.valores));
  const espessura = 10;
  const linha = 18 + series.length * (espessura + 3) + 6;
  const altura = categorias.length * linha;
  const resumo = `${titulo}: ${categorias.map((c, n) => `${c} ${series.map((s) => `${s.nome} ${formato(s.valores[n])}`).join(', ')}`).join('; ')}`;
  const corpo = html`<svg class="viz-svg" role="img" aria-label="${resumo}" width="100%" height="${altura}">
    ${categorias.map((c, n) => {
      const y = n * linha;
      return html`<g><text class="viz-rot" x="0" y="${y + 11}">${c}</text>
        ${series.map((s, k) => {
          const yb = y + 16 + k * (espessura + 3);
          const largura = fixo(proporcao(s.valores[n], maximo));
          return html`<g><title>${c} · ${s.nome}: ${formato(s.valores[n])}</title>
            <rect x="0" y="${yb}" width="${largura}%" height="${espessura}" rx="3" style="fill:${s.cor}"></rect>
            <text class="viz-val" x="${largura}%" dx="6" y="${yb + 9}">${formato(s.valores[n])}</text></g>`;
        })}</g>`;
    })}
  </svg>`;
  return quadro({
    ref, titulo, subtitulo, series, corpo,
    cabecalho: ['Categoria', ...series.map((s) => s.nome)],
    linhas: categorias.map((c, n) => [c, ...series.map((s) => formato(s.valores[n]))]),
  });
}

// Barras empilhadas: uma categoria por linha, um segmento por série (ex.: tipos de equipamento).
export function barrasEmpilhadas({ ref, titulo, subtitulo, categorias, series, formato = (v) => numero(v) }) {
  const totais = categorias.map((_, n) => series.reduce((soma, s) => soma + s.valores[n], 0));
  const maximo = Math.max(0, ...totais);
  const linha = 34;
  const altura = categorias.length * linha + 6;
  const resumo = `${titulo}: ${categorias.map((c, n) => `${c} ${formato(totais[n])} (${series.filter((s) => s.valores[n]).map((s) => `${s.nome} ${formato(s.valores[n])}`).join(', ')})`).join('; ')}`;
  const corpo = html`<svg class="viz-svg" role="img" aria-label="${resumo}" width="100%" height="${altura}">
    ${categorias.map((c, n) => {
      const y = n * linha;
      let x = 0;
      return html`<g><text class="viz-rot" x="0" y="${y + 11}">${c}</text>
        ${series.map((s) => {
          const largura = fixo(proporcao(s.valores[n], maximo));
          const inicio = fixo(x);
          x += largura;
          return s.valores[n] ? html`<rect class="viz-seg" x="${inicio}%" y="${y + 16}" width="${largura}%" height="12" style="fill:${s.cor}"><title>${c} · ${s.nome}: ${formato(s.valores[n])}</title></rect>` : '';
        })}
        <text class="viz-val" x="${fixo(x)}%" dx="6" y="${y + 26}">${formato(totais[n])}</text></g>`;
    })}
  </svg>`;
  return quadro({
    ref, titulo, subtitulo, series, corpo,
    cabecalho: ['Categoria', ...series.map((s) => s.nome), 'Total'],
    linhas: categorias.map((c, n) => [c, ...series.map((s) => formato(s.valores[n])), formato(totais[n])]),
  });
}

// Rosca (pizza com centro vazado): fatias com rótulo, valor e % na legenda, total no centro.
export function rosca({ ref, titulo, subtitulo, fatias, rotuloTotal = 'total' }) {
  const total = fatias.reduce((soma, f) => soma + f.valor, 0);
  const raio = 15.915; // circunferência 100: o traço de cada fatia é o próprio percentual
  let acumulado = 0;
  const porcento = (v) => (total ? (v / total) * 100 : 0);
  const resumo = `${titulo}: ${fatias.map((f) => `${f.rotulo} ${f.valor} (${numero(porcento(f.valor))}%)`).join('; ')}`;
  const corpo = html`<div class="viz-rosca">
    <svg role="img" aria-label="${resumo}" viewBox="0 0 42 42" width="150" height="150">
      <circle class="viz-trilho-rosca" cx="21" cy="21" r="${raio}" fill="none" stroke-width="6"></circle>
      ${fatias.filter((f) => f.valor > 0).map((f) => {
        const parte = porcento(f.valor);
        const desenho = html`<circle cx="21" cy="21" r="${raio}" fill="none" style="stroke:${f.cor}" stroke-width="6"
          stroke-dasharray="${fixo(Math.max(parte - 0.6, 0.1))} ${fixo(100 - Math.max(parte - 0.6, 0.1))}"
          stroke-dashoffset="${fixo(25 - acumulado)}"><title>${f.rotulo}: ${f.valor} (${numero(parte)}%)</title></circle>`;
        acumulado += parte;
        return desenho;
      })}
      <text class="viz-centro" x="21" y="21">${total}</text>
      <text class="viz-centro-sub" x="21" y="26.5">${rotuloTotal}</text>
    </svg>
    <ul class="viz-leg viz-leg-col">${fatias.map((f) => html`<li data-fatia="${f.chave}"><i style="background:${f.cor}"></i>${f.rotulo}<b>${f.valor}</b><span>${numero(porcento(f.valor))}%</span></li>`)}</ul>
  </div>`;
  return quadro({
    ref, titulo, subtitulo, corpo,
    cabecalho: ['Fatia', 'Quantidade', '%'],
    linhas: fatias.map((f) => [f.rotulo, f.valor, `${numero(porcento(f.valor))}%`]),
  });
}

// Linha de uma série no tempo; `pontos` já vêm com zero nos intervalos sem registro.
export function linha({ ref, titulo, subtitulo, pontos, nota = '' }) {
  const maximo = Math.max(1, ...pontos.map((p) => p.valor));
  const teto = maximo <= 4 ? maximo : Math.ceil(maximo / 4) * 4;
  const altura = 190; const topo = 18; const base = 160;
  const y = (v) => fixo(base - (v / teto) * (base - topo));
  const x = (n) => (pontos.length === 1 ? 50 : fixo(1.5 + (n * 97) / (pontos.length - 1)));
  const marcas = [...new Set([0, Math.round((pontos.length - 1) / 2), pontos.length - 1])];
  const total = pontos.reduce((soma, p) => soma + p.valor, 0);
  const resumo = `${titulo}: ${total} registros em ${pontos.length} intervalos; máximo de ${maximo} num intervalo`;
  const corpo = html`<svg class="viz-svg" role="img" aria-label="${resumo}" width="100%" height="${altura}">
    ${[0, teto / 2, teto].map((v) => html`<line class="viz-guia" x1="0" x2="100%" y1="${y(v)}" y2="${y(v)}"></line>
      <text class="viz-eixo" x="0" y="${y(v) - 4}">${numero(v)}</text>`)}
    ${pontos.slice(1).map((p, n) => html`<line class="viz-traco" x1="${x(n)}%" y1="${y(pontos[n].valor)}" x2="${x(n + 1)}%" y2="${y(p.valor)}"></line>`)}
    ${pontos.map((p, n) => html`<g><title>${p.rotulo}: ${p.valor}</title>
      <circle class="viz-alvo" cx="${x(n)}%" cy="${y(p.valor)}" r="10"></circle>
      ${p.valor ? html`<circle class="viz-ponto" cx="${x(n)}%" cy="${y(p.valor)}" r="4"></circle>` : ''}</g>`)}
    ${marcas.map((n, k) => html`<text class="viz-eixo" x="${x(n)}%" y="${altura - 8}" text-anchor="${k === 0 ? 'start' : k === marcas.length - 1 ? 'end' : 'middle'}">${pontos[n].rotuloCurto}</text>`)}
  </svg>`;
  return quadro({
    ref, titulo, subtitulo, corpo, nota,
    cabecalho: ['Intervalo', 'Registros'],
    linhas: pontos.map((p) => [p.rotulo, p.valor]),
  });
}
