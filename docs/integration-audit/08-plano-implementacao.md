# 08 · Plano de implementação do que falta

*Revisado em 09/11/2026: dependências conferidas contra o texto das tarefas em `specs/011-recursos-banco-dados/tasks.md` (commit `556599f`) e contra o status das specs na `main`.*

## Legenda
**Prioridade:**
- P0: prazo de 13/11 (Banco de Dados);
- P1: prazo de 21/11 às 09h (Projetos, Entrega 11);
- P2: depois das entregas principais.

**Complexidade:** P (até meio dia), M (1 dia), G (2 dias ou mais).

**Estado:**
- **PRONTO**: spec aprovada, sem decisão externa. Pode começar assim que as dependências internas indicadas estiverem concluídas.
- **DEPENDE**: spec aprovada, mas espera outra tarefa deste plano.
- **BLOQUEADO**: espera uma decisão humana (D1 a D5) ou a aprovação de uma spec em Rascunho. Pela regra 1 do `AGENTS.md`, não pode ser executado antes disso.

**Base comum:** toda tarefa depende do **passo 1 do doc 07** (fast-forward da 011, ainda **não executado**). O passo 1 não depende de nenhuma tarefa abaixo.

Todas seguem o `/spec-implementar`: teste primeiro, depois `make check` verde, depois `[x]` em `tasks.md`.

## Decisões pendentes (bloqueiam itens)
| ID | Decisão | Quem decide | Bloqueia | Recomendação da auditoria |
|---|---|---|---|---|
| D1 | 30 tuplas nos domínios fechados (8 distritos, 4 áreas técnicas, 7 tipos de unidade, 3 tipos de equipamento, 4 tipos de serviço, 7 papéis, 17 permissões); a decisão U4 da 011 aceita menos de 30 com justificativa | **professor de BD**, consultado pelo grupo | I6 | perguntar ao professor; se não houver resposta, completar até 30 onde o domínio admite e justificar o resto no README (a 011/T20 já prevê essa seção) |
| D2 | `manager_name` em claro no `audit_log` (P2 do doc 06) | Rafael (dono da 006) | correção P2 (passo 2 do doc 07) | mascarar como no `db_change_log` |
| D3 | Escopo de `dashboard:read` (P3) | Rafael (dono da 003 e da 011) | comportamento das consultas da I2, I4 e I5 (elas funcionam com qualquer escolha) | A, D e U para COORD_TECNICO, TECNICO_DISTRITAL e GESTOR_UNIDADE |
| D4 | Aprovar as specs 008, 009 e 010 (para P0 e P1) e 004 e 005 (para P2) | Rafael | I4/T14, I5, I6, I8, I9, I12, I15, I16 | priorizar a 008 (destrava T14, T19 e T20), a 010 (seed) e a 009 com a emenda que a 011 promete |
| D5 | Governança: só documentos ou também tabelas e rotas | grupo | módulo da I14 | só documentos em `docs/governanca/` |
| D6 | Ajustes de base (passo 2 do doc 07) precisam de tarefa nova na 011 | Rafael | I1b | criar a 011/T21 |

---

## P0 · Banco de Dados (13/11/2026)

### I1a. Fast-forward da 011 (passo 1 do doc 07)
- **Estado:** PRONTO. Depende só do passo 0, já executado.
- **Complexidade:** P.
- **Concluído quando:** a `main` for `556599f`, com `make check` (646) e e2e (5) aprovados.

### I1b. Ajustes de base (P1, P4, P5, P6, P9, P11 do doc 06)
- **Estado:** **BLOQUEADO** (D6: não há tarefa na spec; D2 para a máscara).
- **Complexidade:** P.
- **Arquivos:** migração nova `0011_09` com `.sql` em `migrations/sql/0011_09/`, `src/modules/access/api/deps.py`, `.env.example`.
- **Testes:** `test_privilegios.py`, `test_integridade.py`, EXPLAIN dos índices novos.

