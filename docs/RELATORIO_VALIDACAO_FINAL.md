# Relatório de validação final · SGS API

- **Data:** 09/11/2026.
- **Branch consolidada:** `feat/consolidacao-final`, levada à `main` local por fast-forward (ver § 1).
- **Testes:** todos executados nesta data, com o resultado em `reports/junit-test-all.xml` (fora do Git).

## 1. Estado inicial e consolidação
| Item | Antes | Depois |
|---|---|---|
| `main` | `a2e2a47`: fundação (001), 002/T1 e T2; só `/health` | `feat/consolidacao-final` (ver o hash final em § 13) |
| Branches | 15 (doc 01 da auditoria): 1 base, 11 já incorporadas, 3 com commits fora da `main` | Nenhuma apagada; todas preservadas no remoto, nas tags locais `arquivo/*` e no bundle `~/sgs-api-backup-20261109.bundle` |

**Sequência:**
1. Fast-forward da `main` para `feat/011-integracao` (`556599f`, 63 commits, histórico preservado).
2. Inclusão dos documentos da auditoria (`3a8ed1a`, reaplicado como `aa44569`).
3. Branch de trabalho `feat/consolidacao-final`, com 13 commits.
4. Fast-forward da `main` para ela.

**`feat/003-interface-dashboard`:** não foi mesclada. Dela vieram só conteúdos, reescritos para o esquema da 011:
- nomes, endereços, CEPs e telefones das unidades;
- as 4 consultas da Etapa 03;
- o formato de `/dashboard/resumo`;
- o contrato das rotas de equipamento.

**Descartados da 003, com o motivo** (doc 04 da auditoria):
- a autenticação por `X-User-Id`;
- as migrações 0002 e 0003 (revisões em conflito);
- a tabela `ALTERACAO`;
- a troca de status das specs;
- `get-docker.sh`.

**`feat/002-fundacao-vinicius`:** já estava contemplada. O commit `9245d4f` tem o mesmo patch-id do `7fd3f05`, que está na `main`.

## 2. Commits da consolidação (sobre `aa44569`)
| Commit | Conteúdo |
|---|---|
| `dbe38a1` | Revisão técnica das specs 008, 009 e 010 (continuam em Rascunho) e emendas propostas da 011 (T21, T22) |
| `5bb25b3` | Migração `0011_09`: índices, CHECKs, `updated_at`, REVOKE, escopo do dashboard por papel |
| `06f321e` | CRUD de unidades, equipamentos, serviços e referências; máscara LGPD; `actor_roles` |
| `6173b45` | Dashboard (011/T12, T13, T19; 009) e consultas de auditoria (011/T14, T15; 008) |
| `2c29b5a` | Identidade (002/T3, T5 a T8) e acesso (003/T5 a T7) |
| `9602498` | Seed de demonstração (010) e prova dos índices (011/T9) |
| `1c6c18b` | `make sql-bd` (011/T20) |
| `d9012f6` | Roteiro de aceitação; tarefas marcadas `[x]` com o teste que prova cada uma |
| `03e3b55` | Correção das permissões do arquivo de chaves (achada no e2e) |
| `5c713ba` | Documentação: banco, governança, API, instalação, front, README |
| `549b6c2` | Ajuste do bandit no gerador de SQL |
| `73ebb7a` | Relatórios finais e checkpoint |
| `fdb0263` | `reports/` no `.gitignore` |
| *(depois)* | Correções da auditoria de publicação (`docs/RELATORIO_PR_PUBLICACAO.md`) |

Ao todo, até `fdb0263`, 197 arquivos foram alterados em relação a `aa44569`: 135 criados e 62 modificados. Nenhum arquivo do código anterior foi removido.

## 3. Banco de dados
**Migração nova:** `migrations/versions/0011_09_ajustes_base.py`, com 17 arquivos em `migrations/sql/0011_09/`. Nenhuma migração já aplicada foi editada.
- Índices `ix_equipments_unit_id` e `ix_services_equipment_id`.
- CHECKs `ck_equipments_status_valido`, `ck_equipments_quantity_positiva` e `ck_services_status_valido`.
- Função `fn_trg_set_updated_at` e trigger `trg_set_updated_at` em 7 tabelas.
- `REVOKE DELETE` da API em `health_units` e nas referências (exclusão só lógica).
- `REVOKE EXECUTE … FROM PUBLIC` em `audit_log_somente_insercao` e `trg_roles_protect_system`.
- `dashboard:read` com escopo máximo `area`, `distrito` ou `unidade` para COORD_TECNICO, TECNICO_DISTRITAL e GESTOR_UNIDADE (D3).

