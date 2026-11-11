# 30 tuplas por tabela (decisão D1)

> **Situação:** a interpretação abaixo (**cenário D**) foi **aprovada formalmente pelo professor**, conforme comunicado pelo responsável pelo projeto. O documento da aprovação (data e forma) não está anexado a este repositório. Nenhum seed, migração ou dado foi alterado para chegar a 30 registros, e nenhuma tupla artificial foi inserida. O cenário C ficou só como registro do plano alternativo, que não foi usado (§ Plano alternativo).

## Medição
- **Depois do seed:** valores medidos depois de `sgs-admin seed demo` (`tests/integration/tools/test_seed_demo.py`) e depois de `build/sql-bd-insercao.sql` (`tests/integration/tools/test_sql_bd.py`).
- **Ambiente local:** conferido em 10/11/2026 com `count(*)` exato, em transação somente leitura. A diferença em `audit_log`, `sessions` e `refresh_tokens` vem de um login de uso real (eventos `auth.*`), não do seed.
- **Testes:** em 10/11/2026, os dois testes passaram num PostgreSQL descartável (testcontainers), dentro de uma rodada de 82 aprovados.

| Tabela | Categoria | Depois do seed | Ambiente local (10/11) | 30 ou mais? | Motivo, quando abaixo de 30 |
|---|---|---:|---:|---|---|
| `health_units` | negócio | 37 | 37 | ✅ | 27 unidades da `feat/003` (as do Recife) e 10 de Saúde Mental |
| `equipments` | negócio | 31 | 31 | ✅ | |
| `services` | negócio | 35 | 35 | ✅ | |
| `users` | negócio (identidade) | 30 | 30 | ✅ | pessoas fictícias, todos os papéis |
| `role_assignments` | negócio (acesso) | 30 | 30 | ✅ | todos os escopos |
| `role_permissions` | matriz de acesso | 51 | 51 | ✅ | |
| `audit_log` | auditoria | 138 | 141 | ✅ | um evento por registro criado, mais o uso |
| `db_change_log` | auditoria (trigger) | 103 | 103 | ✅ | uma tabela lógica particionada por mês; as 14 partições são armazenamento, não tabelas do modelo |
| `unit_types` | referência aberta | 10 | 10 | ❌ | catálogo real da rede (7 da 0006, mais UPA, Hospital e Laboratório); o catálogo oficial depende do cliente (DF5 da spec 012) |
| `equipment_types` | referência aberta | 5 | 5 | ❌ | 3 da 0006, mais Academia da Saúde e Base do SAMU; mesmo caso |
| `service_types` | referência aberta | 4 | 4 | ❌ | os da 0006; mesmo caso |
| `districts` | domínio fechado | 8 | 8 | ❌ | os 8 distritos sanitários do Recife (DS-I a DS-VIII); um 9º não existe |
| `technical_areas` | domínio fechado | 4 | 4 | ❌ | Saúde Mental, Saúde Bucal, Atenção Primária e Média e Alta Complexidade |
| `roles` | domínio fechado (RBAC) | 7 | 7 | ❌ | os 7 papéis da arquitetura (spec 003), todos `is_system`, protegidos pelo trigger `trg_roles_protect_system` |
| `permissions` | domínio fechado (RBAC) | 17 | 17 | ❌ | as permissões `recurso:acao` da matriz; uma permissão inventada não teria rota |
| `group_role_mappings` | identidade (diretório) | 0 | 0 | ❌ | mapeia grupos do LDAP/OIDC para papéis (spec 004, não implementada); não há grupo real a mapear |
| `sessions` | identidade (uso) | 0 | 1 | ❌ | criada a cada login; não há seed |
| `refresh_tokens` | identidade (uso) | 0 | 1 | ❌ | criada e rotacionada pelo login; guarda o hash SHA-256 de uma credencial |
| `audit_chain_head` | infraestrutura | 1 | 1 | N/A | linha única **por construção**: `CHECK (id = 1)` (`ck_audit_chain_head_linha_unica`) |
| `alembic_version` | infraestrutura (ferramenta) | 1 | 1 | N/A | versão do schema, gravada pelo Alembic; não pertence ao modelo |

**Resumo:**
- 8 tabelas têm 30 tuplas ou mais;
- 12 tabelas físicas têm menos de 30: 3 referências abertas, 4 domínios fechados, 3 tabelas de identidade cujo conteúdo vem do uso ou de integração, e 2 de infraestrutura;
- todas as tabelas de **negócio** do minimundo (unidades, equipamentos, serviços, usuários e atribuições) e as duas de auditoria têm 30 ou mais.

## Por que as tabelas abaixo de 30 não são completadas
1. **Domínios fechados** (`districts`, `technical_areas`, `roles`, `permissions`). O conteúdo é a realidade do domínio ou a especificação de segurança:
   - um 9º distrito ou uma 5ª área técnica seriam dados falsos e apareceriam nos filtros, no painel e nos relatórios como se existissem;
   - um papel ou uma permissão inventados ampliariam a matriz RBAC (spec 003), que é negada por padrão. Seriam dado morto ou, pior, um caminho de acesso sem especificação.