### I2. 011/T12 · Consultas com subconsulta
- **Estado:** PRONTO (bloqueada pela T11, que já está feita).
- **Disciplina:** BD Etapa 4.
- **Complexidade:** P.
- **Arquivos:** `src/modules/dashboard/infrastructure/sql/districts_cnes_above_network.sql` (escalar no `HAVING`), `units_with_services_outside_cnes.sql` (`EXISTS`), rotas e schemas, `contracts/openapi.yaml`.
- **Testes:** `tests/integration/dashboard/test_consultas_qualidade.py::test_distritos_cnes*` e `::test_fora_cnes*`.
- **Concluído quando:** esses testes passarem (com escopo distrital, a "rede" é só o distrito).

### I3. 006/T4 a T9 com 011/T16 a T18 · CRUD em 4 tabelas
- **Estado:** PRONTO (006 e 011 aprovadas; os bloqueios internos, 006/T3, 011/T2, T5, T6 e 003/T4, já estão feitos).
- **Disciplina:** BD Etapas 3 e 6.
- **Impacto:** **crítico**.
- **Complexidade:** G, a maior tarefa.
- **Ordem:**
  1. T4: listar, buscar, filtrar e detalhar.
  2. T5 com 011/T17: atualizar com If-Match, ligado à `version` do trigger.
  3. T6 com 011/T16: desativar pela `sp_deactivate_unit`.
  4. T7: equipamentos (contrato da 003V como referência).
  5. T8: serviços.
  6. T9 com 011/T18: referências; `PATCH /referencias/tipos-equipamento/{id}` com cascata.
- **Testes (nomes da spec 011):** `tests/integration/registry/test_desativar.py`, `test_versao_fora_da_api.py`, `test_referencia_codigo.py`, mais os testes da 006/T4 a T9; regressão do `quantidade: null` (P15).
- **Concluído quando:** houver insert, update e delete (lógico ou físico) por rota em `health_units`, `equipments`, `services` e ao menos uma referência, com auditoria na mesma transação.

### I4. 011/T13 a T15 · Inventário, histórico e log do banco na API
| Tarefa | Estado | Conteúdo | Teste da spec |
|---|---|---|---|
| T13 Inventário | PRONTO | `unit_inventory.sql` sobre `vw_unit_inventory`, rota e schema | `tests/integration/dashboard/test_inventario.py` |
| T14 Histórico pela view | **BLOQUEADO** (D4) | `unit_history.sql` sobre `vw_unit_history` **na rota `GET /unidades/{id}/historico` da 008/T2**; a spec 008 está em **Rascunho** | `tests/integration/audit/test_historico_unidade.py` |
| T15 Log do banco e partições | PRONTO | `db_change_log_list.sql`, `db_change_log_partitions.sql`, rotas `GET /auditoria/banco` e `/auditoria/banco/particoes` | `test_log_banco_api.py`, `test_particoes_api.py` |

- **Disciplina:** BD Etapas 4, 5 e 6.
- **Complexidade:** M.

### I5. 011/T19 · Catálogo de consultas, mais as 4 consultas da 003V reescritas
- **Estado:** **DEPENDE** de I2 e da I4 inteira. Pela spec, a T19 é "bloqueada por: T11, T12, T13, T14, T15". Como a T14 está bloqueada (D4), **a I5 também está bloqueada** até a 008 ser aprovada e a T14 entregue.
- **Disciplina:** BD Etapas 3 e 6.
- **Complexidade:** M.
- **Arquivos:** lista fixa de descrições no `dashboard`, rota `GET /api/v1/dashboard/consultas` filtrada pelas permissões efetivas.
- **As 4 consultas reescritas da 003V:** são conteúdo complementar; ainda não há tarefa na spec para elas. Precisam ser incluídas por emenda da 011 ou da 009 antes de serem implementadas.
- **Teste:** `tests/integration/dashboard/test_catalogo.py`.

