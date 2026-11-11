# Roteiro de demonstração · entrega final (Etapa 06)

Cerca de 8 minutos, mostrando na interface cada requisito das Etapas 03 a 06. A matriz requisito → tela → teste está em [07-matriz-conformidade.md](07-matriz-conformidade.md).

## Antes da apresentação
- **Ambiente:**
  - sistema no ar com o compose e o seed de demonstração (README § Subir o ambiente e § Dados de demonstração);
  - endereço: `https://localhost/`, ou `https://localhost:<SGS_HTTPS_PORT>/` quando o compose sobe com outra porta (ex.: `8443`);
  - com mais de um compose na máquina, use sempre o nome do projeto (`docker compose -p <projeto> -f docker/compose.yml …`), para não mexer em outro ambiente.
- **Usuários do seed** (fictícios). A senha é a definida em `SGS_SEED_SENHA` na execução do seed e não vai neste documento:

  | Papel | Usuário | Para quê |
  |---|---|---|
  | Gestor de Dados (central) | `demo.carla.dias` | quase todo o roteiro |
  | Auditor | `demo.bento.sa` | verificação da cadeia |
  | Técnico Distrital (DS IV) | `demo.nicolas.brito` | permissões e escopo |

- **2FA:** no primeiro acesso, cada usuário cadastra o TOTP num aplicativo autenticador (a tela mostra a chave em texto). Faça isso antes, para os três.
- **Segundo navegador** (ou janela anônima) já aberto com o Gestor de Dados, para o passo do conflito de versão.
- **A demonstração grava no banco** (sessões, auditoria, cadastros). Use o ambiente de demonstração, não rode seed nem migração na hora e não altere o banco por fora da aplicação.

## Roteiro
| Tempo | Onde | O que mostrar | Requisito |
|---|---|---|---|
| 0:00 | Login (`demo.carla.dias`) | Senha e 2FA. Menu montado pelas permissões do `/me` | Etapa 06: interface integrada |
| 0:30 | **Início** | Totais, barras por distrito, tipo, área e situação, atividade recente. Botão "Painel completo" | 03: indicadores; 04: `vw_unit_history` |
| 1:00 | **Qualidade dos dados** | **Indicadores:** total, sem CNES e %, médias de serviços e equipamentos por unidade, ritmo 7 × 30 dias | 06: totais, médias, %, tendência |
| | | **Filtro:** trocar o distrito para DS IV e mostrar que números e gráficos mudam e que a URL guarda o filtro | 06: filtros |
| | | **Gráficos:** pizza da situação cadastral (`fn_registration_status`), % sem CNES com a linha da rede (subconsulta no HAVING), alterações 7 × 30, equipamentos por tipo | 05: função; 04: subconsulta; 06: gráficos |
| | | **Linha do período:** "Personalizado" de hoje (agrupa por hora) | 06: filtro de período |
| | | **Consultas:** abrir "Unidades sem serviço" (anti join), "Conciliação" (FULL OUTER JOIN), "Unidades com serviço fora do CNES" (EXISTS) e o "Inventário" (view), mostrando a técnica SQL de cada uma | 04: anti join, FOJ, subconsultas, views |
| 3:00 | **Tabelas de referência** | Incluir um tipo de serviço, editar o nome, desativar e reativar ("excluir é desativar") | 06: CRUD de 3 tabelas |
| | | Trocar o código de um tipo de equipamento: o painel mostra os equipamentos afetados pelo `ON UPDATE CASCADE` e a conferência nos registros. Trocar de volta | 02/06: `ON UPDATE CASCADE` |
| 4:00 | **Cadastrar unidade** (`#/nova`) | Cadastrar uma unidade de teste. A ficha abre na aba Serviços | 06: CRUD de `health_units` |
| | Ficha › **Serviços** | Incluir um serviço, editar (o painel mostra "Atualizado em" antes e depois, `trg_set_updated_at`), remover | 06: CRUD de `services`; 05: trigger |
| 5:00 | Ficha › **Editar ficha** | Alterar telefone e bairro: o diff de confirmação; depois, versão +1 e nova data (`trg_health_units_version`) | 05: trigger de versão |
| | **Segundo navegador** | Abrir a mesma ficha, editar e salvar. Voltar ao primeiro e salvar: aviso de conflito (HTTP 412), nada sobrescrito | 06: concorrência (`If-Match`) |
| 6:00 | Ficha › **Desativar unidade** | Motivo, confirmação ("desativar não é excluir"), painel com Ativa → Inativa e versão +1 (`sp_deactivate_unit`) | 05: procedimento de atualização |
| | Ficha › **Histórico** | Evento "Unidade desativada" com o motivo (`vw_unit_history`) | 04: view |
| 6:45 | **Histórico geral** | Log do banco: as linhas das ações feitas agora, "pela API" (`trg_registry_change_log`). Aba Partições: as partições mensais (`sp_ensure_monthly_partitions`, com CURSOR) | 05: trigger de log; procedimento com cursor |
| 7:15 | Login (`demo.bento.sa`) › **Verificação da cadeia** | "Cadeia íntegra": a trilha não pode ser alterada (triggers de bloqueio) | 05: triggers de auditoria |
| 7:45 | Login (`demo.nicolas.brito`) | Lista aberta no DS IV; ficha sem "Editar" e com "Propor alteração" desabilitado; sem "Tabelas de referência" | 06: permissões e escopo |