**Objetos da disciplina:** todos existem e foram testados. O detalhe está em `docs/banco/05-objetos-e-justificativas.md`.
- 2 views.
- 2 funções (uma condicional).
- 2 procedures (uma atualiza dados, outra usa CURSOR).
- Triggers de versão, de log e de `updated_at`.
- Índices provados por EXPLAIN.
- ON UPDATE CASCADE e ON DELETE SET NULL.
- 70 arquivos `.sql` de migração e 48 consultas escritas à mão, todos com cabeçalho (`tests/architecture/test_sql_documentado.py`).

**Prova dos índices** (`docs/banco/planos-indices.txt`, `tests/integration/db/test_indices.py`), com 1.000 unidades, 3.000 serviços e 3.000 eventos:
- o histórico de uma unidade usa *Index Scan using ix_audit_log_entity*;
- os serviços de uma unidade usam *Bitmap Index Scan on ix_services_unit_id*.

**SQL consolidado:** `make sql-bd` gera `build/sql-bd.sql`, testado num banco vazio: cria tudo e chega a `alembic_version = 0011_09`. Também gera `build/sql-bd-insercao.sql`.

**Seeds** (`seeds/demo/*.json`, `sgs-admin seed demo`): idempotente, recusado em prod, passa pelos casos de uso e gera auditoria.

| Tabela | Linhas |
|---|---|
| `health_units` | 37 |
| `equipments` | 31 |
| `services` | 35 |
| `users` | 30 |
| `role_assignments` | 30 |
| `audit_log` | 138 |
| `db_change_log` | 103 |

Os domínios fechados ficam com a quantidade real (D1; `docs/banco/06-trinta-tuplas.md`).

## 4. Endpoints
São 55 operações, listadas com a permissão de cada uma em `docs/api/endpoints.md` (gerado das rotas). O contrato está em `contracts/openapi.yaml`.

| Grupo | Rotas |
|---|---|
| Autenticação (002) | `/auth/login`, `/auth/mfa/enroll`, `/auth/mfa/confirm`, `/auth/mfa/verify`, `/auth/refresh`, `/auth/logout` |
| Acesso (003) | `/me`, `/admin/papeis`, `/admin/atribuicoes` (GET, POST, DELETE) |
| Cadastro (006) | `/unidades` (lista, criação, detalhe, PATCH com If-Match, desativar); equipamentos e serviços da unidade e soltos (CRUD); `/referencias/{tipo}` (GET, POST, PATCH) |
| Dashboard (011, 009) | 8 consultas do catálogo, `/dashboard/consultas` (catálogo), `/dashboard/inventario`, `/dashboard/resumo` |
| Auditoria (008, 011) | `/unidades/{id}/historico`, `/auditoria/eventos`, `/auditoria/eventos/{id}`, `/auditoria/verificar`, `/auditoria/banco`, `/auditoria/banco/particoes` |

## 5. Segurança e autenticação
- **Argon2id** com hash fictício para usuário inexistente; mesma mensagem e tempo semelhante.
- **Bloqueio** por 15 min depois de 5 falhas; limite de 10 logins por minuto por IP.
- **TOTP obrigatório:** segredo cifrado com AES-256-GCM e chaves versionadas (`CRYPTO_KEYS`); janela de ±30 s; anti-reuso; 5 tentativas por desafio.
- **Tokens:** access token ES256 de 15 min (JWKS com `kid`); refresh opaco em cookie `HttpOnly; Secure; SameSite=Strict`, rotativo, com revogação da sessão no reuso; anti-CSRF por `X-Requested-With` e `Origin`.
- **RBAC:** deny by default, com teste de arquitetura sobre 55 operações. Escopo por papel nas listagens e no dashboard. Campos estruturais só com escopo amplo. Segregação de funções nas atribuições.
- **Auditoria:** na mesma transação do dado; `actor_roles` preenchido; nome do gestor mascarado. Trilha imutável e verificável (`/auditoria/verificar` acusa o evento adulterado).
- **Banco:** TLS `verify-full` entre API e banco; privilégio mínimo (sem DELETE onde a exclusão é lógica).
- **Segredos:** fora do Git (`git ls-files` sem `.env`, `secrets/` nem chaves). Prod recusa chaves de exemplo.
- **Análise estática:** `bandit -r src` com 0 achados; `pip-audit` sem vulnerabilidades conhecidas (09/11/2026).

