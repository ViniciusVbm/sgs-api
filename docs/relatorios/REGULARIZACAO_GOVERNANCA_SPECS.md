# Regularização da governança das specs 008, 009, 010 e das emendas da 011

- Data: 09/11/2026
- Branch: `docs/regularizacao-governanca-specs` (a partir de `novo/main`, `31e561c`)
- Natureza: documental. Nenhum código, migração, teste, contrato ou matriz RBAC foi alterado.
- Preparado por agente (Claude Code) a pedido da equipe atual. Revisão 2 (09/11/2026): incorpora a decisão formal do responsável pelo projeto, Vinicius (ViniciusVbm), que assume a autoria, o ownership, as decisões e as aprovações das specs 008 a 011 (§ 4.1). Revisão 3 (09/11/2026, encerramento): o responsável autorizou formalmente as decisões V1 a V8, inclusive a transferência da spec 003; as aprovações estão registradas na § 7. As seções 2 a 6 ficam como o registro da auditoria que levou a elas.

## 1. Por que este documento existe
As specs 008, 009 e 010, as emendas da 011 (T21, T22) e a emenda do ADR-0007 foram implementadas na consolidação final (09/11/2026) **antes do portão humano**, por decisão explícita do usuário (`docs/RELATORIO_VALIDACAO_FINAL.md` § 9.1). Os cabeçalhos diziam "aguarda aprovação do Rafael", e os relatórios e o `README.md` condicionavam a continuidade a ele.

Dois fatos, levantados nesta auditoria, mostram que essa dependência não tinha base documental completa:

1. **As specs 008, 009 e 010 nunca tiveram o campo "Dono humano"** (o modelo `specs/_templates/requirements.md` o prevê). A atribuição ao Rafael só aparecia no `README.md` e nos relatórios. A autoria original no Git é do `rafareloM` (`7b63009`, 03/10/2026); a revisão técnica de 09/11/2026 é do `ViniciusVbm` (`dbe38a1`).
2. **O fluxo SDD (`steering/sdd-workflow.md`) não prevê transferência de dono**, rebaseline nem encerramento de spec. Ele exige que "cada spec tem um dono humano (integrante do grupo)" e que "o agente nunca marca a própria spec como `Aprovado`".

Por isso esta regularização: (a) troca a dependência nominal do Rafael pelo **portão do dono da spec**, como o fluxo define; (b) passa as specs revistas de `Rascunho` para `Em revisão`, que é o estado real; (c) registra as divergências entre spec e código com evidência; (d) deixa para os humanos, de forma objetiva, as decisões que o fluxo reserva a eles (§ 4).

O que **não** foi feito: nenhuma spec foi marcada `Aprovado`; nenhuma aprovação foi atribuída a quem não a deu, nem com data retroativa; as aprovações reais do Rafael (001, 002, 003, 006, 011 base, ADR-0007, ADR-0008) e as decisões dele com data foram preservadas com o nome dele.

**Revisão 2.** Na primeira versão, nenhum dono novo foi registrado, porque não havia base documental. Depois, o responsável pelo projeto decidiu formalmente que é o dono das 008, 009, 010 e 011. Essa decisão foi registrada no cabeçalho de cada `requirements.md` e no `steering/sdd-workflow.md`, que ganhou a § Dono da spec: atribuição e transferência.

## 2. Resumo da auditoria

