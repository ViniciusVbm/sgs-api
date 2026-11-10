# 012 · Frontend SGS Recife · Design

- Status: Rascunho (revisão 4, 10/11/2026: P1 a P5 tratadas e pendências formais PF-01 a PF-07; revisão 3, 10/11/2026). Mudanças da revisão 3:
  - sincronização com a `novo/main` `9c37029`;
  - responsáveis atualizados;
  - decisões e premissas do Grupo 01 registradas;
  - seções de histórico, exportação e perfis-alvo;
  - matriz de integração.

  O G1 está aprovado (requisitos: Vinicius, 09/11/2026). **O G2 está pendente**: aguarda o registro do dono e do revisor (§ Registro de aprovação).
- Autor do design: Hélder (decisão do Grupo 01, 10/11/2026). Dono da spec: Vinicius (ViniciusVbm).
- Revisão do G2 indicada pelo grupo: Igor Fugagnoli (principal; **disponibilidade a confirmar**) e Erick Sanches (suplente).
- Requisitos: requirements.md (com a emenda documental 1, que aguarda o dono)
- Decisões: ADR-0010 (front no mesmo repositório, módulos ES, sem build), ADR-0011 (Playwright com Python), ambos Propostos

## Visão geral
O protótipo é dividido, sem redesenho, em arquivos estáticos servidos pelo Caddy no mesmo domínio da API.

| Ganho do mesmo domínio | Por quê |
|---|---|
| Sem CORS | front e API respondem pelo mesmo host |
| Cookie de refresh funciona | é `SameSite=Strict` e tem `Path=/api/v1/auth` |
| CSP restritiva | tudo vem de `'self'` |

Os módulos ES do navegador substituem o empacotador: não há npm nem build. Toda regra de negócio e de acesso continua no backend.

## Estrutura de diretórios
```
frontend/
  prototipo/            # referência, fora do Git (.gitignore)
  app/
    index.html          # o <body> do protótipo; só <script type="module" src="js/main.js">
    assets/
      css/app.css       # o <style> do protótipo (estilos inline viram classes aos poucos)
      fonts/            # Atkinson Hyperlegible (SIL OFL), local
      icons.svg         # os <symbol> do protótipo
    js/
      main.js           # bootstrap: refresh silencioso → /me → render
      api.js            # cliente HTTP
      auth.js           # login, 2FA, refresh, logout; token em memória
      perms.js          # derivação de menu e botões a partir do /me
      router.js         # hash router (rotas do protótipo)
      html.js           # esc() e tag html`` com escape automático
      ui/{modal,toast,format,form}.js
      views/{login,inicio,unidades,unidade,nova,solicitacoes,qualidade,historico,importar,sem-acesso}.js
tests/e2e_front/        # Playwright (ADR-0011), marcados slow
```

## Entrega pelo Caddy
`docker/caddy/Caddyfile`, alterado na tarefa T1:
- `/api/*`, `/health/*` e `/.well-known/*` são encaminhados (`reverse_proxy`) para `api:8000`;
- o resto é servido por `file_server` a partir de `/srv/frontend` (volume `../frontend/app:/srv/frontend:ro`), com `try_files {path} /index.html`.
- **Cabeçalhos das respostas estáticas:**
  - `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`;
  - `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`.
- `style-src 'unsafe-inline'` é uma **exceção temporária**, porque o protótipo usa muitos `style="…"`. Sai quando eles virarem classes (tarefa futura, registrada).

## Rotas consumidas (contrato)
Todas já existem e estão documentadas em `docs/api/endpoints.md`. Nesta spec, o front não cria rota nenhuma.

