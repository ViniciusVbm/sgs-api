# 013 · Reforço da trilha de auditoria · Requisitos

- Status: **Aprovado (Vinicius (ViniciusVbm), proprietário e dono único da spec, 11/11/2026)**. G1 registrado pelo agente por autorização expressa do proprietário na sessão de trabalho de 11/11/2026, com aprovação individual pela exceção de `steering/sdd-workflow.md` § Exceção pontual: spec 013. Histórico: redigido por agente em 11/11/2026; revisões 2 e 3 em 11/11/2026 (achados H1 a H4, M1 a M6 e B1 a B4); revisão 4 em 11/11/2026 (decisões P1 a P8, H4, D1, D2, D3 e D7 do proprietário).
- Rastreia:
  - RF-08, RS-05, RS-09;
  - spec 001 (R5.1 a R5.3; emenda da canonicalização: design § Emenda à spec 001);
  - spec 008 (R1 a R4);
  - spec 009 (R2.3, R2.4: contagem de alterações);
  - spec 011 (R4.4, R6, R7; emenda da `vw_unit_history`: design § Histórico da unidade). A 011 deixava fora do escopo a retenção do log do banco; o R9 **amplia** a 011 com uma política sem expurgo, sem contradizê-la;
  - spec 012 (DF9: o acesso a dados de origem fica preso a `auditoria:read_acessos`, R8.9);
  - risco R02 de `docs/governanca/03-registro-de-riscos.md`;
  - lacunas A a I do diagnóstico de 11/11/2026 (design § Diagnóstico de partida).
- Dono humano: Vinicius (ViniciusVbm), proprietário e único responsável pelo projeto, que acumula as funções de operação (§ Decisões do proprietário).

## Contexto
A trilha (`audit_log`, spec 001) e o log do banco (`db_change_log`, spec 011) já existem. A trilha é encadeada por SHA-256, só aceita inserção e pode ser verificada pela API e pela tela. Uma auditoria técnica encontrou nove lacunas:
- **A:** eventos de sistema sem origem explícita.
- **B:** horário mostrado sem segundos e sem fuso.
- **C:** IP aceito de qualquer proxy; User-Agent só nos eventos `auth.*`.
- **D:** não há campo de resultado, e as falhas de negócio se perdem no rollback.
- **E:** a verificação não detecta a remoção do fim da cadeia.
- **F:** o log do banco não tem proteção contra UPDATE, DELETE e TRUNCATE.
- **G:** não há teste sistemático de cobertura.
- **H:** a tela não mostra o detalhe dos eventos.
- **I:** a retenção só existe no papel.

Esta spec fecha essas lacunas sem criar um segundo mecanismo de auditoria e sem reescrever eventos antigos.

## Fora do escopo
- Exportação da trilha (CSV, Excel, PDF): fica para uma etapa futura, separada.
- HMAC ou qualquer chave criptográfica na cadeia. A decisão de 11/11/2026 foi uma âncora externa sem chave (design § Âncora externa).
- Rotina automatizada de âncora, isto é, agendada e com publicação num serviço externo. Aqui a âncora é gerada por CLI e guardada por procedimento humano (R5.10).
- Descarte, expurgo ou arquivamento automático de qualquer registro.
- Particionamento do `audit_log` (decisão da spec 008, design § Retenção).
- Bloqueio de DDL (DROP ou DETACH de partição) por *event trigger* (P5).
- Auditoria genérica de leitura HTTP. A leitura de dados pessoais do cadastro (por exemplo `manager_name`) fica para uma spec própria.
- Extensões de auditoria do PostgreSQL (por exemplo `pgaudit`) e a configuração de log do servidor de produção. O design as cita só como mitigação externa (§ Limites contra superusuário).
- DF9 da spec 012 (Gestor de Dados vendo eventos de acesso): continua bloqueado e não muda.
- Trilha geral no escopo de distrito ou área (T20 da 012).
- Resistência absoluta contra superusuário ou dono das tabelas. Contra eles, a garantia é só de **detecção**, nos limites do design § Modelo de ameaças.

## Histórias e critérios

