# Integração com o front em HTML

**Situação (atualizada em 10/11/2026):**
- **Onde está o front:** a integração é especificada na **spec 012** (`specs/012-frontend/`).
  - Os requisitos foram aprovados por Vinicius em 09/11/2026. O design e as tarefas estão em Rascunho, aguardando o G2 e o G3.
  - Pelo ADR-0010 (Proposto), o front fica neste repositório, em `frontend/app/`, servido pelo Caddy no mesmo domínio da API.
  - O protótipo de referência é `frontend/prototipo/Prototipo_SGS_Recife_v2.html` (25/09/2026, 145 KB). Ele fica **fora do Git**, e cópias também existem nas máquinas dos integrantes.
  - **Ainda não há código de interface**: nenhuma tarefa da 012 pode começar antes do G2 e do G3 (`AGENTS.md`, regra 1).
- **Como o protótipo funciona:** é uma página única que **guarda os dados no `localStorage`** e não chama nenhuma API. Integrá-lo é trocar esse armazenamento por chamadas à API.
- **Divergências:** as da seção 3 estão ligadas às decisões da spec 012 (DF1 a DF15 e as decisões e premissas do Grupo 01, em `specs/012-frontend/requirements.md` § Decisões). A matriz completa de tela, endpoint e estado está em `specs/012-frontend/design.md` § Matriz de integração.

## 1. Telas do protótipo → endpoints
| Tela do protótipo | Endpoint |
|---|---|
| Entrar / "Confirme que é você" | `POST /api/v1/auth/login`, `/mfa/enroll`, `/mfa/confirm`, `/mfa/verify` |
| Saudação e perfil (papel do usuário) | `GET /api/v1/me` |
| "Unidades da rede" / "Unidades do distrito" | `GET /api/v1/unidades` (o escopo já filtra) |
| Ficha da unidade (identificação, localização, contato) | `GET`/`PATCH /api/v1/unidades/{id}` (com `If-Match`) |
| "Cadastrar unidade" | `POST /api/v1/unidades` |
| "Equipamentos e infraestrutura" | `/api/v1/unidades/{id}/equipamentos` (ver 3.2: o conceito é outro) |
| "Serviços oferecidos" | `/api/v1/unidades/{id}/servicos` (ver 3.3) |
| "Histórico de alterações" / "Atividade recente" | `GET /api/v1/unidades/{id}/historico`, `GET /api/v1/dashboard/consultas/alteracoes-recentes` |
| "Unidades por distrito", "Por nível de atenção", "Qualidade dos dados" | `GET /api/v1/dashboard/resumo`, `/dashboard/consultas/*`, `/dashboard/inventario` |
| Listas de seleção (distrito, tipo) | `GET /api/v1/referencias/{tipo}` |
| "Validações", "Regras com pendência", "Devolver solicitação", "Importar planilha" | **sem endpoint** (seção 4) |

## 2. O que a API já oferece para o front
- **CORS:** `CORS_ORIGINS`. Servindo o HTML pelo Caddy no mesmo domínio (`https://localhost`), nem é preciso CORS, e o cookie de refresh funciona.
- **Contrato:** `contracts/openapi.yaml`.
- **Catálogo para os gráficos:** `GET /api/v1/dashboard/consultas` lista cada consulta com colunas e gráfico sugerido.
- **Erros:** `application/problem+json` com `detail` em português e `errors[{campo, mensagem}]` no 422.

## 3. Divergências entre o protótipo e a API (revisão de 09/11/2026)
Levantadas lendo o protótipo inteiro contra `contracts/openapi.yaml`, os schemas de `src/modules/registry/api/schemas.py` e o seed das migrações `0003` e `0006`.

