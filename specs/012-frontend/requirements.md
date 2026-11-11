# 012 · Frontend SGS Recife · Requisitos

- Status: Aprovado (Vinicius, 09/11/2026). Emenda documental 1 (10/11/2026: responsáveis, decisões do Grupo 01 e análise de P1 a P5, **sem mudança funcional**) **aprovada (Vinicius, 10/11/2026)**: autorização expressa do dono, dada na sessão de trabalho para as alterações puramente documentais e de responsabilidade, e registrada pelo agente. Emenda funcional 1 (R5.5 [C], **proposta**) **aguarda o G1 do dono**. **Emenda funcional 2** (acadêmica: R7.7, R8.2, R12.5, R12.6, R16.1 e o prazo de 13/11/2026) **aprovada na sessão de trabalho de 10/11/2026 (registro do agente, por instrução expressa na sessão; o agente não registra aprovação em nome de ninguém, e a confirmação no PR fica com o dono, Vinicius)**. Ver § Emendas
- Rastreia: RF-01, RF-02, RF-03, RF-04, RF-06, RF-07, RF-08, RF-09, RF-10, RS-01, RS-02; critério 6.1 "login leva a tela coerente com o perfil"; Entrega 11 de Projetos (21/11/2026); **entrega final de Projeto de Banco de Dados, Etapas 03 a 06 (13/11/2026; emenda funcional 2)**; ADR-0010, ADR-0011
- Dono humano: Vinicius (ViniciusVbm)
- Origem: `docs/PLANO_INTEGRACAO_FRONTEND.md` (versão 2, 09/11/2026)

## Contexto
O grupo tem um protótipo navegável em HTML (`frontend/prototipo/Prototipo_SGS_Recife_v2.html`, fora do Git). Ele tem dados fictícios no `localStorage`, login de demonstração e autorização só no navegador. Esta spec transforma o protótipo na interface real da API, **preservando a identidade visual e as 24 funcionalidades inventariadas**. A autenticação, a autorização e as regras de negócio ficam sempre no backend; a interface só reflete o que o `/me` e a API permitem.

## Escopo
- **Escopo mínimo (21/11/2026):** os requisitos marcados **[M]**. Usam só endpoints que já existem, sem mudar spec aprovada nem a matriz RBAC.
- **Escopo completo:** os requisitos marcados **[C]**. Dependem de decisões (DF, ver § Decisões) ou de backend que ainda não existe. Até lá, a funcionalidade **continua visível**, desabilitada, com a indicação "em desenvolvimento" (R13).
- **Corte acadêmico (13/11/2026; emenda funcional 2):** parte do [M] é antecipada para a entrega final de Projeto de Banco de Dados, que pede na interface o CRUD de 4 tabelas ou mais, o uso de funções e procedimentos, o efeito dos triggers, as consultas e views, filtros, gráficos, médias, percentuais e tendências. Entram no corte: R6.1, R6.2, R7.7, R8.1, R8.2, R12.1 (exceto as 8 verificações), R12.2, R12.4, R12.5, R12.6 e R16.1 (nível A); R7.1 a R7.3 (nível B). O resto do [M] continua com o prazo de 21/11/2026. Os requisitos novos usam só rotas que já existem, sem mudar backend, contrato nem a matriz RBAC.

## Fora do escopo
- Mudanças no backend, na matriz RBAC ou em specs aprovadas: cada uma tem a sua spec ou emenda (§ Decisões).
- Aplicativo móvel nativo, modo offline, internacionalização.
- Frameworks, empacotadores e dependências npm (ADR-0010).

## Histórias e critérios
Convenções:
- "Gestor de Dados", "Técnico Distrital" etc. são os papéis da spec 003.
- "Escopo" é o escopo da permissão no `/me`.
- Toda ação de escrita depende da resposta da API (R3.4).

### R1. Entrega e aparência (F24)
Como usuário, quero a mesma interface do protótipo, servida pelo sistema, para não reaprender a ferramenta.
- R1.1 [M] O sistema DEVE servir a interface em `https://<host>/` pelo mesmo domínio da API, e a API DEVE continuar em `/api/v1/*`, `/health/*` e `/.well-known/*`.
- R1.2 [M] A interface DEVE preservar cores, tipografia, layout, navegação (menu lateral e menu móvel), modais, toasts, tema claro e escuro e os três pontos de quebra (1080, 860 e 560 px) do protótipo.
- R1.3 [M] A interface NÃO DEVE carregar recurso de domínio externo; a fonte é servida localmente.
- R1.4 [M] A interface DEVE funcionar nas larguras de 1280, 860 e 390 px sem rolagem horizontal da página.
- R1.5 [M] A interface DEVE manter a acessibilidade do protótipo: `aria-live` nos avisos, foco preso e devolvido nos modais, rótulos nos controles, `prefers-reduced-motion`.
- R1.6 [M] ENQUANTO uma tela aguarda a API, a interface DEVE mostrar o estado de carregamento. Sem itens, DEVE mostrar o estado vazio do protótipo. SE a API falha, ENTÃO DEVE mostrar o aviso de erro com a mensagem (`detail`) da API.

### R2. Autenticação (F01 a F04, F23)
Como usuário, quero entrar com minha conta real e o segundo fator.
- R2.1 [M] QUANDO o usuário envia o campo rotulado **"Usuário"** e a senha, a interface DEVE chamar `POST /api/v1/auth/login` com `{username, password}` e seguir para o cadastro do 2FA (`mfa_enrollment_required`) ou para a verificação (`mfa_required`). DF7: o contrato não muda.
- R2.2 [M] QUANDO o 2FA ainda não foi cadastrado, a interface DEVE chamar `POST /api/v1/auth/mfa/enroll` com o `mfa_token`, mostrar a URI `otpauth://` devolvida e a chave contida nela como texto copiável, **sem QR Code nesta entrega** (DF6), e confirmar o código com `POST /api/v1/auth/mfa/confirm`.
- R2.3 [M] QUANDO o usuário informa o código, a interface DEVE chamar `POST /api/v1/auth/mfa/verify` e guardar o access token **só em memória**.
- R2.4 [M] QUANDO a página é aberta ou recarregada, a interface DEVE tentar `POST /api/v1/auth/refresh` com `X-Requested-With: sgs` e, sem sessão, mostrar o login. Depende de configuração: a origem do front precisa estar em `CORS_ORIGINS` para o anti-CSRF do refresh (002/R3.6). O compose já tem `https://localhost`.
- R2.5 [M] QUANDO uma chamada autenticada (fora de `/api/v1/auth/*`) recebe 401, a interface DEVE tentar um refresh e repetir a chamada uma vez. Se falhar de novo, DEVE voltar ao login.
- R2.6 [M] QUANDO o usuário sai, a interface DEVE chamar `POST /api/v1/auth/logout` e descartar o token.
- R2.7 [M] SE o login ou o código falham (401) ou o login é limitado (429), ENTÃO a interface DEVE mostrar a mensagem da API, que já é a mesma para usuário inexistente e senha errada (002/R1.3).
- R2.8 [M] "Esqueci a senha" (F03) DEVE continuar como orientação para procurar o Administrador de TI.
- R2.9 [C] QUANDO houver endpoint de redefinição de senha, a interface do Administrador de TI DEVE oferecer a redefinição. Depende de: spec ou emenda da 003 para `/admin/usuarios` (`usuario:manage`); dono da 003: Vinicius.
- R2.10 [M] O código da interface NÃO DEVE conter usuários, senhas ou códigos de demonstração. "Restaurar dados de demonstração" (F23) DEVE sair da interface, e a demonstração DEVE continuar disponível pelo comando `sgs-admin seed demo` em dev, documentado.
- R2.11 [M] SE o login devolve `access_token` direto, o que só acontece com `MFA_OBRIGATORIO=false` em dev (002, design), ENTÃO a interface DEVE entrar sem o passo do 2FA.

