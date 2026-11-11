# Relatório geral do projeto · SGS Recife · Etapa 06

- **Data de referência:** 10/11/2026.
- **Estado descrito:**
  - branch `feat/012-etapa06`, criada a partir da `novo/main` (`3b4a9bf`), com as implementações da Etapa 06 ainda **não commitadas**;
  - este relatório descreve o conteúdo da árvore de trabalho nessa data.
- **Equipe:** Grupo 01, CESAR School (CS018). Cliente: Secretaria de Saúde do Recife.
- **Documentos oficiais da entrega:**
  - [README](../../README.md);
  - [matriz de conformidade](../banco/07-matriz-conformidade.md);
  - [roteiro de demonstração](../banco/08-roteiro-demonstracao.md).

  Este relatório resume e conecta esses documentos e não os substitui.
- **Convenção:**
  - **implementado:** existe no código ou no banco;
  - **validado:** um teste automatizado ou uma consulta de catálogo comprovou;
  - **planejado:** está na spec, sem implementação.

---

## 1. Identificação e visão geral

**SGS Recife** é a Plataforma de Governança de Dados de Saúde da Secretaria de Saúde do Recife: um cadastro único e governado de **unidades, equipamentos e serviços de saúde**.

**Problema.** Hoje os dados estão espalhados entre o CNES e planilhas de várias áreas, sem padrão, sem validação e sem trilha de quem alterou o quê (`steering/product.md`). O produto segue o fluxo **Centralizar → Validar → Controlar → Visualizar**, com login, cadastro e consulta, alteração, auditoria e painel.

**Tecnologias.**

| Camada | Tecnologia |
|---|---|
| API | Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2 assíncrono (asyncpg), SQL escrito à mão nos módulos de cadastro e painel (ADR-0009) |
| Banco | PostgreSQL 17, migrações com Alembic, objetos de banco em arquivos `.sql` versionados (`migrations/sql/<revisão>/`) |
| Segurança | senhas Argon2id, 2FA TOTP, access token JWT ES256, refresh rotativo, RBAC com escopo, TLS também entre API e banco |
| Interface | HTML, CSS e módulos ES do navegador, sem framework nem empacotador (ADR-0010), servidos pelo Caddy no mesmo domínio da API |
| Testes | pytest, testcontainers (PostgreSQL descartável) e Playwright em Python para a interface (ADR-0011) |
| Ambiente | Docker Compose: API, PostgreSQL com TLS e proxy TLS (Caddy) |

**Arquitetura.** Monólito modular (ADR-0002), com os módulos `identity`, `access`, `registry`, `audit` e `dashboard`. A camada de domínio não importa FastAPI nem SQLAlchemy (regra verificada por `import-linter` no `make check`). O desenvolvimento segue specs (SDD): requisitos, design e tarefas aprovados antes do código (`specs/`).

**Situação da Etapa 06.** A interface da entrega final está implementada e validada por testes automatizados:
- painel e indicadores;
- consultas e views;
- CRUD de 5 tabelas;
- funções, procedimentos e triggers visíveis na tela;
- histórico e auditoria.

A documentação oficial foi atualizada. Falta consolidar a branch (commits, publicação no novo repositório), o que depende de autorização.

---

## 2. Histórico e evolução

| Etapa | O que foi entregue | Onde está |
|---|---|---|
| 01 · Modelagem | Minimundo, modelo conceitual (ER), modelo lógico e esquema relacional (3FN), dicionário de dados | `docs/banco/01` a `04`. Em 10/11, as 166 colunas do dicionário bateram com o catálogo do banco |
| 02 · Criação e povoamento | Tabelas com PK, FK, UNIQUE, CHECK, DEFAULT, `ON UPDATE CASCADE` e `ON DELETE SET NULL`; seed de demonstração | migrações `0001` a `0011_09`; `seeds/demo/`; `docs/banco/06` |
| 03 · Consultas e interface | Consultas com JOIN, SQL explícito no backend, primeiras telas | `src/modules/*/infrastructure/sql/` |
| 04 · Consultas avançadas, views e índices | Anti join, FULL OUTER JOIN, subconsultas, 2 views, índices com prova de uso | spec 011; `docs/banco/planos-indices.txt` |
| 05 · Funções, procedimentos e triggers | 2 funções, 2 procedimentos (1 com CURSOR), triggers de log, versão, `updated_at` e imutabilidade da auditoria | spec 011; migrações `0011_*` |
| 06 · Integração final | Interface completa sobre a API: painel, consultas, CRUDs, efeitos de funções, procedimentos e triggers | spec 012, emenda funcional 2 |