### R1. Quem: identidade e origem de todo evento (lacuna A)
Como Auditor, quero saber se um evento foi feito por uma pessoa, pelo sistema, por um seed ou por um comando administrativo, para não confundir evento automático com ação humana.

- R1.1 Todo evento gravado a partir desta spec DEVE ter um tipo de ator, entre `usuario`, `anonimo`, `sistema`, `servico`, `seed` e `cli_admin`, e um rótulo de origem (por exemplo `api`, `sgs-admin seed demo`, `sgs-admin create-user`).
- R1.2 SE o tipo de ator for `usuario`, ENTÃO o evento DEVE ter `actor_user_id`. SE o tipo não for `usuario` nem `anonimo`, ENTÃO o sistema NÃO DEVE atribuir o evento a um usuário humano inventado.
- R1.3 A tentativa de login com usuário inexistente DEVE ser gravada com o tipo `anonimo`. O bloqueio automático de conta (`auth.locked`) DEVE ser gravado com o tipo `sistema`, com a conta afetada na entidade.
- R1.4 QUANDO um login termina com sucesso (`auth.login`), o evento DEVE registrar os papéis efetivos do usuário naquele momento.
- R1.5 Os eventos gravados antes desta spec NÃO DEVEM ser alterados para preencher os campos novos. A API (trilha, detalhe e histórico da unidade) DEVE devolvê-los com esses campos nulos, e a tela DEVE mostrá-los como "não registrado".
- R1.6 Depois que todos os caminhos de gravação preencherem tipo de ator e resultado, o banco DEVE recusar evento novo sem eles, sem invalidar as linhas antigas.

### R2. Quando: precisão e fuso na apresentação (lacuna B)
Como Auditor, quero ver o horário com segundos e saber o fuso, para correlacionar eventos sem ambiguidade.

- R2.1 As telas de trilha, de log do banco e de histórico da unidade DEVEM mostrar data e hora com segundos e com o fuso indicado ("UTC−03:00", America/Recife).
- R2.2 O detalhe do evento DEVE mostrar o instante completo em ISO 8601, com microssegundos e deslocamento, exatamente como a API devolve.
- R2.3 O armazenamento DEVE continuar em `timestamptz`, em UTC e com microssegundos. A ordenação DEVE continuar pelo `id`, sem depender da formatação.

### R3. De onde: IP, User-Agent e proteção contra falsificação (lacuna C)
Como Auditor, quero que o IP registrado seja o do cliente, e não um valor que o cliente possa escolher.

- R3.1 A API DEVE aceitar cabeçalhos de encaminhamento apenas do endereço IP fixo do proxy reverso da própria implantação (`/32`). A lista de proxies confiáveis NÃO DEVE ser `*`, NÃO DEVE ser a subnet inteira da rede de borda e NÃO DEVE incluir o gateway da bridge. Um proxy ou balanceador adicional antes do Caddy fica fora do escopo acadêmico (design § Proxies confiáveis).
- R3.2 SE uma requisição chegar de um endereço fora da lista de proxies confiáveis, ENTÃO o IP registrado DEVE ser o endereço da conexão, qualquer que seja o conteúdo de `X-Forwarded-For`, `X-Real-IP` ou `Forwarded`. `X-Real-IP` e `Forwarded` NÃO DEVEM ser fonte de IP em nenhum caso.
- R3.3 QUANDO o cliente enviar `X-Forwarded-For` ao proxy reverso, o IP registrado NÃO DEVE ser o valor enviado pelo cliente.
- R3.4 Todo evento originado de uma requisição HTTP DEVE registrar o User-Agent, limitado a 200 caracteres e sem caracteres de controle. O valor DEVE ser tratado como declaração do cliente, não como prova.
- R3.5 O sistema NÃO DEVE coletar impressão digital do dispositivo nem cabeçalhos além do User-Agent.
- R3.6 A documentação DEVE registrar que o IP é um dado de rede e não basta para identificar a pessoa.
- R3.7 Os stacks descartáveis de teste e os stacks locais NÃO DEVEM disputar a mesma subnet da rede de borda. O compose DEVE recusar subir sem a subnet e o IP do proxy definidos, em vez de usar um padrão comum a todos. Antes de subir containers, cada suíte DEVE conferir, só por leitura, se a subnet está ocupada. SE estiver, ENTÃO DEVE usar a subnet alternativa configurada por variável de ambiente ou encerrar com uma mensagem clara, sem alterar redes existentes.
- R3.8 SE uma requisição com `X-Forwarded-For` chegar à API direto de uma origem que não é o proxy (contêiner vizinho ou gateway da bridge), ENTÃO o IP registrado DEVE ser o da conexão.

