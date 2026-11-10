# 007 · Validação de dados · Tarefas

- Status: Rascunho
- Depende de: 006

## O que já existe no código (revisão de 09/11/2026, agente; aguarda o dono)
Parte da validação foi adiantada pela spec 006. As tarefas abaixo partem daqui:
- T1: CNES com 7 dígitos e CEP com 8 dígitos (com ou sem hífen) já validados em `registry/api/schemas.py`; coordenadas só nos limites globais (±90, ±180); telefone só com caracteres permitidos; espaços das pontas já removidos. Faltam: faixa de CEP de Recife, telefone com 10 ou 11 dígitos, coordenadas no município, horário e espaços repetidos nos nomes.
- T2: referências existentes e ativas já conferidas (tipo e distrito em `registry/application/unidades.py`; tipos de serviço e equipamento em `vinculos.py`). Faltam: CAPS × `FARMACIA_FAMILIA` (os dois tipos já existem no seed `0006/22`) e serviço em unidade inativa.
- T3: `DomainValidationError` com lista de `FieldError` já gera 422. Falta juntar formato, coerência e regras configuráveis numa resposta só, com `regra` em cada erro (R1.2).
- T6: a coluna `health_units.pending_issues` já existe e é lida pela listagem e pelo dashboard (009/R1.2), mas hoje só o seed a preenche.

- [ ] T1. Normalizadores e validadores de formato (CNES, CEP, telefone, coordenadas, horário) nos schemas
  - Requisitos: R1.3, R1.6
  - Pronto quando: `tests/unit/registry/test_formatos.py` passa
- [ ] T2. Validador de domínio com regras de coerência e catálogo de mensagens
  - Requisitos: R1.4, R1.5
  - Pronto quando: `tests/unit/registry/test_regras_coerencia.py` passa
- [ ] T3. Integração do validador nos casos de uso de gravação (422 sem gravar)
  - Requisitos: R1.1, R1.2
  - Pronto quando: `tests/integration/registry/test_dado_invalido_nao_grava.py` passa
- [ ] T4. Migração e CRUD de regras configuráveis com auditoria
  - Requisitos: R2.1–R2.4
  - Pronto quando: `tests/integration/registry/test_regras_configuraveis.py` passa
- [ ] T5. Simulação de validação
  - Requisitos: R2.5
  - Pronto quando: `tests/integration/registry/test_simular_validacao.py` passa
- [ ] T6. Pendências por alerta e revalidação da base
  - Requisitos: R3.1–R3.3
  - Pronto quando: `tests/integration/registry/test_pendencias.py` passa
