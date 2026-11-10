# Pendências com dependência externa

- Data: 09/11/2026
- O que é: o que falta no projeto e depende de alguém de fora da equipe de desenvolvimento. O resto do MVP está pronto e testado ([RESUMO_STATUS_PROJETO.md](../RESUMO_STATUS_PROJETO.md)).
- Prazos: validação em 21/11/2026, code freeze em 28/11/2026, SR2 em 05/12/2026.

## 1. Aprovação das specs (dono: Vinicius)
Nenhum código destas specs pode ser escrito antes da aprovação (regra 1 do `AGENTS.md`). Requisitos e tarefas são aprovados pelo dono; o design precisa do dono e de mais um integrante. As perguntas de cada spec estão na seção "Perguntas em aberto" do `requirements.md`, com uma recomendação.

| Spec | O que falta decidir | O que fica bloqueado |
|---|---|---|
| 007 · Validação de dados | Aprovar os três arquivos; e-mail da unidade, critério de coordenadas, telefone com máscara e tratamento dos dados antigos | Critério 6.1 ("dado inválido não é gravado"); números reais de pendências no dashboard |
| 004 · LDAP e OIDC | Aprovar os três arquivos e aceitar o ADR-0003 | Requisito obrigatório da disciplina; mapeamento de grupos para papéis (003/T8) |
| 005 · Exportação para S3 | Aprovar os três arquivos, aceitar o ADR-0005 e incluir design e tarefa da R5 (assinatura digital), hoje ausentes | Requisito obrigatório da disciplina; objetivo de assinatura digital da disciplina de Criptografia |
| 010 · Dados de demonstração | Aprovar a correção do design do conversor (D010-6) | Nada até a planilha chegar |
| 012 · Frontend | Requisitos aprovados (Vinicius, 09/11/2026); falta aprovar a emenda documental 1 (10/11/2026). G2 do design: dono + Igor Fugagnoli (principal, **disponibilidade a confirmar**) ou Erick Sanches (suplente). Depois, G3 das tarefas pelo dono | Toda a implementação do front (`AGENTS.md`, regra 1) |

## 2. Cliente (Secretaria de Saúde)
| Pergunta | Para quê | Spec |
|---|---|---|
| Enviar a planilha REDE_SAUDE_RECIFE_GEO, ou uma amostra anonimizada (cerca de 20 linhas), com a regra de classificação por escrito | Converter a planilha em dados do sistema | 010/T3 |
| A planilha pode ficar no repositório do projeto? | Definir onde guardar o arquivo | 010 |
| A Secretaria usa Active Directory ou OpenLDAP? | Configurar a conexão com o diretório | 004 |
| Algum atributo do diretório indica o distrito ou a unidade do usuário? | Dar o escopo de acesso automaticamente | 004 |
| Quais campos são obrigatórios além dos atuais? (o campo "Gerente" foi citado) | Definir as regras de validação | 007 |
| Alguma unidade fica fora da faixa de CEP de Recife (50000-000 a 52999-999)? | Validar o CEP sem recusar unidades reais | 007 |
| **Ratificar as premissas adotadas pelo Grupo 01 em 10/11/2026** (PF-07; pendências derivadas PF-01 a PF-05, com responsável, prazo e solução provisória em `specs/012-frontend/requirements.md` § Pendências formais) (sem retorno do cliente até essa data): acesso e leitura no escopo do perfil (Grupo-DF2), permissões por perfil (Grupo-DF13) e campos de edição direta × sensíveis (Grupo-DF14), com as perguntas P1 a P4 | Fluxo de solicitações, leitura por escopo e permissões de exportação | 012 (§ Decisões), 003, spec de solicitações |

## 3. Grupo
- Levar ao professor a questão das 30 tuplas nos domínios fechados: distritos (8), papéis (7), áreas técnicas (4) e tipos. Justificativa em [`docs/banco/06-trinta-tuplas.md`](../banco/06-trinta-tuplas.md).
- Spec 005: confirmar se haverá conta AWS para a demonstração (recomendação: SeaweedFS no compose) e o prazo de guarda dos relatórios (recomendação: 90 dias).
- **Integração do protótipo** (decisões numeradas na spec 012, § Decisões):
  - **já decididas:** login por `username` com o rótulo "Usuário" (DF7), 2FA em texto (DF6), telas para os 7 papéis (DF8), exportação pelo backend (DF10, Grupo-DF15);
  - **pendentes:** conceito de equipamento (DF1), lista de situações (DF3), endereço separado, horário editável e e-mail da unidade (emenda da 006), colunas do CSV e layout do PDF (P5).

  Detalhes em [`docs/frontend-integracao.md`](../frontend-integracao.md) § 3 e 5. O que mudar a API vira emenda na spec 006. **Responsável pela 006: Hélder** (decisão do Grupo 01, 10/11/2026; a formalização na spec parte da `feat/003-interface-dashboard` e do ADR-0009).

## 4. Infraestrutura e outras equipes
| Pendência | Situação | Quem resolve |
|---|---|---|
| GitHub Actions | **Atualização de 10/11/2026:** as verificações `quality` e `compose-smoke` rodaram e passaram nos PRs #1, #2 e #3 (`gh pr checks`), então o bloqueio descrito antes não se confirma mais. O merge continua sendo feito pelo administrador (ADR-0008) | Vinicius |
| Integração do front | Especificada na spec 012 (requisitos aprovados; design e tarefas aguardando o G2 e o G3). O protótipo fica fora do Git, em `frontend/prototipo/`. A matriz de tela, endpoint e estado está em `specs/012-frontend/design.md` | Vinicius (dono da 012); Hélder (autor do design, UX) |
