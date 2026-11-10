# SGS API · Resumo do status do projeto

*Situação em 09/11/2026, depois da consolidação final. Detalhes técnicos: [RELATORIO_VALIDACAO_FINAL.md](RELATORIO_VALIDACAO_FINAL.md). Requisito por requisito: [REQUISITOS_EVIDENCIAS.md](REQUISITOS_EVIDENCIAS.md).*

**Legenda:** ✅ pronto e testado · 🟡 parcial · ⬜ falta

---

## 1. Situação final
- **Base única:** a `main` local agora reúne tudo. A base é a `feat/011-integracao`, com o histórico preservado, mais a auditoria e todas as implementações desta consolidação.
- **Da `feat/003-interface-dashboard` (Vinicius)**, reaproveitamos os dados das unidades, as 4 consultas da Etapa 3, o formato do resumo do dashboard e o desenho das rotas de equipamento, reescritos para o esquema e a segurança da 011. O código dela não foi mesclado.
- **Nenhuma branch foi apagada** e **nada foi publicado** (sem push). Há backup completo: tags `arquivo/*` e o bundle.
- **Testes:** 888 casos, **885 aprovados**, 3 pulados de propósito, **0 falhas**.

## 2. O que foi implementado
| Área | O que existe agora |
|---|---|
| **Cadastro** | ✅ CRUD completo de unidades (com busca sem acento, filtros, controle de edição simultânea e desativação), equipamentos, serviços e tabelas de referência |
| **Banco de dados** | ✅ Views, funções, procedures (uma com cursor), triggers, índices com prova de uso, CASCADE e SET NULL, 30 registros ou mais nas tabelas de negócio, SQL único que instala tudo (`make sql-bd`) |
| **Consultas e dashboard** | ✅ 8 consultas (anti join, full outer join, 2 subconsultas e as 4 da Etapa 3), inventário, resumo da rede e catálogo com gráfico sugerido; cada papel vê só o seu escopo |
| **Login e segurança** | ✅ Usuário e senha (Argon2id) com 2FA por aplicativo (TOTP), sessão renovável e segura, bloqueio por tentativas, limite por IP, logout |
| **Permissões** | ✅ 7 papéis com escopo, acesso negado por padrão, `/me`, administração de papéis, segregação de funções |
| **Auditoria** | ✅ Histórico de cada unidade, trilha geral para o auditor, verificação de integridade da cadeia, log do banco; nome do gestor mascarado (LGPD) |
| **Dados de demonstração** | ✅ `sgs-admin seed demo`: 37 unidades, 31 equipamentos, 35 serviços, 30 usuários fictícios |
| **Documentação** | ✅ Minimundo, modelos, dicionário de dados, objetos de banco, governança (fornecedores, riscos, ISO 38500, COBIT, LGPD), API, instalação |

## 3. O que foi parcialmente implementado
| Item | Situação |
|---|---|
| 30 registros por tabela | 🟡 As tabelas de negócio passam de 30. Distritos (8), papéis (7) e outros domínios fechados ficam com a quantidade real, com justificativa. **O professor precisa confirmar.** |
| Gráficos | 🟡 A API entrega os dados e o gráfico sugerido; quem desenha é o front |
| LGPD | 🟡 Medidas técnicas prontas; processos da Secretaria (titulares, encarregado) ficam fora do sistema |
| Integração com diretório | 🟡 O banco já prevê usuários LDAP e OIDC, mas a integração não existe |

## 4. O que falta
| Item | Depende de |
|---|---|
| ⬜ Integrar o front em HTML (o protótipo existe fora do repositório; as telas já têm endpoint mapeado) | Equipe do front |
| ⬜ LDAP e OIDC (spec 004) | Aprovação da spec |
| ⬜ Exportar relatórios para o S3 (spec 005) | Aprovação da spec |
| ⬜ Regras de validação e pendências (spec 007) | Aprovação da spec |
| ⬜ Testes de desempenho da busca e do dashboard | — |
| ⬜ Mapeamento de grupos do diretório para papéis (003/T8) | Spec 004 (LDAP/OIDC) |
| ⬜ Conversor da planilha REDE_SAUDE_RECIFE_GEO (010/T3) | A planilha não está disponível |
| ⬜ Cache do resumo do dashboard (009/T2) | Só se o teste de desempenho exigir |

## 5. Testes executados (09/11/2026)
| Execução | Resultado |
|---|---|
| `make check` (qualidade do código + testes rápidos) | 878 aprovados |
| `make test-all` (tudo, inclusive Docker e TLS) | 885 aprovados, 3 pulados, 0 falhas |
| Roteiro de aceitação do MVP (login → cadastro → dashboard → auditoria → logout) | Aprovado |
| Prova de uso dos índices com 1.000 unidades | Aprovada |
| Análise de segurança (`bandit`, `pip-audit`) | Sem achados |

## 6. Pendências e limitações
- **Specs regularizadas:** as specs 008, 009 e 010 e as emendas da 011 foram implementadas antes do portão de aprovação, por decisão nossa, e aprovadas em 09/11/2026 pelo dono, Vinicius, que também assumiu a 003 ([relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md](relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md)). **A meta de desempenho do dashboard (009/R1.7) ainda não foi medida.**
- **CI:** o GitHub Actions segue bloqueado; os testes rodaram localmente.
- **Proxy:** o ambiente completo com o proxy HTTPS não foi testado nesta máquina, porque as portas estavam ocupadas por outro ambiente, que preservamos. Banco, API, TLS e comandos foram testados num ambiente isolado.
- **Rate limit:** o limite de login vale por processo da API.

## 7. Próximos passos
1. **Tarefas abertas das specs aprovadas:** 009/T2b e T3 (cache e desempenho), 010/T3 (conversor, quando o cliente enviar a planilha).
2. **Grupo:** levar ao professor a decisão das 30 tuplas nos domínios fechados.
3. **Front:** integrar o HTML seguindo `docs/frontend-integracao.md`.
4. **Publicação:** criar o repositório novo no GitHub e enviar a `main` (os comandos estão no fim do relatório técnico). Isso depende de autorização.
5. **Depois das entregas:** specs 004 (LDAP/OIDC), 005 (S3) e 007 (validação).

> ⚠️ Push, publicação e exclusão de branches **ainda dependem de autorização**. Os secrets de desenvolvimento ficam fora do Git.