| Spec | Situação anterior | Situação real (evidência) | Divergências | Regularização realizada |
|---|---|---|---|---|
| 008 Histórico | Rascunho; "aguarda aprovação do Rafael"; sem dono registrado; T1–T4 `[x]` | R1.1–R1.4, R2.1–R2.3, R3.1–R3.2, R4.1 implementados (`src/modules/audit/api/rotas.py`; `tests/integration/audit/test_consulta_trilha.py`, 9 testes; R2.3 por mascaramento na gravação, `tests/integration/registry/test_crud_unidades.py::test_trilha_mascara_o_nome_do_gestor_e_grava_o_papel`; R4.1 por `test_audit_immutable.py`) | 5 (D008-1 a D008-5, § 3.1): índice `(action, occurred_at)` do design não existe; ids de referência não traduzidos para nomes; filtros de período e autor sem teste; nomes de teste do "Pronto quando" inexistentes | Status → Em revisão; dono: Vinicius (revisão 2); § Divergências no design; nota de rastreabilidade nas tarefas |
| 009 Dashboard | Rascunho; emenda R2 "aguarda o Rafael"; T1 e T4 `[x]`, T2b e T3 abertas | R1.1–R1.6 e R2.1–R2.5 implementados (`/api/v1/dashboard/resumo` e `/consultas/*`; `tests/integration/dashboard/test_painel.py`); R1.7 (1 s com 1.000 unidades) **não** implementado nem medido | 5 (D009-1 a D009-5, § 3.2): sem `asyncio.gather`; sem cache (já adiado); R1.2 depende de `pending_issues`, alimentado só pelo seed (007 não existe); campo `por_situacao_cadastral` fora do design | Status → Em revisão; dono: Vinicius (revisão 2); emenda R2 aguarda validação (V2); § Divergências no design |
| 010 Demonstração | Rascunho; revisão técnica "aguarda o Rafael"; T1, T2 `[x]`, T3 aberta | R1.1–R1.3, R1.5, R1.6 implementados (`src/tools/seed_demo.py`; `tests/integration/tools/test_seed_demo.py`, 3 testes); R1.4 com divergência de letra; R2 (planilha) **não** implementado | 5 (D010-1 a D010-5, § 3.3): design original (YAML, Typer, ator `sistema-seed`) contradiz a revisão técnica no mesmo arquivo; `--reset` e seed no compose não existem (o D010-4 foi retirado na revisão final) | Status → Em revisão; dono: Vinicius (revisão 2); seções originais marcadas como substituídas pela revisão técnica; § Divergências |
| 011 Banco (base T1–T20) | Aprovado (Rafael, 06–07/11/2026) | Implementada; 20 tarefas `[x]` (T1–T11 com os testes do "Pronto quando"; T12–T20 com linha "Prova") | 4 leituras do design "falta o Rafael confirmar"; texto do design (`FOR ROLE sgs`) diferente do código (`FOR ROLE CURRENT_USER`) | Aprovação do Rafael preservada; dono: Vinicius desde 09/11 (revisão 2); "falta o Rafael confirmar" → "falta o dono validar" (V5) |
| 011 Emendas T21–T22 | "Emenda proposta… aguarda aprovação do Rafael", dentro de um `tasks.md` Aprovado | Implementadas (`migrations/versions/0011_09_ajustes_base.py`; `tests/integration/db/test_ajustes_0011_09.py`, 8 testes; `test_painel.py::test_escopo_do_tecnico_distrital_reduz_os_numeros`) | T21 não descreve os 3 CHECKs criados (`0011_09/03–05`); arquivos de teste do "Pronto quando" não existem; T22 muda a matriz RBAC semeada (`dashboard:read`) sem aprovação | Emenda marcada `Em revisão` (a base continua Aprovado); CHECKs registrados; 2 perguntas em aberto marcadas como respondidas na prática pelas emendas, pendentes de aprovação |
| ADR-0007 emenda | "aguarda revisão do Rafael" | `limits`, `pwdlib[argon2]` e `pyotp` no `pyproject.toml`; `slowapi` ausente | `steering/tech.md` ainda lista `slowapi 0.1.x` | Pendência passa a ser o aceite de um integrante humano (`docs/agents/domain.md`); contradição com `tech.md` registrada |

## 3. Divergências entre spec e implementação

Cada item diz se é só documental (o código está certo e o texto envelheceu) ou funcional (falta algo que a spec pede). A resolução é do dono da spec: ajustar o texto ou abrir tarefa.

### 3.1 Spec 008
| ID | Onde | Spec diz | Implementação | Tipo |
|---|---|---|---|---|
| D008-1 | design § Consulta | índice `(action, occurred_at DESC)` "criado aqui" | não existe em nenhuma migração; só `ix_audit_log_entity` (`migrations/sql/0011_03/06_ix_audit_log_entity.sql`) | funcional (desempenho; volume atual pequeno) |
| D008-2 | design § Consulta | "ids de referência são traduzidos para nomes na resposta" | `MudancaOut` devolve `de`/`para` crus (`src/modules/audit/api/schemas.py`); só o **campo** ganha rótulo | funcional parcial (R1.2 pede rótulo do campo, que existe; a tradução do valor é só do design) |
| D008-3 | design § Consulta | `ROTULOS_CAMPOS` no módulo `registry` | está em `src/modules/audit/domain/consultas.py` | documental |
| D008-4 | tasks T1–T4 | "Pronto quando" cita `test_consulta_eventos.py`, `test_historico_unidade.py`, `test_trilha_geral.py`, `test_verificar_cadeia.py` | nenhum existe; a prova é `tests/integration/audit/test_consulta_trilha.py` (já anotada em "Prova") | documental |
| D008-5 | R1.3 | filtros por período, autor e campo | os três existem na rota; só o de campo tem teste (`test_historico_filtra_por_campo`) | cobertura de teste |