### R4. Resultado: sucesso, falha e negação (lacuna D)
Como Auditor, quero saber se a operação deu certo, falhou ou foi negada, e por quê, sem que a falha se perca no rollback.

- R4.1 Todo evento novo DEVE ter um resultado: `success`, `failure` ou `denied`. Os de `failure` e `denied` DEVEM ter uma categoria: `autenticacao`, `autorizacao`, `validacao`, `conflito`, `precondicao` ou `erro_interno`.
- R4.2 Os eventos `auth.login_failed` e `auth.mfa_failed` DEVEM ter resultado `failure` e categoria `autenticacao`. O `acesso.negado` DEVE ter resultado `denied` e categoria `autorizacao`.
- R4.3 QUANDO uma rota de escrita autenticada (POST, PUT, PATCH, DELETE) terminar por um dos **erros selecionados**, o sistema DEVE gravar **um** evento `operacao.falhou` com resultado `failure`, depois que a transação de negócio tiver sido desfeita, numa transação nova e independente. Os erros selecionados são: 409 (`Conflict`), 412 (`PreconditionFailed`), 428 (`PreconditionRequired`), 422 de regra de domínio (`DomainValidationError`) e 500 (exceção não tratada que não seja erro HTTP nem erro de aplicação). O rollback NÃO DEVE desfazer o evento de falha, e o evento de falha NÃO DEVE manter nenhuma escrita da operação que falhou.
- R4.4 As metadata do evento de falha DEVEM se limitar a uma lista fechada:
  - método;
  - rota declarada (template, sem valores);
  - status;
  - código do erro, de uma lista fixa;
  - nomes dos campos com erro, no máximo 20, cada um com até 50 caracteres no formato `[A-Za-z0-9_.]`.
  A entidade só DEVE ser preenchida quando o identificador do caminho for válido e inequívoco.
- R4.5 O evento de falha NÃO DEVE conter, em nenhum campo:
  - valores enviados ou atuais de campos;
  - mensagens livres de erro ou de exceção;
  - nome de classe de exceção não prevista;
  - pilha de chamadas ou texto de SQL;
  - senhas, tokens, cookies, cabeçalhos ou query string;
  - corpo da requisição ou da resposta.
- R4.6 O sistema NÃO DEVE gravar `operacao.falhou` para:
  - 401;
  - 403, cuja negação de permissão continua registrada só como `acesso.negado` (R4.2);
  - 404;
  - 429;
  - 422 de validação de schema;
  - qualquer outro erro de aplicação ou erro HTTP fora da lista de R4.3;
  - requisições de leitura.
  Um erro fora da lista NÃO DEVE ser classificado como erro interno.
- R4.7 Uma requisição DEVE gerar no máximo um evento de falha. Uma negação já auditada como `acesso.negado` NÃO DEVE gerar também `operacao.falhou`.
- R4.8 SE a gravação do evento de falha falhar, ENTÃO o sistema DEVE:
  - responder ao cliente o erro original, com o mesmo status e o mesmo corpo `problem+json`;
  - registrar no log técnico só a rota, o status, o código do erro e o request id;
  - não tentar gravar de novo na mesma requisição.
- R4.9 Na operação bem-sucedida, o evento e a alteração de negócio DEVEM continuar na mesma transação.

### R5. Integridade verificável do `audit_log` (lacuna E)
Como Auditor, quero que a verificação acuse alteração, remoção no meio e remoção no fim da cadeia, e que exista uma referência fora do banco para conferir.

