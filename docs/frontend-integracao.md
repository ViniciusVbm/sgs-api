# Integração com o front em HTML

**Situação (09/11/2026):** o front **não está neste repositório**. Há protótipos locais do grupo, fora do Git:
- `Área de trabalho/entregável8deprojetos/Prototipo_SGS_Recife_v2.html` (25/09, 145 KB);
- duas cópias de uma versão anterior em `TEMP/`.

O protótipo é uma página única que **guarda os dados no `localStorage`** e não chama nenhuma API. Integrá-lo é trocar esse armazenamento por chamadas à API. Esse trabalho fica para a etapa seguinte, por decisão do usuário; nenhuma interface foi criada aqui.

## Telas do protótipo → endpoints
| Tela do protótipo | Endpoint |
|---|---|
| Entrar / "Confirme que é você" | `POST /api/v1/auth/login`, `/mfa/enroll`, `/mfa/confirm`, `/mfa/verify` |
| Saudação e perfil (papel do usuário) | `GET /api/v1/me` |
| "Unidades da rede" / "Unidades do distrito" | `GET /api/v1/unidades` (o escopo já filtra) |
| Ficha da unidade (identificação, localização, contato) | `GET`/`PATCH /api/v1/unidades/{id}` (com `If-Match`) |
| "Cadastrar unidade" | `POST /api/v1/unidades` |
| "Equipamentos e infraestrutura" | `/api/v1/unidades/{id}/equipamentos` |
| "Serviços oferecidos" | `/api/v1/unidades/{id}/servicos` |
| "Histórico de alterações" / "Atividade recente" | `GET /api/v1/unidades/{id}/historico`, `GET /api/v1/dashboard/consultas/alteracoes-recentes` |
| "Unidades por distrito", "Por nível de atenção", "Qualidade dos dados" | `GET /api/v1/dashboard/resumo`, `/dashboard/consultas/*`, `/dashboard/inventario` |
| Listas de seleção (distrito, tipo) | `GET /api/v1/referencias/{tipo}` |
| "Validações", "Regras com pendência", "Devolver solicitação", "Importar planilha" | **sem endpoint**: specs 007 (validação) e RF-04 (workflow), fora desta versão |

## O que a API já oferece para o front
- **CORS:** `CORS_ORIGINS`. Servindo o HTML pelo Caddy no mesmo domínio (`https://localhost`), nem é preciso CORS, e o cookie de refresh funciona.
- **Contrato:** `contracts/openapi.yaml`.
- **Catálogo para os gráficos:** `GET /api/v1/dashboard/consultas` lista cada consulta com colunas e gráfico sugerido.
- **Erros:** `application/problem+json` com `detail` em português e `errors[{campo, mensagem}]` no 422.
