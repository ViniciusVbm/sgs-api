# SGS API · Resumo do status do projeto

*Situação em 09/11/2026. Fonte: auditoria em `docs/integration-audit/` (detalhes e evidências nos docs 01 a 11).*

**Legenda:** ✅ implementado e testado · 🟡 parcial · ⬜ pendente · ⛔ bloqueado (espera decisão ou aprovação de spec)

---

## 1. Situação atual

- **Base escolhida para a versão final: a branch `feat/011-integracao`.**
- **Por que a 011:**
  - já tem a maior parte do que a disciplina de Banco de Dados pede;
  - segue a arquitetura e as regras do projeto;
  - tem autenticação e permissões seguras;
  - entra na `main` **sem nenhum conflito**;
  - todos os testes dela passaram em 09/11/2026 (646 casos no `make check`, mais 5 testes de TLS).
- **O que vem da `feat/003-interface-dashboard` (Vinicius): só conteúdo, não o código:**
  - os dados das 30 unidades e dos 30 equipamentos;
  - as 4 consultas da Etapa 3, a reescrever;
  - o formato do resumo do dashboard;
  - o desenho das rotas de equipamento.
- **Por que não mesclar a 003 diretamente:**
  - usa outro esquema de banco, incompatível com o da 011;
  - as migrações dela colidem com as da `main`;
  - identifica o usuário por um cabeçalho sem senha, o que é uma falha de segurança.
- **A consolidação ainda não foi feita.** A `main` continua como estava. As 15 branches foram preservadas (tags locais `arquivo/*` e um backup completo) e nenhuma foi apagada.

## 2. O que já está implementado

Tudo abaixo está na `feat/011-integracao`, salvo indicação. A `main` hoje só tem a fundação (marcada com "main").

| Área | Situação |
|---|---|
| **Banco de dados e integridade** | ✅ PK, FK, CHECK, DEFAULT, UNIQUE; ✅ `ON UPDATE CASCADE` (tipo de equipamento) e `ON DELETE SET NULL` (equipamento do serviço), com teste |
| **Views, funções, procedures e triggers** | ✅ 2 views (inventário e histórico, com 3 JOINs ou mais); ✅ 2 funções, uma com IF/ELSIF; ✅ 2 procedures (desativar unidade; criar partições, com CURSOR); ✅ 2 triggers (versão da unidade; log do banco); ✅ 7 índices com justificativa (🟡 falta provar o uso) |
| **Auditoria e rastreabilidade** | ✅ trilha com quem, quando, ação e valor anterior e novo, encadeada por hash e imutável (main); ✅ log automático do banco por trigger; 🟡 os papéis do autor não são gravados; 🟡 o nome do gestor vai sem máscara na trilha |
| **Autenticação e segurança** | ✅ tokens assinados (ES256) e chaves públicas (JWKS); ✅ TLS entre a API e o banco; ✅ cifra de campos sensíveis (main); ⬜ **não há login** |
| **RBAC e permissões** | ✅ 7 papéis, 17 permissões, escopo por área, distrito ou unidade, acesso negado por padrão, negações auditadas |
| **API e endpoints** | 🟡 só criar unidade, duas consultas do dashboard e health. Não há atualizar, excluir, equipamentos nem serviços |
| **Consultas SQL e dashboard** | ✅ SQL explícito em arquivos `.sql`; ✅ anti-join e FULL OUTER JOIN com filtros; 🟡 só 2 consultas expostas; ⬜ indicadores estatísticos |
| **Testes e CI** | ✅ testes unitários, de integração (PostgreSQL real) e de arquitetura, todos aprovados no commit `556599f`; ✅ lint, tipos, bandit e pip-audit no CI (o GitHub Actions está bloqueado, e o `make check` local vale no lugar, pelo ADR-0008) |

**Não existem em nenhuma branch:** front-end (o HTML está fora do repositório e será integrado depois), LDAP, OIDC, S3 e governança.

## 3. O que ainda falta implementar

