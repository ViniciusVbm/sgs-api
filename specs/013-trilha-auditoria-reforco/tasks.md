# 013 · Reforço da trilha de auditoria · Tarefas

- Status: **Aprovado (Vinicius (ViniciusVbm), proprietário e dono único da spec, 11/11/2026)**. G3 registrado pelo agente por autorização expressa do proprietário na sessão de trabalho de 11/11/2026, depois do G1 e do G2 no mesmo dia, pela exceção de `steering/sdd-workflow.md` § Exceção pontual: spec 013. Histórico:
  - redigido por agente em 11/11/2026;
  - revisões 2 e 3 em 11/11/2026;
  - revisão 4 em 11/11/2026: a antiga T8 foi dividida em T8 e T9 (D7), o que renumerou as tarefas para T1 a T15.

Cada tarefa é pequena (até ~300 linhas de diff), testável e cita os requisitos que cobre. Só se marca `[x]` quando o teste citado passa e o `make check` está verde.

Regras de execução:
- Os testes de integração rodam com `env -u SGS_TEST_DATABASE_URL`, em Testcontainers descartável.
- Nada roda em `sgs-local` nem em `sgs-api`, e o `make test-all` não é usado.
- As tarefas são executadas **na ordem numérica**.
- As migrações nascem nessa ordem: T1 → `0013_01`, T7 → `0013_02`, T10 → `0013_03`, T13 → `0013_04` (design § Modelo de dados).
- Os arquivos de teste marcados como "novo" ainda não existem e são criados na tarefa. Os demais já existem e só ganham testes.

## Dependências
| Tarefa | Depende de | Por quê |
|---|---|---|
| T1 | — | colunas e canonicalização |
| T2 | T1 | `Ator.tipo` e `Ator.origem` |
| T3 | T1, T2 | `Ator.user_agent`; mexe na mesma `ator_da_requisicao` da T2 |
| T4 | T3 | o helper de origem lê `request.client` depois do middleware de proxy |
| T5 | T1 | colunas `result` e `result_reason` |
| T6 | T3, T5 | `operacao.falhou` usa origem e resultado |
| T7 | T2, T5, T6 | todo caminho de gravação já preenche tipo e resultado antes do `NOT VALID` |
| T8 | T7 | `auditoria.verificada` nasce sob a obrigatoriedade |
| T9 | T8 | a âncora e a CLI reaproveitam a verificação consistente |
| T10 | — (vem depois da T9 só pela ordem das migrações) | independente da trilha |
| T11 | T2, T3, T5, T6, T8 | confere ação, tipo, resultado, IP e UA de todas as rotas, inclusive `verificar` |
| T12 | T1, T3, T7 | detalhe com UA e `origem_restrita`; `auditoria.evento_consultado` sob a obrigatoriedade |
| T13 | T1, T6, T10 | colunas novas na view; `operacao.falhou` com entidade de unidade; vem depois da migração da T10 |
| T14 | T8, T9, T12, T13 | a tela consome os campos novos da verificação, da âncora, do detalhe e do histórico |
| T15 | T7, T9, T10, T13 | documenta e testa a âncora, o log do banco, a view e o backup com `NOT VALID` |

Não há ciclos: cada tarefa depende só de tarefas de número menor.

## Tarefas

- [x] T1. Colunas novas e canonicalização da trilha (11/11/2026; `make check` verde: 1052 passaram, 3 pulados)
  - Requisitos: R1.5 (base), R2.3; base de R1.1, R1.2 e R4.1
  - Faz:
    - migração `0013_01_audit_log_origem_resultado`: cinco colunas e CHECKs de domínio, sem obrigatoriedade;
    - no domínio, `Ator.tipo`, `Ator.origem` e `Ator.user_agent`, e `AuditEntry.result` e `AuditEntry.result_reason`, todos opcionais;
    - `content()` omite os nulos (design § Emenda à spec 001);
    - repositório, consultas e `tables.py`.
  - **Primeiro passo (TDD):** o hash de referência v1 é calculado com o código atual, **antes** de qualquer edição, e fixado no teste.
  - Pronto quando passam:
    - `tests/unit/audit/test_hash.py::test_hash_de_registro_v1_nao_muda`
    - `tests/unit/audit/test_hash.py::test_campo_novo_entra_no_hash` (um caso por campo novo)
    - `tests/unit/audit/test_hash.py::test_usuario_sem_id_e_rejeitado`
    - `tests/integration/audit/test_audit_chain.py::test_cadeia_antiga_continua_integra_apos_migracao`
    - `tests/integration/audit/test_audit_chain.py::test_instante_preserva_microssegundos_e_ordem_por_id`
    - `tests/integration/audit/test_audit_chain.py::test_valor_fora_do_dominio_e_recusado`
    - `tests/integration/test_migracoes_sincronizadas.py`

