# Endpoints da API

Gerado das rotas do app (`src/main.py`). Contrato completo, com schemas e erros: `contracts/openapi.yaml` (`make openapi`) e, em dev, `https://localhost/docs`. Erros em `application/problem+json` (RFC 9457).

| Método | Rota | O que faz | Acesso |
|---|---|---|---|
| GET | `/.well-known/jwks.json` | Chaves públicas de verificação dos access tokens | pública |
| GET | `/health/live` | O processo está no ar | pública |
| GET | `/health/ready` | A API está pronta: o banco responde | pública |
| GET | `/api/v1/admin/atribuicoes` | Atribuições vigentes | `papel:assign` |
| POST | `/api/v1/admin/atribuicoes` | Atribuir papel | `papel:assign` |
| DELETE | `/api/v1/admin/atribuicoes/{id_}` | Remover atribuição | `papel:assign` |
| GET | `/api/v1/admin/papeis` | Papéis e o escopo que cada um exige | `papel:assign` |
| GET | `/api/v1/auditoria/banco` | Log do banco (trigger trg_registry_change_log) | `auditoria:read` |
| GET | `/api/v1/auditoria/banco/particoes` | Partições mensais do log do banco | `auditoria:read` |
| GET | `/api/v1/auditoria/eventos` | Trilha geral de auditoria | `auditoria:read` |
| GET | `/api/v1/auditoria/eventos/{id_}` | Evento da trilha com hash | `auditoria:read` |
| POST | `/api/v1/auditoria/verificar` | Verificar a integridade da cadeia de hash | `auditoria:read` |
| POST | `/api/v1/auth/login` | Login com usuário e senha | pública |
| POST | `/api/v1/auth/logout` | Sair (revoga a sessão) | Bearer (sem permissão) |
| POST | `/api/v1/auth/mfa/confirm` | Confirmar o 2FA e entrar | pública |
| POST | `/api/v1/auth/mfa/enroll` | Iniciar o cadastro do 2FA | pública |
| POST | `/api/v1/auth/mfa/verify` | Verificar o código do 2FA e entrar | pública |
| POST | `/api/v1/auth/refresh` | Renovar o access token (refresh rotativo) | pública |
| GET | `/api/v1/dashboard/consultas` | Catálogo das consultas e views disponíveis | `dashboard:read` |
| GET | `/api/v1/dashboard/consultas/alteracoes-por-periodo` | Alterações em 7 e 30 dias por distrito | `dashboard:read` |
| GET | `/api/v1/dashboard/consultas/alteracoes-recentes` | As 10 alterações mais recentes | `dashboard:read` |
| GET | `/api/v1/dashboard/consultas/conciliacao-unidade-equipamento` | Conciliação unidade x equipamento (full outer join) | `dashboard:read` |
| GET | `/api/v1/dashboard/consultas/distritos-sem-cnes-acima-da-rede` | Distritos com percentual de unidades sem CNES acima da rede (subconsulta) | `dashboard:read` |
| GET | `/api/v1/dashboard/consultas/equipamentos-por-tipo-e-distrito` | Equipamentos por tipo e distrito | `dashboard:read` |
| GET | `/api/v1/dashboard/consultas/unidades-com-servico-fora-do-cnes` | Unidades com ao menos um serviço fora do CNES (subconsulta EXISTS) | `dashboard:read` |
| GET | `/api/v1/dashboard/consultas/unidades-por-categoria` | Unidades por status, tipo, área e distrito | `dashboard:read` |
| GET | `/api/v1/dashboard/consultas/unidades-sem-servico` | Unidades sem nenhum serviço cadastrado (anti join) | `dashboard:read` |
| GET | `/api/v1/dashboard/inventario` | Inventário da rede (vw_unit_inventory) | `dashboard:read` |
| GET | `/api/v1/dashboard/resumo` | Resumo da rede: unidades, qualidade e alterações | `dashboard:read` |
| GET | `/api/v1/equipamentos` | Equipamentos sem unidade | `equipamento:write` |
| POST | `/api/v1/equipamentos` | Cadastrar equipamento sem unidade | `equipamento:write` |
| PATCH | `/api/v1/equipamentos/{equipamento_id}` | Alterar equipamento sem unidade | `equipamento:write` |
| DELETE | `/api/v1/equipamentos/{equipamento_id}` | Remover equipamento sem unidade | `equipamento:write` |
| GET | `/api/v1/me` | Perfil do usuário logado | autenticado |
| GET | `/api/v1/referencias/{tipo}` | Listar uma tabela de referência | `unidade:read` |
| POST | `/api/v1/referencias/{tipo}` | Incluir item de referência | `regra_validacao:manage` |
| PATCH | `/api/v1/referencias/{tipo}/{id_}` | Alterar item de referência (código, nome, ativo) | `regra_validacao:manage` |
| GET | `/api/v1/servicos` | Serviços soltos (sem unidade) | `servico:write` |
| POST | `/api/v1/servicos` | Cadastrar serviço solto | `servico:write` |
| PATCH | `/api/v1/servicos/{servico_id}` | Alterar serviço solto | `servico:write` |
| DELETE | `/api/v1/servicos/{servico_id}` | Remover serviço solto | `servico:write` |
| GET | `/api/v1/unidades` | Listar e buscar unidades | `unidade:read` |
| POST | `/api/v1/unidades` | Cadastrar unidade de saúde | `unidade:create` |
| GET | `/api/v1/unidades/{id}` | Detalhar unidade com equipamentos e serviços | `unidade:read` no escopo da unidade |
| PATCH | `/api/v1/unidades/{id}` | Atualizar unidade (If-Match) | `unidade:update` no escopo da unidade |
| POST | `/api/v1/unidades/{id}/desativar` | Desativar unidade (procedimento sp_deactivate_unit) | `unidade:deactivate` no escopo da unidade |
| GET | `/api/v1/unidades/{id}/equipamentos` | Equipamentos da unidade | `unidade:read` no escopo da unidade |
| POST | `/api/v1/unidades/{id}/equipamentos` | Adicionar equipamento à unidade | `equipamento:write` no escopo da unidade |
| PATCH | `/api/v1/unidades/{id}/equipamentos/{equipamento_id}` | Alterar equipamento da unidade | `equipamento:write` no escopo da unidade |
| DELETE | `/api/v1/unidades/{id}/equipamentos/{equipamento_id}` | Remover equipamento da unidade | `equipamento:write` no escopo da unidade |
| GET | `/api/v1/unidades/{id}/historico` | Histórico da unidade (vw_unit_history) | `auditoria:read` no escopo da unidade |
| GET | `/api/v1/unidades/{id}/servicos` | Serviços da unidade | `unidade:read` no escopo da unidade |
| POST | `/api/v1/unidades/{id}/servicos` | Adicionar serviço à unidade | `servico:write` no escopo da unidade |
| PATCH | `/api/v1/unidades/{id}/servicos/{servico_id}` | Alterar serviço da unidade | `servico:write` no escopo da unidade |
| DELETE | `/api/v1/unidades/{id}/servicos/{servico_id}` | Remover serviço da unidade | `servico:write` no escopo da unidade |

Total: 55 operações.