### R3. Perfis e navegação (F05)
Como usuário, quero ver o menu e as telas do meu papel.
- R3.1 [M] QUANDO o usuário entra, a interface DEVE ler `GET /api/v1/me` e montar o menu e os botões a partir das **permissões efetivas** e dos escopos devolvidos, não do nome do papel.
- R3.2 [M] A interface DEVE ter telas e menu para os 7 papéis (DF8), derivados só das permissões que já existem na matriz da spec 003, sem ampliá-la. Os 3 perfis do protótipo valem como referência: central = Gestor de Dados, distrito = Técnico Distrital, unidade = Gestor de Unidade. Os 4 papéis ausentes do protótipo (Diretoria, Auditor, Administrador de TI, Coordenador Técnico) seguem a tabela do design.
- R3.3 [M] SE o usuário abre uma rota que as permissões dele não cobrem, ENTÃO a interface DEVE mostrar "sem acesso". A API continua negando (403); isso não é responsabilidade do front.
- R3.4 [M] Esconder um botão NÃO DEVE ser o único controle: toda ação DEVE depender da resposta da API, e um 403 DEVE ser mostrado como "sem permissão".
- R3.5 [M] Para o Técnico Distrital, a lista DEVE abrir filtrada pelo distrito do escopo dele. Para o Gestor de Unidade, o início DEVE ser a ficha da unidade do escopo dele, como no protótipo. Esse recorte é **conveniência de navegação**: a matriz atual dá `unidade:read` global a esses papéis (padrão da pergunta em aberto da 003), e a interface NÃO DEVE apresentá-lo como restrição de acesso (DF13). Com mais de uma atribuição, vale a primeira em ordem alfabética do papel.

### R4. Início (F06)
- R4.1 [M] QUANDO um usuário com `dashboard:read` abre o início, a interface DEVE mostrar os indicadores de `GET /api/v1/dashboard/resumo` no escopo dele: total e distribuição por status, tipo, área técnica e distrito, qualidade e alterações recentes. Sem `dashboard:read` (Auditor, Administrador de TI), o início DEVE ser a primeira tela do menu do papel.
- R4.2 [C] A interface DEVE mostrar as solicitações pendentes (depende de R10.2), as regras de qualidade mais violadas e as 5 fichas com mais pendências (dependem da spec 007; dono: Vinicius).

### R5. Lista de unidades (F07, F08)
- R5.1 [M] A interface DEVE listar `GET /api/v1/unidades` com busca (`q`, nome e CNES, também pelo campo de busca do topo), filtros da API (`tipo`, `area`, `distrito`, `status`, `com_pendencias`) e ordenação (`nome`, `distrito`, `atualizacao`), mantendo os filtros na URL. Os nomes de tipo e de distrito DEVEM ser resolvidos por `GET /api/v1/referencias/{tipo}`, porque a lista devolve só os ids.
- R5.2 [M] A interface DEVE paginar a lista conforme a API: `pagina` e `tamanho`, até 100 por página.
- R5.3 [C] A busca por bairro e por tipo e os filtros "com pendência" (as 8 verificações), "completas" e "aguardando validação" DEVEM usar filtros da API, quando existirem. Dependem de: emenda da 006 (busca), spec 007 (verificações) e R10.2 (aguardando).
- R5.4 [C] QUANDO o usuário exporta, a interface DEVE baixar o CSV **gerado pelo backend** no escopo e com a permissão dele (DF10); a interface não gera CSV. As células que começam com `=`, `+`, `-` ou `@` DEVEM chegar neutralizadas pelo backend. Depende de: spec do backend e DF15.

### R6. Ficha da unidade (F09, F12, F13, F14)
- R6.1 [M] A interface DEVE mostrar `GET /api/v1/unidades/{id}`: dados gerais e serviços. Guarda o `ETag` e resolve os nomes das referências como em R5.1. Os "equipamentos de saúde" que a API também devolve NÃO DEVEM ser exibidos na aba de aparelhos do protótipo (R9.1, DF1).
- R6.2 [M] A aba de histórico DEVE mostrar `GET /api/v1/unidades/{id}/historico` com autor, papel, data (fuso de Recife) e `{campo, de, para}` rotulado. SE nenhum escopo de `auditoria:read` do usuário cobre a unidade (global, área do tipo, distrito ou a própria unidade), ENTÃO a aba NÃO DEVE aparecer. É o caso da Diretoria e do Administrador de TI, e do Técnico Distrital para unidades de outro DS.
- R6.3 [M] A interface DEVE mostrar as 8 verificações de qualidade do protótipo, **calculadas sobre os dados da API e só para exibição**. A validação que bloqueia a gravação é do backend (spec 007). Uma verificação cujo dado a API ainda não tem DEVE aparecer como "não verificável ainda", e não como falha: o número do endereço e o horário (R6.4).
- R6.4 [C] Número, complemento, e-mail, horário e as 4 situações (DF3) DEVEM aparecer e ser editáveis quando o backend os tiver. Depende de: emenda da 006 (responsável: Hélder) e DF3.
- R6.5 [C] "Confirmar que os dados estão corretos" (F14) DEVE registrar a revisão pela API, quando houver endpoint. Depende de: emenda da 006.

### R7. Edição e cadastro (F15, F16)
- R7.1 [M] QUANDO um usuário com `unidade:update` de escopo **global** (hoje, só o Gestor de Dados) edita a ficha, a interface DEVE mostrar o diff (antes e depois) para confirmação e enviar `PATCH /api/v1/unidades/{id}` com `If-Match` e só os campos alterados.
- R7.2 [M] SE a API responde 412, ENTÃO a interface DEVE avisar que a ficha mudou e recarregá-la. SE responde 422, DEVE marcar os campos com as mensagens da API (`errors[{campo, mensagem}]`). SE responde 409, DEVE oferecer o link da unidade existente (`unidade_existente_id`). SE responde 403 com `campos_estruturais`, DEVE apontar esses campos.
- R7.3 [M] QUANDO um usuário com `unidade:create` de escopo **global** cadastra uma unidade, a interface DEVE chamar `POST /api/v1/unidades` e abrir a ficha nova na aba de serviços.
- R7.4 [M] Enquanto a DF2 (e a DF14, para o Coordenador) não for decidida, a interface NÃO DEVE oferecer edição nem cadastro direto ao Técnico Distrital, ao Gestor de Unidade nem ao Coordenador Técnico, embora a matriz atual lhes dê `unidade:update` (e ao Coordenador, `unidade:create`) no próprio escopo. Isso restringe a interface, não a API, e não muda permissões. A regra do protótipo é só propor; o botão "Propor alteração" aparece desabilitado com a indicação "em desenvolvimento".
- R7.5 [C] QUANDO a DF2 (e a DF14) e a spec de solicitações estiverem aprovadas, o distrito DEVE poder "solicitar cadastro" (F16) pela solicitação.
- R7.6 [C] O campo de observação do modal de confirmação (protótipo) DEVE ser enviado quando a API aceitar. Hoje o `PATCH` recusa campos extras (`extra="forbid"`) e não grava observação, então o campo aparece desabilitado com a indicação "em desenvolvimento". Depende de: emenda da 006.
- R7.7 [M] (emenda funcional 2) QUANDO um usuário com `unidade:deactivate` de escopo **global** (hoje, só o Gestor de Dados) desativa uma unidade pela ficha, a interface DEVE pedir o motivo, com 3 a 500 caracteres como a API (`DesativacaoIn`), pedir confirmação e chamar `POST /api/v1/unidades/{id}/desativar` com `{motivo}`. A API executa o procedimento `sp_deactivate_unit` (011/R6.2 a R6.4).
  - Com a resposta, a ficha DEVE mostrar o status "Inativa" e guardar o novo `ETag`.
  - SE a unidade já está inativa, ENTÃO o botão NÃO DEVE aparecer.
  - 404, 422 e 403 seguem o design (§ Fluxo).
  - A interface NÃO DEVE oferecer exclusão física de unidade (006/R4.2). Para os demais papéis, o botão não aparece, pela regra de R7.4.