### 3.2 Spec 009
| ID | Onde | Spec diz | Implementação | Tipo |
|---|---|---|---|---|
| D009-1 | design § Implementação | consultas em paralelo com `asyncio.gather` em sessões separadas | uma sessão, consultas em sequência (`src/modules/dashboard/application/consultas.py`) | documental (decisão de implementação) |
| D009-2 | design / T2 | cache de 30 s com invalidação por versão | não existe; adiado para T2b condicionado à T3 | já registrado |
| D009-3 | R1.7 / T3 | p95 < 1 s com 1.000 unidades | sem teste de desempenho (`tests/e2e/test_dashboard_desempenho.py` não existe) | funcional (não implementado) |
| D009-4 | R1.2 | unidades com pendências e total de pendências | lido de `health_units.pending_issues`, que só o seed preenche; a spec 007 (que calcula pendências) não está implementada | funcional parcial |
| D009-5 | design § Resposta | campos do resumo | a resposta tem também `unidades.por_situacao_cadastral` (011/R5.3); nomes de teste do "Pronto quando" (`test_resumo.py`, `test_consultas_etapa3.py`) não existem | documental |

### 3.3 Spec 010
| ID | Onde | Spec diz | Implementação | Tipo |
|---|---|---|---|---|
| D010-1 | design § Formato e § Comando | YAML, Typer, ator `sistema-seed` | JSON, `argparse`, ator nulo com `metadata.origem` (`src/tools/seed_demo.py`), como a § Revisão técnica do mesmo arquivo | documental (contradição interna; a revisão técnica substitui) |
| D010-2 | design § Comando | `sgs-admin seed demo [--reset]` | não há `--reset` | funcional (não implementado) |
| D010-3 | design § Comando | "o compose de `dev` roda o seed após as migrações" | não roda; o seed é manual (`docs/instalacao.md`) | funcional (não implementado) |
| ~~D010-4~~ | R1.4 | 2FA desativado **apenas** quando `APP_ENV=dev` | **Retirada na revisão técnica final.** O seed não liga nem desliga o 2FA. Fora de `dev`, o login exige o cadastro do segundo fator (`login.py`, `MfaPurpose.ENROLL`), e o `Settings` recusa `MFA_OBRIGATORIO=false` fora de `dev` (`test_config.py::test_mfa_so_pode_ser_desligado_em_dev`) | atendido; a primeira versão deste relatório errou |
| D010-5 | tasks T1 / R2 | "Pronto quando" `tests/unit/seeds/test_yaml_valido.py`; conversor da planilha (T3) | o teste não existe (o formato virou JSON); T3 não feita: a planilha não está disponível | documental (T1); funcional (T3) |

### 3.4 Spec 011 e emendas
| ID | Onde | Situação |
|---|---|---|
| D011-1 | tasks T21 | A `0011_09` também cria `ck_equipments_status_valido`, `ck_equipments_quantity_positiva` e `ck_services_status_valido` (`migrations/sql/0011_09/03–05`), que a descrição da T21 não cita. Eles respondem à pergunta em aberto da 006 ("se os valores forem fixados, uma revisão nova põe o CHECK"). Provados por `test_ajustes_0011_09.py::test_checks_do_equipamento_recusam_valor_invalido` e `::test_check_do_servico_recusa_status_invalido`. |
| D011-2 | tasks T13 a T22 | O "Pronto quando" cita arquivos de teste que não existem (por exemplo, `test_inventario.py`, `test_log_banco_api.py`, `test_desativar.py`, `test_catalogo.py`, `tests/tools/test_sql_bd.py`, `test_auditoria_lgpd.py`, `test_escopo_dashboard.py`): os testes foram consolidados em outros arquivos. Todas essas tarefas têm a linha "Prova" com o teste real. Em T1 a T11 os arquivos citados existem. |
| D011-3 | tasks T22 | Muda o escopo máximo de `dashboard:read` semeado pela 0003 (matriz RBAC da spec 003) para `COORD_TECNICO`, `TECNICO_DISTRITAL` e `GESTOR_UNIDADE` (`migrations/sql/0011_09/17_dashboard_read_escopo_por_papel.sql`). É mudança de matriz sem aprovação: precisa do dono da 011 **e** da 003. |
| D011-5 | `docs/architecture/arquitetura-conceitual.md` § 4 e `tests/integration/access/test_seed_matriz.py` | A matriz da arquitetura, que a 003/R1.1 adota, ainda diz `G` para `dashboard:read` em todos os papéis. O teste da 003/R1.1 passou a aplicar a T22 como delta (`AJUSTES_DA_0011_09`, commit `5bb25b3`, 09/11/2026). A matriz documentada e o banco divergem até V4 e V8 serem decididos. |
| D011-4 | requirements § Perguntas em aberto | Quatro leituras do design aguardam confirmação do dono (coluna gerada no trigger de versão; `FOR ROLE CURRENT_USER`; trigger de log; rotas de R2) e uma (isenção do teste da T20) foi resolvida na T20. O design § Na 0011 ainda diz `FOR ROLE sgs`. |