| Tela | Método e rota | Permissão (backend) | Requisitos |
|---|---|---|---|
| Login, 2FA | `POST /api/v1/auth/login`, `/auth/mfa/enroll`, `/auth/mfa/confirm`, `/auth/mfa/verify` | pública | R2.1 a R2.3 |
| Sessão | `POST /api/v1/auth/refresh`, `/auth/logout` | cookie e anti-CSRF / Bearer | R2.4 a R2.6 |
| Perfil | `GET /api/v1/me` | autenticado | R3.1 |
| Início | `GET /api/v1/dashboard/resumo` | `dashboard:read` | R4.1 |
| Lista | `GET /api/v1/unidades` | `unidade:read` | R5.1, R5.2 |
| Ficha | `GET /api/v1/unidades/{id}`, `/historico` | `unidade:read`, `auditoria:read` | R6.1, R6.2 |
| Edição | `PATCH /api/v1/unidades/{id}` (If-Match) | `unidade:update` | R7.1, R7.2 |
| Cadastro | `POST /api/v1/unidades` | `unidade:create` | R7.3 |
| Serviços | `GET/POST/PATCH/DELETE /api/v1/unidades/{id}/servicos[/{sid}]` | `unidade:read` / `servico:write` | R8.1 |
| Referências | `GET /api/v1/referencias/{tipo}` | `unidade:read` | R5.1, R8.1 |
| Qualidade | `GET /api/v1/dashboard/consultas/*`, `/dashboard/inventario` | `dashboard:read` | R12.1 |
| Histórico geral | `GET /api/v1/auditoria/eventos` | `auditoria:read` global | R12.2 |
| Verificação da cadeia | `POST /api/v1/auditoria/verificar` | `auditoria:read` global | R12.4 |
| Papéis (Admin TI) | `GET /api/v1/admin/papeis`, `GET/POST/DELETE /api/v1/admin/atribuicoes` | `papel:assign` | R3.2 (DF8) |

**Rotas do backend necessárias ao escopo completo:** solicitações, notificações, infraestrutura, revisão, exportação CSV/PDF, histórico geral no escopo, usuários e campos da unidade.
- Cada uma terá spec ou emenda própria (`docs/PLANO_INTEGRACAO_FRONTEND.md` § 6). Nenhuma está nesta spec.
- Conferido em `9c37029`: nenhuma delas existe no `contracts/openapi.yaml`.

## Histórico (R6.2, R12.2, R12.3; Grupo-DF9)
- **Por unidade:** `GET /api/v1/unidades/{id}/historico`.
  - Parâmetros: `de` (inclusivo), `ate` (exclusivo), `autor` (id), `campo`, `pagina` e `tamanho`.
  - Resposta: `PaginaOut[EventoOut]`, com `quando`, `acao`, `autor {id, nome, papeis}` e `mudancas[{campo, rotulo, de, para}]`, do mais recente para o mais antigo.
  - A aba aparece se algum escopo de `auditoria:read` do `/me` cobre a unidade (R6.2).
  - A tela oferece os filtros de período e de autor. Os filtros têm testes do backend que detectam regressão (008/T6, `tests/integration/audit/test_consulta_trilha.py`).
- **Geral (perfil central):** `GET /api/v1/auditoria/eventos`.
  - Filtros: `de`, `ate`, `acao`, `entidade_tipo`, `entidade_id` e `autor`, com paginação.
  - Exige `auditoria:read` **global** (Gestor de Dados e Auditor).
  - A Grupo-DF9 cita `GET /api/v1/historico`, mas **essa rota não existe**. A interface usa a rota existente, sem inventar contrato. Criar um alias ou renomear a rota é uma emenda da 008 (dono: Vinicius).
- **Geral no escopo do distrito** (R12.3, Grupo-DF9, "visibilidade pelo escopo hierárquico"): **não existe na API**, porque a trilha geral exige escopo global. A tela fica "em desenvolvimento" até a emenda da 008.
- **Datas:** exibidas no fuso de Recife. Os filtros são enviados em ISO 8601 com fuso.
- **Exportação do histórico:** segue a Grupo-DF15 (§ Exportação), não a DF9.

## Exportação (R5.4; DF10, DF15, Grupo-DF15)
- **Decidido** (DF10 e Grupo-DF15):
  - quem gera é o backend, no escopo do usuário;
  - CSV para dados e PDF para relatório legível;
  - cada exportação vira evento de auditoria com usuário, data e hora, escopo e formato;
  - primeira versão: lista filtrada de unidades e de equipamentos e resumo do dashboard.