### I6. Seed com 30 tuplas (spec 010)
- **Estado:** **BLOQUEADO** (D1 e D4: a 010 está em Rascunho) e **DEPENDE** da I3 (os serviços e equipamentos precisam do CRUD e do esquema final).
- **Disciplina:** BD Etapa 2.
- **Impacto:** **crítico**.
- **Complexidade:** M.
- **Arquivos:** `src/tools/sgs_admin.py` (`seed demo`), `.sql` de inserção, teste no modelo de `test_etapa2_banco.py` da 003V.
- **Concluído quando:** cada tabela tiver 30 ou mais linhas (ou exceção justificada conforme D1) depois do seed, e o seed for idempotente.

### I7. 011/T9 · Prova de uso dos índices com volume
- **Estado:** PRONTO. A spec diz "bloqueada por: T3", já feita. **Não depende do seed**: a T9 cria a própria fixture de volume (1.000 unidades, cerca de 3.000 serviços e a trilha pelo `audit.registrar`).
- **Disciplina:** BD Etapa 4.
- **Complexidade:** P.
- **Teste:** `tests/integration/db/test_indices.py -m slow` (o plano do histórico usa `ix_audit_log_entity`; o dos serviços de uma unidade usa `ix_services_unit_id`). O `EXPLAIN` fica registrado no cabeçalho dos `.sql` dos índices.

### I8. 011/T20 · Arquivo SQL único e documentação, mais os documentos da Etapa 1
- **011/T20:**
  - **Estado:** **DEPENDE** de 011/T1 a T19, portanto **bloqueada** enquanto a T14 e a T19 estiverem.
  - **Conteúdo:** `make sql-bd`, que gera `build/sql-bd.sql` (no `.gitignore`); teste de arquitetura dos cabeçalhos; seção da disciplina no README (onde está cada objeto, 30 tuplas, exclusão lógica).
  - **Testes:** `tests/tools/test_sql_bd.py`, `tests/architecture/test_sql_documentado.py`.
- **Documentos da Etapa 1** (minimundo, modelo conceitual, modelo lógico, dicionário de dados):
  - **Estado:** PRONTO. São documentação, sem código, e não dependem da T20.
  - **Arquivos:** `docs/banco/01-minimundo.md`, `02-modelo-conceitual.md`, `03-modelo-logico.md`, `04-dicionario-dados.md` (gerado de `information_schema` e `pg_description`).
- **Disciplina:** BD Etapas 1 e 2.
- **Complexidade:** M.

### I9. 009 · Indicadores estatísticos (`/dashboard/resumo`)
- **Estado:** **BLOQUEADO** (D4: a 009 está em Rascunho e sem a emenda que a 011 promete).
- **Disciplina:** BD Etapa 6.
- **Complexidade:** M.
- **Depende também de:** I4/T13.
- **Referência:** o formato vem do `/dashboard/resumo` da 003V.

---

## P1 · Projetos E11 (21/11/2026 às 09h)

### I10. 002/T3, T6, T8 · Login, refresh, logout e primeiro administrador
- **Estado:** PRONTO (002 aprovada).
- **Impacto:** **crítico**: sem isso a API não pode ser usada nem pelo front.
- **Complexidade:** G.
- **Arquivos:** porta e adaptador do `PasswordHasher` (Argon2id), caso de uso de login, rotas de login, refresh e logout, `sgs-admin create-user`, dependência `argon2-cffi`.
- **Testes:** `tests/integration/identity/test_login.py` (sucesso, senha errada com tempo constante, bloqueio, refresh rotativo, reuso detectado, logout).

### I11. 003/T5 a T7 · Teste de arquitetura das rotas, `GET /me` e administração de atribuições
- **Estado:** PRONTO. A T6 e a T7 **dependem** da I10 para uso de ponta a ponta.
- **Complexidade:** M.