### R8. Serviços (F10)
- R8.1 [M] A aba de serviços DEVE listar os serviços da unidade (`GET /api/v1/unidades/{id}/servicos`). QUANDO o usuário tem `servico:write` de escopo **global** (hoje, só o Gestor de Dados), DEVE permitir incluir (`POST`) e remover (`DELETE`) serviços, com os tipos de `GET /api/v1/referencias/tipos-servico` (DF5). Para os demais papéis com `servico:write` no próprio escopo, a aba é só leitura até a DF2/DF14, pela mesma regra de R7.4.
- R8.2 [M] (emenda funcional 2) QUANDO o usuário com `servico:write` de escopo **global** altera um serviço da unidade, a interface DEVE enviar `PATCH /api/v1/unidades/{id}/servicos/{sid}` só com os campos alterados: `nome`, `tipo_servico_id`, `no_cnes` e `status`.
  - O vínculo com equipamento (`equipamento_id`) NÃO DEVE ser editável na interface enquanto a DF1 estiver pendente.
  - Vale a mesma regra de escopo de R8.1.
  - Motivo: sem a alteração, a tabela `services` tem inclusão, leitura e exclusão, mas não atualização.

### R9. Equipamentos e infraestrutura (F11)
- R9.1 [M] A aba "Equipamentos" DEVE aparecer. Enquanto a DF1 não for decidida, DEVE mostrar "em desenvolvimento" e NÃO DEVE gravar aparelhos em `equipments`, que guarda equipamento de saúde.
- R9.2 [C] QUANDO a entidade de infraestrutura existir, a aba DEVE listar, incluir, alterar e remover aparelhos com quantidade e estado. Depende de: DF1 e da spec de infraestrutura.

### R10. Solicitações e validações (F16 a F18)
- R10.1 [M] O item de menu "Solicitações" (com `alteracao:propor`) ou "Validações" (com `alteracao:validar`) DEVE aparecer, com a indicação "em desenvolvimento". Pela matriz atual: Gestor de Dados e Coordenador Técnico (validar), Técnico Distrital e Gestor de Unidade (propor).
- R10.2 [C] QUANDO a DF2, a DF14 e a spec de solicitações estiverem aprovadas, a interface DEVE permitir propor (com justificativa obrigatória), acompanhar, aprovar e devolver (motivo com 10 caracteres ou mais), conforme as regras do protótipo: uma solicitação pendente por unidade, e quem propõe não aprova.

### R11. Notificações (F19)
- R11.1 [M] O sino DEVE aparecer para todos os papéis, sem contagem, com a indicação "em desenvolvimento".
- R11.2 [C] QUANDO houver API de notificações, o sino DEVE contar as não lidas, listar e marcar como lidas. Depende de: spec de notificações.

### R12. Qualidade e histórico geral (F20, F21)
- R12.1 [M] Para quem tem `dashboard:read`, o painel de qualidade DEVE mostrar as consultas de qualidade da API (`/api/v1/dashboard/consultas/*`, `/api/v1/dashboard/inventario`) e as 8 verificações calculadas sobre os dados recebidos (R6.3).
- R12.2 [M] O histórico geral DEVE usar `GET /api/v1/auditoria/eventos` para quem tem `auditoria:read` global (Gestor de Dados e Auditor). Para os papéis com `auditoria:read` de escopo menor (Coordenador, Técnico Distrital, Gestor de Unidade), DEVE mostrar a indicação "em desenvolvimento". Para quem não tem `auditoria:read` (Diretoria, Administrador de TI), NÃO DEVE aparecer.
- R12.3 [C] O histórico geral DEVE funcionar no escopo do distrito quando a API permitir. O filtro "Acessos ao sistema" DEVE seguir a DF9. Depende de: emenda da 008 e DF9 (Vinicius, dono da 003 e da 008). A consulta do histórico no escopo hierárquico é também a Grupo-DF9 (§ Decisões do Grupo 01).
- R12.4 [M] Para o Auditor, a interface DEVE oferecer a verificação da cadeia de auditoria (`POST /api/v1/auditoria/verificar`) e mostrar `integra` ou o primeiro evento divergente.
- R12.5 [M] (emenda funcional 2) Para quem tem `auditoria:read` de escopo **global** (Gestor de Dados e Auditor), o histórico geral DEVE ter duas visões além da trilha:
  - aba **"Log do banco"**, com `GET /api/v1/auditoria/banco`: data (fuso de Recife), tabela, operação, id da linha, colunas alteradas como `{de, para}`, usuário do banco e a origem ("pela API" ou "fora da API", campo `pela_api`). Tem filtros `tabela`, `de`, `ate` e `fora_da_api` e paginação. O nome do gestor chega mascarado pelo banco e DEVE ser exibido como veio;
  - painel **"Partições do log"**, com `GET /api/v1/auditoria/banco/particoes`: nome, limite e número de linhas de cada partição.

  A tela DEVE identificar a origem: os registros vêm do trigger `trg_registry_change_log` e as partições, do procedimento com cursor `sp_ensure_monthly_partitions`. A interface NÃO DEVE executar esse procedimento, que roda pelo `sgs-admin banco particoes`. Para quem tem `auditoria:read` de escopo menor, vale R12.2 ("em desenvolvimento").
- R12.6 [M] (emenda funcional 2) O painel de qualidade (R12.1) DEVE mostrar:
  - **as consultas do catálogo** `GET /api/v1/dashboard/consultas`: para cada uma, `titulo`, `justificativa` e `tecnica_sql`, como vêm da API; o resultado paginado da rota da consulta; e os filtros que ela aceita (`parametros`: distrito, tipo de unidade, área técnica). Os filtros são enviados à API e mantidos na URL;
  - **gráficos em SVG gerado pelo próprio front**, sem biblioteca nem domínio externo (R1.3, R15.2). Cada gráfico tem título, rótulos e a tabela com os mesmos dados (acessibilidade, R1.5). São três, no mínimo:
    - percentual de unidades sem CNES dos distritos acima da rede, com a linha do percentual da rede (`distritos-sem-cnes-acima-da-rede`: `percent_without_cnes`, `network_percent_without_cnes`);
    - equipamentos por tipo e distrito (`equipamentos-por-tipo-e-distrito`);
    - alterações em 7 e em 30 dias por distrito (`alteracoes-por-periodo`);
  - **percentuais** calculados pelo banco, como a API os devolve;
  - **tendência**: o ritmo diário dos últimos 7 dias ao lado do ritmo dos últimos 30, isto é, as contagens da API divididas por 7 e por 30;
  - **gráfico de pizza** (rosca) da situação cadastral (`registration_status`, de `fn_registration_status`), contado sobre as linhas do inventário. Cada fatia DEVE ser igual ao `total` de `GET /api/v1/dashboard/inventario?situacao=…` nos mesmos filtros;
  - **gráfico de linha das alterações no período**, para quem tem `auditoria:read` de escopo **global**:
    - **períodos:** 7 dias, 30 dias e intervalo personalizado (`de` inclusivo, `ate` exclusivo);
    - **fonte:** contagem das linhas reais de `GET /api/v1/auditoria/banco?de&ate`, somando **todas as páginas**;
    - **agrupamento:** por hora em períodos de até 2 dias, e por dia nos demais;
    - **lacunas:** intervalos sem registro aparecem com zero; nenhum registro é inventado;
    - **dados insuficientes:** SE o período tem menos de 2 intervalos com registro, ENTÃO a interface DEVE avisar que não há histórico suficiente para mostrar tendência, além de mostrar o gráfico;
    - **sem permissão:** quem não tem `auditoria:read` global não vê o gráfico, sem chamar a rota;
  - **médias** de equipamentos e de serviços por unidade, calculadas sobre **todas** as linhas de `GET /api/v1/dashboard/inventario` no escopo e nos filtros da tela (todas as páginas, sem amostragem), com o número de unidades usado no cálculo.

  A interface NÃO DEVE exibir número que não venha da API ou de conta declarada sobre ela. Sem linhas, mostra o estado vazio (R1.6).