## Se algum passo falhar
| Situação | O que fazer |
|---|---|
| Login responde "muitas tentativas" (429) | O limite é de 10 logins por minuto por IP: aguardar 1 minuto. Por isso o 2FA dos três usuários fica pronto antes |
| Código do 2FA recusado | Conferir o relógio do celular (o TOTP depende da hora certa) e usar o código seguinte, depois de trocar os 30 segundos |
| Certificado do navegador | O ambiente usa a CA interna do Caddy: aceitar o aviso ou importar a CA (README § Subir o ambiente) |
| Tela com "Não foi possível concluir a operação" | A mensagem mostra o `detail` da API e o código do pedido; recarregar a página. Se a sessão expirou, a tela volta ao login |
| O segundo navegador não está logado na hora do conflito (412) | Pular o passo e mostrar a prova automática: `tests/e2e_front/test_edicao.py::test_dois_navegadores_a_segunda_gravacao_recebe_412_e_nada_e_sobrescrito` |
| Gráfico de linha só com o aviso de "histórico insuficiente" | É o esperado com dados de um único dia; usar o período "Personalizado" de hoje (por hora) depois das ações da demonstração |
| Algum passo de escrita falha no ambiente da apresentação | Mostrar o teste correspondente na matriz ([07-matriz-conformidade.md](07-matriz-conformidade.md)) e o resultado registrado em `specs/012-frontend/tasks.md` |
| O ambiente não sobe | Ter à mão as capturas e a saída dos testes (`make check` e `tests/e2e_front`) como evidência de reserva |

## Se perguntarem
- **"Por que não apaga a unidade ou o tipo?"** Integridade referencial (FKs sem cascata na exclusão, `ON DELETE RESTRICT`) e o minimundo ("nunca é apagada, só desativada"). A exclusão física existe em `services` (ver 05 § Etapa 6).
- **"E as tabelas com menos de 30 linhas?"** Ver [06-trinta-tuplas.md](06-trinta-tuplas.md): todas as tabelas de negócio têm 30 ou mais; as demais são domínio fechado, uso ou infraestrutura, com justificativa (cenário D, aprovado pelo professor).
- **"Como sei que o trigger pega alteração fora da aplicação?"** O teste `test_log_do_banco_mostra_alteracao_feita_fora_da_api` faz um `UPDATE` direto num banco descartável e confere a linha "fora da API" na tela. No banco da demonstração, não se altera nada por fora.
- **"A linha do período está quase vazia."** O seed grava o histórico num único dia. Os pontos novos vêm do uso, como as ações feitas nesta demonstração.

## Evidências de reserva
- **Testes:** `make check` e `uv run pytest -m slow tests/e2e_front` (compose descartável; resultados registrados em `specs/012-frontend/tasks.md`, T26).
- **Capturas e diffs:** guardados pelo grupo junto da entrega.