**Etapa 06, passo a passo** (spec 012, emenda funcional 2, aprovada na sessão de trabalho de 10/11/2026):

| Tarefa | Entrega |
|---|---|
| T11 parte A | Painel "Qualidade dos dados" (indicadores, gráficos, consultas e views com filtros); histórico geral, log do banco, partições e verificação da cadeia |
| T24 | CRUD das tabelas de referência e `ON UPDATE CASCADE` na tela |
| T8 parte A | Ficha da unidade, com versão, "Atualizado em" e histórico pela `vw_unit_history` |
| T10 | CRUD de serviços, com o efeito do `trg_set_updated_at` |
| T25 | Desativação pela procedure `sp_deactivate_unit` |
| T9 | Cadastro e edição de unidades, com `If-Match` e tratamento do conflito de versão (412) |
| T26 | Evidências, matriz de conformidade, roteiro de demonstração, README |

**Integração com as etapas anteriores.** A Etapa 06 **não criou rota de API nem objeto de banco novo**. A interface consome as rotas e os objetos das Etapas 02 a 05 (specs 006, 008, 009 e 011). Assim, cada objeto do banco tem uma tela que o mostra e um teste que prova o efeito.

**Consolidação das branches.**
- Em 09/11/2026, a auditoria das 15 branches (`docs/integration-audit/`) levou à consolidação na `main`.
- O repositório oficial passou a ser `ViniciusVbm/sgs-api`, com PRs #1 a #5 já incorporados à `novo/main`.
- A Etapa 06 está na branch `feat/012-etapa06`, ainda sem commits, aguardando autorização para virar a nova `main`.

---

## 3. Banco de dados (seção detalhada)

### 3.1 SGBD e estrutura geral
- **SGBD:** PostgreSQL 17 (17.11 no ambiente local auditado em 10/11/2026).
- **Schema:** `public`, revisão Alembic `0011_09` (a última de `migrations/versions/`).
- **Extensões:** `unaccent` (busca sem acento) e `pg_trgm` (busca por trecho, com índice GIN).
- **Organização:** cada objeto de banco é um `.sql` próprio em `migrations/sql/<revisão>/`, com cabeçalho de objetivo, justificativa, uso e requisito (ADR-0009). O teste `tests/architecture/test_sql_documentado.py` exige esse cabeçalho.

### 3.2 Tabelas e responsabilidades
| Grupo | Tabelas | Responsabilidade |
|---|---|---|
| Cadastro (negócio) | `health_units`, `equipments`, `services` | Unidades, equipamentos de saúde e serviços ofertados |
| Referências | `districts`, `technical_areas`, `unit_types`, `equipment_types`, `service_types` | Catálogos usados no cadastro; distritos e áreas são domínio fechado |
| Identidade | `users`, `sessions`, `refresh_tokens` | Contas, sessões e tokens de renovação (só o hash SHA-256 do token) |
| Acesso (RBAC) | `roles`, `permissions`, `role_permissions`, `role_assignments`, `group_role_mappings` | Papéis, permissões com escopo máximo, atribuições por escopo, mapeamento de grupos (para LDAP, spec 004) |
| Auditoria | `audit_log`, `audit_chain_head` | Trilha de auditoria imutável, encadeada por hash |
| Log do banco | `db_change_log` (particionada por mês) | Toda escrita em unidades, equipamentos e serviços, registrada pelo próprio banco |
| Infraestrutura | `alembic_version` | Versão do schema |

### 3.3 Relacionamentos e integridade
- **Chaves primárias:**
  - UUID no cadastro, na identidade e no acesso (geradas pela aplicação);
  - `smallserial` nas referências;
  - `IDENTITY` em `audit_log` e `db_change_log`.
- **Chaves estrangeiras** (18 no catálogo, contadas em `pg_constraint` em 10/11/2026), com destaque para:
  - `equipments.equipment_type_code → equipment_types(code)` **`ON UPDATE CASCADE`**: corrigir o código de um tipo atualiza todos os equipamentos. Visível na tela de referências;
  - `services.equipment_id → equipments(id)` **`ON DELETE SET NULL`**: remover um equipamento mantém os serviços, sem o vínculo;
  - `equipments.unit_id` e `services.unit_id` → `health_units` **`ON DELETE RESTRICT`**: unidade com vínculos não é apagada.
- **UNIQUE:**
  - códigos das referências, e-mail e usuário;
  - CNES único na rede (índice parcial);
  - nome único no distrito, sem considerar acento, caixa ou espaços (`(district_id, name_normalized)`).
- **CHECK** (24 no catálogo): situações válidas, quantidade positiva, formato Argon2id da senha, SHA-256 do token, coerência entre escopo e tipo, e `audit_chain_head` com linha única (`id = 1`).
- **Coluna gerada:** `health_units.name_normalized = fn_normalize_name(name)`.