- **O front:**
  - chama a rota de exportação com os filtros da tela;
  - baixa o arquivo (`Content-Disposition`);
  - mostra o 403 da API;
  - **não gera CSV nem PDF no navegador**.
- **Situação:**
  - não existe rota de exportação, e o botão fica visível e desabilitado (R13);
  - pendentes: colunas do CSV, layout do PDF (P5), spec do backend e permissão por papel;
  - a permissão por papel depende da premissa Grupo-DF13, porque hoje o Técnico Distrital e o Gestor de Unidade não têm `relatorio:export`.
- **Segurança, para a spec do backend:** neutralizar células iniciadas por `=`, `+`, `-` ou `@` (R5.4); limitar o volume; usar `Content-Type` correto.

## Modelo de dados / migrações
Nenhum. Esta spec não altera o banco. O front não guarda dados de negócio. No navegador fica só `localStorage['sgs-theme']`.

## Fluxo
1. **Abertura:** `main.js` chama `auth.refresh()`. Com sucesso, segue para `GET /me` → `perms` → `router`. Com 401, mostra a view de login.
2. **Login:** `login` → (`enroll` → `confirm`) ou `verify`. O token fica guardado numa variável do módulo `auth.js`.
3. **Chamada (`api.js`):**
   - `fetch('/api/v1…', {headers: {Authorization: Bearer, 'Content-Type': 'application/json'}})`;
   - 401: um refresh e repetir uma vez;
   - problem+json vira `ErroDaApi {status, detail, errors[], extensoes}`.
4. **Erros:**

| Status | O que a view faz |
|---|---|
| 403 | Toast "Você não tem permissão para esta ação." |
| 404 | View de "não encontrado" |
| 409 | Erro no campo, com o link `unidade_existente_id` |
| 412 | Toast e recarga da ficha |
| 422 | `errors[{campo,mensagem}]` vira erro em cada campo (nomes da API: `nome`, `cep`…) |
| 429 | Toast "aguarde um minuto" |
| 5xx | Toast genérico com o `X-Request-ID` |

5. **Carregamento:** cada view mostra um esqueleto ou "carregando…" e o estado vazio do protótipo.
6. **Atualização:** recarrega ao navegar; nesta spec não há consulta periódica (vale só para notificações, no escopo completo).

## Perfis (R3.2, R3.5, DF8)
Menu e botões derivados **só das permissões existentes** na matriz da spec 003 (`/me`), sem ampliá-la. Conferido contra a matriz atual, incluindo os ajustes da 0011_09:

| Papel | Permissões relevantes (matriz atual) | Início | Menu (escopo mínimo) | Ações [M] |
|---|---|---|---|---|
| GESTOR_DADOS (central) | `unidade:*` G, `servico:write` G, `auditoria:read` G, `dashboard:read` G | Início | Início, Unidades, Cadastrar unidade, Validações\*, Qualidade, Histórico, Importar\* | editar e cadastrar (R7.1, R7.3), serviços (R8.1) |
| TECNICO_DISTRITAL (distrito) | `unidade:read` G, `unidade:update` D, `servico:write` D, `auditoria:read` D, `dashboard:read` D | Início | Início, Unidades (abre filtrada pelo DS, R3.5), Solicitar cadastro\*, Solicitações\*, Qualidade, Histórico\*\* | só leitura; propor\* (R7.4) |
| GESTOR_UNIDADE (unidade) | `unidade:read` G, `unidade:update` U, `servico:write` U, `auditoria:read` U, `dashboard:read` U | Minha unidade | Minha unidade, Minhas solicitações\*, Histórico da unidade | só leitura; propor\* (R7.4) |
| COORD_TECNICO | `unidade:read` G, `unidade:update`/`create` A, `auditoria:read` A, `dashboard:read` A | Início | Início, Unidades, Solicitações\*, Qualidade, Histórico\*\* | só leitura até DF14 (R7.4) |
| DIRETORIA | `unidade:read` G, `dashboard:read` G | Início | Início, Unidades (só leitura), Qualidade | nenhuma; sem aba de histórico (R6.2) |
| AUDITOR | `unidade:read` G, `auditoria:read` G, `auditoria:read_acessos` G | Histórico | Histórico geral, Verificação da cadeia, Unidades (só leitura) | `POST /auditoria/verificar` |
| ADMIN_TI | `papel:assign` G, `usuario:manage` G, `auditoria:read_acessos` G | Papéis | Papéis e atribuições (`/admin/papeis`, `/admin/atribuicoes`), Usuários\* | atribuir e remover papéis |