## 4. Decisões

### 4.1 Decisões já tomadas pelo responsável pelo projeto (registradas)
| ID original | Decisão | Onde ficou registrada |
|---|---|---|
| G1 | Dono das specs 008, 009 e 010: **Vinicius (ViniciusVbm)**, desde 09/11/2026. Antes, nenhum dono registrado; a autoria original (`rafareloM`, 03/10/2026) continua no texto. | linha "Dono humano" de cada `requirements.md`; `specs/README.md` |
| G2 | Dono da spec 011: **Vinicius (ViniciusVbm)**, desde 09/11/2026; antes, o Rafael. As aprovações dele (requisitos em 06/11; design e T1 a T20 em 07/11/2026) continuam válidas e com o nome dele. | `specs/011-*/requirements.md` e `tasks.md` |
| G6 | Regra de atribuição e transferência de dono: uma linha no `requirements.md`, transferida pelo dono atual ou pelo responsável pelo projeto, sem aprovação retroativa; os portões pendentes passam ao novo dono. | `steering/sdd-workflow.md` § Dono da spec |
| G7 (parte factual) | A exceção provisória (aprovar sozinho design e tarefas das 003, 006 e 011) foi concedida ao Rafael e não passa a quem assume. As emendas da 011 seguem a tabela do fluxo. | `steering/sdd-workflow.md` § Exceção provisória |

Com isso, **nenhuma decisão pendente depende mais do Rafael** para as specs 008 a 011. A única exceção é a matriz da spec 003, que continua sob o dono dele (item V8).

### 4.2 Decisões técnicas submetidas ao dono (decididas em 09/11/2026; ver § 7)
Estas exigem avaliação do conteúdo, não só de governança. Nenhuma foi aprovada. Para cada item, a recomendação do agente vem marcada como tal; a decisão é do dono.

