# 009 · Dashboard básico · Design

- Status: Aprovado (Vinicius, 09/11/2026; sem revisão por pares, pela exceção pontual V7 de `steering/sdd-workflow.md`). Histórico: autoria original de rafareloM (03/10/2026); revisão técnica de ViniciusVbm (09/11/2026); implementada antes da aprovação, por decisão do usuário (`docs/RELATORIO_VALIDACAO_FINAL.md` § 9); aprovação registrada na regularização (`docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 7, item V2)

## Implementação
- Módulo `dashboard` só lê; consultas `GROUP BY` com `scope_filter` aplicado (spec 003). Sem tabela própria (Atividade 5 §4).
- Consultas em SQL escrito à mão com `text()` e parâmetros nomeados (ADR-0009).
- Uma consulta por bloco: `units_by_category.sql`, `summary_quality.sql`, `summary_changes.sql` e `recent_changes.sql`, executadas **em sequência** na mesma sessão (`src/modules/dashboard/application/consultas.py`), sem `asyncio.gather`.
- Sem cache nesta versão. Cache em memória de 30 s por (usuário, filtros), invalidado por versão global, fica na T2b e só entra se a T3 mostrar p95 acima de 1 s.
- **Desempenho (R1.7) ainda não comprovado:** a T3 não foi feita. Os planos das consultas de índice (`docs/banco/planos-indices.txt`) são indício, não prova.

## Rota
| Método e rota | Permissão | Requisitos |
|---|---|---|
| `GET /api/v1/dashboard/resumo?distrito=&area=` | `dashboard:read` | R1 |

## Resposta (resumo)
```json
{
  "unidades": {"total": 0, "por_status": {}, "por_tipo": [], "por_area": [], "por_distrito": [], "por_situacao_cadastral": {}},
  "qualidade": {"unidades_com_pendencias": 0, "total_pendencias": 0, "sem_cnes": 0, "servicos_fora_cnes": 0},
  "alteracoes": {"ultimos_7_dias": 0, "ultimos_30_dias": 0, "recentes": []},
  "gerado_em": "2026-10-03T10:00:00-03:00"
}
```
`por_tipo`, `por_area` e `por_distrito` são listas de `{chave, rotulo, quantidade}`. `por_situacao_cadastral` vem da 011/R5.3. `alteracoes.recentes` lista as 10 unidades alteradas mais recentemente (R1.4).

## Estratégia de testes
- Integração: cadastrar N unidades com a spec 006 e conferir cada número (teste de aceitação 6.1); escopo reduz os totais; filtros.
- Desempenho (`slow`): 1.000 unidades, p95 < 1 s.

## Divergências da auditoria de 09/11/2026 e como foram resolvidas
Levantadas em `docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 3.2 e decididas pelo dono em 09/11/2026 (item V2).
- **D009-1:** resolvida. O design descreve a execução em sequência.
- **D009-2:** pendência funcional (T2b, condicionada à T3).
- **D009-3:** pendência funcional (T3). A meta de R1.7 não está comprovada.
- **D009-4:** registrada. As pendências vêm de `health_units.pending_issues`, que hoje só o seed preenche; o número só terá sentido real quando a spec 007 for implementada.
- **D009-5:** resolvida. A § Resposta lista `por_situacao_cadastral`.
