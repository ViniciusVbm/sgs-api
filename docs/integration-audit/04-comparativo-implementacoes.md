# 04 · Comparativo das implementações

Só duas linhas de código têm funcionalidades sobrepostas fora da `main`:
- **`feat/011-integracao`**, de Rafael;
- **`feat/003-interface-dashboard`**, de Vinicius.

A `feat/002-fundacao-vinicius` é subconjunto da 003, e o resto está na `main`.

Os dois esquemas são **incompatíveis** (nomes, tipos de chave, revisões de migração). Por isso a escolha é feita **funcionalidade por funcionalidade**. Da 003 aproveitam-se dados, consultas e formatos de rota, nunca arquivos inteiros.

Nada foi entregue ao professor ainda (decisão do usuário em 09/11), então a escolha é livre, por mérito técnico.

Critérios: qualidade, compatibilidade com a arquitetura (`steering/structure.md`, import-linter), segurança, completude, testabilidade, integridade do banco, integração com os demais módulos e atendimento aos requisitos acadêmicos.

---

## F1. Esquema de dados do cadastro
1. **Branch que contém:** 011 (`migrations/sql/0006/*.sql`, `migrations/versions/0006_registry.py`).
2. **Semelhante:** 003V (`src/resources/seeds/1_SQL_Criacao_Tabelas.sql`, `migrations/versions/0002_etapa2_tabelas.py`, `0003_etapa3_legado.py`).
3. **Superior:** 011.
4. **Por quê:**
   - segue `docs/architecture/modelo-dados.md` e `steering/structure.md` (nomes em inglês no banco);
   - tem tabelas de referência normalizadas (distritos, áreas, tipos) em vez de texto livre com CHECK;
   - uuid7 nas tabelas de negócio;
   - um `.sql` por objeto, com justificativa;
   - `name_normalized` gerado pela função;
   - unicidade parcial do CNES;
   - os tipos de serviço existem (a 003V não tem `services`).
5. **Aproveitar:** tudo de `migrations/sql/0006/*` e `migrations/versions/0006_registry.py`.
6. **Adaptar:** índice em `equipments.unit_id` e `services.equipment_id`; trigger ou ajuste de `updated_at` (doc 06).
7. **Complementar:** dados da 003V (F7).
8. **Conflitos:** nenhum se a 003V não for mesclada. Se fosse, as revisões `0002` e `0003` duplicariam as da `main` e da 011, e o Alembic falharia.
9. **Testes após integrar:** `test_schema_registry.py`, `test_integridade.py`, `test_migracoes_sincronizadas.py`. Todos aplicam a cadeia inteira num PostgreSQL limpo de testcontainers e passaram no `556599f` em 09/11/2026. O `downgrade base` não tem teste e não faz parte do roteiro.

## F2. Migrações
- **Superior:** 011. A cadeia é linear: 0001 → 0001_1 → 0002 → 0003 → 0003_1 → 0006 → 0011_05 → 0011_03 → 0011_06 → 0011_04 → 0011_07 → 0011_08.
  - O SQL é carregado por `migrations/sql_loader.py`, com modo offline (`alembic upgrade --sql`).
  - É testada por `tests/unit/migrations/test_sql_loader.py`.
- **003V:** a `0002_etapa2_tabelas` pula a `0001_1` e reusa a revisão `0002`; a `0003_etapa3_legado` reusa a `0003`. **Descartar.**

## F3. Autenticação
| | 011 | 003V |
|---|---|---|
| Mecanismo | Bearer ES256, `kid`, JWKS (`identity/infrastructure/tokens.py`, `identity/api/jwks.py`) | cabeçalho `X-User-Id` sem credencial (`access/api/deps.py:20-36`) |
| Sessão | conferida a cada requisição (`identity/api/deps.py`) | nenhuma |
| Login | **não há**; falta 002/T3 | não há |
| Segurança | boa | **crítica**: personificação em dev e teste; prod sempre 401 |

- **Superior:** 011.
- **Complementar:** 002/T3 (login local e Argon2id), T6 (refresh), T8 (`sgs-admin create-user`).
- **Testes:** `tests/unit/identity/test_tokens.py` e, depois da T3, o fluxo login → rota protegida → logout.

