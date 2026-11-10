# 012 · Frontend SGS Recife · Tarefas

- Status: Rascunho (revisão 4, 10/11/2026: T1 a T4 detalhadas com arquivos e contratos, pendências PF-01 a PF-07 ligadas às tarefas bloqueadas, R5.5 proposto na T21; revisão 3: ajustes do G3; preparado para o G3 do dono, **só depois do G2**)
- Depende de:
  - 002, 003, 006, 008, 009 (APIs existentes, conferidas em `novo/main` `9c37029`);
  - ADR-0010 e ADR-0011 (Propostos).
- **Ordem de aprovação** (`steering/sdd-workflow.md`):
  1. `requirements.md` aprovado (G1: Vinicius, 09/11/2026; a emenda documental 1 aguarda o dono);
  2. `design.md` aprovado pelo dono + 1 integrante (G2: Igor Fugagnoli, ou Erick Sanches como suplente; pendente);
  3. este arquivo aprovado pelo dono (G3).

  **Este arquivo não pode ser aprovado antes do design**, e nenhuma tarefa é implementada antes dos três estarem `Aprovado` (`AGENTS.md`, regra 1).

Cada tarefa é pequena (até ~300 linhas de diff, sem contar o código do protótipo **movido** sem alteração) e testável, e cobre os requisitos citados. Só ganha `[x]` quando o teste citado passa no `make check` ou no CI (o job `quality` roda nos PRs; os E2E são `slow`).

## Escopo mínimo (21/11/2026)
- [x] T1. **(Exceção pontual do dono, 10/11/2026: implementada antes do G2 e do G3; ver `steering/sdd-workflow.md` § Exceção pontual: spec 012, tarefa T1.)** Entrega pelo Caddy: `file_server` de `frontend/app`, proxy de `/api/*`, `/health/*` e `/.well-known/*`, CSP e cabeçalhos; `index.html` mínimo
  - Requisitos: R1.1, R15.2
  - Arquivos:
    - `docker/caddy/Caddyfile`: hoje só tem `reverse_proxy api:8000`. Passa a ter `handle /api/*`, `/health/*` e `/.well-known/*` → `reverse_proxy api:8000`; o resto vai para `root * /srv/frontend`, `try_files {path} /index.html` e `file_server`, com os cabeçalhos do design só nas respostas estáticas;
    - `docker/compose.yml`: volume `../frontend/app:/srv/frontend:ro` no serviço `caddy`;
    - `frontend/app/index.html`;
    - `.gitignore`: `frontend/prototipo/`, já aplicado em 10/11/2026.
  - Dependências: nenhuma de backend. O CSP não pode bloquear `connect-src 'self'`, usado pela API no mesmo domínio.
  - Pronto quando: `tests/e2e/test_frontend_entrega.py -m slow` passa, num projeto compose próprio e com portas alternativas, porque 80 e 443 podem estar ocupadas, como no `test_tls_banco.py`:
    - `/` serve HTML com CSP;
    - `/api/v1/me` sem token dá 401 `application/problem+json` vindo da API;
    - `/health/ready` dá 200;
    - `/.well-known/jwks.json` dá 200;
    - uma rota desconhecida do front devolve o `index.html`.
  - Concluída em 10/11/2026.
    - **Prova:** `tests/e2e/test_frontend_entrega.py` (`-m slow`), 5 aprovados, no projeto compose `sgs-api-e2e-front` com as portas 18080 e 18443 e TLS conferido contra a CA interna do Caddy.
    - **Sensibilidade:** tirar `/api/*` do matcher derruba 2 testes; tirar a CSP derruba 1.
    - **`make check`:** 881 aprovados, 3 pulados.
    - **Arquivos:** `docker/caddy/Caddyfile`, `docker/compose.yml` (portas `SGS_HTTP_PORT` e `SGS_HTTPS_PORT`, com padrão 80 e 443, e o volume do front), `frontend/app/index.html`.
    - O `index.html` é um marcador honesto ("interface em implantação"), sem funcionalidade simulada; as telas vêm da T2 em diante, depois do G2 e do G3.
