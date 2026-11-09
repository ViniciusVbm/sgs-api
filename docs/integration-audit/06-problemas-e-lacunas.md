# 06 · Problemas e lacunas

**Severidade:**
- **Crítica**: bloqueia entrega ou é falha de segurança.
- **Alta**: requisito acadêmico não atendido ou bug com efeito em dado.
- **Média**: inconsistência que prejudica qualidade ou avaliação.
- **Baixa**: limpeza.

## 1. Bugs e inconsistências de código

| ID | Sev. | Branch | Problema | Evidência | Correção proposta |
|---|---|---|---|---|---|
| P1 | Média | 011 | `Ator.papeis` nunca é preenchido, então `audit_log.actor_roles` e `vw_unit_history.actor_roles` ficam sempre `{}` | `src/modules/access/api/deps.py` (`ator_da_requisicao`) | preencher com os códigos de papel do `ResolvedorDePermissoes`; teste em `test_sessao_de_negocio.py` |
| P2 | Alta (LGPD) | 011 | `manager_name` vai em claro para o `changes` do `audit_log` (`unidade.criada`), mas mascarado (`***`) no `db_change_log` | `registry/application/unidades.py`, `migrations/sql/0011_07/05_fn_trg_registry_change_log.sql` | decidir: mascarar na trilha ou cifrar com `FieldCipher`; registrar na 006 |
| P3 | Média | 011 | a matriz semeada dá `dashboard:read` com escopo máximo G a todos, então o escopo das consultas nunca restringe nada | `migrations/versions/0003_access.py` (`MATRIZ`); pergunta em aberto em `specs/011/requirements.md:139` | decisão do Rafael |
| P4 | Média | 011 | `updated_at` não é mantido em `equipments`, `services` e referências (o SQL bruto ignora o `onupdate` do SQLAlchemy) | `0006/16_equipments.sql`, `0006/17_services.sql` | trigger `BEFORE UPDATE` genérico ou `SET updated_at = now()` nos `.sql` de update |
| P5 | Média | 011 | `sgs_app` herda DELETE nas tabelas de negócio pelos default privileges da 0001, embora unidades e referências só tenham exclusão lógica | `migrations/versions/0001_base.py` | `REVOKE DELETE ON health_units, districts, … FROM sgs_app` numa migração nova |
| P6 | Média | 011 | faltam índices em `equipments.unit_id` (FK RESTRICT, view, conciliação) e `services.equipment_id` (o SET NULL varre `services`) | `migrations/sql/0006/16-17` | dois índices novos, que também reforçam a Etapa 4 |
| P7 | Alta (Etapa 4/6) | 011 | as views não são lidas por nenhuma rota; as consultas do dashboard repetem os JOINs num CTE | `dashboard/infrastructure/sql/*.sql` | 011/T13 e T14 |
| P8 | Baixa | 011 | `tests/e2e/test_tls_banco.py` está marcado `slow` e nunca roda no CI | `.github/workflows/ci.yml` | job dedicado ou rodar em `make test-all` |
| P9 | Baixa | 011 | `.env.example` ainda diz `DATABASE_SSL_MODE=disable` | `.env.example` | documentar `verify-full` |
| P10 | **Crítica** | 011 | não há rota de login: nenhuma rota protegida pode ser usada fora dos testes, e o front não tem como se autenticar | 002/T3 aberta | 002/T3, T6, T8 |
| P11 | Média | 011 | funções antigas de trigger continuam executáveis por PUBLIC (`audit_log_somente_insercao`, `trg_roles_protect_system`) | pergunta em aberto na 011 | `REVOKE EXECUTE … FROM PUBLIC` |
| P12 | Baixa | 011 | o design fala em `FOR ROLE CURRENT_USER` e o código difere; exclusão extra de `name_normalized` no trigger de versão | `specs/011/design.md` contra `0011_05/01` | alinhar o texto do design |
| P13 | **Crítica** | 003V | autenticação por cabeçalho `X-User-Id` sem credencial (personificação) | `access/api/deps.py:20-36` da 003V | não incorporar |
| P14 | Alta | 003V | revisões de migração `0002` e `0003` duplicam as da `main` e da 011 | `migrations/versions/0002_etapa2_tabelas.py`, `0003_etapa3_legado.py` | não incorporar |
| P15 | Média | 003V | `PATCH /equipamentos/{id}` com `{"quantidade": null}` dá 500; `{"nome": null}` vira a string `"None"` | `registry/application/servicos.py:78` | não repetir na 006/T7 (teste de regressão) |
| P16 | Média | 003V | equipamentos não são auditados; `alteracao.idunidade NOT NULL` impede auditar equipamento sem unidade | `1_SQL_Criacao_Tabelas.sql` | não incorporar |
| P17 | Média | 003V | troca em massa de `Status: Rascunho` por `Aprovado` em 28 arquivos de spec, inclusive `_templates` | `git diff main...origin/feat/003-interface-dashboard -- specs` | não incorporar |
| P18 | Baixa | 003V | `get-docker.sh` (816 linhas, instalador do Docker) commitado | raiz da branch | não incorporar |
| P19 | Baixa | 003V | o seed usa um único hash bcrypt para 30 usuários e segredos TOTP de mentira; erro de digitação "Muribecca" | `2_SQL_Insercao_Dados.sql` | corrigir ao reaproveitar |