| Item | Spec | O que validar | Opções | Recomendação (não vinculante) |
|---|---|---|---|---|
| V1 | 008 | Requisitos, design e tarefas (T1 a T4 feitas); divergências D008-1, D008-2, D008-3 e D008-5 (§ 3.1) | Para cada divergência: (a) ajustar o design ao código; (b) abrir tarefa | D008-1: (a), tirar o índice por ação do design (volume pequeno). D008-2: (a), sem tradução de valores. D008-3: (a). D008-5: (b), tarefa pequena de teste dos filtros de período e autor |
| V2 | 009 | Requisitos (incluindo a emenda R2), design e tarefas; D009-1 a D009-5 (§ 3.2) | Aprovar com as tarefas abertas (T2b e T3) ou exigir a T3 antes | (a) para D009-1 e D009-5; manter T3 e T2b abertas; registrar a dependência da 007 em D009-4 |
| V3 | 010 | Requisitos, design (revisão técnica: JSON, `argparse`, ator nulo) e tarefas; D010-2 a D010-5 (§ 3.3) | D010-2 e D010-3: tirar do design ou abrir tarefa. (D010-4 retirado: R1.4 atendido) | Tirar `--reset` e o seed no compose do design; manter T3 aberta enquanto a planilha não estiver disponível |
| V4 | 011 | Emenda T21 (índices, CHECKs, `updated_at`, REVOKEs, `actor_roles`, máscara do gestor) e T22 (escopo de `dashboard:read` por papel) | Aprovar, pedir ajuste ou reverter (reverter exige migração nova) | Aprovar a T21. Na T22, ver V8 primeiro |
| V5 | 011 | As quatro leituras do design que esperam confirmação (D011-4): coluna gerada no trigger de versão, `FOR ROLE CURRENT_USER`, recorte do trigger de log e leituras das rotas de R2 | Confirmar e ajustar o texto do design (`FOR ROLE sgs`, lista de colunas do trigger de versão) ou pedir mudança no código | Confirmar; o código é o que os testes provam |
| V6 | ADR-0007 | Emenda: `slowapi` → `limits`; `pwdlib[argon2]` e `pyotp` | Aceitar ou rejeitar | Aceitar e trocar `slowapi 0.1.x` por `limits` em `steering/tech.md` |
| V7 | Fluxo | O portão de design pede **dono + 1 integrante**. Como dono, você aprova sozinho requisitos e tarefas, mas não o design de V1 a V4 | (a) chamar mais um integrante para os designs; (b) criar uma exceção registrada no `sdd-workflow.md` | Decisão de processo sua; o agente não a tomou |
| V8 | 003 | A T22 muda a matriz RBAC semeada pela 0003 (spec 003), cujo dono registrado é o Rafael. As decisões DF da spec 012 também apontam para o dono da 003 e da 006 | (a) estender o ownership à 003 (e à 006, se quiser) pela regra do fluxo; (b) obter a validação do Rafael | (a) se você também responde pela 003; a regra nova cobre isso com uma linha |

Depois de cada validação: o dono troca `Em revisão` por `Aprovado (Vinicius, <data>)` no arquivo validado, com a data real, e o desvio da regra 1 no `RELATORIO_VALIDACAO_FINAL.md` § 9.1 fica encerrado para aquela spec.

### 4.3 Revisão técnica final dos itens V1 a V8 (09/11/2026)
Quando esta seção foi escrita, nenhuma aprovação tinha sido registrada. Esta seção separa, em cada item, o que é aprovação documental, o que é decisão de design e o que é trabalho funcional ainda pendente.

**Dependências**
- **V7 → V1, V2, V3, V4, V5:** o portão de design pede dono + 1 integrante. Requisitos e tarefas o dono aprova sozinho; os designs, não, enquanto V7 não for decidido.
- **V8 → V4 (só a T22):** a T22 altera a matriz da 003/R1.1 (D011-3, D011-5). A T21 não depende de V8.
- **V4 (T22) ↔ spec 012:** a 012/R4.1 espera o dashboard "no escopo dele". Reverter a T22 não quebra o front, mas muda os números que o Técnico Distrital, o Coordenador e o Gestor de Unidade veem.
- **V2 → spec 007:** a R1.2 só tem significado real quando a 007 calcular `pending_issues` (D009-4). Não bloqueia a aprovação.
- **V6 → `steering/tech.md`:** a troca da linha `slowapi` só depois do aceite.
- V1, V3 e V6 não dependem uns dos outros.

| Item | Aprovação documental | Decisão de design | Trabalho funcional pendente |
|---|---|---|---|
| V1 · 008 | Requisitos e tarefas (T1 a T4 com prova) | D008-1 (índice por ação), D008-2 (tradução de valores), D008-3 (texto) | D008-5: testes dos filtros de período e autor |
| V2 · 009 | Requisitos com a emenda R2; tarefas | D009-1 (sem `gather`), D009-5 (campo extra), cache adiado | T3 (R1.7 sem medição), T2b condicionada; D009-4 depende da 007 |
| V3 · 010 | Requisitos (R2 é opcional, "ONDE"); tarefas | Revisão técnica (JSON, `argparse`, ator nulo); D010-2, D010-3 | T3 (sem a planilha) |
| V4 · 011 | Emenda T21; emenda T22 só com V8 | Nenhuma nova: a T21 segue o design | Nenhum para aprovar; reverter a T22 exigiria uma migração nova |
| V5 · 011 | — | Quatro leituras do design (D011-4) e o ajuste de texto | Nenhum |
| V6 · ADR-0007 | Aceite da emenda; linha do `tech.md` | — | Nenhum |
| V7 · fluxo | — | Regra de processo | — |
| V8 · 003 | Validação da matriz pelo dono da 003 | — | Nenhum, se aprovada; migração nova, se rejeitada |

