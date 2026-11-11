# 013 · Reforço da trilha de auditoria · Design

- Status: **Aprovado (Vinicius (ViniciusVbm), proprietário e dono único da spec, 11/11/2026)**. G2 registrado pelo agente por autorização expressa do proprietário na sessão de trabalho de 11/11/2026, com aprovação individual pela exceção de `steering/sdd-workflow.md` § Exceção pontual: spec 013; não houve revisão por um segundo integrante. Histórico: redigido por agente em 11/11/2026; revisões 2 e 3 em 11/11/2026 (H1–H4, M1–M6, B1–B4); revisão 4 em 11/11/2026 (decisões do proprietário: P1–P8, H4, D1, D2, D3, D7).
- Requisitos: requirements.md

## Visão geral
O mecanismo continua um só: `audit.registrar` (spec 001) dentro da transação do caso de uso, com hash SHA-256 encadeado e trava em `audit_chain_head`. Muda o seguinte:

1. **Esquema.** Cinco colunas nuláveis novas em `audit_log`: `actor_type`, `origin`, `user_agent`, `result` e `result_reason`. O conteúdo canônico do hash inclui cada uma **só quando o valor não é nulo** (§ Emenda à spec 001). A obrigatoriedade (`CHECK … NOT VALID`) vem numa migração própria, depois que todos os caminhos de gravação preenchem os campos.
2. **Origem da requisição.** Um helper único resolve IP, User-Agent e request id. A lista de proxies confiáveis do uvicorn deixa de ser `*`, e cada stack tem a sua subnet de borda.
3. **Falhas.** A dependência `SessaoDeNegocio` grava `operacao.falhou` só para os erros selecionados, numa transação independente depois do rollback, sem esconder o erro original.
4. **Verificação.** Roda numa transação `REPEATABLE READ READ ONLY`, compara com a cabeça e com uma âncora externa opcional que identifica a cadeia (`cadeia_id`), e grava `auditoria.verificada` numa transação à parte. A CLI `sgs-admin auditoria verificar` faz a mesma verificação direto no banco, sem API e sem gravar nada (D2).
5. **`db_change_log`.** Triggers de somente inserção na tabela-mãe e em cada partição. Os triggers de imutabilidade e o de log ficam `ENABLE ALWAYS` (P7). Os limites contra o dono e o superusuário ficam caracterizados em teste.
6. **Histórico da unidade.** A `vw_unit_history` passa a expor resultado e origem e a excluir eventos de acesso e de auditoria, e inclui as falhas da unidade. O dashboard deixa de contar falhas como alterações.
7. **Tela.** Painel de detalhe, coluna de resultado, horário com segundos e fuso, verificação com cabeça e âncora.
8. **Operação.** Retenção, backup e restauração com procedimento, evidências e teste automatizado (§ Backup e restauração; ADR-0012 e ADR-0013).

A ordem das tarefas, os testes e a matriz requisito → tarefa → teste estão em `tasks.md`. Este design não repete nomes de teste, para os dois documentos não divergirem.

## Diagnóstico de partida (11/11/2026, `main` @ `4efd36c`)
Verificado por leitura do código, sem executar nada:

| Lacuna | Confirmada? | Evidência |
|---|---|---|
| A: origem | Sim | `seed_demo.py:112` e `sgs_admin.py:275` usam `Ator()` vazio; `login.py:320` (`_auditar`) nunca põe papéis |
| B: horário | Sim | `frontend/app/js/ui/format.js`: `DATA_HORA` sem `second` e sem fuso |
| C: IP/UA | Sim | `docker/Dockerfile:36-39` `--forwarded-allow-ips "*"`; `access/api/deps.py:177` não lê o UA; nenhum teste de XFF |
| D: resultado | Sim | não há coluna; `access/api/deps.py:153` só audita `AcessoNegado`; `auth.mfa_failed` sem teste |
| E: fim da cadeia | Sim | `audit/application/consultar.py:95-130` não lê `audit_chain_head`; os lotes são lidos em READ COMMITTED |
| F: log do banco | Sim | a `0011_07` não cria trigger de imutabilidade |
| G: cobertura | Sim | `tests/architecture/test_rotas_protegidas.py` confere permissão, não auditoria |
| H: tela | Parcial | a API já devolve ip, sessão e hash (`EventoDetalheOut`), mas a tela nunca chama `GET /auditoria/eventos/{id}` |
| I: retenção | Sim | os 2 anos só aparecem em `modelo-dados.md:74` e `steering/security.md:37`; o backup consta como "planejado" (risco R01) |
| Achado da revisão 3 | Sim | a `vw_unit_history` (`migrations/sql/0011_04/02_vw_unit_history.sql`) não filtra por ação; o `acesso.negado` com entidade `unidade` (`access/application/autorizacao.py:151-166`) entra no histórico da unidade e nas contagens do dashboard (`dashboard/infrastructure/sql/summary_changes.sql`, `changes_by_period.sql`, `recent_changes.sql`), o que contraria a 008/R2.2 |

Cadeia de proxy, levantada com `docker inspect` (só leitura):
- O cliente fala com a porta publicada do Caddy (v2.11.9).
- O Caddy encaminha para `api:8000` pela rede `<projeto>_default`, onde também estão `db` e `db-certs`.
- O uvicorn 0.54.0 aceita `X-Forwarded-*` de qualquer endereço.

O Caddy, sem `trusted_proxies`, ignora o `X-Forwarded-For` que vem do cliente e grava o IP da conexão. O risco real é um contêiner vizinho falar direto com a API. No ambiente local, o IP registrado é o gateway da rede Docker (`172.19.0.1`), porque o docker-proxy do host troca a origem; é coisa do ambiente, não da aplicação. A produção não está documentada (P3).

## Modelo de ameaças
| Atacante | Capacidade | O que a spec garante | Limite declarado |
|---|---|---|---|
| Cliente externo | controla todos os cabeçalhos HTTP | o IP registrado não é escolhido por ele (R3.2, R3.3) | o UA é só declaração do cliente (R3.4) |
| Usuário autenticado | rotas dentro das próprias permissões | toda escrita deixa evento (R7.1, R7.2); dados de origem só com `read_acessos` (R8.2, R8.6) | — |
| Contêiner vizinho, ou processo no host pelo gateway da bridge | fala direto com a API | não forja o IP: só o IP fixo do Caddy (`/32`) é confiável (R3.1, R3.8) | — |
| Processo da API comprometido (`sgs_app`) | INSERT e SELECT em `audit_log`; UPDATE em `audit_chain_head`; SELECT em `db_change_log` | não altera nem apaga eventos (REVOKE + trigger); não mexe em partições nem em `session_replication_role` (R6.5); mudar a cabeça faz a verificação acusar divergência | pode **inserir** eventos falsos, encadeados corretamente |
| Dono das tabelas ou `sgs_owner` | desliga ou remove triggers, DETACH ou DROP de partição | **detecção**: a verificação e a âncora acusam alteração no `audit_log`; a lista de partições mostra o mês faltando | o conteúdo apagado do `db_change_log` não é detectável |
| Superusuário | tudo isso, mais `session_replication_role = replica` (que não contorna os triggers `ENABLE ALWAYS`) e reescrita de cadeia e cabeça | **detecção** até a última âncora guardada fora do banco, conferida pela CLI offline (§ Limites contra superusuário) | uma reescrita completa e coerente depois da última âncora não é detectável |
| Quem controla o banco **e** as cópias das âncoras | tudo isso, mais reescrever as âncoras | nada | **risco aceito** (P6): o proprietário é o único responsável e acumula todas as funções; a cópia externa da âncora fica fora do ambiente local e do banco, mas sob o mesmo controle administrativo |