- \* Visível com a indicação "em desenvolvimento" (R13).
- \*\* Histórico geral só com `auditoria:read` global (R12.2); para escopo menor, "em desenvolvimento", e o histórico da ficha continua disponível.
- **ADMIN_TI** tem `auditoria:read_acessos`, mas não `auditoria:read`. A API atual (`/auditoria/eventos` exige `auditoria:read`) não lhe permite listar eventos, e a interface não oferece essa tela. Fica registrado; mudar isso é emenda da 008 ou da matriz da 003 (dono das duas: Vinicius).
- **Leitura global:** pela matriz atual, Técnico Distrital, Gestor de Unidade e Coordenador leem todas as unidades (`unidade:read` G). O recorte por DS ou por unidade do protótipo é só navegação (R3.5) até a DF13.

### Perfis-alvo das premissas do Grupo 01 (escopo completo; **não implementado**, aguarda o cliente)
As premissas Grupo-DF2, Grupo-DF13 e Grupo-DF14 (requirements § Decisões do Grupo 01) descrevem três perfis. A tabela é o **alvo** do escopo completo, não o comportamento do escopo mínimo. A interface só passa a ele quando três coisas existirem:
- a ratificação do cliente;
- a emenda da 003 (leitura por escopo, `alteracao:validar` e `relatorio:export` por papel);
- a spec de solicitações.

| Perfil (papel provável) | Escopo de leitura | Edição comum (nome, endereço, CEP, telefone) | Campos sensíveis (CNES, tipo, status, distrito, vínculo) | Aprova | Exporta | O que falta no backend |
|---|---|---|---|---|---|---|
| Gestora central (`GESTOR_DADOS`) | rede | direta | direta | comuns e sensíveis | rede | fluxo de aprovação; exportação |
| Coordenador do DS (`TECNICO_DISTRITAL`: correspondência por escopo, P2) | distrito | direta ou proposta (PF-01) | gera solicitação ao central | comuns do distrito (PF-02) | distrito | leitura por escopo; solicitações; `alteracao:validar` D; `relatorio:export` D |
| Gerente (`GESTOR_UNIDADE`) | unidade | direta ou proposta (PF-01) | gera solicitação | não | unidade | leitura por escopo; solicitações; `relatorio:export` U |

**Fluxo-alvo da edição (Grupo-DF14):**
1. O diff da ficha separa os campos comuns dos sensíveis.
2. Os comuns vão por `PATCH /unidades/{id}` com `If-Match`, como no [M].
3. Os sensíveis vão para uma solicitação, numa rota que ainda não existe, com justificativa.
4. Se o usuário alterar os dois tipos no mesmo envio, a tela avisa que serão duas operações.

**Hoje, no backend:**
- distrito, tipo e CNES dão 403 (`campos_estruturais`) fora do escopo global ou de área;
- o status **não** é bloqueado;
- o "vínculo" não existe no modelo (P3, PF-04).

Até a ratificação e o backend, vale o [M]: só o escopo global edita (R7.4).

**Pendências e efeito na interface** (requirements § Pendências formais):
- **PF-01:** aplicar na hora ou propor. A interface não tem "aprovar" nem "devolver" para alterações comuns, porque a API aplica na hora e não tem fluxo de aprovação. Se a decisão for "na hora", o status precisa virar estrutural no backend (emenda da 006) **antes** de liberar a edição D/U. Esconder o campo na tela não basta.
- **PF-02 e PF-03:** aprovação pelo coordenador do DS e regra do `COORD_TECNICO`. Sem aprovação na interface.
- **PF-04 e PF-05:** vínculo e campos não listados. Nada novo é exibido. A classificação provisória dos campos está na tabela de P4 dos requisitos.
- **PF-06:** exportação. O botão fica desabilitado, e o navegador não gera arquivo.
- **PF-07:** ratificação pelo cliente. O [M] não depende dela.