### 3.4 Migrações e evolução do esquema
| Revisão | O que trouxe |
|---|---|
| `0001_base`, `0001_1` | Papel `sgs_app`, `audit_log` imutável e cabeça da cadeia de hash |
| `0002_identity`, `0003_1` | Usuários, sessões, refresh tokens, versão das atribuições |
| `0003_access` | Catálogo de papéis e permissões (RBAC com escopo) |
| `0006_registry` | Unidades, equipamentos, serviços, referências, `fn_normalize_name`, busca sem acento |
| `0011_03` | Papel dono (`sgs_owner`), privilégios, índices, `fn_registration_status` |
| `0011_04` | Views `vw_unit_inventory` e `vw_unit_history` |
| `0011_05` | Trigger de versão da unidade |
| `0011_06` | Procedimento `sp_deactivate_unit` |
| `0011_07` | `db_change_log` particionada e trigger de log do cadastro |
| `0011_08` | Procedimento `sp_ensure_monthly_partitions` (com CURSOR) |
| `0011_09` | Ajustes da consolidação: índices das FKs e `trg_set_updated_at` |

### 3.5 Views
| View | Definição | Para que serve | Na interface |
|---|---|---|---|
| `vw_unit_inventory` | 3 INNER JOINs (tipo, área, distrito) e 2 LEFT JOINs com agregados (equipamentos; serviços e serviços fora do CNES); usa `fn_registration_status`; `security_invoker` | Inventário único da rede, com a situação cadastral; sem dado pessoal | Painel de qualidade: tabela com filtro de situação, pizza e médias |
| `vw_unit_history` | 3 INNER JOINs (unidade, tipo, distrito) e 1 LEFT JOIN (autor) sobre `audit_log` | Histórico de uma unidade, incluindo eventos dos equipamentos e serviços dela | Ficha › Histórico; atividade recente no Início |

### 3.6 Consultas
O catálogo `GET /dashboard/consultas` tem 13 entradas. São consultas da disciplina 8 delas:

| Etapa | Consulta | Técnica |
|---|---|---|
| 03 | Unidades por categoria | UNION ALL de agregações sobre a view |
| 03 | Equipamentos por tipo e distrito | JOIN de 5 tabelas, GROUP BY e SUM |
| 03 | Alterações por período | view, `count(*) FILTER` e subconsulta IN |
| 03 | Alterações recentes | view com 4 JOINs |
| 04 | Unidades sem serviço | **anti join** (`LEFT JOIN … WHERE … IS NULL`) |
| 04 | Conciliação unidade × equipamento | **FULL OUTER JOIN** |
| 04 | Distritos com mais unidades sem CNES que a rede | **subconsulta** escalar no HAVING |
| 04 | Unidades com serviço fora do CNES | **subconsulta** correlacionada com EXISTS |

As outras 5 entradas do catálogo são as 2 views, o resumo dos indicadores, o log do banco e as partições. Todas aplicam o escopo de leitura do usuário e aceitam os filtros de distrito, tipo e área técnica.

### 3.7 Funções e procedimentos
| Objeto | Parâmetros e retorno | O que faz | Por que importa |
|---|---|---|---|
| `fn_normalize_name(p_name text) → text` | IMMUTABLE, SQL | Tira acento, caixa e espaços extras | Base da unicidade do nome no distrito e da busca sem acento |
| `fn_registration_status(p_unit health_units) → text` | IMMUTABLE, plpgsql, **IF/ELSIF** | Situação cadastral: inativa → com pendências → sem CNES → regular | Regra única, usada pela view e pelo painel |
| `sp_deactivate_unit(IN p_unit_id uuid, OUT o_previous_status text, OUT o_version int)` | procedimento | Trava a linha (`FOR UPDATE`) e muda para `inativa`; erro `SGS01` se a unidade não existe; idempotente para unidade já inativa | Desativação (exclusão lógica): a unidade nunca é apagada |
| `sp_ensure_monthly_partitions(IN p_table regclass, IN p_months_ahead int)` | procedimento, SECURITY DEFINER, **CURSOR** explícito | Percorre os meses e cria as partições que faltam; avisa e pula o mês que já tem registros na partição `default` | Mantém o log do banco particionado sem perder dados; roda pelo `sgs-admin banco particoes` |

