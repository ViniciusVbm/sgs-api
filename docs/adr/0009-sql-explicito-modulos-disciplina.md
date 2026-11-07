# ADR-0009: SQL explícito nos módulos cobrados pela disciplina de Banco de Dados

- Status: Proposto
- Data: 2026-11-06
- Requisitos relacionados: specs 006 e 009; spec de banco de dados (a criar); requisitos da disciplina de Banco de Dados (Etapa 03, Segunda Parte e Etapa 06)

## Contexto
- A disciplina de Banco de Dados exige que o backend use "comandos SQL explícitos (por exemplo, com o JDBC)". A Segunda Parte, com entrega em 13/11/2026, cobra também consultas com anti join, full outer join e subconsultas, além de views, funções, procedimentos e triggers acessíveis pela interface.
- Os repositórios da 001 montam o SQL com as expressões do SQLAlchemy Core (`insert(tabela).values(...)`). Isso não é SQL escrito à mão, e a disciplina pode não aceitar.
- O PR #4 já usava `text()` com SQL escrito à mão. O porte dele para as specs está na issue #11.
- A auditoria precisa ser gravada na mesma transação do caso de uso (`AGENTS.md`, regra 5). Por isso, o SQL explícito tem de rodar na mesma `AsyncSession` que o `audit.registrar` usa.

## Decisão
Nos módulos `registry` e `dashboard` e nos módulos da spec de banco de dados, os repositórios escrevem o SQL à mão com `sqlalchemy.text()` e parâmetros nomeados (`:nome`). Valores nunca são interpolados na string. Os demais módulos (`audit`, `identity`, `access` e os seguintes) continuam com SQLAlchemy Core.

## Consequências
- Atende à exigência da disciplina, e o SQL fica legível para a apresentação.
- Continua havendo um só driver, uma só engine e uma só transação por requisição. A auditoria segue na mesma transação.
- As tabelas continuam declaradas em `infrastructure/tables.py`, para o Alembic e para o teste `test_migracoes_sincronizadas`. O SQL que roda está em `text()`.
- O Python deixa de conferir nomes de tabela e coluna, e um erro de digitação só aparece na execução. Cada consulta precisa de teste de integração contra PostgreSQL (testcontainers).
- Filtros e ordenação dinâmicos montam a string só a partir de listas fixas de colunas permitidas. Valor vindo do usuário entra sempre como parâmetro.
- O DDL de views, funções, procedimentos e triggers fica nas migrações (`op.execute`), para continuar havendo uma fonte só de DDL.
- O repositório passa a ter duas formas de acesso ao banco. A `steering/tech.md` registra qual vale em cada módulo.

### Complemento da spec 011 (proposto em 07/11/2026)
- O escopo inclui também as consultas de dados dos relatórios (`reports`), porque a disciplina pede "SQL das consultas necessárias para gerar os relatórios".
- DDL em `migrations/sql/<revisão>/NN_<nome>.sql`, uma instrução por arquivo (o asyncpg prepara toda instrução), executado por um carregador que escapa `:`. Arquivo de revisão aplicada não é editado. Consultas em `src/modules/<módulo>/infrastructure/sql/*.sql`, carregadas em `text()`. Todo arquivo abre com cabeçalho de objetivo, justificativa e uso.
- Views da spec 011 podem juntar tabelas de módulos diferentes (por exemplo, `audit_log` com `health_units` e `users`). Vale só para leitura, e a view é dona da junção: nenhum módulo importa `infrastructure` de outro.
- O escopo de leitura entra no SQL explícito como parâmetros (`EscopoLeitura` da spec 003) num fragmento fixo, nunca montado com valores do usuário.

## Alternativas consideradas
- SQL explícito em todo o projeto: obriga a reescrever o que a 001 já entregou (auditoria) sem ganho para a disciplina.
- Manter só o SQLAlchemy Core: arrisca a nota da disciplina, e views, funções e procedimentos exigiriam SQL escrito à mão de qualquer jeito.
- asyncpg direto, sem SQLAlchemy: perde a sessão compartilhada com o `audit.registrar` e duplica o controle de transação.