## Rotas (contrato)
| Método e rota | Permissão | Entrada | Saída | Erros | Requisitos |
|---|---|---|---|---|---|
| `GET /api/v1/auditoria/eventos` | `auditoria:read` global | inalterada | `PaginaOut[EventoOut]`; `EventoOut` ganha `autor.tipo`, `origem`, `resultado` e `resultado_categoria`, e **nunca** traz ip, UA ou sessão. `auth.*`, `acesso.negado` e `auditoria.evento_consultado` só aparecem com `read_acessos` | 401, 403, 422 | R1.1, R1.5, R4.1, R7.4, R8.4, R8.6 |
| `GET /api/v1/auditoria/eventos/{id_}` | `auditoria:read` global | inalterada | `EventoDetalheOut` com `user_agent` e `origem_restrita`; sem `read_acessos`, `ip`, `user_agent` e `sessao_id` vêm `null`. Grava `auditoria.evento_consultado` | 401, 403, 404 | R2.2, R7.4, R8.1, R8.2 |
| `POST /api/v1/auditoria/verificar` | `auditoria:read` global | `VerificacaoIn` + `ancora: {cadeia_id: [0-9a-f]{64}, id: int ≥ 1, hash: [0-9a-f]{64}} \| null` | `VerificacaoOut` + `ultimo_id`, `hash_final`, `cabeca_confere: bool \| null` (null quando há período), `cadeia_confere: bool \| null`, `ancora_confere: bool \| null`. Grava `auditoria.verificada` | 401, 403, 422 | R5.1–R5.5, R5.11, R7.3 |
| `GET /api/v1/unidades/{id}/historico` | inalterada | inalterada | `EventoOut` com os campos novos; conteúdo conforme R8.7 | inalterados | R1.5, R8.4, R8.6, R8.7 |
| `GET /api/v1/dashboard/consultas/alteracoes-*` e o resumo | inalterada | inalterada | inalterada; deixa de contar falhas e eventos de acesso | inalterados | R8.8 |

Todas as mudanças de contrato são aditivas. Mudam de comportamento:
- o detalhe, para o Gestor de Dados (R8.2; P4);
- o histórico da unidade e as contagens do dashboard, que deixam de incluir `acesso.negado` e passam a mostrar as falhas da unidade (R8.7, R8.8).

## Emenda à spec 001 (canonicalização)
A spec 001 (design § Auditoria, `specs/001-fundacao/design.md:24`) define `hash = SHA-256(prev_hash || JSON)`, com o JSON de chaves ordenadas, sem espaços, em UTF-8, data em UTC com microssegundos e IP normalizado. A 013 **acrescenta** uma regra, sem mudar as já existentes:

> As chaves `actor_type`, `origin`, `user_agent`, `result` e `result_reason` entram no JSON canônico **somente quando o valor não é nulo**. As 13 chaves atuais continuam sempre presentes, com o mesmo formato.

Consequências:
- Todo evento gravado antes da 013 recalcula o mesmo hash.
- Anular um campo novo num evento novo tira a chave e muda o hash.
- Preencher um campo novo num evento antigo põe a chave e muda o hash.

A emenda só vale depois que a 013 for aprovada. A 001 continua `Aprovado`; recebe só uma nota de referência apontando para esta seção, sem mudar o seu status nem o seu texto normativo.

## Modelo de dados / migrações
As migrações nascem na ordem das tarefas: T1 → `0013_01`, T7 → `0013_02`, T10 → `0013_03`, T13 → `0013_04`. O `down_revision` de cada uma é o head do momento (`0011_09`, depois `0013_01`, `0013_02`, `0013_03`). Há um comando por arquivo em `migrations/sql/<revisão>/`, com o cabeçalho exigido por `tests/architecture/test_sql_documentado.py`. As migrações anteriores não mudam.

### `0013_01_audit_log_origem_resultado` (T1)
1. `ALTER TABLE audit_log ADD COLUMN actor_type varchar(20)`, e da mesma forma `origin varchar(100)`, `user_agent varchar(200)`, `result varchar(10)` e `result_reason varchar(20)`. Todas nuláveis e sem default; o `ADD COLUMN` não dispara o trigger de UPDATE.
2. `ck_audit_log_actor_type_valido`: `actor_type IS NULL OR actor_type IN ('usuario','anonimo','sistema','servico','seed','cli_admin')`.
3. `ck_audit_log_result_valido`: `result IS NULL OR result IN ('success','failure','denied')`.
4. `ck_audit_log_result_reason_valido`: o valor pertence à lista do R4.1, e `result_reason` é obrigatório quando `result IN ('failure','denied')`.
5. `ck_audit_log_usuario_tem_id`: `actor_type IS DISTINCT FROM 'usuario' OR actor_user_id IS NOT NULL`.

### `0013_02_audit_log_origem_obrigatoria` (T7)
1. `ck_audit_log_origem_obrigatoria CHECK (actor_type IS NOT NULL AND result IS NOT NULL) NOT VALID`.
   - O `NOT VALID` deixa as linhas antigas de fora e confere todo INSERT novo (R1.5, R1.6).
   - A constraint **nunca** é validada (`VALIDATE CONSTRAINT`), e o arquivo SQL diz isso.
   - O `pg_dump` grava constraints `NOT VALID` à parte dos dados e o `pg_restore` as recria sem validar. O teste do R9.4 comprova isso.