## F4. Autorização (RBAC)
- **Superior:** 011:
  - tabelas `roles`, `permissions`, `role_permissions(max_scope)`, `role_assignments`, `group_role_mappings`;
  - `pode()` puro no domínio;
  - `ResolvedorDePermissoes` com cache de 30 s e `authz_version`;
  - `require()` com `ResourceRef`;
  - 403 auditado.
- **003V:** strings `;` em `PERFIL.permissoes` e apelidos fixos em `access/application/autorizacao.py:6-15`; o COORD_TECNICO não tem permissão nenhuma.
- **Adaptar:** preencher `Ator.papeis` (doc 06, P1) e decidir o escopo de `dashboard:read` (pergunta em aberto na 011).
- **Complementar:** 003/T5 (teste de arquitetura das rotas protegidas), T6 (`GET /me`), T7 (administração de atribuições).
- **Testes:** `tests/integration/access/*`, `tests/unit/access/*`.

## F5. Auditoria das alterações
- **Superior:** 011 e `main`:
  - o `audit_log` encadeado é gravado na mesma transação (`registry/application/unidades.py` chama `registrar` na mesma sessão);
  - a sessão de negócio usa `scope="function"`;
  - o `db_change_log` por trigger cobre alterações fora da API.
- **003V:** tabela `alteracao` separada, sem cadeia de hash. Equipamento não é auditado, e o `alteracao.idunidade NOT NULL` impede auditar equipamento sem unidade. O commit provavelmente acontece depois da resposta.
- **Descartar:** a tabela `alteracao` e `audit/domain/alteracao.py` da 003V.
- **Aproveitar da 003V:** a ideia de exigir **motivo** na mudança de status. A 006/R3 já prevê justificativa na desativação; conferir na T6.

## F6. Objetos avançados de banco (Etapas 4 e 5)
- **Superior:** 011, sem concorrente real: views, funções, procedures com cursor, triggers, partições, índices justificados e papel `sgs_owner`.
- **003V:** só `normalizar_unidade_saude_etapa3()` e o trigger que a chama. A 011 já resolve a normalização com `fn_normalize_name` e uma coluna gerada, que é mais simples e não tem efeito colateral.
- **Adaptar:** usar as views nas rotas (011/T13, T14).

## F7. Seed com 30 tuplas
- **Contém:** só a 003V (`src/resources/seeds/2_SQL_Insercao_Dados.sql`: 30, 30, 30, 30 e 31 linhas).
- **Na 011:** só as referências de domínio fechado (8 distritos, 4 áreas, 7 tipos de unidade, 3 tipos de equipamento, 4 tipos de serviço), mais 7 papéis e 17 permissões.
- **Escolha:** **aproveitar o conteúdo da 003V** (nomes, endereços, CNES e telefones das 30 unidades; os 30 equipamentos) e reescrevê-lo sobre o esquema da 011. Vira `sgs-admin seed demo` (spec 010) mais um `.sql` de inserção para a T20.
- **Adaptar:**
  - trocar o texto livre de distrito e tipo pelas FKs;
  - gerar uuid7;
  - criar 30 ou mais serviços;
  - criar 30 ou mais usuários com Argon2id, em vez de um bcrypt compartilhado;
  - não reaproveitar segredos TOTP de mentira;
  - corrigir "Muribecca".
- **Decisão necessária:** os domínios fechados (distritos com 8 reais) contra a regra das 30 tuplas por tabela. Ver o doc 08, item D1.
- **Testes:** um teste no formato de `tests/integration/test_etapa2_banco.py` da 003V, contando 30 ou mais linhas por tabela depois do seed.

## F8. Consultas da Etapa 3 e catálogo
- **011:** anti-join e FULL OUTER JOIN (`dashboard/infrastructure/sql/units_without_services.sql`, `unit_equipment_reconciliation.sql`), com escopo, filtros e paginação.
- **003V:** `consultas_etapa3.sql`, com 4 consultas: unidades por categoria; equipamentos por tipo e distrito; alterações por período em 7 e 30 dias; 10 alterações mais recentes.
- **Escolha:**
  - manter as da 011;
  - **reescrever as 4 da 003V** como `.sql` do módulo `dashboard`, sobre `health_units`/`vw_unit_inventory` e `vw_unit_history`;
  - expor tudo no catálogo (011/T19, R3).
  - O resultado são 8 consultas ou mais: 2 da 011, 2 subconsultas da T12 e as 4 da 003V.