### 3.8 Triggers
| Trigger | Tabelas | Quando | O que faz |
|---|---|---|---|
| `trg_registry_change_log` | `health_units`, `equipments`, `services` | AFTER INSERT, UPDATE, DELETE | Grava em `db_change_log` as colunas alteradas (`de`, `para`), o usuário do banco e se veio pela API. Mascara o nome do gestor (LGPD). Pega até alteração feita fora da aplicação |
| `trg_health_units_version` | `health_units` | BEFORE UPDATE | Só quando algum campo de negócio muda de fato: `version` + 1 e `updated_at` = hora da transação. É a base do `ETag` e do `If-Match` |
| `trg_set_updated_at` | **7 tabelas** (lista abaixo) | BEFORE UPDATE | Mantém o `updated_at` |
| `audit_log_bloqueia_update_delete`, `audit_log_bloqueia_truncate` | `audit_log` | BEFORE UPDATE, DELETE, TRUNCATE | Recusam alteração: a trilha só aceita inserção |
| `trg_roles_protect_system`, `trg_roles_protect_system_truncate` | `roles` | BEFORE UPDATE, DELETE, TRUNCATE | Protegem os 7 papéis de sistema |

**`trg_set_updated_at`, conferido no catálogo do PostgreSQL (`pg_trigger`, 10/11/2026):** 7 tabelas, todas com o trigger **habilitado** e chamando a função `fn_trg_set_updated_at`:

| # | Tabela | Grupo |
|---|---|---|
| 1 | `services` | serviços |
| 2 | `equipments` | equipamentos |
| 3 | `districts` | referência |
| 4 | `technical_areas` | referência |
| 5 | `unit_types` | referência |
| 6 | `equipment_types` | referência |
| 7 | `service_types` | referência |

Ele **não** está em `health_units`, cujo `updated_at` é gravado pelo `trg_health_units_version`.

**`trg_health_units_version`, confirmado nos arquivos e no banco:**
- **arquivos:** `migrations/sql/0011_05/01_fn_trg_health_units_version.sql` e `03_trg_health_units_version.sql`;
- **banco:** `BEFORE UPDATE ON health_units`, habilitado (catálogo, 10/11/2026);
- **regra:** compara a linha nova com a antiga, sem `pending_issues`, `version`, `updated_at` e `name_normalized`. Se algo mudou, faz `NEW.version := OLD.version + 1` e `NEW.updated_at := now()`;
- **prova automática:** `test_versao_trigger.py` (integração) e `test_edicao.py` (interface: versão +1, data nova e 412 na edição concorrente).

### 3.9 Auditoria, histórico e rastreabilidade
São três camadas complementares:
1. **Trilha da aplicação (`audit_log`):** cada alteração de dado de negócio grava um evento na **mesma transação**, com autor, papéis, sessão, IP, ação, entidade e mudanças `{campo, de, para}`. Os eventos são encadeados por hash (`prev_hash`, `hash`), e `POST /auditoria/verificar` recalcula a cadeia. Triggers bloqueiam UPDATE, DELETE e TRUNCATE.
2. **Log do banco (`db_change_log`):** gravado pelo trigger, inclusive para alterações fora da aplicação, e particionado por mês (13 partições mensais mais a `default` no ambiente auditado).
3. **Histórico por unidade (`vw_unit_history`):** visão de leitura sobre a trilha, mostrada na ficha.

### 3.10 Versão e concorrência
- Cada unidade tem `version`, exposta como `ETag`.
- O `PATCH /unidades/{id}` exige `If-Match`: sem ele, 428; com versão diferente, **412**. A gravação trava a linha e confere a versão de novo.
- A interface envia só os campos alterados, mostra o diff antes de salvar e, no 412, avisa que nada foi sobrescrito.
- A API de serviços não usa `If-Match`; nela, a última gravação vale.

### 3.11 Índices e particionamento
| Índice | Uso |
|---|---|
| `ix_audit_log_entity (entity_type, entity_id, occurred_at DESC)` | Histórico de uma unidade |
| `ix_services_unit_id`, `ix_equipments_unit_id`, `ix_services_equipment_id` | Serviços e equipamentos de uma unidade; FKs sem varredura |
| `ix_health_units_name_normalized_trgm` (GIN, `pg_trgm`) | Busca por trecho do nome, sem acento |
| `ix_health_units_cnes` (único parcial), `ix_health_units_district_id_name_normalized` (único) | Unicidade do CNES e do nome no distrito |
| `ix_db_change_log_occurred_at` | Log do banco, do mais recente para o mais antigo |

A prova de uso está em `tests/integration/db/test_indices.py`: `EXPLAIN (ANALYZE, BUFFERS)` com 1.000 unidades, registrado em `docs/banco/planos-indices.txt`. Em 10/11, um `EXPLAIN` sem ANALYZE no ambiente local também mostrou os índices nos planos.