### `0013_03_db_change_log_imutavel` (T10)
Roda em `SET LOCAL ROLE sgs_owner`, como a `0011_07`:
1. Função `db_change_log_somente_insercao()`, plpgsql, `SET search_path = pg_catalog, public`, com `RAISE EXCEPTION 'db_change_log é somente inserção: % bloqueado', TG_OP`. Não é SECURITY DEFINER.
2. `REVOKE EXECUTE … FROM PUBLIC`, como na `0011_09/16`.
3. `CREATE TRIGGER trg_db_change_log_somente_insercao BEFORE UPDATE OR DELETE ON db_change_log FOR EACH ROW`. No PG17, o trigger de linha da mãe é clonado para as partições existentes (inclusive a `DEFAULT`) e para as futuras. Por isso vale também para UPDATE e DELETE feitos direto numa partição (R6.1).
4. `CREATE TRIGGER trg_db_change_log_bloqueia_truncate BEFORE TRUNCATE ON db_change_log FOR EACH STATEMENT`.
5. Um bloco `DO` (um comando só) cria o trigger de TRUNCATE em cada partição existente, inclusive a `DEFAULT`. É necessário porque o `TRUNCATE` direto numa partição não aciona o trigger da mãe (R6.2).
6. `CREATE OR REPLACE PROCEDURE sp_ensure_monthly_partitions`: o mesmo corpo da `0011_08`, mais o `CREATE TRIGGER` de TRUNCATE em cada partição criada e o `ALTER TABLE … ENABLE ALWAYS TRIGGER` desse trigger (R6.4, R6.8).
7. **`ENABLE ALWAYS` (R6.8, P7).** `ALTER TABLE … ENABLE ALWAYS TRIGGER …` em:
   - `audit_log_bloqueia_update_delete` e `audit_log_bloqueia_truncate`, os triggers da `0001_base`, alterados aqui sem mexer na migração antiga;
   - `trg_db_change_log_somente_insercao` e `trg_db_change_log_bloqueia_truncate`, na mãe e em cada partição existente;
   - `trg_registry_change_log` em `health_units`, `equipments` e `services`.
   Para os triggers de linha clonados nas partições, a T10 confere `tgenabled = 'A'` partição por partição. Se o `ALTER` feito na mãe não se propagar no PG17, um bloco `DO` aplica o mesmo comando em cada partição.
   O `ALTER TABLE … ENABLE ALWAYS` em `audit_log` e nas tabelas do cadastro exige ser dono da tabela, por isso esses passos rodam com o papel que fez as migrações (sem `SET ROLE`), como os passos 07 a 09 da `0011_07`.

O INSERT de `trg_registry_change_log` (SECURITY DEFINER, dono `sgs_owner`) não passa por esses triggers, que tratam só UPDATE, DELETE e TRUNCATE (R6.3).

**Sem hash encadeado no `db_change_log`** (R6.7). Ele exigiria uma trava global serializando toda escrita no cadastro, inclusive o SQL direto que o log quer capturar, e não protegeria contra o dono, que desliga o trigger. A correlação com a trilha é pelo `txid`.

### `0013_04_vw_unit_history_resultado` (T13)
`CREATE OR REPLACE VIEW vw_unit_history WITH (security_invoker = true) AS SELECT …`:
- **Colunas:** as 14 da 011, na mesma ordem, seguidas, no fim, de `l.actor_type`, `l.origin`, `l.result` e `l.result_reason`.
- **Filtro:** `WHERE l.action NOT LIKE 'auth.%' AND l.action <> 'acesso.negado' AND l.action NOT LIKE 'auditoria.%'`.
- **O que não muda:** os mesmos `JOIN` e o mesmo `security_invoker`.

O `CREATE OR REPLACE VIEW` mantém o dono e os privilégios (o `REVOKE` da `0011_04/03` continua valendo) e só aceita colunas novas no fim, que é exatamente o que se acrescenta.
- A view **não** ganha `ip`, `user_agent`, `session_id`, `request_id`, `prev_hash` nem `hash` (R8.6).
- Os arquivos da `0011_04` ficam como estão, como registro histórico.
- A 011 recebe só uma nota de referência no design § `vw_unit_history`.

## Fluxo
### Origem do ator (R1, R3)
- `src/core/origem.py` (novo): `origem_da_requisicao(request) -> Origem(ip, user_agent, request_id)`.
  - **IP:** sai de `request.client.host`, já tratado pelo `ProxyHeadersMiddleware` do uvicorn, e é validado com `ipaddress`.
  - **UA:** o cabeçalho `User-Agent`, sem caracteres de controle, cortado em 200.
- `ator_da_requisicao` (`access/api/deps.py`) e `_origem` (`identity/api/auth.py`) passam a usar esse helper.
- O `Ator` ganha `tipo`, `origem` e `user_agent`. Os valores por caminho de gravação:

  | Caminho | `tipo` | `origem` |
  |---|---|---|
  | API (padrão) | `usuario` | `api` |
  | seed | `seed` | `sgs-admin seed demo` |
  | `create-user` | `cli_admin` | `sgs-admin create-user` |

- No `_auditar` de `login.py`, o tipo é `anonimo` quando o usuário não foi encontrado, `sistema` no `auth.locked` e `usuario` nos demais casos.
- Os papéis do `auth.login` vêm da porta `PapeisDoUsuario` (`identity/domain/ports.py`), ligada em `main.py`. O identity não importa o access (o import-linter garante).
- Os eventos `auth.*` antigos têm o UA em `metadata.user_agent`; os novos o guardam só na coluna.

### Proxies confiáveis e cabeçalhos (R3.1 a R3.3, R3.7)
- `docker/compose.yml`:
  - rede `borda` (proxy e api), com `ipam.config.subnet: ${SGS_BORDA_SUBNET:?defina SGS_BORDA_SUBNET (ver .env.example)}`;
  - o proxy tem IP fixo na `borda`: `ipv4_address: ${SGS_BORDA_PROXY_IP:?defina SGS_BORDA_PROXY_IP}` (por convenção, o último endereço útil da subnet, `.14` numa `/28`; o `.1` é o gateway da bridge). *Ajuste da implementação (013/T4, 11/11/2026):* o `.2` previsto antes colidia com a API, que é criada antes do proxy e recebe do Docker o primeiro endereço dinâmico livre;
  - rede `dados` (db, db-certs e api), com subnet escolhida pelo Docker;
  - a api fica nas duas, e o proxy só na `borda`;
  - `api.environment.FORWARDED_ALLOW_IPS: ${SGS_BORDA_PROXY_IP}/32` (D1). **Nem a subnet nem o gateway são confiáveis.** Sem isso, um processo no host alcançaria a API pelo IP da bridge, com origem no gateway, e escolheria o IP registrado.
- O `CMD` do `Dockerfile` deixa de ter `--forwarded-allow-ips "*"`. O uvicorn lê `FORWARDED_ALLOW_IPS` do ambiente (verificado em `uvicorn/config.py:363`, versão 0.54.0) e aceita CIDR (`_TrustedHosts`). Sem a variável, ele confia só em `127.0.0.1` e `::1`.
- **Cabeçalhos tratados (B3):** o `ProxyHeadersMiddleware` do uvicorn 0.54.0 só interpreta `X-Forwarded-For` (para o IP) e `X-Forwarded-Proto` (para o esquema), e só quando a conexão vem de um proxy confiável. Ele **não** trata `X-Real-IP` nem `Forwarded`, e a aplicação também não os lê. Esses cabeçalhos nunca são fonte de IP (R3.2). O teste de R3.2 mostra que eles não têm efeito, não uma proteção feita pela aplicação.
- O Caddy continua sem `trusted_proxies`, então descarta o `X-Forwarded-For` vindo do cliente. **Limitação documentada (P3):** um proxy ou balanceador antes do Caddy fica fora do escopo acadêmico. Se existir, todos os eventos registrariam o IP dele até o Caddy ganhar `trusted_proxies` para esse endereço.