- R5.1 QUANDO a verificação percorre a cadeia inteira (sem período), o sistema DEVE comparar o hash do último evento encontrado com `audit_chain_head.last_hash`, lidos na mesma visão consistente do banco (R5.11). SE forem diferentes, ENTÃO DEVE responder `integra=false` e o motivo.
- R5.2 A verificação DEVE detectar:
  - evento alterado, inclusive em qualquer um dos campos novos (`actor_type`, `origin`, `user_agent`, `result`, `result_reason`);
  - evento removido no meio;
  - eventos removidos no fim.
  Quando houver um primeiro evento divergente, DEVE apontá-lo.
- R5.3 A verificação DEVE aceitar uma âncora externa opcional `{cadeia_id, id, hash}` e responder:
  - se a cadeia é a mesma: o hash do primeiro evento é igual a `cadeia_id`;
  - se o evento com esse `id` ainda existe com esse `hash`.
- R5.4 O sistema DEVE oferecer um comando administrativo, só de leitura, que emite uma âncora com:
  - versão do formato;
  - `cadeia_id` (hash do evento de menor `id`);
  - `id` e `hash` do último evento;
  - total de eventos;
  - instante em UTC;
  - nome do banco, só informativo.
  O comando NÃO DEVE gravar a âncora no banco nem no servidor. SE a cadeia estiver vazia, ENTÃO o comando NÃO DEVE emitir âncora e DEVE terminar com erro explicando o motivo.
- R5.5 A resposta da verificação DEVE informar quantos eventos foram verificados, o último `id`, o hash final e se a cabeça confere. Quando houver âncora, DEVE informar também se a cadeia e a âncora conferem.
- R5.6 A documentação DEVE descrever o modelo de ameaças. Contra quem controla o banco como dono ou superusuário, a garantia é só de detecção, e só até a última âncora guardada fora do banco.
- R5.7 A âncora DEVE ser guardada fora do servidor do banco e do servidor da API, num sistema com credenciais diferentes das do banco. A documentação DEVE dizer que guardá-la no mesmo servidor, no mesmo volume, no mesmo banco (inclusive em outra tabela) ou só dentro do backup do banco **não atende** ao requisito de independência.
- R5.8 A documentação DEVE definir o procedimento manual da âncora:
  - geração: quem, quando e em que ocasiões obrigatórias;
  - armazenamento: onde e com quantas cópias;
  - controle de acesso: quem escreve, quem lê e a segregação em relação a quem administra o banco;
  - histórico: âncoras antigas nunca são sobrescritas nem apagadas;
  - uso na verificação: qual âncora e com que frequência;
  - recuperação: perda das âncoras e conferência depois da restauração;
  - resposta a divergência: preservar evidências, não "corrigir" a cadeia, comunicar.
- R5.9 A âncora NÃO DEVE conter dado pessoal. A autoria da geração fica registrada pelo sistema onde a âncora é guardada.
- R5.10 A documentação DEVE separar a geração manual (esta spec) de uma futura rotina automatizada, que fica fora do escopo e exige spec própria. DEVE também dizer o que essa rotina terá de garantir: credencial só de acréscimo, independente do banco, e alerta quando falhar.
- R5.11 A verificação DEVE ler todos os lotes de eventos e a cabeça da cadeia numa única transação `REPEATABLE READ` e `READ ONLY`. QUANDO houver escrita concorrente durante a verificação, o sistema NÃO DEVE responder `integra=false` por causa dela. Os eventos confirmados depois do início da verificação ficam para a próxima. O evento `auditoria.verificada` (R7.3) DEVE ser gravado numa transação separada, depois da leitura.
- R5.12 O sistema DEVE oferecer o comando `sgs-admin auditoria verificar [--ancora arquivo.json]`, que verifica a cadeia direto no banco, sem a API, com as mesmas regras de R5.1 a R5.3 e R5.11. Ele DEVE ser só de leitura, NÃO DEVE gravar evento e DEVE funcionar contra uma cópia restaurada em outro servidor. Ele DEVE imprimir o resultado em JSON e terminar com código diferente de zero quando a cadeia não estiver íntegra.

### R6. Integridade do `db_change_log` (lacuna F)
Como Auditor, quero que o log do banco também seja somente inserção, e saber exatamente o que ainda escapa dessa proteção.