## 5. Referências ao processo anterior

| Arquivo | Antes | Agora |
|---|---|---|
| `specs/008-*/`, `009-*/`, `010-*/` (9 arquivos) | "Rascunho … aguarda aprovação do Rafael" | "Em revisão … aguarda o portão do dono (Vinicius; § 4.2)"; dono registrado |
| `specs/009-dashboard/requirements.md`, `specs/010-dados-demonstracao/design.md` | "aguarda aprovação do Rafael" na emenda e na revisão técnica | "aguarda validação do dono" (V2, V3) |
| `specs/011-*/requirements.md`, `tasks.md` | "Falta o Rafael confirmar"; "Emenda proposta… aguarda aprovação do Rafael" | "Falta o dono validar (V4, V5)"; emenda "Em revisão"; "Dono humano: Rafael" → Vinicius desde 09/11/2026, com o histórico das aprovações |
| `specs/010-dados-demonstracao/design.md` § Revisão técnica | referência a `docs/banco/30-tuplas.md`, que não existe | `docs/banco/06-trinta-tuplas.md` (o arquivo real) |
| `specs/README.md` | 008, 009, 010 `Rascunho`; 011 `Aprovado` | `Em revisão` com a situação real; 011 `Aprovado (T1–T20); emenda T21–T22 em revisão`; parágrafo apontando para este documento |
| `docs/adr/0007-*.md` | "aguarda revisão do Rafael" | "aguarda aceite de integrante humano (V6)" |
| `README.md`, `docs/RESUMO_STATUS_PROJETO.md` | "o Rafael é o dono"; "Rafael: revisar e aprovar" | dono registrado e pendências V1 a V8 |
| `steering/sdd-workflow.md` | sem regra de transferência; exceção provisória sem dizer se passa adiante | § Dono da spec: atribuição e transferência; a exceção é pessoal |
| `docs/RELATORIO_VALIDACAO_FINAL.md`, `docs/RELATORIO_PR_PUBLICACAO.md`, `docs/CHECKPOINT_CONSOLIDACAO.md` | relatórios datados que citam a aprovação do Rafael | texto original mantido (registro histórico), com nota de regularização apontando para este documento |

Preservados sem alteração, por serem registro histórico verdadeiro: as aprovações e decisões datadas do Rafael nas specs 001, 002, 003, 006 e 011; a remoção da 008/T5 e a decisão de não particionar o `audit_log` (Rafael, 06/11/2026); a exceção provisória de `steering/sdd-workflow.md`; `docs/integration-audit/` (auditoria das branches, datada).

Fora do escopo desta regularização e com menção ao Rafael como decisor: `docs/PLANO_INTEGRACAO_FRONTEND.md` e `specs/012-frontend/` (alterações locais ainda não versionadas; as decisões DF citam o Rafael como dono das specs 003 e 006, o que continua verdadeiro: o ownership assumido em 09/11/2026 cobre só as 008 a 011. Não foram alterados, por instrução; ver V8).

## 6. Pendências funcionais levantadas na auditoria (situação final na § 7.4)
- 008: D008-1, D008-2 e D008-5 (texto ou tarefa).
- 009: T3 (R1.7, desempenho) e T2b (cache, condicionada à T3); D009-4 depende da spec 007.
- 010: T3 (conversor), sem a planilha do cliente; D010-2 e D010-3.
- 011: D011-4 (confirmações) e o ajuste de texto do design (`FOR ROLE`).

## 7. Encerramento da regularização (09/11/2026)
Decisões autorizadas formalmente por Vinicius (ViniciusVbm), responsável pelo projeto, e registradas nos documentos em 09/11/2026, data real da execução. Nenhuma aprovação foi atribuída ao Rafael nem a outra pessoa, e nenhuma tem data retroativa.

### 7.1 Transferências de ownership
| Spec | Dono anterior | Dono atual | Registro |
|---|---|---|---|
| 003 | Rafael (autor; aprovou requisitos, design e tarefas em 07/11/2026) | Vinicius, desde 09/11/2026 (V8) | `specs/003-rbac/requirements.md` |
| 008, 009, 010 | nenhum registrado (autoria original: rafareloM, 03/10/2026) | Vinicius, desde 09/11/2026 (G1) | `requirements.md` de cada uma |
| 011 | Rafael (aprovou requisitos em 06/11 e design e T1 a T20 em 07/11/2026) | Vinicius, desde 09/11/2026 (G2) | `specs/011-recursos-banco-dados/requirements.md` |