- [x] T2. Identidade e origem dos eventos (11/11/2026; `test_origem.py`: 6 passaram; `make check` verde: 1058 passaram, 3 pulados)
  - Requisitos: R1.1, R1.2, R1.3, R1.4
  - Faz:
    - `ator_da_requisicao` grava tipo `usuario` e origem `api`;
    - o seed grava `seed`, e o `create-user` grava `cli_admin`;
    - `login._auditar` grava `anonimo`, `sistema` ou `usuario`;
    - porta `PapeisDoUsuario` para o `auth.login`.
  - Pronto quando:
    - passam, em `tests/integration/audit/test_origem.py` (novo): `::test_evento_da_api_e_de_usuario`, `::test_seed_tem_tipo_seed_sem_usuario`, `::test_create_user_tem_tipo_cli_admin`, `::test_login_de_inexistente_e_anonimo`, `::test_bloqueio_e_do_sistema` e `::test_login_registra_papeis`;
    - o `lint-imports` está verde.

- [x] T3. Origem da requisição: IP e User-Agent (11/11/2026; `tests/unit/core/test_origem.py`: 5 passaram; `test_origem.py` e `test_auth_audit.py`: 10 passaram; `make check` verde: 1065 passaram, 3 pulados)
  - Requisitos: R3.2, R3.4, R3.5
  - Faz:
    - `src/core/origem.py` (`origem_da_requisicao`), usado por `ator_da_requisicao` e pelo `_origem` das rotas de autenticação;
    - UA cortado em 200 caracteres e sem caracteres de controle;
    - só o `User-Agent` é lido;
    - as rotas de autenticação deixam de declarar o cabeçalho `User-Agent` como parâmetro, porque o helper o lê; o `contracts/openapi.yaml` foi regenerado;
    - os eventos `auth.*` novos guardam o UA só na coluna (design § Origem do ator).
  - Pronto quando passam:
    - em `tests/unit/core/test_origem.py` (novo): `::test_user_agent_cortado_e_sem_controle`, `::test_cliente_nao_confiavel_nao_escolhe_ip`, `::test_x_real_ip_e_forwarded_nao_tem_efeito`, `::test_proxy_confiavel_repassa_ip_real` e `::test_sem_cliente_ou_host_invalido_fica_sem_ip`;
    - em `tests/integration/audit/test_origem.py`: `::test_evento_de_negocio_tem_user_agent_e_ip` e `::test_evento_de_autenticacao_tem_user_agent_na_coluna`;
    - `tests/integration/identity/test_auth_audit.py::test_eventos_de_acesso_auditados_com_ip_e_user_agent`, que já existe, ajustado para conferir as colunas.

- [x] T4. Proxy confiável `/32` e subnets por stack (11/11/2026; arquitetura e unidade: 5 passaram; `test_auditoria_proxy.py`: 3 passaram, sem pulo; regressão das suítes e2e com compose: `test_frontend_entrega.py` e `test_tls_banco.py`, 11 passaram, e `tests/e2e_front/test_inicio.py`, 4 passaram; `make check` verde: 1070 passaram, 3 pulados)
  - Requisitos: R3.1, R3.3, R3.7, R3.8
  - Faz:
    - em `docker/compose.yml`: redes `borda` e `dados`; `SGS_BORDA_SUBNET` e `SGS_BORDA_PROXY_IP` obrigatórias (`:?`); `ipv4_address` fixo do proxy; `FORWARDED_ALLOW_IPS=${SGS_BORDA_PROXY_IP}/32`;
    - o `CMD` do `Dockerfile` deixa de usar `*`;
    - valores de exemplo no `.env.example`;
    - `tests/e2e/redes.py` (novo): a tabela de subnets, a variável alternativa `SGS_E2E_SUBNET_<SUITE>` e a conferência só por leitura;
    - `tests/e2e/test_frontend_entrega.py`, `tests/e2e/test_tls_banco.py` e `tests/e2e_front/conftest.py` passam a usar a sua subnet;
    - notas no `Caddyfile` e no `README`; `SGS_BORDA_*` no job `compose-smoke` do CI;
    - ajuste da implementação: o proxy usa o último endereço útil da subnet (`.14` numa `/28`), e não o `.2`, que a API recebia antes por ser criada primeiro (design § Proxies confiáveis).
  - Pronto quando:
    - passam, em `tests/architecture/test_proxy_confiavel.py` (novo): `::test_sem_forwarded_allow_ips_curinga_nem_subnet`, `::test_compose_exige_subnet_e_ip_do_proxy` e `::test_subnets_das_suites_sao_unicas_e_fora_dos_pools_do_docker`;
    - passam, em `tests/unit/e2e/test_redes.py` (novo; sem Docker): `::test_subnet_ocupada_usa_alternativa_ou_para_com_mensagem` e `::test_subnets_padrao_sao_unicas_na_faixa_e_fora_dos_pools_do_docker`;
    - passam, em `tests/e2e/test_auditoria_proxy.py` (novo; `slow`, projeto `sgs-api-e2e-auditoria`):
      - `::test_xff_do_cliente_nao_vira_ip_registrado` (cliente → Caddy com XFF falso)
      - `::test_vizinho_na_rede_dados_nao_forja_ip` (contêiner descartável na rede `dados` → API com XFF)
      - `::test_gateway_da_borda_nao_e_confiavel` (requisição com XFF direto ao IP da API na `borda`, com origem no gateway)