**Rótulo de indisponibilidade:** "em desenvolvimento", o texto aprovado no R13.1. Não se usa "Previsto", para não mudar o critério aprovado. Os controles indisponíveis ficam com `disabled` e `aria-disabled="true"`, sem `onclick` de API e sem toast de sucesso.

## Segurança
- **XSS:** `html.js` exporta `esc()` (o mesmo do protótipo) e a tag `html\`…\`` que escapa toda interpolação, salvo o que for marcado como HTML confiável (`raw()`), só para o HTML gerado pelo próprio código. Os 12 grupos de inserção sem escape apontados na auditoria (plano § 5.3: `cnesHint`/`fld(hint)`, `FIELD_LABEL[c.f] || c.f`, grupos, situações, bairros, estados, quantidades, ids em atributos e no hash) passam a ser escapados.
- **Login (DF7):** o campo se chama "Usuário" e envia o `username`; o contrato não muda. **2FA (DF6):** a chave e a URI aparecem como texto copiável, sem QR Code e sem biblioteca nova.
- **Token** só em memória; o refresh fica no cookie `HttpOnly; Secure; SameSite=Strict`. Sem `localStorage` de dados (R15.3).
- **CSP** no Caddy (seção Entrega); sem `eval` (R15.4); fonte local (R1.3).
- **A autorização é do backend:** o front esconde o que o `/me` não permite e trata o 403; nenhuma regra de acesso fica só no JavaScript.
- **Nenhum segredo** de demonstração no código (R2.10). A demonstração é `sgs-admin seed demo` em dev.

## Decisões e alternativas
- Sem framework (ADR-0010). Alternativas: React, Vue ou Svelte, que exigiriam build e npm e reescreveriam o protótipo.
- Servir pelo Caddy. Alternativa: `StaticFiles` do FastAPI, que misturaria o front no processo da API, com CSP e cache menos simples.
- Playwright em Python (ADR-0011). Alternativa: Playwright em Node, que traria npm.
- Verificações de qualidade calculadas no front só para exibição (R6.3), até a spec 007; a gravação continua validada pelo backend.

## Riscos
- **Paridade visual** ao separar 1.935 linhas. Mitigação: comparação por captura (Playwright) contra o protótipo.
- **Estilos inline e CSP:** a exceção `unsafe-inline` em `style-src` é registrada e temporária.
- **Decisões pendentes** (DF1 a DF5, DF9, DF13 a DF15, premissas do Grupo 01 e perguntas P1 a P5; DF7, DF8 e DF10 já foram decididas): as telas ficam visíveis e desabilitadas (R13), e o escopo mínimo não depende delas.
- **Premissas não ratificadas:** se o cliente mudar Grupo-DF2, Grupo-DF13 ou Grupo-DF14, o escopo completo muda. O mínimo não é afetado, porque não depende delas.
- **Rota do histórico geral:** a Grupo-DF9 cita `/api/v1/historico`, que não existe. A interface usa `/api/v1/auditoria/eventos`, e uma emenda da 008 que renomeie a rota exigiria mudar uma linha do `api.js`.
- **Portas 80/443 ocupadas** nesta máquina pelo ambiente antigo: os E2E rodam num projeto compose isolado com portas alternativas, ou no CI.

## Estratégia de testes
- **E2E** (`tests/e2e_front/`, Playwright, `slow`), contra o compose com `sgs-admin seed demo`:
  - login com TOTP gerado por `pyotp` (cadastro e verificação), recarga, logout;
  - menu por papel (os 7);
  - lista, busca, filtros e paginação;
  - ficha e histórico;
  - edição com 412, 409 e 422;
  - cadastro;
  - serviços;
  - qualidade;
  - telas "em desenvolvimento" visíveis;
  - larguras de 1280, 860 e 390 px.