## 6. Documentação criada
- `docs/banco/` (7 documentos e os planos).
- `docs/governanca/` (6).
- `docs/api/endpoints.md` e `autenticacao.md`.
- `docs/instalacao.md`, `docs/frontend-integracao.md`.
- README atualizado.
- Emenda do ADR-0007.
- Revisões das specs 008, 009 e 010 e emendas da 011.
- Este relatório, `docs/REQUISITOS_EVIDENCIAS.md` e `docs/RESUMO_STATUS_PROJETO.md`.

## 7. Testes executados (09/11/2026)
| Execução | Resultado |
|---|---|
| `make check`: ruff, ruff format, mypy (strict), import-linter (6 contratos), `pytest -m "not slow"` | **878 aprovados**, 3 pulados (consultas que só leem referências, pulo justificado no teste), 0 falhas |
| `make test-all` (`pytest` completo, com os `slow`) | **885 aprovados**, 3 pulados, 0 falhas, 0 erros (103 s) |
| Entre os `slow` | e2e do compose num projeto isolado (`sgs-api-e2e-tls`): TLS `verify-full`, `pg_hba` sem TLS recusado, certificados, nenhuma chave no Git, `seed demo` e `create-user` dentro do container; prova dos índices com volume |
| Roteiro de aceitação (`tests/integration/acceptance/test_roteiro_mvp.py`) | aprovado: seed, criação do admin, login com TOTP de 3 papéis, `/me`, busca, PATCH, histórico, SET NULL, desativação, catálogo, resumo, escopo distrital, 403 auditado, verificação da cadeia, refresh e logout |
| `bandit -r src` / `pip-audit` | 0 achados / sem vulnerabilidades conhecidas |

**Validações pedidas:**

| # | Validação | Evidência |
|---|---|---|
| 1 | PostgreSQL vazio | `test_sql_bd.py` (banco vazio); testcontainers por teste |
| 2 | Migrações completas | `test_migracoes_sincronizadas.py` |
| 3 | Docker | e2e |
| 4 | Health checks | `test_health.py`; healthcheck do compose no e2e |
| 5 | Primeiro administrador | `test_sgs_admin_create_user.py`; e2e no container |
| 6 | Login e renovação de sessão | `test_login.py`, `test_mfa.py`, `test_refresh.py` |
| 7 | CRUD | `test_crud_unidades.py`, `test_crud_vinculos.py` |
| 8 | RBAC | `test_require.py`, `test_rotas_protegidas.py`, `test_admin_atribuicoes.py`, `test_painel.py` |
| 9 | Integridade da auditoria | `test_audit_chain.py`, `test_consulta_trilha.py` |
| 10 | Seeds | `test_seed_demo.py` |
| 11 | Consultas | `test_consultas_qualidade.py`, `test_painel.py` |
| 12 | Dashboard | `test_painel.py` |
| 13 | Reprodutibilidade | banco novo por teste; seed idempotente; `make sql-bd` num banco vazio |

## 8. Problemas encontrados e corrigidos
| Problema | Correção |
|---|---|
| Comentário `:scope_*` no cabeçalho de um `.sql` virava parâmetro do SQLAlchemy | Cabeçalhos revistos, mais um teste de arquitetura que barra o padrão |
| Coluna ambígua na busca (`cnes` na CTE) | CTE com nomes próprios |
| O teste de rotas protegidas passava sem ver rota nenhuma (o FastAPI 0.142 guarda roteadores incluídos) | Coletor que desce pelos roteadores, mais uma asserção de que viu mais de 40 rotas |
| Cookie `Secure` não enviado pelo cliente de teste (`http://`) e domínio `teste.local` do cookiejar | `base_url` https e domínio correto; o teste de reuso volta a provar a revogação |
| Arquivo de chaves com `0600` ilegível pelo usuário do container (a API não subia) | Mesma política do arquivo JWT |
| Imagem sem `seeds/` (`seed demo` falharia no container) | `COPY seeds` no Dockerfile, mais um teste e2e |
| Achados da auditoria: `actor_roles` vazio (P1), nome do gestor em claro (P2), `updated_at` parado (P4), DELETE da API (P5), índices faltando (P6), views sem uso (P7), `.env.example` (P9), sem login (P10), EXECUTE PUBLIC (P11) | Todos corrigidos, com teste (§ 3 a 5) |