### R13. Funcionalidades ainda sem backend
- R13.1 [M] Toda funcionalidade [C] ainda não disponível DEVE continuar visível, desabilitada, com a indicação "em desenvolvimento", e NÃO DEVE chamar a API. Nenhuma das 24 funcionalidades do protótipo DEVE ser removida sem registro nesta spec.

### R14. Importação CSV (F22)
- R14.1 [M] A tela "Importar planilha" DEVE aparecer para quem tem `unidade:create` de escopo global (o Gestor de Dados), com a indicação "em desenvolvimento".
- R14.2 [C] QUANDO houver API de importação, a interface DEVE enviar o arquivo para pré-validação, mostrar as linhas com erro (as regras do protótipo) e confirmar a importação. O backend DEVE limitar tamanho, codificação e número de linhas. Depende de: spec de CSV do backend.

### R15. Segurança da interface
- R15.1 [M] Todo valor vindo da API DEVE ser escapado antes de entrar em HTML, em texto e em atributos; os ids usados em rotas DEVEM passar por `encodeURIComponent`.
- R15.2 [M] A interface DEVE ser servida com CSP sem `unsafe-eval`, com `script-src 'self'` e `frame-ancestors 'none'`. A exceção temporária de estilos inline está registrada no design.
- R15.3 [M] O `localStorage` só PODE guardar o tema; nenhum dado de negócio nem token.
- R15.4 [M] A interface NÃO DEVE usar `eval`, `new Function` nem inserir HTML a partir de dado não escapado.

### R16. Tabelas de referência (F25; emenda funcional 2)
Como Gestor de Dados, quero manter os tipos de unidade, de equipamento e de serviço pela interface, para corrigir o catálogo sem acesso ao banco.
- R16.1 [M] QUANDO um usuário com `regra_validacao:manage` de escopo **global** (hoje, só o Gestor de Dados) abre "Tabelas de referência", a interface DEVE listar os **tipos de unidade, de equipamento e de serviço** (`GET /api/v1/referencias/{tipo}`, com `tipos-unidade`, `tipos-equipamento` e `tipos-servico`) e permitir:
  - **incluir** (`POST /api/v1/referencias/{tipo}`) com `codigo` e `nome`. No tipo de unidade, `area_tecnica_id` é obrigatório, escolhido entre as áreas de `GET /api/v1/referencias/areas-tecnicas`;
  - **alterar** (`PATCH /api/v1/referencias/{tipo}/{id}`) o código, o nome e, no tipo de unidade, a área técnica, enviando só os campos alterados;
  - **desativar e reativar** (`PATCH {ativo}`). É a exclusão lógica: a API não apaga referência, e a interface NÃO DEVE oferecer exclusão física;
  - **cascata:** QUANDO o código de um tipo de equipamento muda, a interface DEVE mostrar quantos equipamentos receberam o novo código pela FK `ON UPDATE CASCADE`. O número vem de `equipamentos_afetados`, no evento `referencia.atualizada` de `GET /api/v1/auditoria/eventos?entidade_tipo=referencia&entidade_id=tipos-equipamento:{id}`. SE o usuário não tem `auditoria:read` global, ENTÃO a contagem é omitida, sem estimativa;
  - **erros:** 409 (código repetido) marca o campo `codigo`; 422 marca os campos com as mensagens da API; 403 mostra "sem permissão" (R3.4).

  Distritos e áreas técnicas DEVEM aparecer **só para leitura**, porque são domínio fechado (os 8 distritos sanitários e as 4 áreas técnicas; `docs/banco/06-trinta-tuplas.md`). O item de menu aparece só com `regra_validacao:manage` global. Para os demais papéis, a rota mostra "sem acesso" (R3.3). Nenhuma permissão nova é criada (R3.2).

## Inventário das 24 funcionalidades × requisitos
| F | Funcionalidade | Requisitos | Escopo |
|---|---|---|---|
| F01 | Login | R2.1, R2.7, R2.10, R2.11 | M |
| F02 | 2º fator | R2.2, R2.3, R2.4, R2.5 | M |
| F03 | Esqueci a senha | R2.8, R2.9 | M (orientação) + C |
| F04 | Logout | R2.6 | M |
| F05 | Menu por perfil | R3.1 a R3.5, R11.1 (sino em todos) | M |
| F06 | Início | R4.1, R4.2 | M + C |
| F07 | Lista, busca do topo e filtros | R5.1 a R5.3, R3.5 | M + C |
| F08 | Exportar CSV | R5.4 | C |
| F09 | Ficha: dados e desativação | R6.1, R6.4, R1.6, R7.7 | M + C |
| F10 | Serviços | R8.1, R8.2 | M |
| F11 | Equipamentos (aparelhos) | R9 | M (visível) + C |
| F12 | Histórico da ficha | R6.2 | M |
| F13 | Verificações na ficha | R6.3 | M (exibição) |
| F14 | Confirmar revisão | R6.5, R13 | C (visível) |
| F15 | Edição com diff | R7.1, R7.2, R7.6 | M (central) + C (observação) |
| F16 | Cadastro | R7.3, R7.5 | M (central) + C |
| F17 | Propor alteração | R7.4, R10 | M (visível) + C |
| F18 | Aprovar e devolver | R10 | M (visível) + C |
| F19 | Notificações | R11 | M (visível) + C |
| F20 | Painel de qualidade | R12.1, R12.6 | M |
| F21 | Histórico geral, log do banco e verificação da cadeia | R12.2, R12.3, R12.4, R12.5 | M + C |
| F22 | Importar CSV | R14 | M (visível) + C |
| F23 | Restaurar demonstração | R2.10 | M (sai da UI; fica no `sgs-admin`) |
| F24 | Tema, responsividade, acessibilidade | R1 | M |
| F25 | Tabelas de referência (não existe no protótipo; emenda funcional 2) | R16.1 | M |

## Decisões (DF1 a DF12 e novas pendências)

### Decididas pelo dono (Vinicius, 09/11/2026)
Decisões de produto. Não autorizam mudar backend, permissões nem specs aprovadas.