- **XSS:** dados com payloads gravados pela API; nenhum `dialog` dispara e o console não registra violação de CSP.
- **Estático** (pytest, sem dependência nova): os arquivos `js/` não têm `eval` nem `new Function`, nem senhas ou códigos de demonstração. Toda interpolação de template HTML passa por `html\`\`` ou `esc()` (lista de exceções revisadas).
- **Caddy:** teste e2e de `/`, `/api/v1/*` e do cabeçalho CSP.

## Matriz de integração (conferida em `9c37029`, 10/11/2026)
**Classificação:**
- **API** = implementável com a API existente;
- **Parcial** = parcialmente implementável;
- **Backend** = bloqueada por backend;
- **Decisão/gate** = bloqueada por decisão ou gate;
- **Fora** = fora do escopo aprovado.

**Estado do frontend:** em todas as linhas, a funcionalidade existe só no protótipo, com dados locais, e **nenhum código de interface foi escrito**. Todas as linhas [M] estão também bloqueadas pelo gate: o G2 e o G3 estão pendentes (`AGENTS.md`, regra 1).

| Tela/fluxo | Requisito | Endpoint | Estado da API | Estado do frontend | Dependência | Classificação |
|---|---|---|---|---|---|---|
| Entrega no mesmo domínio, CSP | R1.1, R15.2 | Caddy `file_server` + proxy de `/api/*`, `/health/*`, `/.well-known/*` | O Caddyfile atual só faz `reverse_proxy api:8000`; `file_server` e CSP entram na T1 | não iniciado | G2/G3 | API (infra) |
| Aparência, tema, responsivo, acessibilidade | R1.2 a R1.5 | — | — | protótipo | G2/G3 | API |
| Carregando, vazio, erro | R1.6 | `application/problem+json` (`detail`, `errors`) | existe | não iniciado | G2/G3 | API |
| Login | R2.1, R2.7, R2.11 | `POST /auth/login` | existe (`mfa_required`, `mfa_enrollment_required`, `mfa_token`; `access_token` só com `MFA_OBRIGATORIO=false`) | protótipo com usuários fixos (sai) | G2/G3 | API |
| Cadastro do 2FA | R2.2 | `POST /auth/mfa/enroll` (`otpauth_uri`), `/auth/mfa/confirm` | existe | não existe no protótipo | G2/G3 | API |
| Verificação do 2FA | R2.3 | `POST /auth/mfa/verify` | existe | protótipo com código fixo (sai) | G2/G3 | API |
| Sessão: refresh, 401, logout | R2.4 a R2.6 | `POST /auth/refresh` (`X-Requested-With: sgs`, `Origin` em `CORS_ORIGINS`), `/auth/logout` | existe; o compose tem `https://localhost` | não iniciado | G2/G3 | API |
| Esqueci a senha | R2.8 / R2.9 | — | sem rota de redefinição | orientação no protótipo | R2.9: emenda da 003 | API (R2.8) / Backend (R2.9) |
| Demonstração fora da UI | R2.10 | `sgs-admin seed demo` | existe | `seed()` e `resetDemo` no protótipo (saem) | G2/G3 | API |
| Menu e botões por permissão | R3.1 a R3.4, DF8 | `GET /me` | existe (`papeis`, `permissoes` com escopo) | perfis fixos no protótipo | G2/G3 | API |
| Recorte do DS e da unidade | R3.5 | `GET /me`, `GET /unidades?distrito=` | existe (só navegação; leitura global) | protótipo | Restrição real: Grupo-DF2 (ratificação) + emenda da 003 (T23) | API (navegação) / Decisão (restrição) |
| Início | R4.1 | `GET /dashboard/resumo` | existe, no escopo de `dashboard:read` (0011_09) | protótipo | G2/G3 | API |
| Início completo | R4.2 | — | sem solicitações nem regras da 007 | protótipo | spec de solicitações, 007 | Backend |
| Lista, busca, filtros, paginação | R5.1, R5.2 | `GET /unidades`, `GET /referencias/{tipo}` | existe (`q`, `tipo`, `area`, `distrito`, `status`, `com_pendencias`, `ordem`, `pagina`, `tamanho`) | protótipo | G2/G3 | API |
| Filtros extras | R5.3 | — | sem bairro, sem as 8 verificações, sem "aguardando" | protótipo | 006 (Hélder), 007, solicitações | Backend |
| Exportação CSV/PDF | R5.4, Grupo-DF15 | — | **não existe** | o protótipo gera CSV no navegador (não será reaproveitado: DF10) | spec do backend; P5; permissão (Grupo-DF13) | Backend + Decisão |
| Ficha: dados e serviços | R6.1 | `GET /unidades/{id}` (`ETag`) | existe (devolve ids; nomes pelas referências) | protótipo | G2/G3 | API |
| Histórico da ficha | R6.2, Grupo-DF9 | `GET /unidades/{id}/historico` | existe, com filtros e paginação | protótipo | G2/G3 | API |
| Verificações de qualidade | R6.3 | dados de `GET /unidades/{id}` | parcial: número do endereço e horário não existem → "não verificável ainda" | protótipo | 006 (campos) | Parcial |
| Campos e situações da unidade | R6.4 | — | sem número, complemento, e-mail, horário editável nem as 4 situações | protótipo | DF3; emenda da 006 (Hélder) | Backend + Decisão |
| Confirmar revisão | R6.5 | — | não existe | protótipo | emenda da 006 | Backend |
| Edição central com diff | R7.1, R7.2 | `PATCH /unidades/{id}` (`If-Match`; 409, 412, 422, 403 `campos_estruturais`) | existe | protótipo | G2/G3 | API |
| Cadastro central | R7.3 | `POST /unidades` | existe | protótipo | G2/G3 | API |
| Edição e proposta pelo distrito e pela unidade | R7.4, R7.5, R10.2; Grupo-DF13/DF14 | — (o `PATCH` existe, mas as premissas pedem solicitação para os sensíveis) | sem rotas de solicitação | protótipo | ratificação; P1 a P4; spec de solicitações; emenda da 003 | Decisão/gate + Backend |
| Observação no modal | R7.6 | — | o `PATCH` recusa campos extras | protótipo | emenda da 006 | Backend |
| Serviços | R8.1 | `GET/POST/DELETE /unidades/{id}/servicos[/{id}]`, `GET /referencias/tipos-servico` | existe | protótipo | G2/G3; catálogo (DF5) | API |
| Equipamentos (aparelhos) | R9.1, R9.2 | — (`/unidades/{id}/equipamentos` é equipamento de saúde, outro conceito) | sem entidade de infraestrutura | protótipo | DF1; spec de infraestrutura | API (aba visível, R9.1) / Backend + Decisão (R9.2) |
| Solicitações e validações (menu) | R10.1 | — | — | protótipo | G2/G3 | API (só "em desenvolvimento") |
| Notificações | R11.1, R11.2 | — | não existe | protótipo | spec de notificações | API (R11.1) / Backend (R11.2) |
| Painel de qualidade | R12.1 | `GET /dashboard/consultas/*`, `/dashboard/inventario` | existe | protótipo | G2/G3 | API |
| Histórico geral (central) | R12.2, Grupo-DF9 | `GET /auditoria/eventos` | existe (a Grupo-DF9 cita `/historico`, que não existe) | protótipo | G2/G3; rota `/historico`: emenda da 008 | Parcial (o nome da rota diverge) |
| Histórico geral no escopo do distrito | R12.3 | — | a trilha geral exige escopo global | protótipo | emenda da 008; DF9 | Backend + Decisão |
| Verificação da cadeia | R12.4 | `POST /auditoria/verificar` | existe (`auditoria:read` global) | não existe no protótipo | G2/G3 | API |
| Papéis e atribuições (Admin TI) | R3.2 (DF8) | `GET /admin/papeis`, `GET/POST/DELETE /admin/atribuicoes` | existe | não existe no protótipo | G2/G3 | API |
| Importar planilha | R14.1, R14.2 | — | não existe | protótipo | spec de importação | API (R14.1, visível) / Backend (R14.2) |
| Segurança da interface | R15.1 a R15.4 | — | — | 12 grupos de inserção sem escape no protótipo (plano § 5.3) | G2/G3 | API |
| Leitura limitada ao escopo | Grupo-DF2 (DF13) | `unidade:read` com escopo D/U | **não**: a leitura é global | — | ratificação; emenda da 003 e migração | Decisão + Backend |

