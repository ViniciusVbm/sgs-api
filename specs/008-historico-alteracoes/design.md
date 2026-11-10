# 008 · Histórico de alterações · Design

- Status: Aprovado (Vinicius, 09/11/2026; sem revisão por pares, pela exceção pontual V7 de `steering/sdd-workflow.md`). Histórico: autoria original de rafareloM (03/10/2026); revisão técnica de ViniciusVbm (09/11/2026); implementada antes da aprovação, por decisão do usuário (`docs/RELATORIO_VALIDACAO_FINAL.md` § 9); aprovação registrada na regularização (`docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 7, item V1)

## Consulta
- `audit/application/consultar.py` monta a query sobre `audit_log`. O histórico da unidade usa o índice `(entity_type, entity_id, occurred_at DESC)` (`ix_audit_log_entity`, spec 011, R1.1). A trilha geral não tem índice próprio: filtra a ação por prefixo (`LIKE`), ordena por `id` e conta o total; com o volume esperado (~250 unidades, 2 anos) isso basta (`docs/banco/planos-indices.txt`).
- O histórico da unidade lê a view de histórico da spec 011 (R4.4, R4.5).
- Rótulos legíveis: dicionário `ROTULOS_CAMPOS` em `src/modules/audit/domain/consultas.py` (ex.: `district_id` → "Distrito sanitário"). Os valores `de` e `para` saem como foram gravados; ids de referência não são traduzidos para nomes.
- Escopo: o histórico de uma unidade usa o mesmo `require("auditoria:read", Unidade(id))` da spec 003.
- Fuso: armazenado em UTC; serializado em `America/Recife`.

## Verificação da cadeia
Recalcula em lotes de 1.000 eventos em ordem de `id`, comparando `hash` com `sha256(prev_hash + canon(evento))`. Retorna o primeiro `id` divergente. Operação só leitura.

## Retenção (R4.1)
O `audit_log` **não** é particionado (decisão do Rafael, 06/11/2026). Particionar obrigaria `UNIQUE(hash)` e `UNIQUE(prev_hash)` da 0001 a incluir `occurred_at`, e a proteção contra bifurcação da cadeia se perderia. O volume (~250 unidades, 2 anos) não justifica. A retenção mínima vem da imutabilidade: os triggers e grants da 0001 impedem apagar eventos.

## Rotas
| Método e rota | Permissão | Requisitos |
|---|---|---|
| `GET /api/v1/unidades/{id}/historico` | `auditoria:read` (escopo da unidade) | R1 |
| `GET /api/v1/auditoria/eventos` · `/{id}` | `auditoria:read` global; `auth.*` exige `auditoria:read_acessos` | R2, R3.2 |
| `POST /api/v1/auditoria/verificar` | `auditoria:read` global | R3.1 |

## Estratégia de testes
- Integração: alteração via spec 006 aparece no histórico com autor, papel, data e campos (teste de aceitação 6.1); filtros; 403 fora do escopo; eventos `auth.*` ocultos sem permissão.
- Integridade: adulterar um registro com superusuário no teste (desabilitando o trigger) e verificar que a cadeia acusa o ponto exato.

## Divergências da auditoria de 09/11/2026 e como foram resolvidas
Levantadas em `docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 3.1 e decididas pelo dono em 09/11/2026 (item V1).
- **D008-1:** resolvida. O índice `(action, occurred_at DESC)` saiu do design (§ Consulta).
- **D008-2:** resolvida. A tradução de ids para nomes saiu do design; o campo continua com rótulo (R1.2).
- **D008-3:** resolvida. O design cita o local real de `ROTULOS_CAMPOS`.
- **D008-5:** pendência funcional. Os filtros de período e de autor existem nas rotas, mas não têm teste; vira a tarefa T6.