| ID | Decisão | Onde entra |
|---|---|---|
| DF6 | Cadastro do 2FA com a chave e a URI como texto, sem QR Code nesta entrega | R2.2 |
| DF7 | Rótulo "Usuário" na tela de login; o contrato de `/auth/login` não muda | R2.1 |
| DF8 | Telas e menus para Diretoria, Auditor, Administrador de TI e Coordenador Técnico, só com as permissões existentes, sem ampliar a matriz | R3.2, design § Perfis |
| DF10 | Exportação CSV feita pelo backend, no escopo e com as permissões do usuário | R5.4; requer spec do backend (DF15) |
| DF11 | Playwright com Python como dependência de desenvolvimento para os E2E | design § Testes; ADR-0011 (ainda Proposto) |
| DF12 | O escopo mínimo obrigatório de 21/11 são os requisitos [M]; os [C] ficam planejados | todo o documento |

### Pendentes (não presumidas)
Responsáveis pela governança de 10/11/2026:
- `steering/sdd-workflow.md` § Dono da spec: Vinicius é dono da 003, 004, 005, 007, 008, 009, 010 e 011;
- decisão do Grupo 01 de 10/11/2026: Hélder é responsável pela 006, com apoio técnico de Vinicius. A formalização na própria spec 006 fica a cargo dele, a partir da branch `feat/003-interface-dashboard` e do ADR-0009.

Até a emenda documental 1, esta tabela apontava "Rafael" nas linhas DF1, DF2, DF3, DF9, DF13, DF14 e DF15.

| ID | Decisão | Responsável | Depende | Afeta | Situação em 10/11/2026 |
|---|---|---|---|---|---|
| DF1 | O que são os "equipamentos" do protótipo (aparelhos) × equipamento de saúde | **Cliente** + **Hélder** (emenda da 006) | spec de infraestrutura | R9.2 | pendente |
| DF2 | Técnico Distrital e Gestor de Unidade gravam direto ou só propõem | **Vinicius** (matriz da 003) + **Cliente** | spec de solicitações | R7.4, R7.5, R10.2 | **premissa do grupo** (Grupo-DF13 e Grupo-DF14), aguarda o cliente |
| DF3 | Situação da unidade: 4 valores × `ativa`/`inativa`/`em_implantacao` | **Cliente** + **Hélder** (006) | emenda da 006 + migração | R6.4 | pendente |
| DF4 | "Grupo de atenção" × área técnica | **Cliente** | — | R4.2 (agrupamento) | pendente |
| DF5 | Catálogos oficiais de tipos de unidade e de serviço | **Cliente** | carga pela API de referências (`POST /referencias/{tipo}`, sem código) | R8.1 (conteúdo) | pendente |
| DF9 | O Gestor de Dados vê os eventos de acesso (`auditoria:read_acessos`) | **Vinicius** (matriz da 003; 008) | — | R12.3 | pendente. A Grupo-DF9 trata de outro assunto (consulta do histórico) e **não** responde a esta |
| DF13 | Escopo de **leitura** de unidades do Técnico Distrital, do Gestor de Unidade e do Coordenador. Hoje `unidade:read` é global para todo papel de negócio, padrão adotado na pergunta em aberto da 003 ("leitura de unidades deve ser global para todos os papéis? padrão: sim"). O protótipo restringia distrito e unidade. O `dashboard:read` já é por escopo (011/T22) | **Vinicius** (003) + **Cliente** | — | R3.5 (a interface mantém o comportamento atual: recorte só de navegação) | **premissa do grupo** (Grupo-DF2: leitura limitada ao escopo), aguarda o cliente; exige emenda da 003 e migração |
| DF14 | A regra do DF2 também vale para o Coordenador Técnico, que tem `unidade:update`, `unidade:create`, `equipamento:write` e `servico:write` na área e não existe no protótipo | **Vinicius** + **Cliente** | DF2 | R7.4, R8.1, R10.2 (a interface oculta a escrita direta até decidir) | pendente: as premissas do grupo falam de "Coordenador do DS", não do `COORD_TECNICO` de área (pergunta P2) |
| DF15 | Exportação no backend: permissão e regra | **Hélder** (regra, Grupo-DF15) + **Vinicius** (matriz da 003) + dono da spec do backend (a definir) | DF10 | R5.4 | **decidida em parte** pela Grupo-DF15 (§ abaixo). Pendentes: colunas do CSV, layout do PDF, spec do backend e a permissão por papel, que depende da premissa Grupo-DF13 |

**Responsáveis ainda não definidos:** donos das specs futuras de solicitações, notificações, infraestrutura e exportação/importação CSV/PDF. O dono da 007 passou a ser o Vinicius em 09/11/2026 (`specs/007-validacao-dados/requirements.md`).

### Decisões do Grupo 01 (10/11/2026)
Registradas a partir de dois documentos do grupo:
- "Decisões Internas do Grupo 01";
- "Decisões do Cliente Adotadas pelo Grupo 01".

A numeração desses documentos **não é a desta spec**. Para não confundir as duas, elas aparecem aqui com o prefixo **Grupo-**, e a coluna "Responde, nesta spec, a" faz a correspondência.

**Nenhuma delas muda os requisitos funcionais aprovados.** As que exigem backend, matriz RBAC ou spec nova só entram na interface quando essas dependências existirem; até lá, vale o [M] atual (R7.4, R3.5, R13).

#### Decisões internas (decididas pelo grupo)
| ID do grupo | Decisão | Responde, nesta spec, a | O que a API faz hoje (conferido em `9c37029`) | Dependência |
|---|---|---|---|---|
| Grupo-DF9 | Histórico de alterações só leitura, reaproveitando a auditoria imutável. Por unidade, `GET /api/v1/unidades/{id}/historico`; geral para o perfil central, `GET /api/v1/historico`. Retorno: campo, valor anterior, valor novo, data e hora, autor. Do mais recente para o mais antigo, paginado. Visibilidade pelo escopo hierárquico. Implementação: Vinicius; validação de UX: Hélder. A exportação do histórico segue a Grupo-DF15 | R6.2, R12.2, R12.3 | Por unidade: **existe**, com `campo/rotulo/de/para`, `quando`, `autor`, paginação (`pagina`, `tamanho`), filtros `de`, `ate`, `autor`, `campo` e escopo de `auditoria:read`. Geral: **existe como `GET /api/v1/auditoria/eventos`**, não `/api/v1/historico`, e exige `auditoria:read` **global** (o Gestor de Dados tem) | Rota `/api/v1/historico` e histórico geral no escopo do distrito: emenda da 008 (dono: Vinicius). Sem ela, a interface usa a rota existente (R12.2) |
| Grupo-DF15 | Exportação: CSV para dados, PDF para relatório legível; no escopo do usuário; cada exportação gera evento de auditoria (usuário, data e hora, escopo, formato). Primeira versão: lista filtrada de unidades e equipamentos e resumo do dashboard. Regra: Hélder; implementação: backend. Colunas do CSV e layout do PDF a definir. A regra do gerente deve ser coerente com a Grupo-DF13 | DF10, DF15, R5.4 | **Não existe** rota de exportação (CSV ou PDF). `relatorio:export` está semeada só para Gestor de Dados (G), Coordenador Técnico (A), Diretoria (G) e Auditor (G). A spec 005 é outra exportação (relatórios no S3) | Spec do backend (exportação); emenda da 003 se Técnico Distrital ou Gestor de Unidade passarem a exportar |
| Grupo-006 | Hélder assume a spec 006, com apoio técnico de Vinicius. A formalização parte da branch `feat/003-interface-dashboard` e do ADR-0009 | DF1, DF3, R5.3, R6.4, R6.5, R7.6 | — | Formalização na spec 006 (fora desta spec) |
| Grupo-G2 | Revisão do design: Igor Fugagnoli (principal) e Erick Sanches (suplente); disponibilidade do Igor a confirmar. Autor do design: Hélder | design § Registro de aprovação | — | Confirmação do Igor |