### 3.12 Seeds e dados de demonstração
O comando `sgs-admin seed demo` é idempotente e recusado em produção. Ele carrega:
- 37 unidades, 31 equipamentos e 35 serviços (Recife, com foco em Saúde Mental);
- 30 usuários fictícios, cobrindo os 7 papéis;
- 30 atribuições de papel;
- 138 eventos de auditoria e 103 linhas no log do banco.

A senha é dada na execução, por `SGS_SEED_SENHA`, e não fica no repositório.

**30 tuplas por tabela.** O **cenário D foi aprovado formalmente pelo professor**, conforme comunicado pelo responsável pelo projeto (o documento da aprovação não está anexado ao repositório):
- todas as tabelas de **negócio e de auditoria** têm 30 ou mais;
- as tabelas de domínio fechado (8 distritos, 4 áreas, 7 papéis, 17 permissões), as preenchidas pelo uso ou por integração (sessões, tokens, mapeamento LDAP) e as de infraestrutura (cabeça da cadeia, versão do Alembic) ficam com a quantidade real, com justificativa;
- nenhuma tupla artificial foi inserida.

Detalhes em [docs/banco/06-trinta-tuplas.md](../banco/06-trinta-tuplas.md).

### 3.13 Segurança no banco
- **Papéis separados:**
  - `sgs` é o dono e roda só as migrações;
  - `sgs_owner` é dono das funções SECURITY DEFINER;
  - a API conecta como `sgs_api`, membro de `sgs_app`, com privilégios mínimos: só insere e lê a trilha de auditoria, só lê as views e executa só as funções e o procedimento concedidos. `sp_ensure_monthly_partitions` não é executável pela API.
- **`search_path` fixo** nas funções `fn_normalize_name` e `fn_registration_status`, no trigger `trg_registry_change_log` e no procedimento `sp_ensure_monthly_partitions` (os dois últimos são SECURITY DEFINER).
- **TLS** entre a API e o banco em `verify-full`; o banco recusa conexão pela rede sem TLS.
- **LGPD:** as views analíticas não expõem o nome do gestor, e o log do banco o mascara.
- **Credenciais de desenvolvimento:**
  - as senhas do compose e do script de inicialização do banco (`docker/postgres/init/01-usuario-app.sql`) servem **só para ambientes locais e descartáveis**, e não devem ser usadas em produção nem em ambientes compartilhados;
  - com `APP_ENV=prod`, a API recusa iniciar com senha de exemplo, chave de cifra de exemplo, `DEBUG` ligado ou TLS do banco diferente de `verify-full` (`src/core/config.py`);
  - em ambientes reais, as credenciais devem ser fortes, únicas e fornecidas por um mecanismo seguro de configuração;
  - as chaves reais (JWT e cifra) ficam em `secrets/`, no `.gitignore`, e não devem ser publicadas nem copiadas para o repositório.

  Este relatório não reproduz nenhum desses valores.

---

## 4. Aplicação e interface

| Funcionalidade | O que existe | Tela |
|---|---|---|
| Painel e indicadores | Início: totais e distribuições. Qualidade: totais, médias de serviços e equipamentos por unidade (sobre todas as páginas do inventário), percentual sem CNES (rede e distritos), tendência (ritmo de 7 dias × 30 dias) | `#/inicio`, `#/qualidade` |
| Gráficos e filtros | SVG gerado no próprio front, sem biblioteca externa: barras, barras agrupadas e empilhadas, pizza (rosca) e linha do período. Filtros de distrito, tipo e área técnica (na URL), situação cadastral e período (7 dias, 30 dias, personalizado; por hora até 2 dias) | `#/qualidade` |
| CRUD das referências | Incluir, alterar, desativar e reativar tipos de unidade, de equipamento e de serviço; distritos e áreas só leitura; cascata do código conferida na tela | `#/referencias` |
| CRUD de unidades | Lista com busca sem acento, filtros e paginação; cadastro; edição com diff e `If-Match`; desativação | `#/unidades`, `#/nova`, `#/unidade/{id}` |
| CRUD de serviços | Incluir, alterar (nome, tipo, "no CNES", situação), desativar, reativar, remover; "Atualizado em" antes e depois | ficha › Serviços |
| Ficha e histórico | Dados, versão, data de atualização, serviços, histórico com filtros de período e autor | `#/unidade/{id}` |
| Desativação lógica | Pelo procedimento `sp_deactivate_unit`, com motivo, confirmação e painel de efeitos | ficha |
| Histórico geral | Trilha, log do banco (pela API ou fora dela), partições | `#/historico` |
| Verificação da cadeia | Integridade da trilha de auditoria | `#/cadeia` (Auditor) |
| Autenticação | Login com 2FA (cadastro com chave em texto), sessão por refresh, saída | login |
| Autorização | Menu e botões pelas permissões efetivas do `/me`. Só o escopo global edita; quem só propõe vê "Propor alteração" desabilitado (R7.4). A API confere de novo | todas |
| Erros | `problem+json` com mensagem em português; 422 marcado no campo; 409 com link para o registro existente; 403; 412 | todas |

