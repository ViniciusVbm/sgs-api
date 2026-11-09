# ISO/IEC 38500 e COBIT 2019 (APO10)

Mapeamento dos controles do repositório para os princípios e práticas. É material de apoio, **não declaração de conformidade**.

## ISO/IEC 38500: princípios e modelo Avaliar–Dirigir–Monitorar
| Princípio | Como o projeto atende (evidência) | Lacuna |
|---|---|---|
| Responsabilidade | Papéis com responsabilidades e escopos definidos (`migrations/versions/0003_access.py`, matriz); dono humano por spec (`specs/*/requirements.md`); aprovação por PR (ADR-0008) | As specs 008, 009 e 010 aguardam aprovação do dono |
| Estratégia | Specs rastreiam requisitos do cliente e das disciplinas (`specs/README.md`, campo "Rastreia") | — |
| Aquisição | Dependências novas por ADR (ADR-0007, com emenda); `steering/tech.md` com versões | Sem processo formal de contratação (fora do repositório) |
| Desempenho | Índices provados por `EXPLAIN` com volume (`docs/banco/planos-indices.txt`); testes automatizados (`make check`) | Testes de carga do dashboard (009/T3) pendentes |
| Conformidade | Trilha imutável e verificável; RBAC deny by default; LGPD técnica (doc 05) | Sem auditoria externa |
| Comportamento humano | Mensagens em português; segregação de funções; regras para agentes de código (`AGENTS.md`) | Treinamento de usuários (fora do repositório) |

**Avaliar–Dirigir–Monitorar:**
- **Avaliar:** auditoria de integração (`docs/integration-audit/`).
- **Dirigir:** specs aprovadas e ADRs.
- **Monitorar:** CI, verificação da cadeia, log do banco, eventos `auth.*`.

## COBIT 2019 · APO10 (Gerenciar fornecedores)
| Prática | Evidência no repositório | Lacuna |
|---|---|---|
| APO10.01 Identificar e avaliar relações e contratos com fornecedores | Cadastro e classificação ([01-fornecedores.md](01-fornecedores.md)) | Contratos fora do repositório |
| APO10.02 Selecionar fornecedores | ADR-0007 (critérios: manutenção, licença, alternativa); pesquisa em `docs/research/01-pesquisa-stack-backend.md` | — |
| APO10.03 Gerenciar relações e contratos | Versões travadas (`uv.lock`); troca documentada (slowapi → limits) | — |
| APO10.04 Gerenciar riscos de fornecedores | Riscos R05, R06 ([03-registro-de-riscos.md](03-registro-de-riscos.md)); `pip-audit` no CI | Imagens sem digest; sem SBOM |
| APO10.05 Monitorar desempenho e conformidade dos fornecedores | `pip-audit` e `bandit` a cada PR; e2e do compose | Sem SLA dos fornecedores de infraestrutura |

**Outras práticas relacionadas:**
- **DSS05**, serviços de segurança: autenticação, RBAC, TLS, cifra de campo.
- **DSS04**, continuidade: reconstrução reprodutível do banco e chaves versionadas.
- **MEA01**, monitoramento: trilha, log do banco e CI.