#### Premissas adotadas pelo grupo (aguardam ratificação do cliente)
**Situação:** adotadas pelo Grupo 01 em 10/11/2026 como premissas de trabalho, porque o cliente não deu retorno. **Ainda não foram ratificadas pelo cliente**, e esta spec não afirma que ele as aprovou.

**Correspondência de perfis (interpretação, a confirmar):**
- "Gestora central" é o `GESTOR_DADOS`;
- "Coordenador do DS IV" é o `TECNICO_DISTRITAL` (escopo distrito);
- "Gerente do CAPS II" é o `GESTOR_UNIDADE`.

| ID do grupo | Premissa | Responde, nesta spec, a | O que a API faz hoje | Dependência |
|---|---|---|---|---|
| Grupo-DF2 | Acesso: central, toda a rede; coordenador do DS, as unidades do próprio distrito; gerente, a própria unidade. **Leitura** e ações limitadas ao escopo | DF13 (e R3.5) | `unidade:read` é **global** para todos os papéis de negócio; a escrita já é limitada ao escopo; o `dashboard:read` já é por escopo | Ratificação; emenda da 003 e migração para restringir a leitura (T23) |
| Grupo-DF13 | Permissões. Central: consulta, propõe, aprova alterações comuns e sensíveis, cadastra e importa unidades, exporta a rede. Coordenador: consulta e propõe no distrito, aprova alterações comuns do distrito, encaminha as sensíveis ao central, exporta o distrito. Gerente: consulta e propõe na própria unidade, não aprova, exporta a própria unidade | DF2, DF15 (permissão) | Não há fluxo de proposta ou aprovação (rotas de solicitação não existem). `alteracao:validar` é só do Gestor de Dados (G) e do Coordenador Técnico (A); o Técnico Distrital tem só `alteracao:propor`. Técnico Distrital e Gestor de Unidade não têm `relatorio:export` | Ratificação; spec de solicitações; emenda da 003 (validar e exportar por papel) |
| Grupo-DF14 | Edição. Diretos: nome, endereço, CEP, telefone. Sensíveis, com aprovação central: CNES, tipo, status, distrito sanitário, vínculo da unidade. As comuns valem na hora (com permissão e escopo); as sensíveis geram solicitação. Tudo auditado, com ETag/If-Match | DF2 | O `PATCH` grava na hora, com If-Match e auditoria. Distrito, tipo e CNES (`CAMPOS_ESTRUTURAIS`) exigem escopo global ou de área, senão dão **403** (`campos_estruturais`), sem criar solicitação. **Status não é estrutural:** quem tem `unidade:update` no escopo pode mudá-lo direto. "Vínculo da unidade" não corresponde a nenhum campo do modelo | Ratificação; spec de solicitações; emenda da 006 (lista de campos sensíveis) |

**Perguntas abertas pelas premissas e como foram tratadas** (análise de 10/11/2026 contra o contrato `contracts/openapi.yaml`, `src/modules/registry/domain/unidade.py`, a matriz da 003 com a `0011_09` e `docs/architecture/arquitetura-conceitual.md` § 3). Nenhuma decisão do cliente foi presumida.

- **P1. As alterações comuns valem na hora ou passam por aprovação?**
  - **Contradição:** a Grupo-DF14 diz que as alterações comuns valem na hora, e a Grupo-DF13 diz que o coordenador "aprova alterações comuns do distrito" e que o gerente "propõe".
  - **Resolvido (técnico):**
    - a API aplica na hora todo `PATCH` aceito, com If-Match e auditoria na mesma transação, e **não tem fluxo de aprovação**;
    - por isso a interface **não oferece "aprovar" nem "devolver"** para alterações comuns, nem simula esse fluxo (R10.1, R13.1);
    - aplicar alterações comuns na hora é tecnicamente possível para o Técnico Distrital e o Gestor de Unidade, porque o `unidade:update` deles no escopo é aceito pela API.
  - **Pendente (PF-01):** se o distrito e a unidade editam na hora ou propõem.
  - **Solução provisória:** vale o R7.4 aprovado. Só o escopo global edita, e o distrito e a unidade veem "Propor alteração" desabilitado, com "em desenvolvimento".
  - **Se a decisão for "na hora":**
    - o caminho é uma emenda funcional do R7.4 e do R8.1;
    - **antes**, uma emenda da 006 deve pôr `status` entre os campos estruturais. Hoje o backend não bloqueia o status no escopo D/U, e escondê-lo só na interface não seria controle.
- **P2. Correspondência entre perfis.**
  - **Resolvido (correspondência), com evidência no modelo:**
    - `TECNICO_DISTRITAL` é a "área técnica distrital" e é o **único papel com escopo de distrito** ("cada distrito é responsável pelas suas unidades", arquitetura § 3), então o "Coordenador do DS IV" corresponde a ele;
    - `COORD_TECNICO` é a "área técnica central", com escopo de **área técnica** (ex.: Saúde Mental), e **não é equivalente**;
    - os três perfis de referência dos testes e da UX são `GESTOR_DADOS`, `TECNICO_DISTRITAL` do DS IV e `GESTOR_UNIDADE` de um CAPS II.
  - **Pendente (PF-02):** o coordenador do DS "aprova alterações comuns do distrito", mas o `TECNICO_DISTRITAL` só tem `alteracao:propor`, e a arquitetura diz que "no workflow futuro, propõe e o nível central valida".
  - **Pendente (PF-03):** a regra do `COORD_TECNICO`, que as premissas não citam (DF14 desta spec).
- **P3. "Vínculo da unidade".**
  - **Pendente (PF-04).** Não há campo, coluna nem rota com esse nome. No projeto, "vínculo" designa a ligação de serviços e equipamentos à unidade por `unit_id` (006/T8, 006/R6.4, `docs/architecture/modelo-dados.md`), que são recursos com rotas e permissões próprias (`servico:write`, `equipamento:write`), e não um campo da ficha.
  - **Solução provisória:** nenhum campo é criado nem exibido. A escrita de serviços continua só para o escopo global (R8.1).
- **P4. Campos não listados.**
  - **Classificação provisória** pela estrutura atual (`UnidadeUpdate`: `nome`, `cnes`, `tipo_unidade_id`, `distrito_id`, `cep`, `endereco`, `bairro`, `telefone`, `nome_gestor`, `latitude`, `longitude`, `status`):

    | Campo | Premissa Grupo-DF14 | Backend hoje | Classificação provisória |
    |---|---|---|---|
    | `nome`, `endereco`, `cep`, `telefone` | comuns | comuns | comum |
    | `cnes`, `tipo_unidade_id`, `distrito_id` | sensíveis | estruturais (403 fora do escopo G/A) | sensível |
    | `status` | sensível | **comum** (não bloqueado) | sensível pela premissa; divergência registrada em P1 |
    | `bairro` | não citado | comum | comum, por inferência (é parte do endereço); a confirmar (PF-05) |
    | `nome_gestor` (dado pessoal, LGPD) | não citado | comum | pendente (PF-05) |
    | `latitude`, `longitude` | não citados | comuns | pendente (PF-05) |
    | área técnica | não é campo da unidade | deriva do tipo | segue o tipo (sensível) |
    | `horario_funcionamento` | não citado | só leitura na API | fora da edição até a emenda da 006 (R6.4) |
    | e-mail da unidade | não citado | não existe | fora até a emenda da 006 (R6.4) |

  - **Sem efeito no escopo mínimo:** só o escopo global edita (R7.4).