**Ordem de implementação, quando o G2 e o G3 forem aprovados:**
1. T1 a T3: estrutura, entrega e base;
2. T4: autenticação, sessão e 2FA;
3. T5: perfis;
4. T6: início;
5. T7 e T8: lista e ficha;
6. T9 e T10: edição e serviços;
7. T11: histórico geral e cadeia;
8. T12: "em desenvolvimento";
9. T13 e T14: XSS, responsividade, E2E e documentação.

Equipamentos (aparelhos), exportação e o fluxo de aprovação ficam no escopo completo (T15, T16 e T21), bloqueados pelas dependências da tabela.

## Roteiro para a revisão do G2
Material para o revisor (Igor Fugagnoli, ou Erick Sanches como suplente). O revisor confere:
1. **Perfis:**
   - a tabela do escopo mínimo bate com a matriz atual (`docs/architecture/arquitetura-conceitual.md` § 4 e `0011_09`);
   - a tabela dos perfis-alvo está marcada como não implementada.
2. **Escopos:** o recorte do R3.5 é só navegação; a leitura por escopo depende da Grupo-DF2 e da 003.
3. **Edição:** o [M] só permite edição pelo escopo global, com If-Match; o fluxo comum/sensível é o alvo, dependente do backend.
4. **Telas e endpoints:** cada linha da matriz de integração aponta uma rota do `contracts/openapi.yaml` ou declara que não há rota.
5. **Histórico e exportação:** nenhuma rota é inventada (`/historico` e exportação estão marcadas como inexistentes).
6. **Estados:** carregando, vazio e erro (Fluxo, itens 4 e 5; R1.6); 401, 403, 409, 412, 422 e 429 tratados.
7. **Pendências:** P1 a P5 tratadas, e PF-01 a PF-07 com a solução provisória segura (§ Perfis-alvo).
8. **Segurança:** CSP, XSS, token em memória, nada de segredo no código.
9. **Testes:** a estratégia cobre os 7 papéis e os 3 perfis de referência, com E2E em Playwright.