- [x] T5. Resultado nos eventos existentes (11/11/2026; `test_auth_audit.py`, `test_require.py` e `test_audit_chain.py`: 49 passaram, inclusive `test_falha_no_caso_de_uso_desfaz_a_auditoria`; `make check` verde: 1073 passaram, 3 pulados)
  - Requisitos: R4.1, R4.2, R4.9
  - Faz: `result` e `result_reason` em todo `registrar`:
    - `success` é o padrão;
    - `auth.login_failed` e `auth.mfa_failed` ficam `failure`/`autenticacao`;
    - `acesso.negado` fica `denied`/`autorizacao`.
  - Pronto quando:
    - passam `tests/integration/identity/test_auth_audit.py::test_mfa_falho_e_auditado` (código errado e reuso), `tests/integration/identity/test_auth_audit.py::test_login_falho_tem_resultado_failure` e `tests/integration/access/test_require.py::test_negacao_tem_resultado_denied`;
    - o teste existente `tests/integration/audit/test_audit_chain.py::test_falha_no_caso_de_uso_desfaz_a_auditoria` continua verde.

- [x] T6. Falhas de negócio auditadas (11/11/2026; `test_falha.py`: 3 passaram; `test_falhas_auditadas.py`: 15 passaram; `make check` verde: 1091 passaram, 3 pulados)
  - Requisitos: R4.3, R4.4, R4.5, R4.6, R4.7, R4.8
  - Faz:
    - `_sessao_de_negocio` com os `except` na ordem do design;
    - `_registrar_falha_sem_mascarar`, com transação independente depois do rollback;
    - `metadados_de_falha` em lista fechada, no domínio (`src/modules/audit/domain/falha.py`), e `registrar_falha` na application da auditoria;
    - entidade só quando for inequívoca.
    - Fica para a T13: tirar da `vw_unit_history` os eventos `auth.*`, `acesso.negado` e `auditoria.*`. A view de hoje não filtra por ação, então o `operacao.falhou` da unidade já aparece no histórico, o que a T6 testa.
  - Pronto quando passam:
    - em `tests/unit/audit/test_falha.py` (novo): `::test_metadados_recusam_chave_fora_da_lista`, `::test_campos_invalidos_sao_descartados` e `::test_codigo_vem_do_mapa_fixo`;
    - em `tests/integration/audit/test_falhas_auditadas.py` (novo):
      - `::test_conflito_grava_um_evento_e_desfaz_o_cadastro`
      - `::test_precondicao_falhou_e_ausente`
      - `::test_validacao_de_dominio`
      - `::test_erro_interno_simulado` (monkeypatch levantando `RuntimeError`)
      - `::test_evento_de_falha_sobrevive_ao_rollback`
      - `::test_metadata_so_tem_chaves_permitidas_e_nenhum_valor_enviado` (valor-sentinela)
      - `::test_falha_ao_auditar_nao_esconde_o_erro_original`
      - `::test_erros_nao_selecionados_nao_gravam` (parametrizado: 401 sem token, 404, 422 de schema, `Forbidden` comum, `TooManyRequests`)
      - `::test_negacao_nao_gera_operacao_falhou`
      - `::test_falha_sem_id_no_caminho_fica_sem_entidade`
      - `::test_falha_da_unidade_aparece_no_historico_da_unidade`

- [x] T7. Obrigatoriedade de tipo e resultado no banco (11/11/2026; `test_audit_chain.py` e `test_migracoes_sincronizadas.py`: 15 passaram; integração de `audit`, `identity`, `access`, `registry` e `tools`: 309 passaram; `make check` verde: 1094 passaram, 3 pulados; `convalidated = false` conferido no teste)
  - Requisitos: R1.6
  - Faz: migração `0013_02_audit_log_origem_obrigatoria` (`CHECK … NOT VALID`, nunca validado).
  - Ajustes de teste: os ajudantes que gravavam com um `Ator` sem tipo, ou com `INSERT` sem `actor_type` e `result`, passaram a informar os dois. São eles: `test_audit_chain.py`, `test_audit_immutable.py`, `tests/integration/db/test_views.py` e `tests/integration/db/test_indices.py` (este é `slow` e passou à parte). O `test_migracoes_sincronizadas.py` filtra só o `SAWarning` da reflexão de CHECK `NOT VALID` do SQLAlchemy 2.1.
  - Pronto quando:
    - passam `tests/integration/audit/test_audit_chain.py::test_insert_sem_tipo_ou_resultado_e_recusado` e `tests/integration/audit/test_audit_chain.py::test_linhas_antigas_continuam_aceitas`;
    - as suítes de integração de `audit`, `identity`, `access`, `registry` e `tools` continuam verdes;
    - `tests/integration/test_migracoes_sincronizadas.py` passa.