### 3.1 Unidade
| Campo | Protótipo | API | O que fazer |
|---|---|---|---|
| Endereço | `logradouro`, `numero`, `complemento` separados | um campo, `endereco` | Juntar no envio; na leitura não dá para separar. Ou emenda na 006 |
| E-mail da unidade | existe | **não existe** | Tirar da tela, ou emenda na 006 |
| Horário de funcionamento | editável: abertura, fechamento ou 24 horas | só leitura: `horario_funcionamento` sai na resposta, mas o cadastro e a edição não o aceitam | Emenda na 006 para aceitar o campo |
| Situação | `Em funcionamento`, `Em reforma`, `Temporariamente fechada`, `Desativada` | `status`: `ativa`, `em_implantacao`, `inativa` | Decidir a lista única; não há correspondência um a um |
| Tipo de unidade | 14 tipos | 10 (7 da `0006` e 3 do seed de demonstração) | Faltam UBS, CAPS III, SRT, UA, Maternidade e SPA: o Gestor de Dados cadastra por `POST /referencias/tipos-unidade`, sem código |
| Nível de atenção | Atenção primária, Saúde mental, Atenção especializada, Urgência e emergência | área técnica: APS, Saúde Mental, Saúde Bucal, MAC | Decidir qual classificação o gráfico usa |
| Distrito | número de 1 a 8 | id e código `DS-I` a `DS-VIII` | Converter pela lista de `GET /referencias/distritos` |
| Nome do gestor, latitude, longitude | não existem | existem, opcionais | Nenhum |

### 3.2 Equipamentos (maior divergência)
- No protótipo, equipamento é **inventário**: computador, impressora, maca, geladeira de vacinas, com quantidade e estado (`Funcionando`, `Em manutenção`, `Parado`).
- Na API, é **equipamento de saúde**: policlínica, maternidade, UTI móvel, base do SAMU, academia da saúde, com `tipo_codigo` obrigatório e `status` (`ativo`, `inativo`, `em_manutencao`). É a definição de `steering/product.md` § Domínio.
- São conceitos diferentes. É a **DF1** da spec 012, ainda pendente (cliente + Hélder, responsável pela 006): decidir se a aba do protótipo muda para equipamentos de saúde ou se o inventário vira outro recurso (spec nova). Até lá, a aba aparece com "em desenvolvimento" e não grava em `equipments` (012/R9.1).

### 3.3 Serviços
- No protótipo, o usuário marca nomes numa lista de 18 opções (acolhimento, vacinação, pré-natal, saúde bucal...) e pode digitar "outro serviço".
- Na API, cada serviço é um registro com `tipo_servico_id` obrigatório, e só há 4 tipos (`FARMACIA`, `FARMACIA_FAMILIA`, `SALA_VACINA`, `ESPACO_MAE_CORUJA`).
- Os tipos que faltam podem ser cadastrados por `POST /referencias/tipos-servico`. "Outro serviço" em texto livre não tem onde entrar.

### 3.4 Login e perfis
- **Login:** o protótipo pede e-mail institucional; a API pede `username`. **Decidido (DF7, Vinicius, 09/11/2026):** a tela usa o rótulo "Usuário" e envia o `username`, sem mudar o contrato.
- **2FA:** o protótipo usa um código fixo de demonstração. A API exige, no primeiro acesso, o cadastro num aplicativo autenticador (`/mfa/enroll` devolve a `otpauth_uri`, que serve para gerar um QR code), e o protótipo não tem essa tela. **Decidido (DF6):** a tela mostra a chave e a URI como texto copiável, sem QR Code nesta entrega.
- **Perfis:** o protótipo tem 3; a API tem 7 papéis. Correspondência proposta: `central` → `GESTOR_DADOS`; `distrito` → `TECNICO_DISTRITAL`; `unidade` → `GESTOR_UNIDADE`. `DIRETORIA`, `AUDITOR`, `ADMIN_TI` e `COORD_TECNICO` não têm tela no protótipo. **Decidido (DF8):** a 012 cria telas para os 7 papéis, só com as permissões existentes (design § Perfis).