**Fora desta entrega** (aparecem como "em desenvolvimento" e não chamam a API): as 8 verificações de qualidade, aparelhos, solicitações e validações, notificações, exportação, importação e usuários. "Papéis e atribuições" segue "em implantação".

---

## 5. Segurança e governança

| Tema | Como está | Situação |
|---|---|---|
| Autenticação | Argon2id; TOTP obrigatório para contas locais; JWT ES256 de curta duração; refresh opaco rotativo, em cookie `HttpOnly`/`Secure`/`SameSite=Strict`, com detecção de reuso e anti-CSRF; limite de 10 logins por minuto por IP | implementado e validado (specs 002, 012/T4) |
| RBAC | 7 papéis, 17 permissões, escopo (global, área, distrito, unidade), negação por padrão; toda rota declara `require("recurso:acao")` | implementado e validado (`test_rotas_protegidas.py`, `test_perfis.py`) |
| Auditoria | Trilha imutável e encadeada; log do banco por trigger; eventos de acesso negado | implementado e validado |
| Integridade e concorrência | FKs, CHECKs, UNIQUEs; versão e `If-Match`; desativação em vez de exclusão | implementado e validado |
| Criptografia | TLS em todos os enlaces (proxy e banco `verify-full`); segredo do TOTP cifrado com AES-256-GCM (`FieldCipher`, chave versionada); chaves em `secrets/`, fora do Git | implementado (spec 002) |
| Interface | CSP sem `unsafe-eval`; todo HTML passa por escape; token só em memória; `localStorage` só para o tema | implementado e validado (`test_frontend_estatico.py`) |
| Proteção de dados (LGPD) | Sem dado de paciente; nome do gestor fora das views analíticas e mascarado no log | implementado |

LDAP, OIDC (spec 004) e exportação para S3 (spec 005) continuam em Rascunho e **não** fazem parte desta entrega.

---

## 6. Testes e evidências

Resultados da **última execução registrada** (10/11/2026, em `specs/012-frontend/tasks.md`). **Não** foram reexecutados para este relatório, porque o código não mudou desde então.

| Validação | Escopo | Resultado |
|---|---|---|
| `make check` | lint, formatação, tipos, camadas e testes rápidos (unitários, arquitetura e integração em PostgreSQL descartável) | **1029 aprovados, 3 pulados** (os 3 de `test_sql_documentado.py`, por desenho) |
| Suíte E2E da interface (`pytest -m slow tests/e2e_front`) | Playwright contra um compose descartável (`sgs-api-e2e-front-ui`), com dados criados pelos próprios testes | **118 aprovados** em 12 arquivos (contagem confirmada por `--collect-only`) |
| Testes de escrita no banco | integridade, cascata, SET NULL, procedimentos, triggers, partições, views, seed (testcontainers) | 82 aprovados, mais 1 de índices (`-m slow`), mais 8 do procedimento de desativação |
| Sensibilidade dos testes | mutações intencionais em cada etapa (ex.: tirar o `If-Match`, mostrar botões sem permissão) | todos os testes visados falharam com a mutação e passaram sem ela |
| Documentação | `git diff --check`; links e âncoras internos | sem problemas; 72 links conferidos |

**E2E por arquivo:**

| Arquivo | Testes |
|---|---|
| `test_qualidade_historico` | 15 |
| `test_referencias` | 14 |
| `test_edicao` | 14 |
| `test_ficha` | 11 |
| `test_servicos` | 9 |
| `test_desativar` | 9 |
| `test_lista` | 7 |
| `test_perfis` | 18 |
| `test_autenticacao` | 11 |
| `test_aparencia` | 4 |
| `test_inicio` | 4 |
| `test_estados` | 2 |
| **Total** | **118** |

Os testes que escrevem dados usam só bancos descartáveis. O ambiente local de demonstração foi conferido contra um registro de referência antes e depois de cada etapa, da T11 parte A à T26, e ficou inalterado. Depois da T26 não houve acesso ao Docker, então não houve nova conferência.

---

## 7. Requisitos e conformidade

A referência é [docs/banco/07-matriz-conformidade.md](../banco/07-matriz-conformidade.md), com cada requisito apontando objeto, rota, tela e teste.

