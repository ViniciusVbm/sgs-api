# Checkpoint da consolidação final

Arquivo de retomada: se a sessão for interrompida, continue daqui sem refazer o que já tem commit.

## Estado do Git
- `main` local = `aa44569` (fast-forward para a `feat/011-integracao` + documentos da auditoria). Sem push.
- Branch de trabalho: `feat/consolidacao-final` (a partir da `main`). Ao terminar, fast-forward da `main` para ela.
- Preservação: tags locais `arquivo/*`, bundle `~/sgs-api-backup-20261109.bundle`.

## Feito (com commit)
| Commit | Conteúdo |
|---|---|
| `dbe38a1` | Revisão técnica das specs 008, 009, 010 (continuam Rascunho, aguardam o Rafael) e emendas propostas da 011 (T21, T22) |
| `5bb25b3` | Migração 0011_09: índices, CHECKs, `updated_at`, REVOKE, escopo do dashboard por papel |
| `06f321e` | CRUD de unidades, equipamentos, serviços e referências; máscara LGPD; `actor_roles` |

## Pendente (na ordem)
1. Dashboard: 011/T12 (subconsultas), T13 (inventário), T14 (histórico pela view, rota da 008/T2), T15 (log do banco), 009 R1 (resumo) e R2 (4 consultas da 003), T19 (catálogo).
2. 008: trilha geral, evento individual, verificação da cadeia.
3. Identidade (002/T3, T5 a T8): login, TOTP, refresh, logout, rate limit, auditoria, `sgs-admin create-user`.
4. 003/T5 a T7: teste de rotas protegidas, `GET /me`, administração de atribuições.
5. 010: seed demo; 011/T9 (prova dos índices); 011/T20 (`make sql-bd`).
6. Documentação (banco, governança, README), aceitação, relatórios finais.

## Últimos testes
- `make check` em `06f321e`: 686 aprovados, 5 `slow` desmarcados.
