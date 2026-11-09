# Relatório de auditoria para publicação · SGS API

- **Data:** 09/11/2026.
- **Escopo:** auditoria final independente antes de publicar a `main` num repositório GitHub novo.
- Nenhuma funcionalidade nova, push, mudança de remote ou exclusão de branch.

## 1. Estado do Git
| Item | Resultado |
|---|---|
| Branch / commit auditado | `main` em `fdb02637283f7e71cd420dd26d5a116b5be42afd` ✅ |
| Árvore de trabalho | limpa (`git status` vazio) ✅ |
| Commits à frente de `origin/main` | 77, nenhum atrás; `origin/main` e `origin/feat/011-integracao` são ancestrais ✅ |
| Integridade | `git fsck` sem erros ✅ |
| Remoto `origin` | intocado: 15 branches; `origin/main` = `a2e2a47` ✅ |
| Preservação | tags locais `arquivo/*` e bundle `~/sgs-api-backup-20261109.bundle` (sha256 conferido) ✅ |

**Commit final:** a auditoria corrigiu só documentação, num commit de documentação depois de `fdb0263`, levado à `main` por fast-forward. O hash final é o mostrado por `git rev-parse main`, registrado na § 7.

## 2. Resultado da auditoria (os 12 itens)
| # | Verificação | Resultado |
|---|---|---|
| 1 | `main` em `fdb0263` | ✅ |
| 2 | Árvore limpa | ✅ |
| 3 | 77 commits preservados | ✅ |
| 4 | Relatórios × código | ✅ depois da correção. Conferidos: 888 testes, 7 `slow`, 55 operações, 48 consultas `.sql` (mais 4 modelos), 70 `.sql` de migração. A tabela de commits e a contagem de arquivos do `RELATORIO_VALIDACAO_FINAL.md` estavam defasadas e foram corrigidas |
| 5 | 3 testes pulados | ✅ justificáveis: `test_consulta_do_dashboard_aplica_o_escopo` pula `district_exists.sql`, `unit_type_exists.sql` e `technical_area_exists.sql`, que só verificam se uma referência existe e não leem o cadastro. O escopo do dashboard é validado por `test_consultas_qualidade.py`, `test_painel.py::test_escopo_do_tecnico_distrital_reduz_os_numeros` e pelo teste de arquitetura nas outras 13 consultas. Nenhum requisito obrigatório fica sem validação |
| 6 | Segredos | ✅ Nenhum `.env`, `secrets/`, `.pem`, `.key`, `.crt` ou arquivo de chaves em **nenhum commit** de nenhuma ref; nenhuma chave privada, token JWT, token do GitHub ou chave AWS no conteúdo de todo o histórico. Só há hashes de **teste** (`tests/factories.py`: Argon2id e bcrypt de senhas de teste), que são dados de fixture, não credenciais |
| 7 | Migrações em banco vazio | ✅ No clone limpo: `test_sql_bd.py` (DDL inteiro num banco vazio, até `0011_09`), `test_migracoes_sincronizadas.py`, e toda a suíte de integração parte de um banco vazio migrado |
| 8 | Instalação e execução pelo README | ✅ Clone limpo (`git clone` local): `uv sync --frozen`, geração das chaves, `make check` com 878 aprovados, `pytest -m slow` com 7 aprovados (compose isolado com TLS, `seed demo` e `create-user` dentro do container, prova dos índices). O `docker compose up` completo **com o proxy** não foi executado: as portas 80/443 desta máquina estão ocupadas por outro ambiente, que foi preservado |
| 9 | Dependências locais | ✅ Nada que impeça outro integrante. Exige uv (o Python 3.13 vem por `.python-version`), GNU Make e Docker 26+ com Compose v2, como diz o README. Os secrets são gerados por comandos documentados. O `.claude/settings.local.json` não é versionado |
| 10 | Specs 008, 009, 010 | ✅ Os 9 arquivos dizem "Rascunho … aguarda aprovação do Rafael. Implementada antes da aprovação por decisão do usuário"; as tarefas implementadas estão `[x]` com o teste. O relatório técnico registra o desvio da regra 1 do `AGENTS.md` |
| 11 | Pendências no resumo | ✅ depois da correção. Front, LDAP/OIDC, S3, spec 007 e testes de desempenho já constavam; foram acrescentados 003/T8, 010/T3 e 009/T2 |
| 12 | `.gitignore`, `.env.example`, README | ✅ O `.gitignore` cobre `.env*` (exceto o exemplo), `secrets/`, `*.pem`, `*.key`, `*.crt`, `build/`, `reports/`. O `.env.example` só tem marcadores (`troque`, chave de zeros recusada em prod). O README tem a instalação, os comandos e o índice da documentação |

