# 009 · Dashboard básico · Requisitos

- Status: Aprovado (Vinicius, 09/11/2026). Histórico: autoria original de rafareloM (03/10/2026); revisão técnica de ViniciusVbm (09/11/2026); implementada antes da aprovação, por decisão do usuário (`docs/RELATORIO_VALIDACAO_FINAL.md` § 9); aprovação registrada na regularização (`docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 7, item V2)
- Rastreia: RF-06; critério 6.1 "dashboard exibe indicadores que refletem os dados realmente cadastrados"
- Dono humano: Vinicius (ViniciusVbm), desde 09/11/2026; antes: nenhum registrado (autoria original: rafareloM, 03/10/2026). Atribuição pelo responsável pelo projeto (`steering/sdd-workflow.md` § Dono da spec)

## Contexto
O cliente já tem dashboards e disse que este serve para conferir os dados inseridos (reunião de 18/09). Por isso o escopo é mínimo: agregados corretos e rápidos, sem gráficos no backend.

## Fora do escopo
- Séries históricas, metas, exportação do dashboard, mapa GIS.

## Histórias e critérios

### R1. Resumo da rede
- R1.1 QUANDO um usuário com `dashboard:read` chama `GET /dashboard/resumo`, o sistema DEVE responder total de unidades por status, distribuição por tipo, por área técnica e por distrito.
- R1.2 O sistema DEVE responder quantidade de unidades com pendências de validação e o total de pendências.
- R1.3 O sistema DEVE responder quantidade de unidades sem CNES e de serviços fora do CNES.
- R1.4 O sistema DEVE responder as alterações dos últimos 7 e 30 dias e as 10 unidades alteradas mais recentemente.
- R1.5 O sistema DEVE calcular os números a partir da base atual, considerando o escopo de leitura do usuário.
- R1.6 O sistema DEVE aceitar filtros por distrito e área técnica.
- R1.7 O sistema DEVE responder em menos de 1 s com 1.000 unidades.

## Perguntas em aberto
- Quais indicadores o Sérgio usa para conferir os dados? (validar na próxima reunião)

## Emenda R2 (09/11/2026; aprovada, Vinicius, 09/11/2026, item V2)
A spec 011 (§ Fora do escopo) remete à 009 o dashboard estatístico da Etapa 06 da disciplina de Banco de Dados. Esta emenda o inclui, reaproveitando as quatro consultas da Etapa 03 feitas na `feat/003-interface-dashboard` (reescritas para o esquema da 006/011).

### R2. Consultas estatísticas da Etapa 03
- R2.1 QUANDO um usuário com `dashboard:read` consulta `GET /dashboard/consultas/unidades-por-categoria`, o sistema DEVE responder a contagem de unidades por status, por tipo, por área técnica e sem CNES.
- R2.2 QUANDO consulta `GET /dashboard/consultas/equipamentos-por-tipo-e-distrito`, o sistema DEVE responder a quantidade de equipamentos (soma de `quantity`) por tipo de equipamento e distrito (JOIN).
- R2.3 QUANDO consulta `GET /dashboard/consultas/alteracoes-por-periodo`, o sistema DEVE responder, por distrito, as alterações de unidades nos últimos 7 e 30 dias, lidas da `vw_unit_history`.
- R2.4 QUANDO consulta `GET /dashboard/consultas/alteracoes-recentes`, o sistema DEVE responder as 10 alterações mais recentes, com unidade, distrito, autor e ação, lidas da `vw_unit_history`.
- R2.5 Todas DEVEM aplicar o escopo de leitura do usuário e aceitar os filtros de distrito e de tipo de unidade (como a 011/R2.5 e R2.7).