- [x] T8. Verificação consistente com a cabeça (11/11/2026; `test_adulteracao.py`: 12 passaram; `test_contrato_openapi.py`: 1 passou; integração de `audit`: 100 passaram; `make check` verde: 1108 passaram, 3 pulados. Prova negativa feita fora do repositório: sem a foto REPEATABLE READ, a escrita concorrente dá `integra=false` e `cabeca_confere=false`)
  - Requisitos: R5.1, R5.2, R5.5 (sem âncora), R5.11, R7.3
  - Faz:
    - `verificar_cadeia` numa transação `REPEATABLE READ READ ONLY`, comparando com `audit_chain_head`;
    - parâmetro `registrar_execucao`, e `auditoria.verificada` gravado em transação separada;
    - `VerificacaoOut` com `ultimo_id`, `hash_final` e `cabeca_confere`;
    - `make openapi`.
  - Pronto quando passam:
    - em `tests/integration/audit/test_adulteracao.py` (novo):
      - `::test_delete_no_meio`
      - `::test_delete_no_fim`
      - `::test_delete_do_primeiro_evento_e_detectado`
      - `::test_update_de_hash`
      - `::test_update_de_metadata`
      - `::test_update_de_result_e_actor_type`
      - `::test_update_de_origin_user_agent_e_result_reason`
      - `::test_truncate_bloqueado`
      - `::test_escrita_concorrente_nao_gera_falso_positivo`
      - `::test_verificacao_seguinte_inclui_os_eventos_concorrentes`
      - `::test_verificacao_grava_evento_em_transacao_separada`
      - `::test_verificacao_sem_registrar_execucao_nao_grava`
    - `tests/architecture/test_contrato_openapi.py`.
  - Implementação: a porta ganha `fixar_foto_consistente()` (`SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY`, em `audit_snapshot_consistente.sql`) e `cabeca_da_cadeia()` (`audit_chain_head.sql`). `registrar_execucao` é um callable opcional: a rota passa um que grava `auditoria.verificada` numa sessão própria; sem ele, nada é gravado.

- [x] T9. Âncora, `cadeia_id` e CLIs `ancorar` e `verificar` (11/11/2026; `test_adulteracao.py`: 16 passaram, 4 deles de âncora; `test_sgs_admin_ancorar.py`: 3 passaram; `test_sgs_admin_verificar.py`: 9 passaram; `test_contrato_openapi.py`: 1 passou; integração de `audit` e `tools`: 129 passaram; `make check` verde: 1126 passaram, 3 pulados)
  - Requisitos: R5.3, R5.4, R5.5 (com âncora), R5.9, R5.12
  - Faz:
    - `ancora` com `cadeia_id` em `VerificacaoIn`, e `cadeia_confere` e `ancora_confere` em `VerificacaoOut`;
    - `sgs-admin auditoria ancorar`;
    - `sgs-admin auditoria verificar [--ancora arquivo.json]`, só leitura e sem gravar evento;
    - `make openapi`.
  - Implementação:
    - `gerar_ancora` (application) roda a mesma `verificar_cadeia`, sem `registrar_execucao`, e só emite âncora de cadeia íntegra e não vazia. O `id` e o `hash` são os do último evento verificado; `cadeia_id`, total e banco são lidos na mesma foto (`audit_chain_identity.sql`).
    - Códigos de saída: `ancorar` dá 0 com âncora, 1 se a cadeia é divergente e 2 se está vazia. `verificar` dá 0 se íntegra, 1 se divergente ou se a âncora não confere, e 2 se a âncora é ilegível, de outra versão ou tem campo inválido.
  - Pronto quando passam:
    - em `tests/integration/audit/test_adulteracao.py`: `::test_delete_no_fim_com_cabeca_ajustada_so_a_ancora_acusa`, `::test_delete_do_primeiro_evento_muda_a_cadeia`, `::test_ancora_de_outra_cadeia_nao_confere` e `::test_ancora_inexistente_nao_confere`;
    - em `tests/integration/tools/test_sgs_admin_ancorar.py` (novo): `::test_ancorar_emite_json_sem_gravar`, `::test_ancorar_identifica_a_cadeia` e `::test_cadeia_vazia_nao_emite_ancora`;
    - em `tests/integration/tools/test_sgs_admin_verificar.py` (novo):
      - `::test_verificar_offline_integra_com_codigo_zero`
      - `::test_verificar_offline_acusa_adulteracao_com_codigo_um`
      - `::test_verificar_offline_nao_grava_nada` (total de eventos e cabeça iguais)
      - `::test_verificar_offline_com_ancora_invalida_da_codigo_dois`
    - `tests/architecture/test_contrato_openapi.py`.

