# Plano de integração frontend + backend · SGS Recife

- **Versão 2 (09/11/2026):** revisão final do planejamento. **A implementação não está autorizada.**
- **Branch:** `feat/integracao-frontend` (= `main` `31e561c`), sem commits.
- **Atualização de 10/11/2026:**
  - **Sincronização:** a branch foi avançada por fast-forward até a `novo/main` `9c37029` (PRs #1 a #3, só documentação e testes; nenhuma mudança de API, banco ou matriz). Backup em `~/sgs-api-frontend-backup-20261110/`.
  - **Responsáveis:** Vinicius é dono da 003, 004, 005, 007, 008, 009, 010, 011 e 012; Hélder é responsável pela 006 (decisão do Grupo 01).
  - **Decisões:** foram registradas as decisões internas do grupo (Grupo-DF9, Grupo-DF15) e as premissas aguardando o cliente (Grupo-DF2, Grupo-DF13, Grupo-DF14).
  - **Pendências formais:** PF-01 a PF-07, que vêm das perguntas P1 a P5 sobre as premissas, estão na spec 012, § Pendências formais.
  - **Referência atual:** onde este plano (v2) diverge da `specs/012-frontend/` (§ Decisões, design § Matriz de integração e tarefas, revisão 3), **vale a spec**. As tabelas das §§ 2 e 3 abaixo são o registro de 09/11/2026.
- **Protótipo auditado:** `frontend/prototipo/Prototipo_SGS_Recife_v2.html` (145.548 bytes, 1.935 linhas, sha256 `781261c2…`), não rastreado.

**Regra deste plano:** nenhuma mudança na matriz RBAC (spec 003), em spec aprovada ou em permissão sem aprovação formal de quem a regra do projeto exige (§ 2).

---

## 1. Diagnóstico (resumo)
**Protótipo:**
- página única em JavaScript puro, com hash router e render por template string em `innerHTML`;
- 3 perfis (`central`, `distrito`, `unidade`), dados fictícios em `localStorage`, nenhuma chamada HTTP;
- login de demonstração, com senha e código exibidos na tela;
- autorização só no navegador.

**Backend:**
- 55 operações com autenticação real (Argon2id, TOTP, ES256, refresh rotativo);
- RBAC com 7 papéis e 4 escopos;
- 885 testes passando.

**Faltam no backend:**
- workflow de solicitações;
- notificações;
- revisão sem alteração;
- CSV;
- validações do protótipo (spec 007);
- histórico no escopo;
- gestão de usuários;
- campos de endereço, contato e horário.

**Incompatibilidades:**
- "equipamentos" do protótipo são aparelhos; os do backend são estabelecimentos de saúde;
- no protótipo, distrito e unidade só propõem; no backend, editam direto;
- situação da unidade: 4 valores no protótipo × 3 status no backend.

O detalhe por funcionalidade está no § 4.

## 2. Quem aprova o quê (regras do projeto)
Fonte: `steering/sdd-workflow.md` e `AGENTS.md`, regra 1.

| Artefato | Aprova |
|---|---|
| `requirements.md` e `tasks.md` de uma spec | o **dono** da spec |
| `design.md` | o **dono + 1 integrante** (a exceção da 003, 006 e 011 vale só até a entrega da 011) |
| Emendas às specs aprovadas 002, 003, 006 e 011 | o **Rafael** (dono e quem aprovou). *10/11/2026:* 003 e 011 → Vinicius (`steering/sdd-workflow.md` § Dono da spec); 006 → Hélder (decisão do Grupo 01) |
| Specs em Rascunho (004, 005, 007, 008, 009, 010) | o dono. Nas 008, 009 e 010, já revistas, é o Rafael; na 007, o dono **não está definido**. *10/11/2026:* dono de todas é o Vinicius; 008, 009 e 010 aprovadas |
| Spec nova (ex.: 012 frontend) | o dono que for indicado. Se for o Vinicius: requisitos e tarefas por ele, design por ele + 1 integrante |
| ADR novo | proposto por qualquer um; aceito pelo grupo (ADR-0006, SDD) |
| Matriz RBAC (`migrations/versions/0003_access.py`, spec 003) | o **Rafael**: muda a spec 003 e exige migração nova. *10/11/2026:* dono da 003 é o Vinicius |

## 3. Tabela de decisões (DF1 a DF12)
**Legenda de "Quem decide":**
- **Você:** decisão do usuário, ou de uma spec nova cujo dono seja você.
- **Cliente:** Secretaria (Sérgio), sobre o domínio.
- **Rafael:** emenda de spec aprovada ou da matriz RBAC.

| ID | Decisão | Quem decide | Opções | Recomendação | Bloqueia |
|---|---|---|---|---|---|
| DF1 | O que são os "equipamentos" do protótipo (aparelhos) | **Cliente** (domínio) + **Rafael** (emenda da 006) | (a) entidade nova "infraestrutura"; (b) reaproveitar `equipments`; (c) só leitura até decidir | (a) | E5 |
| DF2 | Distrito e unidade gravam direto ou só propõem | **Rafael** (matriz da 003; `unidade:update` D/U) + **Cliente** (regra de negócio) | (a) só por solicitação, como no protótipo; (b) manter direto | (a). **Nada muda na matriz sem aprovação formal** | E6, e a edição para distrito e unidade em E4 |
| DF3 | Situação da unidade: 4 valores × 3 status | **Cliente** (valores) + **Rafael** (006/R1.2 e CHECK) | (a) incluir `em_reforma` e `fechada_temporariamente`; (b) mapear para os 3 | (a) | Campo situação em E4 |
| DF4 | "Grupo de atenção" × área técnica | **Cliente** | (a) grupo como atributo do tipo; (b) usar a área técnica | (b), mais simples | Gráfico "por grupo" em E8 |
| DF5 | Catálogos de tipos de unidade (14 × 10) e de serviços (18 × 4) | **Cliente** (lista oficial) | Carga pela API de referências (dado, sem código) | Carga pela API | Conteúdo de E4 e E5 (não o código) |
| DF6 | Como mostrar o cadastro do TOTP | **Você** | (a) chave e URI para digitar no app; (b) biblioteca de QR local | (a) agora; (b) depois, com ADR de dependência | — |
| DF7 | Login por e-mail ou username | **Rafael** (emenda da 002/R1) se mudar o backend; **Você**, se só mudar o rótulo da tela | (a) o backend aceita os dois; (b) a tela pede "usuário" | (b) para 21/11; (a) depois | — |
| DF8 | Telas para ADMIN_TI, COORD_TECNICO, DIRETORIA e AUDITOR (o protótipo só tem 3 perfis) | **Você** (spec do front) + **Cliente** (validação) | Diretoria: início e lista só leitura; Auditor: histórico e verificação; Admin TI: papéis (já há API); Coordenador: como o distrito, na área | Como ao lado | E3 |
| DF9 | O Gestor de Dados vê os eventos de acesso? | **Rafael** (matriz: `auditoria:read_acessos`) | (a) manter: só ADMIN_TI e AUDITOR; (b) conceder | (a): segregação de funções, sem mudança | Filtro "Acessos" em E9 |
| DF10 | Exportação CSV no backend ou no front | **Você** (técnica), com spec nova; **Rafael**, se for emenda da 006 | (a) endpoint no escopo; (b) o front pagina tudo | (a) | E10 |
| DF11 | Testes E2E de navegador | **Você** (ADR de dependência de dev) | (a) Playwright (Python); (b) nenhum | (a) | E11 |
| DF12 | Escopo de 21/11 | **Você** | § 7 | Escopo mínimo do § 7 | — |

**Decisões sem dono definido:**
- quem é o dono da spec 007 (validação);
- quem é o dono da spec nova do frontend e das specs de solicitações, notificações e infraestrutura.

**Proposta:** você é o dono da spec do frontend; o Rafael, das que mexem no modelo e no RBAC.

**Mudanças na matriz RBAC previstas** (todas pendentes, **nenhuma aplicada**):
- DF2: retirar `unidade:update`, `equipamento:write` e `servico:write` de TECNICO_DISTRITAL e GESTOR_UNIDADE, e ativar `alteracao:propor` e `alteracao:validar`;
- B13: usar `usuario:manage`, que já existe, sem mudar a matriz;
- DF9: nenhuma.

## 4. Matriz frontend → backend (as 24 funcionalidades, nenhuma descartada)
**Classe:**
- **IMP:** implementada.
- **PAR:** parcial.
- **NÃO:** não implementada.
- **INC:** incompatível.
- **DEC:** precisa de decisão.

**Destino:** **21/11** (escopo mínimo) ou **Completo** (depois). Uma funcionalidade fora do mínimo **continua na interface**, desabilitada com o aviso "em desenvolvimento".

| # | Funcionalidade | API hoje | Classe | Falta | Destino | Etapa |
|---|---|---|---|---|---|---|
| F01 | Login | `POST /auth/login` (username) | PAR | Rótulo "usuário" (DF7); remover os atalhos demo | 21/11 | E2 |
| F02 | 2º fator (verificar e cadastrar) | `/auth/mfa/*` | PAR | Tela de cadastro (DF6); remover `DEMO_CODE` | 21/11 | E2 |
| F03 | Esqueci a senha | — | NÃO | Manter o texto atual (Admin TI redefine); endpoint de redefinição (B13) | Texto em 21/11; endpoint completo | E2 / E12 |
| F04 | Logout | `POST /auth/logout` | IMP | — | 21/11 | E2 |
| F05 | Menu por perfil | `GET /me` | PAR + DEC | Mapa 7 papéis → telas (DF8) | 21/11 | E3 |
| F06 | Início (indicadores) | `/dashboard/resumo`, `/inventario` | PAR | Contagem por verificação (B7), pendências de solicitações (B1), "por grupo" (DF4) | 21/11 com os dados do resumo; o resto completo | E3 / E8 |
| F07 | Lista, busca, filtros, ordenação | `GET /unidades` | PAR | Busca por bairro e tipo; filtros de qualidade e "aguardando" | 21/11 (filtros existentes); completo | E4 / E8 |
| F08 | Exportar CSV | — | NÃO + DEC | B9 (DF10) | Completo | E10 |
| F09 | Ficha: dados gerais | `GET/PATCH /unidades/{id}` | INC + DEC | Número, complemento, e-mail, horário, situação (B4, DF3) | 21/11 com os campos que existem; o resto completo | E4 |
| F10 | Ficha: serviços | `/unidades/{id}/servicos` | PAR | Catálogo (DF5) | 21/11 | E5a |
| F11 | Ficha: equipamentos (aparelhos) | — (semântica diferente) | INC + DEC | B8 (DF1) | Completo; em 21/11, aba visível com aviso | E5b |
| F12 | Ficha: histórico | `GET /unidades/{id}/historico` | IMP | — | 21/11 | E4 |
| F13 | Ficha: verificações de qualidade | — | NÃO + DEC | B7 (spec 007) | Completo; em 21/11, as verificações calculadas no front sobre dados reais (só exibição) | E8 |
| F14 | Confirmar revisão | — | NÃO | B5 | Completo | E8 |
| F15 | Edição com diff | `PATCH` + If-Match | PAR | Observação nos metadados | 21/11 (central) | E4 |
| F16 | Cadastro de unidade | `POST /unidades` | PAR | "Solicitar cadastro" pelo distrito (B1) | 21/11 (central); solicitação completa | E4 / E6 |
| F17 | Propor alteração | — | NÃO + DEC | B1, B2 (DF2) | Completo | E6 |
| F18 | Aprovar e devolver | — | NÃO | B1 | Completo | E6 |
| F19 | Notificações | — | NÃO | B3 | Completo; em 21/11, sino visível e vazio | E7 |
| F20 | Painel de qualidade | `/dashboard/*` | PAR | B7 | 21/11 com as consultas de qualidade da 011; completo | E8 |
| F21 | Histórico geral | `/auditoria/eventos` (global) | PAR + DEC | B11 (escopo); DF9 | 21/11 para o escopo global; completo | E9 |
| F22 | Importar CSV | — | NÃO | B10 | Completo | E10 |
| F23 | Restaurar demonstração | `sgs-admin seed demo` (CLI, dev) | INC | **Não descartada:** sai da interface de produção e continua disponível como comando de dev, documentado | 21/11 | E2 |
| F24 | Tema, responsividade, acessibilidade | — | IMP (front) | Preservar | 21/11 | E1 |

## 5. Revisão de segurança XSS

### 5.1 Método
Um analisador extraiu **todas as 571 interpolações `${…}`** dos cinco `<script>`, com chaves balanceadas, e classificou cada uma. Os casos não triviais foram revistos à mão, no contexto.

**Pontos de inserção:**
- 20 atribuições de `innerHTML`, incluindo `#app` em `render()`, que recebe o HTML de todas as views, além de `#tbody`, `#htb`, `#bellPop`, `#eqEditor`, os modais (`openModal` → `s.innerHTML`), os toasts e as mensagens de erro de campo;
- nenhum `eval`, `new Function`, `document.write` nem `insertAdjacentHTML`.

### 5.2 Resultado com os dados de hoje
| Grupo | Qtde. | Situação |
|---|---|---|
| Passa por `esc()` ou por função que escapa: `esc`, `V` (`v ? esc(v) : …`), `diffTable`/`changeLine` (`esc(c.de)`, `esc(c.para)`), `bar` (`esc(label)`), `toast` (`esc(title)`, `esc(msg)`), `auditRow` | 168 | ✅ |
| Expressões sem dado do usuário: contagens, booleanos, classes CSS, `ic()`, `dsLabel(n)` com n numérico | 238 | ✅ |
| Revistas à mão | 165 | ver abaixo |

**Todo campo editável pelo usuário é escapado:**

| Campo | Linha(s) |
|---|---|
| nome da unidade | 1110, 1665, 1750, 1791 |
| CNES | 1217, 1462, 1513, 1908 |
| logradouro, número, complemento, bairro | 1516 |
| e-mail | 1519 |
| serviços | 1528, 1544 |
| nome do equipamento | 1569, 1593 |
| justificativa | 1667 |
| motivo da devolução | 1669 |
| observação | 1583, 1823 |
| texto da notificação | `esc(n.texto)` |
| nome e cargo de usuário | 1466, 1520, 1581, 1825 |
| linhas do CSV importado | 1907 a 1910 |
| busca vinda da URL | `value="${esc(p.get('q'))}"` |

Os parâmetros `tipo`, `grupo` e `ds` da URL são aplicados por `.value`, que é propriedade e não HTML; `tab` e `aba` só entram em comparação.

Os textos de notificação (linhas 1406 a 1424, 1705 a 1721), montados com `unit.nome` e `ME.nome` sem escape, **são escapados na exibição**.

**Conclusão:** com os dados locais de hoje, **não há XSS explorável**.

### 5.3 Pontos que viram risco com dados da API (precisam de escape na integração)
São seguros hoje só porque o valor é uma constante do código. Com a integração, o valor passa a vir da API ou do banco.

| Linha | Inserção sem escape | Origem depois da integração | Correção |
|---|---|---|---|
| 1253 (`fld`) + 1301 (`cnesHint`) | `${hint}` com `${t.id}` | código do tipo de unidade (`/referencias/tipos-unidade`) | `esc(t.id)` dentro do `cnesHint`; `fld` recebe texto, não HTML |
| 1368 | `${FIELD_LABEL[c.f] \|\| c.f}` | nome do campo vindo da trilha (`campo`) | `esc(FIELD_LABEL[c.f] \|\| c.f)` |
| 1367 | `${heads[1]}` | constante (manter) | — |
| 1168, 1266 | `${g}` (grupos) | áreas técnicas ou grupos (DF4) | `esc(g)` |
| 1268 | `${s}` (situações) | status ou situações da API (DF3) | `esc(s)` |
| 1276 | `value="${b}"` (bairros) | sugestões vindas do cadastro | `esc(b)` |
| 1596, 1599 | `${s}` (estado, sugestões de aparelho) | catálogo de infraestrutura (DF1) | `esc(s)` |
| 1569 | `${e.qtd}` | número vindo da API | `esc(e.qtd)` (defesa) |
| 1102, 1612, 1756 | `fieldsOf(...)`, `c.nome` das verificações | constantes hoje; vindo da API se B7 devolver os nomes das regras | `esc(...)` |
| `data-id="${u.id}"`, `href="#/unidade/${u.id}"`, `r-${c.id}` e similares (≈40 ocorrências) | ids em atributo | UUID da API | `esc(id)` em atributo, e `encodeURIComponent` em hash |
| 1331 | `href="#/unidade/${msg.unitId}"` | id vindo do 409 da API (`unidade_existente_id`) | idem |
| 956 a 960 (menu) | `${i[2]}` (rótulos), `dsLabel` | constantes, ou o nome do distrito vindo do `/me` | `esc(...)` se vier da API |

### 5.4 Controles que entram na integração
1. **Regra:** todo valor vindo da API passa por `esc()`, em texto e em atributo. Uma tag de template `html\`…\`` que escapa por padrão substitui o uso manual onde for possível, sem biblioteca.
2. **CSP no Caddy:**
   - `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`;
   - os scripts inline saem para arquivos;
   - os `style="…"` inline do protótipo (muitos) viram classes, ou, como **exceção registrada**, `style-src 'self' 'unsafe-inline'` só no CSS até a migração completa.
3. **Fonte local** (Atkinson Hyperlegible, OFL): sem Google Fonts.
4. **Teste estático no CI:** varredura dos `.js` do app que falha se uma interpolação dentro de template HTML não passar por `esc()` ou `html\`\``, com lista de exceções revisadas.
5. **Teste E2E de XSS:**
   - gravar pela API nomes, bairros, justificativas e motivos com payloads (`<img src=x onerror=…>`, `"><svg onload=…>`, `javascript:`);
   - abrir cada tela e conferir que nenhum `dialog` ou script dispara e que o console não registra violação da CSP.

## 6. Etapas: o que pode começar e o que fica bloqueado
**Pré-requisito comum:** a regra 1 do `AGENTS.md` exige spec aprovada para qualquer código, inclusive o do front. A **E0a** cria a spec nova do frontend; se você for o dono, aprova os requisitos e as tarefas, e o design precisa de mais 1 integrante.

| Etapa | Conteúdo | Pode começar? | Depende de |
|---|---|---|---|
| E0a | Spec 012 (frontend) e ADRs: front no mesmo repositório, sem build; Playwright | **Sim**, já (é documentação) | — |
| E0b | Specs e emendas: solicitações, notificações, infraestrutura, campos da unidade, 007, CSV, escopo do histórico | **Sim**, como proposta (Rascunho) | Aprovação: Rafael e o dono de cada uma |
| E1 | Esqueleto: separar o protótipo em `frontend/app`, fonte local, Caddy servindo o front, CSP | Depois da E0a | Spec 012 aprovada |
| E2 | Autenticação real (F01 a F04, F23 fora da UI) | Depois da E1 | Nada novo no backend (DF7 = rótulo) |
| E3 | Perfis e menu (F05), início com o resumo (F06 parcial) | Depois da E2 | DF8 (você) |
| E4 | Unidades: lista (F07), ficha (F09 com os campos que existem, F12), edição e cadastro do **central** (F15, F16) | Depois da E3 | Nenhuma emenda. **A edição de distrito e unidade fica escondida até DF2** (o backend permite, mas a regra do protótipo é só propor) |
| E5a | Serviços (F10) | Depois da E4 | DF5 (dados) |
| E5b | Infraestrutura (F11) | **Bloqueada** | DF1 + spec |
| E6 | Solicitações (F16 do distrito, F17, F18) | **Bloqueada** | DF2 + spec + matriz (Rafael) |
| E7 | Notificações (F19) | **Bloqueada** | Spec |
| E8 | Qualidade (F13, F14, F20, F06 e F07 completos) | Em parte: exibição calculada no front, sobre dados reais | Spec 007 (dono a definir) para a validação no backend; B5 |
| E9 | Histórico geral (F21) | Em parte: escopo global já funciona | B11 (emenda da 008) para o escopo do distrito |
| E10 | CSV (F08, F22) | **Bloqueada** | DF10 + spec |
| E11 | E2E, XSS, responsividade, CI | Junto de cada etapa | DF11 (ADR) |
| E12 | Usuários e senha (F03 completo; B13) | **Bloqueada** | Spec da 003 (usuário:manage); a matriz já tem a permissão |
| E13 | Campos que faltam (F09 completo; B4) e situação (DF3) | **Bloqueada** | Emenda da 006 (Rafael), cliente |

## 7. Escopo de 21/11 × escopo completo
**Escopo mínimo de 21/11**, só com o que já existe no backend e sem mexer em spec aprovada nem na matriz: E0a, E1, E2, E3, E4 e E5a, mais E8 e E9 em parte e os E2E dessas etapas.
- Login real com 2FA, sessão e logout. A demonstração sai da UI.
- Menu e telas por papel, a partir do `/me`.
- Início com os indicadores do `/dashboard/resumo`.
- Lista com busca e filtros existentes; ficha com dados existentes, serviços e histórico.
- Edição e cadastro pelo **Gestor de Dados**, com If-Match e diff.
- Qualidade: as consultas de qualidade da 011 e as 8 verificações calculadas no navegador, **só para exibição**; a validação continua no backend.
- Histórico geral para quem tem escopo global.

**Permanecem visíveis com o aviso "em desenvolvimento":**
- equipamentos (aparelhos);
- solicitações e validações;
- notificações;
- CSV;
- revisão.

Isso mantém as 24 funcionalidades presentes na interface.

**Escopo completo:** tudo acima, mais E5b, E6, E7, E8 completo, E9 completo, E10, E12 e E13, depois das decisões e specs do § 3 e § 6.

## 8. Critérios de aceite verificáveis por etapa
| Etapa | Critérios (todos automatizados, salvo indicação) |
|---|---|
| E0a | Spec 012 com `Status: Aprovado` nos três arquivos; ADRs com status; `make check` verde |
| E1 | `GET https://localhost/` devolve o app (200, `text/html`); `/api/v1/*` continua na API; a CSP vem no cabeçalho; o Playwright compara capturas com o protótipo em 1280, 860 e 390 px, com diferença visual abaixo de um limiar (ou revisão manual registrada); nenhuma requisição a domínio externo; console sem erros |
| E2 | E2E: login com usuário do seed, cadastro do TOTP (código gerado com `pyotp`), recarregar mantém a sessão (refresh silencioso), logout volta ao login e `/me` dá 401; senha errada mostra a mensagem única; a busca no código não acha `DEMO_PASS`, `DEMO_CODE`, `USERS` nem `seed(`; o `localStorage` só tem `sgs-theme` |
| E3 | Para cada papel do seed (7): o menu tem exatamente os itens previstos (tabela da spec 012); acessar a rota de outro perfil mostra "sem acesso" e a API responde 403 (teste direto da API com o mesmo token) |
| E4 | E2E: busca sem acento acha a unidade; o filtro por distrito reduz a lista; a ficha mostra os dados da API; o Gestor de Dados edita (200) e um segundo navegador com a versão antiga recebe 412 com mensagem; cadastro com CNES repetido mostra o 409 com o link da existente; o histórico mostra a alteração com autor e papel; **o distrito e a unidade não veem botão de edição** e o PATCH direto deles é tratado conforme DF2 (registrado) |
| E5a | Incluir e remover serviço; o histórico registra `unidade.servico_*` |
| E5b | Aparelho com quantidade e estado incluído, alterado e removido, auditado; o domínio "equipamento de saúde" e as consultas da 011 continuam passando |
| E6 | Integração e E2E: o distrito propõe (a ficha não muda; solicitação pendente); uma segunda proposta para a mesma unidade é recusada; o central aprova (a ficha muda numa transação; a auditoria tem autor e validador) ou devolve (motivo com 10+ caracteres; ficha intacta); quem propôs não aprova (403); outro distrito não vê a solicitação (404/403) |
| E7 | Os destinatários de cada evento estão corretos (teste por cenário); contador e "marcar como lida" persistem no banco; um usuário não lê a notificação de outro (403) |
| E8 | As 8 verificações batem com uma consulta SQL de conferência sobre o seed; a gravação inválida (CEP fora do Recife, DDD diferente de 81, CNES faltando para o tipo) é recusada pelo **backend** (422); a revisão grava `reviewed_at` e a auditoria |
| E9 | O distrito vê só eventos do seu DS; o Auditor vê os acessos; o Gestor de Dados não (DF9) |
| E10 | A exportação só traz o escopo; células que começam com `= + - @` saem neutralizadas; a importação recusa arquivo acima do limite, codificação inválida e colunas faltando; o dry-run não grava; a confirmação grava em transação com auditoria por linha |
| E11 | Os E2E de todas as etapas entregues passam no job `compose-smoke` do CI; o teste de XSS (§ 5.4) passa; o teste estático de escape passa |
| E12 | O Admin TI cria, desativa e redefine a senha de um usuário; outro papel recebe 403; tudo auditado |
| E13 | Os campos novos são gravados, validados e auditados; a migração aplica num banco vazio e no seed |

**Critérios globais de conclusão (inalterados):**
- funcionalidades preservadas, dados reais e nenhum mock em produção;
- autenticação, autorização e regras no backend;
- persistência no PostgreSQL;
- solicitações completas e CSV validado;
- responsivo;
- testes e E2E passando, documentação atualizada e CI verde.

## 9. Arquitetura recomendada (inalterada da versão 1)
- **Front:** JavaScript em módulos ES, sem framework, sem build e sem npm. HTML e CSS do protótipo preservados.
- **Servidor:** o Caddy serve `frontend/app/` no mesmo domínio da API, sem CORS. O refresh fica no cookie `HttpOnly` e o access token, em memória.
- **Organização:**
  - `js/api.js`: Bearer, refresh automático em 401, problem+json;
  - `auth.js`, `router.js`, `perms.js` (do `/me`, só conveniência), `ui/` e `views/`;
  - o `localStorage` só guarda o tema.
- **Dependências novas:** só `pytest-playwright` (dev), sujeito ao ADR do DF11. A fonte é um arquivo estático local.

## 10. Estratégia de testes (inalterada; complementa o § 8)
- **Backend:** testes de integração por endpoint novo, com auditoria na mesma transação.
- **Contrato:** `contracts/openapi.yaml`.
- **E2E:** Playwright contra o compose com o seed.
- **Segurança:** teste estático de escape, E2E de XSS e CSP.
- **Responsividade:** 3 larguras.

## 11. Riscos
- Aprovações pendentes (§ 3) podem não sair antes de 21/11. O escopo mínimo do § 7 não depende delas, exceto da E0a.
- **DF2 é a maior mudança:** alterar a matriz afeta os testes de escopo existentes e os usuários do seed.
- A paridade visual exige mover os scripts e estilos inline sem regressão.
- O compose completo (com o Caddy) não roda nesta máquina enquanto as portas 80/443 estiverem ocupadas pelo ambiente antigo; o CI cobre.