## 9. Desvios e decisões registradas
1. **Regra 1 do `AGENTS.md`:** as specs 008, 009 e 010, as emendas da 011 (T21, T22) e a emenda do ADR-0007 foram implementadas **antes da aprovação do dono** (Rafael), por decisão explícita do usuário. Elas continuam marcadas como "Rascunho", aguardando aprovação.
2. **D1 a D6:** adotadas como o usuário definiu.
   - D1: 30 tuplas onde cabe; domínios fechados reais.
   - D2: nome do gestor mascarado.
   - D3: dashboard no escopo do papel.
   - D4: specs revistas.
   - D5: governança só documental.
   - D6: ajustes formalizados como T21 e T22.
3. **Rate limit:** `limits` no lugar do `slowapi` (emenda do ADR-0007); limite em memória, por processo.
4. **Contrato do import-linter:** `src.tools` (o `sgs-admin`) foi incluído como segunda raiz de composição.
5. **T9:** o EXPLAIN ficou em `docs/banco/planos-indices.txt`, e não no cabeçalho dos `.sql` dos índices, que são de migrações já aplicadas.
6. **Dados da 003:**
   - 3 unidades fora do Recife foram descartadas;
   - os "equipamentos" (aparelhos médicos) não foram importados, porque no domínio "equipamento" é um estabelecimento de saúde;
   - o mapeamento de bairro para distrito sanitário é aproximado e serve só para demonstração.
7. **Login:** os campos `mfa_token` vão no corpo das rotas de 2FA, já que o design não fixava o meio.
8. **Leitura das referências:** exige `unidade:read`, porque o design dizia só "autenticado" e a regra 4 exige uma permissão declarada.

## 10. Limitações
- **CI:** o GitHub Actions continua bloqueado. O equivalente foi rodado localmente (`make check`, `make test-all`, `bandit`, `pip-audit`).
- **Proxy:** o compose completo com o Caddy não subiu nesta sessão. As portas 80/443 estavam ocupadas pelo ambiente que já rodava (a cópia em `~/Área de trabalho/sgs-api-feat-011-integracao`), que não foi tocado. O e2e valida banco, certificados, API e comandos num projeto isolado, sem o proxy.
- **Rate limit:** em memória. Com mais de um processo da API, cada um tem a própria contagem.
- **Front:** o protótipo HTML não foi integrado (decisão do usuário); o mapeamento das telas para os endpoints está em `docs/frontend-integracao.md`.

## 11. Pendências reais
| Pendência | Situação |
|---|---|
| Spec 004 (LDAP, OIDC, sincronização de usuários e grupos) | Não implementada; spec em Rascunho |
| Spec 005 (exportação para S3) | Não implementada; spec em Rascunho |
| Spec 007 (regras de validação e pendências) | Não implementada; `pending_issues` só vem do seed |
| 003/T8 (mapeamento grupo → papel) | Depende da 004 |
| 006/T10 (desempenho da busca) | Não feita |
| 009/T2 (cache) e T3 (desempenho do resumo) | Não feitas |
| 010/T3 (conversor da planilha) | Não feita: a planilha não está disponível |
| Aprovação das specs 008, 009, 010 e das emendas | Do Rafael |
| Confirmação de D1 | Do professor de BD |
| Integração do front | Pendente |
| Backup e continuidade operacional | Processo fora do repositório |

## 12. Como executar
Ver `docs/instalacao.md`. Em resumo:
```bash
uv sync --frozen
mkdir -p secrets
uv run python -m src.tools.jwt_keys --output secrets/jwt-keys.json
uv run python -m src.tools.crypto_keys --output secrets/crypto-keys.json
docker compose -f docker/compose.yml up -d --build --wait
docker compose -f docker/compose.yml exec api sgs-admin seed demo
make check && make test-all
```

## 13. Estado final do Git
Está no fim do `docs/CHECKPOINT_CONSOLIDACAO.md`:
- a `main` local aponta para o último commit da consolidação;
- as 15 branches remotas continuam intactas;
- nenhum push foi feito.

## 14. Publicação no repositório novo (quando autorizada)
Depois de criar o repositório vazio no GitHub, sem README nem licença, substitua `<URL>`:
```bash
cd sgs-api                                # a pasta do clone local
git switch main
git status --short                        # deve estar vazio
git remote add novo <URL>                 # o remote atual (origin) fica como está
git push -u novo main                     # só a main: uma única branch principal
# Não envie as tags arquivo/003-* e arquivo/002-*: elas trazem o histórico descartado da
# feat/003 (ver docs/RELATORIO_PR_PUBLICACAO.md). As outras duas apontam para commits da main.
```
Os secrets (`secrets/`, `.env`) não vão, porque estão no `.gitignore`. Antes, confira: `git ls-files | grep -E 'secrets/|\.env$'` não deve listar nada.