**Subnets por stack (M1).** Proposta da faixa `10.231.0.0/16` (P8), fora dos pools padrão do Docker (`172.17.0.0/12` e `192.168.0.0/16`), em blocos `/28`:

| Stack | Projeto compose | `SGS_BORDA_SUBNET` |
|---|---|---|
| Desenvolvimento (valor do `.env.example`) | padrão (`docker`) | `10.231.1.0/28` (proxy `10.231.1.14`) |
| Stacks locais adicionais (por exemplo `sgs-local`, `sgs-api`) quando forem recriados por quem os opera | os seus | `10.231.2.0/28`, `10.231.3.0/28`; cada operador escolhe e registra no próprio `.env` |
| `tests/e2e/test_frontend_entrega.py` | `sgs-api-e2e-front` | `10.231.10.0/28` |
| `tests/e2e/test_tls_banco.py` | `sgs-api-e2e-tls` | `10.231.11.0/28` |
| `tests/e2e_front/conftest.py` | `sgs-api-e2e-front-ui` | `10.231.12.0/28` |
| `tests/e2e/test_auditoria_proxy.py` (novo) | `sgs-api-e2e-auditoria` | `10.231.13.0/28` |

- Em todas as suítes, o proxy usa o último endereço útil da sua subnet (`.14`).
- As constantes dos testes ficam num módulo comum (`tests/e2e/redes.py`). Cada suíte aceita uma subnet alternativa pela variável `SGS_E2E_SUBNET_<SUITE>` (por exemplo `SGS_E2E_SUBNET_AUDITORIA=10.231.40.0/28`) (P8).
- Antes do `up`, cada suíte consulta as redes com `docker network ls` e `docker network inspect`, só leitura. Se a subnet escolhida já estiver em uso, a suíte para com `pytest.skip` e uma mensagem que diz qual rede ocupa a faixa e qual variável usar. Nenhuma rede existente é alterada.
- O `:?` no compose impede que dois stacks subam em silêncio com a mesma subnet padrão.
- Os stacks locais de hoje (`sgs-local` em `172.19.0.0/16`, `sgs-api` em `172.18.0.0/16`) não são tocados e não se sobrepõem à faixa proposta. Só passam a precisar da variável quando forem recriados.

### Falhas de negócio (R4.3 a R4.8)
Sequência em `_sessao_de_negocio`:
1. **Rollback.** A exceção sai do `async with sessoes() as s, s.begin()`. O SQLAlchemy desfaz a transação de negócio e devolve a conexão, e nenhuma trava fica presa.
2. **Transação independente.** Uma sessão nova (`estado.sessoes()` + `begin()`) grava `operacao.falhou` com `registrar` e faz commit. Ela não compartilha conexão nem transação com a de negócio. É o mesmo padrão de `_auditar_em_transacao_propria`, que já atende o `AcessoNegado`.
3. **Erro original.** O mesmo objeto de exceção é relançado (`raise`), e os handlers devolvem o mesmo status e o mesmo `problem+json` de hoje.

```
SELECIONADOS = (Conflict, PreconditionFailed, PreconditionRequired, DomainValidationError)

try:
    async with estado.sessoes() as s, s.begin():
        yield s
except AcessoNegado as negacao:            # 403 de permissão: só acesso.negado (como hoje)
    await _auditar_em_transacao_propria(request, usuario, negacao)
    raise
except SELECIONADOS as erro:               # 409, 412, 428, 422 de domínio
    await _registrar_falha_sem_mascarar(request, usuario, erro, categoria=_categoria(erro))
    raise
except (AppError, StarletteHTTPException, RequestValidationError):
    raise                                   # 401, 403 sem ser AcessoNegado, 404, 429, 422 de schema
                                            # e qualquer AppError não selecionado: sem operacao.falhou
except Exception as erro:                   # 500: só o que não é erro HTTP nem de aplicação
    await _registrar_falha_sem_mascarar(request, usuario, erro, categoria="erro_interno")
    raise

async def _registrar_falha_sem_mascarar(request, usuario, erro, *, categoria):
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    if getattr(erro, "auditada", False):
        return
    try:
        async with estado.sessoes() as nova, nova.begin():
            await registrar(
                estado.auditoria(nova),            # mesma fábrica do AcessoNegado
                acao="operacao.falhou",
                ator=ator_da_requisicao(request, usuario),
                entidade=_entidade_do_caminho(request),       # só se for inequívoca
                metadados=metadados_de_falha(request, erro),  # lista fechada (domínio)
                resultado="failure",
                categoria=categoria,
            )
        _marcar_auditada(erro)            # se a exceção aceitar o atributo
    except Exception:
        _error_log.error(
            "auditoria_falha_nao_registrada",
            rota=_template(request),
            status=_status(erro),
            codigo=_codigo(erro),
            request_id=request.state.request_id,
        )
        # não relança: quem sai é o erro original (raise do bloco de fora)
```

A ordem dos `except` importa:
- `AcessoNegado` é subclasse de `Forbidden` (`access/application/autorizacao.py:72`) e vem antes.
- Os selecionados vêm antes do ramo genérico de `AppError`.
- O `Exception` final só recebe o que não é `AppError`, `HTTPException` nem `RequestValidationError`, como `RuntimeError` ou um erro do driver que nenhum repositório converteu.

Por isso, um `NotFound`, um `Unauthorized`, um `TooManyRequests` ou um `Forbidden` comum **não** viram `erro_interno` (R4.6). Os erros de unicidade já chegam como `Conflict`, porque o repositório converte o `IntegrityError` (`registry/infrastructure/repository.py:188`).

O 422 de schema **chega** à dependência como `RequestValidationError`: no FastAPI 0.142.2, `solve_dependencies` abre a dependência `yield` e acumula os erros, que são levantados depois (`fastapi/routing.py`, `get_request_handler`). Ele cai no ramo sem registro. O 401 de `CurrentUser` acontece antes, e a dependência nem chega a abrir. Os dois casos caem no ramo sem registro.

**Metadata em lista fechada (R4.4).** Uma função pura do domínio, `metadados_de_falha`, monta a metadata a partir de valores já classificados, nunca de `str(erro)`. Ela recusa qualquer chave fora da lista:

| Chave | Origem | Restrição |
|---|---|---|
| `metodo` | `scope["method"]` | só `POST`, `PUT`, `PATCH` ou `DELETE` |
| `rota` | `scope["route"].path` | template declarado, sem valores |
| `status` | `type(erro).status`, ou 500 | inteiro |
| `codigo` | mapa fixo | ver abaixo |
| `campos` | `FieldError.campo` de `erro.errors` | até 20 nomes, cada um com `[A-Za-z0-9_.]{1,50}`; os que não casarem são descartados |

Mapa fixo de `codigo`:

| Exceção | `codigo` |
|---|---|
| `Conflict` | `conflito` |
| `PreconditionFailed` | `precondicao_falhou` |
| `PreconditionRequired` | `precondicao_ausente` |
| `DomainValidationError` | `validacao_dominio` |
| ramo do 500 | `erro_interno` |

- **Entidade inequívoca.** Rotas `/unidades/{id}…` geram `("unidade", id)` quando `id` é um UUID válido. `/equipamentos/{equipamento_id}` e `/servicos/{servico_id}` geram o tipo do item. `/referencias/{tipo}/{id_}` gera `("referencia", "{tipo}:{id_}")`. `/admin/atribuicoes/{id_}` gera `("atribuicao", id_)`. Uma rota sem identificador no caminho (`POST /unidades`, por exemplo) fica sem entidade e aparece só na trilha geral.
- **Fica proibido (R4.5):** `FieldError.mensagem`, `erro.titulo`, `erro.detail`, valores do corpo ou do caminho além do id, cabeçalhos, cookies, query string, pilha de chamadas e SQL.
- **Rotas de autenticação:** já gravam as próprias falhas e não usam a `SessaoDeNegocio`, então não há duplicidade (R4.7).

### Verificação (R5.1 a R5.5, R5.11)
`verificar_cadeia(usuario, de, ate, ancora)`:
1. Abre **uma** transação `REPEATABLE READ READ ONLY` (`execution_options(isolation_level="REPEATABLE READ", postgresql_readonly=True)`, por uma fábrica de sessões de leitura consistente em `app.state`). Em `REPEATABLE READ`, o PostgreSQL fixa a foto do banco no primeiro comando, e todas as leituras seguintes veem essa mesma foto.
2. Na mesma transação:
   - lê `audit_chain_head.last_hash`;
   - percorre os lotes por `id`, como hoje, guardando `ultimo_id` e `hash_final`;
   - com âncora, lê o hash do evento de menor `id` (para `cadeia_confere`) e o hash do evento `ancora.id` (para `ancora_confere`).
3. Compara, com divergência levando a `integra=false` e ao motivo:
   - **cadeia:** recálculo de cada evento e conferência do `prev_hash`, como hoje;
   - **cabeça**, só sem período: `cabeca_confere = (hash_final ou GENESIS) == last_hash`, com motivo `"o fim da cadeia não confere com audit_chain_head"`;
   - **âncora:** `cadeia_confere = (hash do primeiro evento == ancora.cadeia_id)` e `ancora_confere = (hash do evento ancora.id == ancora.hash)`. Um id inexistente conta como `false`.
4. Encerra a transação de leitura.
5. Grava `auditoria.verificada` (`result=success`, metadata `{integra, verificados, ultimo_id, cabeca_confere, cadeia_confere, ancora_confere, primeiro_evento_divergente}`) numa transação **separada** (R7.3, R5.11).

**Escrita concorrente (R5.11).**
- Os escritores não esperam o verificador: a leitura não trava nada, e a trava de `audit_chain_head` (`SELECT … FOR UPDATE`) só disputa com outros escritores.
- Um evento confirmado depois da foto não é visto. A cabeça lida também é a da foto, então ela confere e não há falso positivo.
- `verificados` e `ultimo_id` descrevem a cadeia no instante da foto. A verificação seguinte inclui os eventos novos, inclusive o próprio `auditoria.verificada`.
- Custo: uma transação longa segura o horizonte do VACUUM enquanto dura. O lote de 1.000 eventos e a leitura sem trava mantêm o custo baixo, e uma verificação de 2 anos de trilha deve ser medida na T8.

Outras regras:
**Verificação offline (R5.12, D2).** `sgs-admin auditoria verificar [--ancora arquivo.json]` (`src/tools/sgs_admin.py`):
- chama o mesmo caso de uso `verificar_cadeia`, numa conexão `DATABASE_URL` aberta pela própria CLI, na mesma transação `REPEATABLE READ READ ONLY`;
- **não** grava `auditoria.verificada` nem nada mais. Isso permite verificar uma cópia restaurada em outro servidor sem alterá-la e sem confiar na API de produção;
- imprime o `VerificacaoOut` em JSON e termina com código 0 se a cadeia estiver íntegra e com 1 se não estiver. Arquivo de âncora inválido ou ilegível dá código 2.

Para isso, `verificar_cadeia` passa a receber um parâmetro `registrar_execucao` (verdadeiro na API, falso na CLI). A regra fica num lugar só.

- Uma remoção no meio já é detectada hoje, porque o `prev_hash` do evento seguinte deixa de conferir.
- A remoção do primeiro evento também é detectada, porque o novo primeiro tem `prev_hash` diferente de GENESIS e a `cadeia_id` muda.
- Buracos no `id` não são prova de nada: a IDENTITY pula valores quando há rollback.

### Âncora externa (R5.4, R5.7 a R5.10)
**Formato (versão 1).** É gerado por `sgs-admin auditoria ancorar` (`src/tools/sgs_admin.py`), numa transação `REPEATABLE READ READ ONLY` com `DATABASE_URL`:

```json
{"versao": 1, "cadeia_id": "<hash do evento de menor id>", "id": 1234, "hash": "<hash do evento 1234>",
 "total": 1234, "instante": "2026-11-11T18:00:00.000000Z", "banco": "<current_database()>"}
```

- **`cadeia_id` (M2)** identifica a cadeia. O hash do primeiro evento depende do conteúdo e do instante, com microssegundos, desse evento:
  - bancos com o mesmo nome (`sgs`) em stacks diferentes, mesmo com o mesmo seed rodado em momentos diferentes, têm `cadeia_id` diferentes;
  - uma restauração em outro servidor preserva a `cadeia_id`, porque é a mesma cadeia;
  - uma cópia (`TEMPLATE` ou restauração) que depois diverge continua com a mesma `cadeia_id`, mas as âncoras de um ramo não conferem com os eventos posteriores do outro;
  - reescrever ou apagar o primeiro evento muda a `cadeia_id`, e isso é detectado.
- **O `system_identifier` do cluster não é usado.** Ele muda numa restauração em outro servidor e é o mesmo para todos os bancos do cluster.
- **`banco`** é só informativo.
- **Cadeia vazia:** o comando não emite âncora e termina com código 2 e a mensagem "cadeia vazia: nada a ancorar".
- O comando não grava nada no banco nem em arquivo no servidor (R5.4), e a âncora não leva dado pessoal (R5.9).