- **Conflito:** os nomes de coluna mudam (`distritosanitario` vira `districts.name`, `alteracao` vira `audit_log` ou a view de histórico).

## F9. CRUD
- **011:** só `POST /api/v1/unidades`, mas com unicidade, 409, 422, escopo de área, concorrência e auditoria (`registry/api/unidades.py`, `test_criar_unidade.py` com 14 casos).
- **003V:** unidades (GET lista e detalhe, POST, PATCH de status com If-Match e versão, exclusão lógica) e equipamentos (CRUD completo com DELETE físico, inclusive sem unidade).
- **Escolha:**
  - **a implementação é a da 011**, estendida pela 006/T4 a T9;
  - **a 003V vale como referência de contrato**: rotas `/unidades/{id}/equipamentos` e `/equipamentos/{id}`, `If-Match` com 428/412;
  - não aproveitar código, porque ele depende de `X-User-Id` e de tabelas em português.
- **Bug da 003V a não repetir:** `quantidade: null` dá 500 (`servicos.py:78`).
- **Testes:** os da 006/T4 a T9, um por rota, com 401, 403, 404, 409, 412, 422 e auditoria.

## F10. Dashboard estatístico
- **011:** só consultas de qualidade.
- **003V:** `GET /api/v1/dashboard/resumo` (totais por status, tipo e distrito; sem CNES; equipamentos por tipo e distrito; alterações em 7 e 30 dias; recentes).
- **Escolha:** **a ideia da 003V** como base da spec 009 (que está em Rascunho e precisa da emenda que a 011 promete). Implementação nova sobre `vw_unit_inventory`.

## F11. Infraestrutura e ferramentas
- **011:** TLS no banco (`db-certs`, `pg_hba.conf`), `sgs-admin banco particoes`, `jwt_keys`. **Manter.**
- **003V:**
  - `src/tools/seed_db.py`: substituído pelo `sgs-admin seed demo`;
  - `get-docker.sh`: **descartar**, é o instalador oficial do Docker;
  - mudanças em `Dockerfile` e `Makefile`: conferir se algo serve, como copiar arquivos `.sql`; a 011 já resolve isso com `migrations/sql`.

## F12. Specs e steering
- **003V:** trocou todo `Rascunho` por `Aprovado`, inclusive `_templates`; reescreveu partes da 006 e da 009 para o esquema em português; alterou `steering/structure.md`. **Descartar tudo:** contraria a regra 1 do AGENTS.md (a aprovação é do dono humano).

---

## Resumo das escolhas
| Funcionalidade | Base | O que aproveitar da 003V |
|---|---|---|
| Esquema e migrações | 011 | — |
| Autenticação | 011, mais 002/T3 | — |
| RBAC | 011 | — |
| Auditoria | main e 011 | exigência de motivo no status |
| Objetos de BD | 011 | — |
| Seed com 30 tuplas | nova (010) | **conteúdo** de `2_SQL_Insercao_Dados.sql` |
| Consultas | 011 | **4 consultas** de `consultas_etapa3.sql`, reescritas |
| CRUD | 011 e 006 | **contrato** das rotas de equipamento e If-Match |
| Dashboard | nova (009) | **formato** de `/dashboard/resumo` |
| Testes | 011 | **modelo** de `test_etapa2_banco.py` |

## Funcionalidades duplicadas
- Módulos `access`, `registry`, `dashboard`, `identity/infrastructure/tables.py`: as duas branches adicionam com o mesmo caminho. Seria conflito add/add.
- `contracts/openapi.yaml`, `src/main.py`, `migrations/env.py`, `pyproject.toml`, `src/core/errors.py`, `audit/infrastructure/tables.py`, `tests/integration/test_migracoes_sincronizadas.py`: as duas modificam.
- Normalização de nome: `fn_normalize_name` mais coluna gerada (011) contra função e trigger (003V).
- Auditoria: `audit_log` (main e 011) contra `alteracao` (003V).
- Usuário e perfil: `users`, `roles` e `permissions` (main e 011) contra `USUARIO` e `PERFIL` (003V).