## 3. Achados por gravidade
| Gravidade | Achado | Ação |
|---|---|---|
| Crítico | Nenhum | — |
| Médio | Tabela de commits e contagens do `RELATORIO_VALIDACAO_FINAL.md` defasadas | **Corrigido** |
| Médio | Resumo sem 003/T8, 010/T3 e 009/T2 | **Corrigido** |
| Baixo | Caminho absoluto desta máquina nas instruções de publicação | **Corrigido** no relatório técnico. Fica em `docs/integration-audit/07-plano-consolidacao.md`, um registro histórico |
| Baixo | O passo "opcional" de enviar todas as tags `arquivo/*` levaria ao público o histórico descartado da `feat/003`: hash bcrypt de senha de seed, segredos TOTP de marcação, `get-docker.sh`, specs com status trocado | **Corrigido**: as instruções agora dizem para **não** enviar `arquivo/003-*` e `arquivo/002-*` |
| Baixo | Nome e e-mail dos autores ficam públicos no histórico (já são, no repositório atual) | Só registro: mudar exigiria reescrever o histórico, o que é destrutivo e não foi feito |
| Baixo | `docs/integration-audit/*` cita caminhos de backups locais (sem conteúdo de segredo) | Registro; é histórico da auditoria |
| Informativo | `.env.example` usa `DATABASE_SSL_ROOT_CERT=/certs/ca.crt`, caminho do container. A API não lê `.env` sozinha; o compose define as variáveis | Nenhuma |
| Informativo | Aviso do `uv` 0.13.5 sobre `build-system.requires = uv-build <0.13` | Nenhuma: é só aviso; atualizar junto com a próxima revisão de dependências |

## 4. Testes confirmados nesta auditoria (09/11/2026)
| Onde | Execução | Resultado |
|---|---|---|
| Clone limpo de `fdb0263` | `make check` | 878 aprovados, 3 pulados (justificados), 0 falhas |
| Clone limpo | `pytest -m slow` | 7 aprovados (6 e2e no compose isolado, 1 prova dos índices) |
| Clone limpo | `test_sql_bd.py`, `test_migracoes_sincronizadas.py` | 3 aprovados |
| Clone limpo e repositório | `bandit -r src` / `pip-audit` | saída 0 / "No known vulnerabilities found" |
| Repositório, consolidação | `make test-all` | 885 aprovados, 3 pulados, 0 falhas (`RELATORIO_VALIDACAO_FINAL.md` § 7) |

## 5. Riscos restantes
- **Specs sem aprovação formal** (008, 009, 010 e as emendas da 011 e do ADR-0007). O Rafael precisa aprovar; até lá, essas partes são implementação antecipada.
- **CI do GitHub não executado** (Actions bloqueado). No repositório novo, rode o workflow, que traz os jobs `quality` e `compose-smoke`, e só então proteja a `main`.
- **Compose completo com o proxy** não testado nesta máquina. O job `compose-smoke` do CI cobre isso.
- **Rate limit em memória**, por processo.
- **Requisitos fora desta versão:** front integrado, LDAP/OIDC (004), S3 (005), validação (007), desempenho, conversor da planilha.
- **Decisão D1** (30 tuplas nos domínios fechados) a confirmar com o professor.

**Conclusão:** não há problema crítico. Os problemas médios e baixos de documentação foram corrigidos. **A `main` está apta à publicação**, com os riscos acima registrados e a ressalva de que as specs 008, 009 e 010 seguem em Rascunho.

## 6. Instruções exatas para publicação
1. No GitHub, crie o repositório **vazio**, sem README, `.gitignore` nem licença, e copie a URL.
2. No clone local:
```bash
cd sgs-api                                   # pasta do clone local
git switch main
git status --short                           # deve sair vazio
git ls-files | grep -E 'secrets/|\.env$|\.pem$|\.key$|\.crt$'   # deve sair vazio
git remote add novo <URL-DO-REPOSITORIO-NOVO>
git push -u novo main
```
3. **Opcional**, só as tags que apontam para commits já contidos na `main`:
```bash
git push novo refs/tags/arquivo/main-pre-consolidacao refs/tags/arquivo/011-integracao
```
   Não envie `arquivo/003-interface-dashboard` nem `arquivo/002-fundacao-vinicius` (ver § 3).
4. No repositório novo:
   - rode o CI;
   - proteja a `main` (ADR-0008);
   - abra uma issue para a aprovação das specs 008, 009 e 010.

O remote `origin` (`rafareloM/sgs-api`) continua como está; o novo é acrescentado como `novo`.

## 7. Commit final
Registrado depois do fast-forward, no fim da execução que gerou este arquivo:
- `git rev-parse main`;
- o commit "docs: correções da auditoria de publicação".