## 4. Funções do protótipo sem endpoint
| Função | Situação na API |
|---|---|
| Fluxo de solicitação: distrito e unidade solicitam, o nível central aprova ou devolve com motivo | Fora do MVP (RF-04); não há rota de solicitação. Na API, o técnico distrital e o gestor de unidade editam direto no seu escopo, menos distrito, tipo e CNES, que dão 403 (`campos_estruturais`). A interface da 012 **não oferece** essa edição direta (012/R7.4) até a decisão. O Grupo 01 adotou em 10/11/2026, como **premissas ainda não ratificadas pelo cliente**, a edição direta de nome, endereço, CEP e telefone e a aprovação central de CNES, tipo, status, distrito e vínculo (Grupo-DF13 e Grupo-DF14, 012 § Decisões). Isso exige a spec de solicitações |
| Qualidade dos dados (8 verificações) e regras que bloqueiam a gravação | Spec 007, em Rascunho. A API só devolve a contagem `pendencias`, hoje preenchida pelo seed |
| "Confirmar revisão" (marcar a ficha como conferida sem alterar) | Não existe |
| Importar planilha | Spec 010/T3, que depende da planilha do cliente |
| Exportar lista (CSV) e relatório (PDF) | Não existe. **Decidido (DF10 e Grupo-DF15):** o backend gera, no escopo do usuário, CSV para dados e PDF para relatório, e audita cada exportação; o front só baixa o arquivo e **não** gera CSV a partir de `GET /unidades`. A exportação da spec 005 é outra coisa (relatórios no S3). Faltam a spec do backend, as colunas e o layout |
| Notificações | Não existe |
| "Esqueci minha senha" | Não existe |
| Ordenar por "mais pendências" | Não existe; a API ordena por `nome`, `distrito` ou `atualizacao` |

As 8 verificações de qualidade do protótipo são uma base pronta para as decisões da spec 007: CEP entre 50000-000 e 52999-999, telefone com DDD 81 e 10 ou 11 dígitos, horário com abertura antes do fechamento, pelo menos um serviço e ficha revisada há menos de 12 meses.

## 5. Decisões antes de integrar
As decisões estão numeradas na spec 012 (`specs/012-frontend/requirements.md` § Decisões), que é a referência.

1. **Sem código:** cadastrar pela API os tipos de unidade e de serviço que faltam (3.1, 3.3). É o caminho da **DF5**, que depende do catálogo oficial do cliente.
2. **Já decididas:**
   - login por `username` com o rótulo "Usuário" (DF7);
   - 2FA com chave e URI em texto (DF6);
   - telas para os 7 papéis (DF8);
   - exportação pelo backend (DF10 e Grupo-DF15).
3. **Pendentes:**
   - conceito de equipamento (DF1);
   - lista de situações (DF3);
   - endereço separado ou não, horário editável e e-mail da unidade (emenda da 006, R6.4).
4. **Premissas do grupo que aguardam o cliente:** acesso e leitura no escopo (Grupo-DF2), permissões por perfil (Grupo-DF13) e campos diretos × sensíveis (Grupo-DF14). As perguntas abertas por elas viraram as pendências formais **PF-01 a PF-07**, com solução provisória (spec 012 § Pendências formais). As únicas resolvidas são técnicas: "Coordenador do DS" corresponde ao `TECNICO_DISTRITAL` pelo escopo, e não há "aprovar" na interface enquanto a API não tiver o fluxo.
5. **Emendas:** as decisões que mudam a API alteram a spec **006**, aprovada pelo Rafael em 07/11/2026. Por decisão do Grupo 01 (10/11/2026), o **responsável pela 006 é o Hélder**, com apoio técnico de Vinicius. A formalização na própria spec parte da branch `feat/003-interface-dashboard` e do ADR-0009. As mudanças de matriz RBAC são da spec 003 (dono: Vinicius).