- [ ] T2. Mover CSS, ícones e fonte local do protótipo para `assets/`, sem mudança visual
  - Requisitos: R1.2, R1.3, R1.5
  - Arquivos:
    - `frontend/app/assets/css/app.css`: o `<style>` do protótipo;
    - `frontend/app/assets/icons.svg`: os `<symbol>`;
    - `frontend/app/assets/fonts/`: Atkinson Hyperlegible, SIL OFL, com a licença junto.
  - Dependência: a T1; e o Playwright no grupo `dev` do `pyproject.toml` (ADR-0011, Proposto), com o navegador instalado por `playwright install chromium`.
  - Pronto quando: `tests/e2e_front/test_aparencia.py` passa (capturas em 1280, 860 e 390 px comparadas à referência; nenhuma requisição externa).
- [ ] T3. `html.js` (`esc`, `html` com escape), `ui/` (modal, toast, format, form, **estados de carregando, vazio e erro**) e `router.js`, a partir do protótipo
  - Requisitos: R15.1, R15.4, R1.5, **R1.6**
  - Arquivos: `frontend/app/js/html.js`, `frontend/app/js/router.js` (hash router), `frontend/app/js/ui/{modal,toast,format,form,estado}.js`.
  - Os 12 grupos de inserção sem escape do protótipo (plano § 5.3) passam por `esc()` ou pela tag `html` com escape.
  - Dependência: a T1.
  - Pronto quando:
    - `tests/architecture/test_frontend_estatico.py` passa (sem `eval`/`new Function`; interpolações escapadas);
    - `tests/e2e_front/test_estados.py` passa (carregando enquanto a API não responde; vazio sem itens; erro com o `detail` da API, incluindo o 5xx com `X-Request-ID`).
- [ ] T4. `api.js` e `auth.js`:
  - login (campo "Usuário", DF7);
  - cadastro do 2FA com chave e URI em texto (DF6) e verificação;
  - **login direto quando a API devolve `access_token` (`MFA_OBRIGATORIO=false`, dev)**;
  - refresh silencioso, 401 → refresh → repetir, logout;
  - remoção de `USERS`, `DEMO_PASS`, `DEMO_CODE`, `seed()`, `resetDemo` e do `localStorage` de dados.
  - Requisitos: R2.1 a R2.8, R2.10, **R2.11**, R15.3
  - Contratos (conferidos em `contracts/openapi.yaml`, `9c37029`):
    - `POST /api/v1/auth/login {username, password}` → `LoginOut`, com `mfa_required`, `mfa_enrollment_required`, `mfa_token` e, em dev com `MFA_OBRIGATORIO=false`, `access_token` e `expires_in`;
    - `POST /auth/mfa/enroll {mfa_token}` → `{otpauth_uri}`;
    - `POST /auth/mfa/confirm` e `POST /auth/mfa/verify` → access token;
    - `POST /auth/refresh`, com cookie, `X-Requested-With: sgs` e a `Origin` em `CORS_ORIGINS`;
    - `POST /auth/logout`;
    - erros em `problem+json`: 401 com a mesma mensagem para usuário inexistente e senha errada; 429.
  - Arquivos: `frontend/app/js/api.js`, `frontend/app/js/auth.js`, `frontend/app/js/views/login.js`.
  - Dependências: a T3; e o `sgs-admin seed demo` e o `create-user` para os E2E. O TOTP do teste é gerado com `pyotp`, que já é dependência.
  - Pronto quando:
    - `tests/e2e_front/test_autenticacao.py` passa, incluindo um caso com `MFA_OBRIGATORIO=false`;
    - `test_frontend_estatico.py` não acha segredos de demonstração.
- [ ] T5. `perms.js` e menu a partir do `/me` (`papeis`, `permissoes` com escopo); view "sem acesso"; telas dos 7 papéis só com as permissões existentes (DF8, tabela do design); lista do distrito aberta no próprio DS (R3.5, só navegação)
  - Requisitos: R3.1 a R3.5
  - Pronto quando: `tests/e2e_front/test_perfis.py` passa:
    - os 7 papéis do seed, cada um com o menu da tabela do design;
    - a rota de outro perfil mostra "sem acesso" e a API dá 403;
    - nenhuma permissão nova é exigida;
    - os 3 perfis de referência (Gestor de Dados, Técnico Distrital do DS IV e Gestor de Unidade de um CAPS II) são cobertos explicitamente.
- [ ] T6. Início com `/dashboard/resumo`
  - Requisitos: R4.1
  - Pronto quando: `tests/e2e_front/test_inicio.py` passa (os números da tela batem com a resposta da API para dois papéis com escopos diferentes; sem `dashboard:read`, o início é a primeira tela do menu).
