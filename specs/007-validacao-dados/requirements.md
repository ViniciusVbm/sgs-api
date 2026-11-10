# 007 · Validação de dados · Requisitos

- Status: Rascunho
- Rastreia: RF-03, RS-08; critério 6.1 "dado inválido gera mensagem clara e não é gravado"; pilar Confiabilidade
- Dono humano: Vinicius (ViniciusVbm), como responsável pelo projeto: a spec não tinha dono registrado (`steering/sdd-workflow.md` § Dono da spec). Linha registrada na revisão de 09/11/2026.

## Contexto
A funcionalidade que mais diferencia a plataforma das planilhas (Requisitos Esperados §3.5). Combina regras fixas em código (formato) com regras de negócio configuráveis pelo Gestor de Dados, e mede a qualidade da base ("pendências").

## Fora do escopo
- Comparação automática com CNES.
- Sugestões por IA.

## Histórias e critérios

### R1. Bloquear dado inválido
- R1.1 QUANDO uma criação ou alteração de unidade, equipamento ou serviço viola uma regra bloqueante, o sistema DEVE responder 422 e NÃO DEVE gravar nada.
- R1.2 A resposta 422 DEVE listar todos os erros de uma vez, cada um com `campo`, `regra` e `mensagem` em português compreensível pelo usuário final.
- R1.3 O sistema DEVE validar: CNES com 7 dígitos; CEP com 8 dígitos e no intervalo de Recife (50000-000 a 52999-999); telefone brasileiro (10 ou 11 dígitos); e-mail válido; coordenadas dentro do município; horário de funcionamento coerente (abertura antes do fechamento).
- R1.4 O sistema DEVE validar que tipo, distrito, área e tipos de serviço/equipamento existem e estão ativos nas tabelas de referência.
- R1.5 O sistema DEVE validar coerência entre entidades: tipo de serviço `FARMACIA_FAMILIA` não pode ser cadastrado em `CAPS` (CAPS tem `FARMACIA`, regra do cliente); serviço não pode ser vinculado a unidade inativa.
- R1.6 O sistema DEVE normalizar antes de validar: remover máscara de CEP/telefone/CNES e espaços extras em nomes.

### R2. Regras configuráveis
- R2.1 QUANDO o Gestor de Dados cria uma regra (`obrigatorio`, `regex`, `lista`, `intervalo`) para um campo de unidade, o sistema DEVE aplicá-la às gravações seguintes.
- R2.2 Cada regra DEVE ter severidade `bloqueante` ou `alerta`.
- R2.3 SE a regra configurada for inválida (regex que não compila, intervalo invertido), ENTÃO o sistema DEVE recusá-la com 422.
- R2.4 Alterações de regras DEVEM ser auditadas (`regra_validacao.*`).
- R2.5 O sistema DEVE oferecer `POST /validacao/simular` para testar dados contra as regras sem gravar.

### R3. Pendências (qualidade da base)
- R3.1 QUANDO uma gravação passa nas regras bloqueantes mas viola regras de `alerta`, o sistema DEVE gravar e registrar as pendências da unidade.
- R3.2 O sistema DEVE manter `pending_issues` (contagem) e a lista de pendências por unidade, consultável em `GET /unidades/{id}/pendencias`.
- R3.3 QUANDO uma regra é criada ou alterada, o Gestor de Dados DEVE poder disparar a revalidação de toda a base (`POST /validacao/revalidar`), que recalcula pendências sem alterar dados.

## Perguntas em aberto
- Quais campos o cliente considera obrigatórios além dos da spec 006? (o campo "Gerente" foi citado como problemático)
- A faixa de CEP de Recife está correta para todas as unidades (algumas podem estar na região metropolitana)?
- (revisão de 09/11/2026, agente; aguarda o dono) R1.3 pede validar e-mail, mas a unidade não tem campo de e-mail (spec 006). Opções: (a) tirar o e-mail da R1.3; (b) emenda na 006 criando o campo. Recomendação: (a), sem campo novo no MVP.
- (revisão de 09/11/2026, agente; aguarda o dono) R1.3 pede coordenadas "dentro do município" sem dizer como. Opções: (a) retângulo envolvente de Recife, com os limites no design; (b) polígono do município (exato, exige dado geográfico e cálculo de ponto em polígono). Recomendação: (a).
- (revisão de 09/11/2026, agente; aguarda o dono) R1.6 manda tirar a máscara do telefone, mas hoje ele é gravado com máscara (ex.: `(81) 3355-0000`) e o front exibe assim. Gravar só dígitos muda dados existentes e a exibição. Opções: (a) gravar só dígitos e formatar na saída; (b) aceitar com máscara e validar contando os dígitos. Recomendação: (b), sem migração de dados.
- (revisão de 09/11/2026, agente; aguarda o dono) Unidades já cadastradas podem não passar nas regras novas (CEP fora da faixa, telefone com 9 dígitos). Opções: (a) bloquear qualquer gravação da unidade até corrigir; (b) bloquear só o campo enviado na requisição e tratar o legado como pendência na revalidação (R3.3). Recomendação: (b), para não travar edições que não tocam o campo.
