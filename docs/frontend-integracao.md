# Integração com o front em HTML

**Situação (09/11/2026):** o front **não está neste repositório**. Há protótipos locais do grupo, fora do Git:
- `Prototipo_SGS_Recife_v2.html` (25/09/2026, 145 KB), na pasta do Projeto 3 dos integrantes (numa máquina, `Área de trabalho/entregável8deprojetos/`; noutra, `Projetos 3/`);
- duas cópias de uma versão anterior em `TEMP/`.

O protótipo é uma página única que **guarda os dados no `localStorage`** e não chama nenhuma API. Integrá-lo é trocar esse armazenamento por chamadas à API, mas antes o grupo precisa resolver as divergências da seção 3: os dados do protótipo e os da API não são os mesmos.

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
- São conceitos diferentes. O grupo precisa decidir se a aba do protótipo muda para equipamentos de saúde ou se o inventário vira outro recurso (spec nova).

### 3.3 Serviços
- No protótipo, o usuário marca nomes numa lista de 18 opções (acolhimento, vacinação, pré-natal, saúde bucal...) e pode digitar "outro serviço".
- Na API, cada serviço é um registro com `tipo_servico_id` obrigatório, e só há 4 tipos (`FARMACIA`, `FARMACIA_FAMILIA`, `SALA_VACINA`, `ESPACO_MAE_CORUJA`).
- Os tipos que faltam podem ser cadastrados por `POST /referencias/tipos-servico`. "Outro serviço" em texto livre não tem onde entrar.

### 3.4 Login e perfis
- **Login:** o protótipo pede e-mail institucional; a API pede `username`.
- **2FA:** o protótipo usa um código fixo de demonstração. A API exige, no primeiro acesso, o cadastro num aplicativo autenticador (`/mfa/enroll` devolve o QR code), e o protótipo não tem essa tela.
- **Perfis:** o protótipo tem 3; a API tem 7 papéis. Correspondência proposta: `central` → `GESTOR_DADOS`; `distrito` → `TECNICO_DISTRITAL`; `unidade` → `GESTOR_UNIDADE`. `DIRETORIA`, `AUDITOR`, `ADMIN_TI` e `COORD_TECNICO` não têm tela.

## 4. Funções do protótipo sem endpoint
| Função | Situação na API |
|---|---|
| Fluxo de solicitação: distrito e unidade solicitam, o nível central aprova ou devolve com motivo | Fora do MVP (RF-04). Na API, o técnico distrital e o gestor de unidade editam direto no seu escopo; o modo "direto" do protótipo serve para todos os perfis |
| Qualidade dos dados (8 verificações) e regras que bloqueiam a gravação | Spec 007, em Rascunho. A API só devolve a contagem `pendencias`, hoje preenchida pelo seed |
| "Confirmar revisão" (marcar a ficha como conferida sem alterar) | Não existe |
| Importar planilha | Spec 010/T3, que depende da planilha do cliente |
| Exportar lista (CSV) | O front pode gerar o arquivo a partir de `GET /unidades`; a exportação da spec 005 é outra coisa (relatórios no S3) |
| Notificações | Não existe |
| "Esqueci minha senha" | Não existe |
| Ordenar por "mais pendências" | Não existe; a API ordena por `nome`, `distrito` ou `atualizacao` |

As 8 verificações de qualidade do protótipo são uma base pronta para as decisões da spec 007: CEP entre 50000-000 e 52999-999, telefone com DDD 81 e 10 ou 11 dígitos, horário com abertura antes do fechamento, pelo menos um serviço e ficha revisada há menos de 12 meses.

## 5. Decisões antes de integrar
1. **Sem código:** cadastrar pela API os tipos de unidade e de serviço que faltam (3.1, 3.3).
2. **Do grupo:** conceito de equipamento (3.2), lista de situações, endereço separado ou não, horário editável, e-mail da unidade, login por e-mail ou por `username`.
3. **Emendas:** as decisões que mudam a API alteram a spec **006**, aprovada e cujo dono é o Rafael; cada uma vira emenda aprovada por ele.