### 7.2 Aprovações registradas (Vinicius, 09/11/2026)
| Item | Documento | O que foi aprovado |
|---|---|---|
| V1 | 008 `requirements.md`, `design.md`, `tasks.md` | Requisitos e tarefas; design ajustado (sem o índice `(action, occurred_at)`, sem tradução de ids para nomes, local real de `ROTULOS_CAMPOS`). T6 nova, aberta |
| V2 | 009 `requirements.md` (com a emenda R2), `design.md`, `tasks.md` | Requisitos e tarefas; design com consultas em sequência, sem cache e com `por_situacao_cadastral`; R1.7 registrado como não comprovado |
| V3 | 010 `requirements.md`, `design.md`, `tasks.md` | Requisitos (R1.4 mantido) e tarefas; design reescrito para JSON e `argparse`, sem `--reset` nem seed no compose |
| V4 | 011 `tasks.md` (emenda T21–T22); 011 `requirements.md` (perguntas respondidas) | Emenda T21 inteira (índices, CHECKs, `updated_at`, REVOKEs, `actor_roles`, máscara) e T22 (escopo de `dashboard:read` por papel), sem reverter nada |
| V5 | 011 `design.md`, 011 `requirements.md` | As quatro leituras de D011-4; design com `FOR ROLE CURRENT_USER` e `name_normalized` no recorte do trigger de versão |
| V6 | `docs/adr/0007-*.md`; `steering/tech.md` | Emenda aceita (`limits` no lugar do `slowapi`); `tech.md` lista `limits 5.8.x` |
| V7 | `steering/sdd-workflow.md` § Exceção pontual | Designs de V1 a V5 aprovados sem revisão por pares, só nesta regularização; a regra geral não muda |
| V8 | 003 `requirements.md` § Emenda; `docs/architecture/arquitetura-conceitual.md` § 4 | Transferência da 003; matriz com `dashboard:read` = `A`/`D`/`U` para Coordenador Técnico, Técnico Distrital e Gestor de Unidade |

As aprovações anteriores (001, 002, 003, 006, 011 base, ADR-0007, ADR-0008, decisões do Rafael com data) continuam como estavam, com o nome dele.

### 7.3 Coerência da T22
Matriz documentada (`arquitetura-conceitual.md` § 4, adotada pela 003/R1.1), banco (`0003` + `0011_09/17`), testes (`test_seed_matriz.py` com `AJUSTES_DA_0011_09`; `test_ajustes_0011_09.py::test_dashboard_read_tem_o_escopo_de_cada_papel`; `test_painel.py::test_escopo_do_tecnico_distrital_reduz_os_numeros`) e specs 003 e 011 agora dizem a mesma coisa. Nenhum código, migração ou teste precisou mudar: a documentação foi alinhada à implementação existente. D011-5 está resolvida.

### 7.4 Pendências funcionais (não impedem as aprovações)
| Spec | Tarefa | Situação |
|---|---|---|
| 008 | T6: testes dos filtros de período e autor (D008-5) | Aberta. *Nota posterior: concluída em 09/11/2026 (PR #2).* |
| 009 | T3: teste de desempenho (R1.7: menos de 1 s com 1.000 unidades) | Aberta; a meta **não está comprovada** |
| 009 | T2b: cache com invalidação por versão | Aberta, só se a T3 mostrar p95 acima de 1 s |
| 009 | Pendências do resumo (R1.2) com significado real | Depende da spec 007 (D009-4) |
| 010 | T3: conversor da planilha (R2) | Aberta, até o cliente enviar a planilha REDE_SAUDE_RECIFE_GEO |

### 7.5 Limitações
- `docs/PLANO_INTEGRACAO_FRONTEND.md` e `specs/012-frontend/` ainda citam o Rafael como dono da 003 e da 006 nas decisões DF. Não foram alterados, por instrução. A 003 agora é do Vinicius; a 006 continua do Rafael (não foi transferida).
- `docs/integration-audit/` é auditoria datada e continua citando o Rafael como decisor da época.
- Os "Pronto quando" com arquivos de teste que não existem (D008-4, D010-5, D011-2) foram mantidos como texto histórico; a prova de cada tarefa é a linha "Prova".