- [ ] T7. Lista de unidades: busca, filtros existentes, ordenação, paginação, filtros na URL
  - Requisitos: R5.1, R5.2
  - Pronto quando: `tests/e2e_front/test_lista.py` passa (inclui estado vazio e página além da última).
- [ ] T8. Ficha: dados, histórico, verificações de qualidade só para exibição
  - Requisitos: R6.1 a R6.3
  - Pronto quando: `tests/e2e_front/test_ficha.py` passa:
    - **a aba de histórico some quando nenhum escopo de `auditoria:read` do usuário cobre a unidade** (Diretoria; Técnico Distrital olhando unidade de outro DS);
    - **as verificações cujo dado a API não tem (número do endereço, horário) aparecem como "não verificável ainda"**, e não como falha;
    - os filtros de período e de autor do histórico funcionam.
- [ ] T9. Edição e cadastro pelo escopo global (diff, If-Match, tratamento de 409, 412, 422 e 403 com `campos_estruturais`); edição oculta para distrito, unidade e coordenador (R7.4)
  - Requisitos: R7.1 a R7.4
  - Pronto quando: `tests/e2e_front/test_edicao.py` passa:
    - dois navegadores provam o 412;
    - os botões de edição e cadastro estão ausentes para o Técnico Distrital, o Gestor de Unidade e o Coordenador Técnico.
- [ ] T10. Serviços da unidade
  - Requisitos: R8.1
  - Pronto quando: `tests/e2e_front/test_servicos.py` passa:
    - incluir e remover pelo Gestor de Dados, e o histórico mostra `unidade.servico_*`;
    - **só o escopo global vê os controles de incluir e remover**: o Técnico Distrital, o Gestor de Unidade e o Coordenador Técnico veem a aba só para leitura, mesmo tendo `servico:write` no próprio escopo.
- [ ] T11. Histórico geral (escopo global), com filtros de período, autor, ação e entidade, e verificação da cadeia pelo Auditor
  - Requisitos: R12.1, R12.2, **R12.4**
  - Usa `GET /api/v1/auditoria/eventos`. A rota `/api/v1/historico` citada na Grupo-DF9 não existe (design § Histórico).
  - Os filtros `de` (inclusivo), `ate` (exclusivo), `autor`, `entidade_tipo` e `entidade_id` têm testes no backend que detectam regressão (008/T6, `tests/integration/audit/test_consulta_trilha.py::test_trilha_geral_filtra_por_periodo_entidade_e_autor` e `::test_historico_filtra_por_periodo_com_de_inclusivo_e_ate_exclusivo`). O teste do front confere a ligação da tela com a API, não a semântica do filtro.
  - Pronto quando: `tests/e2e_front/test_qualidade_historico.py` passa:
    - o painel de qualidade;
    - a trilha com filtros de período e autor;
    - a "em desenvolvimento" para escopo menor;
    - a verificação da cadeia mostra `integra` para o Auditor.
- [ ] T12. Funcionalidades ainda sem backend visíveis e desabilitadas: equipamentos (aparelhos), solicitações e validações, notificações, revisão, exportação CSV/PDF, importação CSV e observação no modal
  - Requisitos: R9.1, R10.1, R11.1, R13.1, R14.1
  - Pronto quando: `tests/e2e_front/test_em_desenvolvimento.py` passa (as 24 funcionalidades do inventário estão presentes; as [C] mostram "em desenvolvimento" e não chamam a API).
- [ ] T13. XSS de ponta a ponta e responsividade
  - Requisitos: R15.1, R15.2, R1.4
  - Pronto quando: `tests/e2e_front/test_xss.py` passa (payloads gravados pela API; nenhum `dialog`; nenhuma violação de CSP), e `test_responsivo.py` também.