| Etapa | Requisito | Situação | Principal evidência |
|---|---|---|---|
| 01 | Modelos e dicionário coerentes com o banco | ✅ | 166 de 166 colunas conferidas |
| 02 | Constraints, cascata, SET NULL, sequências | ✅ | `test_integridade.py`; cascata na tela (`test_referencias.py`) |
| 02 | 30 tuplas por tabela | ✅ **cenário D aprovado** | `test_seed_demo.py`; `06-trinta-tuplas.md` |
| 03 | 4 ou mais consultas, com JOIN, SQL explícito, visualização | ✅ | `#/qualidade`; `test_qualidade_historico.py` |
| 04 | Anti join, FULL OUTER JOIN, 2 subconsultas | ✅ | catálogo e telas; `test_consultas_qualidade.py`, `test_painel.py` |
| 04 | 2 views | ✅ | inventário e histórico; `test_views.py` |
| 04 | 2 índices adicionais com prova | ✅ (6 índices) | `test_indices.py`; `planos-indices.txt` |
| 05 | 2 funções, uma com condicional | ✅ | busca sem acento e situação cadastral |
| 05 | Procedimento de atualização e procedimento com CURSOR | ✅ | `test_desativar.py`; partições na tela |
| 05 | 2 triggers, um de log | ✅ (log, versão, `updated_at`, auditoria) | `test_log_banco.py`; `test_edicao.py`; `test_servicos.py` |
| 06 | CRUD de 4 tabelas ou mais | ✅ (5) | referências (3), serviços, unidades |
| 06 | Funções, procedimentos e efeitos dos triggers na interface | ✅ | ficha, histórico, painel |
| 06 | Consultas e views com filtros e gráficos | ✅ | `#/qualidade` |
| 06 | Dashboard com dados reais: totais, médias, percentuais, tendências | ✅ | `test_medias_somam_todas_as_paginas_do_inventario` e outros |

---

## 8. Situação atual e pendências

| Categoria | Itens |
|---|---|
| **Implementado e validado** | Etapas 01 a 06 conforme a matriz; spec 012 (T1 a T7, T9, T10, T24, T25, T26; partes A de T8 e T11); backend com todas as tarefas concluídas nas specs 001, 002, 008 e 011, e com tarefas concluídas, salvo as listadas abaixo, nas specs 003, 006, 009 e 010 (contagem de `[x]` e `[ ]` nos `tasks.md` em 10/11/2026) |
| **Documentado** | Matriz de conformidade, roteiro de demonstração, objetos e justificativas, 30 tuplas (cenário D aprovado), README com a documentação oficial e os registros históricos |
| **Pendente para publicar** | Commits por etapa na `feat/012-etapa06`, criação da nova `main` e publicação no novo repositório. Depende de autorização |
| **Planejado para 21/11/2026** (escopo mínimo da spec 012) | **T8 parte B e T11 parte B**: as 8 verificações de qualidade, na ficha e no painel; **T12** (funcionalidades sem backend visíveis e desabilitadas), **T13** (XSS de ponta a ponta e responsividade) e **T14** (E2E no CI e documentação). Não fazem parte da entrega de 13/11 |
| **Pendente de implementação** (tarefas `[ ]` de specs aprovadas, sem bloqueio pendente no `tasks.md`, sem prazo definido; nenhuma iniciada) | 003/T8, mapeamento grupo → papel (só o pré-requisito T7 está concluído; os grupos vêm do diretório da spec 004, em Rascunho); 006/T10, teste de desempenho da busca; 009/T3, teste de desempenho do dashboard; 009/T2b, cache, só se a T3 exigir (substitui a T2, adiada); 010/T3, conversor da planilha (R2.1 o condiciona à planilha do cliente) |
| **Bloqueado por dependências externas** (decisões do cliente ou specs de outros donos) | Spec 012 T15 a T23 (aparelhos, solicitações, notificações, campos da unidade, revisão, histórico no escopo do distrito, exportação e importação, usuários, leitura por escopo) |
| **Specs em Rascunho** | 004 (LDAP e OIDC), 005 (S3) e 007 (validação de dados), sem tarefas concluídas |

Limitações conhecidas, registradas na matriz:
- **Dados de um único dia:** o seed concentra o histórico num só dia, e a linha das alterações mostra "histórico insuficiente" até haver uso.
- **`ON DELETE SET NULL` sem tela:** a remoção de equipamentos não tem tela, por depender da decisão DF1; a prova é por teste de integração.
- **Restrições só da interface:** as restrições do R7.4 limitam a interface, não a API, até a decisão do cliente.

---

## 9. Como executar e demonstrar