- [x] T10. `db_change_log` somente inserção e `ENABLE ALWAYS` (11/11/2026; `test_log_banco_privilegios.py`: 21 passaram, 8 testes novos, dois deles parametrizados por superusuário e dono; `test_log_banco.py` e `test_particoes.py`: 21 passaram; integração de `audit` e `tools` com `test_migracoes_sincronizadas.py`: 141 passaram; `make check` verde: 1149 passaram, 3 pulados)
  - Requisitos: R6.1, R6.2, R6.3, R6.4, R6.5, R6.6, R6.8
  - Faz: migração `0013_03_db_change_log_imutavel`, com:
    - a função;
    - os triggers de linha e de TRUNCATE na tabela-mãe, nas partições mensais e na `DEFAULT`;
    - o `sp_ensure_monthly_partitions` atualizado;
    - `ENABLE ALWAYS` nos três grupos de triggers (design § `0013_03`, item 7).
  - Implementação: 13 arquivos em `migrations/sql/0013_03/`. Os passos 01 a 08 rodam como `sgs_owner` (função, triggers da mãe, bloco `DO` para as partições existentes, ENABLE ALWAYS na mãe e o procedimento recriado); os passos 09 a 13 rodam com o papel que faz as migrações (ENABLE ALWAYS nos triggers do `audit_log` e no `trg_registry_change_log`). A conferência no catálogo (`tgenabled = 'A'`) vale também para os triggers de linha clonados nas partições e para os da partição criada pelo procedimento.
  - Pronto quando passam:
    - em `tests/integration/audit/test_log_banco_privilegios.py`:
      - `::test_update_e_delete_recusados_pela_mae_e_direto_na_particao`
      - `::test_truncate_recusado_na_mae_na_particao_e_na_default`
      - `::test_particao_nova_nasce_protegida`
      - `::test_trigger_legitimo_continua_gravando`
      - `::test_api_so_tem_select_e_nao_faz_detach_drop_nem_replica`
      - `::test_triggers_estao_enable_always` (`tgenabled = 'A'` nos três grupos, em cada partição existente e numa partição nova criada pelo procedure)
      - `::test_replica_nao_contorna_triggers_enable_always` (superusuário com `session_replication_role = replica`: UPDATE no `audit_log` e no `db_change_log` recusado; escrita no cadastro continua gerando log)
      - `::test_limite_dono_consegue_detach_drop_e_disable_trigger`
    - os testes de `tests/integration/audit/test_log_banco.py` e `tests/integration/audit/test_particoes.py` continuam verdes.

- [x] T11. Cobertura sistemática das rotas de escrita (11/11/2026; 26 rotas de escrita: 24 no mapa e 2 exceções justificadas; `test_cobertura_rotas.py`: 3 passaram; integração de `audit`: 117 passaram; `make check` verde: 1152 passaram, 3 pulados)
  - Requisitos: R7.1, R7.2, R7.6
  - Faz: o mapa `ROTA → ação` e as exceções justificadas em `tests/integration/audit/cobertura.py` (novo).
  - Pronto quando passam, em `tests/integration/audit/test_cobertura_rotas.py` (novo): `::test_toda_rota_de_escrita_esta_mapeada`, `::test_rota_grava_evento_completo` e `::test_operacao_nao_gera_fato_duplicado`.

- [x] T12. Detalhe com RBAC, leitura auditada e privacidade (11/11/2026; `test_consulta_trilha.py`, `test_schemas.py`, `test_privacidade_trilha.py` e `test_seed_matriz.py`: 38 passaram; `test_contrato_openapi.py`: 1 passou; integração de `audit`: 126 passaram; `make check` verde: 1163 passaram, 3 pulados)
  - Requisitos: R1.5 (API), R7.4, R7.5, R8.2 (API), R8.5, R8.6, R8.9
  - Faz:
    - `detalhar_evento` esconde IP, UA e sessão sem `auditoria:read_acessos` (`origem_restrita`) e grava `auditoria.evento_consultado`;
    - `auditoria.evento_consultado` passa a ser tratado como evento de acesso em `_e_de_acesso` e em `audit_events.sql`;
    - `EventoOut` e `EventoDetalheOut` ampliados;
    - `make openapi`.
  - Pronto quando passam:
    - em `tests/integration/audit/test_consulta_trilha.py`:
      - `::test_detalhe_esconde_origem_sem_read_acessos`
      - `::test_detalhe_mostra_origem_ao_auditor`
      - `::test_detalhe_grava_evento_consultado`
      - `::test_gestor_nao_ve_evento_consultado`
      - `::test_evento_antigo_vem_com_campos_novos_nulos`
      - `::test_sem_auditoria_read_e_403`
    - `tests/unit/audit/test_schemas.py::test_evento_out_nao_tem_campos_de_origem` (novo);
    - em `tests/integration/audit/test_privacidade_trilha.py` (novo): `::test_lista_nao_expoe_origem`, `::test_gestor_dados_nao_encontra_sentinela_em_nenhuma_rota_get` e `::test_auditor_ve_origem_so_no_detalhe`;
    - `tests/integration/access/test_seed_matriz.py::test_read_acessos_so_para_auditor_e_admin_ti`;
    - `tests/architecture/test_contrato_openapi.py`.

- [x] T13. Histórico da unidade e dashboard (11/11/2026; `test_views.py`, `test_consulta_trilha.py` e `test_painel.py`: 39 passaram; integração de `audit` e `dashboard` com os testes de sincronização e de SQL documentado: 322 passaram, 3 pulados; `make check` verde: 1170 passaram, 3 pulados)
  - Requisitos: R1.5 (histórico), R8.4 (histórico), R8.6 (view), R8.7, R8.8
  - Faz:
    - migração `0013_04_vw_unit_history_resultado`;
    - `unit_history.sql` com as colunas novas;
    - filtro de resultado em `summary_changes.sql`, `changes_by_period.sql` e `recent_changes.sql`.
  - Pronto quando passam:
    - em `tests/integration/db/test_views.py`, com a constante `COLUNAS_DO_HISTORICO` ampliada no fim: `::test_vw_unit_history_nao_tem_colunas_de_origem`, `::test_vw_unit_history_continua_security_invoker_e_sem_dml_para_a_api` e o já existente `::test_historico_traz_eventos_da_unidade_de_equipamentos_e_servicos_com_autor`;
    - em `tests/integration/audit/test_consulta_trilha.py`: `::test_historico_da_unidade_mostra_falha_da_unidade`, `::test_historico_da_unidade_nao_mostra_acesso_negado_nem_auditoria` e `::test_historico_traz_resultado_e_origem`;
    - `tests/integration/dashboard/test_painel.py::test_alteracoes_nao_contam_falhas_nem_acessos`;
    - `tests/integration/test_migracoes_sincronizadas.py`.

