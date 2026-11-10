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

## 2. Cliente (Secretaria de Saúde)
| Pergunta | Para quê | Spec |
|---|---|---|
| Enviar a planilha REDE_SAUDE_RECIFE_GEO, ou uma amostra anonimizada (cerca de 20 linhas), com a regra de classificação por escrito | Converter a planilha em dados do sistema | 010/T3 |
| A planilha pode ficar no repositório do projeto? | Definir onde guardar o arquivo | 010 |
| A Secretaria usa Active Directory ou OpenLDAP? | Configurar a conexão com o diretório | 004 |
| Algum atributo do diretório indica o distrito ou a unidade do usuário? | Dar o escopo de acesso automaticamente | 004 |
| Quais campos são obrigatórios além dos atuais? (o campo "Gerente" foi citado) | Definir as regras de validação | 007 |
| Alguma unidade fica fora da faixa de CEP de Recife (50000-000 a 52999-999)? | Validar o CEP sem recusar unidades reais | 007 |

## 3. Grupo
- Levar ao professor a questão das 30 tuplas nos domínios fechados: distritos (8), papéis (7), áreas técnicas (4) e tipos. Justificativa em [`docs/banco/06-trinta-tuplas.md`](../banco/06-trinta-tuplas.md).
- Spec 005: confirmar se haverá conta AWS para a demonstração (recomendação: SeaweedFS no compose) e o prazo de guarda dos relatórios (recomendação: 90 dias).

## 4. Infraestrutura e outras equipes
| Pendência | Situação | Quem resolve |
|---|---|---|
| GitHub Actions bloqueado | A `main` exige 2 verificações de CI, que não rodam; o `make check` local substitui o CI (ADR-0008), e o merge é feito pelo administrador | Vinicius |
| Integração do front | O protótipo HTML existe fora do repositório; as rotas de cada tela estão em [`docs/frontend-integracao.md`](../frontend-integracao.md) | Equipe do front |
