# 10 · Arquitetura final proposta

**Base:** a arquitetura da `feat/011-integracao` (doc 05), que já segue `steering/structure.md` e os contratos do import-linter. A proposta mantém o estilo e acrescenta só os módulos que os requisitos exigem.

## Princípios mantidos
1. Monólito modular, com camadas api > application > domain. O domain é puro (import-linter).
2. SQL explícito em `.sql` por módulo (ADR-0009). Cada objeto de banco é um `.sql` em `migrations/sql/<revisão>/`.
3. Toda rota declara `require("recurso:acao")` ou está na lista pública. Nega por padrão.
4. Toda alteração de negócio grava no `audit_log` encadeado na mesma transação. O `db_change_log` por trigger cobre alterações fora da API.
5. Privilégio mínimo no banco (`sgs_owner`, `sgs_app`, `sgs_api`), TLS `verify-full` e segredos fora do git.
6. Nomes do banco em inglês (`health_units`), rotas e mensagens em português (`/unidades`).

## Módulos
```
src/modules/
├── audit/        (existe)  + api: GET /auditoria, /auditoria/verificacao            [008]
├── identity/     (existe)  + login, refresh, logout, TOTP, rate limit                [002]
├── access/       (existe)  + GET /me, admin de atribuições, grupo→papel              [003]
├── registry/     (existe)  + CRUD unidades/equipamentos/serviços/referências          [006, 011]
├── dashboard/    (existe)  + catálogo, subconsultas, inventário, resumo               [011, 009]
├── directory/    (novo)    LDAP (ldap3) + OIDC (Authlib), sync de usuários/grupos     [004]
├── reports/      (novo)    export CSV/XLSX → S3 (boto3, STS, SSE, URL pré-assinada)   [005]
└── governance/   (opcional) suppliers, risks, risk_assessments, CRUD                  [sem spec; D5]
src/tools/sgs_admin.py:  banco particoes (existe) | seed demo (010) | create-user (002/T8) | diretorio sincronizar (004)
Makefile:                make sql-bd (011/T20)
```

## Dados
**Tabelas já existentes:** as do doc 05.

**A acrescentar:**
- `groups`, `user_groups`, `directory_sync_runs` (004);
- `report_jobs` (005);
- opcional: `suppliers` (com classificação por criticidade e tipo de dado tratado), `risks` (probabilidade 1 a 5, impacto 1 a 5, nível calculado por uma função condicional), `risk_controls`.

**Ajustes na 0011_09:**
- índices `ix_equipments_unit_id` e `ix_services_equipment_id`;
- trigger de `updated_at`;
- `REVOKE DELETE` nas tabelas de exclusão lógica;
- `REVOKE EXECUTE FROM PUBLIC`.

**Seed:** `sgs-admin seed demo` com 30 linhas ou mais por tabela de negócio (decisão D1 para os domínios fechados).

**Entregável da disciplina:**
- `build/sql-bd.sql` (DDL e consultas), gerado por `make sql-bd` (011/T20; o arquivo fica no `.gitignore` e é anexado à entrega);
- `docs/banco/01` a `05` (minimundo, conceitual, lógico, dicionário, justificativas).

## Superfície da API para o front em HTML
| Grupo | Rotas |
|---|---|
| Auth | `POST /api/v1/auth/login`, `/refresh`, `/logout`; `GET /api/v1/me` |
| Cadastro | `GET`/`POST /unidades`, `GET`/`PATCH /unidades/{id}` (If-Match), `POST /unidades/{id}/desativar`, `GET /unidades/{id}/historico`, `/unidades/{id}/equipamentos`, `/equipamentos/{id}`, `/servicos`, `/referencias/{tipo}` |
| Dashboard | `GET /dashboard/consultas` (catálogo), `GET /dashboard/consultas/{nome}?distrito=&tipo=&pagina=`, `GET /dashboard/inventario`, `GET /dashboard/resumo` |
| Auditoria | `GET /auditoria`, `GET /auditoria/verificacao` (008); `GET /auditoria/banco`, `GET /auditoria/banco/particoes` (011/T15) |
| Admin | atribuições, `POST /admin/diretorio/sincronizar` (004); criar partições é feito pelo comando `sgs-admin banco particoes`, não por rota |
| Relatórios | `POST /relatorios`, `GET /relatorios/{id}` (URL pré-assinada) |

O catálogo devolve, para cada consulta: título, justificativa, parâmetros, colunas, permissão e **tipo de gráfico sugerido**. O front monta filtros e gráficos sem conhecer o SQL. A API não gera gráficos (009).

**Integração do front (etapa futura):**
- servir o HTML pelo Caddy, no mesmo domínio, evitando CORS e mantendo o cookie de refresh `SameSite=Strict`;
- ou liberar a origem em `CORS_ORIGINS`.
- O contrato vale por `contracts/openapi.yaml`.

## Implantação
```
caddy (HTTPS, estático do front + /api → api)
api (FastAPI)  ──TLS verify-full──►  db (postgres:17)
     ├──► ldap (slapd de teste)   [004]
     ├──► keycloak (OIDC)          [004]
     └──► seaweedfs/minio (S3)     [005]
```

## Governança e conformidade (documental)
Ficam em `docs/governanca/`:
- registro de fornecedores e riscos;
- matriz 5×5;
- mapeamento para ISO 38500 e COBIT 2019 APO10, com evidência técnica (arquivo e teste);
- LGPD técnica.

O documento **não declara** conformidade nem certificação.

## Decisões que viram ADR
- **ADR-0010:** consolidação sobre a 011 e descarte do esquema da Etapa 2/3 de Vinicius (resumo do doc 04).
- **ADR-0011:** exceção das 30 tuplas nos domínios fechados, se for o caso (D1).
- **ADR-0012:** governança documental ou em módulo (D5).