- R6.1 ENQUANTO os triggers estiverem ativos, o banco DEVE recusar UPDATE e DELETE no `db_change_log` para qualquer papel, inclusive o dono da tabela, tanto pela tabela-mãe quanto direto em cada partição, inclusive a `DEFAULT`.
- R6.2 ENQUANTO os triggers estiverem ativos, o banco DEVE recusar TRUNCATE para qualquer papel, inclusive o dono: na tabela-mãe, direto numa partição mensal e direto na partição `DEFAULT`.
- R6.3 O trigger `trg_registry_change_log` DEVE continuar gravando no log as escritas feitas no cadastro, pela API e fora dela, com o mesmo conteúdo de hoje.
- R6.4 Toda partição criada por `sp_ensure_monthly_partitions` DEVE nascer com a proteção de R6.1 e R6.2.
- R6.5 O usuário da API DEVE continuar com somente SELECT na tabela-mãe e sem privilégio nas partições. Ele DEVE ser recusado ao tentar UPDATE, DELETE, TRUNCATE, `ALTER TABLE … DETACH PARTITION`, `DROP TABLE` de partição ou `SET session_replication_role`.
- R6.6 Um teste automatizado DEVE caracterizar o limite da proteção:
  - o dono da tabela **consegue** fazer `DETACH PARTITION`, `DROP TABLE` de partição e `DISABLE TRIGGER`;
  - os triggers de R6.8 continuam atuando com `SET session_replication_role = replica`.
  Assim a documentação não promete mais do que o banco garante.
- R6.7 A documentação DEVE registrar:
  - as operações que continuam possíveis para o dono ou o superusuário: desligar ou remover trigger, DETACH ou DROP de partição, DROP de tabela. Depois do R6.8, o `session_replication_role = replica` deixa de contornar os triggers marcados como `ENABLE ALWAYS`, mas continua contornando os triggers internos de chave estrangeira;
  - quais triggers deixam de atuar em cada caso;
  - quais mecanismos ainda permitem detectar a adulteração;
  - por que não há hash encadeado no log do banco.
- R6.8 Os triggers de imutabilidade do `audit_log`, os do `db_change_log` (tabela-mãe e partições, existentes e futuras) e o `trg_registry_change_log` DEVEM ficar habilitados como `ENABLE ALWAYS` (`tgenabled = 'A'`), para continuarem atuando com `session_replication_role = replica`. A documentação DEVE registrar que o dono ou o superusuário ainda pode desabilitá-los explicitamente.

### R7. Completude da auditoria (lacuna G)
Como Auditor, quero ter certeza de que toda operação de escrita deixa evento.

- R7.1 Um teste automatizado DEVE enumerar todas as rotas de escrita da aplicação e falhar se alguma não estiver no mapa de rota para ação auditada nem na lista de exceções justificadas do design.
- R7.2 Para cada rota de escrita mapeada, um teste DEVE executá-la e conferir a ação, o tipo de ator, o resultado, o IP e o User-Agent do evento gravado.
- R7.3 QUANDO a verificação da cadeia for executada, o sistema DEVE gravar o evento `auditoria.verificada` com o resultado da verificação.
- R7.4 QUANDO um usuário consultar o detalhe de um evento, o sistema DEVE gravar o evento `auditoria.evento_consultado` só com o `id` do evento consultado, porque o detalhe expõe dados de origem (IP, User-Agent, sessão). Esse evento DEVE ser tratado como evento de acesso: só aparece na lista e no detalhe para quem tem `auditoria:read_acessos`, como `auth.*` e `acesso.negado` (008/R2.2). Assim o Gestor de Dados não descobre a atividade de investigação do Auditor.
- R7.5 O sistema NÃO DEVE auditar as demais leituras nesta spec. A política de leitura auditável DEVE estar escrita no design, com finalidade, sensibilidade, volume e minimização.
- R7.6 Uma operação NÃO DEVE gerar o mesmo fato duas vezes no `audit_log`. A correlação com o `db_change_log` DEVE ser documentada, e não duplicada.

### R8. Visualização com controle de acesso (lacuna H)
Como Auditor, quero abrir um evento e ver tudo o que foi registrado sobre ele. Como Gestor de Dados, quero ver a trilha sem acessar dados de origem que não me cabem. Como gestor de uma unidade, quero ver o histórico de negócio da unidade, inclusive as tentativas que falharam.