- **P5. Colunas do CSV e layout do PDF.**
  - **Pendente de especificação (PF-06).** Sem exportação simulada: o botão fica visível e desabilitado (R5.4, R13.1).

### Pendências formais (10/11/2026)
| ID | Questão | Impacto | Responsável | Prazo | Solução provisória | Dependência |
|---|---|---|---|---|---|---|
| PF-01 | Distrito e unidade aplicam alterações comuns na hora ou propõem? (contradição Grupo-DF13 × Grupo-DF14) | R7.4, R7.5, R8.1, R10.2; ficha, edição e serviços; T9, T10, T16 | Cliente (ratificação); Vinicius (003) e Hélder (006) para as emendas | validação com o cliente, 21/11/2026 | R7.4: só o escopo global edita; "Propor alteração" desabilitado | Ratificação; emenda da 006 (`status` estrutural) se for "na hora"; spec de solicitações se for "propor" |
| PF-02 | O coordenador do DS (`TECNICO_DISTRITAL`) aprova alterações comuns do distrito? | R10.2; Validações; T16 | Cliente; Vinicius (matriz da 003: `alteracao:validar` D) | 21/11/2026 | Sem aprovação na interface; o menu "Solicitações" desabilitado (R10.1) | Ratificação; emenda da 003; spec de solicitações |
| PF-03 | Regra de edição, aprovação e exportação do `COORD_TECNICO` (área técnica) | R7.4, R8.1, R10.2; T9, T10, T16 | Cliente; Vinicius (003) | 21/11/2026 | Só leitura (R7.4, R8.1), como hoje | Ratificação; DF14 desta spec |
| PF-04 | O que é o "vínculo da unidade" | Grupo-DF14; ficha e serviços; T16, T18 | Cliente; Hélder (006) | antes da spec de solicitações | Nada exibido nem criado | Definição do cliente; emenda da 006, se for campo novo |
| PF-05 | Classificação de `bairro`, `nome_gestor`, `latitude` e `longitude` (comum ou sensível) | Grupo-DF14; edição pelo distrito e pela unidade; T16 | Cliente; Hélder (006) | antes da spec de solicitações | Sem efeito: só o escopo global edita | Ratificação |
| PF-06 | Colunas do CSV e layout do PDF da Grupo-DF15 | R5.4, R5.5 (proposto); lista, ficha, início; T21 | Hélder (regra); dono da spec de exportação (a definir) | antes do início da T21 | Botão de exportar visível e desabilitado ("em desenvolvimento"); nenhuma geração no navegador | Spec do backend de exportação |
| PF-07 | Ratificação das premissas Grupo-DF2, Grupo-DF13 e Grupo-DF14 | R3.5, R7.4, R7.5, R8.1, R10.2, R5.4; T16, T21, T23 | Cliente (Secretaria de Saúde) | 21/11/2026 | O [M] aprovado: leitura global, só o escopo global edita | Retorno do cliente |

## Registro da revisão 3 (09/11/2026)
Revisão integral contra o código atual (rotas, schemas e matriz efetiva da 003 com a 0011_09), sem mudar regra de negócio nem permissão.

**Correções e omissões:**
- **Requisitos novos:**
  - R1.6, estados de carregamento, vazio e erro (omissão);
  - R2.11, login em dev com `MFA_OBRIGATORIO=false`, que devolve o token direto (omissão; o front quebraria);
  - R7.6 [C], observação no modal de confirmação: o `PATCH` recusa campos extras, então R7.1 deixou de prometer o envio;
  - R12.4, verificação da cadeia pelo Auditor (estava no design, sem requisito).
- **Ajustes:**
  - R2.2 explicita a chamada a `/auth/mfa/enroll` e que a chave vem da URI;
  - R2.4 registra a dependência de `CORS_ORIGINS` (anti-CSRF);
  - R2.5 exclui as rotas de `/auth/*` do refresh automático;
  - R3.1 deriva o menu das permissões, não do nome do papel;
  - R3.5 trata múltiplas atribuições;
  - R3.3 e R3.4 separam o que é do front e o que é da API;
  - R4.1 vale para quem tem `dashboard:read` (Auditor e Admin TI não têm);
  - R4.2 depende de R10.2 e da 007 (não de R11);
  - R5.1 resolve nomes pelas referências (a API devolve ids) e inclui a busca do topo;
  - R6.1 não mostra equipamentos de saúde na aba de aparelhos (DF1);
  - R6.2 esconde o histórico pelo escopo de `auditoria:read`, não só pelo papel;
  - R6.3 marca "não verificável ainda" quando a API não tem o dado;
  - R7.2 trata o 403 com `campos_estruturais`;
  - R8.1 limita a escrita de serviços ao escopo global, pela mesma regra de R7.4: Técnico, Gestor de Unidade e Coordenador têm `servico:write` no escopo;
  - R10.1 deriva os itens das permissões `alteracao:propor` e `alteracao:validar`;
  - R12.1 vale para quem tem `dashboard:read`;
  - R14.1 deriva o acesso de `unidade:create` global;
  - R15.1 inclui `encodeURIComponent` para ids em rotas.
- **Referências:** "Perguntas em aberto" → "§ Decisões"; o inventário de funcionalidades foi atualizado.
- **Contagem:** de 53 para **57 requisitos** (44 [M], 13 [C]).

**Impacto em `tasks.md`**, que não foi alterado nesta revisão e deve ser ajustado no G3:
- R1.6 e R2.11 entram na T4 ou na T3;
- R12.4 entra na T11;
- R7.6 entra no escopo completo (junto da T18);
- a T8 deve testar "não verificável ainda" e trocar "oculto sem `auditoria:read`" por "oculto sem `auditoria:read` no escopo da unidade" (R6.2);
- a T10 deve testar que só o escopo global inclui e remove serviços.

**Conferência final (09/11/2026):**
- **IDs:** 57 definidos, nenhum duplicado, todos com a classificação: 44 [M] e 13 [C]. A única contagem no documento é a desta seção.
- **Referências:** todo `Rx.y` citado existe aqui, exceto `002/R3.6` em R2.4, que é da spec 002 e existe.
- **Requisitos sem tarefa:** só R1.6, R2.11, R7.6 e R12.4, os da lista acima. O `tasks.md` não cita requisito inexistente.
- **Inventário:** R15.1 a R15.4 são transversais e não estão ligados a uma funcionalidade específica.
- **Decisões:** DF1 a DF15 aparecem aqui. O `tasks.md` não cita DF4 nem DF5, que só afetam conteúdo (agrupamento e catálogos), e não bloqueiam nenhuma tarefa.

**Nenhuma decisão do Rafael ou do cliente foi tomada:** DF1 a DF5, DF9 e DF13 a DF15 continuam pendentes, e a interface mantém o comportamento que a matriz atual permite, só ocultando a escrita direta onde a regra do protótipo pede proposta.

## Emendas

### Emenda documental 1 (10/11/2026; aprovada, Vinicius, 10/11/2026)
**Revisão para o fechamento** (10/11/2026, por diff contra a versão aprovada em 09/11/2026, guardada em `~/sgs-api-frontend-backup-20261110/`):