**Procedimento manual (R5.8)**, detalhado em `docs/operacao/ancora-auditoria.md` (T15):

| Etapa | Regra |
|---|---|
| Geração | Feita pelo proprietário, que acumula a função (P1). Frequência: diária enquanto houver atividade relevante (P2). Obrigatória antes e depois de migrações e de mudanças estruturais, e antes de cada backup. |
| Armazenamento | Duas cópias, separadas dos backups (P1): uma local, fora do banco e dos containers; outra externa, num armazenamento privado na nuvem independente do ambiente local. Um arquivo novo por âncora (`ancoras/AAAA/MM/AAAA-MM-DDTHHMMSSZ.json`). As âncoras não vão para o repositório do projeto. |
| O que não vale | O mesmo servidor ou volume do banco; o mesmo banco, inclusive outra tabela; o backup do banco como única cópia; o servidor da API. Quem controla esses lugares reescreve a cadeia e a âncora juntas (R5.7). |
| Controle de acesso | Só o proprietário escreve e lê. **Não há segregação de funções** neste projeto (P6): a mesma pessoa administra o banco e guarda as âncoras. Esse é um risco aceito e documentado, não uma separação simulada. |
| Histórico | Nada é sobrescrito nem apagado; cada âncora é um registro novo, e são as antigas que permitem detectar reescrita de períodos antigos. Autoria e instante da guarda ficam no commit ou na mensagem (R5.9). |
| Uso | Na rotina, verificar com a âncora mais recente, pela tela ou pela CLI. Antes da entrega final, verificar também com uma âncora antiga. Sempre informar `cadeia_id`. |
| Recuperação | Perda da cópia principal: reconstruir a partir da secundária. Perda das duas: verificar a cadeia e, se estiver íntegra, gerar uma âncora nova na hora e registrar que a garantia contra reescrita recomeça a partir dela. Depois de uma restauração: ver § Backup e restauração. |
| Divergência | Não "corrigir" a cadeia nem reescrever eventos. Fazer um backup imediato do estado atual como evidência, registrar o resultado da verificação e o evento divergente, e comunicar o dono, o Auditor e o encarregado de dados. |

**Manual agora, automatizada depois (R5.10).** Esta spec cobre só a CLI com guarda humana. Uma rotina futura, com spec própria e citada no ADR-0012 como trabalho futuro, teria de garantir:
- execução agendada fora do servidor do banco;
- publicação num destino com credencial só de acréscimo (bucket com retenção de objeto, ou repositório com token que não reescreve histórico), independente das credenciais do banco;
- alerta quando falhar;
- opcionalmente, carimbo de tempo de terceiro (RFC 3161).

### Limites contra superusuário (R6.6, R6.7; M3)
| Ação de quem tem privilégio | Quem pode | O que deixa de atuar | O que ainda detecta |
|---|---|---|---|
| `ALTER TABLE … DISABLE TRIGGER` ou `DROP TRIGGER` | dono da tabela, superusuário | o trigger desligado ou removido | `audit_log`: a verificação (hash, `prev_hash`, cabeça) e a âncora. `db_change_log`: nada no próprio log; só o `audit_log` mostra as operações feitas pela API |
| `DETACH PARTITION` ou `DROP TABLE` de partição do `db_change_log` | dono (`sgs_owner`), superusuário | as linhas da partição somem da tabela-mãe | um mês faltando em `GET /auditoria/banco/particoes`; o `audit_log` continua com os eventos da API |
| `SET session_replication_role = replica` | superusuário, ou um papel com `GRANT SET ON PARAMETER` (PG15+), que não existe nesta base | **não** contorna os triggers marcados `ENABLE ALWAYS` (R6.8): imutabilidade de `audit_log` e `db_change_log` e `trg_registry_change_log`. **Ainda** contorna os triggers comuns: `trg_roles_protect_system`, `updated_at`, versão e os triggers internos de chave estrangeira | os triggers de imutabilidade e o de log continuam atuando. Para o resto, só o log do servidor PostgreSQL (`log_statement = 'all'`) ou `pgaudit` registrariam o `SET`, e os dois ficam fora do escopo |
| Reescrever a cadeia e a cabeça de forma coerente | superusuário | — | só a âncora externa anterior à reescrita |

- `ENABLE ALWAYS` **não** impede o dono ou o superusuário de desabilitar o trigger explicitamente (`ALTER TABLE … DISABLE TRIGGER`). Só obriga essa ação a ser uma DDL explícita, em vez de um `SET` de sessão (P7).
- Sem *event trigger* contra DROP ou DETACH (P5): o dono e o superusuário continuam podendo alterar a estrutura.
- O `sgs_app` não consegue mudar `session_replication_role`; a T10 testa isso (R6.5).

### Histórico da unidade (R8.6 a R8.8; H4)
**Histórico de negócio da unidade e trilha de auditoria são coisas diferentes:**

| | Histórico da unidade | Trilha de auditoria |
|---|---|---|
| Fonte | `vw_unit_history` (`security_invoker`) | `audit_log` |
| Quem vê | `auditoria:read` no escopo da unidade, inclusive o Gestor de Unidade | `auditoria:read` global; eventos de acesso só com `read_acessos` |
| Conteúdo | eventos de negócio da unidade, inclusive equipamentos e serviços vinculados, e `operacao.falhou` da unidade | todos os eventos, inclusive acesso (`auth.*`, `acesso.negado`) e auditoria (`auditoria.*`) |
| Origem técnica | tipo de ator, origem, resultado e categoria; **sem** IP, UA, sessão, request id nem hash | tudo; IP, UA e sessão só no detalhe e com `read_acessos` |
| Finalidade | o que aconteceu com a unidade | apuração e controle |

**Menor alteração possível.**
- Uma migração recria a view com quatro colunas a mais no fim e um filtro por ação (§ `0013_04`).
- `unit_history.sql` passa a selecionar as colunas novas.
- O índice `ix_audit_log_entity` continua atendendo, porque o filtro por ação é residual.
- Nenhuma tabela nova, nenhuma permissão nova.

**Falhas da unidade.** Uma falha só entra no histórico se tiver a entidade `("unidade", id)`, que vem só do caminho da rota (§ Falhas de negócio).
- O usuário do escopo vê método, rota, status, código e nomes de campos, sem valores (R4.4, R4.5).
- Na ficha, ela aparece como "Tentativa sem sucesso", com a categoria.

**Dashboard (R8.8).** `summary_changes.sql`, `changes_by_period.sql` e `recent_changes.sql` (spec 009) passam a filtrar `AND (result IS NULL OR result = 'success')`. Os eventos antigos (`result` nulo) eram todos alterações efetivas, depois que a view passou a excluir o `acesso.negado`. A 009 não muda de texto: "alterações" continua significando alterações.