- R8.1 QUANDO o usuário clicar num evento da trilha, a tela DEVE mostrar o detalhe, com os campos que houver:
  - ator, tipo de ator e origem;
  - ação e entidade;
  - instante;
  - resultado e categoria;
  - mudanças (`campo`, `de`, `para`) e metadata;
  - IP, User-Agent, sessão e request id;
  - `prev_hash` e `hash`.
- R8.2 IP, User-Agent e sessão DEVEM aparecer só no detalhe do evento e só para quem tem `auditoria:read_acessos`. Para os demais com `auditoria:read` global, esses campos DEVEM vir vazios e marcados como restritos, na API e na tela.
- R8.3 A tela de verificação DEVE mostrar o estado da cadeia, quantos eventos foram verificados, o último `id`, o hash final e se a cabeça confere. DEVE aceitar uma âncora opcional e mostrar se a cadeia e a âncora conferem. Uma divergência DEVE aparecer como alerta, com o evento e o motivo.
- R8.4 A lista da trilha e o histórico da unidade DEVEM mostrar o resultado de cada evento.
- R8.5 As permissões e escopos atuais (spec 008, R1.4 e R2.2) NÃO DEVEM mudar.
- R8.6 Nenhuma resposta além do detalhe de R8.2 DEVE conter IP, User-Agent ou sessão de eventos da trilha. Isso vale para a lista da trilha, o histórico da unidade, o log do banco, as partições e as consultas do dashboard. A `vw_unit_history` NÃO DEVE ter colunas de IP, User-Agent, sessão, request id ou hash.
- R8.7 (Decisão do proprietário, 11/11/2026.) O histórico da unidade DEVE mostrar os eventos de negócio cuja entidade é a unidade, inclusive equipamentos e serviços vinculados (011/R4.4), e os `operacao.falhou` cuja entidade seja a unidade, identificada de forma inequívoca pelo caminho. Ele NÃO DEVE mostrar eventos de acesso (`auth.*`, `acesso.negado`) nem eventos da própria auditoria (`auditoria.*`), que pertencem à trilha geral (008/R2.2).
- R8.8 As contagens e listas de "alterações" do dashboard (009/R2.3, R2.4) NÃO DEVEM contar eventos de falha. Uma tentativa que falhou não é alteração.
- R8.9 O acesso a IP, User-Agent e sessão DEVE depender só de `auditoria:read_acessos`. Um teste DEVE falhar se a matriz de papéis conceder essa permissão a outros papéis além de `AUDITOR` e `ADMIN_TI`. O `ADMIN_TI` não tem `auditoria:read` e não alcança as rotas da trilha. Uma decisão futura do DF9 (spec 012) que conceda `read_acessos` ao Gestor de Dados DEVE vir com emenda desta spec, porque reexporia esses dados.

### R9. Retenção, backup e restauração (lacuna I)
Como responsável pela operação, quero uma política de retenção e um procedimento de backup que possam ser verificados.

- R9.1 A política DEVE definir uma retenção mínima online de 2 anos (RS-05) para o `audit_log` e o `db_change_log`. Depois desse prazo, os registros DEVEM ser preservados por arquivamento, sem descarte automático.
- R9.2 Qualquer descarte futuro DEVE depender de procedimento aprovado pelo dono e gravar evento no `audit_log`. Esta spec NÃO DEVE implementar descarte.
- R9.3 A documentação DEVE descrever:
  - o backup: formato, frequência proposta, local e independência do armazenamento, responsáveis operacionais por função;
  - o RPO e o RTO, como metas propostas pendentes de validação;
  - a restauração em banco novo;
  - a conferência depois da restauração: cadeia, cabeça e âncora (R5.8);
  - a preservação de constraints, triggers, funções e privilégios.
- R9.4 Um teste automatizado, em banco descartável, DEVE fazer backup (`pg_dump -Fc`) e restauração num banco novo. O backup DEVE conter eventos anteriores e posteriores à constraint `NOT VALID` de R1.6. O teste DEVE comprovar, no banco restaurado, que:
  - a constraint continua presente e marcada como não validada;
  - as linhas antigas continuam lá e com o hash íntegro;
  - um INSERT novo sem tipo de ator ou sem resultado é recusado;
  - a cadeia, a cabeça e a âncora gerada antes do backup conferem;
  - os triggers (inclusive os das partições do `db_change_log`), as funções e os privilégios do `sgs_app` continuam como na origem.