- [x] T14. Tela: detalhe, resultado, horário, histórico e verificação (11/11/2026; `test_frontend_estatico.py`: 148 passaram; Playwright, `test_qualidade_historico.py` e `test_ficha.py`: 32 passaram, sendo 6 testes novos, depois de corrigida a rolagem horizontal em 390 px; `test_desativar.py`: 9 passaram; `make check` verde: 1170 passaram, 3 pulados)
  - Requisitos: R1.5 (tela), R2.1, R2.2, R8.1, R8.2 (tela), R8.3, R8.4 (tela)
  - Faz:
    - `ui/format.js` com segundos e fuso, e `fmtInstante`;
    - `<dialog>` de detalhe e coluna "Resultado" em `views/historico.js`;
    - histórico da ficha com chip de resultado;
    - `#/cadeia` com cabeça, `cadeia_id` e âncora.
  - Ajustes da implementação:
    - O detalhe usa o modal acessível que o front já tem (`ui/modal.js`: `role="dialog"`, foco preso e devolvido), e não um `<dialog>` nativo, para seguir o padrão das outras telas.
    - O `fmtDataHora` comum não mudou, para não alterar telas fora do escopo. A trilha, o log do banco e o histórico da unidade usam um helper novo, `fmtAuditoria` (segundos e "UTC−03:00"). O `DATA_HORA_SEGUNDOS` duplicado em `views/unidade.js` passou a usar o `fmtDataHoraSegundos` de `ui/format.js`.
  - Pronto quando:
    - `tests/architecture/test_frontend_estatico.py` passa;
    - passam, em `tests/e2e_front/test_qualidade_historico.py` (`slow`): `::test_detalhe_do_evento_auditor`, `::test_detalhe_restrito_gestor_dados`, `::test_evento_antigo_mostra_nao_registrado`, `::test_horario_com_segundos_e_fuso` e `::test_cadeia_mostra_cabeca_cadeia_e_ancora`;
    - passa `tests/e2e_front/test_ficha.py::test_historico_mostra_tentativa_sem_sucesso`;
    - os testes existentes desses arquivos continuam verdes.

- [x] T15. Âncora, limites, retenção, backup, restauração, ensaio e documentação (11/11/2026; `test_backup_restauracao.py` (`slow`): 1 passou, evidência em `docs/operacao/evidencias/ensaio-restauracao-2026-11-11.json`; R5.8, R9.3, R9.5 e R9.6 revisados em `docs/operacao/backup-restauracao.md` § Conferência; relatório acadêmico em `docs/seguranca-auditoria/relatorio-ferramentas-audit-trail.md`; `make check` verde: 1170 passaram, 3 pulados)
  - Requisitos: R3.6, R5.6, R5.7, R5.8, R5.10, R6.7, R9.1, R9.2, R9.3, R9.4, R9.5, R9.6, R9.7
  - Faz:
    - ADR-0012 (âncora, `cadeia_id`, modelo de confiança, limites, rotina automatizada futura) e ADR-0013 (retenção, backup e restauração);
    - `docs/operacao/ancora-auditoria.md` e `docs/operacao/backup-restauracao.md`, com o modelo de evidências;
    - atualização de `docs/architecture/modelo-dados.md`, `docs/banco/04-dicionario-dados.md`, `docs/banco/05-objetos-e-justificativas.md`, `docs/banco/07-matriz-conformidade.md`, `steering/security.md` e `docs/governanca/03-registro-de-riscos.md`;
    - **ensaio de restauração** (R9.7) num contêiner PostgreSQL descartável, com as evidências registradas em `docs/operacao/evidencias/` (sem dump, sem dado pessoal);
    - nenhum snapshot histórico é alterado.
  - Pronto quando:
    - passa `tests/integration/audit/test_backup_restauracao.py::test_restauracao_preserva_cadeia_ancora_e_protecoes` (novo; `slow`; Testcontainers descartável);
    - o ensaio está registrado com evidências;
    - a revisão do proprietário confirma que R5.8, R9.3, R9.5 e R9.6 estão cobertos.