### Detalhe e RBAC (R7.4, R8.2, R8.6)
- `detalhar_evento` mantém o 404 para evento de acesso quando o usuário não tem `read_acessos`.
- Sem `read_acessos`, a resposta traz `ip=None`, `user_agent=None`, `sessao_id=None` e `origem_restrita=True`. `request_id`, `prev_hash` e `hash` continuam visíveis.
- A consulta grava `auditoria.evento_consultado` (`entidade=("evento_auditoria", id)`) na transação da própria consulta.
- **`auditoria.evento_consultado` é evento de acesso (D3).** `_e_de_acesso` (`consultar.py`) e o filtro de `audit_events.sql` passam a tratar `auth.*`, `acesso.negado` e `auditoria.evento_consultado` como eventos de acesso. Sem `read_acessos`, eles não aparecem na lista e dão 404 no detalhe. O `auditoria.verificada` continua visível para todos com `auditoria:read` global.
- **Acoplamento com o DF9 (R8.9, P4).** A matriz de `0003_access.py` concede `auditoria:read_acessos` só a `ADMIN_TI` e `AUDITOR`. O `ADMIN_TI` não tem `auditoria:read` e recebe 403 nas rotas da trilha. Um teste trava essa matriz: se o DF9 conceder `read_acessos` a outro papel sem emendar esta spec, ele falha.
- **Contorno (R8.6):**
  - `EventoOut` (lista e histórico) não tem os campos de origem;
  - `audit_events.sql` e `unit_history.sql` não selecionam essas colunas;
  - a `vw_unit_history` não as tem;
  - o log do banco e as partições não as contêm.
  A T12 testa isso com um valor-sentinela de UA, percorrendo todas as rotas GET que o Gestor de Dados alcança.

### Política de leitura auditável (R7.5)
| Leitura | Auditada? | Motivo |
|---|---|---|
| Detalhe de evento da trilha | Sim (`auditoria.evento_consultado`, classificado como evento de acesso) | expõe IP, UA e sessão de terceiros; volume baixo; não revela ao Gestor a atividade do Auditor |
| Verificação da cadeia | Sim (`auditoria.verificada`) | ato de controle; o resultado precisa de evidência |
| Lista da trilha, histórico da unidade, log do banco, partições | Não | não expõem dados de origem; volume alto em navegação |
| Leituras do cadastro (unidades, dashboard) | Não, nesta spec | o único dado pessoal é `manager_name`; fica para uma spec própria, com finalidade definida pelo encarregado |
| JWKS, health | Não | públicas e sem dado pessoal |

### Mapa de cobertura (R7.1, R7.2)
`tests/integration/audit/cobertura.py` guarda o mapa `(método, template) → ação de sucesso`. A lista de partida são as rotas de escrita do diagnóstico:
- login, `mfa/confirm`, `mfa/verify`, logout;
- atribuições;
- unidades;
- vínculos de equipamento e de serviço;
- referências;
- verificação.

Exceções justificadas:
- `POST /auth/mfa/enroll`: só emite o QR do segredo pendente, sem estado durável; o evento de matrícula é o `auth.mfa_enrolled`, no `confirm`.
- `POST /auth/refresh` com sucesso: é rotação de token, com volume alto, e o fato relevante (`auth.login`) já está registrado. O `auth.refresh_reuse` é auditado.
- Escrita sem mudança (PATCH idêntico): não há fato a registrar.

### Tela (R1.5, R2, R8)
- `ui/format.js`: `fmtDataHora` ganha `second: '2-digit'` e o sufixo ` (UTC−03:00)`; `fmtInstante(iso)` devolve o ISO sem conversão; o `DATA_HORA_SEGUNDOS` duplicado em `views/unidade.js` passa a usar o helper.
- `views/historico.js`:
  - a linha da trilha abre um `<dialog>` com `GET /auditoria/eventos/{id}`;
  - os campos restritos aparecem como "restrito ao Auditor", e os nulos de eventos antigos como "não registrado";
  - nova coluna "Resultado".
- `views/unidade.js` (histórico da ficha): chip de resultado, `operacao.falhou` como "Tentativa sem sucesso" e horário com segundos.
- `#/cadeia`: mostra `verificados`, `ultimo_id`, `hash_final`, `cabeca_confere`, `cadeia_confere` e `ancora_confere`, com campos opcionais "Âncora: cadeia_id / id / hash". A divergência continua em `role="alert"`.
- Tudo dentro de `tests/architecture/test_frontend_estatico.py`.

### Backup e restauração (R9.1 a R9.6; H3)
Decisões do proprietário de 11/11/2026 (P1, P2). São metas e procedimentos acadêmicos, não garantias de operação empresarial. Não há agendador nem serviço de backup.

| Item | Proposta |
|---|---|
| Formato | `pg_dump -Fc` (formato custom, comprimido) do banco inteiro, **com** donos e ACLs (sem `--no-owner` nem `--no-privileges`), mais `pg_dumpall --roles-only --no-role-passwords` para recriar `sgs_app`, `sgs_owner` e os logins. As senhas dos logins são redefinidas na restauração e nunca vão para o backup nem para o repositório. Cada arquivo tem um `sha256sum`. |
| Frequência | Diária enquanto houver desenvolvimento ativo, mais um backup extra antes de migrações e de mudanças estruturais importantes (P2). Uma âncora é gerada logo antes de cada backup (§ Âncora externa). |
| Local e independência | Cópia principal em armazenamento local separado do banco e dos containers. Segunda cópia em armazenamento privado na nuvem, independente do ambiente local (P1). O dump tem dados pessoais e segredos cifrados, por isso fica em local de acesso restrito e **nunca** no Git. As âncoras ficam separadas dos backups. **Retenção:** 7 backups diários, mais os backups dos marcos acadêmicos, que são preservados (P2). |
| Responsáveis | O proprietário, único responsável, acumula as funções de operador de backup, de verificador e de guardião das cópias (P1). A ausência de segregação é risco aceito (P6). |
| RPO e RTO | RPO de 24 h e RTO de até 4 h, como metas (P2). O ensaio mede o tempo real. |
| Ensaio | Um ensaio completo de restauração antes da entrega final, em banco descartável e sem tocar nos stacks existentes, com as evidências do R9.6 (R9.7). |