- R9.5 A documentação NÃO DEVE afirmar prazo legal universal. As referências legais (LGPD art. 37; Marco Civil da Internet art. 15) DEVEM aparecer como pontos a validar com o encarregado de dados ou com o jurídico da Secretaria.
- R9.6 Cada restauração, real ou de ensaio, DEVE deixar evidências:
  - comandos executados com horário;
  - checksum do arquivo de backup;
  - resultado da verificação e âncora usada;
  - resultado da conferência do catálogo;
  - duração medida, para comparar com o RTO;
  - identificação de quem executou e de quem conferiu.
- R9.7 Antes da entrega final, DEVE haver um ensaio completo de restauração num banco descartável, seguindo o procedimento documentado e registrando as evidências de R9.6. Os stacks existentes NÃO DEVEM ser usados.

## Decisões do proprietário (11/11/2026)
Todas foram tomadas por Vinicius (ViniciusVbm), proprietário e único responsável, na sessão de trabalho de 11/11/2026. O projeto é acadêmico: as metas abaixo são compromissos de procedimento, não garantias de operação empresarial.

- **P1 (responsáveis e locais).** Há um único responsável operacional, o proprietário. Ele acumula as funções de operador de backup, operador de âncora, verificador e guardião das cópias. O backup principal fica em armazenamento local, separado do banco e dos containers. A segunda cópia fica em armazenamento privado na nuvem, independente do ambiente local. As âncoras JSON ficam separadas dos backups, com uma cópia local e outra externa. Dumps nunca vão para o Git. Não se cria infraestrutura nem integração nova para isso.
- **P2 (metas).**
  - RPO de 24 h e RTO de até 4 h, como metas.
  - Backup diário enquanto houver desenvolvimento ativo, mais um backup antes de migrações e de mudanças estruturais.
  - Retenção de 7 backups diários, mais os backups dos marcos acadêmicos.
  - Âncora diária enquanto houver atividade relevante, mais âncoras antes e depois de mudanças estruturais.
  - Um ensaio completo de restauração antes da entrega final (R9.7).
  - Sem agendador nem serviço automatizado.
- **P3 (proxy).** O Caddy é o único proxy confiável, direto diante da API, com IP fixo na rede de borda e `FORWARDED_ALLOW_IPS` restrito a esse `/32`. Proxy ou balanceador adicional em produção fica fora do escopo, como limitação documentada.
- **P4 (privacidade).** IP, User-Agent e sessão só para quem tem `auditoria:read_acessos`, isto é, o Auditor nas rotas da trilha. O Gestor de Dados não os acessa por nenhum caminho. O acoplamento com o DF9 fica protegido pelo R8.9.
- **P5.** Sem *event trigger*. O dono e o superusuário continuam podendo alterar a estrutura e desligar proteções (R6.6, R6.7).
- **P6.** A limitação de responsável único é aceita como risco do projeto acadêmico. A segunda cópia da âncora fica fora do ambiente local e do banco. Não se simula uma segregação de funções que não existe.
- **P7.** `ENABLE ALWAYS` nos três grupos de triggers (R6.8), com testes.
- **P8.** `10.231.0.0/16` é a faixa proposta, configurável, com conferência só por leitura antes de subir containers (R3.7).
- **H4 / R8.7.** Aceito: `operacao.falhou` da unidade entra no histórico; `auth.*`, `acesso.negado` e `auditoria.*` não entram; o dashboard não conta os eventos excluídos; o RBAC continua o mesmo.
- **D1.** IP fixo do Caddy e confiança `/32`, com testes negativos (R3.1, R3.8).
- **D2.** `sgs-admin auditoria verificar --ancora arquivo.json` (R5.12).
- **D3.** `auditoria.evento_consultado` é evento de acesso (R7.4).
- **D7.** A verificação e a âncora ficam em tarefas separadas (`tasks.md`, T8 e T9).