O parecer é registrado como **Approve** no PR que trouxer a spec, ou como pedido de mudanças com os itens do roteiro.

## Registro de aprovação (G2)
Regra (`steering/sdd-workflow.md`): o design é aprovado pelo **dono da spec + 1 integrante**, e só depois do G1 (requisitos aprovados). O agente não registra aprovação de ninguém.

**Indicação do grupo (10/11/2026):**
- revisor principal: Igor Fugagnoli, com **disponibilidade ainda não confirmada**;
- suplente: Erick Sanches;
- autor do design: Hélder.

Em 10/11/2026 não havia evidência de que o Igor tenha aceitado a revisão nem parecer registrado. Ainda não existe PR com a spec 012.

Este registro fica **em branco** até cada pessoa aprovar de fato. Cada aprovador faz uma das duas coisas, de preferência as duas:
1. **No GitHub** (prova verificável): aprova (*Approve*) o PR que traz esta spec, num comentário de revisão citando "Aprovo o design da spec 012 (G2)".
2. **Neste arquivo:** acrescenta a própria linha na tabela abaixo, no PR ou em commit de documentação feito por ele.

| Integrante | Papel no G2 | Data | Evidência (link do PR ou da revisão) |
|---|---|---|---|
| | Dono (Vinicius) | | |
| | Integrante: Igor Fugagnoli (principal) ou Erick Sanches (suplente) | | |

Com as duas linhas preenchidas e o G1 aprovado, a linha `Status` passa a `Aprovado (<dono> e <integrante>, DD/MM/AAAA)`. A aprovação coletiva do time sobre a direção da integração (`docs/PLANO_INTEGRACAO_FRONTEND.md`) não substitui o registro individual exigido pelo fluxo.