## 2. Lacunas de requisito (o que falta construir)

| ID | Sev. | Disciplina | Lacuna | Fecha com |
|---|---|---|---|---|
| L1 | **Crítica** (13/11) | BD Etapa 3/6 | CRUD só tem criação de unidade; faltam update e delete de unidades, equipamentos, serviços e referências (são exigidas 4 tabelas) | 006/T4 a T9 |
| L2 | **Crítica** (13/11) | BD Etapa 2 | nenhuma tabela da 011 tem 30 tuplas | seed demo (010) mais decisão D1 |
| L3 | Alta (13/11) | BD Etapa 4 | faltam as 2 consultas com subconsulta | 011/T12 |
| L4 | Alta (13/11) | BD Etapa 4 | falta a prova de uso dos índices (EXPLAIN com volume) | 011/T9 |
| L5 | Alta (13/11) | BD Etapa 3/6 | só 2 consultas expostas; falta o catálogo com justificativa e gráfico sugerido | 011/T19 e reescrita das 4 da 003V |
| L6 | Alta (13/11) | BD Etapa 6 | o efeito da procedure, do trigger e do log do banco não aparece na API | 011/T13 a T18 |
| L7 | Alta (13/11) | BD Etapa 1 | não há minimundo, modelo conceitual nem dicionário de dados | docs novos em `docs/banco/` |
| L8 | Alta (13/11) | BD Etapa 2 | não há script único de criação e inserção | 011/T20 |
| L9 | Alta (13/11) | BD Etapa 6 | não há indicadores estatísticos (`/dashboard/resumo`) | 009 (Rascunho; **precisa da emenda e da aprovação**) |
| L10 | **Crítica** (21/11) | E11 / IAM | não há login | 002/T3, T6, T8 |
| L11 | Alta (21/11) | E11 | não há testes de aceitação nem relatório de resultados | doc 09 |
| L12 | Alta | Seg/Aud | não há consulta da trilha de auditoria nem verificação da cadeia | 008 (Rascunho) |
| L13 | Alta | IAM | não há LDAP, OIDC nem sincronização de usuários e grupos; faltam as tabelas `groups` e `user_groups` | 004 (Rascunho) |
| L14 | Alta | IAM | não há exportação de relatórios para S3 | 005 (Rascunho) |
| L15 | Alta | Seg/Aud | não há nada de fornecedores, matriz de risco, registro de riscos, interrupção de TI, cadeia de fornecedores, ISO 38500 ou COBIT APO10 | doc e/ou módulo `governance` (sem spec) |
| L16 | Média | IAM | não há TOTP nem rate limit | 002/T5, T7 |
| L17 | Média | IAM | não há administração de atribuições, `GET /me` nem teste de arquitetura das rotas | 003/T5 a T7 |
| L18 | Média | — | não há front no repositório | integração posterior do HTML (decisão do usuário) |

## 3. Inconsistências de processo e documentação

| ID | Problema | Evidência |
|---|---|---|
| D-a | As specs 004, 005, 007, 008, 009 e 010 estão em Rascunho. Pela regra 1 do `AGENTS.md`, nada delas pode ser implementado sem aprovação do dono | cabeçalhos `Status:` |
| D-b | A 011 diz que o dashboard estatístico da Etapa 6 "fica na 009, emendada", mas a 009 não tem essa emenda | `specs/011/requirements.md:14` contra `specs/009-dashboard/requirements.md` |
| D-c | Os ADRs 0001 a 0006 e 0009 continuam "Proposto", o que pesa na avaliação de arquitetura | `docs/adr/README.md` |
| D-d | `docs/architecture/modelo-dados.md` é anterior a parte das migrações da 011 (colunas, `db_change_log`, `sgs_owner`) | comparar com `migrations/sql/**` |
| D-e | O MVP previsto para 07/11 (`steering/product.md`) passou sem 004 e 005 | `specs/README.md` |
| D-f | A decisão U4 (domínios fechados com menos de 30 linhas) contraria a exigência de 30 tuplas em **cada** tabela | `specs/011/requirements.md:126` |
| D-g | Sem o `gh` instalado, PRs abertos e issues (por exemplo, a #17 da 011) não foram auditados | ambiente local |

## 4. Riscos de prazo
- **13/11/2026 (BD):** faltam 4 dias. São L1 a L9: cerca de 15 tarefas, das quais a 006/T4 a T9 é a mais pesada. A 009 depende de aprovação.
- **21/11/2026, 09h (E11):** login, aceitação e relatório. Viável se o 13/11 fechar no prazo.
- **Bloqueio humano:** a aprovação das specs em Rascunho é do Rafael, e algumas decisões são do grupo: D1 (30 tuplas), P2 (máscara do nome do gestor) e P3 (escopo do dashboard).