| Classe | Alterações | Muda comportamento? |
|---|---|---|
| Atualização de responsáveis | R2.9, R4.2, R6.4, R12.3 (só o texto "Depende de"); colunas "Responsável" de DF1, DF2, DF3, DF9, DF13, DF14, DF15 | Não |
| Esclarecimento documental | coluna "Situação em 10/11/2026"; "O que a API faz hoje"; nota de R12.3 ligando a Grupo-DF9; análise de P1 a P5 e tabela de pendências | Não |
| Vinculação de decisões do grupo | subseção "Decisões do Grupo 01", com a correspondência Grupo-DFn → DFn | Não. As premissas não mudam requisitos (abaixo) |
| Alteração de comportamento | **Nenhuma** nos 57 requisitos. A Grupo-DF15 traz comportamento novo (PDF e resumo do dashboard), que **não** foi incorporado aqui: está na emenda funcional 1, proposta | — |
| Novos requisitos ou critérios | Nenhum nesta emenda. R5.5 está na emenda funcional 1 | — |

**Conferências:**
- os 57 requisitos aprovados continuam com o mesmo texto funcional (44 [M], 13 [C]);
- os diffs de R2.9, R4.2, R6.4 e R12.3 tocam só o responsável e a referência.
**Motivo:** a governança mudou depois do G1 (PRs #1 e #3 da `novo/main`, `9c37029`), e o Grupo 01 registrou decisões em 10/11/2026.

**O que mudou:**
- **Responsáveis:**
  - "Rafael" virou Vinicius (dono da 003 e da 008) em R2.9, R12.3 e nas linhas DF2, DF9, DF13 e DF14;
  - virou Hélder (responsável pela 006, por decisão do grupo) em R6.4 e nas linhas DF1 e DF3;
  - "dono a definir" da 007 virou Vinicius em R4.2.
- **§ Decisões:**
  - coluna "Situação em 10/11/2026";
  - nova subseção "Decisões do Grupo 01", com a correspondência entre as numerações, o que a API faz hoje e as perguntas P1 a P5.

**O que não mudou:**
- nenhum critério EARS, nenhuma classificação [M]/[C] e nenhuma das decisões DF6, DF7, DF8, DF10, DF11 e DF12;
- os 57 requisitos (44 [M], 13 [C]) continuam iguais no conteúdo.

**Por que as premissas não mudam requisitos:** DF2, DF13 e DF14 do grupo ainda não foram ratificadas pelo cliente, e o backend não tem fluxo de solicitação, leitura por escopo nem exportação. Quando houver ratificação e backend, os requisitos afetados (R3.5, R7.4, R7.5, R8.1, R10.2, R5.4, R12.3) recebem uma emenda funcional própria, que passa pelo G1.

### Emenda funcional 1 (proposta em 10/11/2026; **aguarda o G1 do dono**; não vale até ser aprovada)
**Origem:** Grupo-DF15, decisão interna aprovada pelo Grupo 01 em 10/11/2026. Ela amplia a exportação de R5.4, que hoje cobre só o CSV da lista, para três coisas novas:
- PDF de relatório legível;
- exportação dos equipamentos;
- exportação do resumo do dashboard.

É comportamento novo, por isso entra como requisito proposto, e não como esclarecimento.

- R5.5 [C] (proposto) QUANDO o backend oferecer a exportação, a interface DEVE permitir exportar, no escopo do usuário, a lista filtrada de unidades e de equipamentos e o resumo do dashboard, em CSV (dados) e em PDF (relatório legível), baixando o arquivo gerado pelo backend. A interface NÃO DEVE gerar CSV nem PDF no navegador (DF10). A auditoria de cada exportação (usuário, data e hora, escopo e formato) é do backend.
  - Depende de: spec do backend de exportação; PF-06 (colunas e layout); permissão por papel (DF15, PF-07).

**Efeito:**
- aprovada, a contagem passa a 58 requisitos (44 [M], 14 [C]), e o R5.5 entra no inventário (F08) e na T21;
- enquanto não for aprovada, o botão de exportar segue o R5.4 e o R13.1: visível, desabilitado, sem chamar a API.

### Emenda funcional 2: entrega acadêmica (proposta e aprovada na sessão de trabalho de 10/11/2026 (registro do agente, por instrução expressa na sessão; o agente não registra aprovação em nome de ninguém, e a confirmação no PR fica com o dono, Vinicius))
**Origem:** a auditoria do banco de 10/11/2026 contra as Etapas 01 a 06 de Projeto de Banco de Dados. O backend já oferece CRUD de 6 tabelas, o procedimento de desativação, as 8 consultas, as 2 views e o log do trigger. A interface, porém, só lia `/me`, `/dashboard/resumo` e `/unidades`: com as tarefas aprovadas (T8 a T11), ela faria CRUD de só 2 tabelas e não mostraria o efeito dos triggers. A entrega final da disciplina é em **13/11/2026**, antes do prazo desta spec (21/11/2026).

**Direção aprovada na sessão de trabalho de 10/11/2026** (registro do agente, que não registra aprovação em nome de ninguém): incluir R7.7, R12.5, R12.6 e R16.1 e registrar o prazo acadêmico. Depois, na mesma sessão, foram aprovados: o R8.2; a pizza, a linha e o filtro de período no R12.6 (agregação no front sobre `/auditoria/banco`, sem rota nova nem mudança na spec 011); e os critérios de versão e de atualização na ficha e nos serviços.

| Requisito | Classe | Etapa da disciplina | Rotas (todas já existem) |
|---|---|---|---|
| R7.7 | novo [M] | 05 e 06: procedimento chamado pela interface | `POST /unidades/{id}/desativar` |
| R8.2 | novo [M] | 03 e 06: atualização em `services` | `PATCH /unidades/{id}/servicos/{sid}` |
| R12.5 | novo [M] | 05 e 06: efeito do trigger de log e resultado do procedimento com cursor | `GET /auditoria/banco`, `/auditoria/banco/particoes` |
| R12.6 | novo [M] | 03, 04 e 06: consultas, views, filtros, gráficos, médias, percentuais, tendência | `GET /dashboard/consultas`, `/dashboard/consultas/*`, `/dashboard/inventario` |
| R16.1 | novo [M] | 02 e 06: CRUD de 3 tabelas; `ON UPDATE CASCADE` visível | `GET/POST/PATCH /referencias/{tipo}[/{id}]`, `GET /auditoria/eventos` |

**O que não muda:**
- **integridade referencial:** a "exclusão" das tabelas de referência é **desativação** (`ativo = false`), não exclusão física. Nenhuma FK muda, e nenhuma exclusão incompatível com o modelo é forçada. `unit_types` e `service_types` são referenciadas por FK sem cascata. A exclusão física pela interface existe só em `services`, que o modelo permite;
- nenhum texto de requisito aprovado; o corte de 13/11 só antecipa o prazo de parte do [M] (§ Escopo);
- nenhuma rota, contrato, permissão nem migração (§ Fora do escopo continua valendo);
- DF1 a DF15 e PF-01 a PF-07 seguem pendentes como estão. R7.7, R8.2 e R16.1 usam só o escopo global, pela mesma regra de R7.4, e a cascata de R16.1 é lida na auditoria, não na aba de aparelhos (R9.1, DF1).

**Separação dentro de R12.1:** as 8 verificações calculadas no front dependem do cálculo de R6.3 e ficam no prazo de 21/11/2026 (T8 parte B e T11 parte B). As consultas e o inventário entram no corte de 13/11.

**Efeito:**
- **62 requisitos** (49 [M], 13 [C]), ou 63 com o R5.5 da emenda funcional 1, ainda proposto;
- tarefas novas: T24 (R16.1) e T25 (R7.7). A T8 e a T11 ganham partes A (13/11) e B (21/11), e a T10 cobre o R8.2 (`tasks.md`).