1. **Pré-requisitos:**
   - Docker 26 ou mais novo, com Compose v2;
   - `uv` (Python 3.13);
   - GNU Make;
   - Chrome ou Chromium, para os testes da interface.
2. **Chaves locais**, uma vez, em `secrets/`, que fica fora do Git: `src.tools.jwt_keys` e `src.tools.crypto_keys` (README § Subir o ambiente).
3. **Subir:** `docker compose -f docker/compose.yml up -d --build --wait`. Com mais de um ambiente na máquina, use `-p <projeto>` e as portas `SGS_HTTP_PORT` e `SGS_HTTPS_PORT`.
4. **Dados de demonstração:** `sgs-admin seed demo` dentro do container da API, com `SGS_SEED_SENHA` definida na hora (README § Dados de demonstração). Não rode seed nem migração contra um banco que precisa ser preservado.
5. **Acesso:** `https://localhost/` (ou a porta configurada). Entre com um usuário do seed; o 2FA é cadastrado no primeiro acesso.
6. **Demonstração:** siga [docs/banco/08-roteiro-demonstracao.md](../banco/08-roteiro-demonstracao.md) (cerca de 8 minutos, com Gestor de Dados, Auditor e Técnico Distrital, e um plano para quando um passo falhar).
7. **Testes:**
   - `make check`;
   - `uv run pytest -m slow tests/e2e_front`, que sobe e derruba um compose próprio;
   - para os testes de integração, deixe `SGS_TEST_DATABASE_URL` sem definir (eles usam testcontainers) ou aponte para um servidor descartável, porque eles criam e apagam bancos.
8. **Cuidados:**
   - nunca versionar `secrets/` nem `.env`, nem copiar chaves reais para o repositório;
   - as senhas do compose e do script de inicialização do banco são só para ambientes locais e descartáveis;
   - os valores dos comandos de exemplo do README (ex.: a senha do seed) são ilustrativos: escolha valores próprios;
   - em ambientes reais, use credenciais fortes e únicas, por um mecanismo seguro de configuração;
   - a demonstração grava no banco (sessões, auditoria, cadastros).

---

## 10. Estrutura da documentação

| Tipo | Documentos |
|---|---|
| **Oficiais e atuais** | [README](../../README.md); [matriz de conformidade](../banco/07-matriz-conformidade.md); [roteiro de demonstração](../banco/08-roteiro-demonstracao.md); este relatório (visão geral) |
| **Referência técnica atual** | `docs/banco/01` a `06` e `planos-indices.txt`; `specs/` (requisitos, design, tarefas e registros de cada entrega); `docs/adr/`; `docs/frontend-integracao.md`; `docs/api/`; `contracts/openapi.yaml` |
| **Registros históricos** (preservados sem alteração) | relatório geral de andamento, relatório de implementação e guia de execução (10/11/2026, `4a07f71`); resumo de status, validação final, requisitos × evidências, PR de publicação e checkpoint (09/11/2026); plano de integração do front (09/11/2026); `docs/integration-audit/` (09/11/2026). Não refletem a Etapa 06 nem a aprovação do cenário D (README § Registros históricos) |
| **Relatórios locais de gestão de segurança** | três relatórios em `docs/relatorios/`, mantidos fora do controle de versão por decisão do responsável pelo projeto |

---

## 11. Conclusão

**Estado geral.** O SGS Recife tem um banco PostgreSQL completo para a disciplina: modelo normalizado, integridade referencial, views, funções, procedimentos (um com cursor), triggers de log, versão e auditoria, particionamento e índices com prova de uso. A API aplica autenticação forte, RBAC com escopo e auditoria em cada alteração. Com a Etapa 06, **todo** esse trabalho ficou visível e utilizável pela interface.

**Principais entregas.**
- Painel com dados reais, gráficos e filtros.
- CRUD de 5 tabelas, com integridade preservada (exclusão lógica onde o modelo exige).
- Ficha com versão e histórico.
- Conflito de versão tratado.
- Procedimentos e triggers demonstráveis.
- Matriz de conformidade e roteiro de demonstração.

**Pronto para apresentação:**
- a interface e o banco, conforme o roteiro;
- a documentação oficial;
- as evidências de teste (última execução registrada: 1029 aprovados no `make check` e 118 na suíte E2E).

**Pendências reais:**
- consolidar a branch em commits, criar a nova `main` e publicar no novo repositório (depende de autorização);
- as partes B da T8 e da T11 (8 verificações de qualidade) e as tarefas T12 a T14 da spec 012, planejadas para 21/11/2026;
- as specs e tarefas bloqueadas por decisões do cliente ou de outros donos, listadas na seção 8.