### I12. 008 · Consulta da trilha e verificação da cadeia
- **Estado:** **BLOQUEADO** (D4: a 008 está em Rascunho).
- **Complexidade:** M.
- **Tarefas da spec:** T1 consulta paginada; T2 histórico da unidade (é a mesma rota da 011/T14); T3 trilha geral; T4 `test_verificar_cadeia.py`.

### I13. Testes de aceitação e relatório de resultados
- **Estado:** **DEPENDE** de I3 e I10 (e da I5 para o passo do catálogo).
- **Complexidade:** M.
- **Arquivos:** `tests/acceptance/test_roteiro_mvp.py` (roteiro do doc 09), `docs/testes/resultados-E11.md`.

### I14. Governança: fornecedores, riscos, ISO 38500, COBIT APO10, LGPD
- **Documentos:** PRONTO. Vão em `docs/governanca/`:
  - fornecedores;
  - matriz de probabilidade × impacto;
  - registro de riscos (interrupção de TI e vazamento na cadeia de fornecedores);
  - mapeamento para ISO 38500 e COBIT APO10;
  - LGPD técnica.
  - Cada controle cita arquivo e teste. Não declarar conformidade nem certificação.
- **Módulo `governance` (tabelas e CRUD):** **BLOQUEADO** (D5 e, se aprovado, uma spec nova).
- **Complexidade:** M (documentos) ou G (módulo).

---

## P2 · Depois de 21/11

| ID | Item | Estado | Complexidade |
|---|---|---|---|
| I15 | 004 · LDAP e OIDC (slapd e Keycloak no compose, módulo `directory`, `groups`, `user_groups`, sincronização) | BLOQUEADO (D4: 004 em Rascunho) | G |
| I16 | 005 · Exportação para S3 (SeaweedFS ou MinIO, `report_jobs`, URL pré-assinada) | BLOQUEADO (D4: 005 em Rascunho) | G |
| I17 | 002/T5, T7 · TOTP e rate limit | PRONTO; depende da I10 | M |
| I18 | Otimização (revisão de segurança, schemathesis, ADRs, `modelo-dados.md`, 006/T10) | PRONTO para itens isolados; 006/T10 depende da I3 | M |

---

## Caminho crítico
```
Passo 0 (feito) → I1a (fast-forward)
  ├─ P0 PRONTO:      I2 · I3 · I4/T13 · I4/T15 · I7 · I8-docs Etapa 1
  ├─ P0 DEPENDE:     I3 → I6 ;  I2 + I4 → I5 → I8/T20
  └─ P0 BLOQUEADO:   I1b (D6/D2) · I4/T14, I5, I8/T20 (D4: 008) · I6 (D1, D4: 010) · I9 (D4: 009)
P1:  I10 → I11 · I13 ;  I14-docs ;  I12 (D4: 008)
P2:  I15, I16 (D4) · I17 · I18
```

**O que destrava mais coisa:** aprovar a **008** (destrava T14, a 011/T19, a 011/T20 e a I12) e a **010**, mais a resposta do professor sobre D1 (destrava a I6).

## Opções de continuidade
| Opção | Escopo | Atende 13/11? | Atende 21/11? | Atende IAM e Segurança? |
|---|---|---|---|---|
| **A** · só consolidação | I1a | **não** (faltam CRUD, 30 tuplas, subconsultas, prova dos índices) | não (sem login) | parcial |
| **B** · consolidação e implementação | I1a, os itens PRONTO, e os BLOQUEADOS conforme forem destravados | só se D1 e D4 (008 e 010) saírem até cerca de 11/11 | sim | sim, com LDAP, OIDC e S3 depois de aprovados |
| **C** · B mais otimização | B mais I17 e I18 | igual a B | igual a B | mais robusto, mas I18 não cabe antes de 21/11 |

**Recomendação: Opção B.** Os itens PRONTO podem começar logo depois do I1a. Em paralelo, o grupo leva D1 ao professor e o Rafael decide D4 e D6. A otimização da C (I18) fica para depois de 21/11.