2. **Linha única por construção** (`audit_chain_head`). O `CHECK (id = 1)` impede a 2ª linha. A tabela guarda o último hash da cadeia de auditoria, e mais linhas quebrariam o encadeamento.
3. **Tabela da ferramenta** (`alembic_version`). É do Alembic, não do modelo lógico (`03-modelo-logico.md` não a lista).
4. **Conteúdo gerado pelo uso** (`sessions`, `refresh_tokens`). Cada linha é uma sessão real, com o hash de um token. Semear 30 seria fabricar credenciais. Elas passam de 30 naturalmente com o uso: cada login cria uma sessão e um refresh token, e cada renovação cria outro.
5. **Integração não implementada** (`group_role_mappings`). Sem o diretório da spec 004, um mapeamento seria um grupo LDAP inexistente.
6. **Referências abertas** (`unit_types`, `equipment_types`, `service_types`). Dá para ampliar com catálogos reais (§ Plano alternativo). O grupo não ampliou porque o catálogo oficial é decisão do cliente (DF5 da spec 012), e um catálogo provisório poderia divergir dele.

## Cenários de interpretação da exigência
| Cenário | Leitura | O que exigiria | Avaliação |
|---|---|---|---|
| A. Literal | Toda tabela física do schema | 30 em todas as 20, inclusive `audit_chain_head` e `alembic_version` | **Impossível** sem remover a constraint da cadeia de auditoria; obrigaria a inventar distritos, áreas, papéis e permissões |
| B. Modelo lógico | Toda tabela de `03-modelo-logico.md` | 30 também em referências, domínios fechados e identidade | Os domínios fechados não chegam; `group_role_mappings` exigiria dado fictício de LDAP |
| C. Negócio e referências abertas | Entidades do minimundo, com os catálogos ampliáveis | Ampliar os 3 tipos com catálogos reais | Viável (§ Plano alternativo); depende do cliente (DF5) |
| **D. Negócio, com justificativa** (**aprovado**) | 30 nas tabelas de negócio e de auditoria; as demais justificadas uma a uma | Nada além do que existe | **Já atendido** (`test_seed_demo.py`) |

## Interpretação aprovada (cenário D)
**Tabelas que atendem:**
- as tabelas que representam entidades e fatos do negócio têm 30 tuplas ou mais, com dados coerentes com o domínio: `health_units`, `equipments`, `services`, `users`, `role_assignments`, `role_permissions`, `audit_log` e `db_change_log`;
- a prova automatizada é `tests/integration/tools/test_seed_demo.py::test_seed_carrega_30_ou_mais_por_tabela_e_e_idempotente`.

**Tabelas que não atendem, com justificativa:** as 12 restantes ficam com a quantidade que o domínio ou a construção determina, pelos motivos acima. Cada caso tem evidência no catálogo do PostgreSQL:
- `CHECK (id = 1)`;
- o trigger que protege os papéis de sistema;
- a lista oficial dos distritos sanitários.

**Resumo da justificativa aprovada.** As tabelas abaixo de 30 são de quatro tipos:
1. domínios fechados da realidade: os 8 distritos sanitários do Recife, as 4 áreas técnicas, os 7 papéis e as 17 permissões do controle de acesso;
2. tabelas preenchidas pelo uso ou por integração: sessões, refresh tokens e o mapeamento de grupos do LDAP;
3. infraestrutura: a cabeça da cadeia de auditoria, com `CHECK (id = 1)`, e a versão do Alembic;
4. três catálogos de tipos, cujo conteúdo oficial depende da Secretaria.

Completá-las exigiria inventar distritos ou permissões, ou remover uma constraint de integridade.

## Plano alternativo (cenário C; **não utilizado**, porque o cenário D foi aprovado)
- **O quê:** ampliar `unit_types`, `equipment_types` e `service_types` até 30, com tipos reais de catálogos públicos (tipos de estabelecimento e serviços especializados do CNES), marcados como **dados de demonstração** até o catálogo oficial do cliente (DF5).
- **Onde:** só o seed de demonstração (`seeds/demo/referencias.json`), carregado por `sgs-admin seed demo`. Sem migração e sem mudança de schema.
- **Pré-requisitos (se um dia for retomado):**
  - uma emenda da spec 010 (dono: Vinicius), pela regra 1 do `AGENTS.md`;
  - um teste em `test_seed_demo.py` que exija 30 nesses três catálogos.
- **O que continua fora:** domínios fechados, identidade, infraestrutura e `group_role_mappings`. Os motivos não mudam com a interpretação.
- **Limite:** `sessions` e `refresh_tokens` podem passar de 30 numa demonstração com logins reais, mas isso não é seed e não deve ser apresentado como povoamento.

## Unidades descartadas da `feat/003`
- **Fora do Recife:** "UPA Barra do Ceara" (Fortaleza), "UBS Muribeca" (Jaboatão) e "UBS Nossa Senhora do Ó". A lista está em `seeds/demo/unidades.json` (`descartadas_da_003`).
- **Aparelhos médicos:** os "equipamentos" da 003 (monitor, ventilador, tomógrafo) são aparelhos, não equipamentos de saúde no sentido do domínio (`steering/product.md`), e não foram importados.
- **Distritos no seed:** o mapeamento de bairro para distrito sanitário é aproximado e serve só para demonstração.