- [ ] T14. E2E no CI (job `compose-smoke` ou um novo) e documentação
  - **Atualizar** o `docs/frontend-integracao.md`, que já existe: onde fica o front, as telas implementadas e como rodar. Não criar outro documento.
  - Atualizar o README.
  - Requisitos: todos os [M]
  - Pronto quando: o workflow do GitHub Actions passa com os E2E (o CI rodou nos PRs #1 a #3 da `novo/main`).

## Escopo completo (bloqueado, depende de decisões ou specs de outros donos)
Estas tarefas ficam listadas para não descartar funcionalidade. Cada uma só será detalhada quando a dependência sair.

**Responsáveis** (governança de 10/11/2026):
- 003, 005, 007 e 008: Vinicius;
- 006: Hélder, por decisão do Grupo 01;
- premissas Grupo-DF2, Grupo-DF13 e Grupo-DF14: adotadas pelo grupo e **aguardando ratificação do cliente**.

- [ ] T15. Infraestrutura (aparelhos) na ficha.
  - Bloqueada por: DF1 (cliente + Hélder) e a spec de infraestrutura.
  - Requisitos: R9.2
- [ ] T16. Solicitações: propor, cadastrar por solicitação, aprovar e devolver. A edição separa os campos comuns (diretos) dos sensíveis (solicitação), conforme a premissa Grupo-DF14.
  - Bloqueada por:
    - ratificação de Grupo-DF13 e Grupo-DF14 pelo cliente, com as perguntas P1 a P4;
    - DF14 desta spec (`COORD_TECNICO`);
    - spec de solicitações (dono a definir);
    - emenda da 003 (`alteracao:validar` por papel; Vinicius).
  - Requisitos: R7.5, R10.2 (e uma emenda funcional de R7.4)
  - Pendências: PF-01, PF-02, PF-03, PF-04, PF-05, PF-07
- [ ] T17. Notificações.
  - Bloqueada por: a spec de notificações.
  - Requisitos: R11.2
- [ ] T18. Campos de endereço, contato, horário e situação; observação no modal de confirmação.
  - Bloqueada por: DF3 e a emenda da 006 (Hélder).
  - Requisitos: R6.4, **R7.6**
- [ ] T19. Revisão sem alteração e filtros de qualidade e "aguardando".
  - Bloqueada por: a spec 007 (Vinicius) e a emenda da 006 (Hélder).
  - Requisitos: R6.5, R5.3, R4.2
- [ ] T20. Histórico geral no escopo do distrito e filtro de acessos.
  - Bloqueada por: a emenda da 008 (Vinicius; a Grupo-DF9 pede visibilidade pelo escopo hierárquico) e a DF9 desta spec (eventos de acesso; Vinicius).
  - Requisitos: R12.3
- [ ] T21. Exportação pelo backend e importação CSV.
  - Exportação conforme a DF10 e a Grupo-DF15:
    - CSV de dados e PDF de relatório legível;
    - lista filtrada de unidades e equipamentos e resumo do dashboard;
    - auditoria de cada exportação.
  - Bloqueada por:
    - a spec do backend de exportação e importação (dono a definir; regra: Hélder);
    - colunas e layout (P5);
    - a permissão por papel (DF15; depende da premissa Grupo-DF13 e de emenda da 003).
  - Requisitos: R5.4, R14.2 e R5.5 (proposto, emenda funcional 1)
  - Pendências: PF-06, PF-07
- [ ] T22. Redefinição de senha e usuários pelo Admin TI.
  - Bloqueada por: a spec da 003 para `/admin/usuarios` (Vinicius).
  - Requisitos: R2.9
- [ ] T23. Leitura por escopo de distrito e unidade.
  - Bloqueada por:
    - ratificação da premissa Grupo-DF2 (DF13 desta spec) pelo cliente;
    - emenda da 003 e migração (Vinicius).
  - Requisitos: R3.5 (e uma emenda funcional)
  - Pendência: PF-07

## O que pode começar (10/11/2026)
- **Antes do G2 e do G3:** só preparação, sem código de interface (`AGENTS.md`, regra 1), **salvo a T1**, por exceção pontual do dono (10/11/2026):
  - PR com a spec para a revisão do G2;
  - `.gitignore` do protótipo;
  - documentação.
- **Depois do G3, sem dependência de backend nem de decisão:** T1 → T2 e T3 → T4 → T5 → T6 a T8 → T9 e T10 → T11 → T12 → T13 → T14.
  - Nenhuma depende de PF-01 a PF-07: o [M] usa só o que a API já oferece.
- **Bloqueadas:** T15 a T23, pelas dependências de cada uma.

## Rastreabilidade (conferida em 10/11/2026)
- Todos os 57 requisitos têm tarefa:
  - R1.6 → T3;
  - R2.11 → T4;
  - R7.6 → T18;
  - R12.4 → T11.
- Nenhuma tarefa cita requisito inexistente.
