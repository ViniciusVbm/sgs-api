# 008 · Histórico de alterações · Design

- Status: Rascunho (revisão técnica de 09/11/2026 por ViniciusVbm na consolidação final; **aguarda aprovação do Rafael**. Implementada antes da aprovação por decisão do usuário; ver `docs/RELATORIO_VALIDACAO_FINAL.md` § Desvios)

## Consulta
- `audit/application/consultar.py` monta a query sobre `audit_log` com índices `(entity_type, entity_id, occurred_at DESC)` (criado pela spec 011, R1.1) e `(action, occurred_at DESC)` (criado aqui).
- O histórico da unidade lê a view de histórico da spec 011 (R4.4, R4.5).
- Rótulos legíveis: dicionário `ROTULOS_CAMPOS` no módulo `registry` (ex.: `district_id` → "Distrito sanitário"), e os ids de referência são traduzidos para nomes na resposta.
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