| Área | O que falta | Prioridade |
|---|---|---|
| Cadastro (BD Etapas 3 e 6) | CRUD completo de unidades, equipamentos, serviços e referências (006/T4 a T9) | P0 |
| Consultas (BD Etapa 4) | 2 consultas com subconsulta (011/T12) | P0 |
| Índices (BD Etapa 4) | Provar com volume que os índices são usados (011/T9) | P0 |
| Views e procedures na API | Inventário (011/T13) e log do banco (011/T15); ⛔ histórico pela view (011/T14) depende da **spec 008** | P0 |
| Modelagem (BD Etapa 1) | Minimundo, modelo conceitual, modelo lógico e dicionário de dados | P0 |
| Dados de demonstração (BD Etapa 2) | ⛔ 30 registros por tabela: depende do CRUD, da **decisão D1** e da **spec 010** | P0 |
| Catálogo de consultas | ⛔ lista das consultas para o front (011/T19): depende da 011/T14, portanto da **spec 008** | P0 |
| SQL consolidado | ⛔ arquivo único `make sql-bd` (011/T20): depende das tarefas T1 a T19 da 011 | P0 |
| Indicadores do dashboard | ⛔ resumo estatístico: depende da **spec 009** | P0 |
| Login | Login, renovação e saída, e o comando para criar o primeiro administrador (002/T3, T6, T8) | P1 |
| Permissões | `GET /me`, administração de papéis, teste que garante a proteção de todas as rotas (003/T5 a T7) | P1 |
| Testes de aceitação | Roteiro reproduzível e relatório de resultados (depende do CRUD e do login) | P1 |
| Trilha de auditoria | ⛔ consulta e verificação da trilha: depende da **spec 008** | P1 |
| Governança | Documentos de fornecedores, matriz de riscos, registro de riscos, ISO 38500, COBIT APO10 e LGPD; ⛔ tabelas no banco só se o grupo decidir (D5) | P1 |
| LDAP e OIDC | ⛔ depende da **spec 004** (Rascunho) | P2 |
| Exportação para S3 | ⛔ depende da **spec 005** (Rascunho) | P2 |

## 4. Prioridades e prazos

- **P0, até 13/11 (Banco de Dados):**
  - **pode começar logo após a consolidação:** CRUD (a maior tarefa), subconsultas, inventário, log do banco, prova dos índices e documentos de modelagem;
  - **depois do CRUD:** dados de demonstração;
  - **se a 008, a 009 e a 010 forem aprovadas a tempo:** histórico, catálogo, SQL consolidado e indicadores.
- **P1, até 21/11 às 09h (Projetos, Entrega 11):** login, depois permissões e testes de aceitação; documentos de governança; trilha de auditoria (se a 008 for aprovada).
- **P2, depois das entregas:** LDAP, OIDC, S3, TOTP, rate limit e otimizações.

## 5. Decisões pendentes

| ID | Decisão | Quem decide | O que trava |
|---|---|---|---|
| D1 | Tabelas de domínio fechado (8 distritos, 7 papéis…) precisam ter 30 registros, ou basta justificar? | **Professor de BD** (o grupo pergunta) | Dados de demonstração |
| D2 | Mascarar o nome do gestor da unidade na trilha de auditoria? | Rafael | Ajuste de LGPD |
| D3 | Cada papel vê o dashboard só do seu escopo, ou todos veem a rede inteira? | Rafael | Comportamento das consultas (não trava a implementação) |
| D4 | Aprovar as specs 008, 009 e 010 (e depois 004 e 005) | Rafael | Histórico, catálogo, SQL consolidado, dados de demonstração, indicadores, trilha, LDAP, OIDC, S3 |
| D5 | Governança só em documentos, ou também com tabelas e telas? | Grupo | Escopo da governança |
| D6 | Criar a tarefa na spec 011 para os ajustes de banco (índices extras, permissões, `updated_at`) | Rafael | Ajustes de base |

**A que mais destrava trabalho:** aprovar a spec **008**, e logo depois a **010**, com a resposta do professor sobre a D1.

## 6. Próximos passos

1. ✅ **Preservar branches e documentos.** Feito em 09/11: tags locais, backup completo do repositório e cópia dos documentos.
2. **Finalizar a revisão da auditoria.** Os documentos estão revisados; falta a leitura do grupo.
3. **Submeter a 011 pelo fluxo de PR** (`feat/011-integracao` → `main`, pela interface do GitHub, conforme o ADR-0008).
4. **Validar a nova `main`:** `make check` e testes de TLS verdes.
5. **Executar as tarefas prioritárias** (P0 e depois P1), cada uma em sua branch e com seu PR.
6. **Validar os entregáveis** e preparar a publicação no novo repositório.

> ⚠️ **Ainda dependem de autorização:** a consolidação (passo 3), qualquer push e a publicação no novo repositório. **Nenhuma branch deve ser apagada.** Os secrets de desenvolvimento ficam fora do Git.