**Restauração em banco novo**, passo a passo, a ser detalhado em `docs/operacao/backup-restauracao.md`:
1. Conferir o `sha256sum` do arquivo.
2. Subir um PostgreSQL 17 novo e vazio, sem dados de produção e sem ligação com o banco de origem.
3. Recriar os papéis com o arquivo de `--roles-only` e definir senhas novas, fora do repositório.
4. Criar o banco com o mesmo dono da origem e rodar `pg_restore --exit-on-error --single-transaction`.
5. Conferir que a revisão do Alembic é a esperada (`alembic current`). Nenhuma migração é aplicada no banco restaurado como parte da restauração.
6. **Conferir o catálogo:**
   - constraints de `audit_log`, com `ck_audit_log_origem_obrigatoria` presente e `convalidated = false`;
   - triggers de `audit_log`, `db_change_log` e de cada partição, presentes e habilitados;
   - funções SECURITY DEFINER com `search_path` fixo;
   - privilégios: `has_table_privilege('sgs_app', …)` igual ao da origem, e o `sgs_app` sem UPDATE, DELETE ou TRUNCATE na trilha;
   - lista de partições.
7. **Verificar a cadeia** com `sgs-admin auditoria verificar --ancora <última âncora anterior ao backup>`, apontando `DATABASE_URL` para o banco restaurado. Não é preciso subir a API, e nada é gravado. O esperado é código 0, com `integra`, `cabeca_confere`, `cadeia_confere` e `ancora_confere` verdadeiros.
8. As âncoras posteriores ao backup **não** vão conferir. Isso marca a janela de perda: registrar como incidente de perda de dados, não como adulteração.
9. Gerar uma âncora nova do banco restaurado antes de abri-lo para uso.

**Evidências (R9.6)**, guardadas junto com as âncoras, em arquivo próprio, sem dado pessoal:
- comandos e horários;
- checksum;
- JSON da verificação e âncora usada;
- saída da conferência do catálogo;
- duração total, comparada com o RTO;
- função de quem executou e de quem conferiu.

**Teste automatizado (R9.4).** Em Testcontainers descartável (§ Estratégia de testes), sem servidor real e sem `sgs-local` ou `sgs-api`:
1. Migrar até `0011_09` e gravar eventos no formato antigo.
2. Migrar até o head e gravar eventos novos.
3. Ancorar e fazer `pg_dump -Fc` dentro do contêiner.
4. Restaurar num banco novo do mesmo contêiner.
5. Conferir os itens 6 e 7 da restauração, e que um INSERT sem tipo ou sem resultado é recusado.

## Segurança
- O evento de falha usa só a lista fechada, e um valor-sentinela no corpo comprova que nada vaza (R4.4, R4.5).
- A falha ao auditar não troca nem esconde o erro original, e o log técnico recebe só rota, status, código e request id (R4.8).
- IP, UA e sessão são dados pessoais (LGPD) e só aparecem no detalhe, para o Auditor (R8.2, R8.6). A finalidade é apurar incidentes.
- O UA é cortado e limpo de caracteres de controle.
- A âncora e as evidências de restauração não têm dado pessoal. O backup tem, e por isso é cifrado e guardado com acesso restrito.
- Nenhum privilégio novo vai para o `sgs_app`.

## Decisões e alternativas
- **Colunas, e não `metadata`:** permitem filtrar, aplicar CHECK e ter um contrato estável.
- **Obrigatoriedade numa migração separada:** junto com as colunas, quebraria toda gravação até os caminhos preencherem os campos.
- **Âncora externa sem chave, e não HMAC** (decisão do usuário, 11/11/2026). O HMAC fica como trabalho futuro no ADR-0012.
- **`cadeia_id` = hash do primeiro evento, e não `system_identifier`:** sobrevive à restauração e distingue bancos com o mesmo nome.
- **Falhas selecionadas** (decisão do usuário, 11/11/2026): 409, 412, 428, 422 de domínio e 500, só em escrita, com exclusão explícita dos demais `AppError` e `HTTPException` antes do ramo do 500.
- **Verificação em `REPEATABLE READ READ ONLY`, e não com trava:** consistente sem bloquear escritores.
- **Subnet obrigatória por stack (`:?`), e não um padrão:** um padrão comum faria dois stacks colidirem em silêncio.
- **Histórico da unidade pela própria view, recriada:** menos mudança do que uma view nova ou uma consulta paralela, e o dashboard continua lendo a mesma fonte.
- **Event trigger contra DROP e DETACH:** não adotado (P5). **`ENABLE ALWAYS`:** adotado (P7), pelo custo mínimo e porque fecha o desvio por `replica`.
- **Confiança no IP fixo do proxy (`/32`), e não na subnet:** a subnet inclui o gateway da bridge (D1).
- **CLI de verificação offline:** a restauração precisa verificar um banco sem API, e a verificação feita só pela API de produção não é evidência independente (D2).

## Riscos
- Se a canonicalização mudar além de "omitir nulos", todo o histórico quebra. O teste de regressão v1 é obrigatório.
- Faixa de subnet colidindo com a rede do host ou com uma VPN: a suíte detecta antes de subir e a variável permite trocar (P8).
- Um 500 com o banco fora do ar faz a gravação da falha falhar também. Fica só o log técnico, e o erro original é devolvido (R4.8).
- Uma verificação longa segura o horizonte do VACUUM.
- A âncora e o backup dependem de procedimento humano. O responsável é um só, então âncora e backup ficam sob o mesmo controle administrativo (risco aceito, P6).
- Proxy ou balanceador adicional antes do Caddy em produção não está coberto (P3).
- O dono ou o superusuário pode apagar ou deixar de gravar entradas do `db_change_log` sem que o próprio log mostre (§ Limites contra superusuário).
- A mudança da view altera o que o Gestor de Unidade vê: some o `acesso.negado` e aparecem as falhas. Isso é intencional (R8.7, decisão do proprietário).

## Estratégia de testes
- **Unidade:**
  - canonicalização: hash v1 e campos novos;
  - domínio do `Ator`;
  - metadata de falha em lista fechada;
  - classificação de exceções: selecionadas, excluídas e 500;
  - helper de origem e `ProxyHeadersMiddleware`;
  - campos de `EventoOut`.
- **Integração** (Testcontainers descartável, `env -u SGS_TEST_DATABASE_URL`):
  - migrações e origem;
  - resultado e falhas, inclusive a falha da própria auditoria;
  - adulteração com `DISABLE TRIGGER USER` e com `session_replication_role = replica`, como superusuário do contêiner;
  - verificação com escrita concorrente;
  - privilégios e limites do `db_change_log`;
  - cobertura das rotas;
  - detalhe com e sem `read_acessos`;
  - privacidade em todas as rotas GET;
  - histórico da unidade e dashboard.
- **Arquitetura:**
  - compose e Dockerfile sem `forwarded-allow-ips "*"`;
  - subnet obrigatória e única por suíte;
  - frontend estático.
- **Lentos** (`slow`, cada um com stack ou contêiner próprio e subnet da tabela de § Proxies confiáveis):
  - XFF falso através do Caddy;
  - backup e restauração;
  - e2e_front do detalhe e do histórico.
- Os nomes exatos estão em `tasks.md` § Matriz. Nada roda em `sgs-local` ou `sgs-api`, e o `make test-all` nunca é usado.
