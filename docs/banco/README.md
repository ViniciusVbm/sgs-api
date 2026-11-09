# Banco de dados · documentação da disciplina

| Etapa | Documento |
|---|---|
| 1 · Minimundo | [01-minimundo.md](01-minimundo.md) |
| 1 · Modelo conceitual | [02-modelo-conceitual.md](02-modelo-conceitual.md) |
| 1 · Modelo lógico e esquema relacional | [03-modelo-logico.md](03-modelo-logico.md) |
| 1 · Dicionário de dados | [04-dicionario-dados.md](04-dicionario-dados.md) (gerado do metadata) |
| 2 a 5 · Objetos (constraints, views, funções, procedures, triggers, índices, consultas) | [05-objetos-e-justificativas.md](05-objetos-e-justificativas.md) |
| 2 · 30 tuplas por tabela | [06-trinta-tuplas.md](06-trinta-tuplas.md) |
| 4 · Prova de uso dos índices | [planos-indices.txt](planos-indices.txt) (`EXPLAIN (ANALYZE, BUFFERS)` com 1.000 unidades) |
| 2 · Scripts de criação e inserção | `make sql-bd` gera `build/sql-bd.sql` e `build/sql-bd-insercao.sql` |
| 3 e 6 · Interface | API REST (ver [../api/endpoints.md](../api/endpoints.md)); o front em HTML é integrado à parte |

Toda consulta escrita à mão fica em `src/modules/*/infrastructure/sql/*.sql` e todo objeto de banco em `migrations/sql/<revisão>/*.sql`, um por arquivo, com cabeçalho de objetivo, justificativa, uso e requisito (ADR-0009; `tests/architecture/test_sql_documentado.py`).