## Matriz requisito → tarefa → teste
| Requisito | Tarefa | Prova |
|---|---|---|
| R1.1, R1.2 | T1, T2 | `test_hash.py::test_usuario_sem_id_e_rejeitado`; `test_origem.py::test_evento_da_api_e_de_usuario`, `::test_seed_tem_tipo_seed_sem_usuario`, `::test_create_user_tem_tipo_cli_admin` |
| R1.3 | T2 | `test_origem.py::test_login_de_inexistente_e_anonimo`, `::test_bloqueio_e_do_sistema` |
| R1.4 | T2 | `test_origem.py::test_login_registra_papeis` |
| R1.5 | T1, T12, T13, T14 | `test_hash.py::test_hash_de_registro_v1_nao_muda`; `test_audit_chain.py::test_cadeia_antiga_continua_integra_apos_migracao`; `test_consulta_trilha.py::test_evento_antigo_vem_com_campos_novos_nulos`, `::test_historico_traz_resultado_e_origem`; `test_qualidade_historico.py::test_evento_antigo_mostra_nao_registrado` |
| R1.6 | T7 | `test_audit_chain.py::test_insert_sem_tipo_ou_resultado_e_recusado`, `::test_linhas_antigas_continuam_aceitas` |
| R2.1, R2.2 | T14 | `test_qualidade_historico.py::test_horario_com_segundos_e_fuso` |
| R2.3 | T1 | `test_audit_chain.py::test_instante_preserva_microssegundos_e_ordem_por_id`, `::test_valor_fora_do_dominio_e_recusado` |
| R3.1 | T4 | `test_proxy_confiavel.py::test_sem_forwarded_allow_ips_curinga_nem_subnet` |
| R3.2 | T3 | `test_origem.py` (unidade): `::test_cliente_nao_confiavel_nao_escolhe_ip`, `::test_x_real_ip_e_forwarded_nao_tem_efeito`, `::test_proxy_confiavel_repassa_ip_real`, `::test_sem_cliente_ou_host_invalido_fica_sem_ip` |
| R3.3 | T4 | `test_auditoria_proxy.py::test_xff_do_cliente_nao_vira_ip_registrado` |
| R3.4, R3.5 | T3 | `test_origem.py::test_user_agent_cortado_e_sem_controle`; `test_origem.py::test_evento_de_negocio_tem_user_agent_e_ip`, `::test_evento_de_autenticacao_tem_user_agent_na_coluna` (integração); `test_auth_audit.py::test_eventos_de_acesso_auditados_com_ip_e_user_agent` |
| R3.6 | T15 | revisão documental (`steering/security.md`) |
| R3.7 | T4 | `test_proxy_confiavel.py::test_compose_exige_subnet_e_ip_do_proxy`, `::test_subnets_das_suites_sao_unicas_e_fora_dos_pools_do_docker`; `test_redes.py::test_subnet_ocupada_usa_alternativa_ou_para_com_mensagem`, `::test_subnets_padrao_sao_unicas_na_faixa_e_fora_dos_pools_do_docker` |
| R3.8 | T4 | `test_auditoria_proxy.py::test_vizinho_na_rede_dados_nao_forja_ip`, `::test_gateway_da_borda_nao_e_confiavel` |
| R4.1, R4.2 | T5 | `test_auth_audit.py::test_mfa_falho_e_auditado`, `::test_login_falho_tem_resultado_failure`; `test_require.py::test_negacao_tem_resultado_denied` |
| R4.3 | T6 | `test_falhas_auditadas.py::test_evento_de_falha_sobrevive_ao_rollback`, `::test_conflito_grava_um_evento_e_desfaz_o_cadastro`, `::test_precondicao_falhou_e_ausente`, `::test_validacao_de_dominio`, `::test_erro_interno_simulado` |
| R4.4, R4.5 | T6 | `test_falha.py::test_metadados_recusam_chave_fora_da_lista`, `::test_campos_invalidos_sao_descartados`, `::test_codigo_vem_do_mapa_fixo`; `test_falhas_auditadas.py::test_metadata_so_tem_chaves_permitidas_e_nenhum_valor_enviado`, `::test_falha_sem_id_no_caminho_fica_sem_entidade` |
| R4.6 | T6 | `test_falhas_auditadas.py::test_erros_nao_selecionados_nao_gravam` |
| R4.7 | T6 | `test_falhas_auditadas.py::test_negacao_nao_gera_operacao_falhou` |
| R4.8 | T6 | `test_falhas_auditadas.py::test_falha_ao_auditar_nao_esconde_o_erro_original` |
| R4.9 | T5 | `test_audit_chain.py::test_falha_no_caso_de_uso_desfaz_a_auditoria` (já existe) |
| R5.1, R5.2 | T1, T8 | `test_hash.py::test_campo_novo_entra_no_hash`; `test_adulteracao.py::test_delete_no_meio`, `::test_delete_no_fim`, `::test_delete_do_primeiro_evento_e_detectado`, `::test_update_de_hash`, `::test_update_de_metadata`, `::test_update_de_result_e_actor_type`, `::test_update_de_origin_user_agent_e_result_reason`, `::test_truncate_bloqueado` |
| R5.3 | T9 | `test_adulteracao.py::test_delete_no_fim_com_cabeca_ajustada_so_a_ancora_acusa`, `::test_delete_do_primeiro_evento_muda_a_cadeia`, `::test_ancora_de_outra_cadeia_nao_confere`, `::test_ancora_inexistente_nao_confere` |
| R5.4, R5.9 | T9 | `test_sgs_admin_ancorar.py::test_ancorar_emite_json_sem_gravar`, `::test_ancorar_identifica_a_cadeia`, `::test_cadeia_vazia_nao_emite_ancora` |
| R5.5 | T8, T9 | `test_adulteracao.py::test_delete_no_fim` (cabeça); `test_adulteracao.py::test_ancora_de_outra_cadeia_nao_confere` (âncora) |
| R5.6, R5.7, R5.8, R5.10 | T15 | revisão documental (ADR-0012, `docs/operacao/ancora-auditoria.md`) |
| R5.11 | T8 | `test_adulteracao.py::test_escrita_concorrente_nao_gera_falso_positivo`, `::test_verificacao_seguinte_inclui_os_eventos_concorrentes`, `::test_verificacao_grava_evento_em_transacao_separada`, `::test_verificacao_sem_registrar_execucao_nao_grava` |
| R5.12 | T9 | `test_sgs_admin_verificar.py::test_verificar_offline_integra_com_codigo_zero`, `::test_verificar_offline_acusa_adulteracao_com_codigo_um`, `::test_verificar_offline_nao_grava_nada`, `::test_verificar_offline_com_ancora_invalida_da_codigo_dois` |
| R6.1 | T10 | `test_log_banco_privilegios.py::test_update_e_delete_recusados_pela_mae_e_direto_na_particao` |
| R6.2 | T10 | `test_log_banco_privilegios.py::test_truncate_recusado_na_mae_na_particao_e_na_default` |
| R6.3 | T10 | `test_log_banco_privilegios.py::test_trigger_legitimo_continua_gravando`; `test_log_banco.py` |
| R6.4 | T10 | `test_log_banco_privilegios.py::test_particao_nova_nasce_protegida` |
| R6.5 | T10 | `test_log_banco_privilegios.py::test_api_so_tem_select_e_nao_faz_detach_drop_nem_replica` |
| R6.6 | T10 | `test_log_banco_privilegios.py::test_limite_dono_consegue_detach_drop_e_disable_trigger`, `::test_replica_nao_contorna_triggers_enable_always` |
| R6.7 | T15 | revisão documental (ADR-0012, `docs/banco/05-objetos-e-justificativas.md`) |
| R6.8 | T10 | `test_log_banco_privilegios.py::test_triggers_estao_enable_always`, `::test_replica_nao_contorna_triggers_enable_always` |
| R7.1, R7.2, R7.6 | T11 | `test_cobertura_rotas.py::test_toda_rota_de_escrita_esta_mapeada`, `::test_rota_grava_evento_completo`, `::test_operacao_nao_gera_fato_duplicado` |
| R7.3 | T8 | `test_adulteracao.py::test_verificacao_grava_evento_em_transacao_separada` |
| R7.4 | T12 | `test_consulta_trilha.py::test_detalhe_grava_evento_consultado`, `::test_gestor_nao_ve_evento_consultado` |
| R7.5 | T12 | política no design (aprovada no G2) |
| R8.1, R8.3 | T14 | `test_qualidade_historico.py::test_detalhe_do_evento_auditor`, `::test_cadeia_mostra_cabeca_cadeia_e_ancora` |
| R8.2 | T12, T14 | `test_consulta_trilha.py::test_detalhe_esconde_origem_sem_read_acessos`, `::test_detalhe_mostra_origem_ao_auditor`; `test_qualidade_historico.py::test_detalhe_restrito_gestor_dados` |
| R8.4 | T13, T14 | `test_consulta_trilha.py::test_historico_traz_resultado_e_origem`; `test_ficha.py::test_historico_mostra_tentativa_sem_sucesso` |
| R8.5 | T12 | `test_consulta_trilha.py::test_sem_auditoria_read_e_403` e os testes de escopo existentes |
| R8.6 | T12, T13 | `test_schemas.py::test_evento_out_nao_tem_campos_de_origem`; `test_privacidade_trilha.py::test_lista_nao_expoe_origem`, `::test_gestor_dados_nao_encontra_sentinela_em_nenhuma_rota_get`, `::test_auditor_ve_origem_so_no_detalhe`; `test_views.py::test_vw_unit_history_nao_tem_colunas_de_origem`, `::test_vw_unit_history_continua_security_invoker_e_sem_dml_para_a_api` |
| R8.7 | T6, T13 | `test_falhas_auditadas.py::test_falha_da_unidade_aparece_no_historico_da_unidade`; `test_consulta_trilha.py::test_historico_da_unidade_mostra_falha_da_unidade`, `::test_historico_da_unidade_nao_mostra_acesso_negado_nem_auditoria`; `test_views.py::test_historico_traz_eventos_da_unidade_de_equipamentos_e_servicos_com_autor` |
| R8.8 | T13 | `test_painel.py::test_alteracoes_nao_contam_falhas_nem_acessos` |
| R8.9 | T12 | `test_seed_matriz.py::test_read_acessos_so_para_auditor_e_admin_ti` |
| R9.1, R9.2, R9.3, R9.5, R9.6 | T15 | revisão documental (ADR-0013, `docs/operacao/backup-restauracao.md`) |
| R9.4 | T15 | `test_backup_restauracao.py::test_restauracao_preserva_cadeia_ancora_e_protecoes` |
| R9.7 | T15 | evidências do ensaio em `docs/operacao/evidencias/` |
